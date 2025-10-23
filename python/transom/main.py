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
import fnmatch
import functools
import http.server as httpserver
import itertools
import mistune
import re
import shutil
import sys
import threading
import traceback
import types
import unicodedata

from collections import defaultdict
from html import escape as html_escape
from html.parser import HTMLParser
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

    def __init__(self, site_dir, verbose=False, quiet=False, threads=8):
        self.site_dir = Path(site_dir).resolve()
        self.config_dir = self.site_dir / "config"
        self.input_dir = self.site_dir / "input"
        self.output_dir = self.site_dir / "output"

        self.verbose = verbose
        self.quiet = quiet

        self.ignored_file_patterns = [".git", ".#*", "#*"]
        self.ignored_link_patterns = []

        self.prefix = ""
        self.config_dirs = [self.config_dir]
        self.config_modified = False

        self.input_files = dict() # InputFile.input_path => InputFile
        self.index_files = dict() # InputFile.input_path.parent => InputFile

        self.globals = {
            "site": SiteInterface(self),
            "include": include,
            "lipsum": lipsum,
            "plural": plural,
            "html_escape": html_escape,
            "html_table": html_table,
            "html_table_csv": html_table_csv,
            "load_template": functools.partial(TransomSite.load_template, self),
            "TransomError": TransomError,
        }

        threading.current_thread().name = "main-thread"

        self.worker_threads = list()
        self.worker_errors = Queue()

        for i in range(threads):
            self.worker_threads.append(WorkerThread(self, f"worker-thread-{i + 1}", self.worker_errors))

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.site_dir}')"

    def start(self):
        self.debug("Starting {} worker {}", len(self.worker_threads), plural("thread", len(self.worker_threads)))

        for thread in self.worker_threads:
            thread.start()

    def stop(self):
        self.debug("Stopping worker threads")

        for thread in self.worker_threads:
            thread.commands.put((None, None))
            thread.join()

    def load_config_files(self):
        self.debug("Loading config files in '{}'", self.config_dir)

        page_template_path = self.config_dir / "page.html"
        body_template_path = self.config_dir / "body.html"
        site_code_path = self.config_dir / "site.py"

        self.page_template = Template(TransomSite.FALLBACK_PAGE_TEMPLATE, "[fallback]")
        self.body_template = Template(TransomSite.FALLBACK_BODY_TEMPLATE, "[fallback]")

        if page_template_path.exists():
            self.debug("Loading page template from '{}'", page_template_path)
            self.page_template = self.load_template(page_template_path)

        if body_template_path.exists():
            self.debug("Loading body template from '{}'", body_template_path)
            self.body_template = self.load_template(body_template_path)

        if site_code_path.exists():
            self.debug("Executing site code in '{}'", self.config_dir / "site.py")

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

    def load_template(self, path):
        path = Path(path) if isinstance(path, str) else path
        return Template(path.read_text(), path)

    def load_input_files(self):
        self.debug("Loading input files in '{}'", self.input_dir)

        if not self.input_dir.is_dir():
            raise TransomError(f"Input directory not found: {self.input_dir}")

        self.input_files.clear() # XXX support efficient reloading?

        def count_files():
            count = 0
            for root, _, files in self.input_dir.walk():
                count += len(files)
            return count

        def get_files():
            for root, _, files in self.input_dir.walk():
                for name in files:
                    yield root / name

        batch_size = (count_files() + len(self.worker_threads) - 1) // len(self.worker_threads)
        batch_size = 1 if batch_size == 0 else batch_size # XXX
        batches = itertools.batched(get_files(), batch_size)
        counter = ThreadSafeCounter()

        for thread, input_files in zip(self.worker_threads, batches):
            thread.commands.put((thread.load_input_files, (input_files, counter)))

        for thread in self.worker_threads:
            thread.commands.join()

        return counter.value()

    def load_input_file(self, input_path):
        try:
            return self.input_files[input_path]
        except KeyError:
            pass

        self.debug("Loading '{}'", input_path)

        match input_path.suffix:
            case ".md":
                input_file = MarkdownPage(self, input_path)
            case ".css" | ".csv" | ".html" | ".js" | ".json" | ".svg" | ".txt":
                input_file = TemplateFile(self, input_path)
            case _:
                input_file = StaticFile(self, input_path)

        self.input_files[input_path] = input_file

        if input_file.output_path.name == "index.html":
            self.index_files[input_file.input_path.parent] = input_file

        return input_file

    def process_input_files(self):
        self.debug("Processing input files in '{}'", self.input_dir)

        counter = ThreadSafeCounter()

        for thread in self.worker_threads:
            thread.commands.put((thread.process_input_files, (counter,)))

        for thread in self.worker_threads:
            thread.commands.join()

        return counter.value()

    def render_output_files(self, force=False):
        self.debug("Rendering output files to '{}'", self.output_dir)

        counter = ThreadSafeCounter()

        for thread in self.worker_threads:
            thread.commands.put((thread.render_output_files, (force, counter)))

        for thread in self.worker_threads:
            thread.commands.join()

        return counter.value()

    def render(self, force=False):
        self.notice("Rendering files from '{}' to '{}'", self.input_dir, self.output_dir)

        self.load_config_files()

        # XXX?
        if self.output_dir.exists():
            self.debug("Checking for config file changes")
            self.config_modified = self.compute_config_modified()

        loaded_count = self.load_input_files()

        self.notice("Loaded {:,} input {}", loaded_count, plural("file", loaded_count))

        processed_count = self.process_input_files()

        self.notice("Processed {:,} input {}", processed_count, plural("file", processed_count))

        rendered_count = self.render_output_files(force=force)

        if not self.worker_errors.empty():
            raise self.worker_errors.get()

        if self.output_dir.is_dir():
            self.output_dir.touch()

        unchanged_count = loaded_count - rendered_count
        unchanged_note = ""

        if unchanged_count > 0:
            unchanged_note = " ({:,} unchanged)".format(unchanged_count)

        self.notice("Rendered {:,} output {}{}", rendered_count, plural("file", rendered_count), unchanged_note)

    # XXX Make this faster
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

    # XXX Reload config if modified?
    def render_one_file(self, input_path, force=False):
        assert input_path.is_file(), input_path

        parent_files = list()

        for parent_path in self.get_parent_input_paths(input_path):
            parent_files.append(self.load_input_file(parent_path))

        for parent_file in parent_files:
            parent_file.process_input()

        input_file = self.load_input_file(input_path)

        input_file.process_input()
        input_file.render_output()

    def get_parent_input_paths(self, input_path):
        parent_dir = input_path.parent

        if input_path.stem == "index":
            parent_dir = parent_dir.parent

        while parent_dir != self.input_dir.parent:
            for index_path in (parent_dir / "index.md", parent_dir / "index.html"):
                if index_path.exists():
                    yield index_path

            parent_dir = parent_dir.parent

    # Input files are loaded and rendered on demand
    def serve(self, port=8080):
        self.load_config_files()

        self.notice("Serving the site at http://localhost:{}", port)

        try:
            with Server(self, port) as server:
                server.serve_forever()
        except OSError as e:
            # OSError: [Errno 98] Address already in use
            if e.errno == 98:
                raise TransomError(f"Port {port} is already in use")
            else: # pragma: nocover
                raise

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

    def error(self, message, *args):
        print("Error!", message.format(*args))

