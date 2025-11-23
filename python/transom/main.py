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
import html
import itertools
import math
import mistune
import os
import re
import shutil
import sys
import threading
import traceback
import types
import unicodedata

from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import partial
from html.parser import HTMLParser
from pathlib import Path
from queue import Queue

__all__ = "TransomError", "TransomSite", "TransomCommand"

class TransomError(Exception):
    """
    The standard Transom error.
    """
    def __init__(self, message, contexts=None):
        self.message = message
        self.contexts = contexts

    def __str__(self):
        if self.contexts:
            return "".join(f"{x}: " for x in self.contexts) + str(self.message)
        else:
            return str(self.message)

class ErrorHandling:
    def __init__(self, contexts):
        self.contexts = contexts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if isinstance(exc_value, TransomError):
            if not exc_value.contexts:
                exc_value.contexts = self.contexts

            return False

        if exc_type is not None:
            raise TransomError(exc_value, self.contexts)

class TransomSite:
    def __init__(self, root_dir, verbose=False, quiet=False, threads=8):
        self.root_dir = Path(root_dir).resolve()
        self.config_dir = self.root_dir / "config"
        self.input_dir = self.root_dir / "input"
        self.output_dir = self.root_dir / "output"

        self.verbose = verbose
        self.quiet = quiet

        self.config = SiteConfig()

        self.variables = {
            "site": self.config,
            "include": include,
            "load_template": load_template,
            "convert_markdown": convert_markdown,
            "strip": strip,
            "plural": plural,
            "lipsum": lipsum,
            "html_escape": html_escape,
            "html_list": html_list,
            "html_list_csv": html_list_csv,
            "html_table": html_table,
            "html_table_csv": html_table_csv,
            "TransomError": TransomError,
        }

        threading.current_thread().name = "main-thread"

        self.worker_threads = []
        self.worker_errors = Queue()

        for i in range(threads):
            self.worker_threads.append(WorkerThread(self, f"worker-thread-{i + 1}", self.worker_errors))

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(str(self.root_dir))})"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

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

        site_code_path = self.config_dir / "site.py"

        if site_code_path.exists():
            self.debug("Executing site code in '{}'", self.config_dir / "site.py")

            with ErrorHandling([site_code_path]):
                exec(site_code_path.read_text(), self.variables)

        self._ignored_files_re = re.compile \
            ("|".join([fnmatch.translate(x) for x in self.config.ignored_files] + ["(?!)"]))

    def load_input_files(self):
        self.debug("Loading input files in '{}'", self.input_dir)

        def find_input_files(start_path, input_files, parent_file):
            def add_input_file(input_path, parent_file):
                input_file = self.load_input_file(Path(entry.path), parent_file)

                input_files.append(input_file)

                if parent_file is not None:
                    parent_file.children.append(input_file)

                return input_file

            with os.scandir(start_path) as entries:
                entries = tuple(x for x in entries if not self._ignored_files_re.match(x.name))

                for entry in entries:
                    if entry.name in ("index.md", "index.html"):
                        input_file = add_input_file(Path(entry.path), parent_file)
                        parent_file = input_file
                        break

                for entry in entries:
                    if entry.name in ("index.md", "index.html"):
                        continue

                    if entry.is_file():
                        input_file = add_input_file(Path(entry.path), parent_file)
                    elif entry.is_dir():
                        find_input_files(entry.path, input_files, parent_file)

        input_files = []

        try:
            find_input_files(self.input_dir, input_files, None)
        except FileNotFoundError:
            self.notice("Input directory not found: {}", self.input_dir)

        return input_files

    def load_input_file(self, input_path, parent):
        self.debug("Loading '{}'", input_path)

        match input_path.suffix:
            case ".md":
                input_file = MarkdownPage(self, input_path, parent)
            case ".css" | ".csv" | ".html" | ".js" | ".json" | ".svg" | ".txt":
                input_file = TemplatePage(self, input_path, parent)
            case _:
                input_file = StaticFile(self, input_path, parent)

        return input_file

    def find_config_modified(self, last_render_time):
        def find_modified_file(start_path, last_render_time):
            with os.scandir(start_path) as entries:
                for entry in (x for x in entries if not self._ignored_files_re.match(x.name)):
                    if entry.is_file():
                        if entry.stat().st_mtime >= last_render_time:
                            return True
                    elif entry.is_dir():
                        return find_modified_file(entry.path, last_render_time)

        try:
            if find_modified_file(self.config_dir, last_render_time):
                return True
        except FileNotFoundError:
            self.notice("Config directory not found: {}", self.config_dir)

    def render(self, force=False):
        self.notice("Rendering files from '{}' to '{}'", self.input_dir, self.output_dir)

        self.load_config_files()

        input_files = self.load_input_files()
        last_render_time = 0

        if not input_files:
            return input_files

        if not force and self.output_dir.exists():
            last_render_time = self.output_dir.stat().st_mtime

            if self.find_config_modified(last_render_time):
                last_render_time = 0

        self.debug("Processing {:,} input {}", len(input_files), plural("file", len(input_files)))

        input_file_batches = itertools.batched(input_files, math.ceil(len(input_files) / len(self.worker_threads)))
        modified_file_batches = tuple([] for x in self.worker_threads)

        for thread, files, modified_files in zip(self.worker_threads, input_file_batches, modified_file_batches):
            thread.commands.put((thread.process_input_files, (files, last_render_time, modified_files)))

        for thread in self.worker_threads:
            thread.commands.join()

        if self.config.title is None:
            self.config.title = input_files[0].input_path.name # XXX should be title from page config

        modified_count = sum(len(x) for x in modified_file_batches)

        self.debug("Rendering {:,} output {} to '{}'", modified_count, plural("file", modified_count), self.output_dir)

        for thread, files in zip(self.worker_threads, modified_file_batches):
            thread.commands.put((thread.render_output_files, (files,)))

        for thread in self.worker_threads:
            thread.commands.join()

        if not self.worker_errors.empty():
            raise TransomError("Rendering failed")

        if self.output_dir.exists():
            self.output_dir.touch()

        unmodified_count = len(input_files) - modified_count
        unmodified_note = ""

        if unmodified_count > 0:
            unmodified_note = " ({:,} unchanged)".format(unmodified_count)

        self.notice("Rendered {:,} output {}{}", modified_count, plural("file", modified_count), unmodified_note)

        return input_files

    def serve(self, port=8080):
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

    def log(self, message, *args):
        if self.verbose:
            message = f"{colorize(threading.current_thread().name, '90')} {message}"

        print(message.format(*args), file=sys.stderr, flush=True)

    def debug(self, message, *args):
        if self.verbose:
            self.log(colorize(f"debug: {message}", "37"), *args)

    def notice(self, message, *args):
        if not self.quiet:
            message = f"{colorize('notice:', '36')} {message}" if self.verbose else message
            self.log(message, *args)

    def error(self, message, *args):
        if self.verbose:
            traceback.print_exc()

        self.log(f"{colorize('error:', '31;1')} {message}", *args)

