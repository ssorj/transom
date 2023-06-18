# Transom

[![main](https://github.com/ssorj/transom/workflows/main/badge.svg)](https://github.com/ssorj/transom/actions?query=workflow%3Amain)

Transom renders static websites from Markdown and Python

## General stuff to know about Transom

Transom is a fairly run-of-the-mill static site generator.  It
converts Markdown input files into HTML output files.

But that does oversimplify things a bit.  Transom actually converts
Markdown input files and simple HTML files and Python code into
somewhat fancier HTML output files.  For me, I like that it automates
a lot of the work of creating a real website, *and* it does it with a
pretty simple transformation model.

By pretty simple, I mean that I only need to think about these things:

* Markdown converts to HTML in a conventional way.

* Python code works like standard Python code, with some extra model
  data and functions for the pages I'm working with.

* Everything, including input HTML, is wrapped in site templates.

The full power of Python is available in the generation phase.  That
allows me to efficiently express and reuse display logic.

On a different note, Transom is pleasantly quick on modern machines.
I use it to generate the Apache Qpid website, which is large (about 2
gigs) and has many files (more than 30,000).  Transom can render
everything in less than a second.

## Using the transom command

To generate a starter website project, use `transom init`.  It
requires the path to the config dir and the path to the input file
dir.  The starter site is really basic.  It just lays down an index
page (`<input-dir>/index.md`) a CSS file (`<input-dir>/main.css`) and
a JavaScript file (`<input-dir>/main.js`) plus the supporting Transom
config files.

~~~ sh
$ cd <your-new-project-dir>
$ transom init config input
transom: Creating 'config/body.html'
transom: Creating 'config/config.py'
transom: Creating 'config/page.html'
transom: Creating 'input/index.md'
transom: Creating 'input/main.css'
transom: Creating 'input/main.js'
~~~

Rendering takes the config dir and the input dir and the *output dir*.
That's of course the interesting part.

~~~ sh
$ transom render config input output
Rendering files from 'input' to 'output'
Found 3 input files
Rendered 3 output files
~~~

Now you have the HTML website under `<your-project-dir>/output`.  You
can send that whereever you need it to be for publishing purposes.
Since I often use GitHub pages for publishing, I set my output dir to
`docs` and then configure the GitHub project serve those files.

For local development, you will likely want to use the `transom serve`
command.  This renders the site to the output dir and stands up a
local webserver so you can see what you have.  Transom watches for any
updates to the config of input files and rerenders the output.

~~~ sh
$ transom serve config input output
Rendering files from 'input' to 'output'
Found 3 input files
Rendered 0 output files (3 unchanged)
Watching for input file changes
Serving at http://localhost:8080
Starting LiveReload v0.9.3 for /tmp/tmp.57gwncgHua/output on port 35729.
~~~

<!-- ### Using Plano commands -->

<!-- ## Project commands -->

<!-- Once you have set up the project, you can use the `./plano` command in -->
<!-- the root of the project to perform project tasks.  It accepts a -->
<!-- subcommand.  Use `./plano --help` to list the available commands. -->
