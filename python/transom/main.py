#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import argparse
import csv
import fnmatch
import http.server as httpserver
import mistune
import re
import shutil
import sys
import types
import threading
import traceback
import unicodedata
import yaml

from collections import defaultdict
from collections.abc import Iterable
from functools import cache, partial
from html import escape as html_escape
from html.parser import HTMLParser
# os.path.relpath is a lot faster than Path.relative_to in Python 3.12
from os.path import relpath as relative_path
from pathlib import Path
from queue import Queue
from urllib import parse as urlparse

__all__ = "TransomError", "TransomSite", "TransomCommand"

class TransomError(Exception):
    pass

class TransomSite:
    FALLBACK_PAGE_TEMPLATE = "<!doctype html>" \
        "<html lang=\"en\"><head><meta charset=\"utf-8\"><title>{{page.title}}</title></head>{{page.body}}</html>"
    FALLBACK_BODY_TEMPLATE = "<body>{{page.content}}</body>"

    def __init__(self, project_dir, verbose=False, quiet=False, threads=8):
        self.project_dir = Path(project_dir).resolve()
        self.config_dir = (self.project_dir / "config").relative_to(Path.cwd())
        self.input_dir = (self.project_dir / "input").relative_to(Path.cwd())
        self.output_dir = (self.project_dir / "output").relative_to(Path.cwd())

        self.verbose = verbose
        self.quiet = quiet
        self.threads = threads

        self.ignored_file_patterns = [".git", ".#*", "#*"]
        self.ignored_link_patterns = []

        self.prefix = ""
        self.config_dirs = [self.config_dir]
        self.config_modified = False

        self.files = list()
        self.index_files = dict() # parent input dir => File

        self.globals = {
            "site": SiteInterface(self),
            "include": include,
            "lipsum": lipsum,
            "plural": plural,
            "html_escape": html_escape,
            "html_table": html_table,
            "html_table_csv": html_table_csv,
            "load_template": partial(TransomSite.load_template, self),
            "TransomError": TransomError,
        }

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.project_dir}')"

    def init(self):
        page_template_path = self.config_dir / "page.html"
        body_template_path = self.config_dir / "body.html"
        site_code_path = self.config_dir / "site.py"

        self.page_template = Template(TransomSite.FALLBACK_PAGE_TEMPLATE, "[fallback]")
        self.body_template = Template(TransomSite.FALLBACK_BODY_TEMPLATE, "[fallback]")

        if page_template_path.exists():
            self.notice("Loading page template from '{}'", page_template_path)
            self.page_template = self.load_template(page_template_path)

        if body_template_path.exists():
            self.notice("Loading body template from '{}'", body_template_path)
            self.body_template = self.load_template(body_template_path)

        if site_code_path.exists():
            self.notice("Executing site code from '{}'", self.config_dir / "site.py")

            try:
                exec(site_code_path.read_text(), self.globals)
            except TransomError:
                raise
            except Exception as e:
                raise TransomError(f"{site_code_path}: {e}")

        self.ignored_file_re = re.compile \
            ("|".join([fnmatch.translate(x) for x in self.ignored_file_patterns] + ["(?!)"]))
        self.ignored_link_re = re.compile \
            ("|".join([fnmatch.translate(x) for x in self.ignored_link_patterns] + ["(?!)"]))

        self.init_files()

    def load_template(self, path):
        path = Path(path) if isinstance(path, str) else path
        return Template(path.read_text(), path)

    def init_files(self):
        self.files.clear()
        self.index_files.clear()

        for root, dirs, files in self.input_dir.walk():
            files = {x for x in files if not self.ignored_file_re.match(x)}
            index_files = {x for x in files if x in File.INDEX_FILE_NAMES}

            if len(index_files) > 1:
                raise TransomError(f"Duplicate index files in {root}")

            for name in index_files:
                self.files.append(self.init_file(root / name))

            for name in files - index_files:
                self.files.append(self.init_file(root / name))

    def init_file(self, input_path):
        output_path = self.output_dir / relative_path(input_path, self.input_dir)

        match "".join(input_path.suffixes):
            case ".md":
                return HtmlPage(self, input_path, output_path.with_suffix(".html"))
            case ".html.in":
                return HtmlPage(self, input_path, output_path.with_suffix(""))
            case ".css" | ".js" | ".html":
                return TemplateFile(self, input_path, output_path)
            case _:
                return StaticFile(self, input_path, output_path)

    def render(self, force=False):
        self.notice("Rendering files from '{}' to '{}'", self.input_dir, self.output_dir)

        if self.output_dir.exists():
            self.debug("Checking for config file changes")
            self.config_modified = self.compute_config_modified()

        self.notice("Found {:,} input {}", len(self.files), plural("file", len(self.files)))

        batch_size = (len(self.files) + self.threads - 1) // self.threads
        threads = list()
        render_counter = ThreadSafeCounter()
        errors = Queue()

        for i in range(self.threads):
            start = i * batch_size
            end = start + batch_size
            files = self.files[start:end]

            threads.append(RenderThread(self, f"render-thread-{i + 1:02}", files, errors))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.commands.put((thread.process_input_files, ()))

        for thread in threads:
            thread.commands.join()

        for thread in threads:
            thread.commands.put((thread.render_output_files, (force, render_counter)))
            thread.commands.put((None, None))

        for thread in threads:
            thread.join()

        if not errors.empty():
            raise errors.get()

        if self.output_dir.exists():
            self.output_dir.touch()

        rendered_count = render_counter.value()
        unchanged_count = len(self.files) - rendered_count
        unchanged_note = ""

        if unchanged_count > 0:
            unchanged_note = " ({:,} unchanged)".format(unchanged_count)

        self.notice("Rendered {:,} output {}{}", rendered_count, plural("file", rendered_count), unchanged_note)

    def compute_config_modified(self):
        output_mtime = self.output_dir.stat().st_mtime

        for config_dir in self.config_dirs:
            for path in (x for x in Path(config_dir).rglob("*") if not self.ignored_file_re.match(str(x))):
                try:
                    config_mtime = path.stat().st_mtime
                except (FileNotFoundError, PermissionError): # pragma: nocover
                    continue

                if config_mtime > output_mtime:
                    return True

        return False

    def serve(self, port=8080):
        watcher = None

        try:
            watcher = WatcherThread(self)
        except ImportError: # pragma: nocover
            self.notice("Failed to import pyinotify, so I won't auto-render updated input files\n"
                        "Try installing the Python inotify package\n"
                        "On Fedora, use 'dnf install python-inotify'")
        else:
            watcher.start()

        try:
            with Server(self, port) as server:
                self.notice("Serving at http://localhost:{}", port)
                server.serve_forever()
        except OSError as e:
            # OSError: [Errno 98] Address already in use
            if e.errno == 98:
                raise TransomError(f"Port {port} is already in use")
            else: # pragma: nocover
                raise
        finally:
            if watcher is not None:
                watcher.stop()

    def check_files(self):
        expected_paths = set(x.output_path for x in self.files)
        found_paths = set()

        for root, dirs, files in self.output_dir.walk():
            found_paths.update(root / x for x in files)

        missing_paths = expected_paths - found_paths
        extra_paths = found_paths - expected_paths

        if missing_paths:
            print("Missing output files:")

            for path in sorted(missing_paths):
                print(f"  {path}")

        if extra_paths:
            print("Extra output files:")

            for path in sorted(extra_paths):
                print(f"  {path}")

        return len(missing_paths), len(extra_paths)

    def check_links(self):
        link_sources = defaultdict(set) # link => files
        link_targets = set()
        errors = 0

        for file_ in self.files:
            file_.collect_link_data(link_sources, link_targets)

        for link in (x for x in link_sources.keys() if not self.ignored_link_re.match(x)):
            if link not in link_targets:
                errors += 1

                print(f"Error: Link to '{link}' has no destination")

                for source in link_sources[link]:
                    print(f"  Source: {source.input_path}")

        return errors

    def debug(self, message, *args):
        if self.verbose:
            print("{}: ".format(threading.current_thread().name), end="")
            print(message.format(*args))

    def notice(self, message, *args):
        if not self.quiet:
            if self.verbose:
                print("{}: ".format(threading.current_thread().name), end="")
            print(message.format(*args))

    def warning(self, message, *args):
        print("Warning:", message.format(*args))

