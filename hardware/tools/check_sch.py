"""Compare the schematic's netlist (kicad-cli) with the nets in parts.py."""
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(__file__))
from parts import PARTS  # noqa: E402

SCH = os.path.join(os.path.dirname(__file__), "..", "gecko-carrier", "gecko-carrier.kicad_sch")
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, "net.xml")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH], check=True,
                   stdout=subprocess.DEVNULL)
    root = ET.parse(out).getroot()
got = set()
for n in root.find("nets"):
    nodes = frozenset((x.get("ref"), x.get("pin")) for x in n if not x.get("ref").startswith("#"))
    if len(nodes) > 1:
        got.add(nodes)
want = {}
for ref, _, _, _, nets, _ in PARTS:
    for pin, net in nets.items():
        if net:
            want.setdefault(net, set()).add((ref, pin))
want = {frozenset(v) for v in want.values() if len(v) > 1}
ok = True
for w in want - got:
    ok = False
    print("MISSING/SPLIT:", sorted(w))
for g in got - want:
    ok = False
    print("UNEXPECTED:", sorted(g))
print("schematic matches parts.py" if ok else "MISMATCH")
sys.exit(0 if ok else 1)
