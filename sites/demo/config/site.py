import inspect

def interface_object_properties(obj_name, obj):
    yield "<dl>"
    yield f"<dt>{obj_name}</dt><dd><code>{repr(obj)}</code></dd>"

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
