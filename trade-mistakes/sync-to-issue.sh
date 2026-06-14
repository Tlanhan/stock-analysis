#!/usr/bin/env bash
# sync-to-issue.sh - 把本地交易错误 md 推送为 GitHub issue
#
# 用法:
#   ./sync-to-issue.sh 2026-06-02-COMPUTEX错过.md
#   ./sync-to-issue.sh 2026-06-02-COMPUTEX错过.md --dry-run    # 仅打印不创建
#
# 行为:
#   1. 解析本地 md 的"基本信息"表格,提取标题/严重度/错误类型/代价
#   2. 整篇 md 作为 issue body 推送
#   3. 自动打标签: trade-mistake + severity-* + Ex
#   4. 成功后把 issue URL 写回本地 md 顶部 frontmatter
#   5. 在 INDEX.md 对应行追加 issue 号
#
# 依赖: gh CLI(已登录 Tlanhan/stock-skill)
# 仓库: PRIVATE — 不脱敏,直接推
#
# 退出码: 0=成功, 1=参数错, 2=文件不存在, 3=解析失败, 4=gh 创建失败

set -euo pipefail

REPO="Tlanhan/stock-journal"
MISTAKES_DIR="G:/github/stock分析/trade-mistakes"
DRY_RUN=0

# ===== 参数解析 =====
if [ $# -lt 1 ]; then
  echo "用法: $0 <md-filename> [--dry-run]" >&2
  echo "例: $0 2026-06-02-COMPUTEX错过.md" >&2
  exit 1
fi

MD_FILE="$1"
shift || true

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
  shift
done

# 允许传入纯文件名或带路径
if [ -f "$MD_FILE" ]; then
  MD_PATH="$MD_FILE"
elif [ -f "$MISTAKES_DIR/$MD_FILE" ]; then
  MD_PATH="$MISTAKES_DIR/$MD_FILE"
else
  echo "❌ 文件不存在: $MD_FILE" >&2
  echo "   尝试过: $MISTAKES_DIR/$MD_FILE" >&2
  exit 2
fi

MD_BASENAME=$(basename "$MD_PATH")
echo "📖 解析文件: $MD_BASENAME"

# ===== 解析关键字段(从"基本信息"表格抽取) =====
# 表格行格式: | **字段** | 内容 |
extract_field() {
  local key="$1"
  grep -E "^\| \*\*$key\*\*" "$MD_PATH" | head -1 | awk -F'|' '{print $3}' | sed 's/^ *//; s/ *$//'
}

OCCURRED_DATE=$(extract_field "发生日期" || echo "")
SYMBOL=$(extract_field "标的" || echo "")
DIRECTION=$(extract_field "方向" || echo "")
ERROR_TYPE=$(extract_field "错误类型" || echo "")
SEVERITY=$(extract_field "严重度" || echo "")
COST=$(extract_field "代价" || echo "")

# 从文件名抽简述: YYYY-MM-DD-简述.md → 简述
SHORT_NAME=$(echo "$MD_BASENAME" | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}-//; s/\.md$//')

if [ -z "$OCCURRED_DATE" ] || [ -z "$ERROR_TYPE" ] || [ -z "$SEVERITY" ]; then
  echo "❌ 解析失败: 缺少必要字段" >&2
  echo "   发生日期: '$OCCURRED_DATE'" >&2
  echo "   错误类型: '$ERROR_TYPE'" >&2
  echo "   严重度: '$SEVERITY'" >&2
  echo "   请确认 md 顶部有完整的'基本信息'表格" >&2
  exit 3
fi

# ===== 推导 labels =====
LABELS=("trade-mistake")

# 严重度 → label
case "$SEVERITY" in
  *重*|*🔴*) LABELS+=("severity-high") ;;
  *中*|*🟡*) LABELS+=("severity-medium") ;;
  *轻*|*🟢*) LABELS+=("severity-low") ;;
esac

