# AGENTS.md — A股交易分析与投研工作区

> 本文件供 AI 编码/分析代理（Kimi Code CLI、Claude Code 等）在本目录启动会话时自动加载。
> 与 `CLAUDE.md` 共存：`CLAUDE.md` 聚焦 Claude Code 特有的三阶段工作流铁律，本文件聚焦项目全景、架构约定与通用规则。

---

## 一、项目概述

**本项目不是一个传统软件开发项目**（无 pyproject.toml / package.json / Cargo.toml 等）。它是一个**个人 A 股交易分析与投研工作区**，主要用于：

1. **每日/每周/每月交易复盘**（收盘后结构化分析报告）
2. **盘前交易计划与条件单卡片**（开盘前机械执行的操作清单）
3. **板块与行业深度研报汇编**（半导体、光模块、算力金属等）
4. **交易错误档案管理**（归档、分类、推送 GitHub Issue）
5. **情绪扰动日历与海外催化跟踪**（事件驱动的风险/机会预警）
6. **AI Skill 迭代试炼**（在本目录验证规则有效后，再写入系统 skill 目录）

### 相关外部仓库（本项目不直接管理，但有工作流关联）

| 仓库 | 路径 | 用途 |
|------|------|------|
| **stock-skill** | `G:/github/stock-skill/` → `https://github.com/Tlanhan/stock-skill` | AI Skill 长期归档（系统 skill 验证后的终态） |
| **stock-journal** | `G:/github/stock-journal/` → `https://github.com/Tlanhan/stock-journal` | 复盘文件终态归档 + 交易错误 Issue |
| **本仓库 (stock-analysis)** | `G:/github/stock分析/` → `https://github.com/Tlanhan/stock-analysis.git` | 试炼场（讨论、草稿、工作数据） |

---

## 二、目录结构与文件类型

```
G:/github/stock分析/
├── AGENTS.md                           ← 本文件（项目级 AI 指令）
├── CLAUDE.md                           ← Claude Code 三阶段工作流铁律
├── .gitignore                          ← 忽略 .claude/ .omc/ *.zip session_*
│
├── trade-mistakes/                     ← 交易错误档案库（草稿区）
│   ├── README.md                       ← 使用说明与错误类型分类（E1-E7）
│   ├── INDEX.md                        ← 错误索引表（倒序，含统计）
│   ├── TEMPLATE.md                     ← 新错误记录模板
│   ├── sync-to-issue.sh                ← 本地 md → GitHub Issue 同步脚本
│   └── YYYY-MM-DD-简述.md              ← 每个错误一个文件
│
├── sentiment-calendar-YYYY-MM.md       ← 情绪扰动日历（按月生成）
├── oversea-catalyst-YYYY-WNN.md        ← 海外科技催化扫描（按周生成）
│
├── YYYY-MM-DD-daily-review.md          ← A股每日复盘报告
├── YYYY-MM-DD-intraday-*.md            ← 盘中复盘报告
├── YYYY-MM-DD-weekly-review.md         ← 周度复盘
│
├── YYYY-MM-DD-trading-card.md          ← 交易卡片（盘前机械执行清单）
├── YYYY-MM-DD-条件单设置卡*.md          ← 条件单设置卡（券商软件预埋单）
├── YYYY-MM-DD-A股开盘前作战计划.md      ← 盘前综合作战计划
│
├── *研报*.md / *指南*.md                ← 行业/板块深度研报汇编
├── 学习笔记-*.md                        ← 投资知识学习笔记
│
├── *.html                              ← 交互式可视化报告（ECharts/Tailwind）
│
├── .claude/settings.local.json         ← Claude Code 权限与 MCP 配置
└── .omc/                               ← OMC 插件状态（notepad/sessions/state）
```

### 文件命名约定

| 类型 | 模式 | 示例 |
|------|------|------|
| 每日复盘 | `YYYY-MM-DD-daily-review.md` | `2026-06-16-daily-review.md` |
| 盘中复盘 | `YYYY-MM-DD-intraday-HHmm.md` | `2026-06-16-intraday-1130.md` |
| 周度复盘 | `YYYY-MM-DD-weekly-review.md` | `2026-06-12-weekly-review.md` |
| 交易卡片 | `YYYY-MM-DD-trading-card.md` | `2026-06-12-trading-card.md` |
| 条件单卡 | `YYYY-MM-DD-条件单设置卡[-vN].md` | `2026-06-16-条件单设置卡-v2.md` |
| 情绪日历 | `sentiment-calendar-YYYY-MM.md` | `sentiment-calendar-2026-06.md` |
| 海外催化 | `oversea-catalyst-YYYY-WNN.md` | `oversea-catalyst-2026W23.md` |
| 错误档案 | `YYYY-MM-DD-简述.md`（4-8字中文） | `2026-06-02-COMPUTEX错过.md` |

