#!/usr/bin/env python3
"""Build the 一二 / 布布 pet packs for dsh-pet.

Source: https://github.com/gbn666/codex-pets-bubuyier (MIT)
Output: pet/<pack>-config.json + pet/<pack>-animation/*.webm + pet/<pack>-memes/*.png

Usage:
    python scripts/build_pet_pack.py                 # build all packs
    python scripts/build_pet_pack.py --preview-only  # only render preview sheets
    python scripts/build_pet_pack.py --packs yier --force
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from render import (  # noqa: E402
    CENTER_X,
    Clip,
    CharacterSpec,
    Fx,
    Segment,
    SpriteSheet,
    encode_clip,
    export_meme,
    hop,
    motion,
    render_preview,
    wave,
    _find_ffmpeg,  # type: ignore[attr-defined]
)

SPRITE_DIR = ROOT / "assets" / "sprites"
PET_DIR = ROOT / "pet"
PREVIEW_DIR = ROOT / "previews"

FPS_NAMES = ("idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review")

# ---------------------------------------------------------------------------
# Clip catalogue
# ---------------------------------------------------------------------------


def _seg(row: int, fps: float = 8.0, repeat: int = 1, cols=None) -> Segment:
    return Segment(row=row, fps=fps, repeat=repeat, cols=cols)


def build_clips() -> list[Clip]:
    """Every unique animation file.  Names are user-visible in dsh-pet's menu."""
    clips: list[Clip] = []

    # --- core loops -------------------------------------------------------
    clips.append(
        Clip(
            "待机",
            [_seg(0, fps=6, repeat=2)],
            motion(dy=wave(1.4, 1.7)),
            note="idle breathing",
        )
    )
    clips.append(
        Clip(
            "东张西望",
            [_seg(0, fps=6, repeat=2)],
            motion(dx=wave(15, 2.0), rot=wave(2.2, 2.0)),
            note="turn/look around; dsh-pet flips facing after it ends",
        )
    )
    clips.append(
        Clip(
            "悬空挣扎",
            [_seg(4, fps=12, repeat=4)],
            motion(dy=wave(5, 0.42), rot=wave(4.5, 0.56)),
            note="drag loop",
        )
    )
    clips.append(
        Clip(
            "元气挥手",
            [_seg(3, fps=8, repeat=4)],
            motion(dx=wave(1.5, 0.8), dy=wave(1.0, 0.8)),
            [Fx("sparkle", 0.35, 0.95, 400, 175, 0.8, period=0.55), Fx("sparkle", 1.15, 1.8, 385, 145, 1.0, period=0.65)],
            note="click reaction — wave",
        )
    )
    clips.append(
        Clip(
            "开心跳跳",
            [_seg(4, fps=9, repeat=3)],
            motion(dy=hop(17, 0.62), sy=lambda t, d: 1 + 0.04 * math.sin(2 * math.pi * t / 0.62)),
            [
                Fx("heart", 0.2, 0.9, 210, 72, 0.85),
                Fx("heart", 0.75, 1.45, 438, 82, 0.7),
                Fx("sparkle", 0.15, 1.5, 430, 95, 0.8, period=0.5),
            ],
            note="click reaction — happy hop",
        )
    )
    clips.append(
        Clip(
            "委屈巴巴",
            [_seg(5, fps=7, repeat=2, cols=(0, 1, 2, 3, 2, 1))],
            motion(dy=wave(1.2, 1.2), rot=wave(1.5, 1.2)),
            [Fx("sweat", 0.9, 2.0, 386, 162, 0.8)],
            note="click reaction — teary/shy",
        )
    )
    clips.append(
        Clip(
            "认真看手机",
            [_seg(8, fps=7, repeat=2)],
            motion(dy=wave(0.8, 1.4)),
            [Fx("sparkle", 0.4, 1.8, 390, 235, 0.75, period=0.7)],
            note="click reaction — phone",
        )
    )
    clips.append(
        Clip(
            "捧杯暖手",
            [_seg(6, fps=6, repeat=2)],
            motion(dy=wave(1.0, 1.8)),
            [Fx("steam", 0.2, 99, 320, 243, 0.9, period=1.4)],
            note="click reaction — warm drink",
        )
    )

    # --- moves ------------------------------------------------------------
    clips.append(
        Clip(
            "小跑",
            [_seg(7, fps=12, repeat=12)],
            motion(dy=wave(2.4, 0.38)),
            note="move — trot",
        )
    )
    clips.append(
        Clip(
            "一蹦一跳",
            [_seg(4, fps=12, repeat=12)],
            motion(dy=hop(15, 0.52)),
            note="move — hop",
        )
    )
    clips.append(
        Clip(
            "欢快冲刺",
            [_seg(1, fps=14, repeat=10)],
            motion(dy=wave(2.0, 0.28)),
            note="move — sprint",
        )
    )
    clips.append(
        Clip(
            "悄悄走",
            [_seg(2, fps=9, repeat=7)],
            motion(dy=wave(1.5, 0.55)),
            note="move — quiet walk",
        )
    )

    # --- random small actions --------------------------------------------
    clips.append(
        Clip(
            "发会儿呆",
            [_seg(0, fps=4, repeat=2)],
            motion(dy=wave(1.0, 3.0)),
            [Fx("bubble", 0.2, 2.8, 365, 58, 0.9, params={"dots": True})],
            note="bubble with ...",
        )
    )
    clips.append(
        Clip(
            "打瞌睡",
            [_seg(0, fps=3, repeat=3, cols=(0, 1, 2, 1))],
            motion(dy=wave(2.0, 3.2), rot=wave(2.0, 3.2)),
            [Fx("zzz", 0.2, 99, 402, 92, 1.0, period=1.35)],
            note="sleepy",
        )
    )
    clips.append(
        Clip(
            "伸懒腰",
            [_seg(4, fps=3, repeat=2, cols=(0, 1, 2, 3))],
            motion(dy=-4, sy=lambda t, d: 1 + 0.035 * math.sin(math.pi * min(1.0, t / max(0.1, d)))),
            [Fx("sparkle", 0.4, 2.0, 440, 95, 1.0, period=0.65)],
            note="stretch",
        )
    )
    clips.append(
        Clip(
            "转圈圈",
            [_seg(7, fps=9, repeat=3)],
            motion(dx=wave(4, 0.5), flip=lambda t, d: int(t * 6) % 2 == 1),
            [
                Fx("sparkle", 0.2, 1.8, 200, 150, 0.9, period=0.55),
                Fx("sparkle", 0.5, 2.0, 445, 175, 0.8, period=0.6),
            ],
            note="spin",
        )
    )
    clips.append(
        Clip(
            "数星星",
            [_seg(0, fps=4, repeat=2)],
            motion(dy=wave(1.2, 3.0), rot=wave(1.2, 3.0)),
            [
                Fx("sparkle", 0.1, 2.9, 235, 95, 1.0, period=0.8),
                Fx("sparkle", 0.3, 2.9, 420, 115, 0.8, period=0.9),
                Fx("sparkle", 0.6, 2.9, 300, 70, 0.65, period=0.75),
                Fx("moon", 0.4, 2.9, 470, 100, 0.85),
            ],
            note="count stars",
        )
    )
    clips.append(
        Clip(
            "追逐泡泡",
            [_seg(0, fps=5, repeat=2)],
            motion(dx=wave(7, 2.4), dy=wave(1.2, 2.4)),
            [
                Fx("ring", 0.2, 1.3, 390, 210, 1.0),
                Fx("ring", 0.9, 2.2, 260, 185, 0.8),
                Fx("ring", 1.5, 2.6, 420, 160, 0.7),
            ],
            note="chase bubbles",
        )
    )
    clips.append(
        Clip(
            "摇摇晃晃",
            [_seg(0, fps=5, repeat=2)],
            motion(rot=wave(5.5, 1.6), dx=wave(5, 1.6)),
            [],
            note="sway",
        )
    )
    clips.append(
        Clip(
            "是啊，吃什么",
            [_seg(0, fps=4, repeat=2)],
            motion(dy=wave(1.0, 3.0)),
            [Fx("bubble", 0.15, 2.85, 350, 56, 1.05, params={"text": "吃什么？", "dots": False})],
            note="text clip — noMirror",
        )
    )
    clips.append(
        Clip(
            "深度思考",
            [_seg(8, fps=6, repeat=2)],
            motion(dy=wave(0.8, 1.2)),
            [
                Fx("question", 0.2, 1.7, 410, 72, 1.0, period=0.9),
                Fx("sparkle", 0.6, 2.0, 250, 130, 0.7, period=0.6),
            ],
            note="deep thought",
        )
    )
    clips.append(
        Clip(
            "新年好",
            [_seg(3, fps=8, repeat=4)],
            motion(dx=wave(1.5, 0.9), dy=hop(4, 0.9)),
            [
                Fx("redpacket", 0.3, 2.0, 420, 268, 0.9),
                Fx("coin", 0.5, 2.0, 230, 275, 0.75, period=0.8),
                Fx("sparkle", 0.1, 2.0, 380, 105, 0.9, period=0.55),
            ],
            note="seasonal — new year",
        )
    )

    # --- balance event animations (6 tiers) -------------------------------
    clips.append(
        Clip(
            "余额-钱包鼓鼓",
            [_seg(8, fps=6, repeat=3)],
            motion(dy=wave(1.0, 1.2)),
            [
                Fx("coin", 0.2, 1.8, 430, 282, 1.0, period=0.7),
                Fx("coin", 0.5, 2.2, 215, 274, 0.85, period=0.75),
                Fx("sparkle", 0.1, 2.4, 390, 105, 1.0, period=0.55),
            ],
            note="balance tier 0 — full wallet",
        )
    )
    clips.append(
        Clip(
            "余额-数金币",
            [_seg(6, fps=6, repeat=3)],
            motion(dy=wave(0.8, 1.4)),
            [
                Fx("coin", 0.2, 1.6, 430, 280, 0.9, period=0.65),
                Fx("coin", 0.8, 2.2, 220, 276, 0.8, period=0.7),
                Fx("sparkle", 0.4, 2.4, 430, 130, 0.8, period=0.6),
            ],
            note="balance tier 1",
        )
    )
    clips.append(
        Clip(
            "余额-钱包还好",
            [_seg(0, fps=5, repeat=2)],
            motion(dy=wave(1.0, 2.2)),
            [Fx("coin", 0.3, 2.0, 420, 280, 0.85, period=0.8)],
            note="balance tier 2",
        )
    )
    clips.append(
        Clip(
            "余额-有点心疼",
            [_seg(5, fps=6, repeat=3, cols=(0, 1, 2, 3))],
            motion(dy=wave(0.8, 1.3)),
            [Fx("coin", 0.4, 1.8, 410, 282, 0.7, period=0.8), Fx("sweat", 0.6, 2.0, 386, 162, 0.8)],
            note="balance tier 3",
        )
    )
    clips.append(
        Clip(
            "余额-快见底",
            [_seg(5, fps=5, repeat=2)],
            motion(dy=wave(0.8, 1.5), rot=wave(1.4, 1.5)),
            [Fx("wallet", 0.4, 3.0, 418, 278, 0.95), Fx("sweat", 0.8, 2.8, 386, 162, 0.8)],
            note="balance tier 4",
        )
    )
    clips.append(
        Clip(
            "余额-空空如也",
            [_seg(5, fps=4, repeat=2)],
            motion(dy=wave(0.6, 1.6), rot=wave(1.2, 1.6)),
            [Fx("bowl", 0.3, 3.8, 418, 282, 1.0), Fx("sweat", 0.7, 3.4, 386, 162, 0.9), Fx("zzz", 1.2, 3.9, 404, 92, 0.7, period=1.4)],
            note="balance tier 5",
        )
    )

    # --- whisper / work status -------------------------------------------
    clips.append(
        Clip(
            "碎碎念-点头",
            [_seg(0, fps=4, repeat=2)],
            motion(dy=wave(2.0, 0.75)),
            [Fx("bubble", 0.2, 2.9, 355, 58, 0.95, params={"dots": True})],
            note="whisper — nodding",
        )
    )
    clips.append(
        Clip(
            "工作状态-思考冒泡",
            [_seg(0, fps=4, repeat=2)],
            motion(dy=wave(1.2, 2.8), rot=wave(1.4, 2.8)),
            [
                Fx("question", 0.2, 2.8, 406, 72, 1.0, period=1.0),
                Fx("bubble", 1.0, 2.9, 300, 58, 0.75, params={"dots": True}),
            ],
            note="work — thinking",
        )
    )
    clips.append(
        Clip(
            "工作状态-忙碌敲键盘",
            [_seg(8, fps=7, repeat=3)],
            motion(dy=wave(1.0, 0.45)),
            [Fx("bubble", 0.3, 2.5, 380, 58, 0.8, params={"dots": True})],
            note="work — typing",
        )
    )
    clips.append(
        Clip(
            "工作状态-清点归档",
            [_seg(6, fps=5, repeat=2)],
            motion(dy=wave(0.9, 1.6)),
            [Fx("check", 0.4, 2.2, 408, 75, 1.0)],
            note="work — done",
        )
    )
    clips.append(
        Clip(
            "工作状态-原地踱步张望",
            [_seg(7, fps=8, repeat=3)],
            motion(dx=wave(12, 1.5), rot=wave(1.5, 1.5)),
            [Fx("question", 0.5, 2.2, 406, 72, 0.9, period=0.9)],
            note="work — waiting",
        )
    )
    clips.append(
        Clip(
            "工作状态-雀跃庆祝",
            [_seg(4, fps=9, repeat=3)],
            motion(dy=hop(18, 0.6)),
            [
                Fx("heart", 0.15, 0.85, 214, 74, 0.9),
                Fx("heart", 0.65, 1.35, 436, 84, 0.75),
                Fx("sparkle", 0.1, 1.6, 430, 100, 1.0, period=0.5),
            ],
            note="work — success",
        )
    )
    clips.append(
        Clip(
            "工作状态-垂头叹气冒汗",
            [_seg(5, fps=5, repeat=2)],
            motion(dy=wave(0.7, 1.8), rot=wave(1.4, 1.8)),
            [Fx("sweat", 0.5, 2.9, 386, 162, 0.95), Fx("exclaim", 0.2, 1.1, 414, 72, 0.8)],
            note="work — error",
        )
    )

    return clips