class File:
    __slots__ = "site", "input_path", "input_mtime", "output_path", "output_mtime", "url", "title", "parent"
    INDEX_FILE_NAMES = "index.md", "index.html.in", "index.html"
    ROOT_PATHS = Path("/"), Path(".")

    def __init__(self, site, input_path, output_path):
        self.site = site

        self.input_path = input_path
        self.input_mtime = self.input_path.stat().st_mtime

        self.output_path = output_path
        self.output_mtime = None

        self.debug("Initializing file")

        self.url = f"{self.site.prefix}/{relative_path(self.output_path, self.site.output_dir)}"
        self.title = self.output_path.name
        self.parent = None

        parent_dir = self.input_path.parent

        if self.input_path.name in File.INDEX_FILE_NAMES:
            self.site.index_files[parent_dir] = self
            parent_dir = parent_dir.parent

        while parent_dir not in File.ROOT_PATHS:
            try:
                self.parent = self.site.index_files[parent_dir]
            except KeyError:
                parent_dir = parent_dir.parent
            else:
                break

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.input_path}', '{self.output_path}')"

    def is_modified(self):
        if self.output_mtime is None:
            try:
                self.output_mtime = self.output_path.stat().st_mtime
            except FileNotFoundError:
                return True

        return self.input_mtime > self.output_mtime

    def process_input(self):
        self.debug("Processing input")

    def render_output(self):
        self.debug("Rendering output")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def collect_link_data(self, link_sources, link_targets):
        link_targets.add(self.url)

        if not self.url.endswith(".html"):
            return

        parser = LinkParser(self, link_sources, link_targets)
        parser.feed(self.output_path.read_text())

    @property
    def ancestors(self):
        file_ = self

        while file_ is not None:
            yield file_
            file_ = file_.parent

    @property
    def children(self):
        for file_ in self.site.files:
            if file_.parent is self:
                yield file_

    def debug(self, message, *args):
        message = f"{self.input_path}: {message}"
        self.site.debug(message, *args)

