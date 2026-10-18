"""Address lint (dd.py lint): flags EVM addresses whose letters are all lowercase or all uppercase.

The check is case shape only: EIP-55 needs keccak-256, which the standard library lacks, so a mixed-case
address with a wrong checksum is not detected. Strings inside the sources array are not checked.
"""

import re

from lib import schema

ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")


def _strings(node, parts):
    if isinstance(node, str):
        yield parts, node
    elif isinstance(node, dict):
        for key, value in node.items():
            if not parts and key == "sources":
                continue
            yield from _strings(value, parts + (key,))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _strings(value, parts + (i,))


def _single_case(address):
    letters = [ch for ch in address[2:] if ch.isalpha()]
    return bool(letters) and (all(ch.islower() for ch in letters) or all(ch.isupper() for ch in letters))


def address_warnings(doc):
    """[{"path", "address"}, ...] sorted by path then address, without duplicates."""
    found = set()
    for parts, text in _strings(doc, ()):
        for match in ADDRESS.finditer(text):
            if _single_case(match.group(0)):
                found.add((schema.format_path(parts), match.group(0)))
    return [{"path": path, "address": address} for path, address in sorted(found)]
