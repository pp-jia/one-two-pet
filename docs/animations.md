# 动画一览

共 35 段。源图集为 8 列 × 9 行、192×208/格；输出统一 640×360、24fps、VP9-alpha。

| 动画名 | 时长 | 源行 | 用途 / 备注 |
| --- | ---: | --- | --- |
| 待机 | 2.00s | 0 | idle breathing |
| 东张西望 | 2.00s | 0 | turn/look around; dsh-pet flips facing after it ends |
| 悬空挣扎 | 1.67s | 4 | drag loop |
| 元气挥手 | 2.00s | 3 | click reaction — wave |
| 开心跳跳 | 1.67s | 4 | click reaction — happy hop |
| 委屈巴巴 | 1.71s | 5 | click reaction — teary/shy |
| 认真看手机 | 1.71s | 8 | click reaction — phone |
| 捧杯暖手 | 2.00s | 6 | click reaction — warm drink |
| 小跑 | 6.00s | 7 | move — trot |
| 一蹦一跳 | 5.00s | 4 | move — hop |
| 欢快冲刺 | 5.71s | 1 | move — sprint |
| 悄悄走 | 6.22s | 2 | move — quiet walk |
| 发会儿呆 | 3.00s | 0 | bubble with ... |
| 打瞌睡 | 4.00s | 0 | sleepy |
| 伸懒腰 | 2.67s | 4 | stretch |
| 转圈圈 | 2.00s | 7 | spin |
| 数星星 | 3.00s | 0 | count stars |
| 追逐泡泡 | 2.40s | 0 | chase bubbles |
| 摇摇晃晃 | 2.40s | 0 | sway |
| 是啊，吃什么 | 3.00s | 0 | text clip — noMirror |
| 深度思考 | 2.00s | 8 | deep thought |
| 新年好 | 2.00s | 3 | seasonal — new year |
| 余额-钱包鼓鼓 | 3.00s | 8 | balance tier 0 — full wallet |
| 余额-数金币 | 3.00s | 6 | balance tier 1 |
| 余额-钱包还好 | 2.40s | 0 | balance tier 2 |
| 余额-有点心疼 | 2.00s | 5 | balance tier 3 |
| 余额-快见底 | 3.20s | 5 | balance tier 4 |
| 余额-空空如也 | 4.00s | 5 | balance tier 5 |
| 碎碎念-点头 | 3.00s | 0 | whisper — nodding |
| 工作状态-思考冒泡 | 3.00s | 0 | work — thinking |
| 工作状态-忙碌敲键盘 | 2.57s | 8 | work — typing |
| 工作状态-清点归档 | 2.40s | 6 | work — done |
| 工作状态-原地踱步张望 | 2.25s | 7 | work — waiting |
| 工作状态-雀跃庆祝 | 1.67s | 4 | work — success |
| 工作状态-垂头叹气冒汗 | 3.20s | 5 | work — error |

## 配置里的分组

- `idle`：待机、发呆、打瞌睡、摇摇晃晃、数星星
- `turn`：东张西望
- `drag`：悬空挣扎
- `clicks`：元气挥手、开心跳跳、委屈巴巴、认真看手机、捧杯暖手
- `moves`：小跑、一蹦一跳、欢快冲刺、悄悄走
- `events.balance`：余额-钱包鼓鼓 → 空空如也（6 档）
- `events.whisper`：碎碎念-点头 / 元气挥手 / 认真看手机
- `events.workStatus`：思考 / 敲键盘 / 归档 / 踱步 / 庆祝 / 出错（6 档）