class StaticFile(File):
    __slots__ = ()

    def render_output(self):
        super().render_output()
        shutil.copy(self.input_path, self.output_path)

class GeneratedFile(File):
    __slots__ = ()
    HEADER_RE = re.compile(r"(?s)^---\s*\n(.*?)\n---\s*\n")

    def is_modified(self):
        return super().is_modified() or self.site.config_modified

    def extract_header_code(self, text):
        match_ = GeneratedFile.HEADER_RE.match(text)

        if match_:
            return text[match_.end():], match_.group(1)

        return text, None

    def exec_header_code(self, header_code):
        self.debug("Executing header code")

        try:
            exec(header_code, self.site.globals, self.locals)
        except TransomError:
            raise
        except Exception as e:
            raise TransomError(f"{self.input_path}: header: {e}")

class TemplateFile(GeneratedFile):
    __slots__ = "template", "locals"

    def process_input(self):
        super().process_input()

        text = self.input_path.read_text()
        text, header_code = self.extract_header_code(text)

        self.template = Template(text, self.input_path)
        self.locals = None

        if header_code:
            self.exec_header_code(header_code)

    def render_output(self):
        super().render_output()
        self.template.write(self)

class HtmlPage(GeneratedFile):
    __slots__ = "page_template", "body_template", "content_template", "extra_headers", "locals"
    MARKDOWN_TITLE_RE = re.compile(r"(?s)^(?:#|##)\s+(.*?)\n")
    HTML_TITLE_RE = re.compile(r"(?si)<(?:h1|h2)\b[^>]*>(.*?)</(?:h1|h2)>")

    def process_input(self):
        super().process_input()

        text = self.input_path.read_text()
        text, header_code = self.extract_header_code(text)

        self.page_template = self.site.page_template
        self.body_template = self.site.body_template
        self.content_template = Template(text, self.input_path)
        self.extra_headers = ""

        match "".join(self.input_path.suffixes):
            case ".md":
                m = HtmlPage.MARKDOWN_TITLE_RE.search(text)
                self.title = m.group(1) if m else ""
            case ".html.in":
                m = HtmlPage.HTML_TITLE_RE.search(text)
                self.title = m.group(1) if m else ""

        self.locals = {
            "page": PageInterface(self),
            "render": partial(HtmlPage.render_file, self),
            "path_nav": partial(HtmlPage.path_nav, self),
            "toc_nav": partial(HtmlPage.toc_nav, self),
            "directory_nav": partial(HtmlPage.directory_nav, self),
        }

        if header_code:
            self.exec_header_code(header_code)

    def render_output(self):
        super().render_output()
        self.page_template.write(self)

    @property
    def body(self):
        return self.body_template.render(self)

    @property
    @cache
    def content(self):
        pieces = self.content_template.render(self)

        if self.input_path.suffix == ".md":
            return self.convert_markdown("".join(pieces))

        return pieces

    def render_file(self, path):
        path = Path(path) if isinstance(path, str) else path
        pieces = self.site.load_template(path).render(self)

        if path.suffix == ".md":
            return self.convert_markdown("".join(pieces))

        return pieces

    def convert_markdown(self, text):
        try:
            return MarkdownLocal.INSTANCE.value(text)
        except Exception as e:
            raise TransomError(f"Error converting Markdown: {self.input_path}: {e}")

    def path_nav(self, start=0, end=None, min=1):
        files = reversed(list(self.ancestors))
        links = tuple(f"<a href=\"{x.url}\">{x.title}</a>" for x in files)
        links = links[start:end]

        if len(links) < min:
            return ""

        return f"<nav class=\"page-path\">{''.join(links)}</nav>"

    def toc_nav(self):
        parser = HeadingParser()
        parser.feed("".join(self.content))

        links = tuple(f"<a href=\"#{x[1]}\">{x[2]}</a>" for x in parser.headings
                      if x[0] in ("h1", "h2") and x[1] is not None)

        return f"<nav class=\"page-toc\">{''.join(links)}</nav>"

    def directory_nav(self):
        children = sorted(self.children, key=lambda x: x.title)
        links = tuple("<a href=\"{}\">{}</a>".format(x.url, x.title) for x in children)

        return f"<nav class=\"page-directory\">{''.join(links)}</nav>"

