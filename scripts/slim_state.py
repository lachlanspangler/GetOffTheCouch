"""Copy the pipeline DB for persistence, dropping what every run re-derives anyway.

`events.data` is a full snapshot rebuilt from `source_records` by every build; only the ids, first_seen and
event_members are needed between runs (sticky canonical ids). Dropping it cuts the persisted state ~60%.

    python scripts/slim_state.py data/gotc.db /tmp/state.db
"""

from __future__ import annotations

import sqlite3
import sys


def main(src: str, dst: str) -> int:
    con = sqlite3.connect(src)
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.execute(f"VACUUM INTO '{dst}'")
    con.close()
    out = sqlite3.connect(dst)
    out.execute("UPDATE events SET data = '{}'")
    out.commit()
    out.execute("VACUUM")
    out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
