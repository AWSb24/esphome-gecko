"""Generate the gecko carrier PCB (KiCad 7) from parts.py: footprints,
nets, board outline, isolation keep-outs and ground pours. Routing is done
afterwards by route.sh (Freerouting).

Run with KiCad's Python: python3 hardware/tools/gen_pcb.py
"""
import json
import os
import sys
import uuid

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
from parts import BOARD_H, BOARD_W, LIB, NETCLASSES, PARTS, PLACEMENT  # noqa: E402
from gen_sch import uid  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "gecko-carrier")
SYS_FP = "/usr/share/kicad/footprints"
OX, OY = 100.0, 100.0  # board origin on the KiCad page


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


WT32_FP = """(footprint "WT32-ETH01_Socket" (version 20221018) (generator gecko_carrier_gen)
  (layer "F.Cu")
  (descr "WT32-ETH01 (ESP32 + LAN8720) on two 1x13 female headers, 22.86 mm row spacing. RJ45 at the +Y end, overhanging the module by about 8 mm. Pad numbering after egnor/wt32-eth01.")
  (tags "WT32-ETH01 ESP32 Ethernet")
  (attr through_hole)
  (fp_text reference "REF**" (at 0 -29) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text value "WT32-ETH01" (at 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_rect (start -13 -27.5) (end 13 27.5) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
  (fp_rect (start -8.89 12.7) (end 8.89 35.56) (stroke (width 0.1) (type dash)) (fill none) (layer "F.Fab"))
  (fp_text user "RJ45" (at 0 24) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))
  (fp_text user "ANT" (at 0 -24.5) (layer "F.SilkS") (effects (font (size 1.2 1.2) (thickness 0.15))))
  (fp_rect (start -13.25 -27.75) (end 13.25 27.75) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
  (fp_line (start -13.4 -20.3) (end -12.4 -20.3) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
{pads})
"""

LEFT = ["CLK_EN", "GND", "3V3", "EN", "IO32", "IO33", "IO5", "IO17", "GND", "3V3", "GND", "5V", "LINK"]
RIGHT_TOP_DOWN = ["IO1", "IO3", "IO0", "GND", "IO39", "IO36", "IO15", "IO14", "IO12", "IO35", "IO4", "IO2", "GND"]


def write_wt32_fp():
    pads = []
    labels = []
    for i in range(13):
        y = -19.05 + 2.54 * i
        n = i + 1
        shape = "rect" if n == 1 else "circle"
        pads.append('  (pad "%d" thru_hole %s (at -11.43 %.2f) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask"))' % (n, shape, y))
        labels.append('  (fp_text user "%s" (at -8.4 %.2f) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.1))))' % (LEFT[i], y))
    for i in range(13):
        y = 11.43 - 2.54 * i  # pad 14 at the bottom right, counting up (DIP order)
        n = 14 + i
        pads.append('  (pad "%d" thru_hole circle (at 11.43 %.2f) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask"))' % (n, y))
    for i, name in enumerate(RIGHT_TOP_DOWN):
        y = -19.05 + 2.54 * i
        labels.append('  (fp_text user "%s" (at 8.4 %.2f) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.1))))' % (name, y))
    d = os.path.join(OUT, LIB + ".pretty")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "WT32-ETH01_Socket.kicad_mod"), "w") as f:
        f.write(WT32_FP.replace("{pads}", "\n".join(labels + pads)))
    return d


def poly(board, pts, layer, net=None, rule=None, name=None, priority=0):
    z = pcbnew.ZONE(board)
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.F_Cu)
        ls.AddLayer(pcbnew.B_Cu)
        z.SetLayerSet(ls)
        z.SetZoneName(rule)
    else:
        z.SetLayer(layer)
        z.SetNet(net)
        z.SetMinThickness(mm(0.25))
        z.SetLocalClearance(mm(0.4))
        z.SetThermalReliefGap(mm(0.4))
        z.SetThermalReliefSpokeWidth(mm(0.5))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetAssignedPriority(priority)
        if name:
            z.SetZoneName(name)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(mm(OX + x), mm(OY + y))
    board.Add(z)
    return z


def rect_edge(board, x0, y0, x1, y1, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(pt(x0, y0))
    s.SetEnd(pt(x1, y1))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(width))
    board.Add(s)


def text(board, t, x, y, size=1.2, layer=pcbnew.F_SilkS, angle=0):
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(t)
    tx.SetPosition(pt(x, y))
    tx.SetLayer(layer)
    tx.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    tx.SetTextThickness(mm(size * 0.15))
    tx.SetTextAngleDegrees(angle)
    board.Add(tx)


