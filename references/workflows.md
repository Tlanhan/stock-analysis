# 工作流程示意图集（从 CLAUDE.md 抽取，2026-06-23）

> 本文件汇集 CLAUDE.md 中 6 个强制规则的执行流程示意图。
> 主文件（CLAUDE.md）保留触发条件与核心铁律，执行细节见本文件。
> 内容从 CLAUDE.md 机械搬运，未改一字。

---

## 复盘文件写入流程

<a id="review-write"></a>

```
收盘时间到 / 用户说"日复盘"
   ↓
Claude 触发 a-share-daily-review skill
   ↓
自动检查 {{WORKSPACE_JOURNAL}}/reviews/daily/YYYY-MM/ 目录是否存在
   ↓
mkdir -p 后,Write 到 YYYY-MM-DD.md
   ↓
报告: 已写入 [文件路径] (本地仓库工作树,等用户说"推送复盘"才 push)
   ↓
用户说"推送复盘" → cd stock-journal/ → git add reviews/ → atomic commit → push
```

---

## 交易决策综合分析流程

<a id="trading-decision"></a>

```
用户："我有点后悔早上没做159558，我觉得明天可能有回踩"
    ↓
[第1步] 识别意图：踏空 + 有标的 + 有预判 → 触发组合
    ├─ a-share-trigger-check 模式C（踏空归因）
    └─ a-share-trigger-check 模式A（写明日条件卡）
    ↓
[第2步] 强制加载背景
    ├─ Read sentiment-calendar-2026-06.md（6/18是否强扰动日）
    └─ Read oversea-catalyst-2026W25.md（FOMC 进行中）
    ↓
[第3步] 调用数据 skill
    ├─ qt_quote.py 拉 159558 + 深指 + 中证500 行情
    └─ 技术面：159558 的 5日线位置、乖离率
    ↓
[输出] 综合决策报告：
    ┌─ 模式C 踏空归因表（结构化，不是情绪）
    ├─ 模式A 明日条件交易卡（159558 的 IF-THEN）
    ├─ 扰动检查（6/18 FOMC = 🔴强扰动 → 写入"不开新仓"或调整）
    ├─ 量价观察清单（设备今日放量=警惕，明日关注）
    └─ 仓位温度计（深指乖离+1.6%=超买，等回踩）
```

---

## 交易决策综合分析流程

<a id="trading-decision"></a>

```
用户问"明天怎么做"
   ↓
Claude 自动 Read {{WORKSPACE_ANALYSIS}}/sentiment-calendar-2026-06.md
   ↓
检查"明日"是否在 🔴 强扰动日列表
   ↓
├─ 是 → 写卡时强制加入"不做清单",建议降仓
└─ 否 → 正常写卡流程
   ↓
若发现新事件 → 建议用户更新日历文件
```

---

## 情绪日历加载流程

<a id="sentiment-calendar"></a>

```
周日晚 20:00 / 工作日早 8:30
   ↓
Claude 主动触发 a-share-catalyst (OST)
   ↓
扫描 1: 下周海外事件库(COMPUTEX/Apple/Tesla 财报等)
扫描 2: 美股龙头隔夜表现(NVIDIA/Apple/Tesla/Marvell 等)
   ↓
判定信号强度 🔴 强 / 🟡 中 / 🟢 弱
   ↓
├─ 🔴 强 → 立即生成模式D 事件驱动交易卡
├─ 🟡 中 → 输出观察清单
└─ 🟢 弱 → 仅记录,不操作
   ↓
若有强信号,自动写入 sentiment-calendar-YYYY-MM.md 当日扰动条目
```

---

## 海外催化扫描流程

<a id="oversea-catalyst"></a>

```
用户说"更新催化" / 或周日晚自动触发
   ↓
Claude 调用 a-share-catalyst (OST)
   ↓
并行抓: 下周海外事件库 + 美股龙头隔夜表现
   ↓
判定信号强度,识别 🔴 强信号
   ↓
按完整结构(10 部分)生成 markdown
   ↓
覆盖 {{WORKSPACE_ANALYSIS}}/oversea-catalyst-YYYY-WNN.md
   ↓
更新日志追加一行
   ↓
回报用户:文件路径 + 本次变化要点
```

---

## 消息真实性三层检验流程

<a id="news-authenticity"></a>

```
任何"利好/催化"消息进入对话
   ↓
[第一层] 标注双日期: 报道日期 vs 事件首发日期
   ↓
首发日期 > 7 天 ?
├─ 否 → 正常处理
└─ 是 → [第二层] 跨源搜索确认是否旧闻翻炒
            ↓
       是旧闻翻炒 → [第三层] 检查 5 个出货信号
            ├─ 0-1 信号 → ⚠️ 谨慎,不追
            └─ 2+ 信号 → 🚨 出货警报,严禁追入,持仓考虑减仓
```
