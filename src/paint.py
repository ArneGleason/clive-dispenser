"""Full-colour paint job for colour 3D printing and renders.

Starts from the flat region colours in gnome.PAINT and layers on what a
painter (and a few years in a garden) would add:

* painted details: eyes with a glint, the wink, blush on cheeks, nose, ears,
  knees and bum, stitches on the patch, holes in the buttons;
* exaggerated ambient occlusion and cavity grime so creases and folds read
  even at 15 cm tall;
* edge wear: paint chipped off high points, showing pale plaster;
* mottling and fine speckle, like the ad's vintage print.

Everything is computed per vertex from the same signed distance fields that
shape Clive, so it lines up exactly with the geometry.
"""
import math

import numpy as np

import gnome
from noise import fbm
from params import to_torso

PLASTER = np.array([0.93, 0.90, 0.84])
GRIME = np.array([0.24, 0.19, 0.13])
INSIDE = np.array([0.86, 0.85, 0.82])
LETTERING = np.array([0.08, 0.06, 0.05])


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def _mix(c, target, amount):
    amount = np.clip(amount, 0, 1)[:, None]
    return c * (1 - amount) + np.asarray(target) * amount


def _pts(v):
    return v[:, 0], v[:, 1], v[:, 2]


def _ao(sdf, v, n, steps=(0.6, 1.4, 2.4, 3.6, 5.0)):
    occ = np.zeros(len(v))
    wsum = 0.0
    for i, h in enumerate(steps):
        w = 0.75 ** i
        d = sdf(_pts(v + n * h))
        occ += w * np.clip((h - d) / h, 0, 1)
        wsum += w
    return 1 - occ / wsum


def _curvature(sdf, v, h=0.6):
    """Laplacian of the distance field: > 0 on ridges, < 0 in creases."""
    lap = -6 * sdf(_pts(v))
    for ax in range(3):
        e = np.zeros(3)
        e[ax] = h
        lap += sdf(_pts(v + e)) + sdf(_pts(v - e))
    return lap / (h * h)


def _weathering(c, v, n, sdf, seed, lower=0.0):
    """AO, grime, chips and speckle, shared by every painted part."""
    ao = _ao(sdf, v, n)
    curv = _curvature(sdf, v)
    p = _pts(v)
    # Exaggerated occlusion: deep creases go dark, like an inked illustration.
    c = c * (0.42 + 0.58 * ao ** 1.4)[:, None]
    c = _mix(c, GRIME, 0.45 * _smooth(0.0, -0.9, curv) + 0.25 * _smooth(0.85, 0.4, ao))
    # Edge highlights and paint worn thin on ridges.
    c = _mix(c, np.ones(3), 0.18 * _smooth(0.15, 0.8, curv))
    chip_noise = fbm(p, 0.35, 3, seed=seed)
    chips = _smooth(0.25, 0.9, curv) * _smooth(0.15, 0.35, chip_noise)
    rim = _smooth(0.25, 0.9, curv) * _smooth(0.05, 0.15, chip_noise) * (1 - _smooth(0.15, 0.35, chip_noise))
    c = _mix(c, GRIME * 0.8, 0.3 * rim)
    c = _mix(c, PLASTER, 0.9 * chips)
    # Mottled paint and the vintage print speckle.
    c = c * (1 + 0.07 * fbm(p, 0.12, 3, seed=seed + 1))[:, None]
    speck = fbm(p, 2.2, 1, seed=seed + 2)
    c = _mix(c, np.ones(3), 0.35 * _smooth(0.78, 0.86, speck))
    c = _mix(c, GRIME, 0.25 * _smooth(-0.80, -0.88, speck))
    # Garden dirt creeping up from the ground.
    c = _mix(c, GRIME, 0.35 * _smooth(lower + 14, lower, v[:, 2]) * (0.6 + 0.4 * fbm(p, 0.2, 2, seed=seed + 3)))
    return c


def _blush(c, skin_w, dist, radius, strength=0.55, colour=(0.95, 0.42, 0.40)):
    return _mix(c, colour, strength * skin_w * _smooth(radius, 0.0, dist))


