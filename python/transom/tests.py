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

from .main import TransomError, TransomSite, TransomCommand, lipsum, plural, html_table, html_table_csv

TRANSOM_HOME = get_parent_dir(get_parent_dir(get_parent_dir(__file__)))
RESULT_FILE = "output/result.json"

def call_transom_command(args=[]):
    TransomCommand(home=TRANSOM_HOME).main(args + ["--verbose"])

def call_plano_command(args=[]):
    PlanoCommand().main(args + ["--verbose"])

class empty_test_site_dir(working_dir):
    def __enter__(self):
        super().__enter__()

        make_dir("input")

class test_site_dir(empty_test_site_dir):
    def __enter__(self):
        super().__enter__()

        copy(join(TRANSOM_HOME, "sites/test"), ".", inside=False, symlinks=False)

class empty_test_site(empty_test_site_dir):
    def __enter__(self):
        super().__enter__()

        self.site = TransomSite(".", verbose=True, threads=1)
        self.site.start()

        return self.site

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)

        self.site.stop()

class standard_test_site(empty_test_site):
    def __enter__(self):
        site = super().__enter__()

        copy(join(TRANSOM_HOME, "sites/test"), ".", inside=False, symlinks=False)

        return site

@test
def site_load_files():
    with standard_test_site() as site:
        site.load_files()

    # Only the input dir, no config
    with empty_test_site() as site:
        site.load_files()

    # No input dir
    with empty_test_site() as site:
        remove("input")

        with expect_exception(TransomError):
            site.load_files()

    # Duplicate index files
    with empty_test_site() as site:
        touch("input/index.md")
        touch("input/index.html")

        with expect_exception(TransomError):
            site.load_files()

@test
def site_process_input_files():
    with standard_test_site() as site:
        site.load_files()
        site.process_input_files()

@test
def site_render_output_files():
    with standard_test_site() as site:
        site.load_files()
        site.process_input_files()
        site.render_output_files()

@test
def site_render():
    # The standard test site
    with test_site_dir():
        site = TransomSite(".", verbose=True, threads=1)
        site.start()

        try:
            site.render()
        finally:
            site.stop()

        check_dir("output")
        check_file("output/index.html")
        check_file("output/test-cases-1.html")
        check_file("output/test-cases-2.html")
        check_file("output/site.css")
        check_file("output/site.js")

        result = read("output/index.html")
        assert "<title>Transom</title>" in result, result
        assert "<h1 id=\"transom\">Transom</h1>" in result, result

    # with empty_test_site() as site:

@test
def command_options():
    run("transom --help")

    with expect_system_exit():
        TransomCommand(home=None).main([])

    with expect_system_exit():
        call_transom_command(["--help"])

    with expect_system_exit():
        call_transom_command([])

    with empty_test_site_dir():
        call_transom_command(["render", "--output", "other"])

@test
def command_init():
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

        # Re-init
        call_transom_command(["init"])

    # A preexisting index file
    with working_dir():
        touch("input/index.html")

        call_transom_command(["init"])

@test
def command_render():
    run("transom render --help")

    with empty_test_site_dir():
        run("transom render --init-only --quiet")
        run("transom render --init-only --verbose")

    with test_site_dir():
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

        call_transom_command(["render", "--quiet"])
        call_transom_command(["render", "--force"])

    # Broken site code
    with empty_test_site_dir():
        write("config/site.py", "1 / 0")

        with expect_system_exit():
            call_transom_command(["render"])

    # Transom error handling in site code
    with empty_test_site_dir():
        write("config/site.py", "raise TransomError()")

        with expect_system_exit():
            call_transom_command(["render"])

    # Syntax error in site code
    with empty_test_site_dir():
        write("config/site.py", ")(")

        with expect_system_exit():
            call_transom_command(["render"])

    # Illegal site attribute access
    with empty_test_site_dir():
        write("config/site.py", "print(site.files)")

        with expect_system_exit():
            call_transom_command(["render"])

    # Illegal site attribute access
    with empty_test_site_dir():
        write("input/test.md", "{{page.input_path = '/nope'}}")

        with expect_system_exit():
            call_transom_command(["render"])

    # Broken header code
    with empty_test_site_dir():
        write("input/test.md", "---\n1 / 0\n---\n")

        with expect_system_exit():
            call_transom_command(["render"])

    # Transom error handling in header code
    with empty_test_site_dir():
        write("input/test.md", "---\nraise TransomError()\n---\n")

        with expect_system_exit():
            call_transom_command(["render"])

    # Syntax error in header code
    with empty_test_site_dir():
        write("input/test.md", "---\n)(\n---\n")

        with expect_system_exit():
            call_transom_command(["render"])

    # Broken template code
    with empty_test_site_dir():
        write("input/test.md", "{{1 / 0}}")

        with expect_system_exit():
            call_transom_command(["render"])

    # Syntax error in template code
    with empty_test_site_dir():
        write("input/test.md", "{{)(}}")

        with expect_system_exit():
            call_transom_command(["render"])

