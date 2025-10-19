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

import csv
import threading

from plano import *
from xml.etree.ElementTree import XML

from .main import TransomCommand, lipsum, plural, html_table, html_table_csv

transom_home = get_parent_dir(get_parent_dir(get_parent_dir(__file__)))
result_file = "output/result.json"

def call_transom_command(args=[]):
    TransomCommand(home=transom_home).main(args + ["--verbose"])

def call_plano_command(args=[]):
    PlanoCommand().main(args + ["--verbose"])

class test_site(working_dir):
    def __enter__(self):
        dir_ = super().__enter__()
        copy(join(transom_home, "sites/test"), ".", inside=False, symlinks=False)
        return dir_

class empty_test_site(working_dir):
    def __enter__(self):
        dir_ = super().__enter__()
        make_dir("input")
        return dir_

@test
def transom_options():
    run("transom --help")

    with expect_system_exit():
        TransomCommand(home=None).main([])

    with expect_system_exit():
        call_transom_command(["--help"])

    with expect_system_exit():
        call_transom_command([])

    with empty_test_site():
        call_transom_command(["render", "--output", "other"])

@test
def transom_init():
    run("transom init --help")
    run("transom init --init-only --quiet")
    run("transom init --init-only --verbose")

    with expect_system_exit():
        TransomCommand(home=None).main(["init"])

    call_transom_command(["init", "--init-only"])

    with working_dir():
        call_transom_command(["init", "--github"])

        check_dir("config")
        check_dir("input")
        check_file("config/site.py")
        check_file("config/transom.css")
        check_file("config/transom.js")
        check_file("input/index.md")
        check_file("input/site.css")
        check_file("input/site.js")
        check_file(".gitignore")
        check_file(".plano.py")
        check_dir("python/transom")
        check_dir(".github")

        call_transom_command(["init"]) # Re-init

    with working_dir():
        touch("input/index.html") # A preexisting index file

        call_transom_command(["init"])

@test
def transom_render():
    run("transom render --help")

    with empty_test_site():
        run("transom render --init-only --quiet")
        run("transom render --init-only --verbose")

    with test_site():
        call_transom_command(["render"])

        check_dir("output")
        check_file("output/index.html")
        check_file("output/test-cases-1.html")
        check_file("output/test-cases-2.html")
        check_file("output/site.css")
        check_file("output/site.js")

        result = read("output/index.html")
        assert "<title>Transom</title>" in result, result
        assert "<h1 id=\"transom\">Transom</h1>" in result, result

        call_transom_command(["render", "--quiet"]) # XXX
        call_transom_command(["render", "--force"])

    with empty_test_site():
        call_transom_command(["render"])

    with empty_test_site():
        remove("input") # No input dir

        with expect_system_exit():
            call_transom_command(["render"])

    with empty_test_site():
         # Duplicate index files
        touch("input/index.md")
        touch("input/index.html")

        with expect_system_exit():
            call_transom_command(["render"])

    with empty_test_site():
        write("config/site.py", "1 / 0")

        with expect_system_exit():
            call_transom_command(["render"])

    with empty_test_site():
        write("config/site.py", "raise TransomError()")

        with expect_system_exit():
            call_transom_command(["render"])

    with empty_test_site():
        write("input/test.md", "---\n1 / 0\n---\n")

        with expect_system_exit():
            call_transom_command(["render"])

    with empty_test_site():
        write("input/test.md", "---\nraise TransomError()\n---\n")

        with expect_system_exit():
            call_transom_command(["render"])

    with empty_test_site():
        write("input/test.md", "{{1 / 0}}")

        with expect_system_exit():
            call_transom_command(["render"])

