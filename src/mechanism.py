"""The dispensing mechanism, built as manifold3d solids in the torso frame.

How it works
------------
* A hopper sleeve stands in Clive's back, tilted with his torso.
* A tray slides front-to-back under it. At rest its pocket sits under the
  sleeve and one candy drops in.
* The head is glued to a lever that pivots on an axle in his chest. Push
  the head forward and the lever's leg swings back, dragging the tray out
  through a hatch in his bum: "out pops a sweet".
* A small compression spring (a ballpoint-pen spring) returns everything.
"""
import math

import manifold3d as mf
import numpy as np

import params as P

SEG = 48
DEG = math.pi / 180


# --- small solid helpers (torso frame: x, u, v) ---------------------------
def box(x0, x1, u0, u1, v0, v1):
    return mf.Manifold.cube((x1 - x0, u1 - u0, v1 - v0)).translate((x0, u0, v0))


def cyl_x(u, v, r, x0, x1):
    """Cylinder along x."""
    return mf.Manifold.cylinder(x1 - x0, r, circular_segments=SEG).rotate((0, 90, 0)).translate((x0, u, v))


def cyl_axis(p0, p1, r):
    """Cylinder between two (x, u, v) points."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    h = float(np.linalg.norm(d))
    c = mf.Manifold.cylinder(h, r, circular_segments=SEG)
    z = np.array([0, 0, 1.0])
    axis = np.cross(z, d / h)
    s, cth = np.linalg.norm(axis), float(np.dot(z, d / h))
    if s < 1e-9:
        rot = np.eye(3) if cth > 0 else np.diag([1, -1, -1])
    else:
        k = axis / s
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        rot = np.eye(3) + s * K + (1 - cth) * K @ K
    m = np.hstack([rot, p0[:, None]])
    return c.transform(m.tolist())


def circ(u, v, r):
    return mf.CrossSection.circle(r, SEG).translate((u, v))


def rect(u0, u1, v0, v1):
    return mf.CrossSection.square((u1 - u0, v1 - v0)).translate((u0, v0))


def slab(cs, t):
    """Extrude a (u, v) outline into a solid spanning x = -t..t."""
    return cs.extrude(2 * t).transform([[0, 0, 1, -t], [1, 0, 0, 0], [0, 1, 0, 0]])


def tilt2d(cs, theta_deg):
    return cs.translate((-P.PIVOT_U, -P.PIVOT_V)).rotate(-theta_deg).translate((P.PIVOT_U, P.PIVOT_V))


def hull(*ms):
    return mf.Manifold.batch_hull(list(ms))


def tilt(m, theta_deg):
    """Rotate about the pivot axle; positive tips the head forward."""
    return m.translate((0, -P.PIVOT_U, -P.PIVOT_V)).rotate((-theta_deg, 0, 0)).translate((0, P.PIVOT_U, P.PIVOT_V))


def to_global(m):
    return m.transform(P.TORSO_TO_GLOBAL)


def to_torso_frame(m):
    R = np.array(P.TORSO_TO_GLOBAL, float)[:, :3]
    t = np.array(P.TORSO_TO_GLOBAL, float)[:, 3]
    inv = np.hstack([R.T, (-R.T @ t)[:, None]])
    return m.transform(inv.tolist())


def pin_offset(theta_deg, pin_u, pin_v):
    """Where the lever's pin hole sits after tilting (u, v)."""
    ru, rv = pin_u - P.PIVOT_U, pin_v - P.PIVOT_V
    t = theta_deg * DEG
    return P.PIVOT_U + ru * math.cos(t) + rv * math.sin(t), P.PIVOT_V - ru * math.sin(t) + rv * math.cos(t)


