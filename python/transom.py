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
import concurrent.futures as _futures
import fnmatch as _fnmatch
import markdown2 as _markdown
import os as _os
import re as _re
import runpy as _runpy
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile
import time as _time

from collections import defaultdict as _defaultdict
from urllib.parse import urljoin as _urljoin
from urllib.parse import urlsplit as _urlsplit
from urllib.request import urlopen as _urlopen
from xml.etree.ElementTree import XML as _XML

_title_regex = _re.compile(r"<([hH][12]).*?>(.*?)</\1>")
_tag_regex = _re.compile(r"<.+?>")
_page_extensions = ".md", ".html.in", ".html", ".css", ".js"

_markdown_extras = {
    "code-friendly": True,
    "footnotes": True,
    "header-ids": True,
    "markdown-in-html": True,
    "metadata": True,
    "tables": True,
}

class Transom:
    def __init__(self, site_url, input_dir, output_dir, home=None):
        self.site_url = site_url
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.home = home

        self.verbose = False
        self.quiet = False

        self.outer_template_path = _join(self.input_dir, ".transom", "outer-template.html")
        self.inner_template_path = _join(self.input_dir, ".transom", "inner-template.html")
        self.config_path = _join(self.input_dir, ".transom", "config.py")

        self.template = None
        self.config_env = None

        self.files = list()
        self.files_by_path = dict()
        self.pages = list()

        self.links = _defaultdict(set)
        self.link_targets = set()

        self.executor = _futures.ThreadPoolExecutor()
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

        init_globals = {"site_url": self.site_url}

        if _is_file(self.config_path):
            self.config_env = _runpy.run_path(self.config_path, init_globals)
        else:
            self.config_env = init_globals

        self.start_time = _time.time()

    def find_input_files(self):
        with _Phase(self, "Finding input files"):
            self._traverse_input_files("")

            for file_ in self.files:
                file_.init()

    def _traverse_input_files(self, subdir, parent_page=None, ignore_pages=False):
        input_dir = _join(self.input_dir, subdir)
        names = set(_os.listdir(input_dir))

        if input_dir == _join(self.input_dir, ".transom"):
            return

        if "_transom_ignore_pages" in names:
            ignore_pages = True

        for name in ("index.md", "index.html", "index.html.in"):
            if name in names:
                names.remove(name)
                parent_page = _Page(self, _join(subdir, name), parent_page)
                break

        for name in sorted(names):
            if name.startswith("_transom_"):
                continue

            if name == ".svn":
                continue

            path = _join(subdir, name)
            input_path = _join(self.input_dir, path)

            if _is_file(input_path):
                if input_path.endswith(".html.in"):
                    ext = ".html.in"
                else:
                    stem, ext = _os.path.splitext(name)

                if ext in _page_extensions and not ignore_pages:
                    _Page(self, path, parent_page)
                else:
                    _File(self, path)
            elif _is_dir(input_path):
                self._traverse_input_files(path, parent_page, ignore_pages)

    def _traverse_output_files(self, subdir, files):
        output_dir = _join(self.output_dir, subdir)
        names = set(_os.listdir(output_dir))

        for name in names:
            path = _join(subdir, name)
            output_path = _join(self.output_dir, path)

            if _is_file(output_path):
                files.add(output_path)
            elif _is_dir(output_path):
                if name == ".svn":
                    continue

                if name == "transom":
                    continue

                self._traverse_output_files(path, files)

    def render(self):
        self.find_input_files()

        with _Phase(self, "Loading pages"):
            for page in self.pages:
                page.load_input()

        with _Phase(self, "Converting pages"):
            futures = [self.executor.submit(x.convert) for x in self.pages]
            _futures.wait(futures)

        with _Phase(self, "Processing pages"):
            for page in self.pages:
                page.process()

        with _Phase(self, "Rendering pages"):
            for page in self.pages:
                page.render()

        with _Phase(self, "Writing output files"):
            for file_ in self.files:
                file_.save_output()

            self._copy_default_files()

    def _copy_default_files(self):
        if self.home is None:
            return

        from_dir = _join(self.home, "files")
        to_dir = _join(self.output_dir, "transom")
        subpaths = list()

        for root, dirs, files in _os.walk(from_dir):
            dir_ = root[len(from_dir) + 1:]

            for file_ in files:
                subpaths.append(_join(dir_, file_))

        for subpath in subpaths:
            from_file = _join(from_dir, subpath)
            to_file = _join(to_dir, subpath)

            _copy_file(from_file, to_file)

    def check_files(self):
        self.find_input_files()

        with _Phase(self, "Checking output files"):
            expected_files = set()
            found_files = set()

            for file_ in self.files:
                expected_files.add(file_.output_path)

            self._traverse_output_files("", found_files)

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

    def check_links(self, internal=True, external=False):
        self.find_input_files()

        with _Phase(self, "Finding links"):
            for page in self.pages:
                page.load_output()

            for page in self.pages:
                page.find_links()

        with _Phase(self, "Checking links"):
            errors_by_link = _defaultdict(list)
            links = self.filter_links(self.links)

            for link in links:
                if internal and link.startswith(self.site_url):
                    if link[len(self.site_url):].startswith("/transom"):
                        continue

                    if link not in self.link_targets:
                        errors_by_link[link].append("Link has no target")

                if external and not link.startswith(self.site_url):
                    code, error = self.check_external_link(link)

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

    def filter_links(self, links):
        config_path = _join(self.input_dir, "_transom_ignore_links")

        if _is_file(config_path):
            ignore_patterns = _read_file(config_path).splitlines()

            def retain(link):
                for pattern in ignore_patterns:
                    pattern = pattern.strip()
                    path = link[len(self.site_url) + 1:]

                    if _fnmatch.fnmatch(path, pattern):
                        return False

                return True

            return filter(retain, links)

        return links

    def check_external_link(self, link):
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
            print("{:.<30} ".format(message + " "), end="", flush=True)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            print("FAILED")
            return

        self.end_time = _time.time()

        phase_dur = self.end_time - self.start_time
        total_dur = self.end_time - self.site.start_time

        if not self.site.verbose:
            print("{:0.3f}s [{:0.3f}s]".format(phase_dur, total_dur))