@test
def command_serve():
    run("transom serve --help")

    with empty_test_site_dir():
        run("transom serve --init-only --port 9191 --quiet")
        run("transom serve --init-only --port 9191 --verbose")

    with empty_test_site_dir():
        write("config/site.py", "site.prefix = '/prefix'\n")
        write("input/index.md", "# Test\n")

        def run_():
            call_transom_command(["serve", "--port", "9191"])

        server = threading.Thread(target=run_, name="test-thread")
        server.start()

        await_port(9191)

        http_get("http://localhost:9191/")
        http_get("http://localhost:9191/prefix/")

        write("input/another.md", "# Another")  # A new input file
        write("input/#ignore.md", "# Ignore")   # A new ignored input file
        write("config/another.html", "<html/>") # A new config file
        write("config/#ignore.html", "<html/>") # A new ignored config file

        http_get("http://localhost:9191/another.html")

        with expect_error():
            http_get("http://localhost:9191/ignore.html")

        # Another server on the same port
        with expect_system_exit():
            call_transom_command(["serve", "--port", "9191"])

        http_post("http://localhost:9191/STOP", "please")

        server.join()

# @test
# def command_check_links():
#     run("transom check-links --help")

#     with empty_test_site_dir():
#         run("transom check-links --init-only --quiet")
#         run("transom check-links --init-only --verbose")

#     with test_site_dir():
#         call_transom_command(["render"])
#         call_transom_command(["check-links"])

#     # Not rendering before checking links
#     with empty_test_site_dir():
#         with expect_system_exit():
#             call_transom_command(["check-links"])

#     with empty_test_site_dir():
#         write("input/test.md", "[Nope](no-such-file.html)")

#         call_transom_command(["render"])

#         with expect_system_exit():
#             call_transom_command(["check-links"])

@test
def command_check():
    run("transom check --help")

    with empty_test_site_dir():
        run("transom check --init-only --quiet")
        run("transom check --init-only --verbose")

    with test_site_dir():
        touch("output/extra.html")         # An extra output file
        remove("output/test-cases-2.html") # A missing output file

        with expect_system_exit():
            call_transom_command(["check"])

    # Checking without first rendering
    with empty_test_site_dir():
        with expect_system_exit():
            call_transom_command(["check"])

@test
def function_lipsum():
    result = lipsum(0, end="")
    assert result == "", result

    result = lipsum(1)
    assert result == "Lorem."

    result = lipsum(1000)
    assert result

@test
def function_plural():
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
def function_html_table():
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

@test
def plano_render():
    with test_site_dir():
        call_plano_command(["render", "--force"])

        result = read_json(RESULT_FILE)
        assert result["rendered"], result

@test
def plano_serve():
    with test_site_dir():
        def run():
            call_plano_command(["serve", "--port", "9191", "--force"])

        server = threading.Thread(target=run)
        server.start()

        await_port(9191)

        http_post("http://localhost:9191/STOP", "please")

        server.join()

        result = read_json(RESULT_FILE)
        assert result["served"], result

@test
def plano_check():
    with test_site_dir():
        call_plano_command(["render"])
        call_plano_command(["check"])

        result = read_json(RESULT_FILE)
        assert result["checked"], result

@test
def plano_clean():
    with test_site_dir():
        call_plano_command(["clean"])
