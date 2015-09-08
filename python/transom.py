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
import importlib as _importlib
import markdown2 as _markdown2
import os as _os
import re as _re
import sys as _sys
import tempfile as _tempfile

from collections import defaultdict as _defaultdict
from xml.etree.ElementTree import XML as _XML

try:
    from urllib.request import urlopen as _urlopen
except:
    from urllib2 import urlopen as _urlopen

try:
    from urllib.parse import urlsplit as _urlsplit
except:
    from urlparse import urlsplit as _urlsplit

try:
    from urllib.parse import urljoin as _urljoin
except:
    from urlparse import urljoin as _urljoin

try:
    from configparser import SafeConfigParser as _SafeConfigParser
except:
    from ConfigParser import SafeConfigParser as _SafeConfigParser

_title_regex = _re.compile(r"<([hH][12]).*?>(.*?)</\1>")
_tag_regex = _re.compile(r"<.+?>")
_page_extensions = ".md", ".html.in", ".html", ".css", ".jss"
_buffer_size = 128 * 1024

class Transom:
    def __init__(self, home_dir, site_url, input_dir, output_dir):
        self.home_dir = home_dir
        self.site_url = site_url
        self.input_dir = input_dir
        self.output_dir = output_dir

        self.verbose = False

        self.config_path = _os.path.join(self.input_dir, "_config.ini")
        self.template_path = _os.path.join(self.input_dir, "_template.html")
        self.python_module_path = _os.path.join(self.input_dir, "_module.py")

        extras = {
            "code-friendly": True,
            "tables": True,
            "wiki-tables": True,
            "header-ids": True,
            "markdown-in-html": True,
            }

        self.markdown = _markdown2.Markdown(extras=extras)

        self.config_parser = _SafeConfigParser()
        self.config_vars = dict()

        self.template_content = None
        self.python_module = None
        
        self.files = list()
        self.files_by_input_path = dict()

        self.resources = list()
        self.pages = list()

        self.links = _defaultdict(set)
        self.targets = set()

    def init(self):
        self.config_vars["site-url"] = self.site_url

        if _os.path.isfile(self.config_path):
            self.config_parser.read(self.config_path)
            items = self.config_parser.items("main", vars=self.config_vars)
            self.config_vars.update(items)

        if not _os.path.isfile(self.template_path):
            path = _os.path.join(self.home_dir, "resources", "template.html")
            self.template_path = path

        with _open_file(self.template_path, "r") as file:
            self.template_content = file.read()

        if _os.path.isfile(self.python_module_path):
            _sys.path.append(self.input_dir)
            self.python_module = _importlib.import_module("_module")
            
            import pprint
            pprint.pprint(vars(self.python_module))
                
        self.traverse_input_pages(self.input_dir, None)
        self.traverse_input_resources(self.input_dir)

        for file in self.files:
            file.init()

    def render(self):
        for page in self.pages:
            page.load_input()

        for page in self.pages:
            page.convert()

        for page in self.pages:
            page.process()

        for page in self.pages:
            page.render()

        for page in self.pages:
            page.save_output()

        for resource in self.resources:
            resource.save_output()

        self.copy_default_resources()

    def copy_default_resources(self):
        from_dir = _os.path.join(self.home_dir, "resources")
        to_dir = _os.path.join(self.output_dir, "transom")
        subpaths = list()

        for root, dirs, files in _os.walk(from_dir):
            dir = root[len(from_dir) + 1:]

            for file in files:
                subpaths.append(_os.path.join(dir, file))

        for subpath in subpaths:
            from_file = _os.path.join(from_dir, subpath)
            to_file = _os.path.join(to_dir, subpath)
            parent_dir = _os.path.dirname(to_file)

            if not _os.path.exists(parent_dir):
                _make_dirs(parent_dir)

            _copy_file(from_file, to_file)

    def check_output_files(self):
        expected_files = set()
        found_files = set()

        for file in self.files:
            expected_files.add(file.output_path)

        self.traverse_output_files(self.output_dir, found_files)

        missing_files = expected_files.difference(found_files)
        extra_files = found_files.difference(expected_files)

        if missing_files:
            print("Missing files:")

            for path in sorted(missing_files):
                print("  {}".format(path))

        if extra_files:
            print("Extra files:")

            for path in sorted(extra_files):
                print("  {}".format(path))

    def traverse_output_files(self, dir, files):
        names = set(_os.listdir(dir))

        for name in names:
            path = _os.path.join(dir, name)

            if _os.path.isfile(path):
                files.add(path)
            elif _os.path.isdir(path) and name != ".svn":
                self.traverse_output_files(path, files)

    def check_links(self, internal=True, external=False):
        for page in self.pages:
            page.load_output()

        for page in self.pages:
            page.check_links()

        errors_by_link = _defaultdict(list)

        for link in self.links:
            if internal and link.startswith(self.site_url):
                if link not in self.targets:
                    errors_by_link[link].append("Link has no target")

            if external and not link.startswith(self.site_url):
                code, error = self.check_external_link(link)
            
                if code >= 400:
                    msg = "HTTP error code {}".format(code)
                    errors_by_link[link].append(msg)

                if error:
                    errors_by_link[link].append(error.message)

            _sys.stdout.write(".")
            _sys.stdout.flush()

        print()

        for link in errors_by_link:
            print("Link: {}".format(link))

            for error in errors_by_link[link]:
                print("  Error: {}".format(error))

            for source in self.links[link]:
                print("  Source: {}".format(source))

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

    def traverse_input_pages(self, dir, page):
        names = set(_os.listdir(dir))

        if ".transom-skip" in names:
            return

        for name in ("index.md", "index.html", "index.html.in"):
            if name in names:
                names.remove(name)
                page = _Page(self, _os.path.join(dir, name), page)
                break

        for name in sorted(names):
            path = _os.path.join(dir, name)

            if path in (self.config_path, self.template_path):
                continue

            if _os.path.isfile(path):
                for extension in _page_extensions:
                    if name.endswith(extension):
                        _Page(self, path, page)
                        break
            elif _os.path.isdir(path) and name != ".svn":
                self.traverse_input_pages(path, page)

    def traverse_input_resources(self, dir):
        names = set(_os.listdir(dir))

        for name in sorted(names):
            path = _os.path.join(dir, name)

            if path in (self.config_path, self.template_path):
                continue

            if _os.path.isfile(path):
                if path not in self.files_by_input_path:
                    _Resource(self, path)
            elif _os.path.isdir(path) and name != ".svn":
                self.traverse_input_resources(path)

    def get_output_path(self, input_path):
        path = input_path[len(self.input_dir) + 1:]
        return _os.path.join(self.output_dir, path)

    def get_url(self, output_path):
        path = output_path[len(self.output_dir) + 1:]
        path = path.replace(_os.path.sep, "/")
        return "{}/{}".format(self.site_url, path)

