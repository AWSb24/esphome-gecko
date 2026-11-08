"""Generate the KiCad 7 schematic and symbol library from parts.py.

Every pin carries a net label, so connections are by name - no drawn wires.
Run: python3 hardware/tools/gen_sch.py
"""
import math
import os
import uuid
import sys

sys.path.insert(0, os.path.dirname(__file__))
from parts import LIB, PARTS, SYMBOLS  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "gecko-carrier")
NS = uuid.UUID("6f1c3a1e-7b55-4c1a-9a4e-0c0ffee0b0a7")
G = 2.54


def uid(*k):
    return str(uuid.uuid5(NS, "/".join(map(str, k))))


def snap(v):
    return round(v / G) * G


def fmt(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


FONT = "(effects (font (size 1.27 1.27)))"
FONT_HIDE = "(effects (font (size 1.27 1.27)) hide)"


def sym_pins(name):
    """Return list of (number, name, x, y, angle, length) in symbol coords (y up)."""
    d = SYMBOLS[name]
    if d.get("two_pin"):
        return [("1", "~", 0, 3.81, 270, 1.27), ("2", "~", 0, -3.81, 90, 1.27)]
    pins = d["pins"]
    if not pins:
        return []
    top, w = box(name)
    tp, bp = pads(name)
    out = []
    for num, pname, side, slot in pins:
        if side == "L":
            out.append((num, pname, -w / 2 - G, top - (slot + 1) * G, 0, G))
        elif side == "R":
            out.append((num, pname, w / 2 + G, top - (slot + 1) * G, 180, G))
        elif side == "T":
            out.append((num, pname, -w / 2 + (slot + 1) * G, top + tp + G, 270, G))
        else:
            out.append((num, pname, -w / 2 + (slot + 1) * G, -top - bp - G, 90, G))
    return out


def pads(name):
    """Extra body height above/below the L/R pin rows so vertical T/B pin names fit."""
    pins = SYMBOLS[name]["pins"]
    tp = 2 * G if any(q[2] == "T" for q in pins) else 0
    bp = 2 * G if any(q[2] == "B" for q in pins) else 0
    return tp, bp


def box(name):
    d = SYMBOLS[name]
    pins = d["pins"]
    n = max([p[3] for p in pins if p[2] in "LR"] + [-1]) + 1
    return (n + 1) * G / 2, d["w"]


def body(name):
    d = SYMBOLS[name]
    if d.get("two_pin"):
        if name == "C" or name == "CP":
            s = ("(polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))\n"
                 "(polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))\n"
                 "(polyline (pts (xy 0 2.54) (xy 0 0.762)) (stroke (width 0) (type default)) (fill (type none)))\n"
                 "(polyline (pts (xy 0 -2.54) (xy 0 -0.762)) (stroke (width 0) (type default)) (fill (type none)))")
            if name == "CP":
                s += "\n(text \"+\" (at -1.524 1.778 0) (effects (font (size 1.27 1.27))))"
            return s
        s = "(rectangle (start -1.016 -2.54) (end 1.016 2.54) (stroke (width 0.254) (type default)) (fill (type none)))"
        if name == "Fuse":
            s += "\n(polyline (pts (xy 0 2.54) (xy 0 -2.54)) (stroke (width 0) (type default)) (fill (type none)))"
        if name == "Varistor":
            s += "\n(polyline (pts (xy -1.905 -1.905) (xy -1.27 -1.905) (xy 1.905 1.905)) (stroke (width 0) (type default)) (fill (type none)))"
        return s
    pins = d["pins"]
    if not pins:
        return "(circle (center 0 0) (radius 1.6) (stroke (width 0.254) (type default)) (fill (type none)))"
    top, w = box(name)
    tp, bp = pads(name)
    return ("(rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default)) (fill (type background)))"
            % (fmt(-w / 2), fmt(top + tp), fmt(w / 2), fmt(-top - bp)))


def lib_symbol(name, qualified):
    d = SYMBOLS[name]
    full = "%s:%s" % (LIB, name) if qualified else name
    pins = sym_pins(name)
    two = d.get("two_pin")
    names_hide = " (pin_names hide)" if two else " (pin_names (offset 0.762))"
    if two:
        ref_at, val_at, just = "(at 2.54 1.27 0)", "(at 2.54 -1.27 0)", " (justify left)"
    else:
        top, w = box(name)
        tp, bp = pads(name)
        ref_at = "(at %s %s 0)" % (fmt(-w / 2 - 0.5), fmt(top + tp + 1.27))
        val_at = "(at %s %s 0)" % (fmt(-w / 2 - 0.5), fmt(-top - bp - 1.27))
        just = " (justify right)"
    lines = ['(symbol "%s"%s%s (in_bom yes) (on_board yes)' % (full, " (pin_numbers hide)" if two else "", names_hide)]
    lines.append('(property "Reference" "%s" %s (effects (font (size 1.27 1.27))%s))' % (d["prefix"], ref_at, just))
    lines.append('(property "Value" "%s" %s (effects (font (size 1.27 1.27))%s))' % (name, val_at, just))
    lines.append('(property "Footprint" "" (at 0 0 0) %s)' % FONT_HIDE)
    lines.append('(property "Datasheet" "~" (at 0 0 0) %s)' % FONT_HIDE)
    lines.append('(symbol "%s_0_1" %s)' % (name, body(name)))
    pl = []
    for num, pname, x, y, ang, ln in pins:
        pl.append('(pin passive line (at %s %s %d) (length %s) (name "%s" %s) (number "%s" %s))'
                  % (fmt(x), fmt(y), ang, fmt(ln), pname, FONT, num, FONT))
    lines.append('(symbol "%s_1_1" %s)' % (name, "\n".join(pl)))
    lines.append(")")
    return "\n".join(lines)




# ---------------------------------------------------------------------------
# Drawn schematic: placement, wires, power symbols, junctions
# ---------------------------------------------------------------------------

# ref -> (x, y, rotation, mirror)
SCH = {
    # Mains
    "J1": (40.64, 70.0, 0, True),
    "F1": (60.96, 68.73, 90, False),
    "RV1": (76.2, 80.01, 0, False),
    "PS1": (100.33, 70.0, 0, False),
    "C1": (127.0, 76.2, 0, False),
    "C2": (142.24, 76.2, 0, False),
    # WT32
    "U1": (101.6, 190.5, 0, False),
    "J4": (152.4, 180.34, 0, False),
    # I2C isolation
    "U2": (264.16, 76.2, 0, False),
    "R1": (243.84, 64.77, 0, False),
    "R2": (233.68, 64.77, 0, False),
    "C3": (210.82, 66.04, 0, False),
    "R3": (287.02, 66.04, 0, False),
    "R4": (289.56, 90.17, 0, False),
    "C4": (302.26, 59.69, 0, False),
    "J2": (320.04, 76.2, 0, False),
    # RS485
    "U3": (264.16, 190.5, 0, False),
    "C5": (243.84, 175.26, 0, False),
    "R6": (284.48, 182.88, 0, False),
    "R7": (289.56, 198.12, 0, False),
    "R5": (302.26, 182.88, 180, False),
    "JP1": (323.85, 177.8, 0, False),
    "D1": (309.88, 213.36, 0, False),
    "J3": (340.36, 191.77, 0, False),
    # Mechanics
    "H1": (355.6, 228.6, 0, False),
    "H2": (365.76, 228.6, 0, False),
    "H3": (375.92, 228.6, 0, False),
    "H4": (386.08, 228.6, 0, False),
}

# Where to put the value text when the default (below-left) collides with wiring.
VALUE_POS = {"J3": "below", "J4": "below", "JP1": "below", "PS1": "above"}

POWER_NETS = {"+5V": "up", "+3V3": "up", "SPA_5V": "up", "GND": "down", "GND_SPA": "down"}


def rot(x, y, a):
    a = a % 360
    if a == 0:
        return x, y
    if a == 90:
        return -y, x
    if a == 180:
        return -x, -y
    return y, -x


class Sheet:
    def __init__(self):
        self.parts = {p[0]: p for p in PARTS}
        self.wires = []
        self.items = []  # extra s-expressions
        self.pwr_n = 0
        self.pins_xy = {}
        self.label_pts = set()
        for ref, (x, y, a, m) in SCH.items():
            sym = self.parts[ref][1]
            for num, pname, px, py, ang, ln in sym_pins(sym):
                if m:
                    px = -px
                    ang = (180 - ang) % 360
                X, Y = rot(px, py, a)
                dx, dy = rot(-math.cos(math.radians(ang)), -math.sin(math.radians(ang)), a)
                self.pins_xy[(ref, num)] = ((round(x + X, 3), round(y - Y, 3)), (round(dx), round(-dy)))

    def P(self, ref, num):
        return self.pins_xy[(ref, num)][0]

    def wire(self, *pts):
        pts = [self.P(*p) if isinstance(p[0], str) else p for p in pts]
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.wires.append((tuple(round(v, 3) for v in a), tuple(round(v, 3) for v in b)))

    def stub(self, ref, num, length=2.54):
        (x, y), (dx, dy) = self.pins_xy[(ref, num)]
        end = (round(x + dx * length, 3), round(y + dy * length, 3))
        self.wire((x, y), end)
        return end, (dx, dy)

    def power(self, net, at, direction):
        """Power symbol at `at`, body pointing along `direction` (sheet vector)."""
        body = (0, 1) if POWER_NETS[net] == "up" else (0, -1)  # lib coords
        want = (direction[0], -direction[1])
        ang = next(a for a in (0, 90, 180, 270) if tuple(round(v) for v in rot(*body, a)) == want)
        self.pwr_n += 1
        ref = "#PWR%02d" % self.pwr_n
        u = uid("pwr", self.pwr_n)
        vx, vy = rot(0, 3.0 if POWER_NETS[net] == "up" else -3.3, ang)
        self.items.append(
            '(symbol (lib_id "%s:PWR_%s") (at %s %s %d) (unit 1) (in_bom no) (on_board yes) (dnp no) (uuid %s)\n'
            '(property "Reference" "%s" (at %s %s 0) (effects (font (size 1.27 1.27)) hide))\n'
            '(property "Value" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))))\n'
            '(property "Footprint" "" (at %s %s 0) %s)\n(property "Datasheet" "" (at %s %s 0) %s)\n'
            '(pin "1" (uuid %s))\n'
            '(instances (project "gecko-carrier" (path "/%s" (reference "%s") (unit 1)))))'
            % (LIB, pwr_name(net), fmt(at[0]), fmt(at[1]), ang, u, ref, fmt(at[0]), fmt(at[1]), net,
               fmt(at[0] + vx), fmt(at[1] - vy), fmt(at[0]), fmt(at[1]), FONT_HIDE, fmt(at[0]), fmt(at[1]), FONT_HIDE,
               uid("pwrpin", self.pwr_n), uid("root"), ref))

    def pwr(self, ref, num, net, length=2.54, bend=False):
        end, d = self.stub(ref, num, length)
        if bend and d[1] == 0:
            up = POWER_NETS[net] == "up"
            nd = (0, -1) if up else (0, 1)
            end2 = (end[0], round(end[1] + nd[1] * 2.54, 3))
            self.wire(end, end2)
            end, d = end2, nd
        self.power(net, end, d)

    def pwr_group(self, pins, net, at_index=0):
        ends = [self.stub(ref, num)[0] for ref, num in pins]
        d = self.pins_xy[pins[0]][1]
        self.wire(ends[0], ends[-1])
        self.power(net, ends[at_index], d)

    def label(self, ref, num, net, length=5.08):
        end, (dx, dy) = self.stub(ref, num, length)
        self.label_at(net, end, (dx, dy))

    def label_at(self, net, at, d):
        self.label_pts.add((round(at[0], 3), round(at[1], 3)))
        if d == (-1, 0):
            a, j = 180, "right"
        elif d == (1, 0):
            a, j = 0, "left"
        elif d == (0, -1):
            a, j = 90, "left"
        else:
            a, j = 270, "right"
        self.items.append('(label "%s" (at %s %s %d) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid %s))'
                          % (net, fmt(at[0]), fmt(at[1]), a, j, uid("lbl", net, at)))

    def nc(self, ref, num):
        x, y = self.P(ref, num)
        self.items.append("(no_connect (at %s %s) (uuid %s))" % (fmt(x), fmt(y), uid("nc", ref, num)))

    def split(self):
        """Break wires at every wire end or pin lying on their interior, so
        KiCad sees T-connections as real connections."""
        nodes = {p for w in self.wires for p in w} | {v[0] for v in self.pins_xy.values()} | self.label_pts
        out = []
        for a, b in self.wires:
            inner = [p for p in nodes if p not in (a, b) and on_segment(p, a, b)]
            inner.sort(key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
            pts = [a] + inner + [b]
            out += list(zip(pts, pts[1:]))
        self.wires = out

    def junctions(self):
        ends = {}
        for a, b in self.wires:
            for p in (a, b):
                ends[p] = ends.get(p, 0) + 1
        pins = {v[0] for v in self.pins_xy.values()}
        out = set()
        for p, n in ends.items():
            if n + (1 if p in pins else 0) >= 3:
                out.add(p)
            for a, b in self.wires:
                if p in (a, b):
                    continue
                if on_segment(p, a, b):
                    out.add(p)
        return out


def on_segment(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) > 1e-6:
        return False
    return min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6 and min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6


def pwr_name(net):
    return net.replace("+", "P")


def power_lib(net, qualified):
    name = "PWR_" + pwr_name(net)
    full = "%s:%s" % (LIB, name) if qualified else name
    if POWER_NETS[net] == "up":
        g = ("(polyline (pts (xy -0.762 1.27) (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))\n"
             "(polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))")
        pa = 90
    else:
        g = ("(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27)) "
             "(stroke (width 0) (type default)) (fill (type none)))")
        pa = 270
    return ('(symbol "%s" (power) (pin_names (offset 0)) (in_bom yes) (on_board yes)\n'
            '(property "Reference" "#PWR" (at 0 0 0) %s)\n(property "Value" "%s" (at 0 3.5 0) %s)\n'
            '(property "Footprint" "" (at 0 0 0) %s)\n(property "Datasheet" "" (at 0 0 0) %s)\n'
            '(symbol "%s_0_1" %s)\n'
            '(symbol "%s_1_1" (pin power_in line (at 0 0 %d) (length 0) hide (name "%s" %s) (number "1" %s))))'
            % (full, FONT_HIDE, net, FONT, FONT_HIDE, FONT_HIDE, name, g, name, pa, net, FONT, FONT))


def draw(S):
    W = S.wire
    # ---- Mains ----
    W(("J1", "1"), ("F1", "1"))
    lf = S.P("RV1", "1")[0]
    W(("F1", "2"), ("PS1", "1"))
    W((lf, S.P("PS1", "1")[1]), ("RV1", "1"))
    n_y = 88.9
    a = S.P("J1", "2")
    W(a, (a[0] + 5.08, a[1]), (a[0] + 5.08, n_y), (lf, n_y), ("RV1", "2"))
    b = S.P("PS1", "2")
    W((lf, n_y), (b[0] - 3.81, n_y), (b[0] - 3.81, b[1]), b)
    v = S.P("PS1", "4")
    rail_end = (S.P("C2", "1")[0] + 7.62, v[1])
    W(v, rail_end)
    for c in ("C1", "C2"):
        W((c, "1"), (S.P(c, "1")[0], v[1]))
        S.pwr(c, "2", "GND")
    S.power("+5V", rail_end, (0, -1))
    S.pwr("PS1", "3", "GND", bend=True)

    # ---- WT32 ----
    S.pwr("U1", "12", "+5V")
    S.pwr_group([("U1", "3"), ("U1", "10")], "+3V3")
    S.pwr_group([("U1", "2"), ("U1", "9"), ("U1", "11"), ("U1", "14"), ("U1", "23")], "GND", at_index=2)
    for num in ("1", "13", "15", "17", "18", "19", "20", "21", "22"):
        S.nc("U1", num)
    S.label("U1", "4", "EN")
    S.label("U1", "5", "SCL_ESP")
    S.label("U1", "6", "RS485_DE")
    S.label("U1", "7", "RS485_RO")
    S.label("U1", "8", "RS485_DI")
    S.label("U1", "16", "SDA_ESP")
    for u, j in (("26", "2"), ("25", "3"), ("24", "4")):
        W(("U1", u), ("J4", j))
    S.pwr("J4", "1", "GND", bend=True)
    S.label("J4", "5", "EN", 7.62)

    # ---- I2C isolation ----
    sda1, scl1 = S.P("U2", "2"), S.P("U2", "3")
    xl = 226.06
    W(sda1, (xl, sda1[1]))
    W(scl1, (xl, scl1[1]))
    S.label_at("SDA_ESP", (xl, sda1[1]), (-1, 0))
    S.label_at("SCL_ESP", (xl, scl1[1]), (-1, 0))
    W(("R1", "2"), (S.P("R1", "2")[0], sda1[1]))
    W(("R2", "2"), (S.P("R2", "2")[0], scl1[1]))  # crosses SDA without connecting
    S.pwr("R1", "1", "+3V3")
    S.pwr("R2", "1", "+3V3")
    S.pwr("U2", "1", "+3V3")
    S.pwr("U2", "4", "GND")
    S.pwr("C3", "1", "+3V3")
    S.pwr("C3", "2", "GND")
    S.pwr("U2", "8", "SPA_5V")
    S.pwr("U2", "5", "GND_SPA")
    W(("U2", "7"), ("J2", "3"))
    W(("R3", "2"), (S.P("R3", "2")[0], S.P("U2", "7")[1]))
    S.pwr("R3", "1", "SPA_5V")
    s2 = S.P("U2", "6")
    j2 = S.P("J2", "2")
    yb = 100.33
    W(s2, (s2[0] + 5.08, s2[1]), (s2[0] + 5.08, yb), (j2[0] + 12.7, yb), (j2[0] + 12.7, j2[1]), j2)
    W(("R4", "2"), (S.P("R4", "2")[0], yb))
    S.pwr("R4", "1", "SPA_5V")
    S.pwr("C4", "1", "SPA_5V")
    S.pwr("C4", "2", "GND_SPA")
    S.pwr("J2", "4", "SPA_5V")
    S.pwr("J2", "8", "GND_SPA", bend=True)
    for n in ("1", "5", "7", "6"):
        S.nc("J2", n)

    # ---- RS485 ----
    S.label("U3", "1", "RS485_RO", 15.24)
    re_, de = S.P("U3", "2"), S.P("U3", "3")
    W(re_, (re_[0] - 2.54, re_[1]), (de[0] - 2.54, de[1]))
    de_end = (de[0] - 15.24, de[1])
    W(de, de_end)
    S.label_at("RS485_DE", de_end, (-1, 0))
    S.label("U3", "4", "RS485_DI", 15.24)
    S.pwr("U3", "8", "+3V3")
    S.pwr("U3", "5", "GND")
    W(("U3", "6"), ("J3", "1"))
    W(("U3", "7"), ("J3", "2"))
    S.pwr("J3", "3", "GND", bend=True)
    ya, yb = S.P("U3", "6")[1], S.P("U3", "7")[1]
    W(("R6", "2"), (S.P("R6", "2")[0], ya))
    S.pwr("R6", "1", "+3V3")
    W(("R7", "1"), (S.P("R7", "1")[0], yb))
    S.pwr("R7", "2", "GND")
    W(("R5", "1"), (S.P("R5", "1")[0], ya))
    t = S.P("R5", "2")
    j1 = S.P("JP1", "1")
    W(t, (t[0], j1[1]), j1)
    j2p = S.P("JP1", "2")
    xb = j2p[0] - 2.54
    W(j2p, (xb, j2p[1]), (xb, yb))
    S.pwr("C5", "1", "+3V3")
    S.pwr("C5", "2", "GND")
    S.label("D1", "1", "RS485_A")
    S.label("D1", "2", "RS485_B")
    S.pwr("D1", "3", "GND", bend=True)
    x0 = S.P("U3", "6")[0]
    S.label_at("RS485_A", (x0 + 2.54, ya), (0, -1))
    S.label_at("RS485_B", (x0 + 5.08, yb), (0, 1))


def main():
    os.makedirs(OUT, exist_ok=True)
    used = sorted({p[1] for p in PARTS})
    with open(os.path.join(OUT, LIB + ".kicad_sym"), "w") as f:
        f.write("(kicad_symbol_lib (version 20220914) (generator gecko_carrier_gen)\n")
        for n in used:
            f.write(lib_symbol(n, False) + "\n")
        for net in POWER_NETS:
            f.write(power_lib(net, False) + "\n")
        f.write(")\n")

    S = Sheet()
    draw(S)
    S.split()
    root = uid("root")
    out = ["(kicad_sch (version 20230121) (generator eeschema)",
           "(uuid %s)" % root, '(paper "A3")',
           '(title_block (title "Gecko in.YE-5 carrier: WT32-ETH01, ISO1540, RS485, HLK-PM01") (date "2026-11-08") (rev "0.2")'
           ' (comment 1 "github.com/AWSb24/esphome-gecko - hardware/gecko-carrier")'
           ' (comment 2 "Generated by hardware/tools/gen_sch.py"))',
           "(lib_symbols"]
    for n in used:
        out.append(lib_symbol(n, True))
    for net in POWER_NETS:
        out.append(power_lib(net, True))
    out.append(")")

    for ref, sym, value, fp, nets, _ in PARTS:
        x, y, a, m = SCH[ref]
        two = SYMBOLS[sym].get("two_pin")
        n = len(sym_pins(sym))
        vjust = None
        if two:
            if a in (90, 270):
                rpos, vpos, just = (x, y - 2.54), (x, y + 2.54), ""
            else:
                rpos, vpos, just = (x + 2.54, y - 1.27), (x + 2.54, y + 1.27), " (justify left)"
        else:
            top, w = box(sym)
            tp, bp = pads(sym)
            rpos, vpos, just = (x - w / 2 - 0.5, y - top - tp - 1.27), (x - w / 2 - 0.5, y + top + bp + 1.27), " (justify right)"
            vjust = just
            if VALUE_POS.get(ref) == "below":
                vpos, vjust = (x - w / 2, y + top + bp + 2.54), " (justify left)"
            elif VALUE_POS.get(ref) == "above":
                vpos, vjust = (x - w / 2, y - top - tp - 3.81), " (justify left)"
        mir = " (mirror y)" if m else ""
        out.append('(symbol (lib_id "%s:%s") (at %s %s %d)%s (unit 1) (in_bom yes) (on_board yes) (dnp %s) (uuid %s)'
                   % (LIB, sym, fmt(x), fmt(y), a, mir, "yes" if "DNP" in value else "no", uid("sym", ref)))
        fa = a if (two and a in (90, 270)) else 0
        out.append('(property "Reference" "%s" (at %s %s %d) (effects (font (size 1.27 1.27))%s))' % (ref, fmt(rpos[0]), fmt(rpos[1]), fa, just))
        out.append('(property "Value" "%s" (at %s %s %d) (effects (font (size 1.27 1.27))%s))' % (value, fmt(vpos[0]), fmt(vpos[1]), fa, vjust or just))
        out.append('(property "Footprint" "%s" (at %s %s 0) %s)' % (fp, fmt(x), fmt(y), FONT_HIDE))
        out.append('(property "Datasheet" "~" (at %s %s 0) %s)' % (fmt(x), fmt(y), FONT_HIDE))
        for p in sym_pins(sym):
            out.append('(pin "%s" (uuid %s))' % (p[0], uid("pin", ref, p[0])))
        out.append('(instances (project "gecko-carrier" (path "/%s" (reference "%s") (unit 1))))' % (root, ref))
        out.append(")")

    for a, b in S.wires:
        out.append("(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))"
                   % (fmt(a[0]), fmt(a[1]), fmt(b[0]), fmt(b[1]), uid("w", a, b)))
    for p in sorted(S.junctions()):
        out.append("(junction (at %s %s) (diameter 0) (color 0 0 0 0) (uuid %s))" % (fmt(p[0]), fmt(p[1]), uid("j", p)))
    out += S.items

    notes = [
        (25.4, 40.64, "Mains 230 V AC. >= 8 mm creepage to everything else (keep-out + milled slot under PS1)."),
        (205.74, 40.64, "I2C isolation: ESP side (GND) | spa side (GND_SPA). R3/R4 not fitted - the pack has pull-ups."),
        (25.4, 152.4, "WT32-ETH01 on two 1x13 sockets. Powered on 5V only (never 5V and 3V3 together)."),
        (205.74, 160.02, "RS485 / Modbus RTU to the pump drives. JP1 = 120R termination, fit at the bus end."),
    ]
    for x, y, t in notes:
        out.append('(text "%s" (at %s %s 0) (effects (font (size 2 2)) (justify left bottom)) (uuid %s))' % (t, fmt(x), fmt(y), uid("txt", t)))
    out.append('(sheet_instances (path "/" (page "1")))')
    out.append(")")
    with open(os.path.join(OUT, "gecko-carrier.kicad_sch"), "w") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(OUT, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.kicad_sym")(options "")(descr "Gecko carrier parts"))\n)\n' % (LIB, LIB))
    print("schematic written: %d wires, %d junctions, %d power symbols" % (len(S.wires), len(S.junctions()), S.pwr_n))


if __name__ == "__main__":
    main()