class Template:
    __slots__ = "pieces", "path"
    VARIABLE_RE = re.compile(r"({{{.+?}}}|{{.+?}})")

    def __init__(self, text, path):
        self.pieces = list()
        self.path = path

        self.parse(text)

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.path}')"

    def parse(self, text):
        for token in Template.VARIABLE_RE.split(text):
            if token.startswith("{{{") and token.endswith("}}}"):
                piece = token[1:-1]
            elif token.startswith("{{") and token.endswith("}}"):
                try:
                    piece = compile(token[2:-2], "<string>", "eval"), token
                except Exception as e:
                    raise TransomError(f"Error parsing template: {self.path}: {e}")
            else:
                piece = token

            self.pieces.append(piece)

    def render(self, file_):
        for piece in self.pieces:
            if type(piece) is tuple:
                code, token = piece

                try:
                    result = eval(code, file_.site.globals, file_.locals)
                except TransomError:
                    raise
                except Exception as e:
                    raise TransomError(f"{self.path}: {token}: {e}")

                if type(result) is types.GeneratorType:
                    yield from result
                else:
                    yield str(result)
            else:
                yield piece

    def write(self, file_):
        text = "".join(self.render(file_))
        file_.output_path.write_text(text)

class RestrictedInterface:
    __slots__ = "_object", "_allowed"

    def __init__(self, obj, allowed):
        object.__setattr__(self, "_object", obj)
        object.__setattr__(self, "_allowed", allowed)

    def __repr__(self):
        return getattr(self._object, "__repr__")()

    def __getattribute__(self, name):
        if name in RestrictedInterface.__slots__:
            return object.__getattribute__(self, name)

        if name in self._allowed:
            return getattr(self._object, name)

        raise AttributeError(f"Accessing '{name}' is not allowed")

    def __setattr__(self, name, value):
        assert name not in RestrictedInterface.__slots__

        if name in self._allowed:
            setattr(self._object, name, value)
            return

        raise AttributeError(f"Accessing '{name}' is not allowed")