class InputFile:
    __slots__ = "site", "input_path", "input_mtime", "output_path", "output_mtime", "url", "title", "parent"

    def __init__(self, site, input_path):
        self.site = site
        self.input_path = input_path
        self.input_mtime = None

        # Path.relative_to is surprisingly slow in Python 3.12, so we
        # avoid it here
        output_path = str(self.input_path)[len(str(self.site.input_dir)) + 1:]

        if output_path.endswith(".md"):
            output_path = output_path[:-3] + ".html"

        self.output_path = self.site.output_dir / output_path
        self.output_mtime = None

        self.url = f"{self.site.prefix}/{output_path}"
        self.title = self.output_path.name
        self.parent = None

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.input_path}')"

    def ancestors(self):
        parent = self.parent

        while parent is not None:
            yield parent
            parent = parent.parent

    def is_modified(self):
        if self.output_mtime is None:
            try:
                self.output_mtime = self.output_path.stat().st_mtime
            except FileNotFoundError:
                return True

        return self.input_mtime > self.output_mtime

    def process_input(self):
        self.debug("Processing input")
        self.input_mtime = self.input_path.stat().st_mtime

    def render_output(self):
        self.debug("Rendering output")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def debug(self, message, *args):
        self.site.debug(f"{self.input_path}: {message}", *args)

