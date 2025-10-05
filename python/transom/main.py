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
import os
import pathlib
import re
import sys
import threading
import types
import yaml

from collections import defaultdict
from collections.abc import Iterable
from html import escape as html_escape
from html.parser import HTMLParser
from queue import Queue
from shutil import copyfile
from urllib import parse as urlparse

__all__ = ["TransomSite", "TransomCommand"]

_default_page_template = """
<!DOCTYPE html>
<html>

{{page.head}}

{{page.body}}

</html>
"""

_default_head_template = """
<head>
  <title>{{page.title}}</title>
  <link rel="icon" href="data:;"/>

{{page.extra_headers}}

</head>
"""

_default_body_template = """
<body>

{{page.content}}

</body>
"""

_index_file_names = "index.md", "index.html.in", "index.html"
_html_page_titleregex = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_html_body_titleregex = re.compile(r"<(:?h1|h2)\b[^>]*>(.*?)</(:?h1|h2)>", re.IGNORECASE | re.DOTALL)
_markdown_titleregex = re.compile(r"^(?:#|##)\s+(.*)")
_variableregex = re.compile(r"({{{.+?}}}|{{.+?}})")

class TransomError(Exception):
    pass

class TransomSite:
    def __init__(self, project_dir, verbose=False, quiet=False):
        self.project_dir = os.path.normpath(project_dir)
        self.config_dir = os.path.normpath(os.path.join(self.project_dir, "config"))
        self.input_dir = os.path.normpath(os.path.join(self.project_dir, "input"))
        self.output_dir = os.path.normpath(os.path.join(self.project_dir, "output"))

        self.verbose = verbose
        self.quiet = quiet

        self.ignored_file_patterns = [".git", ".svn", ".#*", "#*"]
        self.ignored_link_patterns = []

        self.prefix = ""
        self.extra_input_dirs = [self.config_dir]

        self._config = {
            "site": self,
            "lipsum": lipsum,
            "plural": plural,
            "html_table": html_table,
            "html_table_csv": html_table_csv,
            "convert_markdown": convert_markdown,
        }

        self._modified = False

        self._files = list()
        self._index_files = dict() # parent input dir => File

    def init(self):
        self._page_template = load_site_template(os.path.join(self.config_dir, "page.html"), _default_page_template)
        self._head_template = load_site_template(os.path.join(self.config_dir, "head.html"), _default_head_template)
        self._body_template = load_site_template(os.path.join(self.config_dir, "body.html"), _default_body_template)

        self._ignored_fileregex = "({})".format("|".join([fnmatch.translate(x) for x in self.ignored_file_patterns]))
        self._ignored_fileregex = re.compile(self._ignored_fileregex)

        try:
            exec(read_file(os.path.join(self.config_dir, "site.py")), self._config)
        except FileNotFoundError as e:
            self.warning("Config file not found: {}", e)

    def _compute_modified(self):
        output_mtime = os.path.getmtime(self.output_dir)

        for input_dir in self.extra_input_dirs:
            for root, dirs, names in os.walk(input_dir):
                for name in {x for x in names if not self._ignored_fileregex.match(x)}:
                    mtime = os.path.getmtime(os.path.join(root, name))

                    if mtime > output_mtime:
                        return True

        return False

    def _init_files(self):
        self._files.clear()
        self._index_files.clear()

        for root, dirs, names in os.walk(self.input_dir):
            files = {x for x in names if not self._ignored_fileregex.match(x)}
            index_files = {x for x in names if x in _index_file_names}

            if len(index_files) > 1:
                raise TransomError(f"Duplicate index files in {root}")

            for name in index_files:
                self._files.append(self._init_file(os.path.join(root, name)))

            for name in files - index_files:
                self._files.append(self._init_file(os.path.join(root, name)))

    def _init_file(self, input_path):
        path = pathlib.Path(input_path)
        file_extension = "".join(path.suffixes)
        output_path = self.output_dir / path.relative_to(self.input_dir)

        match file_extension:
            case ".md":
                return MarkdownPage(self, input_path, str(output_path.with_suffix(".html")))
            case ".html.in":
                return HtmlPage(self, input_path, str(output_path).removesuffix(".in"))
            case ".css" | ".js" | ".html":
                return TemplatePage(self, input_path, str(output_path))
            case _:
                return StaticFile(self, input_path, str(output_path))

    def render(self, force=False):
        self.notice("Rendering files from '{}' to '{}'", self.input_dir, self.output_dir)

        if os.path.exists(self.output_dir):
            self._modified = self._compute_modified()

        self._init_files()

        self.notice("Found {:,} input {}", len(self._files), plural("file", len(self._files)))

        thread_count = os.cpu_count()
        batch_size = (len(self._files) + thread_count - 1) // thread_count
        batches = list() # (thread, files)
        render_counter = ThreadSafeCounter()

        for i in range(thread_count):
            thread = WorkerThread(self, f"worker-thread-{i + 1}")

            start = i * batch_size
            end = start + batch_size
            files = self._files[start:end]

            batches.append((thread, files))

        for thread, _ in batches:
            thread.start()

        for thread, files in batches:
            thread.commands.put((process_input_files, (self, files)))

        for thread, files in batches:
            thread.commands.put((render_output_files, (self, files, force, render_counter)))

        for thread, files in batches:
            thread.commands.put((None, None))

        for thread, _ in batches:
            thread.join()

        if os.path.exists(self.output_dir):
            os.utime(self.output_dir)

        rendered_count = render_counter.value()
        unchanged_count = len(self._files) - rendered_count
        unchanged_note = ""

        if unchanged_count > 0:
            unchanged_note = " ({:,} unchanged)".format(unchanged_count)

        self.notice("Rendered {:,} output {}{}", rendered_count, plural("file", rendered_count), unchanged_note)

    def serve(self, port=8080):
        watcher = None

        try:
            watcher = WatcherThread(self)
        except ImportError: # pragma: nocover
            self.notice("Failed to import pyinotify, so I won't auto-render updated input files")
            self.notice("Try installing the Python inotify package")
            self.notice("On Fedora, use 'dnf install python-inotify'")
        else:
            watcher.start()

        try:
            server = ServerThread(self, port)
            server.run()
        except OSError as e:
            # OSError: [Errno 98] Address already in use
            if e.errno == 98:
                raise TransomError(f"Port {port} is already in use")
            else:
                raise
        finally:
            if watcher is not None:
                watcher.stop()

    def check_files(self):
        self._init_files()

        expected_paths = {x.output_path for x in self._files}
        found_paths = set()

        for root, dirs, names in os.walk(self.output_dir):
            found_paths.update((os.path.join(root, x) for x in names))

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
        self._init_files()

        link_sources = defaultdict(set) # link => files
        link_targets = set()

        for file_ in self._files:
            file_._collect_link_data(link_sources, link_targets)

        def not_ignored(link):
            return not any((fnmatch.fnmatchcase(link, x) for x in self.ignored_link_patterns))

        links = filter(not_ignored, link_sources.keys())
        errors = 0

        for link in links:
            if link not in link_targets:
                errors += 1

                print(f"Error: Link to '{link}' has no destination")

                for source in link_sources[link]:
                    print(f"  Source: {source.input_path}")

        return errors

    def debug(self, message, *args):
        if self.verbose:
            print(message.format(*args))

    def notice(self, message, *args):
        if not self.quiet:
            print(message.format(*args))

    def warning(self, message, *args):
        print("Warning:", message.format(*args))

