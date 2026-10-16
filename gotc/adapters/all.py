"""Import every adapter module so @register runs. Add new adapter modules here."""

from gotc.adapters import (  # noqa: F401
    calendars,
    demo,
    galaxydigital,
    handsonconnect,
    ics,
    socrata,
    ticketing,
    volo,
)
