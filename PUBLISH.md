# 发布 / 安装（one-two-pet）

这个包是一个 **DSH 插件 bundle**，作用是“一键安装 pet pack”：

- 安装 / 加载时把 `pet/yier-hd-config.json` + `pet/yier-hd-animation/*.webm`
  复制到 `$DSH_HOME/dsh-pet/pet/`；
- **没有设置页**，不会在 DSH 设置里新增任何面板；
- 配置仍然是 dsh-pet 的文件宠物机制：
  `$DSH_HOME/dsh-pet/pet/yier-hd-config.json`。

## 前置

必须先安装 **dsh-pet**（运行引擎）。本插件检测不到 dsh-pet 时仍会安装素材，但桌宠不会显示；
控制台会打印 `[one-two-pet] ... 未检测到 dsh-pet`。

## 本地安装（发布前自测）

在 `one-two-pet/` 根目录：

```powershell
dsh plugin --profile desktop add file:D:/smallProject/zhuochong/one-two-pet
```

装完**重启 DSH**（宿主半侧插件只在启动时加载）。之后：

- 桌宠按 `yier-hd-config.json` 里的 `display` / `size` / `position` 出现；
- 没有新增设置页；改配置请直接编辑 JSON，或右键宠物触发 dsh-pet 的重载；
- 想调显示/大小：编辑
  `C:\Users\ppj\.dsh\dsh-pet\pet\yier-hd-config.json`。

## 发布到 npm

```powershell
npm pack --dry-run   # 先看包内容
npm publish --access public
```

别人安装：

```powershell
dsh plugin --profile desktop add one-two-pet
```

> 包名 `one-two-pet` 目前未被占用（发布前再确认一次）。如果已被占用，改成
> `@你的scope/one-two-pet` 或 `dsh-pet-onetwo`，并同步 `package.json` 的 `name`
> 与 `cordis.patch.yml` 的 `id`。

## 发布到 GitHub（不走 npm）

别人也可以直接：

```powershell
dsh plugin --profile desktop add "github:pp-jia/one-two-pet"
```

## 版本更新

- 改动画：替换 `pet/yier-hd-animation/*.webm`，升 `version`；
- 改默认配置：`pet/yier-hd-config.json`。插件**不会覆盖已存在的用户配置**，
  用户升级后保留自己的显示/大小设置；
- 本插件没有客户端半侧，不需要重建 lib/client。

## 卸载

```powershell
dsh plugin --profile desktop remove one-two-pet
```

卸载只移除插件本身；`$DSH_HOME/dsh-pet/pet/yier-hd-*` 素材会保留，避免误删用户配置。
要彻底清理：

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.dsh\dsh-pet\pet\yier-hd-animation"
Remove-Item -Force "$env:USERPROFILE\.dsh\dsh-pet\pet\yier-hd-config.json"
```

## 版权提醒

**一二 / 布布** 是现有 IP，形象版权不属于本项目。个人、非商业自用没问题；
**公开发布到 npm / GitHub / 插件市场前，请先确认你拥有分发该形象的权利**。
如果没有授权，建议只私有安装，不要把素材公开上传。代码（插件壳）是 MIT，
但角色素材不随代码许可证授权。
