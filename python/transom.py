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

import codecs as _codecs
import commandant as _commandant
import fnmatch as _fnmatch
import markdown2 as _markdown
import os as _os
import re as _re
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile
import time as _time

from collections import defaultdict as _defaultdict
from urllib.parse import urljoin as _urljoin
from urllib.parse import urlsplit as _urlsplit
from urllib.request import urlopen as _urlopen
from xml.etree.ElementTree import XML as _XML

_html_title_regex = _re.compile(r"<([hH][12]).*?>(.*?)</\1>")
_html_tag_regex = _re.compile(r"<.+?>")

_markdown_title_regex = _re.compile(r"(#|##)(.+)")

_markdown_extras = {
    "code-friendly": True,
    "footnotes": True,
    "header-ids": True,
    "markdown-in-html": True,
    "metadata": True,
    "tables": True,
}

_variable_regex = _re.compile("({{.+?}})")

class Transom:
    def __init__(self, site_url, input_dir, output_dir, home=None):
        self.site_url = site_url
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.home = home

        self.verbose = False
        self.quiet = False

        self.config_dir = _join(self.input_dir, ".transom")
        self.config_file = _join(self.config_dir, "config.py")
        self.config = None

        self.outer_template_path = _join(self.config_dir, "outer-template.html")
        self.inner_template_path = _join(self.config_dir, "inner-template.html")

        self.input_files = list()
        self.output_files = list()
        self.config_files = list()

        self.links = _defaultdict(set)
        self.link_targets = set()

        self.ignored_file_patterns = [
            "*/.git",
            "*/.svn",
        ]

        self.ignored_link_patterns = list()

        self._markdown_converter = _markdown.Markdown(extras=_markdown_extras)

        self.start_time = None

    def init(self):
        if self.home is not None:
            if not _is_file(self.outer_template_path):
                self.outer_template_path = _join(self.home, "files", "outer-template.html")

            if not _is_file(self.inner_template_path):
                self.inner_template_path = _join(self.home, "files", "inner-template.html")

        if not _is_file(self.outer_template_path):
            raise Exception("No outer template found")

        if not _is_file(self.inner_template_path):
            raise Exception("No inner template found")

        self.outer_template = _read_file(self.outer_template_path)
        self.inner_template = _read_file(self.inner_template_path)

        self.config = {
            "site_url": self.site_url,
            "ignored_files": self.ignored_file_patterns,
            "ignored_links": self.ignored_link_patterns,
        }

        if _is_file(self.config_file):
            exec(_read_file(self.config_file), self.config)

        self.start_time = _time.time()

    def find_input_files(self):
        with _Phase(self, "Finding input files"):
            input_files = list()

            for root, dirs, files in _os.walk(self.input_dir):
                for file_ in files:
                    input_files.append(_join(root, file_))

            return input_files

    def init_input_files(self, input_paths):
        with _Phase(self, "Initializing input files"):
            for input_path in input_paths:
                if not self._is_ignored_file(input_path):
                    self._create_file(input_path)

            for file_ in self.input_files:
                file_.init()

        index_files = dict()
        other_files = _defaultdict(list)

        for file_ in self.output_files:
            path = file_.output_path[len(self.output_dir):]
            dir_, name = _split(path)

            if name == "index.html":
                index_files[dir_] = file_
            else:
                other_files[dir_].append(file_)

        for dir_ in index_files:
            parent_dir = _split(dir_)[0]

            if parent_dir == "/":
                continue

            file_ = index_files[dir_]
            file_.parent = index_files.get(parent_dir)

        for dir_ in other_files:
            parent = index_files.get(dir_)

            for file_ in other_files[dir_]:
                file_.parent = parent

    def _is_ignored_file(self, input_path):
        path = input_path[len(self.input_dir):]

        for pattern in self.ignored_file_patterns:
            if _fnmatch.fnmatch(path, pattern):
                return True

        return False

    def _create_file(self, input_path):
        config_dir = _join(self.input_dir, ".transom")

        if input_path.startswith(config_dir):
            return _ConfigFile(self, input_path)

        if input_path.endswith(".html.in"):
            ext = ".html.in"
        else:
            ext = _os.path.splitext(input_path)[1]

        if   ext == ".md":      return _MarkdownFile(self, input_path)
        elif ext == ".css":     return _CssFile(self, input_path)
        elif ext == ".html.in": return _HtmlInFile(self, input_path)
        elif ext == ".js":      return _JavaScriptFile(self, input_path)
        else:                   return _StaticFile(self, input_path)

    def render(self):
        input_file_paths = self.find_input_files()

        self.init_input_files(input_file_paths)

        print("  Input files        {:>10,}".format(len(self.input_files)))
        print("  Output files       {:>10,}".format(len(self.output_files)))
        print("  Config files       {:>10,}".format(len(self.config_files)))

        with _Phase(self, "Processing input files"):
            for file_ in self.input_files:
                file_.process_input()

        force = any([x.modified() for x in self.config_files])

        with _Phase(self, "Rendering output files"):
            for file_ in self.output_files:
                file_.render_output(force)

        _os.utime(self.output_dir)

    def check_files(self):
        input_file_paths = self.find_input_files()

        self.init_input_files(input_file_paths)

        with _Phase(self, "Checking output files"):
            expected_files = set()
            found_files = set()

            for file_ in self.output_files:
                expected_files.add(file_.output_path)

            found_files = self._find_output_files()

            missing_files = expected_files.difference(found_files)
            extra_files = found_files.difference(expected_files)

        if missing_files:
            print("Missing output files:")

            for path in sorted(missing_files):
                print("  {}".format(path))

        if extra_files:
            print("Extra output files:")

            for path in sorted(extra_files):
                print("  {}".format(path))

    def _find_output_files(self):
        output_files = set()

        for root, dirs, files in _os.walk(self.output_dir):
            for file_ in files:
                output_files.add(_join(root, file_))

        return output_files

    def check_links(self, internal=True, external=False):
        input_file_paths = self.find_input_files()

        self.init_input_files(input_file_paths)

        with _Phase(self, "Finding links"):
            for file_ in self.output_files:
                file_.find_links()

        with _Phase(self, "Checking links"):
            errors_by_link = _defaultdict(list)
            links = self._filter_links(self.links)

            for link in links:
                if internal and link.startswith(self.site_url):
                    if link not in self.link_targets:
                        errors_by_link[link].append("Link has no target")

                if external and not link.startswith(self.site_url):
                    code, error = self._check_external_link(link)

                    if code >= 400:
                        msg = "HTTP error code {}".format(code)
                        errors_by_link[link].append(msg)

                    if error:
                        errors_by_link[link].append(error.message)

        for link in errors_by_link:
            print("Link: {}".format(link))

            for error in errors_by_link[link]:
                print("  Error: {}".format(error))

            for source in self.links[link]:
                print("  Source: {}".format(source))

    def _filter_links(self, links):
        def retain(link):
            for pattern in self.ignored_link_patterns:
                path = link[len(self.site_url):]

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
        path = output_path[len(self.output_dir) + 1:]
        path = path.replace(_os.path.sep, "/")

        return "{}/{}".format(self.site_url, path)

    def info(self, message, *args):
        if self.verbose:
            print(message.format(*args))

    def notice(self, message, *args):
        if not self.quiet:
            print(message.format(*args))

    def warn(self, message, *args):
        message = message.format(*args)
        print("Warning! {}".format(message))

