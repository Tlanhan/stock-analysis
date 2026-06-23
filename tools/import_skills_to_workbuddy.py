"""将 ~/.agents/skills/ 中的金融相关 skill 复制到 ~/.workbuddy/skills/。
采用复制方案（符号链接/junction 在 WorkBuddy 沙箱下被拦截）。
支持重复运行：已存在的目录会合并覆盖（dirs_exist_ok=True）。
"""
import shutil
import sys
from pathlib import Path

AGENTS_SKILLS = Path(r"C:\Users\linguowei\.agents\skills")
WORKBUDDY_SKILLS = Path(r"C:\Users\linguowei\.workbuddy\skills")

# 排除清单（误判 / DEPRECATED / 重复）
EXCLUDE = {
    "lark-okr",
    "financial-report-reader",
    "industry-research-report",
    "risk-sentinel",
    "senior-financial-advisor",
    "technical-analysis",
    "backtest-expert-0.1.0",
}

# 待导入的 51 个金融相关 skill
TO_IMPORT = [
    "a-share-analysis", "a-share-catalyst", "a-share-daily-review",
    "a-share-etf-selector", "a-share-intraday-review", "a-share-portfolio",
    "a-share-sentiment-calendar", "a-share-technical-analysis",
    "a-share-trading", "a-share-trigger-check",
    "a-stock-analysis-1.0.0", "a-stock-news-glmmcp",
    "agent-reviewer", "backtest-expert", "baostock",
    "bond-fixed-income-analysis",
    "business-decomposition-order-quality", "business-reality-check",
    "canslim-screener", "china-stock-analyst",
    "china-stock-research-orchestrator",
    "commodity-analysis", "commodity-research-outlook",
    "data-integrity-protocol", "data-verifier",
    "derivatives-options-analysis",
    "equity-earnings-review", "equity-researcher",
    "event-driven-ma", "event-etf-study",
    "finance-html-report", "financial-health",
    "fund-etf-analyzer", "industry-deep-report",
    "investment-html-report", "ipo-analysis",
    "kimi-datasource", "macro-analysis",
    "portfolio-manager", "position-sizer",
    "quant-risk-management", "quantitative-backtest",
    "sector-deep-research", "stock-deep-analysis",
    "stock-finance-profiler", "stock-research-report-cn",
    "technical-analyst", "trading-strategy-backtest",
    "valuation-investment-strategy", "valuation-modeling",
    "vcp-screener",
]


def main():
    assert len(TO_IMPORT) == 51, f"预期 51 个，实际 {len(TO_IMPORT)}"
    WORKBUDDY_SKILLS.mkdir(parents=True, exist_ok=True)

    success = []
    skipped_missing = []
    failed = []

    for name in TO_IMPORT:
        src = AGENTS_SKILLS / name
        dst = WORKBUDDY_SKILLS / name

        if not src.exists():
            print(f"[缺失] 源不存在: {src}")
            skipped_missing.append(name)
            continue

        try:
            # dirs_exist_ok=True 允许合并复制（重复运行时覆盖旧文件）
            # 如果 dst 是符号链接（之前可能残留），先删除
            if dst.is_symlink():
                dst.unlink()
            shutil.copytree(src, dst, dirs_exist_ok=True)
            # 验证 SKILL.md 存在
            skill_md = dst / "SKILL.md"
            if skill_md.exists():
                print(f"[成功] {name}")
                success.append(name)
            else:
                print(f"[警告] {name} 复制完成但 SKILL.md 不存在")
                failed.append((name, "SKILL.md missing after copy"))
        except Exception as e:
            print(f"[失败] {name}: {e}")
            failed.append((name, str(e)))

    print()
    print("=" * 70)
    print(f"汇总：成功 {len(success)} | 缺失 {len(skipped_missing)} | 失败 {len(failed)}")
    if failed:
        print("失败清单：")
        for n, err in failed:
            print(f"  - {n}: {err}")


if __name__ == "__main__":
    main()