class File:
    __slots__ = "site", "input_path", "_input_mtime", "output_path", "_output_mtime", "url", "title", "parent"

    def __init__(self, site, input_path, output_path):
        self.site = site

        self.input_path = input_path
        self._input_mtime = os.path.getmtime(self.input_path)

        self.output_path = output_path
        self._output_mtime = None

        self.url = self.site.prefix + self.output_path[len(self.site.output_dir):]
        self.title = None
        self.parent = None

        dir_, name = os.path.split(self.input_path)

        if name in _index_file_names:
            self.site._index_files[dir_] = self
            dir_ = os.path.dirname(dir_)

        while dir_ != "":
            try:
                self.parent = self.site._index_files[dir_]
            except KeyError:
                dir_ = os.path.dirname(dir_)
            else:
                break

    def __repr__(self):
        return f"{self.__class__.__name__}({self.input_path}, {self.output_path})"

    def is_modified(self):
        if self._output_mtime is None:
            try:
                self._output_mtime = os.path.getmtime(self.output_path)
            except FileNotFoundError:
                return True

        return self._input_mtime > self._output_mtime

    def process_input(self): # pragma: nocover
        pass

    def render_output(self):
        copy_file(self.input_path, self.output_path)

    def _collect_link_data(self, link_sources, link_targets):
        link_targets.add(self.url)

        if not self.url.endswith(".html"):
            return

        parser = LinkParser(self, link_sources, link_targets)
        parser.feed(read_file(self.output_path))

    @property
    def ancestors(self):
        file_ = self

        while file_ is not None:
            yield file_
            file_ = file_.parent

    @property
    def children(self):
        for file_ in self.site._files:
            if file_.parent is self:
                yield file_