class _Phase:
    def __init__(self, site, message, *args):
        self.site = site
        self.message = message
        self.args = args

        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = _time.time()

        if not self.site.verbose:
            message = self.message.format(*self.args)
            print("{:.<40} ".format(message + " "), end="", flush=True)

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.site.verbose and exc_type is not None:
            print("FAILED")
            return

        self.end_time = _time.time()

        phase_dur = self.end_time - self.start_time
        total_dur = self.end_time - self.site.start_time

        if not self.site.verbose:
            print("{:0.3f}s [{:0.3f}s]".format(phase_dur, total_dur))

class _InputFile:
    __slots__ = "site", "input_path", "input_mtime", "parent"

    def __init__(self, site, input_path):
        self.site = site

        self.input_path = input_path
        self.input_mtime = None

        self.parent = None

        self.site.input_files.append(self)

    def __repr__(self):
        path = self.input_path[len(self.site.input_dir) + 1:]
        return _format_repr(self, path)

    def init(self):
        self.input_mtime = _os.path.getmtime(self.input_path)

    def process_input(self):
        pass

    def _load_input(self):
        self.site.info("Loading {}", self)
        self.content = _read_file(self.input_path)

class _ConfigFile(_InputFile):
    __slots__ = "output_mtime",

    def __init__(self, site, input_path):
        super().__init__(site, input_path)

        self.output_mtime = None

        self.site.config_files.append(self)

    def modified(self):
        if self.output_mtime is None:
            try:
                self.output_mtime = _os.path.getmtime(self.site.output_dir)
            except FileNotFoundError:
                return True

        return self.input_mtime > self.output_mtime

