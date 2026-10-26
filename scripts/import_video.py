#!/usr/bin/env python3
"""Import a green-screen MP4 into a dsh-pet 640x360 VP9-alpha WebM.

This is the bridge for higher-quality AI-video actions:

    Doubao/Kling green-screen MP4
        -> crop safe area (also removes corner watermarks)
        -> chroma key + despill + alpha feather
        -> scale to dsh-pet character height (270px)
        -> encode 640x360 VP9-alpha WebM

Example:
    python scripts/import_video.py \
        --input "C:/Users/me/Downloads/待机.mp4" \
        --name "待机HD" --pack yier-hd

The crop default (330,20,960,710) is tuned for a 1280x720 Doubao clip with a
centered character and a corner watermark.  Adjust --crop for other sources.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PET = ROOT / "pet"
PREVIEW = ROOT / "previews"


def find_ffmpeg(explicit: str | None = None) -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    if os.environ.get("FFMPEG_BIN"):
        candidates.append(os.environ["FFMPEG_BIN"])
    candidates.append(str(ROOT / ".tools" / "ffmpeg.exe"))
    for name in ("ffmpeg", "ffmpeg.exe"):
        import shutil

        found = shutil.which(name)
        if found:
            candidates.append(found)
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    raise FileNotFoundError("ffmpeg not found; put it in .tools/ffmpeg.exe or set FFMPEG_BIN")


def key_frame(rgb: np.ndarray) -> Image.Image:
    """Green-screen key + despill, returns straight-alpha RGBA."""
    a = rgb.astype(np.float32)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    # Green dominance.  White/brown/pink all have d <= 0; pure green d ~ 255.
    d = g - np.maximum(r, b)
    alpha = np.clip((58.0 - d) * 255.0 / 58.0, 0, 255)
    am = Image.fromarray(alpha.astype(np.uint8))
    # Eat a 1px green fringe, then soften the matte.
    am = am.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.9))
    alpha = np.array(am).astype(np.float32)
    # Despill: never let green exceed the max of red/blue on kept pixels.
    a[:, :, 1] = np.minimum(a[:, :, 1], np.maximum(a[:, :, 0], a[:, :, 2]))
    rgba = np.dstack([a, alpha]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def paste_clipped(canvas: Image.Image, layer: Image.Image, x: int, y: int) -> None:
    """alpha_composite with negative/overflow coordinates (crop instead of throw)."""
    sx0 = max(0, -x)
    sy0 = max(0, -y)
    dx0 = max(0, x)
    dy0 = max(0, y)
    w = min(layer.width - sx0, canvas.width - dx0)
    h = min(layer.height - sy0, canvas.height - dy0)
    if w <= 0 or h <= 0:
        return
    part = layer.crop((sx0, sy0, sx0 + w, sy0 + h))
    canvas.alpha_composite(part, (dx0, dy0))


def checker(size: tuple[int, int], step: int = 16) -> Image.Image:
    bg = Image.new("RGBA", size, (255, 255, 255, 255))
    d = ImageDraw.Draw(bg)
    for y in range(0, size[1], step):
        for x in range(0, size[0], step):
            if (x // step + y // step) % 2 == 0:
                d.rectangle((x, y, x + step - 1, y + step - 1), fill=(222, 227, 232, 255))
    return bg


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--name", required=True, help="animation name, e.g. 待机HD")
    ap.add_argument("--pack", default="yier-hd", help="pet pack prefix, e.g. yier-hd")
    ap.add_argument("--crop", default="330,20,960,710", help="x0,y0,x1,y1 in source pixels")
    ap.add_argument("--target-height", type=int, default=270, help="character height on 640x360 canvas")
    ap.add_argument("--feet", type=int, default=330, help="feet y on canvas")
    ap.add_argument("--center-x", type=int, default=320)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--crf", type=int, default=30)
    ap.add_argument("--ffmpeg", default=None)
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args(argv)

    ffmpeg = find_ffmpeg(args.ffmpeg)
    x0, y0, x1, y1 = (int(v) for v in args.crop.split(","))
    cw, ch = x1 - x0, y1 - y0
    if cw <= 0 or ch <= 0:
        raise SystemExit("invalid --crop")

    out_dir = PET / f"{args.pack}-animation"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.webm"
    preview_path = PREVIEW / f"{args.pack}-{args.name}.png"
    PREVIEW.mkdir(exist_ok=True)

    # Pull RGBA frames from ffmpeg, already cropped.
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        args.input,
        "-vf",
        f"fps={args.fps},crop={cw}:{ch}:{x0}:{y0}",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    frame_bytes = cw * ch * 4

    # Encode pipe
    enc_cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        "640x360",
        "-r",
        str(args.fps),
        "-i",
        "pipe:0",
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuva420p",
        "-b:v",
        "0",
        "-crf",
        str(args.crf),
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
    enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert enc.stdin is not None

    scale = None
    paste = None
    frames = 0
    mid_preview: Image.Image | None = None
    try:
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            rgb = np.frombuffer(buf, dtype=np.uint8).reshape((ch, cw, 4))[:, :, :3]
            rgba = key_frame(rgb)
            if scale is None:
                bbox = rgba.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
                if not bbox:
                    raise SystemExit("keyed frame is empty; check --crop and the green background")
                bx0, by0, bx1, by1 = bbox
                scale = args.target_height / max(1, (by1 - by0))
                sw, sh = max(1, round(cw * scale)), max(1, round(ch * scale))
                paste = (
                    round(args.center_x - ((bx0 + bx1) / 2) * scale),
                    round(args.feet - by1 * scale),
                )
                print(f"bbox={bbox} scale={scale:.4f} scaled={sw}x{sh} paste={paste}")
            sw, sh = max(1, round(cw * scale)), max(1, round(ch * scale))
            layer = rgba.resize((sw, sh), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (640, 360), (0, 0, 0, 0))
            paste_clipped(canvas, layer, paste[0], paste[1])  # type: ignore[index]
            enc.stdin.write(canvas.tobytes())
            frames += 1
            if not args.no_preview and frames == 1:
                bg = checker((640, 360))
                bg.alpha_composite(canvas)
                mid_preview = bg
    finally:
        try:
            enc.stdin.close()
        except BrokenPipeError:
            pass
        enc_err = enc.stderr.read().decode("utf-8", "replace") if enc.stderr else ""
        enc_code = enc.wait()
        proc.stdout.close()
        proc_err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        proc_code = proc.wait()

    if proc_code != 0:
        raise SystemExit(f"decode failed: {proc_err[-1500:]}")
    if enc_code != 0:
        raise SystemExit(f"encode failed: {enc_err[-1500:]}")
    if frames == 0:
        raise SystemExit("no frames decoded")

    if mid_preview is not None:
        mid_preview.convert("RGB").save(preview_path)
        print(f"preview: {preview_path}")
    print(f"wrote {out_path}  {frames} frames ({frames / args.fps:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
