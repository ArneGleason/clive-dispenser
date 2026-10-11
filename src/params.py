"""Every dimension that matters, in millimetres.

Coordinates: x = Clive's left/right, y = forward (the way he faces),
z = up. The mechanism is laid out in a "torso frame" (x, u, v) that is
the global frame tilted forward by LEAN degrees about the hip point:
u points out of his belly, v points up his spine.
"""
import math

# --- candy presets --------------------------------------------------------
# Lengths are nominal published/estimated sizes. MEASURE YOUR OWN CANDY and
# edit these before printing; everything else is derived from them.
CANDY = {
    # Wikipedia: 15 x 8 x 5 mm pressed brick.
    "pez": dict(length=15.0, width=8.0, thick=5.0, shape="brick"),
    # Estimated from photos and ~0.5 g mass: an oval pill.
    "tictac": dict(length=12.0, width=7.5, thick=5.5, shape="pill"),
}
CANDY_CLEAR = 0.6          # added to candy length/width for the hopper bore
POCKET_EXTRA = 0.3         # pocket depth = candy thickness + this

# --- pose -----------------------------------------------------------------
LEAN = 32.0                # torso tilt forward, degrees
HIP_Y, HIP_Z = 0.0, 60.0   # torso-frame origin in global coordinates
CA, SA = math.cos(math.radians(LEAN)), math.sin(math.radians(LEAN))

# --- printing tolerances --------------------------------------------------
SLIDE_GAP = 0.3            # per side, sliding fits
PIN_D = 3.0                # pivot axle and tray pin: 3 mm rod / M3 screw / filament
PIN_HOLE = 3.3             # clearance hole for a moving pin
PIN_PRESS = 3.0            # snug hole in the body halves

# --- hopper sleeve (candy-specific bore, universal outside) --------------
SLEEVE_W = 18.0            # x
SLEEVE_D = 11.0            # u
SLEEVE_U = -14.5           # sleeve centre in u
SLEEVE_GAP_BOTTOM = 0.4    # sleeve bottom above tray top
SLEEVE_TOP_V = 38.0        # top of sleeve tube (flange sits here)
FLANGE = 1.5               # flange overhang and thickness

# --- tray (slider) --------------------------------------------------------
TRAY_W = 19.0
TRAY_FLOOR = 1.8
TRAY_H = max(c["thick"] for c in CANDY.values()) + POCKET_EXTRA + TRAY_FLOOR
CHEEK_X0 = 2.75            # inner face of the clevis cheeks (|x|)
CHEEK_X1 = 6.25            # outer face of the clevis cheeks (|x|)

# --- lever (head + leg) ---------------------------------------------------
PIVOT_U, PIVOT_V = 9.0, 38.0
LEG_T = 5.0                # thickness in x
LEG_W = 6.0                # width in u
PIN_V_REST = 6.5           # tray pin height at rest

# --- spring ---------------------------------------------------------------
# Any small compression spring: a ballpoint-pen spring is the target.
SPRING_OD = 4.5
SPRING_D_FROM_PIVOT = 8.0  # where it presses on the leg
SPRING_POCKET = 8.0
SPRING_REST_GAP = 7.0      # leg face to rib face at rest

# --- shell ----------------------------------------------------------------
MIN_WALL = 1.2
GRID = 0.45                # SDF meshing resolution


def to_torso(p):
    x, y, z = p
    dy, dz = y - HIP_Y, z - HIP_Z
    return x, dy * CA - dz * SA, dy * SA + dz * CA


def from_torso(x, u, v):
    return x, HIP_Y + u * CA + v * SA, HIP_Z - u * SA + v * CA


TORSO_TO_GLOBAL = [[1, 0, 0, 0], [0, CA, SA, HIP_Y], [0, -SA, CA, HIP_Z]]


def sleeve_bore(candy):
    c = CANDY[candy]
    return c["length"] + CANDY_CLEAR, c["width"] + CANDY_CLEAR


def candy_checks(candy):
    """Return (ok, messages) for a candy preset."""
    c = CANDY[candy]
    bx, bu = sleeve_bore(candy)
    msgs = []
    ok = True
    diag = math.hypot(c["width"], c["thick"])
    if diag <= bu:
        ok = False
        msgs.append(f"{candy}: can tumble on its edge in the bore ({diag:.1f} <= {bu:.1f})")
    if bx > SLEEVE_W - 2 * 0.8 or bu > SLEEVE_D - 2 * 0.8:
        ok = False
        msgs.append(f"{candy}: bore too big for the sleeve walls")
    depth = c["thick"] + POCKET_EXTRA
    if depth >= 1.5 * c["thick"]:
        ok = False
        msgs.append(f"{candy}: pocket could take two candies")
    msgs.append(f"{candy}: bore {bx:.1f} x {bu:.1f}, pocket depth {depth:.1f}, "
                f"anti-tumble margin {diag - bu:.1f} mm")
    return ok, msgs
