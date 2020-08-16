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

from __future__ import print_function

import argparse as _argparse
import codecs as _codecs
import commandant as _commandant
import csv as _csv
import fnmatch as _fnmatch
import functools as _functools
import http.server as _http
import markdown2 as _markdown
import os as _os
import re as _re
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile
import threading as _threading
import time as _time
import traceback as _traceback

from collections import defaultdict as _defaultdict
from urllib.parse import urljoin as _urljoin
from urllib.parse import urlsplit as _urlsplit
from urllib.request import urlopen as _urlopen
from xml.etree.ElementTree import XML as _XML
from xml.sax.saxutils import escape as _xml_escape

_markdown_title_regex = _re.compile(r"(#|##)(.+)")
_variable_regex = _re.compile("({{.+?}})")
_reload_script = "<script src=\"http://localhost:35729/livereload.js\"></script>"

_markdown_extras = {
    "code-friendly": True,
    "footnotes": True,
    "header-ids": True,
    "markdown-in-html": True,
    "tables": True,
}

class Transom:
    def __init__(self, config_dir, input_dir, output_dir, home=None):
        self.config_dir = config_dir
        self.input_dir = _os.path.abspath(input_dir)
        self.output_dir = output_dir
        self.home = home

        self.verbose = False
        self.quiet = False
        self.reload = False

        self._config_file = _os.path.join(self.config_dir, "config.py")
        self._config = None

        self._body_template_path = _os.path.join(self.config_dir, "default-body.html")
        self._page_template_path = _os.path.join(self.config_dir, "default-page.html")
        self._body_template = None
        self._page_template = None

        self._input_files = dict()
        self._output_files = dict()

        self._links = _defaultdict(set)
        self._link_targets = set()

        self._ignored_file_patterns = ["*/.git", "*/.svn", "*/.#*"]
        self._ignored_link_patterns = list()

        self._markdown_converter = _markdown.Markdown(extras=_markdown_extras)

    def init(self):
        if self.home is not None:
            if not _os.path.isfile(self._page_template_path):
                self._page_template_path = _os.path.join(self.home, "files", "default-page.html")

            if not _os.path.isfile(self._body_template_path):
                self._body_template_path = _os.path.join(self.home, "files", "default-body.html")

        if not _os.path.isfile(self._page_template_path):
            raise Exception(f"No page template found at {self._page_template_path}")

        if not _os.path.isfile(self._body_template_path):
            raise Exception(f"No body template found at {self._body_template_path}")

        self._page_template = _read_file(self._page_template_path)
        self._body_template = _read_file(self._body_template_path)

        self._config = {
            "site": self,
            "ignored_files": self._ignored_file_patterns,
            "ignored_links": self._ignored_link_patterns,
            "lipsum": _lipsum,
            "html_table": _html_table,
            "html_table_csv": _html_table_csv,
        }

        if _os.path.isfile(self._config_file):
            exec(_read_file(self._config_file), self._config)

    def _find_input_paths(self):
        input_paths = list()

        for root, dirs, files in _os.walk(self.input_dir):
            # Process index files before the others in the same directory
            for file_ in files:
                if file_.startswith("index."):
                    input_paths.append(_os.path.join(root, file_))
                    files.remove(file_)
                    break

            for file_ in files:
                input_paths.append(_os.path.join(root, file_))

        return input_paths

    def _create_input_files(self, input_paths):
        for input_path in input_paths:
            if not self._is_ignored_file(input_path):
                self._create_file(input_path)

        index_files = dict()
        other_files = _defaultdict(list)

        for file_ in self._output_files.values():
            path = file_._output_path[len(self.output_dir):]
            dir_, name = _os.path.split(path)

            if name == "index.html":
                index_files[dir_] = file_
            else:
                other_files[dir_].append(file_)

        for dir_ in index_files:
            if dir_ == "/":
                continue

            parent_dir = _os.path.split(dir_)[0]
            file_ = index_files[dir_]
            file_.parent = index_files[parent_dir]

        for dir_ in other_files:
            parent = index_files.get(dir_)

            for file_ in other_files[dir_]:
                file_.parent = parent

    def _is_ignored_file(self, input_path):
        path = input_path[len(self.input_dir):]

        for pattern in self._ignored_file_patterns:
            if _fnmatch.fnmatch(path, pattern):
                return True

        return False

    def _create_file(self, input_path):
        name, ext = _os.path.splitext(input_path)

        if input_path.endswith(".md"):
            return _MarkdownPage(self, input_path)
        elif input_path.endswith(".html.in"):
            return _HtmlInPage(self, input_path)
        else:
            return _StaticFile(self, input_path)

    def render(self, force=False, serve=None):
        self._create_input_files(self._find_input_paths())

        self.notice("Rendering {:,} input files", len(self._input_files))

        for file_ in self._input_files.values():
            self.info("Processing {}", file_)
            file_._process_input()

        for file_ in self._output_files.values():
            if file_._is_modified() or force:
                self.info("Rendering {}", file_)
                file_._render_output()

        if _os.path.exists(self.output_dir):
            _os.utime(self.output_dir)

        if serve is not None:
            self._serve(serve)

    def _serve(self, port):
        try:
            watcher = _WatcherThread(self)
            watcher.start()
        except ImportError:
            self.notice("Failed to import pyinotify, so I won't auto-render updated input files")
            self.notice("Try installing the python3-pyinotify package")

        try:
            livereload = _subprocess.Popen(f"livereload {self.output_dir}", shell=True)
        except _subprocess.CalledProcessError as e:
            self.notice("Failed to start the livereload server, so I won't auto-reload the browser")
            self.notice("Use 'npm install -g livereload' to install the server")
            self.notice("Subprocess error: {}", e)
            livereload = None

        try:
            server = _ServerThread(self, port)
            server.run()
        finally:
            if livereload is not None:
                livereload.terminate()

    def _render_one_file(self, input_path, force=False):
        file_ = self._create_file(input_path)

        self.notice("Rendering {}", file_)

        file_._process_input()
        file_._render_output(force=force)

        _os.utime(self.output_dir)

    def check_files(self):
        self._create_input_files(self._find_input_paths())

        expected_paths = set()
        found_paths = set()

        for file_ in self._output_files.values():
            expected_paths.add(file_._output_path)

        found_paths = self._find_output_paths()

        missing_paths = expected_paths.difference(found_paths)
        extra_paths = found_paths.difference(expected_paths)

        if missing_paths:
            print("Missing output files:")

            for path in sorted(missing_paths):
                print(f"  {path}")

        if extra_paths:
            print("Extra output files:")

            for path in sorted(extra_paths):
                print(f"  {path}")

        return len(missing_paths), len(extra_paths)

    def _find_output_paths(self):
        output_paths = set()

        for root, dirs, files in _os.walk(self.output_dir):
            for file_ in files:
                output_paths.add(_os.path.join(root, file_))

        return output_paths

    def check_links(self, internal=True, external=False):
        self._create_input_files(self._find_input_paths())

        for file_ in self._output_files.values():
            file_._find_links()

        errors_by_link = _defaultdict(list)
        links = self._filter_links(self._links)

        for link in links:
            if internal and link not in self._link_targets:
                errors_by_link[link].append("Link has no target")

            if external and not link.startswith(self.url):
                code, error = self._check_external_link(link)

                if code >= 400:
                    errors_by_link[link].append(f"HTTP error code {code}")

                if error:
                    errors_by_link[link].append(error.message)

        for link in errors_by_link:
            print(f"Link: {link}")

            for error in errors_by_link[link]:
                print(f"  Error: {error}")

            for source in self._links[link]:
                print(f"  Source: {source}")

        return len(errors_by_link)

    def _filter_links(self, links):
        def retain(link):
            for pattern in self._ignored_link_patterns:
                path = link[len(self.url):]

                if _fnmatch.fnmatch(path, pattern):
                    return False

            return True

        return filter(retain, links)

    def _check_external_link(self, link):
        sock, code, error = None, None, None

        try:
            sock = _urlopen(link, timeout=5)
            code = sock.getcode()
        except IOError as e:
            error = e
        finally:
            if sock:
                sock.close()

        return code, error

    def get_url(self, output_path):
        path = output_path[len(self.output_dir):]
        path = path.replace(_os.path.sep, "/")

        return path

    def info(self, message, *args):
        if self.verbose:
            print(message.format(*args))

    def notice(self, message, *args):
        if not self.quiet:
            print(message.format(*args))

    def warn(self, message, *args):
        print("Warning!", message.format(*args))

