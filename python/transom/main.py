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

from html import escape as html_escape
from html.parser import HTMLParser
from pathlib import Path
from queue import Queue
from urllib import parse as urlparse

__all__ = "TransomError", "TransomTemplate", "TransomSite", "TransomCommand"

class TransomError(Exception):
    def __init__(self, message, contexts=None):
        self.message = message
        self.contexts = contexts

    def __str__(self):
        if self.contexts:
            return "".join(f"{x}: " for x in self.contexts) + str(self.message)
        else:
            return str(self.message)

class error_handling:
    def __init__(self, contexts):
        self.contexts = contexts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type == TransomError:
            if not exc_value.contexts:
                exc_value.contexts = self.contexts

            return False

        if exc_type is not None:
            raise TransomError(exc_value, self.contexts)

class TransomTemplate:
    __slots__ = "pieces", "context"
    _VARIABLE_RE = re.compile(r"({{{.+?}}}|{{.+?}})")

    def __init__(self, text, context=None):
        self.pieces = []
        self.context = context

        self._parse(text)

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(str(self.context))})"

    def _parse(self, text):
        for token in TransomTemplate._VARIABLE_RE.split(text):
            if token.startswith("{{{") and token.endswith("}}}"):
                piece = token[1:-1]
            elif token.startswith("{{") and token.endswith("}}"):
                # XXX try to move {{{ }}} handling in here

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

                with error_handling([input_file._input_path, token]):
                    result = eval(code, input_file._site._globals, input_file._locals)

                if type(result) is types.GeneratorType:
                    yield from result
                else:
                    yield str(result)
            else:
                yield piece

    def write(self, input_file):
        text = "".join(self.render(input_file))
        input_file._output_path.write_text(text)

def load_template(path):
    path = Path(path) if isinstance(path, str) else path
    return TransomTemplate(path.read_text(), path)

def object_property(name, type_, default=None):
    def get(obj):
        return getattr(obj, f"_{name}", default)

    def set_(obj, value):
        if not isinstance(value, type_):
            raise TransomError(f"Site property '{name}' set to illegal type '{type(value).__name__}' "
                               f"(type '{type_.__name__}' is required)")

        setattr(obj, f"_{name}", value)

    return property(get, set_)

