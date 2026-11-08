"""Simple two-layer grid router for the gecko carrier board.

Freerouting would do a nicer job; this keeps the board reproducible with
nothing but KiCad's Python and numpy. A* on a 0.25 mm grid, 8 directions,
vias between layers, per-netclass width and clearance, keep-out areas
respected. After routing it fills the pours and writes a DRC report.

Run: python3 hardware/tools/route.py
"""
import heapq
import math
import os
import sys

import numpy as np
import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
from parts import BOARD_H, BOARD_W, NETCLASSES, RJ45_NOTCH  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "..", "gecko-carrier", "gecko-carrier.kicad_pcb")
OX, OY = 100.0, 100.0
STEP = 0.25
NX, NY = int(BOARD_W / STEP) + 1, int(BOARD_H / STEP) + 1
EDGE = 0.5
VIA_D, VIA_DRILL = 0.7, 0.35
DEFAULT = (0.25, 0.2)  # width, clearance
CLASS = {}
for cname, c in NETCLASSES.items():
    for n in c["nets"]:
        CLASS[n] = (c["width"], c["clearance"])
MAINS = set(NETCLASSES["Mains"]["nets"])
# Route order: mains, then power, then the rest by length
ORDER_FIRST = ["L_IN", "L_F", "N", "GND_SPA", "SPA_5V", "+5V", "+3V3", "GND"]


def mm(v):
    return pcbnew.FromMM(v)


def to_mm(v):
    return pcbnew.ToMM(v)


def cell(x, y):
    return int(round(x / STEP)), int(round(y / STEP))


def disk(r_mm):
    r = r_mm / STEP
    ri = int(math.ceil(r))
    return [(dx, dy) for dx in range(-ri, ri + 1) for dy in range(-ri, ri + 1) if dx * dx + dy * dy <= r * r]


def dilate(mask, r_mm):
    if r_mm <= 0:
        return mask.copy()
    out = np.zeros_like(mask)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return out
    for dx, dy in disk(r_mm):
        x2, y2 = xs + dx, ys + dy
        ok = (x2 >= 0) & (x2 < NX) & (y2 >= 0) & (y2 < NY)
        out[y2[ok], x2[ok]] = True
    return out


