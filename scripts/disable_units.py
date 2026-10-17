"""Disable units in their city config with a reason comment (used when robots.txt or terms forbid a source).
   python scripts/disable_units.py "reason" unit@city [unit@city ...]"""

import re
import sys
from pathlib import Path

reason, units = sys.argv[1], sys.argv[2:]
for u in units:
    sid, city = u.split("@")
    p = Path(f"config/cities/{city}.yaml")
    lines = p.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)- id: " + re.escape(sid) + r"\s*$", line)
        if not m:
            continue
        indent = m.group(1) + "  "
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if re.match(r"^\s*enabled:", nxt):
            lines[i + 1] = f"{indent}enabled: false  # {reason}\n"
        else:
            lines.insert(i + 1, f"{indent}enabled: false  # {reason}\n")
        break
    else:
        print(f"not found: {u}")
        continue
    p.write_text("".join(lines))
    print(f"disabled {u}")