class TransomSite:
    _FALLBACK_PAGE_TEMPLATE = TransomTemplate("<!doctype html>" \
        "<html lang=\"en\"><head><meta charset=\"utf-8\"><title>{{page.title}}</title></head>{{page.body}}</html>")
    _FALLBACK_BODY_TEMPLATE = TransomTemplate("<body>{{page.content}}</body>")

    prefix = object_property("prefix", str, "")
    ignored_file_patterns = object_property("ignored_file_patterns", list, [".git", ".#*", "#*"])
    page_template = object_property("page_template", TransomTemplate)
    body_template = object_property("body_template", TransomTemplate)

    def __init__(self, site_dir, verbose=False, quiet=False, threads=8):
        self._site_dir = Path(site_dir).resolve()
        self._config_dir = self._site_dir / "config"
        self._input_dir = self._site_dir / "input"
        self._output_dir = self._site_dir / "output"

        self._verbose = verbose
        self._quiet = quiet

        self._globals = {
            "site": self,
            "include": include,
            "lipsum": lipsum,
            "plural": plural,
            "html_escape": html_escape,
            "html_table": html_table,
            "html_table_csv": html_table_csv,
            "load_template": load_template,
            "TransomError": TransomError,
            "TransomTemplate": TransomTemplate,
        }

        threading.current_thread().name = "main-thread"

        self._worker_threads = []
        self._worker_errors = Queue()

        for i in range(threads):
            self._worker_threads.append(WorkerThread(self, f"worker-thread-{i + 1}", self._worker_errors))

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(str(self._site_dir))})"

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def start(self):
        self.debug("Starting {} worker {}", len(self._worker_threads), plural("thread", len(self._worker_threads)))

        for thread in self._worker_threads:
            thread.start()

    def stop(self):
        self.debug("Stopping worker threads")

        for thread in self._worker_threads:
            thread.commands.put((None, None))
            thread.join()

    def load_config_files(self):
        self.debug("Loading config files in '{}'", self._config_dir)

        page_template_path = self._config_dir / "page.html"
        body_template_path = self._config_dir / "body.html"
        site_code_path = self._config_dir / "site.py"

        self.page_template = TransomSite._FALLBACK_PAGE_TEMPLATE
        self.body_template = TransomSite._FALLBACK_BODY_TEMPLATE

        if page_template_path.exists():
            self.debug("Loading page template from '{}'", page_template_path)
            self.page_template = load_template(page_template_path)

        if body_template_path.exists():
            self.debug("Loading body template from '{}'", body_template_path)
            self.body_template = load_template(body_template_path)

        if site_code_path.exists():
            self.debug("Executing site code in '{}'", self._config_dir / "site.py")

            with error_handling([site_code_path]):
                exec(site_code_path.read_text(), self._globals)

        self._ignored_file_re = re.compile \
            ("|".join([fnmatch.translate(x) for x in self.ignored_file_patterns] + ["(?!)"]))

    def load_input_files(self):
        self.debug("Loading input files in '{}'", self._input_dir)

        def find_input_files(start_path, input_files, parent_file):
            with os.scandir(start_path) as entries:
                entries = tuple(x for x in entries if not self._ignored_file_re.match(x.name))

                for entry in entries:
                    if entry.name in ("index.md", "index.html"):
                        input_file = self.load_input_file(Path(entry.path), parent_file)
                        input_files.append(input_file)
                        parent_file = input_file
                        break

                for entry in entries:
                    if entry.name in ("index.md", "index.html"):
                        continue

                    if entry.is_file():
                        input_file = self.load_input_file(Path(entry.path), parent_file)
                        input_files.append(input_file)
                    elif entry.is_dir():
                        find_input_files(entry.path, input_files, parent_file)

        input_files = []

        try:
            find_input_files(self._input_dir, input_files, None)
        except FileNotFoundError:
            self.notice("Input directory not found: {}", self._input_dir)

        return input_files

    def load_input_file(self, input_path, parent):
        self.debug("Loading '{}'", input_path)

        match input_path.suffix:
            case ".md":
                input_file = MarkdownPage(self, input_path, parent)
            case ".css" | ".csv" | ".html" | ".js" | ".json" | ".svg" | ".txt":
                input_file = TemplateFile(self, input_path, parent)
            case _:
                input_file = StaticFile(self, input_path, parent)

        return input_file

    def find_config_modified(self, last_render_time):
        def find_modified_file(start_path, last_render_time):
            with os.scandir(start_path) as entries:
                for entry in (x for x in entries if not self._ignored_file_re.match(x.name)):
                    if entry.is_file():
                        if entry.stat().st_mtime >= last_render_time:
                            return True
                    elif entry.is_dir():
                        return find_modified_file(entry.path, last_render_time)

        try:
            if find_modified_file(self._config_dir, last_render_time):
                return True
        except FileNotFoundError:
            self.notice("Config directory not found: {}", self._config_dir)

    def render(self, force=False):
        self.notice("Rendering files from '{}' to '{}'", self._input_dir, self._output_dir)

        self.load_config_files()

        input_files = self.load_input_files()
        last_render_time = 0

        if not input_files:
            return input_files

        if not force and self._output_dir.exists():
            last_render_time = self._output_dir.stat().st_mtime

            if self.find_config_modified(last_render_time):
                last_render_time = 0

        self.debug("Processing {:,} input {}", len(input_files), plural("file", len(input_files)))

        input_file_batches = itertools.batched(input_files, math.ceil(len(input_files) / len(self._worker_threads)))
        modified_file_batches = tuple([] for x in self._worker_threads)

        for thread, files, modified_files in zip(self._worker_threads, input_file_batches, modified_file_batches):
            thread.commands.put((thread.process_input_files, (files, last_render_time, modified_files)))

        for thread in self._worker_threads:
            thread.commands.join()

        modified_count = sum(len(x) for x in modified_file_batches)

        self.debug("Rendering {:,} output {} to '{}'", modified_count, plural("file", modified_count), self._output_dir)

        for thread, files in zip(self._worker_threads, modified_file_batches):
            thread.commands.put((thread.render_output_files, (files,)))

        for thread in self._worker_threads:
            thread.commands.join()

        if not self._worker_errors.empty():
            raise TransomError("Rendering failed")

        if self._output_dir.exists():
            self._output_dir.touch()

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
        if self._verbose:
            message = f"{colorize(threading.current_thread().name, '90')} {message}"

        print(message.format(*args), file=sys.stderr, flush=True)

    def debug(self, message, *args):
        if self._verbose:
            self.log(colorize(f"debug: {message}", "37"), *args)

    def notice(self, message, *args):
        if not self._quiet:
            message = f"{colorize('notice:', '36')} {message}" if self._verbose else message
            self.log(message, *args)

    def error(self, message, *args):
        self.log(f"{colorize('error:', '31;1')} {message}", *args)

class InputFile:
    __slots__ = "_site", "_input_path", "_output_path", "_url", "_title", "_parent"

    url = object_property("url", str)
    title = object_property("title", str)
    parent = object_property("parent", object)

    def __init__(self, site, input_path, parent):
        self._site = site
        self._input_path = input_path

        # Path.relative_to is surprisingly slow in Python 3.12, so we
        # avoid it here
        output_path = str(self._input_path)[len(str(self._site._input_dir)) + 1:]

        if output_path.endswith(".md"):
            output_path = output_path[:-3] + ".html"

        self._output_path = self._site._output_dir / output_path

        self._url = f"{self._site.prefix}/{output_path}"
        self._title = self._output_path.name
        self._parent = parent

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(str(self._input_path))})"

    @property
    def ancestors(self):
        parent = self.parent

        while parent is not None:
            yield parent
            parent = parent.parent

    def _process_input(self, last_render_time=0):
        self.debug("Processing input")
        return self._input_path.stat().st_mtime >= last_render_time

    def _render_output(self):
        self.debug("Rendering output")
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    def debug(self, message, *args):
        self._site.debug(f"{self._input_path}: {message}", *args)