@test
def transom_serve():
    run("transom serve --help")

    with empty_test_site():
        run("transom serve --init-only --port 9191 --quiet")
        run("transom serve --init-only --port 9191 --verbose")

    with empty_test_site():
        write("config/site.py", "site.prefix = '/prefix'\n")
        write("input/index.md", "# Test\n")

        def run_():
            call_transom_command(["serve", "--port", "9191"])

        server = threading.Thread(target=run_, name="test-thread")
        server.start()

        await_port(9191)

        http_get("http://localhost:9191/")
        http_get("http://localhost:9191/prefix/")

        try:
            import pyinotify
        except ModuleNotFoundError:
            pass
        else:
            write("input/another.md", "# Another\n")  # A new input file
            write("input/#ignore.md", "# Ignore\n")   # A new ignored input file
            write("config/another.html", "<html/>\n") # A new config file
            write("config/#ignore.html", "<html/>\n") # A new ignored config file

            sleep(0.2)

            http_get("http://localhost:9191/another.html")

            with expect_error():
                http_get("http://localhost:9191/ignore.html")

        # Another server on the same port
        with expect_system_exit():
            call_transom_command(["serve", "--port", "9191"])

        http_post("http://localhost:9191/STOP", "please")

        server.join()

@test
def transom_check_links():
    run("transom check-links --help")

    with empty_test_site():
        run("transom check-links --init-only --quiet")
        run("transom check-links --init-only --verbose")

    with test_site():
        call_transom_command(["render"])
        call_transom_command(["check-links"])

    # Not rendering before checking links
    with empty_test_site():
        with expect_system_exit():
            call_transom_command(["check-links"])

    with empty_test_site():
        write("input/test.md", "[Nope](no-such-file.html)")

        call_transom_command(["render"])

        with expect_system_exit():
            call_transom_command(["check-links"])

@test
def transom_check_files():
    run("transom check-files --help")

    with empty_test_site():
        run("transom check-files --init-only --quiet")
        run("transom check-files --init-only --verbose")

    with test_site():
        write("output/extra.html", "<html/>") # An extra output file
        remove("output/test-cases-2.html") # A missing output file

        with expect_system_exit():
            call_transom_command(["check-files"])

    with empty_test_site():
        with expect_system_exit():
            # Not rendering before
            call_transom_command(["check-files"])

@test
def plano_render():
    with test_site():
        call_plano_command(["render", "--force"])

        result = read_json(result_file)
        assert result["rendered"], result

@test
def plano_serve():
    with test_site():
        def run():
            call_plano_command(["serve", "--port", "9191", "--force"])

        server = threading.Thread(target=run)
        server.start()

        await_port(9191)

        http_post("http://localhost:9191/STOP", "please")

        server.join()

        result = read_json(result_file)
        assert result["served"], result

@test
def plano_check_links():
    with test_site():
        call_plano_command(["render"])
        call_plano_command(["check-links"])

        result = read_json(result_file)
        assert result["links_checked"], result

@test
def plano_check_files():
    with test_site():
        call_plano_command(["render"])
        call_plano_command(["check-files"])

        result = read_json(result_file)
        assert result["files_checked"], result

@test
def plano_clean():
    with test_site():
        call_plano_command(["clean"])

@test
def plano_modules():
    with test_site():
        with expect_system_exit():
            call_plano_command(["modules", "--remote", "--recursive"])

@test
def lipsum_function():
    result = lipsum(0, end="")
    assert result == "", result

    result = lipsum(1)
    assert result == "Lorem."

    result = lipsum(1000)
    assert result

@test
def plural_function():
    result = plural(None)
    assert result == "", result

    result = plural("")
    assert result == "", result

    result = plural("test")
    assert result == "tests", result

    result = plural("test", 1)
    assert result == "test", result

    result = plural("bus")
    assert result == "busses", result

    result = plural("bus", 1)
    assert result == "bus", result

    result = plural("terminus", 2, "termini")
    assert result == "termini", result

@test
def html_table_functions():
    data = (
        (1, 2, 3),
        ("a", "b", "c"),
        (None, "", 0),
    )

    XML(html_table(data, class_="X"))
    XML(html_table(data, headings=("A", "B", "C")))

    with working_dir():
        with open("test.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        XML(html_table_csv("test.csv"))
