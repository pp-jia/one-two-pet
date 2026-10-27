# 发布 / 安装（one-two-pet）

这个包是 **DSH 插件 bundle**，不是纯 pet pack。它做两件事：

1. 安装时把 `pet/yier-hd-config.json` + `pet/yier-hd-animation/*.webm` 复制到
   `$DSH_HOME/dsh-pet/pet/`；
2. 在 DSH 设置里注册 **「一二 HD」** 配置页（显示位置 / 大小 / 角落 / 边距 / 热重载）。

## 前置

必须先安装 **dsh-pet**（运行引擎）。本插件检测不到 dsh-pet 时仍会安装素材，但桌宠不会显示，
配置页会给出提示。

## 本地安装（发布前自测）

在 `one-two-pet/` 根目录：

```powershell
dsh plugin --profile desktop add file:D:/smallProject/zhuochong/one-two-pet
```

装完重启 DSH（宿主半侧要重启；只刷新页面不够）。然后：

- DSH 设置 → **一二 HD**：改显示位置 / 大小 / 边距；
- 保存后会调用 dsh-pet 的 `/pet-display` 热重载；
- 如果 dsh-pet 设置页里看不到文件宠物，这是正常的：文件宠物不在 dsh-pet 设置页里列，
  但本插件的「一二 HD」配置页会直接改 `yier-hd-config.json`。

## 发布到 npm

```powershell
npm pack --dry-run   # 先看包内容（只包含 plugin + yier-hd 素材 + 文档）
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
- 改默认配置：`pet/yier-hd-config.json`。注意插件**不会覆盖已存在的用户配置**，
  用户升级后保留自己的显示/大小设置；
- 改配置页：`plugin/index.js` + `plugin/settings.html` + `plugin/client.js`。

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
如果没有授权，建议只私有安装，不要把素材公开上传。代码（插件壳、配置页）是 MIT，
但角色素材不随代码许可证授权。