class StaticFile(InputFile):
    __slots__ = ()

    def _render_output(self):
        super()._render_output()
        shutil.copy(self._input_path, self._output_path)

class GeneratedFile(InputFile):
    __slots__ = ()
    _HEADER_RE = re.compile(r"(?s)^---\s*\n(.*?)\n---\s*\n")

    def extract_header_code(self, text):
        match_ = GeneratedFile._HEADER_RE.match(text)

        if match_:
            return text[match_.end():], match_.group(1)

        return text, None

    def exec_header_code(self, header_code):
        self.debug("Executing header code")

        with error_handling([self._input_path, "header"]):
            exec(header_code, self._site._globals, self._locals)

class TemplateFile(GeneratedFile):
    __slots__ = "_template", "_locals"

    def _process_input(self, last_render_time=0):
        modified = super()._process_input(last_render_time)

        if modified:
            text = self._input_path.read_text()
            text, header_code = self.extract_header_code(text)

            self._template = TransomTemplate(text, self._input_path)
            self._locals = {"file": self}

            if header_code:
                self.exec_header_code(header_code)

        return modified

    def _render_output(self):
        super()._render_output()
        self._template.write(self)

class MarkdownPage(GeneratedFile):
    __slots__ = "_page_template", "_body_template", "_content_template", "_locals"
    _MARKDOWN_TITLE_RE = re.compile(r"(?s)^(?:#|##)\s+(.*?)\n")
    _HTML_TITLE_RE = re.compile(r"(?si)<(?:h1|h2)\b[^>]*>(.*?)</(?:h1|h2)>")

    page_template = object_property("page_template", TransomTemplate)
    body_template = object_property("body_template", TransomTemplate)

    def _process_input(self, last_render_time=0):
        modified = super()._process_input(last_render_time)

        if modified:
            text = self._input_path.read_text()
            text, header_code = self.extract_header_code(text)

            self._page_template = self._site._page_template
            self._body_template = self._site._body_template
            self._content_template = TransomTemplate(text, self._input_path)

            match_ = MarkdownPage._MARKDOWN_TITLE_RE.search(text)
            self.title = match_.group(1) if match_ else ""
            match_ = MarkdownPage._HTML_TITLE_RE.search(text)
            self.title = match_.group(1) if match_ else self.title

            self._locals = {
                "page": self,
                "render_template": functools.partial(MarkdownPage.render_template, self),
                "path_nav": functools.partial(MarkdownPage.path_nav, self),
                "toc_nav": functools.partial(MarkdownPage.toc_nav, self),
            }

            if header_code:
                self.exec_header_code(header_code)

        return modified

    def _render_output(self):
        super()._render_output()
        self.page_template.write(self)

    @property
    def body(self):
        return self.body_template.render(self)

    @property
    def content(self):
        pieces = self._content_template.render(self)
        return MarkdownLocal.INSTANCE.value("".join(pieces))

    def render_template(self, path):
        pieces = load_template(path).render(self)
        return MarkdownLocal.INSTANCE.value("".join(pieces))

    def path_nav(self, start=0, end=None, min=1):
        files = [self] + list(self.ancestors)
        files.reverse()
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
            modified = input_file._process_input(last_render_time)

            if modified:
                modified_files.append(input_file)

    def render_output_files(self, modified_files):
        for input_file in modified_files:
            input_file._render_output()

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
        self.input_files = {x._input_path: x for x in self.site.render()}

class ServerRequestHandler(httpserver.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server, directory=None):
        super().__init__(request, client_address, server, directory=server.site._output_dir)

    def do_POST(self):
        assert self.path == "/STOP", self.path

        self.server.shutdown()

        self.send_response(httpserver.HTTPStatus.OK)
        self.end_headers()

    # This intercepts all GET and HEAD requests
    def send_head(self):
        if not self.path.startswith(self.server.site.prefix):
            self.send_response(httpserver.HTTPStatus.TEMPORARY_REDIRECT)
            self.send_header("Location", self.server.site.prefix + self.path)
            self.end_headers()
            return

        self.path = self.path + "index.html" if self.path.endswith("/") else self.path
        self.path = self.path.removeprefix(self.server.site.prefix).removeprefix("/")

        input_path = self.server.site._input_dir / self.path

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

            for ancestor in input_file.ancestors:
                ancestor._process_input()

            input_file._process_input()
            input_file._render_output()

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
            self.site._output_dir = Path(self.args.output)

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

def colorize(text, code):
    return text if "NO_COLOR" in os.environ else f"\u001b[{code}m{text}\u001b[0m"

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
