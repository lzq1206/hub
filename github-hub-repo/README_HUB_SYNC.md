# 将 HubWhisper 接入 github.com/lzq1206/hub 指南

## 1. 仓库文件放入方式
你可以直接将本压缩包中的以下文件上传/提交到 `github.com/lzq1206/hub` 仓库根目录：
- `HubWhisper.html`：Web 端聚合微端页面（部署后可通过 `https://lzq1206.github.io/hub/HubWhisper.html` 直接访问，也可改名为 `index.html` 作为主入口）
- `HubWhisper.apk`：已签名的安卓端安装包（方便直接从仓库或 GitHub Pages 下载）
- `sites.json`：远程动态站点与排序配置文件

## 2. 远程自动增删与排序同步机制（无需重新打包安装 APK）
`HubWhisper.apk` 与 `HubWhisper.html` 已内置多源自动同步引擎，每次打开或切回前台时会按以下优先级自动拉取 `github.com/lzq1206/hub` 的最新站点与顺序：
1. **方式一（直接修改 `hub/index.html` 或 `README.md`）**：
   即使不维护 `sites.json`，只要你在 `github.com/lzq1206/hub` 的 `index.html` 中按顺序添加新的 `<a href="https://lzq1206.github.io/新项目/">新项目名称</a>` 卡片（或在脚本数组中新增站点），App 会自动按 HTML 中卡片出现的先后顺序解析并同步底部切换栏，顺序 100% 保持一致。
2. **方式二（维护 `sites.json`）**：
   如果你在 `github.com/lzq1206/hub` 根目录放置 `sites.json`，只需在数组中新增一行或调整数组顺序，所有已安装的手机端 `HubWhisper` 会在打开时自动增加对应底部标签并保持完全一致的排序。
