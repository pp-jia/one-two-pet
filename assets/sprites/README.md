# 精灵图说明

两张 `spritesheet.webp` 都是 **1536×1872**，按 **8 列 × 9 行** 切成 **192×208** 的格子。

| 行 | 状态 | 本图集实际帧数 |
| ---: | --- | ---: |
| 0 | idle | 6 |
| 1 | running-right | 8 |
| 2 | running-left | 8 |
| 3 | waving | 4 |
| 4 | jumping | 5 |
| 5 | failed | 8 |
| 6 | waiting | 6 |
| 7 | running | 6 |
| 8 | review | 6 |

每行末尾的空格会自动跳过；构建脚本按行取帧，再合成到 640×360、脚底 y=330 的统一画布上。

## 想自己补动作

- 保持 **192×208/格**、8 格一行、透明背景、脚底在同一条线上；
- 或在 `scripts/build_pet_pack.py` 的 `build_clips()` 里加新的 `Clip`，复用现有行 + 新特效；
- 加完跑 `powershell -ExecutionPolicy Bypass -File scripts\build.ps1 --packs yier --force`。

## 署名

来源：[gbn666/codex-pets-bubuyier](https://github.com/gbn666/codex-pets-bubuyier)（MIT）。
角色形象版权见仓库根目录 `NOTICE.md`。
