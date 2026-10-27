# HD 源视频（一二）

这些是 `yier-hd` 的绿幕源视频：1280×720、24fps、6.08s、H.264。
`scripts/build_hd.ps1` 会用 `scripts/import_video.py` 把它们抠像、缩放、编码成
`pet/yier-hd-animation/*.webm`。

| 文件 | 动作 | 输出动画 | 裁剪 | 角色高度 |
| --- | --- | --- | --- | --- |
| `00-idle.mp4` | 待机呼吸 | `待机HD.webm` | `330,20,960,710` | 270 |
| `01-swing.mp4` | 荡秋千 | `荡秋千HD.webm` | `180,0,1000,720` | 350 |
| `02-headache.mp4` | 脑阔疼 | `脑阔疼HD.webm` | `340,30,940,710` | 270 |
| `03-please.mp4` | 拜托 球球你 | `拜托球球你HD.webm` | `340,30,940,710` | 270 |
| `04-skincare.mp4` | 护肤/发带 | `护肤HD.webm` | `340,30,940,710` | 270 |

重新生成：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_hd.ps1 -Force
```

说明：

- 这 5 段都是 **原地动作**，没有走路/拖拽/转向素材，所以 HD 版暂时不漫游。
- 新视频是低饱和绿幕，默认用 `--key-mode hsv`；纯 #00FF00 亮绿幕可用 `--key-mode dominance`。
- 版权归一二布布原作者 / 表情包权利人；仅个人非商业使用。