class _OutputFile(_InputFile):
    __slots__ = "output_path", "output_mtime", "content", "template", "parent", \
                "url", "title", "attributes"

    def __init__(self, site, input_path):
        super().__init__(site, input_path)

        path = self.input_path[len(self.site.input_dir) + 1:]

        self.output_path = _join(self.site.output_dir, path)
        self.output_mtime = None

        self.content = None
        self.template = None

        self.parent = None
        self.url = None
        self.title = None
        self.attributes = dict()

        self.site.output_files.append(self)

    def init(self):
        super().init()

        self.url = self.site.get_url(self.output_path)

        self.site.link_targets.add(self.url)

        if self.url.endswith("/index.html"):
            self.site.link_targets.add(self.url[:-10])
            self.site.link_targets.add(self.url[:-11])

    def process_input(self):
        self.site.info("Processing {}", self)
        self._load_input()

    def modified(self):
        if self.output_mtime is None:
            try:
                self.output_mtime = _os.path.getmtime(self.output_path)
            except FileNotFoundError:
                return True

        return self.input_mtime > self.output_mtime

    def render_output(self, force=False):
        raise NotImplementedError()

    def _apply_template(self):
        outer_template = self.site.outer_template
        inner_template = self.site.inner_template

        if "outer_template" in self.attributes:
            outer_template_path = self.attributes["outer_template"]

            if _is_file(outer_template_path):
                outer_template = _read_file(outer_template_path)
            else:
                raise Exception("Outer template {} not found".format(outer_template_path))

        if "inner_template" in self.attributes:
            inner_template_path = self.attributes["inner_template"]

            if inner_template_path == "none":
                inner_template = "@content@"
            elif _is_file(inner_template_path):
                inner_template = _read_file(inner_template_path)
            else:
                raise Exception("Inner template {} not found".format(inner_template_path))

        extra_headers = self.attributes.get("extra_headers", "")

        template = outer_template.replace("@inner_template@", inner_template, 1)
        template = template.replace("@extra_headers@", extra_headers, 1)

        self.content = template.replace("@content@", self.content, 1)

    def _replace_variables(self):
        self.site.info("Replacing variables in {}", self)

        page_vars = {
            "title": self.title if self.title is not None else "[none]",
            "path_navigation": self._render_path_navigation(),
        }

        out = list()
        tokens = _variable_regex.split(self.content)

        for token in tokens:
            if token[:2] != "{{" or token[-2:] != "}}":
                out.append(token)
                continue

            token_content = token[2:-2]

            if page_vars and token_content in page_vars:
                out.append(page_vars[token_content])
                continue

            expr = token_content

            try:
                result = eval(expr, self.site.config)
            except Exception as e:
                msg = "Expression '{}'; file '{}'; {}"
                args = expr, self.input_path, e

                print(msg.format(*args))

                out.append(token)
                continue

            if result is not None:
                out.append(str(result))

        self.content = "".join(out)

    def _render_link(self):
        return "<a href=\"{}\">{}</a>".format(self.url, self.title)

    def _render_path_navigation(self):
        links = list()
        file_ = self

        while file_ is not None:
            links.append(file_._render_link())
            file_ = file_.parent

        links = "".join(reversed(links))

        return "<nav id=\"-path-navigation\">{}</nav>".format(links)

    def _save_output(self):
        self.site.info("Saving {}", self)
        _write_file(self.output_path, self.content)

    def find_links(self):
        if not self.output_path.endswith(".html"):
            return

        self.site.info("Finding links in {}", self)

        self._load_output()

        try:
            root = _XML(self.content)
        except Exception as e:
            self.site.info(str(e))
            return

        assert root is not None, self.content

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

            self.site.links[link].add(self.url)

        self.site.link_targets.update(link_targets)

    def _load_output(self):
        self.content = _read_file(self.output_path)

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

            target = "{}#{}".format(self.url, id)

            if target in link_targets:
                self.site.info("Duplicate link target in '{}'", target)

            link_targets.add(target)

        return link_targets