> **周数算法**：ISO 8601 标准，可用 `date +%V` 验证。

---

## 三、技术栈与工具链

本项目**无编译/构建步骤**。内容生产依赖 AI Agent + 外部数据源 + Shell 脚本。

### 数据源

| 工具 | 能力 | 限制 |
|------|------|------|
| **kimi-datasource** (`query_stock`) | A股/港股实时行情、分钟K线、技术指标 | **不支持 ETF 查询**，返回 "No realtime data available" |
| **a-stock-analysis skill** (新浪财经接口) | ETF 实时行情、分时量能分析 | 深交所新 ETF（如 159558）可能无法获取 |
| **东方财富 API** | 板块数据、龙虎榜、资金流向 | 部分接口需 WebFetch |
| **WebSearch / web-search-prime** | 跨源新闻搜索、美股隔夜数据 | 需交叉验证（≥3 源） |

### HTML 报告技术栈

- **ECharts 5.4.3**（CDN）— 图表可视化
- **Tailwind CSS**（CDN）— 布局样式
- 纯前端单 HTML 文件，无构建步骤，浏览器直接打开

### Shell 脚本

- `trade-mistakes/sync-to-issue.sh` — 使用 `gh` CLI 将本地错误 md 同步为 GitHub Issue
  - 依赖：`gh` CLI 已登录 `Tlanhan/stock-journal`
  - 用法：`./sync-to-issue.sh 2026-06-02-COMPUTEX错过.md [--dry-run]`

### 配置文件

| 文件 | 用途 |
|------|------|
| `.claude/settings.local.json` | Claude Code 权限白名单、MCP 服务器配置 |
| `.omc/project-memory.json` | OMC 插件项目元数据（自动扫描，空 techStack） |
| `.omc/notepad.md` | OMC 工作记忆（会话笔记，7 天自动清理） |

---

## 四、核心工作流与铁律

### 4.1 三阶段分离工作流（Skill 迭代专用）

```
阶段 1: 本目录讨论（G:/github/stock分析/）  ← 默认模式
    ↓ 用户明确说"更新 skill"
阶段 2: 修改系统 skill（~/.claude/skills/ 或 ~/.agents/skills/）
    ↓ 用户明确说"推送"
阶段 3: 同步 GitHub 仓库（G:/github/stock-skill/）
```

- **阶段间必须由用户明确指令触发，AI 不得自作主张跨阶段执行**
- 详细规则见 `CLAUDE.md`

### 4.2 复盘文件写入路径

复盘文件的终态归档**不在本目录**，而在 `stock-journal` 仓库：

| 类型 | 终态路径 |
|------|---------|
| 日复盘 | `G:/github/stock-journal/reviews/daily/YYYY-MM/YYYY-MM-DD.md` |
| 盘中复盘 | `G:/github/stock-journal/reviews/daily/YYYY-MM/YYYY-MM-DD-intraday-HHmm.md` |
| 周复盘 | `G:/github/stock-journal/reviews/weekly/YYYY-WNN.md` |
| 月复盘 | `G:/github/stock-journal/reviews/monthly/YYYY-MM.md` |

- 写入前自检：目标目录不存在 → 自动 `mkdir -p`
- 写完报告路径并提醒用户"可推送"，用户说"推送复盘"时才执行 `git commit + push`

### 4.3 交易错误档案流程

```
trade-mistakes/YYYY-MM-DD-简述.md（草稿区）
    ↓ 用户说"推送错误" / "开 issue"
sync-to-issue.sh → GitHub Issue（Tlanhan/stock-journal）
    ↓ 成功后回写 issue 号到本地 md 顶部
更新 INDEX.md
```

- **错误终态是 GitHub Issue，不是文件**
- 错误类型分 7 类：E1 追涨杀跌 / E2 止损不严 / E3 情绪化开仓 / E4 规则外仓位 / E5 错过机会 / E6 提前出场 / E7 加错仓

---

## 五、⏰ 数据时效性铁律

### 获取数据前必须先确认北京时间

```python
from datetime import datetime, timezone, timedelta
bj = timezone(timedelta(hours=8))
print(datetime.now(bj).strftime('%Y-%m-%d %H:%M:%S %A'))
```

### 各市场交易时段（北京时间）