class _File:
    __slots__ = "site", "parent", "_input_path", "_input_path_stem", "_input_mtime", "_output_path", "_output_mtime"

    def __init__(self, site, input_path):
        self.site = site
        self.parent = None

        self._input_path = input_path
        self._input_path_stem = self._input_path[len(self.site.input_dir) + 1:]
        self._input_mtime = _os.path.getmtime(self._input_path)

        self._output_path = _os.path.join(self.site.output_dir, self._input_path_stem)
        self._output_mtime = None

        self.site._input_files[self._input_path] = self
        self.site._output_files[self._input_path] = self

    def __repr__(self):
        return f"{self.__class__.__name__}({self._input_path_stem})"

    def _is_modified(self):
        if self._output_mtime is None:
            try:
                self._output_mtime = _os.path.getmtime(self._output_path)
            except FileNotFoundError:
                return True

        return self._input_mtime > self._output_mtime

class _HtmlPage(_File):
    __slots__ = "url", "title", "_attributes", "_content"

    def __init__(self, site, input_path):
        super().__init__(site, input_path)

        self.url = self.site.get_url(self._output_path)
        self.title = ""

        self.site._link_targets.add(self.url)

        if self.url.endswith("/index.html"):
            self.site._link_targets.add(self.url[:-10])
            self.site._link_targets.add(self.url[:-11])

    def _process_input(self):
        self._content = _read_file(self._input_path)
        self._extract_metadata()
        self.title = self._attributes.get("title", "")

    def _extract_metadata(self):
        self._attributes = dict()

        if self._content.startswith("---\n"):
            end = self._content.index("---\n", 4)
            lines = self._content[4:end].strip().split("\n")

            for line in lines:
                key, value = line.split(":", 1)
                self._attributes[key.strip()] = value.strip()

            self._content = self._content[end + 4:]

    def _render_output(self, force=False):
        self._convert_content()

        page_template = self.site._page_template

        if "page_template" in self._attributes: # XXX don't repeat this for each render
            page_template_path = self._attributes["page_template"]

            if _os.path.isfile(page_template_path):
                page_template = _read_file(page_template_path)
            else:
                raise Exception(f"Page template {page_template_path} not found")

        _write_file(self._output_path, self._replace_variables(page_template))

    def _convert_content(self):
        pass

    @property
    def reload_script(self):
        return _reload_script

    @property
    def extra_headers(self):
        return self._attributes.get("extra_headers", "")

    @property
    def body(self):
        body_template = self.site._body_template

        if "body_template" in self._attributes:
            body_template_path = self._attributes["body_template"]

            if body_template_path == "none":
                body_template = "{{page.content}}"
            elif _os.path.isfile(body_template_path):
                body_template = _read_file(body_template_path)
            else:
                raise Exception(f"Body template {body_template_path} not found")

        return self._replace_variables(body_template)

    @property
    def content(self):
        return self._replace_variables(self._content, self._input_path)

    @property
    def path_nav_links(self):
        files = [self]
        file_ = self.parent

        while file_ is not None:
            files.append(file_)
            file_ = file_.parent

        return [f"<a href=\"{x.url}\">{x.title}</a>" for x in reversed(files)]

    def path_nav(self, start=None, end=None):
        return f"<nav id=\"-path-nav\">{''.join(self.path_nav_links[start:end])}</nav>"

    def _replace_variables(self, text, input_path=None):
        out = list()
        tokens = _variable_regex.split(text)
        globals_ = self.site._config
        locals_ = {"page": self}

        for token in tokens:
            if token.startswith("{{"):
                expr = token[2:-2]
                out.append(eval(expr, globals_, locals_) or "")
            else:
                out.append(token)

        return "".join(out)

    def include(self, input_path):
        with open(input_path, "r") as f:
            content = f.read()

        if input_path.endswith(".md"):
            content = self.site._markdown_converter.convert(content)

        return self._replace_variables(content, input_path=input_path)

    def _find_links(self):
        if not self._output_path.endswith(".html"):
            return

        self.site.info("Finding links in {}", self)

        self._content = _read_file(self._output_path)

        try:
            root = _XML(self._content)
        except Exception as e:
            self.site.info(str(e))
            return

        assert root is not None, self._content

        links = self._gather_links(root)
        link_targets = self._gather_link_targets(root)

        for link in links:
            if link == "?":
                continue

            scheme, netloc, path, query, fragment = _urlsplit(link)

            if scheme and scheme not in ("file", "http", "https", "ftp"):
                continue

            if netloc in ("issues.apache.org", "bugzilla.redhat.com"):
                continue

            if (fragment and not path) or not path.startswith("/"):
                link = _urljoin(self.url, link)

            self.site._links[link].add(self.url)

        self.site._link_targets.update(link_targets)

    def _gather_links(self, root_elem):
        links = set()

        for elem in root_elem.iter("*"):
            for name in ("href", "src", "action"):
                try:
                    link = elem.attrib[name]
                except KeyError:
                    continue

                links.add(link)

        return links

    def _gather_link_targets(self, root_elem):
        link_targets = set()

        for elem in root_elem.iter("*"):
            try:
                id = elem.attrib["id"]
            except KeyError:
                continue

            target = f"{self.url}#{id}"

            if target in link_targets:
                self.site.info("Duplicate link target in '{}'", target)

            link_targets.add(target)

        return link_targets