class _CssFile(_OutputFile):
    __slots__ = ()

    def render_output(self, force=False):
        if self.modified() or force:
            self.site.info("Rendering {}", self)

            self._replace_variables()
            self._save_output()

class _JavaScriptFile(_OutputFile):
    __slots__ = ()

    def render_output(self, force=False):
        if self.modified() or force:
            self.site.info("Rendering {}", self)

            self._replace_variables()
            self._save_output()

class _HtmlInFile(_OutputFile):
    __slots__ = ()

    def __init__(self, site, input_path):
        super().__init__(site, input_path)

        self.output_path = self.output_path[:-3]

    def process_input(self):
        super().process_input()

        match = _html_title_regex.search(self.content)

        if match:
            self.title = match.group(2).strip()
            self.title = _html_tag_regex.sub("", self.title)

    def render_output(self, force=False):
        if self.modified() or force:
            self.site.info("Converting {} to HTML", self)

            self._apply_template()
            self._replace_variables()
            self._save_output()

class _MarkdownFile(_OutputFile):
    __slots__ = ()

    def __init__(self, site, input_path):
        super().__init__(site, input_path)

        self.output_path = "{}.html".format(self.output_path[:-3])

    def process_input(self):
        super().process_input()

        match = _markdown_title_regex.search(self.content)

        if match:
            self.title = match.group(2).strip()

    def render_output(self, force=False):
        if self.modified() or force:
            self.site.info("Rendering {}", self)

            # Strip out comments
            content_lines = self.content.splitlines()
            content_lines = [x for x in content_lines if not x.startswith(";;")]

            self.content = _os.linesep.join(content_lines)
            self.content = self.site._markdown_converter.convert(self.content)

            self.attributes.update(self.content.metadata)

            self._apply_template()
            self._replace_variables()
            self._save_output()