class _File(object):
    def __init__(self, site, input_path):
        self.site = site
        self.input_path = input_path
        self.output_path = self.site.get_output_path(self.input_path)
        self.url = self.site.get_url(self.output_path)

        self.site.files.append(self)
        self.site.files_by_input_path[self.input_path] = self

    def init(self):
        self.site.targets.add(self.url)

    def replace_placeholders(self, content):
        out = list()
        tokens = _re.split("({{.+?}})", content)

        for token in tokens:
            if token.startswith("{{") and token.endswith("}}"):
                code = token[2:-2]

                try:
                    result = eval(code, vars(self.site.python_module), vars(self.site.python_module))
                except Exception as e:
                    msg = "Failed evaluating '{}' in file '{}'; {}".format \
                          (token, self.input_path, e)
                    raise Exception(msg)

                if result is not None:
                    out.append(str(result))
            else:
                out.append(token)

        return "".join(out)

    def __repr__(self):
        return _repr(self, self.input_path)

class _Resource(_File):
    def __init__(self, site, input_path):
        super(_Resource, self).__init__(site, input_path)

        self.site.resources.append(self)

    def save_output(self):
        _make_dirs(_os.path.dirname(self.output_path))
        _copy_file(self.input_path, self.output_path)

class _Page(_File):
    def __init__(self, site, input_path, parent):
        super(_Page, self).__init__(site, input_path)

        self.parent = parent

        self.content = None
        self.title = None

        self.site.pages.append(self)

    def init(self):
        if self.output_path.endswith(".md"):
            self.output_path = "{}.html".format(self.output_path[:-3])
        elif self.output_path.endswith(".html.in"):
            self.output_path = self.output_path[:-3]

        self.url = self.site.get_url(self.output_path)

        super(_Page, self).init()

    def load_input(self):
        if self.site.verbose:
            print("Loading {}".format(self))

        with _open_file(self.input_path, "r") as file:
            self.content = file.read()

    def save_output(self, path=None):
        if self.site.verbose:
            print("Saving {} to {}".format(self, self.output_path))

        if path is None:
            path = self.output_path

        _make_dirs(_os.path.dirname(path))

        with _open_file(self.output_path, "w") as file:
            file.write(self.content)

    def load_output(self):
        with _open_file(self.output_path, "r") as file:
            self.content = file.read()

    def convert(self):
        if self.input_path.endswith(".md"):
            self.convert_from_markdown()
        elif self.input_path.endswith(".html.in"):
            self.convert_from_html_in()

    def convert_from_markdown(self):
        if self.site.verbose:
            print("Converting {} from markdown".format(self))

        # Strip out comments
        content_lines = self.content.splitlines()
        content_lines = (x for x in content_lines if not x.startswith(";;"))

        content = _os.linesep.join(content_lines)
        content = self.site.markdown.convert(content)

        self.content = self.apply_template(content)

    def convert_from_html_in(self):
        if self.site.verbose:
            print("Converting {} from html.in".format(self))

        self.content = self.apply_template(self.content)

    def apply_template(self, content):
        return self.site.template_content.replace("{{content}}", content)

    def process(self):
        if self.site.verbose:
            print("Processing {}".format(self))

        if self.parent is None:
            self.title = "Home"
            return

        self.title = _os.path.split(self.output_path)[1]

        if isinstance(self.title, bytes):
            self.title = self.title.decode("utf8")

        match = _title_regex.search(self.content)

        if match:
            self.title = match.group(2)

        self.title = _tag_regex.sub("", self.title)
        self.title = self.title.strip()

    def render(self):
        if self.site.verbose:
            print("Rendering {}".format(self))

        path_nav = self.render_path_navigation()

        self.content = self.content.replace("{{path_navigation}}", path_nav)
        self.content = self.content.replace("{{title}}", self.title)
        self.content = self.content.replace("{{site_url}}", self.site.site_url)

        self.content = self.replace_placeholders(self.content)

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

    def check_links(self):
        if not self.output_path.endswith(".html"):
            return

        try:
            root = self.parse_xml(self.content)
        except Exception as e:
            print("Warning: {}".format(str(e)))
            return

        links = self.gather_links(root)
        targets = self.gather_targets(root)

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

        self.site.targets.update(targets)

    def parse_xml(self, xml):
        try:
            return _XML(xml)
        except Exception as e:
            path = _tempfile.mkstemp(".xml")[1]
            msg = "{} fails to parse; {}; see {}".format(self, str(e), path)

            with _open_file(path, "w") as file:
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

    def gather_targets(self, root_elem):
        targets = set()

        for elem in root_elem.iter("*"):
            try:
                id = elem.attrib["id"]
            except KeyError:
                continue

            target = "{}#{}".format(self.url, id)

            assert target not in targets, target

            targets.add(target)

        return targets

def _make_dirs(dir):
    if not _os.path.exists(dir):
        _os.makedirs(dir)

def _open_file(path, mode):
    return _codecs.open(path, mode, "utf8", "replace", _buffer_size)

# Adapted from http://stackoverflow.com/questions/22078621/python-how-to-copy-files-fast

_read_flags = _os.O_RDONLY
_write_flags = _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC
_eof = b""

def _copy_file(src, dst):
    try:
        fin = _os.open(src, _read_flags)
        fout = _os.open(dst, _write_flags)

        for x in iter(lambda: _os.read(fin, _buffer_size), _eof):
            _os.write(fout, x)
    finally:
        _os.close(fin)
        _os.close(fout)

def _repr(obj, *args):
    cls = obj.__class__.__name__
    strings = [str(x) for x in args]
    return "{}({})".format(cls, ",".join(strings))
