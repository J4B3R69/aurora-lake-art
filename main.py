#!/usr/bin/env python3
"""Aurora Lake - a procedural night-sky artwork.

Renders a northern-lights scene over a mountain lake using nothing but
the Python standard library: a gradient sky with three aurora ribbons,
a star field, a glowing moon, two mountain ridgelines and a rippled
reflection in the lake. The picture is computed pixel by pixel from
fixed mathematical functions, so every run writes exactly the same
PNG bytes (no randomness at run time, no network, no input files).

Output: $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png)
"""

import math
import os
import random
import struct
import zlib

W = 720
H = 720
HORIZON = int(H * 0.66)          # where the lake starts
MOON_X = int(W * 0.78)
MOON_Y = int(H * 0.16)
MOON_R = 26


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


# --- scene geometry, precomputed per column ---------------------------------

def ridge_far(x):
    return (H * 0.52 + 26 * math.sin(x * 0.011 + 1.7)
            + 14 * math.sin(x * 0.023 + 0.4) + 6 * math.sin(x * 0.051))


def ridge_near(x):
    return (H * 0.605 + 20 * math.sin(x * 0.009 + 4.2)
            + 10 * math.sin(x * 0.027 + 2.1) + 5 * math.sin(x * 0.043 + 1.0))


RIDGE_FAR = [ridge_far(x) for x in range(W)]
RIDGE_NEAR = [ridge_near(x) for x in range(W)]


def aurora_center(x, ribbon):
    """Vertical centre of an aurora ribbon at column x."""
    if ribbon == 0:
        return H * 0.30 + 46 * math.sin(x * 0.006 + 0.8) + 18 * math.sin(x * 0.013)
    if ribbon == 1:
        return H * 0.22 + 38 * math.sin(x * 0.008 + 2.6) + 14 * math.sin(x * 0.017 + 1.0)
    return H * 0.40 + 52 * math.sin(x * 0.005 + 4.4) + 20 * math.sin(x * 0.011 + 2.2)


AURORA_WIDTH = (64.0, 44.0, 84.0)
AURORA_STRENGTH = (0.85, 0.6, 0.5)
GREEN = (0.25, 1.0, 0.62)
TEAL = (0.16, 0.86, 0.78)
VIOLET = (0.58, 0.35, 1.0)


def sky_color(x, y):
    """Colour of the open sky (before mountains) at pixel (x, y)."""
    t = clamp((y / HORIZON) ** 1.25)
    r, g, b = mix((0.03, 0.04, 0.15), (0.10, 0.22, 0.38), t)

    # Aurora ribbons: gaussian falloff around a wavy centre line, with
    # vertical rays modulated along x and a green-to-violet shift.
    for ribbon in range(3):
        cy = aurora_center(x, ribbon)
        d = (y - cy) / AURORA_WIDTH[ribbon]
        if d < -3.0 or d > 3.0:
            continue
        rays = 0.72 + 0.28 * math.sin(x * 0.11 + ribbon * 2.1 + y * 0.012)
        glow = math.exp(-d * d) * AURORA_STRENGTH[ribbon] * rays
        glow *= clamp(1.15 - y / H, 0.35, 1.0)
        tint = clamp(0.5 + d * 0.55)
        cr, cg, cb = mix(GREEN, VIOLET, tint) if d > -0.4 else mix(TEAL, GREEN, clamp(d + 1.0))
        r += cr * glow * 0.75
        g += cg * glow * 0.75
        b += cb * glow * 0.75

    # Soft moon glow behind everything else in the sky.
    dx = x - MOON_X
    dy = y - MOON_Y
    dist2 = dx * dx + dy * dy
    if dist2 < 200 * 200:
        glow = math.exp(-dist2 / (2 * 68 * 68)) * 0.30
        r += 0.85 * glow
        g += 0.88 * glow
        b += 1.0 * glow
    return (r, g, b)


def land_color(x, y):
    """Colour at (x, y) for the sky half of the scene (sky + mountains)."""
    if y > RIDGE_NEAR[x]:
        t = clamp((y - RIDGE_NEAR[x]) / (HORIZON - RIDGE_NEAR[x] + 1))
        return mix((0.05, 0.06, 0.12), (0.02, 0.03, 0.07), t)
    if y > RIDGE_FAR[x]:
        edge = y - RIDGE_FAR[x]
        base = mix((0.08, 0.11, 0.22), (0.04, 0.05, 0.12),
                   clamp((y - RIDGE_FAR[x]) / 90.0))
        if edge < 2.0:  # moonlit snow line on the far ridge
            base = mix(base, (0.55, 0.62, 0.78), 0.55 * (1.0 - edge / 2.0))
        return base
    return sky_color(x, y)


