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

from .main import TransomCommand, _lipsum, _plural, _html_table, _html_table_csv
from plano import *
from plano.commands import PlanoCommand
from threading import Thread
from xml.etree.ElementTree import XML as _XML

transom_command = TransomCommand(home=get_absolute_path("build/transom"))
test_site_dir = get_absolute_path("test-site")
result_file = "output/result.json"

class test_site(working_dir):
    def __enter__(self):
        dir = super(test_site, self).__enter__()
        copy(test_site_dir, ".", inside=False, symlinks=False)
        return dir

@test
def transom_options():
    run("transom --help")

    with expect_system_exit():
        transom_command.main(["--help"])

    with expect_system_exit():
        transom_command.main()

@test
def transom_init():
    run("transom init --help")
    run("transom init --init-only --verbose config input")

    with expect_system_exit():
        TransomCommand(home=None).main(["init", "config", "input"])

    with working_dir():
        transom_command.main(["init", "config", "input"])

        check_dir("config")
        check_dir("input")
        check_file("config/config.py")
        check_file("input/index.md")
        check_file("input/main.css")
        check_file("input/main.js")

        transom_command.main(["init", "config", "input"]) # Re-init

@test
def transom_render():
    run("transom render --help")
    run("transom render --init-only --quiet config input output")

    with test_site():
        transom_command.main(["render", "--verbose", "config", "input", "output"])

        check_dir("output")
        check_file("output/index.html")
        check_file("output/test-1.html")
        check_file("output/test-2.html")
        check_file("output/main.css")
        check_file("output/main.js")

        result = read("output/index.html")
        assert "<title>Doorjamb</title>" in result, result
        assert "<h1 id=\"doorjamb\">Doorjamb</h1>" in result, result

        transom_command.main(["render", "--quiet", "config", "input", "output"])
        transom_command.main(["render", "--force", "config", "input", "output"])

@test
def transom_serve():
    run("transom serve --help")
    run("transom serve --init-only --port 9191 --quiet config input output")

    with test_site():
        def run_():
            transom_command.main(["serve", "--port", "9191", "config", "input", "output"])

        server = Thread(target=run_)
        server.start()

        await_port(9191)

        http_get("http://localhost:9191/")
        http_get("http://localhost:9191/index.html")
        http_get("http://localhost:9191/main.css")

        http_post("http://localhost:9191/STOP", "please")

        server.join()

@test
def transom_check_links():
    run("transom check-links --help")
    run("transom check-links --init-only --verbose config input output")

    with test_site():
        transom_command.main(["render", "config", "input", "output"])
        transom_command.main(["check-links", "config", "input", "output"])

        append(join("a", "index.md"), "[Not there](not-there.html)")

        transom_command.main(["check-links", "config", "input", "output"])

@test
def transom_check_files():
    run("transom check-files --help")
    run("transom check-files --init-only --quiet config input output")

    with test_site():
        transom_command.main(["render", "config", "input", "output"])

        remove(join("input", "test-page-1.md")) # An extra output file
        remove(join("output", "test-page-2.html")) # A missing output file

        transom_command.main(["check-files", "config", "input", "output"])

@test
def plano_render():
    with test_site():
        PlanoCommand().main(["render"])

        result = read_json(result_file)
        assert result["rendered"], result

@test
def plano_serve():
    with test_site():
        def run():
            PlanoCommand().main(["serve", "--port", "9191"])

        server = Thread(target=run)
        server.start()

        await_port(9191)

        http_post("http://localhost:9191/STOP", "please")

        server.join()

        result = read_json(result_file)
        assert result["served"], result

@test
def plano_check_links():
    with test_site():
        PlanoCommand().main(["check-links"])

        result = read_json(result_file)
        assert result["links_checked"], result

@test
def plano_check_files():
    with test_site():
        PlanoCommand().main(["check-files"])

        result = read_json(result_file)
        assert result["files_checked"], result

@test
def plano_clean():
    with test_site():
        PlanoCommand().main(["clean"])

@test
def plano_modules():
    with test_site():
        with expect_system_exit():
            PlanoCommand().main(["modules", "--remote", "--recursive"])

@test
def lipsum_function():
    result = _lipsum(0, end="")
    assert result == "", result

    result = _lipsum(1)
    assert result == "Lorem."

    result = _lipsum(1000)
    assert result

@test
def plural_function():
    result = _plural(None)
    assert result == "", result

    result = _plural("")
    assert result == "", result

    result = _plural("test")
    assert result == "tests", result

    result = _plural("test", 1)
    assert result == "test", result

    result = _plural("bus")
    assert result == "busses", result

    result = _plural("bus", 1)
    assert result == "bus", result

    result = _plural("terminus", 2, "termini")
    assert result == "termini", result

@test
def html_table_functions():
    data = (
        (1, 2, 3),
        ("a", "b", "c"),
        (None, "", 0),
    )

    _XML(_html_table(data, class_="X"))
    _XML(_html_table(data, headings=("A", "B", "C")))

    with working_dir():
        with open("test.csv", "w", newline="") as f:
            writer = _csv.writer(f)
            writer.writerows(data)

        _XML(_html_table_csv("test.csv"))