class Design:
    """Derived mechanism geometry. `rear_u` is the furthest-back point of
    Clive's bum across the tray's footprint (from the sculpt)."""

    def __init__(self, rear_u):
        self.rear_u = rear_u
        self.bore_u_max = max(P.sleeve_bore(c)[1] for c in P.CANDY)
        self.pocket_front = P.SLEEVE_U + self.bore_u_max / 2
        # Travel so the whole pocket clears the bum, plus 1 mm.
        self.travel = self.pocket_front - rear_u + 1.0
        self.sleeve_cav_front = P.SLEEVE_U + P.SLEEVE_D / 2 + P.SLIDE_GAP
        self.over = 2.0  # degrees of over-travel the cavities allow at each end
        # Place the pin so the clevis cheeks never reach the sleeve cavity.
        self.pin_u = self.sleeve_cav_front + 0.6 + 4.5 + self.travel + 1.5
        for _ in range(6):
            self.theta = self._solve_theta(self.travel)
            over_travel = self.pin_u - pin_offset(self.theta + self.over, self.pin_u, P.PIN_V_REST)[0]
            self.pin_u = self.sleeve_cav_front + 0.6 + 4.5 + over_travel
        self.theta = self._solve_theta(self.travel)
        vs = [pin_offset(a, self.pin_u, P.PIN_V_REST)[1] for a in np.linspace(-self.over, self.theta + self.over, 60)]
        self.slot_lo = min(vs) - P.PIN_HOLE / 2 - 0.2
        self.slot_hi = max(vs) + P.PIN_HOLE / 2 + 0.2
        self.cheek_top = self.slot_hi + 1.6
        self.tray_front = self.pin_u + 4.5
        self.tray_back = rear_u - 1.5

    def _solve_theta(self, travel):
        lo, hi = 0.0, 80.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if self.pin_u - pin_offset(mid, self.pin_u, P.PIN_V_REST)[0] < travel:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def tray_shift(self, theta):
        return pin_offset(theta, self.pin_u, P.PIN_V_REST)[0] - self.pin_u

    # --- parts --------------------------------------------------------------
    def tray(self, candy):
        c = P.CANDY[candy]
        bx, bu = P.sleeve_bore(candy)
        depth = c["thick"] + P.POCKET_EXTRA
        w = P.TRAY_W / 2
        t = box(-w, w, self.tray_back, self.tray_front, -P.TRAY_H, 0)
        pocket = box(-bx / 2, bx / 2, P.SLEEVE_U - bu / 2, P.SLEEVE_U + bu / 2, -depth, 1)
        # Chamfer the front lip so the next candy rides up instead of snagging.
        front = P.SLEEVE_U + bu / 2
        lip = box(-bx / 2, bx / 2, -0.75, 0.75, -0.75, 0.75).rotate((45, 0, 0)).translate((0, front, 0))
        t = t - pocket - lip
        cheeks = box(-P.CHEEK_X1, P.CHEEK_X1, self.pin_u - 4.5, self.pin_u + 4.5, -1, self.cheek_top)
        cheeks = cheeks - box(-P.CHEEK_X0, P.CHEEK_X0, self.pin_u - 5, self.pin_u + 5, 0, self.cheek_top + 1)
        slot = hull(cyl_x(self.pin_u, self.slot_lo + P.PIN_HOLE / 2, P.PIN_HOLE / 2, -8, 8),
                    cyl_x(self.pin_u, self.slot_hi - P.PIN_HOLE / 2, P.PIN_HOLE / 2, -8, 8))
        return (t + cheeks) - slot

    def sleeve(self, candy):
        bx, bu = P.sleeve_bore(candy)
        w, d = P.SLEEVE_W / 2, P.SLEEVE_D / 2
        v0 = P.SLEEVE_GAP_BOTTOM
        tube = box(-w, w, P.SLEEVE_U - d, P.SLEEVE_U + d, v0, P.SLEEVE_TOP_V)
        f = P.FLANGE
        flange = box(-w - f, w + f, P.SLEEVE_U - d - f, P.SLEEVE_U + d + f, P.SLEEVE_TOP_V, P.SLEEVE_TOP_V + f)
        bore = box(-bx / 2, bx / 2, P.SLEEVE_U - bu / 2, P.SLEEVE_U + bu / 2, v0 - 1, P.SLEEVE_TOP_V + f + 1)
        # Funnel at the top so refills drop in flat.
        funnel = hull(box(-bx / 2, bx / 2, P.SLEEVE_U - bu / 2, P.SLEEVE_U + bu / 2, P.SLEEVE_TOP_V - 2, P.SLEEVE_TOP_V - 1.99),
                      box(-bx / 2 - 1, bx / 2 + 1, P.SLEEVE_U - bu / 2 - 1, P.SLEEVE_U + bu / 2 + 1,
                          P.SLEEVE_TOP_V + f, P.SLEEVE_TOP_V + f + 0.01))
        return tube + flange - bore - funnel

    def lever_profiles(self, grow=0.0):
        """The lever's outline in the (u, v) plane, as convex pieces: leg, post."""
        pu, pv = P.PIVOT_U, P.PIVOT_V
        leg = circ(pu, pv, 5.5 + grow).hull() + circ(self.pin_u, P.PIN_V_REST, 3.6 + grow)
        post_u, post_v = P.PIVOT_U + 1.0, 56.0
        post = circ(pu, pv, 3.5 + grow) + rect(post_u - 3.5 - grow, post_u + 3.5 + grow, post_v - 1, post_v + grow)
        return [leg.hull(), post.hull()]

    def lever_parts(self, grow=0.0, thick_grow=0.0):
        t = P.LEG_T / 2 + thick_grow
        return [slab(p, t) for p in self.lever_profiles(grow)]

    def peg(self, grow=0.0):
        (su, sv), (nu, nv) = self.spring_axis()
        return cyl_axis((0, su - nu * 0.5, sv - nv * 0.5), (0, su + nu * (3.0 + grow), sv + nv * (3.0 + grow)), 1.4 + grow)

    def spring_axis(self):
        """Spring seat on the back of the leg: point and unit direction (u, v) pointing backwards."""
        du, dv = self.pin_u - P.PIVOT_U, P.PIN_V_REST - P.PIVOT_V
        n = math.hypot(du, dv)
        du, dv = du / n, dv / n
        d = P.SPRING_D_FROM_PIVOT
        nu, nv = dv, -du  # perpendicular to the leg, pointing backwards (dv < 0)
        cu, cv = P.PIVOT_U + du * d, P.PIVOT_V + dv * d
        half_w = 5.5 + (3.6 - 5.5) * d / n  # the leg tapers from hub to boss
        return (cu + nu * half_w, cv + nv * half_w), (nu, nv)

    def lever(self):
        leg, post = self.lever_parts()
        peg = self.peg()
        holes = cyl_x(P.PIVOT_U, P.PIVOT_V, P.PIN_HOLE / 2, -9, 9) + cyl_x(self.pin_u, P.PIN_V_REST, P.PIN_HOLE / 2, -9, 9)
        return leg + post + peg - holes

    def head_socket(self):
        _, post = self.lever_parts(grow=0.15, thick_grow=0.15)
        return post

    def pin(self):
        return cyl_x(self.pin_u, P.PIN_V_REST, P.PIN_D / 2, -P.CHEEK_X1 + 0.3, P.CHEEK_X1 - 0.3)

    def axle(self):
        return cyl_x(P.PIVOT_U, P.PIVOT_V, P.PIN_D / 2, -11, 11)

    # --- cavities in the body -----------------------------------------------
    def cavities(self):
        g = P.SLIDE_GAP
        w = P.TRAY_W / 2 + g
        fwd = self.tray_front + self.tray_shift(-self.over) + g
        cav = [box(-w, w, self.tray_back - 40, fwd, -P.TRAY_H - g, 0.25)]
        cw = P.CHEEK_X1 + g + 0.05
        rear = self.pin_u - 4.5 + self.tray_shift(self.theta + self.over) - g
        cav.append(box(-cw, cw, rear, fwd, -1, self.cheek_top + g))
        sw, sd = P.SLEEVE_W / 2 + g, P.SLEEVE_D / 2 + g
        cav.append(box(-sw, sw, P.SLEEVE_U - sd, P.SLEEVE_U + sd, 0, P.SLEEVE_TOP_V + 0.01))
        f = P.FLANGE + g
        cav.append(box(-sw - f, sw + f, P.SLEEVE_U - sd - f, P.SLEEVE_U + sd + f, P.SLEEVE_TOP_V, 90))
        # Lever sweep: hull consecutive poses of each convex piece in 2D, then
        # extrude once so the slot has clean flat sides.
        angles = np.linspace(-self.over, self.theta + self.over, 24)
        sweep = []
        for piece in self.lever_profiles(grow=0.4):
            poses = [tilt2d(piece, a) for a in angles]
            sweep += [a + b for a, b in zip(poses, poses[1:])]
        sweep = mf.CrossSection.batch_boolean([x.hull() for x in sweep], mf.OpType.Add)
        cav.append(slab(sweep, P.LEG_T / 2 + 0.4))
        peg_poses = [tilt(self.peg(grow=0.4), a) for a in angles]
        cav += [hull(a, b) for a, b in zip(peg_poses, peg_poses[1:])]
        # Spring pocket behind the leg.
        (su, sv), (nu, nv) = self.spring_axis()
        r = P.SPRING_OD / 2 + 0.3
        start = (0, su - nu * 1.0, sv - nv * 1.0)
        far = P.SPRING_REST_GAP + P.SPRING_POCKET
        cav.append(cyl_axis(start, (0, su + nu * far, sv + nv * far), r))
        # Axle holes (blind, opened from the split face).
        cav.append(cyl_x(P.PIVOT_U, P.PIVOT_V, P.PIN_PRESS / 2, -11.2, 11.2))
        return mf.Manifold.batch_boolean(cav, mf.OpType.Add)

    def lid_region(self):
        sw, sd = P.SLEEVE_W / 2 + P.SLIDE_GAP + P.FLANGE, P.SLEEVE_D / 2 + P.SLIDE_GAP + P.FLANGE
        c = 0.15
        return box(-sw + c, sw - c, P.SLEEVE_U - sd + c, P.SLEEVE_U + sd - c, P.SLEEVE_TOP_V + P.FLANGE + 0.2, 90)

    def spring_coil(self, theta, turns=9, wire=0.45):
        """Render-only helix between the leg (tilted by theta) and the pocket floor."""
        (su, sv), (nu, nv) = self.spring_axis()
        far = P.SPRING_REST_GAP + P.SPRING_POCKET
        a = np.array([0, su, sv])
        t = theta * DEG
        ru, rv = su - P.PIVOT_U, sv - P.PIVOT_V
        a = np.array([0, P.PIVOT_U + ru * math.cos(t) + rv * math.sin(t), P.PIVOT_V - ru * math.sin(t) + rv * math.cos(t)])
        b = np.array([0, su + nu * far, sv + nv * far])
        axis = (b - a) / np.linalg.norm(b - a)
        e1 = np.array([1.0, 0, 0])
        e2 = np.cross(axis, e1)
        r = P.SPRING_OD / 2 - wire
        n = turns * 20
        pts = [a + (b - a) * i / n + r * (math.cos(2 * math.pi * i / 20) * e1 + math.sin(2 * math.pi * i / 20) * e2)
               for i in range(n + 1)]
        balls = [mf.Manifold.sphere(wire, 10).translate(tuple(p)) for p in pts]
        return mf.Manifold.batch_boolean([hull(x, y) for x, y in zip(balls, balls[1:])], mf.OpType.Add)

    def spring_report(self):
        (su, sv), (nu, nv) = self.spring_axis()
        moved = P.SPRING_D_FROM_PIVOT * (self.theta * DEG)
        rest_len = P.SPRING_REST_GAP + P.SPRING_POCKET
        return dict(rest_length=rest_len, pressed_length=rest_len - moved,
                    recommended_free_length=(rest_len + 3, rest_len + 8), max_od=P.SPRING_OD)