class SiteInterface(RestrictedInterface):
    __slots__ = ()

    def __init__(self, obj):
        allowed = "prefix", "config_dirs", "ignored_file_patterns", "ignored_link_patterns", \
            "page_template", "body_template"
        super().__init__(obj, allowed)

class PageInterface(RestrictedInterface):
    __slots__ = ()

    def __init__(self, obj):
        allowed = "url", "title", "parent", "body", "content", "extra_headers", \
            "page_template", "body_template"
        super().__init__(obj, allowed)

class RenderThread(threading.Thread):
    def __init__(self, site, name, files, errors):
        super().__init__(name=name)

        self.site = site
        self.files = files
        self.errors = errors
        self.commands = Queue()

    def run(self):
        while True:
            command, args = self.commands.get()

            if command is None:
                break

            try:
                command(*args)
            except Exception as e:
                traceback.print_exc()
                self.errors.put(e)
            finally:
                self.commands.task_done()

    def process_input_files(self):
        for file_ in self.files:
            file_.process_input()

    def render_output_files(self, force, render_counter):
        for file_ in self.files:
            if force or file_.is_modified():
                file_.render_output()
                render_counter.increment()

class ThreadSafeCounter:
    def __init__(self):
        self.counter = 0
        self.lock = threading.Lock()

    def increment(self):
        with self.lock:
            self.counter += 1

    def value(self):
        with self.lock:
            return self.counter

class LinkParser(HTMLParser):
    def __init__(self, file_, link_sources, link_targets):
        super().__init__()

        self.file = file_
        self.link_sources = link_sources
        self.link_targets = link_targets

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        for name in ("href", "src", "action"):
            try:
                url = attrs[name]
            except KeyError:
                continue

            split_url = urlparse.urlsplit(url)

            # Ignore off-site links
            if split_url.scheme or split_url.netloc:
                continue

            # Treat somepath/ as somepath/index.html
            if split_url.path.endswith("/"):
                split_url = split_url.replace(path=f"{split_url.path}index.html")

            normalized_url = urlparse.urljoin(self.file.url, urlparse.urlunsplit(split_url))

            self.link_sources[normalized_url].add(self.file)

        if "id" in attrs:
            normalized_url = urlparse.urljoin(self.file.url, f"#{attrs['id']}")

            if normalized_url in self.link_targets:
                self.file.site.warning("Duplicate link target: {}", normalized_url)

            self.link_targets.add(normalized_url)

class HeadingParser(HTMLParser):
    def __init__(self):
        super().__init__()

        self.headings = list()

        self.open_element_tag = None
        self.open_element_id = None
        self.open_element_text = list()

    def handle_starttag(self, tag, attrs):
        if tag not in ("h1", "h2", "h3"):
            return

        self.open_element_tag = tag

        attrs = dict(attrs)

        if "id" in attrs:
            self.open_element_id = attrs["id"]
        else:
            self.open_element_id = None

    def handle_data(self, data):
        if self.open_element_tag:
            self.open_element_text.append(data)

    def handle_endtag(self, tag):
        if tag == self.open_element_tag:
            self.headings.append((self.open_element_tag, self.open_element_id, "".join(self.open_element_text)))

            self.open_element_tag = None
            self.open_element_id = None
            self.open_element_text = list()

