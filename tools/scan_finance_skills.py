"""扫描 ~/.agents/skills/ 下所有 SKILL.md，解析 frontmatter，
筛选出金融相关 skill（重点 a- 前缀和含 stock 的）。"""
import os
import re
from pathlib import Path

AGENTS_SKILLS = Path(r"C:\Users\linguowei\.agents\skills")

# 金融关键词（中英文）
FINANCE_KEYWORDS = [
    # 中文
    "A股", "a股", "股票", "投资", "交易", "金融", "行情", "复盘", "投顾",
    "持仓", "仓位", "止损", "止盈", "板块", "龙虎榜", "北向资金", "融资融券",
    "港股", "美股", "日股", "可转债", "债券", "基金", "ETF", "期货", "期权",
    "衍生品", "大宗商品", "宏观", "央行", "FOMC", "美联储", "BOJ", "财报",
    "估值", "基本面", "技术面", "K线", "量价", "回测", "量化", "策略",
    "大盘", "牛市", "熊市", "牛熊", "市盈率", "ROE", "CFA",
    # 英文
    "stock", "equity", "trade", "trading", "portfolio", "backtest",
    "finance", "financial", "bond", "etf", "option", "derivative",
    "commodity", "macro", "fed", "central bank", "earnings",
    "valuation", "canslim", "quant",
]

# 目录名关键词（直接命中即算金融相关）
DIRNAME_KEYWORDS = [
    "a-share", "a-stock", "stock", "trade", "trading", "finance",
    "financial", "bond", "etf", "backtest", "quant", "portfolio",
    "commodity", "derivatives", "option", "macro",
    "china-stock", "business-decomposition", "business-reality",
    "event-driven-ma", "canslim",
]


def parse_frontmatter(content: str):
    """解析 SKILL.md 的 YAML frontmatter，返回 name 和 description。"""
    if not content.startswith("---"):
        return None, None
    # 找到第二个 ---
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return None, None
    fm = m.group(1)
    name = None
    desc = None
    # name: 单行
    nm = re.search(r"^name:\s*(.+?)\s*$", fm, re.MULTILINE)
    if nm:
        name = nm.group(1).strip().strip('"').strip("'")
    # description: 可能是单行或 > 折叠多行
    dm = re.search(r"^description:\s*(.+(?:\n(?!\w+:).*)*)", fm, re.MULTILINE)
    if dm:
        raw = dm.group(1)
        # 去掉 > 和换行，合并成一行
        desc = re.sub(r"\s+", " ", raw.replace(">", " ")).strip()
    return name, desc


def is_finance_related(dirname: str, name: str, desc: str) -> tuple[bool, str]:
    """判断是否金融相关，返回 (是否相关, 命中原因)。"""
    dl = dirname.lower()
    # 1. 目录名直接命中
    for kw in DIRNAME_KEYWORDS:
        if kw in dl:
            return True, f"目录名命中 '{kw}'"
    # 2. description 命中关键词
    if desc:
        dl_desc = desc.lower()
        for kw in FINANCE_KEYWORDS:
            kwl = kw.lower()
            if kwl in dl_desc:
                return True, f"描述命中 '{kw}'"
    # 3. name 命中
    if name:
        nl = name.lower()
        for kw in DIRNAME_KEYWORDS:
            if kw in nl:
                return True, f"name命中 '{kw}'"
    return False, ""


def main():
    if not AGENTS_SKILLS.exists():
        print(f"目录不存在: {AGENTS_SKILLS}")
        return

    all_skills = []
    finance_skills = []

    for entry in sorted(AGENTS_SKILLS.iterdir()):
        if not entry.is_dir():
            continue
        # 跳过符号链接（如 aegis -> .codex/aegis/skills）
        if entry.is_symlink():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            content = skill_md.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  读取失败 {entry.name}: {e}")
            continue
        name, desc = parse_frontmatter(content)
        all_skills.append(entry.name)
        related, reason = is_finance_related(entry.name, name or "", desc or "")
        if related:
            finance_skills.append((entry.name, name or "", reason, desc or ""))

    print(f"=== 扫描完成 ===")
    print(f"总 skill 数: {len(all_skills)}")
    print(f"金融相关 skill 数: {len(finance_skills)}")
    print()
    print("=" * 80)
    print("金融相关 skill 清单（按目录名排序）:")
    print("=" * 80)
    for dirname, name, reason, desc in finance_skills:
        print(f"\n📁 {dirname}")
        print(f"   name: {name}")
        print(f"   命中: {reason}")
        # description 截断到 150 字符
        d = desc[:150] + ("..." if len(desc) > 150 else "")
        print(f"   desc: {d}")

    # 输出目录名列表，方便后续建链接
    print()
    print("=" * 80)
    print("待导入目录名清单（复制用）:")
    print("=" * 80)
    for dirname, _, _, _ in finance_skills:
        print(dirname)


if __name__ == "__main__":
    main()
