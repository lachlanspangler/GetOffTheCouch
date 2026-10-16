"""Import every adapter module so @register runs. Add new adapter modules here."""

from gotc.adapters import (  # noqa: F401
    arcgis,
    bibliocommons,
    calendars,
    ckan,
    communico,
    curated,
    demo,
    ics,
    simpleview,
    socrata,
    ticketing,
    trumba,
)
