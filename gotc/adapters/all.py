"""Import every adapter module so @register runs. Add new adapter modules here."""

from gotc.adapters import (  # noqa: F401
    arcgis,
    bibliocommons,
    calendars,
    ckan,
    communico,
    csvfile,
    curated,
    demo,
    galaxydigital,
    handsonconnect,
    ics,
    makerfaire,
    runsignup,
    simpleview,
    socrata,
    ticketing,
    trumba,
    upcomingcons,
    volo,
)