# ---------------------------------------------------------------------------
# Pack definitions and configs
# ---------------------------------------------------------------------------


def _animations_for(clips: list[Clip], duo: bool = False) -> dict:
    names = {c.name for c in clips}
    idle = ["待机", "发会儿呆", "打瞌睡", "摇摇晃晃", "数星星"]
    categories = [
        {
            "id": "小动作",
            "weight": 22,
            "actions": ["元气挥手", "发会儿呆", "打瞌睡", "伸懒腰", "转圈圈", "数星星", "摇摇晃晃"],
        },
        {
            "id": "玩耍",
            "weight": 14,
            "actions": ["开心跳跳", "追逐泡泡", "转圈圈", "数星星"],
        },
        {
            "id": "吃什么",
            "weight": 8,
            "actions": ["捧杯暖手"],
        },
        {
            "id": "文字",
            "weight": 8,
            "noMirror": True,
            "actions": ["是啊，吃什么", "深度思考"],
        },
        {
            "id": "时节",
            "weight": 6,
            "actions": ["新年好"],
        },
    ]
    for cat in categories:
        for action in cat["actions"]:
            if action not in names:
                raise KeyError(f"category references missing clip: {action}")
    for name in idle:
        if name not in names:
            raise KeyError(f"idle references missing clip: {name}")

    return {
        "idle": idle,
        "turn": ["东张西望"],
        "drag": ["悬空挣扎"],
        "clicks": ["元气挥手", "开心跳跳", "委屈巴巴", "认真看手机", "捧杯暖手"],
        "moves": {
            "default": {"minDist": 60, "maxDist": 260, "margin": 20, "leadSec": 0.9, "tailSec": 0.8},
            "actions": [
                {"name": "小跑"},
                {"name": "一蹦一跳", "params": {"minDist": 40, "maxDist": 160}},
                {"name": "欢快冲刺", "params": {"minDist": 180, "maxDist": 420, "leadSec": 0.7, "tailSec": 0.6}},
                {"name": "悄悄走", "params": {"minDist": 80, "maxDist": 220, "leadSec": 1.1, "tailSec": 1.0}},
            ],
        },
        "categories": categories,
        "events": {
            "balance": [
                "余额-钱包鼓鼓",
                "余额-数金币",
                "余额-钱包还好",
                "余额-有点心疼",
                "余额-快见底",
                "余额-空空如也",
            ],
            "whisper": ["碎碎念-点头", "元气挥手", "认真看手机"],
            "workStatus": [
                "工作状态-思考冒泡",
                "工作状态-忙碌敲键盘",
                "工作状态-清点归档",
                "工作状态-原地踱步张望",
                "工作状态-雀跃庆祝",
                "工作状态-垂头叹气冒汗",
            ],
        },
    }


