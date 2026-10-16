"""``gotc discover``: automatic source discovery for a new city (docs/research/SCALING.md §2, ADR-0008).

``parse`` holds the pure parsers (every one unit-tested from recorded fixtures); ``engine`` does the polite
probing through ``PoliteClient`` (robots first, always) and writes the scored candidate file.
"""
