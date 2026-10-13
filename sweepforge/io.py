"""Bounded JSON input shared by CLI and the loopback studio."""
import json
from pathlib import Path
MAX_INPUT = 65536

def encoded(value):
    return json.dumps(value, allow_nan=False, separators=(',', ':')).encode('utf-8')

def decode(raw):
    if len(raw) > MAX_INPUT:
        raise ValueError('Request exceeds 64 KiB')
    def reject(value):
        raise ValueError('Non-finite JSON number is unsupported')
    try:
        value = json.loads(raw, parse_constant=reject)
    except (UnicodeDecodeError, RecursionError, json.JSONDecodeError):
        raise ValueError('Invalid JSON') from None
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 32:
            raise ValueError('JSON nesting exceeds 32 levels')
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
    if type(value) is not dict:
        raise ValueError('Expected a JSON object')
    return value

def read_json(path):
    with Path(path).open('rb') as stream:
        return decode(stream.read(MAX_INPUT + 1))
