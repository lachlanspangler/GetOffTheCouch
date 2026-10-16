"""Pittsburgh (batch A): Localist ``types`` (any-of event-type filter) used by ``pitt_events``.

Pitt's calendar has no "general public" audience, so the unit asks for several public event types at once. Localist
ORs repeated ``type[]=`` values; a repeated plain ``type=`` ANDs them (verified live: 35 + 5 items → ``type=`` both:
5, ``type[]=`` both: 40), so the adapter must send ``type[]``. No network: a canned transport records the URL.
"""

from gotc.adapters.base import get_adapter
from gotc.settings import Settings
from tests.adapters._util import client, fetch_ctx, unit
from tests.conftest import FixtureTransport

PITT = unit("pitt_events")


def test_types_are_sent_as_type_brackets(tmp_path):
    t = FixtureTransport().add(r"calendar\.pitt\.edu/api/2/events", {"events": [], "page": {"total": 1}})
    fr = get_adapter("localist").fetch(fetch_ctx(PITT, client(t, tmp_path), Settings(data_dir=tmp_path)))
    assert len(fr.payloads) == 1
    url = next(c for c in t.calls if "/api/2/events" in c)
    for type_id in PITT.source.params["types"]:
        assert f"type%5B%5D={type_id}" in url
    assert "type=" not in url.replace("type%5B%5D=", "")  # never the AND-ing plain form
    assert "days=30" in url and "pp=100" in url and "page=1" in url