class Router:
    def __init__(self, board):
        self.b = board
        self.netid = {}
        # copper owner per layer: 0 = free, else net index; mains copper tracked separately
        self.cu = [np.zeros((NY, NX), np.int16) for _ in range(2)]
        self.static_block = [np.zeros((NY, NX), bool) for _ in range(2)]  # keepouts, edges, holes
        self.pads = {}  # net -> list of (layers, mask list)
        self._init_edges()
        self._init_keepouts()
        self._init_pads()

    def nid(self, name):
        if name not in self.netid:
            self.netid[name] = len(self.netid) + 1
        return self.netid[name]

    def _rect(self, x0, y0, x1, y1):
        m = np.zeros((NY, NX), bool)
        cx0, cy0 = max(0, int(math.floor(x0 / STEP))), max(0, int(math.floor(y0 / STEP)))
        cx1, cy1 = min(NX - 1, int(math.ceil(x1 / STEP))), min(NY - 1, int(math.ceil(y1 / STEP)))
        m[cy0:cy1 + 1, cx0:cx1 + 1] = True
        return m

    def _init_edges(self):
        e = np.zeros((NY, NX), bool)
        e[:, 0] = e[:, -1] = True
        e[0, :] = e[-1, :] = True
        # milled slot
        e |= self._rect(33, 38.5, 35, 59.5)
        # RJ45 notch
        e |= self._rect(*RJ45_NOTCH)
        self.edge = e

    def _init_keepouts(self):
        for z in self.b.Zones():
            if not z.GetIsRuleArea():
                continue
            o = z.Outline()
            pts = [(to_mm(o.CVertex(i).x) - OX, to_mm(o.CVertex(i).y) - OY) for i in range(o.TotalVertices())]
            m = np.zeros((NY, NX), bool)
            ys, xs = np.mgrid[0:NY, 0:NX]
            px, py = xs * STEP, ys * STEP
            inside = np.zeros((NY, NX), bool)
            n = len(pts)
            j = n - 1
            for i in range(n):
                xi, yi = pts[i]
                xj, yj = pts[j]
                cond = ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-9) + xi)
                inside ^= cond
                j = i
            m |= inside
            for L in range(2):
                self.static_block[L] |= m
        # NPTH holes / mounting holes
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    c = p.GetPosition()
                    x, y = to_mm(c.x) - OX, to_mm(c.y) - OY
                    r = to_mm(max(p.GetSize().x, p.GetSize().y)) / 2 + 0.3
                    m = self._rect(x - r, y - r, x + r, y + r)
                    for L in range(2):
                        self.static_block[L] |= m

    def _pad_mask(self, p):
        bb = p.GetBoundingBox()
        x0, y0 = to_mm(bb.GetLeft()) - OX, to_mm(bb.GetTop()) - OY
        x1, y1 = to_mm(bb.GetRight()) - OX, to_mm(bb.GetBottom()) - OY
        m = np.zeros((NY, NX), bool)
        cx0, cy0 = int(math.floor(x0 / STEP + 0.3)), int(math.floor(y0 / STEP + 0.3))
        cx1, cy1 = int(math.ceil(x1 / STEP - 0.3)), int(math.ceil(y1 / STEP - 0.3))
        if cx1 < cx0 or cy1 < cy0:
            c = cell((x0 + x1) / 2, (y0 + y1) / 2)
            m[c[1], c[0]] = True
        else:
            m[cy0:cy1 + 1, cx0:cx1 + 1] = True
        return m

    def _init_pads(self):
        self.pad_list = []
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    continue
                layers = [L for L, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if p.IsOnLayer(lid)]
                net = p.GetNetname()
                m = self._pad_mask(p)
                n = self.nid(net) if net else -1
                for L in layers:
                    self.cu[L][m] = n if n > 0 else 30000
                c = p.GetPosition()
                self.pad_list.append((net, layers, m, (to_mm(c.x) - OX, to_mm(c.y) - OY), fp.GetReference() + "." + p.GetNumber()))
                if net:
                    self.pads.setdefault(net, []).append(self.pad_list[-1])

    def forbidden(self, net):
        w, c = CLASS.get(net, DEFAULT)
        n = self.netid[net]
        mains_ids = [self.netid[m] for m in MAINS if m in self.netid and m != net]
        out = []
        for L in range(2):
            cu = self.cu[L]
            foreign = (cu != 0) & (cu != n)
            fm = np.isin(cu, mains_ids) if net not in MAINS else np.zeros_like(foreign)
            r = c + w / 2 + STEP * 0.75
            f = dilate(foreign & ~fm, r)
            if fm.any():
                f |= dilate(fm, NETCLASSES["Mains"]["clearance"] + w / 2 + STEP * 0.5)
            if net in MAINS:
                f |= dilate(foreign, NETCLASSES["Mains"]["clearance"] + w / 2 + STEP * 0.5)
            f |= dilate(self.edge, EDGE + w / 2)
            f |= self.static_block[L]
            out.append(f)
        # via needs both layers free of copper within via radius + clearance
        vr = VIA_D / 2 + c + STEP * 0.75
        vb = []
        for L in range(2):
            cu = self.cu[L]
            foreign = (cu != 0) & (cu != n)
            vb.append(dilate(foreign, vr) | dilate(self.edge, EDGE + VIA_D / 2) | self.static_block[L])
        via_block = vb[0] | vb[1]
        return out, via_block

    def route_net(self, net):
        pads = self.pads.get(net, [])
        if len(pads) < 2:
            return True
        n = self.netid[net]
        forb, via_block = self.forbidden(net)
        w, c = CLASS.get(net, DEFAULT)
        no_via = net in MAINS
        # tree starts with the first pad
        tree = [set(), set()]
        first = pads[0]
        for L in first[1]:
            ys, xs = np.nonzero(first[2])
            tree[L].update(zip(xs.tolist(), ys.tolist()))
        remaining = list(pads[1:])
        paths = []
        ok = True
        while remaining:
            # nearest remaining pad to the tree centre
            targets = {}
            for i, pd in enumerate(remaining):
                for L in pd[1]:
                    ys, xs = np.nonzero(pd[2])
                    for x, y in zip(xs.tolist(), ys.tolist()):
                        targets[(L, x, y)] = i
            path = self.astar(tree, targets, forb, via_block, no_via)
            if path is None:
                print("  FAILED", net, [p[4] for p in remaining])
                ok = False
                break
            idx = targets[path[-1]]
            pd = remaining.pop(idx)
            for L in pd[1]:
                ys, xs = np.nonzero(pd[2])
                tree[L].update(zip(xs.tolist(), ys.tolist()))
            for (L, x, y) in path:
                tree[L].add((x, y))
            paths.append((path, pd))
        for path, pd in paths:
            self.commit(net, path, w)
        return ok

    def astar(self, tree, targets, forb, via_block, no_via):
        tx = np.array([k[1] for k in targets])
        ty = np.array([k[2] for k in targets])
        cx, cy = tx.mean(), ty.mean()

        def h(x, y):
            return math.hypot(x - cx, y - cy) * 0.9

        openq = []
        g = {}
        prev = {}
        for L in range(2):
            for (x, y) in tree[L]:
                if forb[L][y, x] and (L, x, y) not in targets:
                    # tree cells inside own pads may sit in dilated zones near neighbours; still allow start
                    pass
                s = (L, x, y)
                g[s] = 0.0
                heapq.heappush(openq, (h(x, y), 0.0, s))
        dirs = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
        VIA_COST = 12.0
        LAYER_BIAS = (1.0, 1.15)
        seen = 0
        while openq:
            f, gc, s = heapq.heappop(openq)
            if gc > g.get(s, 1e18):
                continue
            if s in targets and gc > 0:
                path = [s]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return list(reversed(path))
            seen += 1
            if seen > 2_500_000:
                return None
            L, x, y = s
            for dx, dy, cost in dirs:
                x2, y2 = x + dx, y + dy
                if not (0 <= x2 < NX and 0 <= y2 < NY):
                    continue
                s2 = (L, x2, y2)
                if forb[L][y2, x2] and s2 not in targets:
                    continue
                if dx and dy and (forb[L][y, x2] or forb[L][y2, x]) and s2 not in targets:
                    continue
                ng = gc + cost * LAYER_BIAS[L]
                if ng < g.get(s2, 1e18):
                    g[s2] = ng
                    prev[s2] = s
                    heapq.heappush(openq, (ng + h(x2, y2), ng, s2))
            if not no_via and not via_block[y, x]:
                s2 = (1 - L, x, y)
                if not forb[1 - L][y, x] or s2 in targets:
                    ng = gc + VIA_COST
                    if ng < g.get(s2, 1e18):
                        g[s2] = ng
                        prev[s2] = s
                        heapq.heappush(openq, (ng + h(x, y), ng, s2))
        return None

    def commit(self, net, path, w):
        n = self.netid[net]
        ni = self.b.FindNet(net)
        r = w / 2
        segs = []
        cur = [path[0]]
        for a, b in zip(path, path[1:]):
            if a[0] != b[0]:
                segs.append(cur)
                v = pcbnew.PCB_VIA(self.b)
                v.SetPosition(pcbnew.VECTOR2I(mm(OX + a[1] * STEP), mm(OY + a[2] * STEP)))
                v.SetWidth(mm(VIA_D))
                v.SetDrill(mm(VIA_DRILL))
                v.SetNet(ni)
                self.b.Add(v)
                vm = dilate(self._rect(a[1] * STEP, a[2] * STEP, a[1] * STEP, a[2] * STEP), VIA_D / 2)
                for L in range(2):
                    self.cu[L][vm & (self.cu[L] == 0)] = n
                cur = [b]
            else:
                cur.append(b)
        segs.append(cur)
        for seg in segs:
            if len(seg) < 2:
                continue
            L = seg[0][0]
            # merge collinear runs
            pts = [seg[0]]
            for i in range(1, len(seg) - 1):
                d1 = (seg[i][1] - pts[-1][1], seg[i][2] - pts[-1][2])
                d2 = (seg[i + 1][1] - seg[i][1], seg[i + 1][2] - seg[i][2])
                if d1[0] * d2[1] - d1[1] * d2[0] != 0:
                    pts.append(seg[i])
            pts.append(seg[-1])
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(self.b)
                t.SetStart(pcbnew.VECTOR2I(mm(OX + a[1] * STEP), mm(OY + a[2] * STEP)))
                t.SetEnd(pcbnew.VECTOR2I(mm(OX + b[1] * STEP), mm(OY + b[2] * STEP)))
                t.SetWidth(mm(w))
                t.SetLayer(pcbnew.F_Cu if L == 0 else pcbnew.B_Cu)
                t.SetNet(ni)
                self.b.Add(t)
            # rasterise into copper map
            m = np.zeros((NY, NX), bool)
            for (_, x, y) in seg:
                m[y, x] = True
            m = dilate(m, r)
            self.cu[L][m & (self.cu[L] == 0)] = n
        # connect off-grid pad centres to the grid end points
        for end in (path[0], path[-1]):
            L, x, y = end
            for net2, layers, pm, (px, py), name in self.pads[net]:
                if L in layers and pm[y, x]:
                    gx, gy = x * STEP, y * STEP
                    if abs(gx - px) > 1e-3 or abs(gy - py) > 1e-3:
                        t = pcbnew.PCB_TRACK(self.b)
                        t.SetStart(pcbnew.VECTOR2I(mm(OX + px), mm(OY + py)))
                        t.SetEnd(pcbnew.VECTOR2I(mm(OX + gx), mm(OY + gy)))
                        t.SetWidth(mm(min(w, 0.25) if net not in MAINS else w))
                        t.SetLayer(pcbnew.F_Cu if L == 0 else pcbnew.B_Cu)
                        t.SetNet(ni)
                        self.b.Add(t)
                    break


def net_len(r, net):
    pts = [p[3] for p in r.pads.get(net, [])]
    if len(pts) < 2:
        return 0
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (max(xs) - min(xs)) + (max(ys) - min(ys))


def main():
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        board.Remove(t)
    r = Router(board)
    nets = [n for n in r.pads if n]
    rest = sorted([n for n in nets if n not in ORDER_FIRST], key=lambda n: net_len(r, n))
    order = [n for n in ORDER_FIRST if n in nets] + rest
    failed = []
    for net in order:
        print("routing", net, flush=True)
        if not r.route_net(net):
            failed.append(net)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(PCB)
    # Saving the board rewrites the project file without our net classes
    from gen_pcb import write_project
    write_project()
    rpt = os.environ.get("DRC_REPORT", "/tmp/gecko-drc.rpt")
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print("failed:", failed)
    print("DRC report:", rpt)


if __name__ == "__main__":
    main()
