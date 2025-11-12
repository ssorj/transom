# Define custom variables and functions for use in {{replaceables}}

import re

def strip_license_header(text):
    return re.sub(r"(?sm)^\s*(?:(?:#.*?\n)+|(?://.*?\n)+|/\*.*?\*/)", "", text).lstrip()
