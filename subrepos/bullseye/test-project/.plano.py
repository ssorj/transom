import sys

sys.path.insert(0, "../python")

from bullseye import *

project.name = "chucker"
project.source_exclude = ["bumper.*"]
project.data_dirs = ["files"]
project.test_modules = ["chucker.tests"]

result_file = "build/result.json"

@command(parent=build)
def build(*args, **kwargs):
    build.parent.function(*args, **kwargs)

    notice("Extended building")

    data = {"built": True}
    write_json(result_file, data)

@command(parent=test_)
def test_(*args, **kwargs):
    test_.parent.function(*args, **kwargs)

    notice("Extended testing")

    check_file(result_file)

    if exists(result_file):
        data = read_json(result_file)
        data["tested"] = True
        write_json(result_file, data)

@command(parent=install)
def install(*args, **kwargs):
    install.parent.function(*args, **kwargs)

    notice("Extended installing")

    data = read_json(result_file)
    data["installed"] = True
    write_json(result_file, data)