def _weights() -> dict:
    return {"idle": 24, "turn": 6, "move": 12}


def _work_texts(kind: str) -> list[list[str]]:
    shared = [
        ["让我想想哦…", "脑袋里在冒泡泡…"],
        ["正在认真干活呢", "敲敲敲，马上就好"],
        ["这一步搞定啦", "整理一下，继续～"],
        ["等你确认一下下", "这里要你来看看哦"],
        ["完成啦，击个掌！", "这一轮辛苦啦～"],
        ["好像卡住了…", "呜，这里出错了"],
    ]
    if kind == "bubu":
        return [
            ["困困地想…", "让我眯一会儿再想"],
            ["慢慢做，不着急", "在努力啦…"],
            ["这步好了，呼", "收好收好"],
            ["等你点头哦", "不急，我等你"],
            ["搞定，想睡觉了", "完成…奖励一杯奶茶？"],
            ["卡住了，呜呜", "出错啦，抱抱我"],
        ]
    if kind == "duo":
        return [
            ["一二在想，布布在打盹", "让我俩一起想想…"],
            ["一二敲键盘，布布递奶茶", "忙忙碌碌中…"],
            ["这一步收好啦", "清点一下，继续～"],
            ["等你确认哦", "一二和布布都在等"],
            ["完成！击掌！", "这一轮辛苦啦～"],
            ["卡住了…", "呜，一起抱抱"],
        ]
    return shared


