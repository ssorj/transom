def _globals():
    yield "<dl>"

    for attr_name, attr_value in (x for x in globals().items() if not x[0].startswith("_")):
        yield f"<dt>{attr_name}</dt><dd><code>"

        match attr_value:
            case str() if len(attr_value) > 50:
                yield html_escape(repr(f"{attr_value[:40]}[...]") + f" ({len(attr_value):,})")
            case _:
                yield html_escape(repr(attr_value))

        yield "</code></dd>"

    yield "</dl>"

def _locals():
    yield "<dl>"

    for attr_name, attr_value in (x for x in locals().items() if not x[0].startswith("_")):
        yield f"<dt>{attr_name}</dt><dd><code>"

        match attr_value:
            case str() if len(attr_value) > 50:
                yield html_escape(repr(f"{attr_value[:40]}[...]") + f" ({len(attr_value):,})")
            case _:
                yield html_escape(repr(attr_value))

        yield "</code></dd>"

    yield "</dl>"

def _object_properties(obj_name, obj):
    import inspect

    yield "<dl>"

    data_members = inspect.getmembers(obj)

    for attr_name, attr_value in (x for x in data_members if not x[0].startswith("_")):
        yield f"<dt>{obj_name}.{attr_name}</dt><dd><code>"

        match attr_value:
            case str() if len(attr_value) > 50:
                yield html_escape(repr(f"{attr_value[:40]}[...]") + f" ({len(attr_value):,})")
            case _:
                yield html_escape(repr(attr_value))

        yield "</code></dd>"

    yield "</dl>"