def lake_color(x, y):
    """Reflection: sample the land scene mirrored in the horizon."""
    depth = y - HORIZON
    wobble = int(3.0 * math.sin(y * 0.11) + 2.0 * math.sin(y * 0.031 + 1.3))
    sx = min(W - 1, max(0, x + wobble))
    sy = max(0, HORIZON - depth)
    r, g, b = land_color(sx, sy)
    fade = 0.78 - 0.22 * clamp(depth / (H - HORIZON))
    ripple = 0.96 + 0.04 * math.sin(y * 1.35 + x * 0.02)
    # The aurora reflects more strongly than the dark land around it:
    # add a share of the pure sky colour at the mirrored point so the
    # ribbons shimmer on the water instead of drowning in silhouette.
    sr, sg, sb = sky_color(sx, sy)
    lift = 0.30 * clamp(depth / (H - HORIZON) + 0.25)
    return (r * fade * ripple + sr * lift + 0.012,
            g * fade * ripple + sg * lift + 0.03,
            b * fade * ripple + sb * lift + 0.07)


def star_field():
    rng = random.Random(20261112)
    stars = []
    for _ in range(950):
        x = rng.randrange(W)
        y = int(H * 0.58 * (rng.random() ** 1.6))
        if y > RIDGE_FAR[x] - 4:
            continue
        stars.append((x, y, 0.35 + 0.65 * rng.random(), rng.random()))
    return stars


def render():
    img = bytearray(W * H * 3)
    for y in range(H):
        row = y * W * 3
        for x in range(W):
            if y < HORIZON:
                r, g, b = land_color(x, y)
            else:
                r, g, b = lake_color(x, y)
            i = row + x * 3
            img[i] = int(255 * clamp(r))
            img[i + 1] = int(255 * clamp(g))
            img[i + 2] = int(255 * clamp(b))

    # Stars: single bright pixels, a few with a small cross sparkle.
    for x, y, bright, kind in star_field():
        i = (y * W + x) * 3
        for ch in range(3):
            img[i + ch] = min(255, int(img[i + ch] + 255 * bright))
        if kind > 0.93:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    j = (ny * W + nx) * 3
                    for ch in range(3):
                        img[j + ch] = min(255, int(img[j + ch] + 110 * bright))

    # Moon: bright disc with a gentle terminator and two soft craters.
    for yy in range(MOON_Y - MOON_R, MOON_Y + MOON_R + 1):
        for xx in range(MOON_X - MOON_R, MOON_X + MOON_R + 1):
            dx, dy = xx - MOON_X, yy - MOON_Y
            if dx * dx + dy * dy > MOON_R * MOON_R:
                continue
            shade = 0.92 + 0.08 * (dx / MOON_R)
            crater = 1.0
            for cx, cy, cr in ((-11, 5, 5), (4, 12, 4), (13, -6, 3), (-3, -13, 3)):
                d2 = (dx - cx) ** 2 + (dy - cy) ** 2
                if d2 < cr * cr:
                    crater = 0.955
            i = (yy * W + xx) * 3
            img[i] = int(238 * shade * crater)
            img[i + 1] = int(242 * shade * crater)
            img[i + 2] = int(252 * shade * crater)
    return bytes(img)


def write_png(path, pixels):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    raw = bytearray()
    stride = W * 3
    prev = bytes(stride)
    for y in range(H):
        row = pixels[y * stride:(y + 1) * stride]
        # PNG "Sub" filter: store differences from the left neighbour.
        filt = bytearray(stride)
        for i in range(stride):
            left = row[i - 3] if i >= 3 else 0
            filt[i] = (row[i] - left) & 0xFF
        raw.append(1)
        raw.extend(filt)
        prev = row
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    size = write_png(os.path.join(out_dir, "entry.png"), render())
    print(f"entry.png written: {W}x{H}, {size} bytes")


if __name__ == "__main__":
    main()