class _MarkdownPage(_HtmlPage):
    __slots__ = ()

    def __init__(self, site, input_path):
        super().__init__(site, input_path)

        self._output_path = f"{self._output_path[:-3]}.html"

    def _process_input(self):
        super()._process_input()

        match = _markdown_title_regex.search(self._content)

        if match:
            self.title = match.group(2).strip()

    def _convert_content(self):
        # Strip out comments
        content_lines = self._content.splitlines()
        content_lines = [x for x in content_lines if not x.startswith(";;")]

        self._content = _os.linesep.join(content_lines)
        self._content = self.site._markdown_converter.convert(self._content)

class _HtmlInPage(_HtmlPage):
    __slots__ = ()

    def __init__(self, site, input_path):
        super().__init__(site, input_path)

        self._output_path = self._output_path[:-3]

    def _process_input(self):
        super()._process_input()

        try:
            self.title = self._attributes["title"]
        except KeyError:
            match = _html_title_regex.search(self._content)

            if match:
                self.title = match.group(2).strip()
                self.title = _html_tag_regex.sub("", self.title)

class _StaticFile(_File):
    __slots__ = ()

    def _process_input(self):
        pass

    def _render_output(self, force=False):
        _copy_file(self._input_path, self._output_path)

class _WatcherThread(_threading.Thread):
    def __init__(self, site):
        import pyinotify as _pyinotify

        super().__init__()

        self.site = site
        self.daemon = True

        watcher = _pyinotify.WatchManager()
        mask = _pyinotify.IN_CREATE | _pyinotify.IN_DELETE | _pyinotify.IN_MODIFY

        def render(event):
            if _os.path.isdir(event.pathname) or event.name.startswith((".#", "#")):
                return True

            self.site._render_one_file(event.pathname, force=True) # XXX Handle delete

        watcher.add_watch(self.site.input_dir, mask, render, rec=True, auto_add=True)

        self.notifier = _pyinotify.Notifier(watcher)

    def run(self):
        self.site.notice("Watching for input file changes")
        self.notifier.loop()

