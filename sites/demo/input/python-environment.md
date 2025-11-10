---
import inspect as _inspect
import re as _re
import textwrap as _textwrap

def _format_value(value):
    match value:
        case str() if len(value) > 50:
            return repr(f"{value[:40]}[...]") + f" ({len(value):,})"
        case x if callable(x):
            sig = f"{x.__name__}{_inspect.signature(x)}"
            return _re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*\.)+(?=[A-Z])", "", sig)
        case _:
            return repr(value)

def _format_comment(text):
    if text is None:
        return ""

    return _textwrap.indent(_textwrap.fill(text, 77), "# ") + "\n"

def _render_properties(obj, obj_name):
    for name, member in _inspect.getmembers(type(obj), lambda x: isinstance(x, property)):
        if name.startswith("_"):
            continue

        # This avoids recursion
        if obj_name == "page" and name == "content":
            yield _format_comment(_inspect.getdoc(member))
            yield "page.content = '[...]'\n\n"
            continue

        yield _format_comment(_inspect.getdoc(member))
        yield f"{obj_name}.{name} = {_format_value(getattr(obj, name))}\n\n"

def _render_methods(obj, obj_name):
    for name, member in _inspect.getmembers(type(obj), lambda x: not isinstance(x, property)):
        if name.startswith("_"):
            continue

        yield _format_comment(_inspect.getdoc(member))
        yield f"{obj_name}.{_format_value(getattr(obj, name))}\n\n"

def _render_callables():
    for name, member in globals().items():
        if name.startswith("_"):
            continue

        if not callable(member):
            continue

        if _inspect.getdoc(member) is not None:
            yield _format_comment(_inspect.getdoc(member))

        yield _format_value(member) + "\n\n"
---

<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>

# Python environment

## Site

You can modify site properties in `config/site.py`.  Use
`load_template(path)` to set template properties.

~~~ python
# The object representing the whole site
site = {{repr(site)}}

{{strip(_render_properties(site, "site"))}}
~~~

## Page

You can modify page properties in the header of Markdown and other
textual input files.

~~~ python
# The object representing the current page
page = {{repr(page)}}

{{strip(_render_properties(page, "page"))}}

{{strip(_render_methods(page, "page"))}}
~~~

## Global functions and classes

~~~ python
{{strip(_render_callables())}}
~~~