class StaticFile(InputFile):
    __slots__ = ()

    def render_output(self):
        super().render_output()
        shutil.copy(self.input_path, self.output_path)

class GeneratedFile(InputFile):
    __slots__ = ()
    HEADER_RE = re.compile(r"(?s)^---\s*\n(.*?)\n---\s*\n")

    def process_input(self):
        super().process_input()

        if self.output_path.suffix == ".html":
            parent_dir = self.input_path.parent

            if self.output_path.name == "index.html":
                parent_dir = parent_dir.parent

            while parent_dir != self.site.input_dir.parent:
                try:
                    self.parent = self.site.index_files[parent_dir]
                except KeyError:
                    parent_dir = parent_dir.parent
                else:
                    break

        # if self.output_path.suffix == ".html":
        #     parent_dir = self.input_path.parent

        #     if self.output_path.name == "index.html":
        #         parent_dir = parent_dir.parent

        #     while parent_dir != self.site.input_dir.parent:
        #         self.parent = self.site.input_files.get(parent_dir / "index.md")

        #         if self.parent is None:
        #             self.parent = self.site.input_files.get(parent_dir / "index.html")

        #         if self.parent is not None:
        #             break

        #         parent_dir = parent_dir.parent

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

class MarkdownPage(GeneratedFile):
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

        m = MarkdownPage.MARKDOWN_TITLE_RE.search(text)
        self.title = m.group(1) if m else ""
        m = MarkdownPage.HTML_TITLE_RE.search(text)
        self.title = m.group(1) if m else self.title

        self.locals = {
            "page": PageInterface(self),
            "render": functools.partial(MarkdownPage.render_file, self),
            "path_nav": functools.partial(MarkdownPage.path_nav, self),
            "toc_nav": functools.partial(MarkdownPage.toc_nav, self),
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
    @functools.cache
    def content(self):
        pieces = self.content_template.render(self)

        return MarkdownLocal.INSTANCE.value("".join(pieces))

    def render_file(self, path):
        path = Path(path) if isinstance(path, str) else path
        pieces = self.site.load_template(path).render(self)

        return MarkdownLocal.INSTANCE.value("".join(pieces))

    def path_nav(self, start=0, end=None, min=1):
        files = list(self.ancestors())
        files.reverse()
        files.append(self)

        links = tuple(f"<a href=\"{x.url}\">{x.title}</a>" for x in files[start:end])

        if len(links) < min:
            return ""

        return f"<nav class=\"page-path\">{''.join(links)}</nav>"

    def toc_nav(self):
        parser = HeadingParser()
        parser.feed("".join(self.content))

        links = tuple(f"<a href=\"#{x[1]}\">{x[2]}</a>" for x in parser.headings
                      if x[0] in ("h1", "h2") and x[1] is not None)

        return f"<nav class=\"page-toc\">{''.join(links)}</nav>"

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
                    raise TransomError(f"{self.path}: '{token}': {e}")
            else:
                piece = token

            self.pieces.append(piece)

    def render(self, input_file):
        for piece in self.pieces:
            if type(piece) is tuple:
                code, token = piece

                try:
                    result = eval(code, input_file.site.globals, input_file.locals)
                except TransomError:
                    raise
                except Exception as e:
                    raise TransomError(f"{self.path}: '{token}': {e}")

                if type(result) is types.GeneratorType:
                    yield from result
                else:
                    yield str(result)
            else:
                yield piece

    def write(self, input_file):
        text = "".join(self.render(input_file))
        input_file.output_path.write_text(text)

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
        super().__init__(obj, ("prefix", "config_dirs", "ignored_file_patterns", "ignored_link_patterns",
                               "page_template", "body_template"))

class PageInterface(RestrictedInterface):
    __slots__ = ()

    def __init__(self, obj):
        super().__init__(obj, ("url", "title", "parent", "body", "content", "extra_headers", "page_template",
                               "body_template"))

class WorkerThread(threading.Thread):
    def __init__(self, site, name, errors):
        super().__init__(name=name)

        self.site = site
        self.errors = errors
        self.commands = Queue()
        self.input_files = list()

    def run(self):
        while True:
            fn, args = self.commands.get()

            if fn is None:
                break

            try:
                fn(*args)
            except TransomError as e:
                self.site.error(str(e))
                self.errors.put(e)
            except Exception as e: # pragma: nocover
                traceback.print_exc()
                self.errors.put(e)
            finally:
                self.commands.task_done()

    def load_input_files(self, input_paths, counter):
        self.input_files.clear()

        for input_path in (x for x in input_paths if not self.site.ignored_file_re.match(x.name)):
            self.input_files.append(self.site.load_input_file(input_path))
            counter.increment()

    def process_input_files(self, counter):
        for input_file in self.input_files:
            input_file.process_input()
            counter.increment()

    def render_output_files(self, force, counter):
        for input_file in self.input_files:
            if force or input_file.is_modified():
                input_file.render_output()
                counter.increment()

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

    def handle_data(self, data):
        if self.open_element_tag:
            self.open_element_text.append(data)

    def handle_endtag(self, tag):
        if tag == self.open_element_tag:
            self.headings.append((self.open_element_tag, self.open_element_id, "".join(self.open_element_text)))

            self.open_element_tag = None
            self.open_element_id = None
            self.open_element_text = list()

class Server(httpserver.ThreadingHTTPServer):
    def __init__(self, site, port):
        super().__init__(("localhost", port), ServerRequestHandler)

        self.site = site

class ServerRequestHandler(httpserver.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server, directory=None):
        super().__init__(request, client_address, server, directory=server.site.output_dir)

    def do_POST(self):
        assert self.path == "/STOP", self.path

        self.server.shutdown()

        self.send_response(httpserver.HTTPStatus.OK)
        self.end_headers()

    # This handles GET and HEAD requests
    def send_head(self):
        if not self.path.startswith(self.server.site.prefix):
            self.send_response(httpserver.HTTPStatus.TEMPORARY_REDIRECT)
            self.send_header("Location", self.server.site.prefix + self.path)
            self.end_headers()

            return None

        self.path = self.path + "index.html" if self.path.endswith("/") else self.path
        self.path = self.path.removeprefix(self.server.site.prefix).removeprefix("/")

        input_path = self.server.site.input_dir / self.path

        if input_path.is_file():
            self.server.site.render_one_file(input_path)
        elif input_path.with_suffix(".md").exists():
            self.server.site.render_one_file(input_path.with_suffix(".md"))

        return super().send_head()

class TransomCommand:
    def __init__(self, home=None):
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
                            help="The output directory (default: SITE-DIR/output)")
        common.add_argument("site_dir", metavar="SITE-DIR", nargs="?", default=".",
                            help="The site root directory (default: current directory)")

        init = subparsers.add_parser("init", parents=[common], add_help=False,
                                     help="Create files and directories for a new project")
        init.set_defaults(command_fn=self.command_init)
        init.add_argument("--profile", metavar="PROFILE", choices=("website", "webapp"), default="website",
                          help="Select starter files for different scenarios (default: website)")
        init.add_argument("--github", action="store_true",
                          help="Add extra files for use in a GitHub repo")

        render = subparsers.add_parser("render", parents=[common], add_help=False,
                                       help="Generate output files")
        render.set_defaults(command_fn=self.command_render)
        render.add_argument("-f", "--force", action="store_true",
                            help="Render all input files, including unchanged ones")

        render = subparsers.add_parser("serve", parents=[common], add_help=False,
                                       help="Generate output files and serve the site on a local port")
        render.set_defaults(command_fn=self.command_serve)
        render.add_argument("-p", "--port", type=int, metavar="PORT", default=8080,
                            help="Listen on PORT (default 8080)")

        check = subparsers.add_parser("check", parents=[common], add_help=False,
                                            help="Check for broken links and missing output files")
        check.set_defaults(command_fn=self.command_check)

    def init(self, args=None):
        self.args = self.parser.parse_args(args)

        if "command_fn" not in self.args:
            self.parser.print_usage()
            sys.exit(1)

        if self.args.command_fn != self.command_init:
            self.site = TransomSite(self.args.site_dir, verbose=self.args.verbose, quiet=self.args.quiet,
                                    threads=self.args.threads)

            if self.args.output:
                self.site.output_dir = Path(self.args.output)

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

    def command_init(self):
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
        site_dir = Path(self.args.site_dir)

        assert profile_dir.exists(), profile_dir

        for name in (profile_dir / "config").iterdir():
            copy(name, site_dir / "config" / name.name)

        for name in (profile_dir / "input").iterdir():
            copy(name, site_dir / "input" / name.name)

        if self.args.github:
            copy(profile_dir / ".github", site_dir / ".github")
            copy(profile_dir / ".gitignore", site_dir / ".gitignore")
            copy(profile_dir / ".plano.py", site_dir / ".plano.py")
            copy(profile_dir / "plano", site_dir / "plano")
            copy(self.home / "python/transom", site_dir / "python/transom")
            copy(self.home / "python/mistune", site_dir / "python/mistune")
            copy(self.home / "python/plano", site_dir / "python/plano")

    def command_render(self):
        self.site.start()

        try:
            self.site.render(force=self.args.force)
        finally:
            self.site.stop()

    def command_serve(self):
        self.site.start()

        try:
            self.site.serve(port=self.args.port)
        finally:
            self.site.stop()

    def command_check(self):
        # XXX Check links

        self.notice("Checking output files in '{}'", self.site.output_dir)

        if not self.site.output_dir.is_dir():
            self.fail("Output directory not found: {} (render the site before checking files)", self.site.output_dir)


        self.site.start()

        try:
            self.site.load_config_files()
            self.site.load_input_files()
        finally:
            self.site.stop()

        expected_paths = set(x.output_path for x in self.site.input_files.values())
        found_paths = set()

        for root, dirs, files in self.site.output_dir.walk():
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

        missing_files, extra_files = len(missing_paths), len(extra_paths)

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
    import csv

    with open(path, newline="") as f:
        return html_table(csv.reader(f), **attrs)

def html_table_cell(column_index, value):
    return html_elem("td", str(value if value is not None else ""))

def html_table(data, headings=None, cell_fn=html_table_cell, **attrs):
    if headings:
        thead = html_elem("thead", html_elem("tr", (html_elem("th", x) for x in headings)))
    else:
        thead = ""

    tbody = html_elem("tbody", html_table_rows(data, headings, cell_fn))

    return html_elem("table", (thead, tbody), **attrs)

def html_table_rows(data, headings, cell_fn):
    for row in data:
        yield html_elem("tr", (cell_fn(i, x) for i, x in enumerate(row)))

def html_elem(tag, content, **attrs):
    if not isinstance(content, str):
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