# 错误类型 → label(支持 E2+E4 复合)
# ERROR_TYPE 形如 "**E5** 错过机会" 或 "E2+E4"
ETYPES=$(echo "$ERROR_TYPE" | grep -oE 'E[1-7]' | sort -u)
declare -A ETYPE_NAMES=(
  [E1]="E1-追涨杀跌"
  [E2]="E2-止损不严"
  [E3]="E3-情绪化开仓"
  [E4]="E4-规则外仓位"
  [E5]="E5-错过机会"
  [E6]="E6-提前出场"
  [E7]="E7-加错仓"
)
for et in $ETYPES; do
  if [ -n "${ETYPE_NAMES[$et]:-}" ]; then
    LABELS+=("${ETYPE_NAMES[$et]}")
  fi
done

# ===== 构造 title 与 body =====
TITLE="[错误] $OCCURRED_DATE $SHORT_NAME"

# body = 整篇 md + footer
BODY_FILE=$(mktemp)
trap "rm -f $BODY_FILE" EXIT

{
  cat "$MD_PATH"
  echo ""
  echo "---"
  echo ""
  echo "> 🤖 本 issue 由 \`trade-mistakes/sync-to-issue.sh\` 自动同步"
  echo "> 来源文件: \`G:/github/stock分析/trade-mistakes/$MD_BASENAME\`"
  echo "> 同步时间: $(date '+%Y-%m-%d %H:%M:%S')"
} > "$BODY_FILE"

# ===== 打印摘要 =====
echo ""
echo "=== 准备创建 Issue ==="
echo "仓库: $REPO"
echo "标题: $TITLE"
echo "标签: ${LABELS[*]}"
echo "标的: $SYMBOL"
echo "方向: $DIRECTION"
echo "代价: $COST"
echo "正文长度: $(wc -c < "$BODY_FILE") bytes"
echo ""

if [ "$DRY_RUN" = "1" ]; then
  echo "🔍 DRY-RUN 模式,不实际创建"
  echo "--- BODY 预览(前 30 行) ---"
  head -30 "$BODY_FILE"
  exit 0
fi

# ===== 调用 gh issue create =====
LABEL_ARGS=""
for l in "${LABELS[@]}"; do
  LABEL_ARGS="$LABEL_ARGS --label \"$l\""
done

echo "🚀 创建中..."
ISSUE_URL=$(eval gh issue create \
  --repo "$REPO" \
  --title \"\$TITLE\" \
  --body-file \"\$BODY_FILE\" \
  $LABEL_ARGS) || {
  echo "❌ gh issue create 失败" >&2
  exit 4
}

ISSUE_NUMBER=$(echo "$ISSUE_URL" | grep -oE '[0-9]+$')

echo ""
echo "✅ Issue #$ISSUE_NUMBER 创建成功"
echo "   URL: $ISSUE_URL"

# ===== 回写 issue 号到本地 md(在文件顶部追加 frontmatter) =====
TMP_MD=$(mktemp)
{
  echo "<!-- github-issue: #$ISSUE_NUMBER -->"
  echo "<!-- github-url: $ISSUE_URL -->"
  echo "<!-- synced-at: $(date '+%Y-%m-%d %H:%M:%S') -->"
  echo ""
  # 如果原文件已经有 github-issue 标记,先剥掉
  sed -E '/^<!-- github-(issue|url)/d; /^<!-- synced-at/d' "$MD_PATH"
} > "$TMP_MD"
mv "$TMP_MD" "$MD_PATH"
echo "✅ 已回写 issue 号到 $MD_BASENAME 顶部"

# ===== 在 INDEX.md 追加 issue 号(如果还没追加过) =====
INDEX_PATH="$MISTAKES_DIR/INDEX.md"
if [ -f "$INDEX_PATH" ]; then
  if ! grep -q "#$ISSUE_NUMBER" "$INDEX_PATH"; then
    echo "ℹ️  请手动在 INDEX.md 对应行末追加: [#$ISSUE_NUMBER]($ISSUE_URL)"
    echo "   (自动追加暂未实现,避免破坏表格格式)"
  fi
fi

echo ""
echo "🎯 完成。可在 GitHub 查看: $ISSUE_URL"
