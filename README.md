# Transom

[![main](https://github.com/ssorj/transom/workflows/main/badge.svg)](https://github.com/ssorj/transom/actions?query=workflow%3Amain)

Transom renders static websites from Markdown and Python.

## Overview

Transom is a static site generator written in Python.  It converts
Markdown input files into HTML output files.

- Input files come from `input/`.  Corresponding output files go to
  `output/`.

- `.md` input files are converted to `.html` output files.  Transom
  uses [Mistune][mistune] for conversion.

- `.md`, `.html.in`, `.html`, `.js`, and `.css` input files are
  treated as templates, with `{{ }}` curly braces for template
  placeholders.  All other files are copied as is.

- Template placeholders contain Python code, executed using `eval()`.
  The Python environment is defined in `config/site.py`.

- The Python environment includes a `site` object for configuring the
  site.  It also includes a `page` object and utility functions for
  generating output.

- `.md` and `.html.in` files are wrapped in page templates defined in
  `config/head.html` and `config/body.html`.

[mistune]: https://github.com/lepture/mistune

## Installation

Install the dependencies and then use `./plano install`:

~~~
pip install pyyaml
./plano install
~~~

## Using the transom command

To generate a starter website project, use `transom init`.  The
starter site is really basic.  It lays down an index page
(`input/index.md`) a CSS file (`input/site.css`) and a JavaScript file
(`input/site.js`) plus the supporting Transom config files.

~~~ console
$ cd <your-new-project-dir>

$ transom init
transom: Creating 'config/site.py'
transom: Creating 'config/transom.css'
transom: Creating 'config/transom.js'
transom: Creating 'config/head.html'
transom: Creating 'config/body.html'
transom: Creating 'input/index.md'
transom: Creating 'input/site.css'
transom: Creating 'input/site.js'
~~~

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

<!-- Site checks for files and links -->
<!-- ## Implementation notes -->
<!-- Multiprocessing -->
<!-- Mistune (having tried others before) -->
<!-- ## Template syntax (really Python code syntax) -->
<!-- ## Site config options and how to set them -->
<!-- ## Page and Site APIs -->
<!-- ## Page metadata -->
<!-- ## HTML generation functions -->
<!-- Conveniences -->
<!-- ## Using Plano project commands -->
<!-- ## Project commands -->
<!-- Once you have set up the project, you can use the `./plano` command in -->
<!-- the root of the project to perform project tasks.  It accepts a -->
<!-- subcommand.  Use `./plano --help` to list the available commands. -->

<!-- ## Site configuration -->

<!-- ## Page configuration -->

## The rendering process

XXX

## Templates

Transom templates allow you to generate output by embedding Python
expressions inside `{{ }}` placeholders.  These expressions are
designed to execute Python code using Python's `eval` function.

You can call functions or access variables you've defined in
`config/site.py`.  You also have access to the Transom `site` and
`page` objects, which have APIs for accessing metadata and performing
object-specific operations.

You can use `{{{ }}}` to produce literal `{{ }}` output.

`config/site.py`:

~~~ python
def get_page_info(page):
    return page.url, page.title, page.parent, page.site
~~~

`input/index.md`:

~~~ html
<pre>{{get_page_info(page)}}</pre>
~~~

## Site configuration

`config/site.py`

XXX Table with the other files under config/.

## The Site API

`site.prefix` - A string prefix used in templates and for generated
links.  It is inserted before the file path.  This is important when
the published site lives under a directory prefix, as is the case for
GitHub Pages.  The default is `""`, the empty string.

`site.config_dirs` - A list of directories to watch for changes.  If
any file changes in these directories, the whole site is re-rendered.
The default is `["config"]`.

`site.ignored_file_patterns` - A list of shell globs for excluding
input files from processing.  The default is `[".git", ".svn", ".#*","#*"]`.

`site.ignored_link_patterns` - A list of shell globs for excluding
link URLs from link checking.  The default is `[]`, the empty list.

## The Page API

`page.site` - The site API object.

`page.include(path)` - Include the file at `path`.  Any variables in
the input file are evaluated.

#### HTML page parts

`page.head` - The head element of the page.  It is a template read
from `config/head.html`.

`page.extra_headers` - A list of extra HTML headers to add to the
HTML head element.  The default is `[]`, the empty list.

`page.body` - The body element of the page.  It is a template read
from `config/body.html`.

`page.content` - The primary page content, read from `input/<file>.md`
or `input/<file>.html.in`.

#### Navigation elements

`page.path_nav(start=0, end=None, min=1)`

`page.toc_nav()`

`page.directory_nav()`

## Text and HTML generation functions

`lipsum(count=50, end=".")`

`plural(noun, count=0, plural=None)`

`html_table(data, headings=None, cell_fn=<default>, **attrs)`

`html_table_csv(path, **attrs)`

`convert_markdown(text)`

## Setting up Transom for a website repo

Change directory to the root of your project:

~~~
cd <project-dir>/
~~~

Add the Transom code as a subdirectory:

~~~
mkdir -p external
curl -sfL https://github.com/ssorj/transom/archive/main.tar.gz | tar -C external -xz
mv external/transom-main external/transom
~~~

Symlink the Transom and Plano libraries into your `python` directory:

~~~ sh
mkdir -p python
ln -s ../external/transom/python/transom python/transom
ln -s ../external/transom/python/plano python/plano
~~~

Copy the `plano` command into the root of your project:

~~~ sh
cp external/transom/plano plano
~~~

Copy the standard config files:

~~~ sh
cp external/transom/profiles/website/.plano.py .plano.py
cp external/transom/profiles/website/.gitignore .gitignore
~~~

Copy the standard workflow file:

~~~ sh
mkdir -p .github/workflows
cp external/transom/profiles/website/.github/workflows/main.yaml .github/workflows/main.yaml
~~~