class StaticFile(File):
    pass

class TemplatePage(File):
    __slots__ = "_template", "metadata"

    def is_modified(self):
        return self.site._modified or super().is_modified()

    def process_input(self):
        text = read_file(self.input_path)
        text, self.metadata = extract_metadata(text)

        self.title = self.metadata.get("title")

        if self.title is None:
            path = pathlib.Path(self.input_path)
            file_extension = "".join(path.suffixes)

            match file_extension:
                case ".md":
                    m = _markdown_titleregex.search(text)
                    self.title = m.group(1) if m else ""
                case ".html.in":
                    m = _html_body_titleregex.search(text)
                    self.title = m.group(1) if m else ""
                case ".html":
                    m = _html_page_titleregex.search(text)
                    self.title = m.group(1) if m else ""
                case _:
                    self.title = path.name

        self._template = parse_template(text, self.input_path)

    def render_output(self):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        output = render_template(self._template, self.site._config, {"page": self}, self.input_path)

        with open(self.output_path, "w") as f:
            for elem in output:
                f.write(elem)

    def include(self, input_path):
        text = read_file(input_path)
        template = parse_template(text, input_path)
        locals_ = {"page": self}

        return render_template(template, self.site._config, locals_, input_path)

class HtmlPage(TemplatePage):
    __slots__ = "_page_template", "_head_template", "_body_template"

    def process_input(self):
        super().process_input()

        try:
            self._page_template = load_page_template(self.metadata["page_template"], "")
        except KeyError:
            self._page_template = self.site._page_template

        try:
            self._head_template = load_page_template(self.metadata["head_template"], "")
        except KeyError:
            self._head_template = self.site._head_template

        try:
            self._body_template = load_page_template(self.metadata["body_template"], "{{page.content}}")
        except KeyError:
            self._body_template = self.site._body_template

    def render_output(self):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        output = render_template(self._page_template, self.site._config, {"page": self}, self.input_path)

        with open(self.output_path, "w") as f:
            for elem in output:
                f.write(elem)

    @property
    def head(self):
        return render_template(self._head_template, self.site._config, {"page": self}, self.input_path)

    @property
    def extra_headers(self):
        return self.metadata.get("extra_headers", "")

    @property
    def body(self):
        return render_template(self._body_template, self.site._config, {"page": self}, self.input_path)

    @property
    def content(self):
        return render_template(self._template, self.site._config, {"page": self}, self.input_path)

    def path_nav(self, start=0, end=None, min=1):
        files = reversed(list(self.ancestors))
        links = [f"<a href=\"{x.url}\">{x.title}</a>" for x in files]
        links = links[start:end]

        if len(links) < min:
            return ""

        return f"<nav class=\"page-path\">{''.join(links)}</nav>"

    def toc_nav(self):
        parser = HeadingParser()
        parser.feed("".join(self.content))

        links = [f"<a href=\"#{x[1]}\">{x[2]}</a>" for x in parser.headings
                 if x[0] in ("h1", "h2") and x[1] is not None]

        return f"<nav class=\"page-toc\">{''.join(links)}</nav>"

    def directory_nav(self):
        def sort_fn(x):
            return x.title if x.title else ""

        children = sorted(self.children, key=sort_fn)
        links = [f"<a href=\"{x.url}\">{x.title if x.title else x.url.removeprefix('/')}</a>" for x in children]

        return f"<nav class=\"page-directory\">{''.join(links)}</nav>"

class MarkdownPage(HtmlPage):
    __slots__ = "_converted_content",

    def process_input(self):
        super().process_input()

        self._converted_content = None

    @property
    def content(self):
        if self._converted_content is None:
            self._converted_content = convert_markdown("".join(super().content))

        return self._converted_content

class WorkerThread(threading.Thread):
    def __init__(self, site, name):
        super().__init__(name=name)

        self.site = site
        self.commands = Queue()
        self.rendered_count = 0

    def run(self):
        while True:
            command, args = self.commands.get()

            if command is None:
                break

            try:
                command(*args)
            except:
                sys.exit(1)
            finally:
                self.commands.task_done()

def process_input_files(site, files):
    for file in files:
        file.process_input()

def render_output_files(site, files, force, render_counter):
    for file in files:
        if force or file.is_modified():
            site.debug("Rendering {}", file)

            file.render_output()

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
                self.file.site.warning("Duplicate link target in '{}'", normalized_url)

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