class _StaticFile(_OutputFile):
    __slots__ = ()

    def process_input(self):
        pass

    def render_output(self, force=False):
        if self.modified() or force:
            self.site.info("Saving {}", self)
            _copy_file(self.input_path, self.output_path)

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
        super().__init__(home, "transom")

        self.description = _description
        self.epilog = _epilog

        self.add_argument("--site-url", metavar="URL",
                          help="Prefix site links with URL")

        subparsers = self.add_subparsers()

        init = subparsers.add_parser("init")
        init.description = "Prepare an input directory"
        init.set_defaults(func=self.init_command)
        init.add_argument("input_dir", metavar="INPUT-DIR",
                          help="Place default input files in INPUT-DIR")

        render = subparsers.add_parser("render")
        render.description = "Generate the output files"
        render.set_defaults(func=self.render_command)
        render.add_argument("input_dir", metavar="INPUT-DIR",
                            help="Read input files from INPUT-DIR")
        render.add_argument("output_dir", metavar="OUTPUT-DIR",
                            help="Write output files to OUTPUT-DIR")

        check_links = subparsers.add_parser("check-links")
        check_links.description = "Check for broken links"
        check_links.set_defaults(func=self.check_links_command)
        check_links.add_argument("input_dir", metavar="INPUT-DIR",
                                 help="Check input files in INPUT-DIR")
        check_links.add_argument("output_dir", metavar="OUTPUT-DIR",
                                 help="Check output files in OUTPUT-DIR")
        check_links.add_argument("--all", action="store_true",
                                 help="Check external links as well as internal ones")

        check_files = subparsers.add_parser("check-files")
        check_files.description = "Check for missing or extra files"
        check_files.set_defaults(func=self.check_files_command)
        check_files.add_argument("input_dir", metavar="INPUT-DIR",
                                 help="Check input files in INPUT-DIR")
        check_files.add_argument("output_dir", metavar="OUTPUT-DIR",
                                 help="Check output files in OUTPUT-DIR")

        self.lib = None

    def init(self):
        super().init()

        if "func" not in self.args:
            self.fail("Missing subcommand")

        if self.args.func != self.init_command:
            self.init_lib()

    def init_lib(self):
        assert self.lib is None

        site_url = self.args.site_url

        if site_url is None:
            site_url = "file:{}".format(_os.path.abspath(self.args.output_dir))

        self.lib = Transom(site_url, self.args.input_dir, self.args.output_dir, self.home)
        self.lib.verbose = self.args.verbose
        self.lib.quiet = self.args.quiet

        self.lib.init()

    def run(self):
        self.args.func()

    def init_command(self):
        if self.home is None:
            self.fail("I can't find the default input files")

        def copy(file_name, to_path):
            if _exists(to_path):
                self.notice("Skipping '{}'. It already exists.", to_path)
                return

            _copy_file(_join(self.home, "files", file_name), to_path)

            self.notice("Creating '{}'", to_path)

        config_dir = _join(self.args.input_dir, ".transom")

        copy("outer-template.html", _join(config_dir, "outer-template.html"))
        copy("inner-template.html", _join(config_dir, "inner-template.html"))
        copy("config.py", _join(config_dir, "config.py"))

        copy("site.css", _join(self.args.input_dir, "site.css"))
        copy("site.js", _join(self.args.input_dir, "site.js"))
        copy("index.md", _join(self.args.input_dir, "index.md"))

    def render_command(self):
        self.lib.render()

    def check_links_command(self):
        self.lib.check_links(internal=True, external=self.args.all)

    def check_files_command(self):
        self.lib.check_files()

_join = _os.path.join
_split = _os.path.split
_exists = _os.path.exists
_is_file = _os.path.isfile
_is_dir = _os.path.isdir

def _make_dir(path):
    _os.makedirs(path, exist_ok=True)

def _read_file(path):
    with open(path, "r") as file_:
        return file_.read()

def _write_file(path, content):
    _os.makedirs(_split(path)[0], exist_ok=True)
    with open(path, "w") as file_:
        return file_.write(content)

def _copy_file(from_path, to_path):
    _os.makedirs(_split(to_path)[0], exist_ok=True)
    with open(from_path, "rb") as from_:
        with open(to_path, "wb") as to_:
            _shutil.copyfileobj(from_, to_, 4096)

def _format_repr(obj, *args):
    cls = obj.__class__.__name__
    strings = [str(x) for x in args]
    return "{}({})".format(cls, ",".join(strings))

def _eprint(*args, **kwargs):
    kwargs["file"] = _sys.stderr
    print(*args, **kwargs)

def _pprint(*args, **kwargs):
    import pprint as _pprint
    kwargs["stream"] = _sys.stderr
    _pprint.pprint(*args, **kwargs)
