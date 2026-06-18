# AGENTS.md — A股交易分析工作区（权威源）

> 本文件是所有 AI 代理（Claude Code / OpenCode / Codex 等）的**唯一权威操作规则**。
> `CLAUDE.md` 补充 Claude Code 特有的三阶段工作流细节，操作规则以本文件为准。

---

## 项目性质

**不是软件项目** — 无 build/test/package.json/pyproject.toml。这是个人 A 股交易分析与投研工作区，产出物为 Markdown 报告、HTML 可视化页面和 Python 工具脚本。

---

## 关键工具

| 工具 | 用法 | 注意 |
|------|------|------|
| `tools/qt_quote.py` | `python tools/qt_quote.py 600183 002916` 或 `python tools/qt_quote.py @watchlist.txt` | 腾讯 qt.gtimg.cn 接口，A股/指数行情，支持 `--json`/`--csv` |
| `trade-mistakes/sync-to-issue.sh` | `./sync-to-issue.sh YYYY-MM-DD-简述.md [--dry-run]` | 需 `gh` CLI 已登录 `Tlanhan/stock-journal` |

### 数据源限制

- `kimi-datasource` (`query_stock`)：**不支持 ETF 查询**
- `a-stock-analysis skill`（新浪接口）：深交所新 ETF（如 159558）可能无法获取
- `qt_quote.py`：当前最稳定的行情源，无风控，批量快

---

## 文件命名约定

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

> 周数算法：ISO 8601，`date +%V` 验证。

---

## 复盘文件路径（非本目录）

**复盘终态归档在 `G:/github/stock-journal/`，不在本目录。**

| 类型 | 写入路径 |
|------|---------|
| 日复盘 | `G:/github/stock-journal/reviews/daily/YYYY-MM/YYYY-MM-DD.md` |
| 盘中复盘 | `G:/github/stock-journal/reviews/daily/YYYY-MM/YYYY-MM-DD-intraday-HHmm.md` |
| 周复盘 | `G:/github/stock-journal/reviews/weekly/YYYY-WNN.md` |

写入前 `mkdir -p`，写完提醒用户"可推送"，用户说"推送复盘"才 `git commit + push`。

---

## 交易错误档案

- 草稿区：`trade-mistakes/YYYY-MM-DD-简述.md`（从 `TEMPLATE.md` 复制）
- 终态：**GitHub Issue**（`Tlanhan/stock-journal`），不是文件
- 用户说"推送错误"/"开 issue" → `sync-to-issue.sh` → 成功后回写 issue 号到本地 md
- **错误类型**：E1 追涨杀跌 / E2 止损不严 / E3 情绪化开仓 / E4 规则外仓位 / E5 错过机会 / E6 提前出场 / E7 加错仓
- **默认不推 GitHub**（含交易金额/仓位敏感信息）

---

## 强制规则（会搞错的高频坑）

### 0. 会话启动必须校准"今天"（最高优先级前置层）

**每次会话开始的第一件事**，不是回应用户问题，而是先用 Python 确认并**明确告知用户**"今天是几月几号、星期几、当前北京时间几点、A 股处于什么交易时段（盘前/盘中/盘后/休市）"。这是所有后续讨论的时间基准。

```python
from datetime import datetime, timezone, timedelta
bj = timezone(timedelta(hours=8))
now = datetime.now(bj)
print(now.strftime('%Y-%m-%d %A %H:%M:%S'))
# 必须输出且告知用户：例如 "今天 2026-06-18 周四 16:17，A股已收盘"
```

**为什么必须校准**：
- AI 会跨会话丢失时间上下文，把"今天"当作训练数据里的某天，导致用旧数据分析"今天"
- 已发生事故：上个会话把 6/18 真实收盘数据（创业板+2.05%）错标成 6/17，因为没校准"今天"就拉数据，混淆了缓存与实时
- 用户说"今天"/"昨天"/"明天"时，**必须先转换为绝对日期 + 星期**再处理，禁止保留相对时间表述

**校准输出模板**（每次会话首条回复必须包含）：
> ✅ 已校准：**今天 2026-MM-DD 周X HH:MM**（北京时间），A 股状态：[盘前/盘中-上午/午间休市/盘中-下午/已收盘/休市]。

**附加要求**：
- 校准后再判断当日数据是否已可获取（盘后才有收盘数据，盘前只能用昨日数据并标注）
- 若用户消息提及具体日期，用代码核验该日期的星期，禁止凭记忆
- 若距上次会话 >1 天，主动提醒用户"情绪日历/海外催化文件可能需要刷新"

### 1. 时间必须用 Python UTC+8

系统时区可能配置错误，**禁止依赖 `date` 命令**。

```python
from datetime import datetime, timezone, timedelta
bj = timezone(timedelta(hours=8))
print(datetime.now(bj).strftime('%Y-%m-%d %H:%M:%S %A'))
```

