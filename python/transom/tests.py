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
    pass

class empty_test_site(empty_test_site_dir):
    def __enter__(self):
        super().__enter__()

        self.site = TransomSite(".", verbose=True, threads=1)
        self.site.start()

        return self.site

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)

        self.site.stop()

class standard_test_site_dir(working_dir):
    def __enter__(self):
        super().__enter__()

        copy(join(TRANSOM_HOME, "sites/test"), ".", inside=False, symlinks=False)

class standard_test_site(standard_test_site_dir):
    def __enter__(self):
        super().__enter__()

        self.site = TransomSite(".", verbose=True, threads=1)
        self.site.start()

        return self.site

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)

        self.site.stop()

class test_server:
    def __init__(self, site):
        def run_():
            site.serve(port=9191)

        self.server = threading.Thread(target=run_, name="test-server-thread")

    def __enter__(self):
        self.server.start()

        await_port(9191)

        return self.server

    def __exit__(self, exc_type, exc_value, traceback):
        http_post("http://localhost:9191/STOP", "please")

        self.server.join()

@test
def site_load_config_files():
    with empty_test_site() as site:
        site.load_config_files()

    with standard_test_site() as site:
        site.load_config_files()

@test
def site_load_input_files():
    with empty_test_site() as site:
        site.load_config_files()
        input_files = site.load_input_files()

        assert len(input_files) == 0, len(input_files)

    with standard_test_site() as site:
        site.load_config_files()
        input_files = site.load_input_files()

        assert len(input_files) > 0, len(input_files)

@test
def site_render():
    with empty_test_site() as site:
        site.render()

    with standard_test_site() as site:
        site.render()

        check_dir("output")
        check_file("output/index.html")
        check_file("output/test-cases-1.html")
        check_file("output/test-cases-2.html")
        check_file("output/site.css")
        check_file("output/site.js")

        result = read("output/index.html")
        assert "<title>Home - Transom test</title>" in result, result
        assert "<h1 id=\"transom-test\">Transom test</h1>" in result, result

    # Site prefix
    with empty_test_site() as site:
        write("config/site.py", "site.prefix = \"/prefix\"\n")
        write("input/index.md", "# Top\n")
        write("input/test.md", "{{path_nav()}}\n")

        site.render()

        result = read("output/test.html")
        assert "href=\"/prefix/index.html\"" in result, result

    # Find config modified when there is no config dir
    with empty_test_site() as site:
        write("input/test.md", "# Test")

        make_dir("output")

        site.render()

    # Re-render after config file change
    with standard_test_site() as site:
        site.render()

        touch("config/outer/inner/nested.html")

        site.render()

    # Re-render after input file change
    with standard_test_site() as site:
        site.render()

        touch("input/outer/inner/nested.md")

        site.render()

    # # Duplicate index files
    # with empty_test_site() as site:
    #     site.load_config_files()

    #     touch("input/index.md")
    #     touch("input/index.html")

    #     with expect_exception(TransomError):
    #         site.load_input_files()

@test
def site_serve():
    with empty_test_site() as site:
        with test_server(site):
            with expect_exception():
                http_get("http://localhost:9191/")

    with standard_test_site() as site:
        with test_server(site):
            http_get("http://localhost:9191/")
            http_get("http://localhost:9191/site.css")
            http_get("http://localhost:9191/outer/inner/nested.html")

    with empty_test_site() as site:
        with test_server(site):
            write("input/outer/inner/new-file.html", "<html/>")

            http_get("http://localhost:9191/outer/inner/new-file.html")

    with empty_test_site() as site:
        with test_server(site):
            write("input/broken-file.md", "{{1 / 0}}")

            with expect_error():
                http_get("http://localhost:9191/broken-file.html")

    with empty_test_site() as site:
        write("config/site.py", "site.prefix = \"/prefix\"\n")
        write("input/index.md", "# Test\n")

        with test_server(site):
            http_get("http://localhost:9191/")
            http_get("http://localhost:9191/prefix/")

@test
def site_code_execution():
    # Broken code
    with empty_test_site() as site:
        write("config/site.py", "1 / 0")

        with expect_exception(TransomError):
            site.load_config_files()

    # Transom error handling
    with empty_test_site() as site:
        write("config/site.py", "raise TransomError()")

        with expect_exception(TransomError):
            site.load_config_files()

    # Syntax error handling
    with empty_test_site() as site:
        write("config/site.py", ")(")

        with expect_exception(TransomError):
            site.load_config_files()

    # Load a non-existant template
    with empty_test_site() as site:
        write("config/site.py", "site.page_template = load_template(\"/not-there.html\")")

        with expect_exception(TransomError):
            site.load_config_files()

@test
def page_code_execution():
    # Broken code
    with empty_test_site() as site:
        write("input/test.md", "---\n1 / 0\n---\n")

        with expect_exception(TransomError):
            site.render()

    # Transom error handling
    with empty_test_site() as site:
        write("input/test.md", "---\nraise TransomError()\n---\n")

        with expect_exception(TransomError):
            site.render()

    # Syntax error handling
    with empty_test_site() as site:
        write("input/test.md", "---\n)(\n---\n")

        with expect_exception(TransomError):
            site.render()

@test
def template_code_execution():
    # Broken code
    with empty_test_site() as site:
        write("input/test.md", "{{1 / 0}}")

        with expect_exception(TransomError):
            site.render()

    # Transom error handling
    with empty_test_site() as site:
        write("input/test.md", "{{raise TransomError()}}")

        with expect_exception(TransomError):
            site.render()

    # Syntax error handling
    with empty_test_site() as site:
        write("input/test.md", "{{)(}}")

        with expect_exception(TransomError):
            site.render()

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
        check_file("config/page.html")
        check_file("config/body.html")
        check_dir("config/transom")
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

    with empty_test_site_dir():
        copy(join(TRANSOM_HOME, "sites/test"), ".", inside=False, symlinks=False)

        call_transom_command(["render"])

        check_dir("output")
        check_file("output/index.html")
        check_file("output/test-cases-1.html")
        check_file("output/test-cases-2.html")
        check_file("output/site.css")
        check_file("output/site.js")

        result = read("output/index.html")
        assert "<title>Home - Transom test</title>" in result, result
        assert "<h1 id=\"transom-test\">Transom test</h1>" in result, result

        call_transom_command(["render", "--quiet"])
        call_transom_command(["render", "--force"])

@test
def command_serve():
    run("transom serve --help")

    with empty_test_site_dir():
        run("transom serve --init-only --port 9191 --quiet")
        run("transom serve --init-only --port 9191 --verbose")

    with empty_test_site_dir():
        def run_():
            call_transom_command(["serve", "--port", "9191"])

        server = threading.Thread(target=run_, name="test-thread")
        server.start()

        await_port(9191)

        # Another server on the same port
        with expect_system_exit():
            call_transom_command(["serve", "--port", "9191"])

        http_post("http://localhost:9191/STOP", "please")

        server.join()

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
    with standard_test_site_dir():
        call_plano_command(["render", "--force"])

        result = read_json(RESULT_FILE)
        assert result["rendered"], result

@test
def plano_serve():
    with standard_test_site_dir():
        def run():
            call_plano_command(["serve", "--port", "9191"])

        server = threading.Thread(target=run, name="test-thread")
        server.start()

        await_port(9191)

        http_post("http://localhost:9191/STOP", "please")

        server.join()

        result = read_json(RESULT_FILE)
        assert result["served"], result

@test
def plano_clean():
    with standard_test_site_dir():
        call_plano_command(["clean"])
