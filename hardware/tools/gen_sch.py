"""Generate the KiCad 7 schematic and symbol library from parts.py.

Every pin carries a net label, so connections are by name - no drawn wires.
Run: python3 hardware/tools/gen_sch.py
"""
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
    nl = max([p[3] for p in pins if p[2] == "L"] + [-1]) + 1
    nr = max([p[3] for p in pins if p[2] == "R"] + [-1]) + 1
    n = max(nl, nr)
    top = (n + 1) * G / 2
    w = d["w"]
    out = []
    for num, pname, side, slot in pins:
        y = top - (slot + 1) * G
        if side == "L":
            out.append((num, pname, -w / 2 - G, y, 0, G))
        else:
            out.append((num, pname, w / 2 + G, y, 180, G))
    return out


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
    nl = max([p[3] for p in pins if p[2] == "L"] + [-1]) + 1
    nr = max([p[3] for p in pins if p[2] == "R"] + [-1]) + 1
    h = (max(nl, nr) + 1) * G
    w = d["w"]
    return ("(rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default)) (fill (type background)))"
            % (fmt(-w / 2), fmt(h / 2), fmt(w / 2), fmt(-h / 2)))


def lib_symbol(name, qualified):
    d = SYMBOLS[name]
    full = "%s:%s" % (LIB, name) if qualified else name
    pins = sym_pins(name)
    two = d.get("two_pin")
    names_hide = " (pin_names hide)" if two else " (pin_names (offset 0.762))"
    ref_at = "(at 2.54 1.27 0)" if two else "(at 0 %s 0)" % fmt((len(pins) // 2 + 2) * G)
    val_at = "(at 2.54 -1.27 0)" if two else "(at 0 %s 0)" % fmt(-(len(pins) // 2 + 2) * G)
    just = " (justify left)" if two else ""
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


def main():
    os.makedirs(OUT, exist_ok=True)
    used = sorted({p[1] for p in PARTS})
    # Symbol library file
    with open(os.path.join(OUT, LIB + ".kicad_sym"), "w") as f:
        f.write("(kicad_symbol_lib (version 20220914) (generator gecko_carrier_gen)\n")
        for n in used:
            f.write(lib_symbol(n, False) + "\n")
        f.write(")\n")

    root = uid("root")
    out = ["(kicad_sch (version 20230121) (generator eeschema)",
           "(uuid %s)" % root, '(paper "A3")',
           '(title_block (title "Gecko in.YE-5 carrier: WT32-ETH01, ISO1540, RS485, HLK-PM01") (date "2026-11-08") (rev "0.1")'
           ' (comment 1 "github.com/AWSb24/esphome-gecko - hardware/gecko-carrier")'
           ' (comment 2 "Generated by hardware/tools/gen_sch.py - nets are joined by label name"))',
           "(lib_symbols"]
    for n in used:
        out.append(lib_symbol(n, True))
    out.append(")")

    for ref, sym, value, fp, nets, pos, *_ in PARTS:
        sx, sy = snap(pos[0]), snap(pos[1])
        two = SYMBOLS[sym].get("two_pin")
        pins = sym_pins(sym)
        n = len(pins)
        if two:
            rpos, vpos, just = (sx + 2.54, sy - 1.27), (sx + 2.54, sy + 1.27), " (justify left)"
        else:
            rpos, vpos, just = (sx, sy - (n // 2 + 2) * G), (sx, sy + (n // 2 + 2) * G), ""
        out.append('(symbol (lib_id "%s:%s") (at %s %s 0) (unit 1) (in_bom yes) (on_board yes) (dnp %s) (uuid %s)'
                   % (LIB, sym, fmt(sx), fmt(sy), "yes" if "DNP" in value else "no", uid("sym", ref)))
        out.append('(property "Reference" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))%s))' % (ref, fmt(rpos[0]), fmt(rpos[1]), just))
        out.append('(property "Value" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))%s))' % (value, fmt(vpos[0]), fmt(vpos[1]), just))
        out.append('(property "Footprint" "%s" (at %s %s 0) %s)' % (fp, fmt(sx), fmt(sy), FONT_HIDE))
        out.append('(property "Datasheet" "~" (at %s %s 0) %s)' % (fmt(sx), fmt(sy), FONT_HIDE))
        for p in pins:
            out.append('(pin "%s" (uuid %s))' % (p[0], uid("pin", ref, p[0])))
        out.append('(instances (project "gecko-carrier" (path "/%s" (reference "%s") (unit 1))))' % (root, ref))
        out.append(")")
        # labels / no-connects at each pin end
        for num, pname, px, py, ang, ln in pins:
            x, y = sx + px, sy - py
            net = nets.get(num)
            if net is None:
                out.append("(no_connect (at %s %s) (uuid %s))" % (fmt(x), fmt(y), uid("nc", ref, num)))
                continue
            if ang == 0:      # pin on the left, label goes left
                la, j = 180, "right"
            elif ang == 180:
                la, j = 0, "left"
            elif ang == 270:  # top pin of a two-pin part
                la, j = 90, "left"
            else:
                la, j = 270, "right"
            out.append('(label "%s" (at %s %s %d) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid %s))'
                       % (net, fmt(x), fmt(y), la, j, uid("lbl", ref, num)))

    notes = [
        (30, 30, "230 V AC - mains section. Keep >= 8 mm creepage to everything else (milled slot under PS1)."),
        (200, 30, "Galvanic isolation: ESP side (GND) | spa side (GND_SPA), barrier under U2."),
        (200, 120, "RS485 / Modbus RTU to the pump drives. Fit JP1 at the bus end only."),
        (30, 120, "WT32-ETH01 plugs into two 1x13 female headers. 5 V only (never 5 V and 3V3 at once)."),
    ]
    for x, y, t in notes:
        out.append('(text "%s" (at %s %s 0) (effects (font (size 2 2)) (justify left bottom)) (uuid %s))' % (t, fmt(x), fmt(y), uid("txt", t)))

    out.append('(sheet_instances (path "/" (page "1")))')
    out.append(")")
    with open(os.path.join(OUT, "gecko-carrier.kicad_sch"), "w") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(OUT, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.kicad_sym")(options "")(descr "Gecko carrier parts"))\n)\n' % (LIB, LIB))
    print("schematic written")


if __name__ == "__main__":
    main()
