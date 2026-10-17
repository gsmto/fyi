# FYI · Personal Intelligence Archive

Personal Intelligence Hub 的公开内容源。报告正文、结构化条目和原始来源都保存在这个仓库，Site 在访问或刷新时读取，无需随日报重新部署。

## 目录约定

| 路径 | 内容 |
| --- | --- |
| `catalog.json` | 大分类及栏目注册表，添加栏目时修改 |
| `content/technology-business/daily-brief/index.json` | 最新资讯的月份清单 |
| `content/technology-business/daily-brief/2026/10.json` | 2026 年 10 月的日报 |
| `content/cities-housing/hangzhou-property/index.json` | 楼市的月份清单 |
| `content/cities-housing/hangzhou-property/2026/10.json` | 2026 年 10 月的楼市报告 |
| `content/games-entertainment/games/index.json` | 游戏资讯的月份清单，首份报告前为空 |
| `docs/ARCHIVING.md` | 自动任务写入流程与失败处理 |
| `schemas/month.schema.json` | 月文件和单份报告的数据格式 |
| `scripts/archive.py` | 不依赖第三方库的校验与合并工具 |
| `meta/migrations/2026/10/17-hub-v1.json` | 首批历史迁移记录 |

目录分四层：**大分类 → 栏目 → 年份 → 月文件**。每个年份下通常最多 12 个 JSON，单个月文件内按日期保存独立报告。这样避免一个目录堆积数千个文件，也避免 Site 为每一天发起一个网络请求。

每份报告的稳定 ID 为 `collectionId-YYYY-MM-DD`，日期使用 Asia/Shanghai。同一天重跑只更新该报告，保留同月其他日期。图片用报告正文中的 Markdown 和来源链接保留，不提交大体积二进制。

## 使用

```sh
python3 scripts/archive.py validate
python3 scripts/archive.py upsert /absolute/path/to/one-brief.json
```

`upsert` 只合并一个栏目当月文件，并重建该栏目的月份清单；用一次 commit 提交这两个文件。也可以通过已有 GitHub 连接按 [归档流程](docs/ARCHIVING.md) 执行同样操作。

## 扩展栏目

先复用已有大分类，确有需要再在 `catalog.json.categories` 增加大分类。新增栏目在 `catalog.json.collections` 注册唯一 `id`、名称、描述、颜色、`categoryId` 和 `path`，再创建对应 `index.json`（`shards: []` 即可）。Site 会自动发现栏目，无需为每个栏目修改代码。大分类进一步增长时可在 `content/` 下增加中间目录，只需调整注册表中的 `path`。

日期、栏目 ID、日报 ID 均不得因为显示名称或目录迁移而随意变化。历史补录保留 `summary` / `partial` 标记；只有真实完整正文才可标为 `full`。

## 栏目与任务

执行时间使用 Asia/Shanghai（北京时间），由 ChatGPT 定时任务管理：

| 栏目 | 执行时间 | 内容 |
| --- | --- | --- |
| 最新资讯 | 每天 08:00，沿用原弹性调度 | AI、软件工程与科技商业等重点信息 |
| 楼市 | 每天 09:00 | 杭州及转塘周边重点区域楼市观察 |
| 游戏 | 每天 09:00 | 分国内与国外筛选单机、主机与 PC 游戏重点资讯 |

2026-10-18 起，原“每日重点简报”和“杭州楼市晚报”的栏目显示名称分别改为“最新资讯”和“楼市”，既有 ID、路径和历史记录保留。游戏首份报告在任务成功执行后生成，栏目初始化不伪造历史数据。

## 首批数据

2026-10-17 从 Hub 当前数据库迁移 29 份历史摘要、135 个条目：每日重点简报 22 份，杭州楼市晚报 7 份。缺失日期不补造，缺失原文、链接和评分不猜填，迁移不构成事实重新核验。日后的自动任务保存完整正文。

Site: https://ice-personal-intelligence-hub.alight-chime-5317.chatgpt.site

本仓库公开；仅存放拟公开的信息报告，不存放凭据、私人对话或任务内部标识。