def _persona(kind: str) -> str:
    if kind == "yier":
        return (
            "你是「一二」，一只白色圆润、深棕色圆耳朵、粉色腮红、没有眉毛的软萌小角色。"
            "性格温柔、害羞、有点小迷糊，说话轻声细语，喜欢安静陪着主人。"
            "每次只说一句很短的话（20字以内），自然随意，不要解释自己是AI，不要提表情包或版权。"
        )
    if kind == "bubu":
        return (
            "你是「布布」，一只奶茶棕色、深棕色描边、黄色腮红、总是一副困困表情的小熊。"
            "性格慵懒、治愈、呆萌，说话慢悠悠，喜欢睡觉和热饮，偶尔冒出一句冷幽默。"
            "每次只说一句很短的话（20字以内），自然随意，不要解释自己是AI，不要提表情包或版权。"
        )
    return (
        "你是「一二布布」：白色圆耳朵的一二温柔害羞，奶茶色的小熊布布慵懒爱困。"
        "你们是一对好朋友，一起住在主人的桌面上。说话时可以用“一二：”“布布：”区分，"
        "每次总共一两句、30字以内，自然随意，不要解释自己是AI，不要提表情包或版权。"
    )


def _pets(kind: str) -> list[dict]:
    common = {
        "balanceEnabled": False,
        "whisperEnabled": False,
        "workStatusEnabled": True,
        "fixedEnabled": False,
        "display": "web",
        "whisperPrompt": _persona(kind),
    }
    if kind == "yier":
        return [
            {
                **common,
                "id": "yier",
                "name": "一二",
                "size": 280,
                "position": {"corner": "top-left", "marginX": 24, "marginY": 160},
            }
        ]
    if kind == "bubu":
        return [
            {
                **common,
                "id": "bubu",
                "name": "布布",
                "size": 280,
                "position": {"corner": "top-right", "marginX": 24, "marginY": 160},
            }
        ]
    return [
        {
            **common,
            "id": "duo",
            "name": "一二布布",
            "size": 340,
            "display": "none",
            "position": {"corner": "top-left", "marginX": 24, "marginY": 160},
        }
    ]