def build():
    wt_dir = write_wt32_fp()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_MinClearance = mm(0.2)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.5)

    # Nets
    netnames = sorted({n for p in PARTS for n in p[4].values() if n})
    nets = {}
    for n in netnames:
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        nets[n] = ni

    root = uid("root")
    for ref, sym, value, fpid, pinnets, _ in PARTS:
        lib, name = fpid.split(":")
        libpath = wt_dir if lib == LIB else os.path.join(SYS_FP, lib + ".pretty")
        fp = pcbnew.FootprintLoad(libpath, name)
        if fp is None:
            raise SystemExit("footprint not found: " + fpid)
        fp.SetFPIDAsString(fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPath(pcbnew.KIID_PATH("/" + uid("sym", ref)))
        x, y, rot, side = PLACEMENT[ref]
        board.Add(fp)
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            n = pinnets.get(pad.GetNumber())
            if n:
                pad.SetNet(nets[n])
        if "DNP" in value:
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)

    # Outline with rounded corners kept simple: plain rectangle
    rect_edge(board, 0, 0, BOARD_W, BOARD_H)
    # Milled slot between mains and SELV under the HLK module
    rect_edge(board, 33, 38.5, 35, 59.5)

    # Isolation keep-outs (no tracks, vias or pour; pads allowed)
    poly(board, [(30, 0), (38, 0), (38, BOARD_H), (30, BOARD_H)], None, rule="mains_creepage_8mm")
    poly(board, [(100.8, 0), (103.2, 0), (103.2, 38.8), (BOARD_W, 38.8), (BOARD_W, 41.2),
                 (100.8, 41.2)], None, rule="iso1540_barrier")

    # Ground pours
    gnd_pts = [(38.5, 0.5), (100.3, 0.5), (100.3, 41.7), (BOARD_W - 0.5, 41.7),
               (BOARD_W - 0.5, BOARD_H - 0.5), (38.5, BOARD_H - 0.5)]
    spa_pts = [(103.7, 0.5), (BOARD_W - 0.5, 0.5), (BOARD_W - 0.5, 38.3), (103.7, 38.3)]
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        poly(board, gnd_pts, layer, nets["GND"], name="GND")
        poly(board, spa_pts, layer, nets["GND_SPA"], name="GND_SPA")

    # Silkscreen notes
    text(board, "230V AC", 15, 2.2, 1.5)
    text(board, "!! MAINS !!", 15, 72, 1.5)
    text(board, "8 mm", 34, 72, 1.0)
    text(board, "SPA SIDE", 111.5, 36.5, 1.0)
    text(board, "Gecko CO", 114.8, 20.8, 1.0)
    text(board, "Modbus D1+ D0- 0V", 49, 12.5, 1.0)
    text(board, "TERM", 64, 15, 0.9)
    text(board, "PROG GND TX RX IO0 EN", 108.5, 52, 0.9, angle=90)
    text(board, "gecko-carrier v0.1  esphome-gecko", 78, 2.2, 1.0)

    path = os.path.join(OUT, "gecko-carrier.kicad_pcb")
    board.Save(path)
    return path


def write_project():
    classes = [{
        "name": "Default", "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.7, "via_drill": 0.35,
        "bus_width": 12, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
        "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1, "pcb_color": "rgba(0, 0, 0, 0.000)",
        "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6}]
    patterns = []
    for name, c in NETCLASSES.items():
        d = dict(classes[0])
        d.update(name=name, clearance=c["clearance"], track_width=c["width"],
                 via_diameter=1.0 if name == "Power" else 1.2, via_drill=0.5 if name == "Power" else 0.6)
        classes.append(d)
        patterns += [{"netclass": name, "pattern": n} for n in c["nets"]]
    pro = {
        "board": {"design_settings": {"rules": {
            "min_clearance": 0.2, "min_track_width": 0.2, "min_via_diameter": 0.6, "min_through_hole_diameter": 0.3,
            "min_copper_edge_clearance": 0.5, "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25,
            "min_silk_clearance": 0.0, "min_text_height": 0.8, "min_text_thickness": 0.08,
            "min_via_annular_width": 0.1, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
            "min_resolved_spokes": 1, "solder_mask_clearance": 0.0, "solder_mask_min_width": 0.0,
            "use_height_for_length_calcs": True},
            "rule_severities": {"silk_overlap": "ignore", "silk_over_copper": "ignore", "silk_edge_clearance": "ignore",
                                "lib_footprint_issues": "ignore", "lib_footprint_mismatch": "ignore"}}},
        "meta": {"filename": "gecko-carrier.kicad_pro", "version": 1},
        "net_settings": {"classes": classes, "meta": {"version": 3}, "netclass_patterns": patterns},
        "sheets": [[uid("root"), ""]],
    }
    with open(os.path.join(OUT, "gecko-carrier.kicad_pro"), "w") as f:
        json.dump(pro, f, indent=2)
    with open(os.path.join(OUT, "fp-lib-table"), "w") as f:
        f.write('(fp_lib_table\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")(options "")(descr "Gecko carrier footprints"))\n)\n' % (LIB, LIB))


if __name__ == "__main__":
    print(build())
    write_project()
