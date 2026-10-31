"""CI: fail when what the agent can reach differs from the reviewed egress.json.

    python check_egress.py           # in CI
    python check_egress.py --write   # after review, to update egress.json
"""

import json
import sys

from charter import egress_map

from tools import TOOLS


def changes(approved: dict, current: dict) -> list:
    out = []
    for key, row in current.items():
        old = approved.get(key)
        if old is None:
            out.append(f"{key}: new tool, the model can set {', '.join(row['visible']) or 'nothing'}")
            continue
        if added := sorted(set(row["visible"]) - set(old["visible"])):
            out.append(f"{key}: the model can now set {', '.join(added)}")
        for path in sorted(set(old["pinned"]) - set(row["pinned"])):
            out.append(f"{key}: no longer pins {path}")
        if (row["method"], row["url_template"]) != (old["method"], old["url_template"]):
            out.append(f"{key}: now {row['method']} {row['url_template']}")
    out += [f"{key}: removed" for key in sorted(approved.keys() - current.keys())]
    return out


current = egress_map(TOOLS)
if "--write" in sys.argv:
    json.dump(current, open("egress.json", "w"), indent=2)
    sys.exit(0)
found = changes(json.load(open("egress.json")), current)
for line in found:
    print(line)
print("egress widened: needs review" if found else "egress: unchanged")
sys.exit(1 if found else 0)