@dataclass
class SiteConfig:
    # The site title.  XXX Used in head/title element (so, in bookmarks).
    #
    # A string prefix used in generated links. It is
    # inserted before the file path. This is important when the
    # published site lives under a directory prefix, as is the case for
    # GitHub Pages. The default is the empty string, meaning no prefix.
    #
    # A list of shell globs for excluding input and config files from
    # processing. The default is `[".git", ".#*","#*"]`.
    #
    # The default top-level template object for Markdown pages. The page
    # template wraps `{{page.body}}`. The default is loaded from
    # `config/page.html`.
    #
    # The default template object for the body element of Markdown
    # pages. The body element wraps `{{page.content}}`. The default
    # is loaded from `config/body.html`.

    title: str = None
    prefix: str = ""
    ignored_files: list[str] = field(default_factory=lambda: [".git", ".#*", "#*"])
    page_template: str = "config/page.html"
    body_template: str = "config/body.html"

class InputFile:
    __slots__ = "site", "input_path", "output_path", "url", "parent", "children"

    def __init__(self, site, input_path, parent):
        self.site = site
        self.input_path = input_path

        # Path.relative_to is surprisingly slow in Python 3.12, so we
        # avoid it here
        output_path = str(self.input_path)[len(str(self.site.input_dir)) + 1:]

        if output_path.endswith(".md"):
            output_path = output_path[:-3] + ".html"

        self.output_path = self.site.output_dir / output_path

        self.url = f"{self.site.config.prefix}/{output_path}"
        self.parent = parent
        self.children = []

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(str(self.input_path))})"

    @property
    def parents(self):
        """
        The ancestor index files of this file, nearest ancestor first.
        """
        parent = self.parent

        while parent is not None:
            yield parent
            parent = parent.parent

    def process_input(self, last_render_time=0):
        self.debug("Processing input")
        return self.input_path.stat().st_mtime >= last_render_time

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