获取数据后必须标注：`数据获取时间：北京时间 YYYY-MM-DD HH:MM`

### 2. 日期+星期必须用代码核验

**禁止凭印象写星期。** AI 多次把"6/16 周二"写成"6/16 周一"。

```python
from datetime import datetime
print(datetime(2026,6,17).strftime('%Y-%m-%d %A'))
# 2026-06-17 Wednesday → 才能写"6/17 周三"
```

### 3. 各市场交易时段（北京时间）

| 市场 | 交易时段 |
|------|---------|
| A股 | 周一-周五 9:30-11:30, 13:00-15:00 |
| 港股 | 周一-周五 9:30-12:00, 13:00-16:00 |
| 美股（夏令时 3月中-11月初） | **21:30**-次日4:00 |
| 美股（冬令时 11月初-3月中） | **22:30**-次日5:00 |

### 4. 消息真实性三层检验

任何消息驱动型交易决策必须过三层：

1. **双日期标注**：报道日期 + 事件首发日期同时标注
2. **旧闻翻炒识别**：跨源搜索找首发日期，>30天 → ❌ 旧闻翻炒
3. **借利好出货反向判定**：5个出货信号叠加，2+ → 🚨 出货警报

### 5. trigger-check 强制调用

用户表达交易意图时**必须先调用 `a-share-trigger-check`**，不允许用分析替代执行框架。

| 用户意图 | 强制模式 | 输出 |
|---------|---------|------|
| "我想买/我要做/可以做吗" + 明确标的 | 模式A 写条件交易卡 | IF-THEN 条件卡（价格/仓位/止损）|
| "应该买吗/我有感觉/现在能进吗" | 模式B 扳机检查 | 30秒 GO/NO-GO |
| "后悔没做/想做但没做/错过了/踏空" | 模式C 失误复盘 | 结构化归因 |
| "缩量/量价/低开" | 模式I 量价触发 | 四重确认 + 量价观察清单 |
| "明天怎么做/明日策略/写卡" | 模式A + 情绪日历 + 催化 | 组合调用 |

**核心铁律**：执行框架优先于分析。用户说"想交易"时，**先出卡，再补数据支撑**。不允许用分析对话替代执行框架。

### 6. 情绪扰动日历强制加载

- **文件**：`sentiment-calendar-YYYY-MM.md`（本目录）
- **触发**：用户问"明天怎么做"/"写卡"/做任何交易决策/触发复盘时
- **失效检查**：当月文件不存在 → 提示生成；距今 >25 天 → 提示刷新
- **写卡铁律**：检查"明日"是否在 🔴 强扰动日中，若在则加入"不做清单"+ 降仓建议

### 7. 海外科技催化主动扫描

- **文件**：`oversea-catalyst-YYYY-WNN.md`（本目录）
- **触发**：用户问海外/美股/英伟达/苹果等关键词；写卡/盘前规划时
- **失效检查**：当周文件不存在 → 提示扫描；距今 >5 天 → 提示刷新
- **刷新触发词**："更新催化"/"刷新催化"/"更新海外"/"OST 扫描"

### 8. 综合分析流程（交易决策时）

```
用户问"是否应该交易"
  → [第1步] a-share-trigger-check（执行框架优先）
  → [第2步] 加载情绪日历 + 海外催化（扰动检查）
  → [第3步] a-share-technical-analysis / a-stock-analysis（数据支撑）
  → [输出] 执行框架 + 扰动检查 + 数据支撑 = 综合决策
```

每个 skill 的输出必须嵌入最终回复，不能只说"我调用了 skill"。

---

## Git 提交规范

- Commit message：中文描述性，禁止 `update`/`fix` 空话
- 示例：`新增：6/16 A股每日复盘报告` / `认知迭代：有色与科技跷跷板效应`
- Atomic commit，每个独立逻辑一个 commit
- **推送需用户明确触发**：用户说"推送"/"push"才执行

---

## 相关仓库

| 仓库 | 路径 | 用途 |
|------|------|------|
| stock-skill | `G:/github/stock-skill/` | AI Skill 长期归档（`~/.claude/skills/` → 此仓库） |
| stock-journal | `G:/github/stock-journal/` | 复盘文件终态归档 + 交易错误 Issue |
| 本仓库 | `G:/github/stock分析/` | 试炼场（讨论、草稿、工作数据） |

---

## 安全

- `.claude/settings.local.json` 含 MCP 认证信息，已被 `.gitignore` 忽略
- 数据获取失败时标注"未能确认"，不用旧数据填空
- 所有分析报告必须包含"不构成投资建议"声明

---

*2026-06-18 重写；2026-06-18 增补第0条"会话启动校准今天"铁律（修复跨日数据混淆事故）。详细工作流（三阶段分离、情绪日历加载、海外催化扫描等）见 `CLAUDE.md`。*
