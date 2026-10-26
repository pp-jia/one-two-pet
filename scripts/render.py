#!/usr/bin/env python3
"""Rendering helpers for the one-two-pet sprite atlas.

The source Codex pet atlas is a 8x9 grid of 192x208 cells.  This module turns
those cells into 640x360 VP9-alpha WebM clips that dsh-pet can play, and draws
small hand-made effects (hearts, Zzz, coins, bubbles, ...) so a nine-row atlas
still feels like a full desktop pet.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Canvas constants — kept identical to dsh-pet's 640x360 thumb contract.
# ---------------------------------------------------------------------------

CANVAS_W = 640
CANVAS_H = 360
FPS = 24

CHAR_H = 270
CHAR_W = 249
FEET_Y = 330
CENTER_X = CANVAS_W // 2

CELL_W = 192
CELL_H = 208
ROWS = 9
COLS = 8

OUTLINE = (74, 44, 42, 255)
CREAM = (255, 250, 242, 255)
PINK = (255, 154, 178, 255)
PINK_DARK = (238, 112, 148, 255)
GOLD = (255, 211, 92, 255)
GOLD_DARK = (224, 162, 36, 255)
BLUE = (155, 214, 255, 255)
GREEN = (92, 190, 128, 255)
PURPLE = (140, 120, 220, 255)
RED = (232, 88, 88, 255)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONT_CN = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")
FONT_FALLBACK = Path(r"C:\Windows\Fonts\arialbd.ttf")


def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for candidate in ((FONT_BOLD, FONT_CN) if bold else (FONT_CN, FONT_BOLD)):
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size)
            except OSError:
                pass
    if FONT_FALLBACK.exists():
        return ImageFont.truetype(str(FONT_FALLBACK), size)
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Sprite atlas
# ---------------------------------------------------------------------------


class SpriteSheet:
    """One Codex pet atlas: nine animation rows, each up to eight cells."""

    def __init__(self, key: str, path: Path):
        self.key = key
        self.path = path
        sheet = Image.open(path).convert("RGBA")
        if sheet.size != (CELL_W * COLS, CELL_H * ROWS):
            raise ValueError(f"{path}: expected 1536x1872, got {sheet.size}")
        self.sheet = sheet
        self.rows: list[list[Image.Image]] = []
        for r in range(ROWS):
            cells: list[Image.Image] = []
            for c in range(COLS):
                cell = sheet.crop(
                    (c * CELL_W, r * CELL_H, (c + 1) * CELL_W, (r + 1) * CELL_H)
                )
                if cell.getbbox() is None:
                    break
                cells.append(cell)
            self.rows.append(cells)

    def cell(self, row: int, col: int) -> Image.Image:
        cells = self.rows[row % len(self.rows)]
        return cells[col % len(cells)]

    def frame_count(self, row: int) -> int:
        return len(self.rows[row % len(self.rows)])


# ---------------------------------------------------------------------------
# Character pose / clips
# ---------------------------------------------------------------------------


@dataclass
class Transform:
    dx: float = 0.0
    dy: float = 0.0
    rot: float = 0.0
    sx: float = 1.0
    sy: float = 1.0
    flip: bool | None = None


@dataclass
class CharacterSpec:
    """How one sprite participates in a clip."""

    key: str
    scale: float = 1.0
    cx: float = CENTER_X
    feet: float = FEET_Y
    mirror: bool = False
    delay: float = 0.0
    behind: bool = False


@dataclass
class Segment:
    row: int
    cols: Sequence[int] | None = None
    fps: float = 8.0
    repeat: int = 1

    def frames(self, sprite: SpriteSheet) -> list[int]:
        if self.cols is not None:
            cols = list(self.cols)
        else:
            cols = list(range(sprite.frame_count(self.row)))
        if not cols:
            cols = [0]
        return cols * self.repeat

    def duration(self, sprite: SpriteSheet) -> float:
        frames = self.frames(sprite)
        return max(1.0 / FPS, len(frames) / self.fps)


@dataclass
class Fx:
    """A small overlay effect, drawn procedurally."""

    kind: str
    start: float = 0.0
    end: float | None = None
    x: float = CENTER_X
    y: float = 100.0
    size: float = 1.0
    period: float = 0.0
    params: dict = field(default_factory=dict)


def _value(v, t: float, dur: float):
    return v(t, dur) if callable(v) else v


def motion(
    dx=0.0,
    dy=0.0,
    rot=0.0,
    sx=1.0,
    sy=1.0,
    flip=None,
) -> Callable[[float, float], Transform]:
    return lambda t, d: Transform(
        dx=_value(dx, t, d),
        dy=_value(dy, t, d),
        rot=_value(rot, t, d),
        sx=_value(sx, t, d),
        sy=_value(sy, t, d),
        flip=_value(flip, t, d),
    )


def wave(amp: float, period: float, phase: float = 0.0) -> Callable[[float, float], float]:
    return lambda t, d: amp * math.sin(2 * math.pi * t / period + phase)


def hop(amp: float, period: float, phase: float = 0.0) -> Callable[[float, float], float]:
    """Negative dy = up.  A sequence of little hops, never below the ground."""
    return lambda t, d: -amp * abs(math.sin(math.pi * (t / period + phase)))


@dataclass
class Clip:
    name: str
    segments: list[Segment]
    transform: Callable[[float, float], Transform] = motion()
    fx: list[Fx] = field(default_factory=list)
    characters: list[CharacterSpec] | None = None
    note: str = ""

    def duration(self, sprite: SpriteSheet) -> float:
        return sum(seg.duration(sprite) for seg in self.segments)

    def pose_at(
        self, t: float, dur: float, sprite: SpriteSheet
    ) -> tuple[int, int, Transform]:
        local = max(0.0, min(t, max(0.0, dur - 1e-6)))
        for seg in self.segments:
            seg_dur = seg.duration(sprite)
            if local < seg_dur:
                frames = seg.frames(sprite)
                idx = min(len(frames) - 1, int(local * seg.fps))
                return seg.row, frames[idx], self.transform(t, dur)
            local -= seg_dur
        seg = self.segments[-1]
        frames = seg.frames(sprite)
        return seg.row, frames[-1], self.transform(t, dur)


# ---------------------------------------------------------------------------
# Low-level drawing helpers (effect layers are rendered at 2x and downsampled)
# ---------------------------------------------------------------------------


def _new_layer(scale: int = 2) -> Image.Image:
    return Image.new("RGBA", (CANVAS_W * scale, CANVAS_H * scale), (0, 0, 0, 0))


def _downscale(layer: Image.Image, scale: int = 2) -> Image.Image:
    return layer.resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)


def _apply_alpha(layer: Image.Image, factor: float) -> Image.Image:
    factor = max(0.0, min(1.0, factor))
    if factor >= 0.999:
        return layer
    a = layer.getchannel("A").point(lambda v: int(v * factor))
    layer = layer.copy()
    layer.putalpha(a)
    return layer


def _outline_mask(mask: Image.Image, width: int) -> Image.Image:
    return mask.filter(ImageFilter.MaxFilter(width))


def _shape_layer(
    size: int,
    draw_fn: Callable[[ImageDraw.ImageDraw, int], None],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] = OUTLINE,
    outline_width: int = 7,
) -> Image.Image:
    """Build a small filled shape with a soft/dilated outline."""
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    draw_fn(md, size)
    layer = Image.new("RGBA", (size, size), outline)
    layer.putalpha(_outline_mask(mask, outline_width))
    fill_layer = Image.new("RGBA", (size, size), fill)
    fill_layer.putalpha(mask)
    return Image.alpha_composite(layer, fill_layer)


def _paste(layer: Image.Image, dest: tuple[int, int]) -> Image.Image:
    """Return a full-canvas layer with `layer` pasted at dest (cropping outside)."""
    full = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    x, y = dest
    full.alpha_composite(layer, (int(x), int(y)))
    return full


def _heart_layer(size: int) -> Image.Image:
    def draw(d: ImageDraw.ImageDraw, s: int) -> None:
        r = s * 0.30
        cx = s * 0.5
        cy = s * 0.44
        d.ellipse((cx - 0.46 * s, cy - 0.34 * s, cx - 0.02 * s, cy + 0.10 * s), fill=255)
        d.ellipse((cx + 0.02 * s, cy - 0.34 * s, cx + 0.46 * s, cy + 0.10 * s), fill=255)
        d.polygon(
            ((cx - 0.44 * s, cy - 0.02 * s), (cx + 0.44 * s, cy - 0.02 * s), (cx, cy + 0.45 * s)),
            fill=255,
        )

    return _shape_layer(size, draw, PINK)


def _star_layer(size: int) -> Image.Image:
    def draw(d: ImageDraw.ImageDraw, s: int) -> None:
        cx = cy = s * 0.5
        r1, r2 = s * 0.46, s * 0.12
        pts = []
        for i in range(8):
            ang = -math.pi / 2 + i * math.pi / 4
            r = r1 if i % 2 == 0 else r2
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        d.polygon(pts, fill=255)

    return _shape_layer(size, draw, GOLD)


def _tear_layer(size: int) -> Image.Image:
    def draw(d: ImageDraw.ImageDraw, s: int) -> None:
        d.ellipse((s * 0.30, s * 0.38, s * 0.70, s * 0.78), fill=255)
        d.polygon(((s * 0.5, s * 0.14), (s * 0.68, s * 0.58), (s * 0.32, s * 0.58)), fill=255)

    return _shape_layer(size, draw, BLUE, outline_width=5)


def _coin_layer(size: int) -> Image.Image:
    layer = _shape_layer(
        size,
        lambda d, s: d.ellipse((s * 0.12, s * 0.12, s * 0.88, s * 0.88), fill=255),
        GOLD,
        outline_width=7,
    )
    d = ImageDraw.Draw(layer)
    font = load_font(max(10, int(size * 0.46)), bold=True)
    text = "¥"
    bbox = d.textbbox((0, 0), text, font=font)
    d.text(
        ((size - (bbox[2] - bbox[0])) / 2, (size - (bbox[3] - bbox[1])) / 2 - size * 0.05),
        text,
        font=font,
        fill=OUTLINE,
    )
    return layer


def _letter_layer(text: str, size: int, color, font_size: int) -> Image.Image:
    font = load_font(font_size, bold=True)
    bbox = font.getbbox(text)
    w = max(4, bbox[2] - bbox[0] + 12)
    h = max(4, bbox[3] - bbox[1] + 12)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((6 - bbox[0], 6 - bbox[1]), text, font=font, fill=color, stroke_width=3, stroke_fill=OUTLINE)
    return layer


def _check_layer(size: int) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = max(4, int(size * 0.12))
    d.line(
        ((size * 0.12, size * 0.52), (size * 0.40, size * 0.80), (size * 0.88, size * 0.18)),
        fill=GREEN,
        width=w,
        joint="curve",
    )
    d.line(
        ((size * 0.12, size * 0.52), (size * 0.40, size * 0.80), (size * 0.88, size * 0.18)),
        fill=OUTLINE,
        width=max(1, w // 3),
        joint="curve",
    )
    return layer


def _bubble_layer(size: int, text: str | None = None, dots: bool = False) -> Image.Image:
    w, h = int(size * 2.0), int(size * 1.15)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((3, 3, w - 4, h - 4), radius=int(size * 0.36), fill=CREAM, outline=OUTLINE, width=4)
    d.polygon(
        ((w * 0.32, h - 4), (w * 0.48, h - 4), (w * 0.34, h + int(size * 0.26))),
        fill=CREAM,
        outline=OUTLINE,
    )
    if text:
        font = load_font(max(12, int(size * 0.52)), bold=True)
        bbox = d.textbbox((0, 0), text, font=font)
        d.text(
            ((w - (bbox[2] - bbox[0])) / 2 - bbox[0], (h - (bbox[3] - bbox[1])) / 2 - bbox[1]),
            text,
            font=font,
            fill=OUTLINE,
        )
    elif dots:
        for i in range(3):
            cx = w * (0.3 + i * 0.2)
            cy = h * 0.5
            r = size * 0.09
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=OUTLINE)
    return layer


def _wallet_layer(size: int) -> Image.Image:
    w, h = int(size * 1.6), int(size * 1.05)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((3, 3, w - 4, h - 4), radius=int(size * 0.2), fill=(226, 196, 160, 255), outline=OUTLINE, width=4)
    d.rounded_rectangle((3, 3, w - 4, h * 0.38), radius=int(size * 0.2), fill=(240, 214, 180, 255), outline=OUTLINE, width=4)
    d.rounded_rectangle((w * 0.62, h * 0.44, w - 4, h * 0.82), radius=int(size * 0.12), fill=GOLD, outline=OUTLINE, width=4)
    return layer


def _bowl_layer(size: int) -> Image.Image:
    w, h = int(size * 1.7), int(size * 1.05)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # bowl body (lower half of an ellipse), then a cream rim
    d.pieslice((3, h * 0.02, w - 4, h * 1.02), 0, 180, fill=(255, 252, 246, 255), outline=OUTLINE, width=4)
    d.ellipse((3, h * 0.02, w - 4, h * 0.30), fill=(255, 255, 255, 255), outline=OUTLINE, width=4)
    d.arc((w * 0.18, h * 0.36, w * 0.82, h * 0.78), 20, 160, fill=PINK_DARK, width=max(3, int(size * 0.08)))
    return layer


def _moon_layer(size: int) -> Image.Image:
    layer = _shape_layer(
        size,
        lambda d, s: d.ellipse((s * 0.10, s * 0.10, s * 0.90, s * 0.90), fill=255),
        (255, 244, 196, 255),
        outline_width=7,
    )
    d = ImageDraw.Draw(layer)
    for cx, cy, r in ((0.34, 0.36, 0.10), (0.66, 0.58, 0.07), (0.44, 0.70, 0.05)):
        d.ellipse(
            (size * (cx - r), size * (cy - r), size * (cx + r), size * (cy + r)),
            fill=(246, 224, 160, 255),
            outline=(216, 188, 126, 255),
            width=2,
        )
    return layer


def _redpacket_layer(size: int) -> Image.Image:
    w, h = int(size * 0.95), int(size * 1.35)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((3, 3, w - 4, h - 4), radius=int(size * 0.12), fill=RED, outline=OUTLINE, width=4)
    d.ellipse((w * 0.3, h * 0.28, w * 0.7, h * 0.62), fill=GOLD, outline=OUTLINE, width=3)
    font = load_font(max(10, int(size * 0.22)), bold=True)
    d.text((w * 0.38, h * 0.34), "福", font=font, fill=OUTLINE)
    return layer


# ---------------------------------------------------------------------------
# Effect renderer
# ---------------------------------------------------------------------------


def _ease_out(p: float) -> float:
    return 1 - (1 - max(0.0, min(1.0, p))) ** 2


def _fade(p: float, fade_in: float = 0.12, fade_out: float = 0.25) -> float:
    if p < fade_in:
        return p / fade_in
    if p > 1 - fade_out:
        return max(0.0, (1 - p) / fade_out)
    return 1.0


def render_fx(fx: Fx, t: float, dur: float) -> Image.Image | None:
    end = dur if fx.end is None else min(fx.end, dur)
    if t < fx.start or t > end:
        return None
    span = max(1e-6, end - fx.start)
    if fx.period > 0:
        p = ((t - fx.start) % fx.period) / fx.period
    else:
        p = (t - fx.start) / span
    q = max(0.0, min(1.0, p))
    alpha = _fade(q)
    size = fx.size
    layer: Image.Image | None = None
    dest = (fx.x, fx.y)

    if fx.kind == "heart":
        base = 64
        layer = _heart_layer(base)
        s = (1.0 + 0.18 * math.sin(q * math.pi)) * size
        layer = layer.resize((max(4, int(base * s)), max(4, int(base * s))), Image.Resampling.LANCZOS)
        dest = (fx.x - layer.width / 2, fx.y - _ease_out(q) * 46 * size - layer.height / 2)
    elif fx.kind == "sparkle":
        base = 52
        layer = _star_layer(base)
        s = (0.55 + 0.55 * abs(math.sin(q * math.pi * 2))) * size
        layer = layer.resize((max(4, int(base * s)), max(4, int(base * s))), Image.Resampling.LANCZOS)
        layer = layer.rotate(q * 90, resample=Image.Resampling.BICUBIC, expand=True)
        dest = (fx.x - layer.width / 2, fx.y - layer.height / 2)
    elif fx.kind == "zzz":
        layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        for i in range(3):
            phase = (q + i / 3) % 1.0
            s = 27 + 12 * (1 - phase)
            z = _letter_layer("Z", 0, (255, 255, 255, 255), int(s))
            z = _apply_alpha(z, max(0.0, 1 - phase) * 0.95)
            layer.alpha_composite(z, (int(fx.x + phase * 62 * size), int(fx.y - phase * 84 * size)))
        dest = (0, 0)
    elif fx.kind == "sweat":
        base = 44
        layer = _tear_layer(base)
        layer = layer.resize((max(4, int(base * size)), max(4, int(base * size))), Image.Resampling.LANCZOS)
        layer = _apply_alpha(layer, alpha)
        dest = (fx.x, fx.y + _ease_out(q) * 28 * size - layer.height / 2)
    elif fx.kind in ("question", "exclaim", "note", "text", "ha"):
        text = {
            "question": "?",
            "exclaim": "!",
            "note": "♪",
            "ha": "哈",
        }.get(fx.kind, fx.params.get("text", ""))
        color = {
            "question": PURPLE,
            "exclaim": RED,
            "note": (255, 138, 178, 255),
            "ha": OUTLINE,
        }.get(fx.kind, fx.params.get("color", OUTLINE))
        fs = fx.params.get("font_size", int(46 * size))
        layer = _letter_layer(text, 0, color, fs)
        if fx.params.get("pop", True):
            s = 0.7 + 0.45 * _ease_out(min(1.0, q * 3))
            layer = layer.resize(
                (max(4, int(layer.width * s)), max(4, int(layer.height * s))),
                Image.Resampling.LANCZOS,
            )
        layer = _apply_alpha(layer, alpha)
        dest = (fx.x - layer.width / 2, fx.y - layer.height / 2 - 10 * math.sin(q * math.pi))
    elif fx.kind == "bubble":
        layer = _bubble_layer(int(54 * size), text=fx.params.get("text"), dots=fx.params.get("dots", True))
        layer = _apply_alpha(layer, alpha)
        dest = (fx.x - layer.width / 2, fx.y - layer.height)
    elif fx.kind == "steam":
        layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for i in range(3):
            phase = (q + i / 3) % 1.0
            x0 = fx.x + (i - 1) * 16 * size
            pts = []
            for k in range(9):
                yy = fx.y - k * 5 * size - phase * 18 * size
                xx = x0 + math.sin(k * 0.9 + i + t * 6) * 4 * size
                pts.append((xx, yy))
            d.line(pts, fill=(206, 232, 246, int(210 * (1 - phase))), width=max(3, int(4 * size)), joint="curve")
        layer = _apply_alpha(layer, alpha)
        dest = (0, 0)
    elif fx.kind == "coin":
        base = 58
        layer = _coin_layer(base)
        spin = abs(math.cos(q * math.pi * 3))
        w = max(5, int(base * size * (0.35 + 0.65 * spin)))
        layer = layer.resize((w, max(4, int(base * size))), Image.Resampling.LANCZOS)
        dest = (fx.x - layer.width / 2, fx.y - _ease_out(q) * 34 * size - layer.height / 2)
    elif fx.kind == "blush":
        layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for sign in (-1, 1):
            x = fx.x + sign * 42 * size
            d.ellipse(
                (x - 17 * size, fx.y - 9 * size, x + 17 * size, fx.y + 9 * size),
                fill=(255, 140, 170, 150),
            )
        layer = _apply_alpha(layer, alpha * 0.8)
        dest = (0, 0)
    elif fx.kind == "check":
        base = 54
        layer = _check_layer(base)
        layer = layer.resize((max(4, int(base * size)), max(4, int(base * size))), Image.Resampling.LANCZOS)
        layer = _apply_alpha(layer, alpha)
        dest = (fx.x - layer.width / 2, fx.y - layer.height / 2)
    elif fx.kind == "wallet":
        layer = _wallet_layer(int(56 * size))
        layer = _apply_alpha(layer, alpha)
        dest = (fx.x - layer.width / 2, fx.y - layer.height / 2)
    elif fx.kind == "bowl":
        layer = _bowl_layer(int(56 * size))
        layer = _apply_alpha(layer, alpha)
        dest = (fx.x - layer.width / 2, fx.y - layer.height / 2)
    elif fx.kind == "moon":
        layer = _moon_layer(int(66 * size))
        layer = _apply_alpha(layer, alpha)
        dest = (fx.x - layer.width / 2, fx.y - layer.height / 2)
    elif fx.kind == "redpacket":
        layer = _redpacket_layer(int(60 * size))
        layer = _apply_alpha(layer, alpha)
        dest = (fx.x - layer.width / 2, fx.y - layer.height / 2)
    elif fx.kind == "ring":
        layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        r = 10 + 36 * _ease_out(q)
        d.ellipse(
            (fx.x - r * size, fx.y - r * size * 0.55, fx.x + r * size, fx.y + r * size * 0.55),
            outline=(255, 255, 255, int(160 * (1 - q))),
            width=max(2, int(4 * size)),
        )
        dest = (0, 0)
    else:
        return None

    if layer is None:
        return None
    if layer.size == (CANVAS_W, CANVAS_H):
        return _apply_alpha(layer, alpha) if fx.kind not in ("zzz", "steam", "blush", "ring") else layer
    return _paste(layer, dest)


# ---------------------------------------------------------------------------
# Character rendering + clip encoding
# ---------------------------------------------------------------------------


def render_character(
    sprite: SpriteSheet,
    row: int,
    col: int,
    spec: CharacterSpec,
    tf: Transform,
) -> Image.Image:
    cell = sprite.cell(row, col)
    w = max(2, int(round(CHAR_W * spec.scale * tf.sx)))
    h = max(2, int(round(CHAR_H * spec.scale * tf.sy)))
    cell = cell.resize((w, h), Image.Resampling.NEAREST)
    if tf.rot:
        cell = cell.rotate(tf.rot, resample=Image.Resampling.NEAREST, center=(w / 2, h))
    if tf.flip:
        cell = cell.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if spec.mirror:
        cell = cell.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    x = spec.cx - w / 2 + tf.dx
    y = spec.feet - h + tf.dy
    layer.alpha_composite(cell, (int(round(x)), int(round(y))))
    return layer


def render_frame(
    clip: Clip,
    t: float,
    dur: float,
    sprites: dict[str, SpriteSheet],
    main_key: str,
) -> Image.Image:
    main = sprites[main_key]
    row, col, tf = clip.pose_at(t, dur, main)
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    specs = clip.characters or [CharacterSpec(main_key)]
    ordered = sorted(specs, key=lambda s: (not s.behind, s.cx))
    for spec in ordered:
        sprite = sprites[spec.key]
        local_t = max(0.0, t - spec.delay)
        r, c, ttf = clip.pose_at(local_t, dur, sprite)
        # Apply only position/rotation from the base pose; keep per-character scale.
        char_tf = Transform(
            dx=tf.dx,
            dy=tf.dy,
            rot=tf.rot,
            sx=tf.sx,
            sy=tf.sy,
            flip=(tf.flip if tf.flip is not None else False),
        )
        layer = render_character(sprite, r, c, spec, char_tf)
        canvas.alpha_composite(layer)
    for e in clip.fx:
        layer = render_fx(e, t, dur)
        if layer is not None:
            canvas.alpha_composite(layer)
    return canvas


def _find_ffmpeg(explicit: str | None = None) -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    if os.environ.get("FFMPEG_BIN"):
        candidates.append(os.environ["FFMPEG_BIN"])
    candidates.append(str(ROOT / ".tools" / "ffmpeg.exe"))
    for name in ("ffmpeg", "ffmpeg.exe"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    raise FileNotFoundError(
        "ffmpeg not found. Put ffmpeg.exe in one-two-pet/.tools/ or set FFMPEG_BIN."
    )


def encode_clip(
    clip: Clip,
    sprites: dict[str, SpriteSheet],
    main_key: str,
    out_path: Path,
    ffmpeg: str,
    *,
    crf: int = 30,
    verbose: bool = False,
) -> float:
    dur = clip.duration(sprites[main_key])
    frames = max(1, round(dur * FPS))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="otp-"))
    try:
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error" if not verbose else "info",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{CANVAS_W}x{CANVAS_H}",
            "-r",
            str(FPS),
            "-i",
            "pipe:0",
            "-c:v",
            "libvpx-vp9",
            "-pix_fmt",
            "yuva420p",
            "-b:v",
            "0",
            "-crf",
            str(crf),
            "-auto-alt-ref",
            "0",
            "-row-mt",
            "1",
            "-cpu-used",
            "4",
            "-deadline",
            "good",
            "-an",
            str(out_path),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        assert proc.stdin is not None
        try:
            for i in range(frames):
                t = i / FPS
                frame = render_frame(clip, t, dur, sprites, main_key)
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
        except BrokenPipeError:
            pass
        stderr = proc.stderr.read() if proc.stderr else b""
        code = proc.wait()
        if code != 0:
            raise RuntimeError(f"ffmpeg failed for {clip.name}: {stderr.decode('utf-8', 'replace')[-2000:]}")
        return dur
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def render_preview(
    clip: Clip,
    sprites: dict[str, SpriteSheet],
    main_key: str,
    out_path: Path,
    *,
    t: float | None = None,
    cols: int = 6,
) -> None:
    """Write a small contact strip PNG for one clip (used by README/preview page)."""
    dur = clip.duration(sprites[main_key])
    frames = cols
    thumbs = []
    for i in range(frames):
        tt = dur * (i + 0.5) / frames if t is None else t
        thumbs.append(render_frame(clip, tt, dur, sprites, main_key))
    tw, th = 160, 90
    pad = 6
    out = Image.new("RGB", (cols * (tw + pad) + pad, th + pad * 2 + 18), (245, 243, 240))
    d = ImageDraw.Draw(out)
    for i, frame in enumerate(thumbs):
        checker = Image.new("RGBA", (tw, th), (255, 255, 255, 255))
        cd = ImageDraw.Draw(checker)
        for y in range(0, th, 8):
            for x in range(0, tw, 8):
                if (x // 8 + y // 8) % 2 == 0:
                    cd.rectangle((x, y, x + 7, y + 7), fill=(226, 230, 234, 255))
        thumb = frame.resize((tw, th), Image.Resampling.LANCZOS)
        checker.alpha_composite(thumb)
        out.paste(checker.convert("RGB"), (pad + i * (tw + pad), pad + 18))
    d.text((pad, 3), clip.name, fill=(60, 45, 42))
    out.save(out_path)


def export_meme(
    sprite: SpriteSheet,
    row: int,
    col: int,
    out_path: Path,
    *,
    scale: float = 1.0,
    bg: bool = False,
) -> None:
    cell = sprite.cell(row, col)
    w, h = max(2, int(CHAR_W * scale)), max(2, int(CHAR_H * scale))
    cell = cell.resize((w, h), Image.Resampling.LANCZOS)
    pad = 18
    out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if bg:
        d = ImageDraw.Draw(out)
        d.rounded_rectangle((0, 0, out.width - 1, out.height - 1), radius=24, fill=CREAM, outline=OUTLINE, width=4)
    out.alpha_composite(cell, (pad, pad))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