class TemplatePage(InputFile):
    __slots__ = "config", "variables", "template"
    _HEADER_RE = re.compile(r"(?s)^---\s*\n(.*?)\n---\s*\n")
    _MARKDOWN_TITLE_RE = re.compile(r"(?m)^(?:#|##)\s+(.*?)\n")
    _HTML_TITLE_RE = re.compile(r"(?si)<(?:h1|h2)\b[^>]*>(.*?)</(?:h1|h2)>")

    def __init__(self, site, input_path, parent):
        super().__init__(site, input_path, parent)

        self.config = PageConfig(self)
        self.variables = self.site.variables | {
            "page": PageConfig(self),
            "path_nav": partial(self.path_nav),
            "render_template": partial(self.render_template),
        }

        try:
            self.variables["toc_nav"] = partial(self.toc_nav)
        except AttributeError:
            pass

    def process_input(self, last_render_time=0):
        modified = super().process_input(last_render_time)

        if modified:
            code, text = self.process_input_text()

            self.template = Template(text, self.input_path)

            if self.input_path.suffix in (".md", ".html"):
                if match_ := MarkdownPage._HTML_TITLE_RE.search(text):
                    self.config.title = match_.group(1)
                elif match_ := MarkdownPage._MARKDOWN_TITLE_RE.search(text):
                    self.config.title = match_.group(1)

            if code:
                self.debug("Executing page code")

                with ErrorHandling([self.input_path, "header"]):
                    exec(code, self.variables)

        return modified

    def process_input_text(self):
        code, text = None, self.input_path.read_text()

        if match_ := TemplatePage._HEADER_RE.match(text):
            code, text = match_.group(1), text[match_.end():]

        return code, text

    def render_output(self):
        super().render_output()
        self.template.write(self)

    def path_nav(self, start=0, end=None, min=1) -> str:
        """
        Generate context navigation links.  It produces a `<nav>`
        element with links to the parents of this page.  `start` and
        `end` trim off parts you don't need.  If the resulting number
        of links is less than `min`, it returns empty string.
        """
        files = [self] + list(self.parents)
        files.reverse()
        links = tuple(f"<a href=\"{x.url}\">{x.config.title if hasattr(x, "config") else x.input_path.name}</a>" for x in files[start:end]) # XXX

        if len(links) < min:
            return ""

        return f"<nav class=\"transom-page-path\">{''.join(links)}</nav>"

    def render_template(self, path) -> Iterator[str]:
        """
        Load the template at `path` and render it using the Python
        environment of this page.
        """
        return load_template(path).render(self)

class MarkdownPage(TemplatePage):
    __slots__ = "content",

    def process_input_text(self):
        code, text = super().process_input_text()

        self.content = MarkdownLocal.INSTANCE.value(text)

        page_path = Path(self.config.page_template)
        body_path = Path(self.config.body_template)

        page = page_path.read_text() if page_path.exists() else "@body@"
        body = body_path.read_text() if body_path.exists() else "@content@"

        text = page.replace("@body@", body.replace("@content@", self.content))

        return code, text

    def toc_nav(self) -> str:
        """
        Generate a table of contents.  It produces a `<nav>`
        element with links to the headings in the content of this
        page.
        """
        parser = HeadingParser()
        parser.feed(self.content)

        links = tuple(f"<a href=\"#{x[1]}\">{x[2]}</a>" for x in parser.headings
                      if x[0] in ("h1", "h2") and x[1] is not None)

        return f"<nav class=\"transom-page-toc\">{''.join(links)}</nav>"

@dataclass
class PageConfig:
    # The title of this file.  Default title values are extracted from Markdown or HTML content.
    #
    # The top-level template object for the page.  The page
    # template wraps `{{page.body}}`.  The default is the value of
    # `site.page_template`.
    # XXX null means
    #
    # The template object for the body element of the page.
    # The body element wraps `{{page.content}}`.  The default is
    # the value of `site.body_template`.
    # XXX null means

    _page: MarkdownPage
    title: str = None
    page_template: str = "config/page.html"
    body_template: str = "config/body.html"

class Template:
    __slots__ = "pieces", "context"
    _VARIABLE_RE = re.compile(r"(\{\{\{.+?\}\}\}|\{\{.+?\}\})")

    def __init__(self, text, context=None):
        self.pieces = []
        self.context = context

        self._parse(text)

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(str(self.context))})"

    def _parse(self, text):
        for token in Template._VARIABLE_RE.split(text):
            if token.startswith("{{{") and token.endswith("}}}"):
                piece = token[1:-1]
            elif token.startswith("{{") and token.endswith("}}"):
                code = token[2:-2]

                try:
                    piece = compile(code, "<string>", "eval"), repr(code)
                except Exception as e:
                    raise TransomError(e, [self.context, repr(code)])
            else:
                piece = token

            self.pieces.append(piece)

    def render(self, input_file):
        for piece in self.pieces:
            if type(piece) is tuple:
                code, token = piece

                with ErrorHandling([input_file.input_path, token]):
                    result = eval(code, input_file.variables)

                if type(result) is types.GeneratorType:
                    yield from result
                else:
                    yield str(result)
            else:
                yield piece

    def write(self, input_file):
        text = "".join(self.render(input_file))
        input_file.output_path.write_text(text)