class _ServerThread(_threading.Thread):
    def __init__(self, site, port):
        super().__init__()

        self.site = site
        self.port = port
        self.daemon = True

        address = "localhost", self.port
        handler = _functools.partial(_http.SimpleHTTPRequestHandler, directory=self.site.output_dir)

        self.server = _http.ThreadingHTTPServer(address, handler)

    def run(self):
        self.site.notice("Serving at http://localhost:{}", self.port)
        self.server.serve_forever()

_description = """
Generate static websites from Markdown and Python
"""

_epilog = """
subcommands:
  init                  Prepare an input directory
  render                Generate the output files
  check-links           Check for broken links
  check-files           Check for missing or extra files
"""

class TransomCommand(_commandant.Command):
    def __init__(self, home=None):
        super().__init__(home=home, name="transom", standard_args=False)

        self.description = _description
        self.epilog = _epilog

        subparsers = self.add_subparsers()

        init = subparsers.add_parser("init")
        init.description = "Prepare an input directory"
        init.set_defaults(func=self.init_command)
        init.add_argument("config_dir", metavar="CONFIG-DIR",
                          help="Read config files from CONFIG-DIR")
        init.add_argument("input_dir", metavar="INPUT-DIR",
                          help="Place default input files in INPUT-DIR")
        init.add_argument("--quiet", action="store_true",
                          help="Print no logging to the console")
        init.add_argument("--verbose", action="store_true",
                          help="Print detailed logging to the console")
        init.add_argument("--init-only", action="store_true",
                          help=_argparse.SUPPRESS)

        render = subparsers.add_parser("render")
        render.description = "Generate output files"
        render.set_defaults(func=self.render_command)
        render.add_argument("config_dir", metavar="CONFIG-DIR",
                            help="Read config files from CONFIG-DIR")
        render.add_argument("input_dir", metavar="INPUT-DIR",
                            help="Read input files from INPUT-DIR")
        render.add_argument("output_dir", metavar="OUTPUT-DIR",
                            help="Write output files to OUTPUT-DIR")
        render.add_argument("--force", action="store_true",
                            help="Render all input files, including unmodified ones")
        render.add_argument("--serve", type=int, metavar="PORT",
                            help="Serve the site and rerender when input files change")
        render.add_argument("--quiet", action="store_true",
                            help="Print no logging to the console")
        render.add_argument("--verbose", action="store_true",
                            help="Print detailed logging to the console")
        render.add_argument("--init-only", action="store_true",
                            help=_argparse.SUPPRESS)

        check_links = subparsers.add_parser("check-links")
        check_links.description = "Check for broken links"
        check_links.set_defaults(func=self.check_links_command)
        check_links.add_argument("config_dir", metavar="CONFIG-DIR",
                                 help="Read config files from CONFIG-DIR")
        check_links.add_argument("input_dir", metavar="INPUT-DIR",
                                 help="Check input files in INPUT-DIR")
        check_links.add_argument("output_dir", metavar="OUTPUT-DIR",
                                 help="Check output files in OUTPUT-DIR")
        check_links.add_argument("--all", action="store_true",
                                 help="Check external links as well as internal ones")
        check_links.add_argument("--quiet", action="store_true",
                                 help="Print no logging to the console")
        check_links.add_argument("--verbose", action="store_true",
                                 help="Print detailed logging to the console")
        check_links.add_argument("--init-only", action="store_true",
                                 help=_argparse.SUPPRESS)

        check_files = subparsers.add_parser("check-files")
        check_files.description = "Check for missing or extra files"
        check_files.set_defaults(func=self.check_files_command)
        check_files.add_argument("config_dir", metavar="CONFIG-DIR",
                                 help="Read config files from CONFIG-DIR")
        check_files.add_argument("input_dir", metavar="INPUT-DIR",
                                 help="Check input files in INPUT-DIR")
        check_files.add_argument("output_dir", metavar="OUTPUT-DIR",
                                 help="Check output files in OUTPUT-DIR")
        check_files.add_argument("--quiet", action="store_true",
                                 help="Print no logging to the console")
        check_files.add_argument("--verbose", action="store_true",
                                 help="Print detailed logging to the console")
        check_files.add_argument("--init-only", action="store_true",
                                 help=_argparse.SUPPRESS)

        self.lib = None

    def init(self):
        super().init()

        if "func" not in self.args:
            self.fail("Missing subcommand")

    def init_lib(self):
        assert self.lib is None

        self.lib = Transom(self.args.config_dir, self.args.input_dir, self.args.output_dir, home=self.home)
        self.lib.verbose = self.args.verbose
        self.lib.quiet = self.args.quiet

        self.lib.init()

        if self.args.init_only:
            _sys.exit(0)

    def run(self):
        self.args.func()

    def init_command(self):
        if self.home is None:
            self.fail("I can't find the default input files")

        def copy(file_name, to_path):
            if _os.path.exists(to_path):
                self.notice("Skipping '{}'. It already exists.", to_path)
                return

            _copy_file(_os.path.join(self.home, "files", file_name), to_path)

            self.notice("Creating '{}'", to_path)

        if self.args.init_only:
            _sys.exit(0)

        copy("default-page.html", _os.path.join(self.args.config_dir, "default-page.html"))
        copy("default-body.html", _os.path.join(self.args.config_dir, "default-body.html"))
        copy("config.py", _os.path.join(self.args.config_dir, "config.py"))

        copy("main.css", _os.path.join(self.args.input_dir, "main.css"))
        copy("main.js", _os.path.join(self.args.input_dir, "main.js"))
        copy("index.md", _os.path.join(self.args.input_dir, "index.md"))

    def render_command(self):
        self.init_lib()

        if self.args.serve is not None:
            self.lib.reload = True

        self.lib.render(force=self.args.force, serve=self.args.serve)

    def check_links_command(self):
        self.init_lib()

        link_errors = self.lib.check_links(internal=True, external=self.args.all)

        if link_errors == 0:
            print("PASSED")
        else:
            self.fail("FAILED")

    def check_files_command(self):
        self.init_lib()

        missing_files, extra_files = self.lib.check_files()

        if extra_files != 0:
            self.warn("{} extra files in the output", extra_files)

        if missing_files == 0:
            print("PASSED")
        else:
            self.fail("FAILED")