class _File:
    def __init__(self, site, path):
        self.site = site
        self.path = path

        self.input_path = _join(self.site.input_dir, self.path)
        self.output_path = _join(self.site.output_dir, self.path)
        self.url = self.site.get_url(self.output_path)

        self.input_mtime = None

        self.site.files.append(self)
        self.site.files_by_path[self.path] = self

    def init(self):
        self.input_mtime = _os.path.getmtime(self.input_path)

        self.site.link_targets.add(self.url)

        if self.url.endswith("/index.html"):
            self.site.link_targets.add(self.url[:-10])
            self.site.link_targets.add(self.url[:-11])

    def save_output(self):
        if _os.path.exists(self.output_path):
            output_mtime = _os.path.getmtime(self.output_path)

            if output_mtime < self.input_mtime:
                _copy_file(self.input_path, self.output_path)
        else:
            _copy_file(self.input_path, self.output_path)

    def __repr__(self):
        return _format_repr(self, self.path)

class _Page(_File):
    def __init__(self, site, path, parent):
        super().__init__(site, path)

        self.parent = parent

        self.content = None
        self.template = None

        self.title = None
        self.attributes = dict()

        self.site.pages.append(self)

    def init(self):
        if self.output_path.endswith(".md"):
            self.output_path = "{}.html".format(self.output_path[:-3])
        elif self.output_path.endswith(".html.in"):
            self.output_path = self.output_path[:-3]

        self.url = self.site.get_url(self.output_path)

        super().init()

    def load_input(self):
        self.site.info("Loading {}", self)
        self.content = _read_file(self.input_path)

    def save_output(self):
        self.site.info("Saving {} to {}", self, self.output_path)
        _write_file(self.output_path, self.content)

    def load_output(self):
        self.content = _read_file(self.output_path)

    def convert(self):
        if self.path.endswith(".md"):
            self.convert_from_markdown()
        elif self.path.endswith(".html.in"):
            self.convert_from_html_in()

    def convert_from_markdown(self):
        self.site.info("Converting {} from markdown", self)

        # Strip out comments
        content_lines = self.content.splitlines()
        content_lines = [x for x in content_lines if not x.startswith(";;")]

        content = _os.linesep.join(content_lines)
        content = _markdown.markdown(content, extras=_markdown_extras)

        self.attributes.update(content.metadata)

        self.content = self.apply_template(content)

    def convert_from_html_in(self):
        self.site.info("Converting {} from html.in", self)
        self.content = self.apply_template(self.content)

    def apply_template(self, content):
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
        output = template.replace("@content@", content, 1)

        return output

    def process(self):
        self.site.info("Processing {}", self)

        dir, name = _split(self.output_path)
        self.title = name

        if isinstance(self.title, bytes):
            self.title = self.title.decode("utf8")

        match = _title_regex.search(self.content)

        if match:
            self.title = match.group(2)

        self.title = _tag_regex.sub("", self.title)
        self.title = self.title.strip()

        self.title = self.attributes.get("title", self.title)

    def render(self):
        self.site.info("Rendering {}", self)

        page_vars = {
            "title": self.title,
            "path_navigation": self.render_path_navigation(),
            "extra_headers" : self.attributes.get("extra_headers", ""),
        }

        self.content = self.replace_placeholders(self.content, page_vars)

    def render_link(self):
        return u"<a href=\"{}\">{}</a>".format(self.url, self.title)

    def render_path_navigation(self):
        links = list()
        page = self.parent

        links.append(self.title)

        while page:
            links.append(page.render_link())
            page = page.parent

        links = u"".join((u"<li>{}</li>".format(x) for x in reversed(links)))

        return u"<ul id=\"-path-navigation\">{}</ul>".format(links)

    def replace_placeholders(self, content, page_vars):
        out = list()
        tokens = _re.split("({{.+?}})", content)

        for token in tokens:
            if token[:2] != "{{" or token[-2:] != "}}":
                out.append(token)
                continue

            token_content = token[2:-2]

            if page_vars and token_content in page_vars:
                out.append(page_vars[token_content])
                continue

            expr = token_content
            env = self.site.config_env

            try:
                result = eval(expr, env)
            except Exception as e:
                msg = "Expression '{}'; file '{}'; {}"
                args = expr, self.input_path, e

                print(msg.format(*args))

                out.append(token)
                continue

            if result is not None:
                out.append(str(result))

        return "".join(out)

    def find_links(self):
        if not self.output_path.endswith(".html"):
            return

        self.site.info("Finding links in {}", self)

        try:
            root = self.parse_xml(self.content)
        except Exception as e:
            self.site.warn(str(e))
            return

        links = self.gather_links(root)
        link_targets = self.gather_link_targets(root)

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

    def parse_xml(self, xml):
        try:
            return _XML(xml)
        except Exception as e:
            path = _tempfile.mkstemp(".xml")[1]
            msg = "{} fails to parse; {}; see {}".format(self, str(e), path)

            with open(path, "w") as file:
                file.write(xml)

            raise Exception(msg)

    def gather_links(self, root_elem):
        links = set()

        for elem in root_elem.iter("*"):
            for name in ("href", "src", "action"):
                try:
                    link = elem.attrib[name]
                except KeyError:
                    continue

                links.add(link)

        return links

    def gather_link_targets(self, root_elem):
        link_targets = set()

        for elem in root_elem.iter("*"):
            try:
                id = elem.attrib["id"]
            except KeyError:
                continue

            target = "{}#{}".format(self.url, id)

            if target in link_targets:
                self.site.warn("Duplicate link target in '{}'", target)

            link_targets.add(target)

        return link_targets

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
                          help="Place standard input files in INPUT-DIR")

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
        assert self.lib is None

        super().init()

        if "func" not in self.args:
            print("Error! Missing subcommand", file=_sys.stderr)
            _sys.exit(1)

    def init_lib(self):
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
            self.fail("Home is not set")

        source_dir = _join(self.home, "files")
        config_dir = _join(self.args.input_dir, ".transom")

        def copy(file_name, to_path):
            if _os.path.exists(to_path):
                return

            _copy_file(_join(source_dir, file_name), to_path)

            print(to_path)

        copy("outer-template.html", _join(config_dir, "outer-template.html"))
        copy("inner-template.html", _join(config_dir, "inner-template.html"))
        copy("config.py", _join(config_dir, "config.py"))

        copy("site.css", _join(self.args.input_dir, "site.css"))
        copy("site.js", _join(self.args.input_dir, "site.js"))
        copy("index.md", _join(self.args.input_dir, "index.md"))

    def render_command(self):
        self.init_lib()
        self.lib.render()

    def check_links_command(self):
        self.init_lib()
        self.lib.check_links(internal=True, external=self.args.all)

    def check_files_command(self):
        self.init_lib()
        self.lib.check_files()

_join = _os.path.join
_split = _os.path.split
_is_file = _os.path.isfile
_is_dir = _os.path.isdir

def _make_dir(dir):
    if not _os.path.exists(dir):
        _os.makedirs(dir)

def _read_file(path):
    with open(path, "r") as file:
        return file.read()

def _write_file(path, content):
    _make_dir(_split(path)[0])

    with open(path, "w") as file:
        return file.write(content)

def _copy_file(from_path, to_path):
    _make_dir(_split(to_path)[0])
    _shutil.copy(from_path, to_path)

def _format_repr(obj, *args):
    cls = obj.__class__.__name__
    strings = [str(x) for x in args]
    return "{}({})".format(cls, ",".join(strings))