def load_template(path) -> Template:
    """
    Load the template at 'path'.
    """
    path = Path(path) if isinstance(path, str) else path
    return Template(path.read_text(), path)

class WorkerThread(threading.Thread):
    def __init__(self, site, name, errors):
        super().__init__(name=name)

        self.site = site
        self.errors = errors
        self.commands = Queue()

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

    def process_input_files(self, input_files, last_render_time, modified_files):
        for input_file in input_files:
            modified = input_file.process_input(last_render_time)

            if modified:
                modified_files.append(input_file)

    def render_output_files(self, modified_files):
        for input_file in modified_files:
            input_file.render_output()

class HeadingParser(HTMLParser):
    def __init__(self):
        super().__init__()

        self.headings = []
        self.open_element_tag = None
        self.open_element_id = None
        self.open_element_text = []

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
            self.open_element_text = []

class Server(httpserver.ThreadingHTTPServer):
    def __init__(self, site, port):
        super().__init__(("localhost", port), ServerRequestHandler)

        self.site = site
        self.lock = threading.Lock()

        self.render()

    def render(self):
        self.input_files = {x.input_path: x for x in self.site.render()}

class ServerRequestHandler(httpserver.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server, directory=None):
        super().__init__(request, client_address, server, directory=server.site.output_dir)

    def do_POST(self):
        assert self.path == "/STOP", self.path

        self.server.shutdown()

        self.send_response(httpserver.HTTPStatus.OK)
        self.end_headers()

    # This intercepts all GET and HEAD requests
    def send_head(self):
        prefix = self.server.site.config.prefix

        if not self.path.startswith(prefix):
            self.send_response(httpserver.HTTPStatus.TEMPORARY_REDIRECT)
            self.send_header("Location", prefix + self.path)
            self.end_headers()
            return

        self.path = self.path + "index.html" if self.path.endswith("/") else self.path
        self.path = self.path.removeprefix(prefix).removeprefix("/")

        input_path = self.server.site.input_dir / self.path

        try:
            if input_path.is_file():
                self.render(input_path)
            elif input_path.with_suffix(".md").exists():
                self.render(input_path.with_suffix(".md"))
        except TransomError as e:
            self.send_error(httpserver.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
            return

        return super().send_head()

    def render(self, input_path):
        with self.server.lock:
            try:
                input_file = self.server.input_files[input_path]
            except KeyError:
                self.server.render()
                return

            for parent in input_file.parents:
                parent.process_input()

            input_file.process_input()
            input_file.render_output()

class TransomCommand:
    def __init__(self, home=None):
        self.home = Path(home) if home is not None else None
        self.name = "transom"

        self.parser = argparse.ArgumentParser()
        self.parser.description = "Generate static websites from Markdown and Python"
        self.parser.formatter_class = argparse.RawDescriptionHelpFormatter

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

        serve = subparsers.add_parser("serve", parents=[common], add_help=False,
                                       help="Generate output files and serve the site on a local port")
        serve.set_defaults(command_fn=self.command_serve)
        serve.add_argument("-p", "--port", type=int, metavar="PORT", default=8080,
                           help="Listen on PORT (default 8080)")

    def init(self, args=None):
        self.args = self.parser.parse_args(args)

        if "command_fn" not in self.args:
            self.parser.print_usage()
            sys.exit(1)

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
        self.site.notice(message, *args)

    def fail(self, message, *args):
        self.site.error(message, *args)
        sys.exit(1)

    def command_init(self):
        if self.home is None:
            self.fail("I can't find the default input files")

        def copy(from_path, to_path):
            if to_path.exists():
                self.notice("Skipping '{}'. It already exists.", to_path)
                return

            to_path.parent.mkdir(parents=True, exist_ok=True)

            if from_path.is_dir():
                shutil.copytree(from_path, to_path, copy_function=shutil.copy)
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
        with self.site:
            self.site.render(force=self.args.force)

    def command_serve(self):
        with self.site:
            self.site.serve(port=self.args.port)

class HtmlRenderer(mistune.renderers.html.HTMLRenderer):
    _HTML_ID_RESTRICT_RE = re.compile(r"[^a-z0-9\s-]")
    _HTML_ID_HYPHENATE_RE = re.compile(r"[-\s]+")

    @staticmethod
    def html_id(text):
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        text = HtmlRenderer._HTML_ID_RESTRICT_RE.sub("", text.lower())
        text = HtmlRenderer._HTML_ID_HYPHENATE_RE.sub("-", text).strip("-")

        return text

    def text(self, text):
        # Prevent the default HTML escaping
        return text

    def heading(self, text, level, **attrs):
        return f"<h{level} id=\"{HtmlRenderer.html_id(text)}\">{text}</h{level}>\n"

    def block_code(self, code, info=None):
        lang_attr = f" class=\"language-{info}\"" if info else ""
        return f"<pre><code{lang_attr}>{html_escape(code)}</code></pre>\n"

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

def colorize(text, code):
    return text if "NO_COLOR" in os.environ else f"\u001b[{code}m{text}\u001b[0m"

def normalize_content(content):
    if content is None:
        return ""

    if not isinstance(content, (str, int, float, complex, bool)):
        content = "".join(str(x) for x in content if x is not None)

    return str(content)

def include(path) -> str:
    """
    Return the content of the file at `path`.
    """
    path = Path(path) if isinstance(path, str) else path
    return path.read_text()

def convert_markdown(content) -> str:
    """
    Convert `content` from Markdown to HTML.
    """
    return MarkdownLocal.INSTANCE.value(normalize_content(content))

def strip(content) -> str:
    """
    Remove leading and trailing whitespace from `content`.
    """
    return normalize_content(content).strip()

def plural(noun, count=0, plural=None) -> str:
    """
    Return the plural form of `noun` if `count` is not 1.  Set the
    plural form explicitly with `plural` if it's not a simple matter of
    adding `s` or `es`.
    """
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

def lipsum(count=50, end=".") -> str:
    """
    Generate lorem ipsum filler text.
    """
    return (" ".join((LIPSUM_WORDS[i % len(LIPSUM_WORDS)] for i in range(count))) + end).capitalize()

def html_escape(content) -> str:
    """
    Escape HTML special characters in `text`.
    """
    return html.escape(normalize_content(content), quote=False)

def html_elem(tag, content, **attrs):
    attrs = "".join(html_attrs(attrs))
    return f"<{tag}{attrs}>{normalize_content(content)}</{tag}>"

def html_attrs(attrs):
    for name, value in attrs.items():
        name = "class" if name in ("class_", "_class") else name
        value = name if value is True else value

        if value is not False:
            yield f" {name}=\"{html.escape(value)}\""

# item_fn(index, value) -> "<li>...</li>"
def html_list(data, tag="ul", item_fn=None, **attrs) -> str:
    """
    Generate an HTML list from 'data'.
    """
    if item_fn is None:
        item_fn = lambda index, value: html_elem("li", value)

    items = (item_fn(i, v) for i, v in enumerate(data))

    return html_elem(tag, items, **attrs)

def html_list_csv(path, tag="ul", item_fn=None, **attrs) -> str:
    """
    Generate an HTML list with CSV data loaded from 'path'.
    """
    with open(path, newline="") as f:
        return html_list(csv.reader(f), tag=tag, item_fn=item_fn, **attrs)

# item_fn(row_index, column_index, value) -> "<td>...</td>"
# heading_fn(column_index, value) -> "<th>...</th>"
def html_table(data, headings=None, item_fn=None, heading_fn=None, **attrs) -> str:
    """
    Generate an HTML table from 'data'.
    """
    if item_fn is None:
        item_fn = lambda row_index, column_index, value: html_elem("td", value)

    if heading_fn is None:
        heading_fn = lambda column_index, value: html_elem("th", value)

    thead = None
    trows = (html_elem("tr", (item_fn(ri, ci, x) for ci, x in enumerate(row))) for ri, row in enumerate(data))

    if headings:
        thead = html_elem("thead", html_elem("tr", (heading_fn(i, x) for i, x in enumerate(headings))))

    return html_elem("table", (thead, html_elem("tbody", trows)), **attrs)

def html_table_csv(path, headings=None, item_fn=None, heading_fn=None, **attrs) -> str:
    """
    Generate an HTML table with CSV data loaded from 'path'.
    """
    with open(path, newline="") as f:
        return html_table(csv.reader(f), headings=headings, item_fn=item_fn, heading_fn=heading_fn, **attrs)

if __name__ == "__main__": # pragma: nocover
    command = TransomCommand()
    command.main()