def _make_dir(path):
    _os.makedirs(path, exist_ok=True)

def _read_file(path):
    with open(path, "r") as file_:
        return file_.read()

def _write_file(path, content):
    _make_dir(_os.path.split(path)[0])
    with open(path, "w") as file_:
        return file_.write(content)

def _copy_file(from_path, to_path):
    _make_dir(_os.path.split(to_path)[0])
    with open(from_path, "rb") as from_file, open(to_path, "wb") as to_file:
        _shutil.copyfileobj(from_file, to_file, 4096)

def _eprint(*args, **kwargs):
    print(*args, file=_sys.stderr, **kwargs)

_lipsum_words = [
    "Lorem", "ipsum", "dolor", "sit", "amet,", "consectetur", "adipiscing", "elit.",
    "Vestibulum", "enim", "urna,", "ornare", "pellentesque", "felis", "eget,", "maximus", "lacinia", "lorem.",
    "Nulla", "auctor", "massa", "vitae", "ultricies", "varius.",
    "Curabitur", "consectetur", "lacus", "sapien,", "a", "lacinia", "urna", "tempus", "quis.",
    "Vestibulum", "vitae", "augue", "non", "augue", "lobortis", "semper.",
    "Nullam", "fringilla", "odio", "quis", "ligula", "consequat", "condimentum.",
    "Integer", "tempus", "sem.",
]

