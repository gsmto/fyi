# 模型前线数据

Personal Intelligence Hub 的模型前线读取本目录 `current.json`，无需重新部署页面。源码和发布流程位于私有仓库 `gsmto/fyi-site`。

初始资料从旧模型前线迁入，核验日期为 **2026-10-13**。迁移日期不是资料重新核验日期。

## 更新约定

- 保留 `schemaVersion: 1`，以及 `models`、`news`、`companies`、`evaluations`、`updatedAt`、`verifiedAt`、`provenance` 字段。
- 每个模型使用稳定且唯一的 `id`；公司限 OpenAI、Anthropic、Google、Meta、xAI。价格单位为美元/百万 tokens，未知价格或上下文使用 null，不使用 0 代表未知。
- `verified` 只记录实际核对官方来源的日期；`verifiedAt` 使用档案中最早的模型核验日期。未核实的旧字段保留日期并解释原因，不得更新日期伪装为已核验。
- 保存 HTTPS 官方来源。OpenRouter 是独立渠道目录，不覆盖官方模型价格。
- `pricingRules` 中 `minInput` 是包含边界的输入 token 阈值；`from` 是生效日期。按数组顺序应用匹配规则，后匹配规则覆盖前者；对每个阈值核对官方说明。
- 新闻按 URL 去重，上限 500 条；评测保留公司、测试日期、口径、原始报告，不能将不同条件的成绩强行排名。
- 内容有实际变更才更新 `updatedAt`；同时写入 `snapshots/YYYY/MM/YYYY-MM-DD.json` 历史快照。提交前在私有源码中用 `lib/observatory.ts` 的 `observatorySchema` 校验完整 JSON，并运行价格边界检查。
- 写入前读取当前 main；使用预期旧 SHA 更新分支，冲突时重新读取和合并。不要覆盖现有日报、日历或其他集合。提交后按提交 SHA 读回核对。

线上 `/api/models` 验证结构，失败则返回带日期的本地快照和提示；资料成功读取缓存一分钟。公司新闻和渠道目录独立请求，缓存十五分钟。

资料核验需要单独执行；本目录的存在并不表示已创建定期更新任务。
