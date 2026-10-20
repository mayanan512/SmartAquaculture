# 智渔云 —— 智慧养殖数字孪生管理平台 (SmartAquaculture)

> **当前版本**：`v0.1.0`（基础项目骨架与全链路核心底座版）  
> **推荐技术栈**：Python 3.11+、Streamlit、SQLite、Pandas、Plotly、OpenPyXL、Scikit-learn  
> **参赛方向**：中国研究生智慧城市技术与创意设计大赛

---

## 一、项目简介

**智渔云**是一套面向鱼、虾、蟹等水产养殖场景的轻量化数字孪生管理与智能决策平台。系统通过数字孪生园区大屏集中展示养殖场全局态势，打通**水质监测中心 → 智能预警中心 → 养殖生产管理 → AI 智能决策辅助 → 养殖分析报表**的完整业务闭环。

### 核心设计原则
1. **数据同源共享**：总览大屏、监测、预警、生产、AI与报表模块统一通过 `services/` 和 `repositories/` 读写同一套 SQLite 数据库，杜绝静态假页面。
2. **严格区分数据来源**：所有记录显式标注 `SIMULATED`（模拟演示数据）、`MANUAL`（人工录入）或 `SENSOR`（真实传感器），不将模拟数据伪装为真实监测值。
3. **免 Git 模块化协作**：支持团队成员按模块分工、独立本地数据库开发、ZIP 版本包交付与合并。

---

## 二、目录结构

```text
SmartAquaculture/
├── app.py                      # 系统主入口与全局导航导览
├── requirements.txt            # Python 依赖清单
├── run.bat                     # Windows 一键环境构建与启动脚本
├── README.md                   # 项目说明与启动指南
├── .gitignore                  # 打包与版本忽略配置
├── AGENTS.md                   # AI / Codex 辅助协作开发规范
├── pages/                      # 页面层（仅负责布局、交互与调用服务）
│   ├── 01_智慧养殖总览.py
│   ├── 02_水质监测中心.py
│   ├── 03_智能预警中心.py
│   ├── 04_养殖生产管理.py
│   ├── 05_AI智能决策.py
│   ├── 06_养殖分析报表.py
│   ├── 07_养殖场与设备管理.py
│   ├── 08_数据管理中心.py
│   └── 09_系统设置.py
├── components/                 # 公共 UI 组件层（科技风样式、指标卡、通用图表）
├── services/                   # 业务服务层（核心业务规则、预警判断、统计算法口径）
├── repositories/               # 数据访问层（统一 SQL 查询与事务持久化）
├── database/                   # 数据库层
│   ├── __init__.py
│   ├── connection.py           # SQLite 连接与事务上下文管理
│   ├── init_db.py              # 幂等建表与演示数据初始化脚本
│   └── schema.sql              # 20 张核心数据表定义
├── algorithms/                 # 算法层（规则阈值评估、趋势斜率与异常检测）
├── config/                     # 配置层（状态枚举、单位、默认阈值与路径）
├── data/                       # 本地数据库存储目录与示例导入 CSV
├── assets/                     # 静态资源（深蓝青色科技风 CSS、园区数字孪生矢量图）
├── docs/                       # 团队协作与设计文档
│   ├── 项目设计说明.md
│   ├── 数据库设计.md
│   ├── 接口与字段约定.md
│   └── 页面与模块分工.md
└── tests/                      # 自动化单元测试与全链路验证
```

---

## 三、快速启动方式

### 方式一：Windows 一键启动（推荐）
双击项目根目录下的 `run.bat`，脚本将自动检查 Python 环境、创建 `.venv` 虚拟环境、安装依赖、安全初始化 SQLite 数据库并打开浏览器运行系统。

### 方式二：命令行手动启动（Windows / macOS / Linux）
```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库（幂等执行，仅在空库时插入 SIMULATED 演示数据）
python -m database.init_db

# 4. 启动应用
streamlit run app.py
```

### 重置演示数据
如需清空现有本地数据并重新生成标准演示数据，可执行：
```bash
python -m database.init_db --reset-demo
```

### 运行自动化测试
```bash
python -m unittest discover -s tests -v
```
