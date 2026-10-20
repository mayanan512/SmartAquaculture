# AGENTS.md —— 智渔云 (SmartAquaculture) 团队与 AI 协作开发规范

本文档供团队成员及 AI 编程助手（Codex / Cursor / Gemini 等）在模块开发前阅读并严格遵守。

## 一、开发前必读文件
在编写或修改任何代码前，请先阅读：
1. `README.md`
2. `docs/项目设计说明.md`
3. `docs/数据库设计.md`
4. `docs/接口与字段约定.md`
5. `docs/页面与模块分工.md`

## 二、架构与分层红线
1. **严格分层调用**：`pages/` → `services/` → `repositories/` → `database/`。禁止在 `pages/` 页面代码中直接编写复杂 SQL 或重复实现存量、成活率、饲料成本等计算公式。
2. **禁止私建数据库或改表字段**：所有表结构统一由 `database/schema.sql` 定义，数据库连接统一调用 `database.connection.get_connection()`。未经项目负责人确认，不得擅自修改公共字段名或枚举值。
3. **统一状态与来源枚举**：统一引用 `config/settings.py` 中定义的常量：
   - 告警状态：`NEW`（待确认）、`ACKNOWLEDGED`（处理中）、`RESOLVED`（已解决）、`CLOSED`（已关闭）。
   - 数据来源：`SIMULATED`（模拟数据）、`MANUAL`（人工录入）、`SENSOR`（传感器上报）。
   - 批次状态：`ACTIVE`（在养）、`COMPLETED`（已出塘结束）、`PLANNED`（计划中）。
4. **视觉与语言规范**：所有页面统一调用 `components.theme.apply_digital_twin_theme()` 加载深蓝、青蓝科技风样式，所有界面文案、图表标题、提示信息必须使用简体中文。
5. **真实性标注**：严禁将 `SIMULATED` 模拟数据标记为“真实传感器实时采集”；空值必须明确展示为“缺失/未采集”，严禁将 `NULL` 自动替换为 `0` 参与平均值或阈值计算。

## 三、标准模块开发提示词模板
```text
请基于当前 SmartAquaculture 项目开发分配给你的模块。
要求：
1. 先检查现有代码、目录、数据库和公共服务（config/settings.py、services/、repositories/）。
2. 只修改分配给你的模块及必要的配套服务和测试。
3. 遵循统一数据字段、业务状态、单位和统计口径。
4. 所有页面使用简体中文，调用 components.theme 延续统一深蓝青色数字孪生科技风。
5. 所有操作必须连接实际业务逻辑和 SQLite 数据库，不能只做静态 UI。
6. 开发后运行 python -m unittest discover -s tests -v，并检查数据能否持久化。
7. 最后输出修改文件清单、完成内容、测试结果、已知问题和待集成事项。
```
