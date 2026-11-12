#!/usr/bin/env python3
"""Aurora Cabin - a procedural night-sky artwork.

A log cabin with warm glowing windows sits among pine trees under
curtains of northern lights; the aurora and the cabin light reflect in
a still lake. Pure Python standard library: every pixel is computed
here and written as a PNG. A fixed-seed PRNG places the stars, so the
output bytes are identical on every run. No input, no network.
"""

import math
import os
import random
import struct
import zlib

W = 720
H = 720

SKY_TOP = (6, 10, 34)
SKY_MID = (13, 24, 66)
SKY_LOW = (24, 44, 92)
LAKE_TOP = (16, 34, 74)
LAKE_BOT = (6, 12, 34)
PINE = (8, 22, 20)
PINE_FAR = (14, 34, 38)
SNOW = (214, 228, 244)
WOOD = (74, 48, 32)
WOOD_DARK = (52, 33, 21)
ROOF = (38, 30, 44)
WINDOW = (255, 186, 84)
WINDOW_HOT = (255, 226, 150)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def get(self, x, y):
        i = (y * self.w + x) * 3
        return (self.px[i], self.px[i + 1], self.px[i + 2])

    def add(self, x, y, color, scale):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            for k in range(3):
                v = self.px[i + k] + int(color[k] * scale)
                self.px[i + k] = 255 if v > 255 else v

    def blend(self, x, y, color, alpha):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            for k in range(3):
                self.px[i + k] = int(self.px[i + k] * (1 - alpha) + color[k] * alpha)

    def disc(self, cx, cy, r, color):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                d = math.hypot(x - cx, y - cy)
                if d <= r:
                    self.set(x, y, color)
                elif d <= r + 1:
                    self.blend(x, y, color, r + 1 - d)


def draw_sky(cv):
    for y in range(470):
        if y < 240:
            c = lerp(SKY_TOP, SKY_MID, y / 240)
        else:
            c = lerp(SKY_MID, SKY_LOW, (y - 240) / 230)
        for x in range(W):
            cv.set(x, y, c)


def draw_stars(cv):
    rng = random.Random(20261112)
    for _ in range(340):
        x = rng.randrange(W)
        y = int(430 * (rng.random() ** 1.6))
        b = rng.random()
        if b < 0.75:
            cv.add(x, y, (190, 205, 255), 0.35 + 0.4 * b)
        else:
            cv.add(x, y, (255, 255, 255), 0.8)
            cv.add(x + 1, y, (255, 255, 255), 0.35)
            cv.add(x, y + 1, (255, 255, 255), 0.35)
    # a shooting star
    for t in range(46):
        x = 512 + t * 2
        y = 84 + int(t * 0.9)
        fade = 1 - t / 46
        cv.add(x, y, (255, 255, 255), 0.9 * fade)
        cv.add(x, y + 1, (200, 215, 255), 0.4 * fade)
    cv.add(512, 84, (255, 255, 255), 0.9)
    cv.add(513, 84, (255, 255, 255), 0.6)


def aurora_color(t):
    # green core, teal edges, violet fringe
    if t < 0.45:
        return lerp((24, 220, 140), (90, 255, 190), t / 0.45)
    if t < 0.75:
        return lerp((90, 255, 190), (40, 160, 220), (t - 0.45) / 0.3)
    return lerp((40, 160, 220), (150, 80, 220), (t - 0.75) / 0.25)


def draw_aurora(cv):
    # three overlapping curtains
    curtains = [
        (150.0, 60.0, 210.0, 0.9, 0.011, 1.7),
        (90.0, 130.0, 260.0, 0.65, 0.014, 4.2),
        (210.0, 40.0, 170.0, 0.5, 0.009, 2.6),
    ]
    for (base_y, amp, height, strength, freq, phase) in curtains:
        for x in range(W):
            wave = (math.sin(x * freq + phase) * 26
                    + math.sin(x * freq * 2.7 + phase * 2.0) * 9)
            top = base_y + wave
            for yy in range(int(top), int(top + height)):
                t = (yy - top) / height
                # vertical rays: brightness ripples along x
                ray = 0.72 + 0.28 * math.sin(x * 0.11 + phase * 3.0
                                             + math.sin(x * 0.021) * 2.0)
                fade = max(0.0, math.sin(math.pi * min(1.0, t * 1.15))) ** 1.4
                glow = strength * fade * ray
                if glow > 0.02:
                    cv.add(x, yy, aurora_color(t), glow * 0.75)


def draw_moon(cv):
    cv.disc(118, 96, 30, (232, 238, 250))
    cv.disc(118, 96, 30, (232, 238, 250))
    for (cx, cy, r) in [(106, 86, 6), (128, 106, 4), (122, 80, 3)]:
        cv.disc(cx, cy, r, (206, 214, 232))
    for r in range(64, 34, -6):
        for y in range(96 - r, 96 + r):
            for x in range(118 - r, 118 + r):
                if math.hypot(x - 118, y - 96) <= r:
                    cv.blend(x, y, (200, 214, 255), 0.03)