def _lipsum(count=50):
    words = list()

    for i in range(count):
        words.append(_lipsum_words[i % len(_lipsum_words)])

    text = " ".join(words)

    if text.endswith(","):
        text = text[:-1] + "."

    if not text.endswith("."):
        text = text + "."

    return text

def _html_table_csv(csv_path, **attrs):
    items = list()

    with open(csv_path, newline="") as f:
        reader = _csv.reader(f)

        for row in reader:
            items.append(row)

    return _html_table(items, **attrs)

def _html_table(items, column_headings=True, row_headings=False,
                escape_cell_data=False, cell_render_fn=None,
                **attrs):
    rows = list()

    if column_headings:
        headings = list()

        for cell in items[0]:
            headings.append(_html_elem("th", cell))

        rows.append(_html_elem("tr", "".join(headings)))

        items = items[1:]

    for row_index, item in enumerate(items):
        columns = list()

        for column_index, cell in enumerate(item):
            if escape_cell_data:
                cell = _xml_escape(cell)

            if cell_render_fn is not None:
                cell = cell_render_fn(row_index, column_index, cell)

            if column_index == 0 and row_headings:
                columns.append(_html_elem("th", cell))
            else:
                columns.append(_html_elem("td", cell))

        rows.append(_html_elem("tr", "".join(columns)))

    tbody = _html_elem("tbody", "\n{}\n".format("\n".join(rows)))

    return _html_elem("table", tbody, **attrs)

def _html_elem(tag, content, **attrs):
    attrs = [_html_attr(name, value) for name, value in attrs.items() if value is not False]

    if content is None:
        content = ""

    return f"<{tag} {' '.join(attrs)}>{content}</{tag}>"

def _html_attr(name, value):
    if value is True:
        value = name

    if name == "class_" or name == "_class":
        name = "class"

    return f"{name}=\"{_xml_escape(value)}\""

if __name__ == "__main__":
    command = TransomCommand()
    command.main()