def _memes(kind: str) -> dict:
    if kind == "bubu":
        return {
            "布布-困困": "半眯着眼、困困的布布，适合犯困、待机、想睡觉",
            "布布-挥手": "抬起小爪子打招呼，适合问候、回应",
            "布布-开心": "蹦起来开心庆祝，适合完成、好消息",
            "布布-委屈": "眼泪汪汪、委屈巴巴，适合出错、撒娇",
            "布布-喝茶": "捧着热饮暖手，适合休息、喝下午茶",
            "布布-看手机": "认真盯着小手机，适合思考、等待回复",
        }
    if kind == "duo":
        return {
            "一二布布-合影": "一二和布布并排站着，适合日常问候、开场",
            "一二布布-开心": "两只一起蹦起来，适合庆祝、成功",
            "一二布布-委屈": "两只一起委屈，适合出错、求安慰",
            "一二布布-喝茶": "两只一起捧杯，适合休息、下午茶",
        }
    return {
        "一二-好奇": "圆眼睛好奇地看着你，适合待机、提问",
        "一二-挥手": "抬起小手打招呼，适合问候、回应",
        "一二-开心": "蹦起来开心庆祝，适合完成、好消息",
        "一二-害羞": "脸红害羞、眼泪汪汪，适合被夸、撒娇",
        "一二-喝茶": "捧着热饮暖手，适合休息、下午茶",
        "一二-看手机": "认真盯着小手机，适合思考、等待回复",
    }


