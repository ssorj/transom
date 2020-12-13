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

import csv as _csv

from plano import *
from transom import _lipsum, _html_table, _html_table_csv
from xml.etree.ElementTree import XML as _XML

_test_site_dir = get_absolute_path("test-site")
_result_file = "output/result.json"

class _test_site(working_dir):
    def __enter__(self):
        dir = super(_test_site, self).__enter__()
        copy(_test_site_dir, ".", inside=False, symlinks=False)
        return dir

def open_test_session(session):
    enable_logging(level="error")

    if session.module.command.verbose:
        enable_logging(level="notice")

def test_command_options(session):
    run("transom --help")

def test_command_init(session):
    run("transom init --help")
    run("transom init --init-only --verbose config input")

    with working_dir():
        run("transom init config input")

        assert is_dir("config"), list_dir()
        assert is_dir("input"), list_dir()
        assert is_file("config/config.py"), list_dir("config")
        assert is_file("input/index.md"), list_dir("input")
        assert is_file("input/main.css"), list_dir("input")
        assert is_file("input/main.js"), list_dir("input")

        run("transom init config input") # Re-init

def test_command_render(session):
    run("transom render --help")
    run("transom render --init-only --quiet config input output")

    with _test_site():
        run("transom render config input output")

        assert is_dir("output"), list_dir()
        assert is_file("output/index.html"), list_dir("output")
        assert is_file("output/test-1.html"), list_dir("output")
        assert is_file("output/test-2.html"), list_dir("output")
        assert is_file("output/main.css"), list_dir("output")
        assert is_file("output/main.js"), list_dir("output")

        result = read("output/index.html")
        assert "<title>Doorjamb</title>" in result, result
        assert "<h1 id=\"doorjamb\">Doorjamb</h1>" in result, result

        run("transom render config input output")
        run("transom render --force config input output")

def test_command_check_links(session):
    run("transom check-links --help")
    run("transom check-links --init-only --verbose config input output")

    with _test_site():
        run("transom render config input output")
        run("transom check-links config input output")

        append(join("a", "index.md"), "[Not there](not-there.html)")

        run("transom check-links config input output")

def test_command_check_files(session):
    run("transom check-files --help")
    run("transom check-files --init-only --quiet config input output")

    with _test_site():
        run("transom render config input output")

        remove(join("input", "test-page-1.md")) # An extra output file
        remove(join("output", "test-page-2.html")) # A missing output file

        run("transom check-files config input output")

def test_target_render(session):
    with _test_site():
        PlanoCommand().main(["render"])

        result = read_json(_result_file)
        assert result["rendered"], result

# def test_target_serve(session):
#     with _test_site():
#         PlanoCommand().main(["render", "--serve"])

#         result = read_json(_result_file)
#         assert result["served"], result

def test_target_check_links(session):
    with _test_site():
        PlanoCommand().main(["check-links"])

        result = read_json(_result_file)
        assert result["links_checked"], result

def test_target_check_files(session):
    with _test_site():
        PlanoCommand().main(["check-files"])

        result = read_json(_result_file)
        assert result["files_checked"], result

def test_target_clean(session):
    with _test_site():
        PlanoCommand().main(["clean"])

def test_target_modules(session):
    with _test_site():
        try:
            PlanoCommand().main(["modules", "--remote", "--recursive"])
            assert False
        except PlanoException:
            pass

def test_configure_file(session):
    with working_dir():
        input_file = write("zeta-file", "X@replace-me@X")
        output_file = configure_file(input_file, "zeta-file", {"replace-me": "Y"})
        output = read(output_file)
        assert output == "XYX", output

def test_lipsum_function(session):
    result = _lipsum(0, end="")
    assert result == "", result

    result = _lipsum(1)
    assert result == "Lorem."

    result = _lipsum(1000)
    assert result

def test_html_table_functions(session):
    data = (
        (1, 2, 3),
        ("a", "b", "c"),
        (None, "", 0),
    )

    _XML(_html_table(data))
    _XML(_html_table(data, headings=("A", "B", "C")))

    with working_dir():
        with open("test.csv", "w", newline="") as f:
            writer = _csv.writer(f)
            writer.writerows(data)

        _XML(_html_table_csv("test.csv"))