class WatcherThread:
    def __init__(self, site):
        import pyinotify as _pyinotify

        self.site = site

        watcher = _pyinotify.WatchManager()
        mask = _pyinotify.IN_CREATE | _pyinotify.IN_MODIFY

        def render_file(event):
            input_path = os.path.relpath(event.pathname, os.getcwd())
            _, base_name = os.path.split(input_path)

            if os.path.isdir(input_path):
                return True

            if self.site._ignored_fileregex.match(base_name):
                return True

            try:
                file_ = self.site._init_file(input_path)
            except FileNotFoundError:
                return True

            self.site.debug("Processing {}", file_)

            file_.process_input()

            self.site.debug("Rendering {}", file_)

            file_.render_output()

            if os.path.exists(self.site.output_dir):
                os.utime(self.site.output_dir)

        def render_site(event):
            self.site.init()
            self.site.render()

        watcher.add_watch(self.site.input_dir, mask, render_file, rec=True, auto_add=True)

        for input_dir in self.site.extra_input_dirs:
            watcher.add_watch(input_dir, mask, render_site, rec=True, auto_add=True)

        self.notifier = _pyinotify.ThreadedNotifier(watcher)

    def start(self):
        self.site.notice("Watching for input file changes")
        self.notifier.start()

    def stop(self):
        self.notifier.stop()

class ServerThread(threading.Thread):
    def __init__(self, site, port):
        super().__init__(name="server", daemon=True)

        self.site = site
        self.port = port
        self.server = Server(site, port)

    def run(self):
        self.site.notice("Serving at http://localhost:{}", self.port)
        self.server.serve_forever()

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
        self.home = home
        self.name = "transom"

        self.parser = argparse.ArgumentParser()
        self.parser.description = "Generate static websites from Markdown and Python"
        self.parser.formatter_class = argparse.RawDescriptionHelpFormatter

        self.args = None
        self.quiet = False
        self.verbose = False

        subparsers = self.parser.add_subparsers(title="subcommands")

        common = argparse.ArgumentParser()
        common.add_argument("--init-only", action="store_true",
                            help=argparse.SUPPRESS)
        common.add_argument("--verbose", action="store_true",
                            help="Print detailed logging to the console")
        common.add_argument("--quiet", action="store_true",
                            help="Print no logging to the console")
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

        self.quiet = self.args.quiet
        self.verbose = self.args.verbose

        if self.args.command_fn != self.init_command:
            self.lib = TransomSite(self.args.project_dir, verbose=self.verbose, quiet=self.quiet)

            if self.args.output:
                self.lib.output_dir = self.args.output

            self.lib.init()

    def main(self, args=None):
        self.init(args)

        assert self.args is not None

        if self.args.init_only:
            return

        try:
            self.args.command_fn()
        except TransomError as e:
            self.fail(str(e))
        except KeyboardInterrupt: # pragma: nocover
            pass

    def notice(self, message, *args):
        if not self.quiet:
            self.print_message(message, *args)

    def warning(self, message, *args):
        message = "Warning: {}".format(message)
        self.print_message(message, *args)

    def error(self, message, *args):
        message = "Error! {}".format(message)
        self.print_message(message, *args)

    def fail(self, message, *args):
        self.error(message, *args)
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
            if os.path.exists(to_path):
                self.notice("Skipping '{}'. It already exists.", to_path)
                return

            copy_path(from_path, to_path)

            self.notice("Creating '{}'", to_path)

        profile_dir = os.path.join(self.home, "profiles", self.args.profile)
        project_dir = self.args.project_dir

        assert os.path.exists(profile_dir), profile_dir

        for name in os.listdir(os.path.join(profile_dir, "config")):
            copy(os.path.join(profile_dir, "config", name),
                 os.path.join(project_dir, "config", name))

        for name in os.listdir(os.path.join(profile_dir, "input")):
            copy(os.path.join(profile_dir, "input", name),
                 os.path.join(project_dir, "input", name))

        if self.args.github:
            python_dir = os.path.join(self.home, "python")

            copy(os.path.join(profile_dir, ".github/workflows/main.yaml"),
                 os.path.join(project_dir, ".github/workflows/main.yaml"))
            copy(os.path.join(profile_dir, ".gitignore"), os.path.join(project_dir, ".gitignore"))
            copy(os.path.join(profile_dir, ".plano.py"), os.path.join(project_dir, ".plano.py"))
            copy(os.path.join(python_dir, "mistune"), os.path.join(project_dir, "python", "mistune"))
            copy(os.path.join(python_dir, "transom"), os.path.join(project_dir, "python", "transom"))

    def render_command(self):
        self.lib.render(force=self.args.force)

    def serve_command(self):
        self.lib.render(force=self.args.force)
        self.lib.serve(port=self.args.port)

    def check_links_command(self):
        errors = self.lib.check_links()

        if errors == 0:
            self.notice("PASSED")
        else:
            self.fail("FAILED")

    def check_files_command(self):
        missing_files, extra_files = self.lib.check_files()

        if extra_files != 0:
            self.warning("{} extra files in the output", extra_files)

        if missing_files == 0:
            self.notice("PASSED")
        else:
            self.fail("FAILED")

