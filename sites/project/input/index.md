---
page.title = "Home"
---

<div style="display: flex; gap: 2rem; margin-right: 2rem;">
  <h1 style="font-size: 2rem; font-weight: 800;">Transom</h1>
</div>

<p style="font-family: Merriweather; font-size: 1rem;">Transom is a
static site generator for Python programmers.  It generates websites
from Markdown using Python code.</p>

<div class="code-label">config/site.py</div>

~~~ python
def shout(greeting):
    return greeting.upper()
~~~

<div class="code-label">input/index.md</div>

~~~ python
---
def hello():
    return "Hello!"
---

# A greeting

{{{shout(hello())}}}
~~~

<div class="code-label">output/index.html</div>

~~~ html
<html>
  <head>
    <title>A greeting</title>
  </head>
  <body>
    <h1>A greeting</h1>
    <p>HELLO!</p>
  </body>
</html>
~~~

## Installation

~~~ shell
./plano install
~~~

## Resources

- How Transom works
- [Transom templates](templates.html)
- [Transom Python](python.html)
- [Transom CSS](css.html)
- [Transom Javascript](javascript.html)
