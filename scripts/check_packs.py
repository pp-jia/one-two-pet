#!/usr/bin/env python3
"""Static checks for the generated pet packs.

Run after build_pet_pack.py:
    python scripts/check_packs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "pet"


def collect_names(anim: dict) -> set[str]:
    names: set[str] = set()
    for key in ("idle", "turn", "drag", "clicks"):
        names.update(anim[key])
    for action in anim["moves"]["actions"]:
        names.add(action["name"])
    for cat in anim["categories"]:
        names.update(cat["actions"])
    for pool in anim["events"].values():
        for slot in pool:
            if isinstance(slot, list):
                names.update(slot)
            else:
                names.add(slot)
    return names


def main() -> int:
    errors: list[str] = []
    total = 0
    for cfg_path in sorted(PET.glob("*-config.json")):
        pack = cfg_path.name[: -len("-config.json")]
        conf = json.loads(cfg_path.read_text(encoding="utf-8"))
        anim = conf["animations"]
        names = collect_names(anim)
        anim_dir = PET / f"{pack}-animation"
        missing = sorted(n for n in names if not (anim_dir / f"{n}.webm").exists())
        if missing:
            errors.append(f"{pack}: missing webm: {missing}")
        extra = sorted(p.stem for p in anim_dir.glob("*.webm") if p.stem not in names)
        if extra:
            errors.append(f"{pack}: unreferenced webm: {extra}")

        weights = conf["animationWeights"]
        cat_sum = sum(c["weight"] for c in anim["categories"])
        total_w = weights["idle"] + weights["turn"] + weights["move"] + cat_sum
        if total_w != 100:
            errors.append(f"{pack}: weights sum {total_w}, expected 100")
        if len(anim["events"]["balance"]) != 6:
            errors.append(f"{pack}: balance must have 6 tiers")
        if len(anim["events"]["workStatus"]) != 6:
            errors.append(f"{pack}: workStatus must have 6 tiers")
        if len(conf["pets"]) != 1:
            errors.append(f"{pack}: expected exactly one pet instance")
        if any(p["id"] != pack for p in conf["pets"]):
            errors.append(f"{pack}: pet id must equal prefix (assetRoot = prefix)")

        total += len(list(anim_dir.glob("*.webm")))
        print(f"{pack}: {len(names)} referenced clips, {len(list(anim_dir.glob('*.webm')))} webm")

    if errors:
        print("\nERRORS:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"\nOK: {total} webm across {len(list(PET.glob('*-config.json')))} packs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