| 市场 | 交易时段 |
|------|---------|
| A股 | 周一-周五 9:30-11:30, 13:00-15:00 |
| 港股 | 周一-周五 9:30-12:00, 13:00-16:00 |
| 美股（夏令时 3月中-11月初） | 周一-周五 **21:30**-次日4:00 |
| 美股（冬令时 11月初-3月中） | 周一-周五 **22:30**-次日5:00 |
| 日股 | 周一-周五 8:00-14:00 |

- 数据获取后必须标注："数据获取时间：北京时间 YYYY-MM-DD HH:MM"
- **不要依赖 `date` 命令**（系统时区可能配置错误，必须用 Python UTC+8 手动转换）

### ⚠️ 日期与星期必须交叉核验（2026-06-17 新增铁律）

> **背景**：AI 多次凭印象把"6/16 周二"写成"6/16 周一"，导致复盘归因错误（把连续两天的踏空误记成不同事件）。**星期不能靠记忆推断，必须用代码核验。**

**铁律**：任何输出中涉及"日期 + 星期"时（如复盘标题、事件时间线、交易记录），**必须先用 Python 核验该日期对应的星期，再写入**：

```python
from datetime import datetime
print(datetime(2026,6,17).strftime('%Y-%m-%d %A'))
# 输出 2026-06-17 Wednesday → 周三，才能写"6/17 周三"
```

**禁止**：
- ❌ 凭印象推断"6/16 大概是周一"（实际是周二）
- ❌ 复制粘贴旧日期时只改数字不改星期
- ❌ 把"隔夜美股 6/16"和"A股 6/17"的星期搞混（美东 6/16 晚 = 北京 6/17 凌晨，但两者都涉及日期边界，星期必须分别核验）

**交易日历快速核对**（2026 年 6 月）：
| 周次 | 周一 | 周二 | 周三 | 周四 | 周五 |
|------|------|------|------|------|------|
| W24 (6/16-6/20) | 6/16 | 6/17 | 6/18 | 6/19 | 6/20 |

> 注：上表仅为示例格式，实际使用时必须用代码核验，不依赖此表。

### 反铁律

- ❌ 不确认当前时间就获取数据并分析
- ❌ 混淆北京时间与美东时间
- ❌ 用过期缓存数据当实时数据
- ❌ 不标注数据获取的具体时间
- ❌ **凭印象写星期，不核验日期-星期对应关系**

---

## 六、强制加载文件（自动检查）

### 情绪扰动日历

- **文件**：`G:/github/stock分析/sentiment-calendar-YYYY-MM.md`
- **触发**：用户问"明天怎么做"/"写卡"/做任何交易决策/触发复盘时
- **失效检查**：当月文件不存在 → 提示生成；距今 >25 天 → 提示刷新
- **写卡铁律**：检查"明日"是否在 🔴 强扰动日中，若在则加入"不做清单"+ 降仓建议

### 海外科技催化

- **文件**：`G:/github/stock分析/oversea-catalyst-YYYY-WNN.md`
- **触发**：用户问海外/美股/英伟达/苹果等关键词；写卡/盘前规划时
- **失效检查**：当周文件不存在 → 提示扫描；距今 >5 天 → 提示刷新
- **刷新触发词**："更新催化"/"刷新催化"/"更新海外"/"OST 扫描"

---

## 七、数据完整性与真实性规则

### 来源标注

- 所有数据必须标注来源（API 名称 / 媒体名 / 官方机构）
- 多源交叉验证（关键数据 ≥3 源）
- 标注数据可信度等级（✅ 已验证 / ⚠️ 估算 / ❌ 未获取）

### 消息真实性三层检验

| 层级 | 检验内容 | 失败动作 |
|------|---------|---------|
| 1️⃣ 双日期标注 | 报道日期 + 事件首发日期同时标注 | 缺一即退回重查 |
| 2️⃣ 旧闻翻炒识别 | 跨源搜索找首发日期 | >30 天 → 强制 ❌ 旧闻翻炒 |
| 3️⃣ 借利好出货反向判定 | 5 个出货信号叠加检查 | 2+ 信号 → 🚨 出货警报 |

### 信息源分级

| 等级 | 代表性来源 |
|------|-----------|
| ⭐⭐⭐⭐⭐ | 官方机构（BOJ、Fed、BLS、上交所等） |
| ⭐⭐⭐⭐ | 一线通讯社（Reuters、Bloomberg、FT、CNBC） |
| ⭐⭐⭐ | 金融机构研究/中国一线媒体（东方财富、证券时报） |
| ⭐⭐ | 智库/个人观点/中国二线媒体 |
| ⭐ | 个人博客/社交媒体 |

---

## 八、内容写作规范

### Markdown 报告结构