def read_file(path):
    with open(path, "r") as f:
        return f.read()

def copy_file(from_path, to_path):
    try:
        copyfile(from_path, to_path)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(to_path), exist_ok=True)
        copyfile(from_path, to_path)

def copy_dir(from_dir, to_dir):
    for name in os.listdir(from_dir):
        if name == "__pycache__":
            continue

        from_path = os.path.join(from_dir, name)
        to_path = os.path.join(to_dir, name)

        copy_path(from_path, to_path)

def copy_path(from_path, to_path):
    if os.path.isdir(from_path):
        copy_dir(from_path, to_path)
    else:
        copy_file(from_path, to_path)

def extract_metadata(text):
    if text.startswith("---\n"):
        end = text.index("---\n", 4)
        header = text[4:end]
        text = text[end + 4:]

        return text, yaml.safe_load(header)

    return text, dict()

def load_site_template(path, default_text):
    if path is None or not os.path.exists(path):
        return parse_template(default_text, "[default]")

    return parse_template(read_file(path), path)

def load_page_template(path, default_text):
    if path is None:
        return parse_template(default_text, "[default]")

    return parse_template(read_file(path), path)

def parse_template(text, context):
    template = list()

    for token in _variableregex.split(text):
        if token.startswith("{{{") and token.endswith("}}}"):
            item = token[1:-1]
        elif token.startswith("{{") and token.endswith("}}"):
            try:
                item = compile(token[2:-2], "<string>", "eval")
            except Exception as e:
                raise TransomError(f"Error parsing template: {context}: {e}")
        else:
            item = token

        template.append(item)

    return template

def render_template(template, globals_, locals_, context):
    for elem in template:
        if type(elem) is types.CodeType:
            try:
                result = eval(elem, globals_, locals_)
            except TransomError:
                raise
            except Exception as e:
                raise TransomError(f"{context}: {e}")

            if type(result) is types.GeneratorType:
                yield from result
            else:
                yield result
        else:
            yield elem

_heading_idregex_1 = re.compile(r"[^a-zA-Z0-9_ ]+")
_heading_idregex_2 = re.compile(r"[_ ]")

class HtmlRenderer(mistune.renderers.html.HTMLRenderer):
    def heading(self, text, level, **attrs):
        id = _heading_idregex_1.sub("", text)
        id = _heading_idregex_2.sub("-", id)
        id = id.lower()

        return f"<h{level} id=\"{id}\">{text}</h{level}>\n"

class MarkdownLocal(threading.local):
    def __init__(self):
        self.value = mistune.create_markdown(renderer=HtmlRenderer(escape=False), plugins=["table", "strikethrough"])
        self.value.block.list_rules += ['table', 'nptable']

_markdown_local = MarkdownLocal()

def convert_markdown(text):
    lines = (x for x in text.splitlines(keepends=True) if not x.startswith(";;"))
    return _markdown_local.value("".join(lines))

_lipsum_words = [
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "vestibulum", "enim", "urna",
    "ornare", "pellentesque", "felis", "eget", "maximus", "lacinia", "lorem", "nulla", "auctor", "massa", "vitae",
    "ultricies", "varius", "curabitur", "consectetur", "lacus", "sapien", "a", "lacinia", "urna", "tempus", "quis",
    "vestibulum", "vitae", "augue", "non", "augue", "lobortis", "semper", "nullam", "fringilla", "odio", "quis",
    "ligula", "consequat", "condimentum", "integer", "tempus", "sem",
]

def lipsum(count=50, end="."):
    return (" ".join((_lipsum_words[i % len(_lipsum_words)] for i in range(count))) + end).capitalize()

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

if __name__ == "__main__": # pragma: nocover
    command = TransomCommand()
    command.main()
