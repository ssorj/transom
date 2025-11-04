# Transom

Transom renders static websites from Markdown and Python.

<!-- XXX Markdown conversion happens after templates are resolved, so
you can generate markdown in functions -->

## Overview

Transom is a static site generator written in Python.  It converts
Markdown input files into HTML output files.

- Input files come from `input/`.  Corresponding output files go to
  `output/`.

- `.md`, `.html`, `.css`, `.csv`, `.js`, `.json`, `.svg`, and `.txt`
  input files are treated as templates, with `{{ }}` curly braces for
  template placeholders.  All other files are copied as is.

- `.md` input files are converted to `.html` output files.  Transom
  uses [Mistune][mistune] for conversion.

- `.md` files are wrapped in templates defined in `config/page.html`
  and `config/body.html`.

- Template placeholders contain Python code, executed using `eval()`.
  The Python environment is defined in `config/site.py`.

- The Python environment includes a `site` object for configuring the
  site.  It also includes a `page` object and utility functions for
  generating output.

[mistune]: https://github.com/lepture/mistune

## Installation

~~~
./plano install
~~~

## Transom commands

#### transom init

To generate a starter website project, use `transom init`.  The
starter site is very basic.  It lays down an index page
(`input/index.md`) a CSS file (`input/site.css`) and a JavaScript file
(`input/site.js`) plus the supporting Transom config files.

~~~ console
$ cd <your-project-dir>

$ transom init
transom: Creating 'config/body.html'
transom: Creating 'config/page.html'
transom: Creating 'config/site.py'
transom: Creating 'config/transom.css'
transom: Creating 'config/transom.js'
transom: Creating 'input/index.md'
transom: Creating 'input/site.css'
transom: Creating 'input/site.js'
~~~

#### transom init --github

If you want to deploy your site from a GitHub repo, use the `--github`
option to include additional files in the starter project:

~~~ console
$ cd <your-project-dir>

$ transom init --github
transom: Creating 'config/body.html'
transom: Creating 'config/page.html'
transom: Creating 'config/site.py'
transom: Creating 'config/transom.css'
transom: Creating 'config/transom.js'
transom: Creating 'input/index.md'
transom: Creating 'input/site.css'
transom: Creating 'input/site.js'
transom: Creating '.github/workflows/main.yaml'
transom: Creating '.gitignore'
transom: Creating '.plano.py'
transom: Creating 'plano'
transom: Creating 'python/transom'
transom: Creating 'python/mistune'
transom: Creating 'python/plano'
~~~

The resulting site code is self-contained.  You don't need any
dependencies beyond the Python standard library.  Use the `./plano`
command to perform site operations.

<!-- How to set up GitHub Pages to use this -->

#### transom render (./plano render)

The `transom render` command uses the config and input files to
generate the rendered output.

~~~ console
$ transom render
Rendering files from 'input' to 'output'
Found 3 input files
Rendered 3 output files
~~~

Now you have the HTML website under `<your-project-dir>/output`.  You
can send that whereever you need it for publishing purposes.

#### transom serve (./plano serve)

For local development, you will likely want to use the `transom serve`
command.  This renders the site to the output dir and stands up a
local webserver so you can see what you have.  Transom watches for any
updates to the config or input files and re-renders the output as
needed.

~~~ console
$ transom serve
Rendering files from 'input' to 'output'
Found 3 input files
Rendered 0 output files (3 unchanged)
Watching for input file changes
Serving at http://localhost:8080
~~~

<!-- XXX Site checks for files and links -->

<!-- ## Page metadata -->
<!-- ## Using Plano project commands -->
<!-- ## Project commands -->
<!-- Once you have set up the project, you can use the `./plano` command in -->
<!-- the root of the project to perform project tasks.  It accepts a -->
<!-- subcommand.  Use `./plano --help` to list the available commands. -->

<!-- ## Site configuration -->

<!-- ## Page configuration (YAML header) -->

<!-- (./plano serve) -->
<!-- Explain plano, the command runner - think Make but Python-centric -->

<!-- ## The rendering process -->

## Page templates

<!-- XXX which files -->

<!-- XXX This is missing discussion of the page header -->

<!-- XXX The function return values can be strings or string generators (yield "somestring"). -->

Transom templates allow you to generate output by embedding Python
expressions inside `{{ }}` placeholders.  These expressions are
executed using Python's `eval()` function.

You can call functions or access variables you've defined in
`config/site.py`.  You also have access to the Transom `site` and
`page` objects, which have APIs for accessing metadata and performing
object-specific operations.

You can use `{{{` and `}}}` to produce literal `{{` and `}}` output.

`config/site.py`:

~~~ python
def get_page_info(page):
    return page.url, page.title, page.parent
~~~

`input/index.md`:

~~~ html
<pre>{{get_page_info(page)}}</pre>
~~~

`output/index.html`

~~~ html
<pre>('/index.html', 'Transom', None, TransomSite('/home/fritz/example-site'))</pre>
~~~

<!-- ## Site configuration -->

<!-- `config/site.py` -->

<!-- XXX Table with the other files under config/. -->

<!-- XXX All site properties and functions are available in page context as well -->

<!-- XXX paths are relative to the current dir when transom is run, which is the project_dir -->

## Site properties

<!-- XXX These are all mutable when site.py is executed -->

`site.prefix` - A string prefix used in generated links.  It is
inserted before the file path.  This is important when the published
site lives under a directory prefix, as is the case for GitHub Pages.
The default is `""`, meaning no prefix.

`site.ignored_file_patterns` - A list of shell globs for excluding
input and config from processing.  The default is `[".git",
".#*","#*"]`.

`site.page_template` - The default top-level template object for HTML
pages.  The page template includes `{{page.body}}`.  The default is
loaded from `config/page.html`.

`site.body_template` - The default template object for the body
element of HTML pages.  The body element includes `{{page.content}}`.
The default is loaded from `config/body.html`.

## Page properties

<!-- title, extra_headers, page_template, and body_template are
mutable when the page header is executed -->

`page.url` -

`page.title` -

`page.parent` -

`page.body` - The body element of the page.  It is rendered from
`page.body_template`.

`page.content` - The primary page content.  It is rendered from
`input/<file>.md`.

`page.extra_headers` - A list of extra HTML headers to add to the HTML
head element.  The default is `[]`, the empty list.

`page.page_template` - The top-level template object for the page.
The page template includes `{{page.body}}`.  The default is
`site.page_template`.

`page.body_template` - The template object for the body element of the
page.  The body element includes `{{page.content}}`.  The default is
`site.body_template`.

## Functions

#### File operations

`load_template(path)` - Load a template object from `path`.  Use this
when setting template properties.

`include(path)` - Include the file at `path`.

`render(path)` - Include the file at `path` and render it as a
template.  If `path` ends with `.md`, it is converted to HTML.

#### Page navigation functions

`path_nav(start=0, end=None, min=1)` - XXX

`toc_nav()` - XXX inspects the page content and generates a table
of contents from its headings.  This must be placed outside the page
content, in a separate navigation element, such as an aside.

#### HTML generation functions

`html_escape(xxx)` - XXX

`html_table(data, headings=None, cell_fn=<default>, **attrs)` -
Generate an HTML table.

`html_table_csv(path, **attrs)`- Generate an HTML table from a CSV
file.

#### Text generation functions

`lipsum(count=50, end=".")` - Generate filler text.

`plural(noun, count=0, plural=None)` - Generate the plural form of a
word based on `count`.  Set the plural form explicitly with `plural`
if it's not a simple matter of adding `s` or `es`.
