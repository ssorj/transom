albert = "Frank"

def benny():
    return "Agatha"

def interface_object_properties(obj_name, obj):
    yield f"{obj_name}\n: `{repr(obj)}`\n\n"

    for attr_name in obj._allowed:
        attr_value = getattr(obj, attr_name)

        yield f"{obj_name}.{attr_name}\n: `"

        match attr_value:
            case str() if len(attr_value) > 50:
                yield repr(f"{attr_value[:40]}[...]") + f"({len(attr_value)})"
            case _:
                yield repr(attr_value)

        yield "`\n\n"

    yield "\n&nbsp;\n"