def pine(cv, cx, base, h, color):
    tiers = 5
    for i in range(tiers):
        t = i / tiers
        y_top = base - h * (0.25 + 0.75 * t) - h * 0.18
        y_bot = base - h * 0.75 * t
        half = (1 - t * 0.72) * h * 0.30
        steps = int(y_bot - y_top)
        for s in range(steps):
            yy = int(y_top + s)
            wdt = half * (s / max(1, steps))
            for x in range(int(cx - wdt), int(cx + wdt)):
                cv.set(x, yy, color)
    for y in range(int(base - h * 0.06), int(base)):
        for x in range(cx - 3, cx + 3):
            cv.set(x, y, color)


def draw_shore(cv):
    # snowy shore band
    for y in range(452, 486):
        edge = 452 + int(8 * math.sin(y * 0.0 + 1.2)) + (y - 452)
        for x in range(W):
            cv.set(x, y, lerp(SNOW, LAKE_TOP, (y - 452) / 34))
    # far pines
    far = [(30, 90), (78, 120), (560, 100), (616, 130), (668, 86),
           (700, 118), (140, 74), (508, 70)]
    for (cx, h) in far:
        pine(cv, cx, 470, h, PINE_FAR)
    # near pines framing the scene
    pine(cv, 52, 486, 210, PINE)
    pine(cv, 96, 486, 150, PINE)
    pine(cv, 676, 486, 226, PINE)
    pine(cv, 632, 486, 138, PINE)


def draw_cabin(cv):
    x0, y0 = 288, 372  # top-left of the wall
    wdt, hgt = 150, 86
    # warm light pool on the snow
    for y in range(448, 486):
        for x in range(x0 - 26, x0 + wdt + 26):
            d = abs(x - (x0 + wdt / 2)) / (wdt / 2 + 26)
            cv.blend(x, y, WINDOW, 0.20 * max(0.0, 1 - d) * (1 - (y - 448) / 40))
    # wall with log lines
    for y in range(y0, y0 + hgt):
        for x in range(x0, x0 + wdt):
            cv.set(x, y, WOOD if (y - y0) % 14 < 12 else WOOD_DARK)
    # roof: wide snowy slab
    for i in range(26):
        y = y0 - 24 + i
        over = 18 - i // 3
        for x in range(x0 - over - 8, x0 + wdt + over + 8):
            cv.set(x, y, ROOF if i < 17 else SNOW)
    # chimney with a curl of smoke
    for y in range(y0 - 52, y0 - 20):
        for x in range(x0 + 108, x0 + 126):
            cv.set(x, y, WOOD_DARK)
    for i in range(26):
        t = i / 25
        cx = x0 + 117 + int(16 * math.sin(t * 4.2))
        cy = y0 - 58 - int(38 * t)
        r = 4 + int(7 * t)
        for y in range(cy - r, cy + r):
            for x in range(cx - r, cx + r):
                if math.hypot(x - cx, y - cy) <= r:
                    cv.blend(x, y, (210, 218, 232), 0.35)
    # door
    for y in range(y0 + 30, y0 + hgt):
        for x in range(x0 + 62, x0 + 90):
            cv.set(x, y, WOOD_DARK)
    cv.disc(x0 + 84, y0 + 60, 2, WINDOW)
    # two glowing windows with frames and crossbars
    for wx in (x0 + 16, x0 + 102):
        for y in range(y0 + 26, y0 + 58):
            for x in range(wx, wx + 32):
                cv.set(x, y, WINDOW_HOT)
        for y in range(y0 + 26, y0 + 58):
            for x in range(wx, wx + 32):
                if x in (wx, wx + 31) or y in (y0 + 26, y0 + 57) \
                        or x == wx + 15 or y == y0 + 41:
                    cv.set(x, y, WOOD_DARK)
        # glow spilling below the window
        for y in range(y0 + 58, y0 + 70):
            for x in range(wx - 3, wx + 35):
                cv.blend(x, y, WINDOW, 0.30 * (1 - (y - y0 - 58) / 12))


def draw_lake(cv):
    for y in range(486, H):
        c = lerp(LAKE_TOP, LAKE_BOT, (y - 486) / (H - 486))
        for x in range(W):
            cv.set(x, y, c)
    # reflect the sky: sample the finished sky/cabin rows, dim + wobble
    src = Canvas(W, H)
    src.px = bytearray(cv.px)
    for y in range(486, H):
        depth = (y - 486) / (H - 486)
        sy = 452 - int(depth * 210)
        wob = int(3 * math.sin(y * 0.11) + 2 * math.sin(y * 0.031 + 1.0))
        for x in range(W):
            sx = x + wob
            if 0 <= sx < W:
                r, g, b = src.get(sx, sy)
                keep = 0.55 - 0.25 * depth
                cv.set(x, y, (int(r * keep), int(g * keep), int(b * keep)))
    # sparkle streaks under the moon and windows
    rng = random.Random(77)
    for _ in range(130):
        x = rng.randrange(W)
        y = 492 + int((H - 500) * (rng.random() ** 1.4))
        ln = rng.randrange(3, 12)
        warm = rng.random() < 0.3 and 250 < x < 470
        col = WINDOW if warm else (170, 200, 240)
        for k in range(ln):
            cv.blend(x + k, y, col, 0.30)


def render():
    cv = Canvas(W, H)
    draw_sky(cv)
    draw_aurora(cv)
    draw_stars(cv)
    draw_moon(cv)
    draw_shore(cv)
    draw_cabin(cv)
    draw_lake(cv)
    return cv


def png_bytes(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(render())
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
