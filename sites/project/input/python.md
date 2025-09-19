---
import inspect as _inspect
import re as _re
import textwrap as _textwrap

#from transom.main import TransomSite as _TransomSite, InputFile as _InputFile, PageConfig as _PageConfig
from transom.main import SiteConfig as _SiteConfig, PageConfig as _PageConfig

def _format_value(value):
    match value:
        case str() if len(value) > 50:
            return repr(f"{value[:40]}[...]") + f" ({len(value):,})"
        case x if callable(x):
            sig = f"{str(x)}{_inspect.signature(x)}"
            # sig = f"{x.__name__}{_inspect.signature(x)}"
            return _re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*\.)+(?=[A-Z])", "", sig)
        case _:
            return repr(value)

def _format_comment(text):
    if text is None:
        return ""

    return _textwrap.indent(_textwrap.fill(text, 77), "# ") + "\n"

def _render_properties(type_, obj, obj_name):
    for name, member in _inspect.getmembers(type_):
        if name.startswith("_"):
            continue

        yield f"{obj_name}.{name} = {_format_value(getattr(obj, name))}\n"

def _render_callables():
    for name, member in globals().items():
        if name.startswith("_"):
            continue

        if not callable(member):
            continue

        if _inspect.getdoc(member) is not None:
            yield _format_comment(_inspect.getdoc(member))

        yield f"{name}{_inspect.signature(member)}\n\n"
---

# Transom Python

In Transom, Python code is used for all logic performed at
site-generation time.

Python code appears in the following locations:

- *Site scope* - `config/site.py`
- *File scope* - The header of template files (between `---\n` and
  `---\n` at the start of the file)
- *Expression scope* - Template placeholders inside double curly
  braces (between `{{{` and `}}}` at any location inside the body of
  the template)

## The site object

You can modify site properties in `config/site.py`.

~~~ python
{{strip(_render_properties(_SiteConfig, site, "site"))}}
~~~

## The page object

All textual files (`.css`, `.csv`, `.html`, `.js`, `.json`, `.md`,
`.svg`, `.txt`) are processed as templates.  You can access and modify
their properties by accessing the `page` variable.

~~~ python
{{strip(_render_properties(_PageConfig, page, "page"))}}
~~~

## Global functions and classes

~~~ python
{{strip(_render_callables())}}
~~~