# XXX Try using the unthreaded notifier
class WatcherThread:
    def __init__(self, site):
        import pyinotify

        self.site = site

        watcher = pyinotify.WatchManager()

        def render_file(event):
            try:
                input_path = Path(relative_path(event.pathname, Path.cwd()))

                if input_path.is_dir():
                    return True

                if self.site.ignored_file_re.match(input_path.name):
                    return True

                try:
                    file_ = self.site.init_file(input_path)
                except FileNotFoundError:
                    return True

                self.site.debug("Input file changed: {}", input_path)

                file_.process_input()
                file_.render_output()

                if self.site.output_dir.exists():
                    self.site.output_dir.touch()
            except:
                traceback.print_exc()

        def render_site(event):
            self.site.debug("A config file changed")

            try:
                self.site.init()
                self.site.render()
            except:
                traceback.print_exc()

        watcher.add_watch(str(self.site.input_dir), pyinotify.IN_CLOSE_WRITE, render_file, rec=True, auto_add=True)

        for config_dir in self.site.config_dirs:
            watcher.add_watch(str(config_dir), pyinotify.IN_CLOSE_WRITE, render_site, rec=True, auto_add=True)

        self.notifier = pyinotify.ThreadedNotifier(watcher)
        self.notifier.name = "watcher-thread"

    def start(self):
        self.site.notice("Watching for input and config file changes")
        self.notifier.start()

    def stop(self):
        self.notifier.stop()

class Server(httpserver.ThreadingHTTPServer):
    def __init__(self, site, port):
        super().__init__(("localhost", port), ServerRequestHandler)

        self.site = site

class ServerRequestHandler(httpserver.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server, directory=None):
        super().__init__(request, client_address, server, directory=server.site.output_dir)

    def do_POST(self):
        if self.path == "/RENDER":
            self.server.site.render()
        elif self.path == "/STOP":
            self.server.shutdown()
        else:
            raise Exception()

        self.send_response(httpserver.HTTPStatus.OK)
        self.end_headers()

    def intercept_fetch(self):
        if self.path == "/" and self.server.site.prefix:
            self.send_response(httpserver.HTTPStatus.FOUND)
            self.send_header("Location", self.server.site.prefix + "/")
            self.end_headers()

            return True # redirected

        self.path = self.path.removeprefix(self.server.site.prefix)

    def do_HEAD(self):
        redirected = self.intercept_fetch()

        if not redirected:
            super().do_HEAD()

    def do_GET(self):
        redirected = self.intercept_fetch()

        if not redirected:
            super().do_GET()