def head_colours(v, n, weather=True):
    p = _pts(v)
    regs = gnome.head_regions(p)
    names, w = gnome.region_weights(regs, soft=0.15)
    W = dict(zip(names, w))
    c = w.T @ np.array([gnome.PAINT[k] for k in names])
    a, b, cc = gnome.head_local(p)
    skin = W["skin"]

    # Blush: cheeks, nose, ears.
    for s in (-1, 1):
        c = _blush(c, skin, np.sqrt((a - 6.8 * s) ** 2 + (b - 12.0) ** 2 + (cc + 3.6) ** 2), 5.0)
        c = _blush(c, skin, np.sqrt((a - 12.8 * s) ** 2 + (b + 0.5) ** 2 + (cc - 0.5) ** 2), 5.5, 0.35)
    c = _blush(c, skin, np.sqrt(a ** 2 + (b - 17.0) ** 2 + (cc + 0.5) ** 2), 4.5, 0.45)

    # Open (left) eye: dark iris and pupil looking back over his shoulder, with a glint.
    eye = W["eye"]
    centre = np.array([-4.5, 10.6, 4.2])
    gaze = np.array([0.45, 0.85, 0.05])
    gaze /= np.linalg.norm(gaze)
    rel = np.stack([a, b, cc], 1) - centre
    cosang = (rel @ gaze) / np.maximum(np.linalg.norm(rel, axis=1), 1e-6)
    c = _mix(c, (0.13, 0.20, 0.42), eye * _smooth(0.72, 0.80, cosang) * (a < 0))
    c = _mix(c, (0.02, 0.02, 0.03), eye * _smooth(0.86, 0.90, cosang) * (a < 0))
    glint = np.array([0.30, 0.80, 0.52])
    glint /= np.linalg.norm(glint)
    c = _mix(c, (1, 1, 1), eye * _smooth(0.975, 0.985, (rel @ glint) / np.maximum(np.linalg.norm(rel, axis=1), 1e-6)) * (a < 0))
    # The wink: a dark crease along the bottom of the closed lid.
    lid = np.sqrt(((a - 4.5) / 2.6) ** 2 + ((b - 12.4) / 2.0) ** 2)
    crease = (a > 1.6) & (a < 7.4) & (np.abs(cc - (3.0 + 0.25 * ((a - 4.5) / 2.3) ** 2 * 2.0)) < 0.45) & (lid < 1.6)
    c = _mix(c, (0.20, 0.10, 0.08), crease.astype(float) * (skin + eye))
    # Beard: creamy, with streaks along the hair and a little yellowing near the mouth.
    beard = W["beard"]
    streak = fbm((a, b, cc), 0.9, 2, seed=12, stretch=(1, 1, 0.18))
    c = _mix(c, (0.80, 0.78, 0.72), beard * 0.5 * _smooth(0.0, 0.7, streak))
    c = _mix(c, (0.93, 0.86, 0.66), beard * 0.4 * _smooth(7.0, 2.0, np.sqrt(a ** 2 + (b - 11) ** 2 + (cc + 7) ** 2)))
    # Hat: sun-faded where it faces the sky.
    c = _mix(c, (0.97, 0.55, 0.48), W["hat"] * 0.25 * _smooth(0.4, 0.95, n[:, 2]))

    if weather:
        c = _weathering(c, v, n, lambda q: gnome.combine(gnome.head_regions(q)), seed=200, lower=-50)
    return np.clip(c, 0, 1)


def body_colours(v, n, text_bounds=None, weather=True):
    p = _pts(v)
    regs = gnome.body_regions(p)
    names, w = gnome.region_weights(regs, soft=0.15)
    W = dict(zip(names, w))
    c = w.T @ np.array([gnome.PAINT[k] for k in names])
    x, u, vv = to_torso(p)
    skin = W["skin"]

    # Rosy bum, knees and knuckles.
    for s in (-1, 1):
        c = _blush(c, skin, np.sqrt((x - 13.0 * s) ** 2 + (u + 24.0) ** 2 + (vv - 2.0) ** 2), 9.0, 0.45)
        c = _blush(c, skin, np.sqrt((v[:, 0] - 10.5 * s) ** 2 + (v[:, 1] - 5.0) ** 2 + (v[:, 2] - 46.0) ** 2), 6.0, 0.35)
        c = _blush(c, skin, np.sqrt((v[:, 0] - 21.8 * s) ** 2 + (v[:, 1] + 0.5) ** 2 + (v[:, 2] - 49.6) ** 2), 4.0, 0.35)
    # Button holes and the patch's stitching.
    for vb in (19.5, 26.5):
        uf = gnome._front_u(vb) + 0.3
        for dx, dv in ((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)):
            hole = np.sqrt((x - dx) ** 2 + (vv - vb - dv) ** 2) < 0.35
            c = _mix(c, (0.15, 0.10, 0.05), hole * W["button"] * (u > uf))
    patch = W["patch"]
    edge = patch * (1 - patch) * 4
    ang = np.arctan2(v[:, 2] - 70.0, v[:, 1] - 10.0)
    c = _mix(c, (0.25, 0.16, 0.08), _smooth(0.55, 0.8, edge) * (np.sin(ang * 26) > 0.2))
    # Stone base: speckled, with moss in the pits.
    stone = W["base"]
    c = _mix(c, (0.55, 0.50, 0.40), stone * 0.6 * _smooth(0.55, 0.75, fbm(p, 0.9, 1, seed=301)))
    c = _mix(c, (0.38, 0.45, 0.22), stone * 0.5 * _smooth(0.15, 0.55, fbm(p, 0.12, 3, seed=302)) * (v[:, 2] > 8.5))

    sdf = lambda q: gnome.combine(gnome.body_regions(q))
    d = sdf(p)
    if weather:
        c = _weathering(c, v, n, sdf, seed=100, lower=-3)
    # Faces that are not on the sculpted surface (split faces, the mechanism's cavities) stay plain plastic.
    c[np.abs(d) > 0.3] = INSIDE
    if text_bounds is not None:
        lo, hi = text_bounds
        on_text = np.all((v >= lo - 0.05) & (v <= hi + 0.05), axis=1) & (np.abs(d) > 0.05)
        c[on_text] = LETTERING
    return np.clip(c, 0, 1)
