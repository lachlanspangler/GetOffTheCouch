"""Import every adapter module so @register runs. Add new adapter modules here."""

from gotc.adapters import calendars, curated, demo, ics, socrata, ticketing  # noqa: F401