def _memes_files(kind: str) -> list[tuple[str, int, int, str]]:
    """(name, row, col, note) — the file name is the meme key."""
    if kind == "bubu":
        return [
            ("布布-困困", 0, 1, "sleepy idle"),
            ("布布-挥手", 3, 2, "wave"),
            ("布布-开心", 4, 2, "jump"),
            ("布布-委屈", 5, 0, "cry"),
            ("布布-喝茶", 6, 2, "drink"),
            ("布布-看手机", 8, 2, "phone"),
        ]
    if kind == "duo":
        return [
            ("一二布布-合影", 0, 0, "duo idle"),
            ("一二布布-开心", 4, 2, "duo jump"),
            ("一二布布-委屈", 5, 0, "duo cry"),
            ("一二布布-喝茶", 6, 2, "duo drink"),
        ]
    return [
        ("一二-好奇", 0, 0, "curious idle"),
        ("一二-挥手", 3, 2, "wave"),
        ("一二-开心", 4, 2, "jump"),
        ("一二-害羞", 5, 0, "cry/blush"),
        ("一二-喝茶", 6, 2, "drink"),
        ("一二-看手机", 8, 2, "phone"),
    ]


def _characters(kind: str) -> list[CharacterSpec]:
    if kind == "duo":
        return [
            CharacterSpec("yier", scale=0.84, cx=278, feet=330),
            CharacterSpec("bubu", scale=0.78, cx=398, feet=330),
        ]
    return [CharacterSpec(kind)]