class TransomCommand:
    def __init__(self, home=None):
        threading.current_thread().name = "main-thread"

        self.home = Path(home) if home is not None else None
        self.name = "transom"

        self.parser = argparse.ArgumentParser()
        self.parser.description = "Generate static websites from Markdown and Python"
        self.parser.formatter_class = argparse.RawDescriptionHelpFormatter

        self.args = None

        subparsers = self.parser.add_subparsers(title="subcommands")

        common = argparse.ArgumentParser()
        common.add_argument("--init-only", action="store_true",
                            help=argparse.SUPPRESS)
        common.add_argument("--verbose", action="store_true",
                            help="Print detailed logging to the console")
        common.add_argument("--quiet", action="store_true",
                            help="Print no logging to the console")
        common.add_argument("--threads", type=int, metavar="COUNT", default=8,
                            help=f"Use COUNT worker threads (default: 8)")
        common.add_argument("--output", metavar="OUTPUT-DIR",
                            help="The output directory (default: PROJECT-DIR/output)")
        common.add_argument("project_dir", metavar="PROJECT-DIR", nargs="?", default=".",
                            help="The project root directory (default: current directory)")

        init = subparsers.add_parser("init", parents=[common], add_help=False,
                                     help="Create files and directories for a new project")
        init.set_defaults(command_fn=self.init_command)
        init.add_argument("--profile", metavar="PROFILE", choices=("website", "webapp"), default="website",
                          help="Select starter files for different scenarios (default: website)")
        init.add_argument("--github", action="store_true",
                          help="Add extra files for use in a GitHub repo")

        render = subparsers.add_parser("render", parents=[common], add_help=False,
                                       help="Generate output files")
        render.set_defaults(command_fn=self.render_command)
        render.add_argument("--force", action="store_true",
                            help="Render all input files, including unchanged ones")

        render = subparsers.add_parser("serve", parents=[common], add_help=False,
                                       help="Generate output files and serve the site on a local port")
        render.set_defaults(command_fn=self.serve_command)
        render.add_argument("--port", type=int, metavar="PORT", default=8080,
                            help="Listen on PORT (default 8080)")
        render.add_argument("--force", action="store_true",
                            help="Render all input files, including unchanged ones")

        check_links = subparsers.add_parser("check-links", parents=[common], add_help=False,
                                            help="Check for broken links")
        check_links.set_defaults(command_fn=self.check_links_command)

        check_files = subparsers.add_parser("check-files", parents=[common], add_help=False,
                                            help="Check for missing or extra files")
        check_files.set_defaults(command_fn=self.check_files_command)

    def init(self, args=None):
        self.args = self.parser.parse_args(args)

        if "command_fn" not in self.args:
            self.parser.print_usage()
            sys.exit(1)

        if self.args.command_fn != self.init_command:
            self.site = TransomSite(self.args.project_dir, verbose=self.args.verbose, quiet=self.args.quiet,
                                    threads=self.args.threads)

            if self.args.output:
                self.site.output_dir = self.args.output

            self.site.init()

    def main(self, args=None):
        try:
            self.init(args)

            assert self.args is not None

            if self.args.init_only:
                return

            self.args.command_fn()
        except TransomError as e:
            self.fail(str(e))
        except KeyboardInterrupt: # pragma: nocover
            pass

    def notice(self, message, *args):
        if not self.args.quiet:
            self.print_message(message, *args)

    def warning(self, message, *args):
        message = "Warning: {}".format(message)
        self.print_message(message, *args)

    def fail(self, message, *args):
        message = "Error! {}".format(message)
        self.print_message(message, *args)
        sys.exit(1)

    def print_message(self, message, *args):
        message = message[0].upper() + message[1:]
        message = message.format(*args)
        message = "{}: {}".format(self.name, message)

        sys.stderr.write("{}\n".format(message))
        sys.stderr.flush()

    def init_command(self):
        if self.home is None:
            self.fail("I can't find the default input files")

        def copy(from_path, to_path):
            if to_path.exists():
                self.notice("Skipping '{}'. It already exists.", to_path)
                return

            to_path.parent.mkdir(parents=True, exist_ok=True)

            if from_path.is_dir():
                shutil.copytree(from_path, to_path)
            else:
                shutil.copy(from_path, to_path)

            self.notice("Creating '{}'", to_path)

        profile_dir = self.home / "profiles" / self.args.profile
        project_dir = Path(self.args.project_dir)

        assert profile_dir.exists(), profile_dir

        for name in (profile_dir / "config").iterdir():
            copy(name, project_dir / "config" / name.name)

        for name in (profile_dir / "input").iterdir():
            copy(name, project_dir / "input" / name.name)

        if self.args.github:
            python_dir = self.home / "python"

            copy(profile_dir / ".github" / "workflows" / "main.yaml",
                 project_dir / ".github" / "workflows" / "main.yaml")
            copy(profile_dir / ".gitignore", project_dir / ".gitignore")
            copy(profile_dir / ".plano.py", project_dir / ".plano.py")
            copy(profile_dir / "plano", project_dir / "plano")
            copy(python_dir / "transom", project_dir / "python" / "transom")
            copy(python_dir / "mistune", project_dir / "python" / "mistune")
            copy(python_dir / "plano", project_dir / "python" / "plano")

    def render_command(self):
        self.site.render(force=self.args.force)

    def serve_command(self):
        self.site.render(force=self.args.force)
        self.site.serve(port=self.args.port)

    def check_links_command(self):
        self.site.render(force=True)

        errors = self.site.check_links()

        if errors == 0:
            self.notice("PASSED")
        else:
            self.fail("FAILED")

    def check_files_command(self):
        self.site.render(force=True)

        missing_files, extra_files = self.site.check_files()

        if extra_files != 0:
            self.warning("{} extra {} in the output", extra_files, plural("file", extra_files))

        if missing_files == 0:
            self.notice("PASSED")
        else:
            self.fail("FAILED")

