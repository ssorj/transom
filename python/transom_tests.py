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

def open_test_session(session):
    enable_logging(level="error")

    if session.module.command.verbose:
        enable_logging(level="notice")

def test_command_options(session):
    call("transom --help")

def test_command_init(session):
    call("transom init --help")
    call("transom init --init-only --verbose config input")

    with temp_working_dir():
        call("transom init config input")
        call("transom init config input") # Re-init

def test_command_render(session):
    call("transom render --help")
    call("transom render --init-only --quiet config input output")

    with temp_working_dir():
        make_input_files("config", "input")

        call("transom render config input output")
        call("transom render config input output")
        call("transom render --force config input output")

def test_command_check_links(session):
    call("transom check-links --help")
    call("transom check-links --init-only --verbose config input output")

    with temp_working_dir():
        make_input_files("config", "input")

        call("transom render config input output")
        call("transom check-links config input output")

        append(join("a", "index.md"), "[Not there](not-there.html)")

        call("transom check-links config input output")

def test_command_check_files(session):
    call("transom check-files --help")
    call("transom check-files --init-only --quiet config input output")

    with temp_working_dir():
        make_input_files("config", "input")

        call("transom render config input output")

        remove(join("input", "test-page-1.md")) # An extra output file
        remove(join("output", "test-page-2.html")) # A missing output file

        call("transom check-files config input output")

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

    with temp_working_dir():
        with open("test.csv", "w", newline="") as f:
            writer = _csv.writer(f)
            writer.writerows(data)

        _XML(_html_table_csv("test.csv"))

_index_page = """
# Index
[Test 1](test-1.html)
[Test 2](test-2.html)
"""

_test_page_1 = """
# Test 1
"""

_test_page_2 = """
# Test 2
"""

def make_input_files(config_dir, input_dir):
    call("transom init {} {}", config_dir, input_dir)

    write(join(input_dir, "index.md"), _index_page)
    write(join(input_dir, "test-1.md"), _test_page_1)
    write(join(input_dir, "test-2.md"), _test_page_2)