- **顶部 frontmatter**：日期、数据截止时间、可信度等级、生成 skill
- **数据表格**：用 Markdown 表格，标注来源与验证状态
- **三情景推演**：🟢 鸽/乐观 · 🟡 中/中性 · 🔴 鹰/悲观
- **强制风险提示**：所有分析报告末尾必须有"风险提示"段落
- **数据来源**：每条关键数据后注明 `[来源: XXX]`

### HTML 报告规范

- 单文件、CDN 依赖、浏览器直接打开
- 暗色主题：毛玻璃效果（`.glass`）、悬浮深度卡
- 浅色主题：ECharts 图表 + sticky 指标栏
- 中文 `lang="zh-CN"`，字体优先 `-apple-system`

### 交易卡片规范

- 打印/截图放手机旁，到价机械执行
- 包含：持仓快照、隔夜美股、触发条件表、止损止盈位、资金分配

---

## 九、Git 提交规范

- **Commit message**：中文描述性，必须包含"做了什么"，禁止 `update`/`fix` 空话
  - 示例：`新增：6/16 A股每日复盘报告（多Agent深度版）`
  - 示例：`认知迭代：有色与科技跷跷板效应+高位识别5信号`
- **Atomic commit**：每个独立逻辑一个 commit，不允许 mega commit
- **推送需用户明确触发**："推送"/"push"/"同步仓库" 等
- 错误档案默认不推 GitHub（含交易金额/仓位敏感信息），需用户明确说"推送错误档案"

---

## 十、安全注意事项

1. **交易金额/仓位隐私**：错误档案含敏感交易数据，默认不推公开仓库
2. **API Key 保护**：`.claude/settings.local.json` 含 MCP 服务认证信息，已被 `.gitignore` 忽略
3. **不编造数据**：数据获取失败时标注"未能确认"，不用旧数据填空
4. **投资免责声明**：所有分析报告必须包含"不构成投资建议"声明

---

## 十一、常用 AI Skills（本目录关联）

| Skill | 用途 | 触发场景 |
|-------|------|---------|
| `a-share-daily-review` | 收盘复盘 | "日复盘"/收盘后 |
| `a-share-intraday-review` | 盘中复盘 | 11:30-13:00 午间 |
| **`a-share-trigger-check`** | **交易执行框架（条件卡/扳机/复盘/量价）** | **用户表达任何交易意图时强制调用（见下方）** |
| `a-share-catalyst` | 事件催化扫描（含 OST 海外） | "更新催化"/周一盘前 |
| `a-share-sentiment-calendar` | 情绪扰动日历 | 月度生成/"刷新日历" |
| `a-stock-analysis` | 实时行情与量能分析 | 查 ETF 行情/分时量能 |
| `a-share-technical-analysis` | 技术面分析 | 均线/支撑压力位 |
| `a-share-portfolio` | 持仓跟踪与换仓决策 | 查持仓/盈亏 |
| `a-share-etf-selector` | 板块 ETF 选品 | "XX板块有什么 ETF" |
| `data-integrity-protocol` | 数据完整性强制协议 | 所有金融分析任务 |

### 🔴 trigger-check 强制调用规则（2026-06-17 新增）

> **背景**：AI 多次在用户表达交易意图时只做分析，没调用 trigger-check 执行框架，导致用户"看好但不敢下单"未被系统拦截。
> **规则**：用户表达以下任一意图时，AI **必须主动调用 `a-share-trigger-check`**，不允许用分析对话替代执行框架。

| 用户意图 | 强制模式 | 说明 |
|---------|---------|------|
| "我想买/我要做/可以做吗" + 明确标的 | 模式A 写条件交易卡 | 先出卡（价格/仓位/止损），再分析 |
| "应该买吗/我有感觉/现在能进吗" | 模式B 扳机检查 | 30秒 GO/NO-GO，明确二值化 |
| "后悔没做/想做但没做/错过了/踏空" | 模式C 失误复盘 | 结构化归因（不是情绪安慰）|
| "缩量/量价/低开" | 模式I 量价触发 | 四重确认 + 量价观察清单 |
| "明天怎么做/明日策略/写卡" | 模式A + 情绪日历 + 催化 | 组合调用，综合决策 |

**核心铁律**：执行框架优先于分析。不允许先分析半天最后才问"要不要写卡"——用户说"想交易"时，**先出卡，再补数据支撑**。

**详细规则与工作流见 `CLAUDE.md`「交易决策强制调用 Skill 矩阵」**。

---

*本文件由 AI 在 2026-06-15 创建，2026-06-16 全面重写，2026-06-17 补充日期核验铁律与 trigger-check 强制调用规则。如需修改核心铁律，需经用户明确同意。*