class HtmlRenderer(mistune.renderers.html.HTMLRenderer):
    def heading(self, text, level, **attrs):
        return f"<h{level} id=\"{html_id(text)}\">{text}</h{level}>\n"

class MarkdownLocal(threading.local):
    def __init__(self):
        plugins = "table", "strikethrough", "def_list"
        self.value = mistune.create_markdown(renderer=HtmlRenderer(escape=False), plugins=plugins)
        self.value.block.list_rules += ['table', 'nptable']

MarkdownLocal.INSTANCE = MarkdownLocal()

LIPSUM_WORDS = (
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "vestibulum", "enim", "urna",
    "ornare", "pellentesque", "felis", "eget", "maximus", "lacinia", "lorem", "nulla", "auctor", "massa", "vitae",
    "ultricies", "varius", "curabitur", "consectetur", "lacus", "sapien", "a", "lacinia", "urna", "tempus", "quis",
    "vestibulum", "vitae", "augue", "non", "augue", "lobortis", "semper", "nullam", "fringilla", "odio", "quis",
    "ligula", "consequat", "condimentum", "integer", "tempus", "sem",
)

def include(path):
    path = Path(path) if isinstance(path, str) else path
    return path.read_text()

def lipsum(count=50, end="."):
    return (" ".join((LIPSUM_WORDS[i % len(LIPSUM_WORDS)] for i in range(count))) + end).capitalize()

def plural(noun, count=0, plural=None):
    if noun in (None, ""):
        return ""

    if count == 1:
        return noun

    if plural is None:
        if noun.endswith("s"):
            plural = "{}ses".format(noun)
        else:
            plural = "{}s".format(noun)

    return plural

def html_table_csv(path, **attrs):
    with open(path, newline="") as f:
        return html_table(csv.reader(f), **attrs)

def html_table_cell(column_index, value):
    return html_elem("td", str(value if value is not None else ""))

def html_table(data, headings=None, cell_fn=html_table_cell, **attrs):
    # XXX Use thead
    return html_elem("table", html_elem("tbody", html_table_rows(data, headings, cell_fn)), **attrs)

def html_table_rows(data, headings, cell_fn):
    if headings:
        yield html_elem("tr", (html_elem("th", x) for x in headings))

    for row in data:
        yield html_elem("tr", (cell_fn(i, x) for i, x in enumerate(row)))

def html_elem(tag, content, **attrs):
    if isinstance(content, Iterable) and not isinstance(content, str):
        content = "".join(content)

    return f"<{tag}{''.join(html_attrs(attrs))}>{content or ''}</{tag}>"

def html_attrs(attrs):
    for name, value in attrs.items():
        name = "class" if name in ("class_", "_class") else name
        value = name if value is True else value

        if value is not False:
            yield f" {name}=\"{html_escape(value, quote=True)}\""

HTML_ID_RESTRICT_RE = re.compile(r"[^a-z0-9\s-]")
HTML_ID_HYPHENATE_RE = re.compile(r"[-\s]+")

def html_id(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = HTML_ID_RESTRICT_RE.sub("", text.lower())
    text = HTML_ID_HYPHENATE_RE.sub("-", text).strip("-")

    return text

if __name__ == "__main__": # pragma: nocover
    command = TransomCommand()
    command.main()