def build_config(kind: str, clips: list[Clip]) -> dict:
    return {
        "pets": _pets(kind),
        "animations": _animations_for(clips, duo=kind == "duo"),
        "animationWeights": _weights(),
        "workStatusTexts": _work_texts(kind),
        "memes": _memes(kind),
        "notificationsEnabled": False,
        "clickSoundEnabled": False,
        "whisperImageEnabled": True,
        "chatImageEnabled": True,
        "confineToScreen": False,
        "trayEnabled": False,
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def write_preview_page(packs: dict[str, list[Clip]]) -> None:
    rows = []
    for pack, clips in packs.items():
        rows.append(f"<h2>{pack}</h2><div class='grid'>")
        for c in clips:
            src = f"../pet/{pack}-animation/{c.name}.webm"
            rows.append(
                "<figure><video src='"
                + src
                + "' muted loop autoplay playsinline></video><figcaption>"
                + c.name
                + "</figcaption></figure>"
            )
        rows.append("</div>")
    html = f"""<!doctype html>
<html lang="zh-CN"><meta charset="utf-8">
<title>one-two-pet preview</title>
<style>
body{{font-family:system-ui,'Microsoft YaHei',sans-serif;background:#f6f3ef;color:#3d2c2a;margin:24px}}
h1{{font-weight:700}} h2{{margin-top:32px;border-left:6px solid #ff9ab2;padding-left:10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}
figure{{margin:0;background:conic-gradient(#e7e2dc 25%,#f4f0eb 0 50%,#e7e2dc 0 75%,#f4f0eb 0) 0 0/16px 16px;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px #0001}}
video{{width:100%;display:block;aspect-ratio:16/9;object-fit:contain}}
figcaption{{background:#fff;padding:6px 10px;font-size:13px}}
</style>
<h1>一二布布 · 动画预览</h1>
<p>棋盘格 = 透明背景。动画源为 640×360 VP9-alpha WebM，实际桌宠中透明播放。</p>
{''.join(rows)}
</html>"""
    (PREVIEW_DIR / "index.html").write_text(html, encoding="utf-8")


def make_contact_sheet(
    pack: str,
    clips: list[Clip],
    sprites: dict[str, SpriteSheet],
    main_key: str,
    characters: list[CharacterSpec],
) -> None:
    from render import render_frame

    cols = 5
    cell_w, cell_h = 220, 132
    pad = 10
    rows = math.ceil(len(clips) / cols)
    out = Image.new("RGB", (pad + cols * (cell_w + pad), 50 + rows * (cell_h + 28 + pad)), (246, 243, 239))
    d = ImageDraw.Draw(out)
    d.text((pad, 12), f"{pack} — {len(clips)} clips", fill=(60, 45, 42))
    for i, clip in enumerate(clips):
        dur = clip.duration(sprites[main_key])
        saved = clip.characters
        clip.characters = characters
        try:
            frame = render_frame(clip, dur * 0.45, dur, sprites, main_key)
        finally:
            clip.characters = saved
        thumb = Image.new("RGBA", (cell_w, cell_h), (255, 255, 255, 255))
        td = ImageDraw.Draw(thumb)
        for y in range(0, cell_h, 10):
            for x in range(0, cell_w, 10):
                if (x // 10 + y // 10) % 2 == 0:
                    td.rectangle((x, y, x + 9, y + 9), fill=(226, 230, 234, 255))
        thumb.alpha_composite(frame.resize((cell_w, cell_h), Image.Resampling.LANCZOS))
        x = pad + (i % cols) * (cell_w + pad)
        y = 42 + (i // cols) * (cell_h + 28 + pad)
        out.paste(thumb.convert("RGB"), (x, y))
        d.text((x + 2, y + cell_h + 4), clip.name, fill=(60, 45, 42))
    out.save(PREVIEW_DIR / f"contact-{pack}.png")


def write_animation_docs(clips: list[Clip], sprite: SpriteSheet) -> None:
    lines = [
        "# 动画一览",
        "",
        "共 " + str(len(clips)) + " 段。源图集为 8 列 × 9 行、192×208/格；输出统一 640×360、24fps、VP9-alpha。",
        "",
        "| 动画名 | 时长 | 源行 | 用途 / 备注 |",
        "| --- | ---: | --- | --- |",
    ]
    for clip in clips:
        dur = clip.duration(sprite)
        row = clip.segments[0].row
        note = clip.note or ""
        lines.append(f"| {clip.name} | {dur:.2f}s | {row} | {note} |")
    lines += [
        "",
        "## 配置里的分组",
        "",
        "- `idle`：待机、发呆、打瞌睡、摇摇晃晃、数星星",
        "- `turn`：东张西望",
        "- `drag`：悬空挣扎",
        "- `clicks`：元气挥手、开心跳跳、委屈巴巴、认真看手机、捧杯暖手",
        "- `moves`：小跑、一蹦一跳、欢快冲刺、悄悄走",
        "- `events.balance`：余额-钱包鼓鼓 → 空空如也（6 档）",
        "- `events.whisper`：碎碎念-点头 / 元气挥手 / 认真看手机",
        "- `events.workStatus`：思考 / 敲键盘 / 归档 / 踱步 / 庆祝 / 出错（6 档）",
        "",
    ]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "animations.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", default="yier,bubu,duo", help="comma separated: yier,bubu,duo")
    ap.add_argument("--preview-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-encode existing webm")
    ap.add_argument("--ffmpeg", default=None)
    ap.add_argument("--crf", type=int, default=30)
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args(argv)

    packs = [p.strip() for p in args.packs.split(",") if p.strip()]
    unknown = set(packs) - {"yier", "bubu", "duo"}
    if unknown:
        raise SystemExit(f"unknown packs: {sorted(unknown)}")

    sprites = {
        "yier": SpriteSheet("yier", SPRITE_DIR / "yier" / "spritesheet.webp"),
        "bubu": SpriteSheet("bubu", SPRITE_DIR / "bubu" / "spritesheet.webp"),
    }
    clips = build_clips()
    PET_DIR.mkdir(exist_ok=True)
    PREVIEW_DIR.mkdir(exist_ok=True)
    ffmpeg = None if args.preview_only else _find_ffmpeg(args.ffmpeg)

    all_packs: dict[str, list[Clip]] = {}
    for pack in packs:
        all_packs[pack] = clips
        chars = _characters(pack)
        main_key = "yier"
        anim_dir = PET_DIR / f"{pack}-animation"
        meme_dir = PET_DIR / f"{pack}-memes"
        anim_dir.mkdir(parents=True, exist_ok=True)
        meme_dir.mkdir(parents=True, exist_ok=True)

        sprites_for_pack = sprites
        config = build_config(pack, clips)
        (PET_DIR / f"{pack}-config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        # Configs only reference names that we encode below.
        if not args.preview_only:
            total = len(clips)
            t0 = time.time()
            for i, clip in enumerate(clips):
                out = anim_dir / f"{clip.name}.webm"
                if out.exists() and not args.force:
                    print(f"[{pack}] {i + 1}/{total} skip {clip.name}")
                    continue
                # Temporarily attach the pack's characters to the clip.
                saved = clip.characters
                clip.characters = chars
                try:
                    dur = encode_clip(clip, sprites_for_pack, main_key, out, ffmpeg, crf=args.crf)
                finally:
                    clip.characters = saved
                size = out.stat().st_size / 1024
                print(
                    f"[{pack}] {i + 1}/{total} {clip.name}.webm  {dur:.2f}s  {size:.0f} KiB  "
                    f"(elapsed {time.time() - t0:.0f}s)"
                )

        # Memes: export still cells from the source atlas (duo composites both).
        for name, row, col, _note in _memes_files(pack):
            out = meme_dir / f"{name}.png"
            if pack == "duo":
                from render import render_frame
                from render import Clip as _C

                tmp_clip = _C("meme", [Segment(row, cols=(col,), fps=1)], characters=chars)
                frame = render_frame(tmp_clip, 0, 1.0, sprites, "yier")
                frame = frame.crop((80, 20, 560, 350))
                frame.save(out)
            else:
                export_meme(sprites[pack], row, col, out, scale=1.0)

        if not args.no_preview:
            make_contact_sheet(pack, clips, sprites_for_pack, main_key, chars)

        print(f"[{pack}] config + {len(clips)} clips ready")

    if not args.no_preview:
        write_preview_page(all_packs)
    write_animation_docs(clips, sprites["yier"])
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
