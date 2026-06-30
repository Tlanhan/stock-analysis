#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
watchlist_scanner.py — Watchlist 批量信号扫描器
==============================================
每日收盘后运行，扫描 watchlist 中所有标的的技术信号，
输出"回踩5日线"/"突破前高"/"缩量到地量"等信号标记。

用法：
  python tools/watchlist_scanner.py                          # 扫描默认 watchlist
  python tools/watchlist_scanner.py --file watchlist.txt     # 指定文件
  python tools/watchlist_scanner.py --tier core              # 只扫核心监控
  python tools/watchlist_scanner.py --json                   # JSON 输出

输出：
  表格形式，每行一个标的，标注信号类型和优先级。

依赖：
  - qt_quote.py（同目录）
  - 需要能访问腾讯 K 线 API（web.ifzq.gtimg.cn）

创建：2026-06-24
"""

import sys
import os
import argparse
import json
from datetime import datetime, timezone, timedelta

# 确保能 import 同目录的 qt_quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qt_quote import quote_many

# ========================= 配置 =========================

# 信号阈值
MA5_DEVIATION_CLOSE = 1.5    # 距5日线乖离 < 1.5% = "回踩5日线附近"
MA5_DEVIATION_OVERBOUGHT = 5.0  # 乖离 > 5% = "超买警告"
VOLUME_RATIO_LOW = 0.5       # 量比 < 0.5 = "缩量"
VOLUME_RATIO_HIGH = 2.0      # 量比 > 2.0 = "放量"

# 默认 watchlist 路径
DEFAULT_WATCHLIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..', 'watchlist.txt'
)

# ========================= K 线取数 =========================

def _fetch_kline(code: str, days: int = 20) -> list:
    """从腾讯 K 线 API 取最近 N 天日K。返回 [{date, open, close, high, low, volume}, ...]"""
    import urllib.request
    # 推断市场前缀
    if code.startswith(('sh', 'sz')):
        secid = code
    elif code.startswith(('5', '6')):
        secid = f'sh{code}'
    else:
        secid = f'sz{code}'

    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={secid},day,,{days},qfq'
    try:
        req = urllib.request.Request(url, headers={
            'Referer': 'https://gu.qq.com/',
            'User-Agent': 'Mozilla/5.0'
        })
        resp = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        data = json.loads(resp)
        # 提取 K 线数据
        kdata = data.get('data', {}).get(secid, {})
        lines = kdata.get('day', []) or kdata.get('qfqday', [])
        result = []
        for line in lines:
            if len(line) >= 6:
                result.append({
                    'date': line[0],
                    'open': float(line[1]),
                    'close': float(line[2]),
                    'high': float(line[3]),
                    'low': float(line[4]),
                    'volume': float(line[5]),
                })
        return result
    except Exception as e:
        return []


def _calc_ma5(klines: list) -> float:
    """计算最近5天收盘价均值"""
    if len(klines) < 5:
        return 0
    return sum(k['close'] for k in klines[-5:]) / 5


def _calc_volume_ratio(klines: list) -> float:
    """计算今日量 / 5日均量"""
    if len(klines) < 6:
        return 1.0
    today_vol = klines[-1]['volume']
    avg_vol = sum(k['volume'] for k in klines[-6:-1]) / 5
    return today_vol / avg_vol if avg_vol > 0 else 1.0


def _find_recent_high(klines: list, lookback: int = 20) -> float:
    """取近 N 天最高价"""
    if not klines:
        return 0
    return max(k['high'] for k in klines[-lookback:])


def _find_recent_low(klines: list, lookback: int = 20) -> float:
    """取近 N 天最低价"""
    if not klines:
        return 0
    return min(k['low'] for k in klines[-lookback:])


# ========================= 信号检测 =========================

def detect_signals(code: str, name: str, klines: list) -> dict:
    """分析单个标的的技术信号"""
    if not klines or len(klines) < 5:
        return {'code': code, 'name': name, 'signals': ['数据不足'], 'priority': '—'}

    close = klines[-1]['close']
    ma5 = _calc_ma5(klines)
    vol_ratio = _calc_volume_ratio(klines)
    recent_high = _find_recent_high(klines)
    recent_low = _find_recent_low(klines)

    signals = []
    priority = '🟢'

    # 1. 回踩5日线
    if ma5 > 0:
        deviation = (close - ma5) / ma5 * 100
        if -MA5_DEVIATION_CLOSE <= deviation <= MA5_DEVIATION_CLOSE:
            signals.append(f'回踩5日线({deviation:+.1f}%)')
            priority = '🟡'
        elif deviation > MA5_DEVIATION_OVERBOUGHT:
            signals.append(f'超买({deviation:+.1f}%)')
            priority = '🔴'
        elif deviation < -MA5_DEVIATION_OVERBOUGHT:
            signals.append(f'超卖({deviation:+.1f}%)')
            priority = '🟡'

    # 2. 突破前高
    if close >= recent_high * 0.99:
        signals.append(f'突破{lookback}日前高({recent_high:.3f})')
        priority = '🔴'

    # 3. 缩量
    if vol_ratio < VOLUME_RATIO_LOW:
        signals.append(f'缩量(量比{vol_ratio:.2f})')
        if priority == '🟢':
            priority = '🟡'

    # 4. 放量
    if vol_ratio > VOLUME_RATIO_HIGH:
        signals.append(f'放量(量比{vol_ratio:.2f})')

    # 5. 接近前低（潜在低吸位）
    if close <= recent_low * 1.02:
        signals.append(f'接近前低({recent_low:.3f})')
        if priority == '🟢':
            priority = '🟡'

    if not signals:
        signals.append('无明显信号')

    return {
        'code': code,
        'name': name,
        'close': close,
        'ma5': round(ma5, 3) if ma5 else 0,
        'vol_ratio': round(vol_ratio, 2),
        'signals': signals,
        'priority': priority,
    }


# ========================= 主流程 =========================

def parse_watchlist(filepath: str) -> list:
    """解析 watchlist 文件，返回 [(code, name), ...]"""
    result = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('#')
            code = parts[0].strip()
            name = parts[1].strip() if len(parts) > 1 else code
            if code:
                result.append((code, name))
    return result


def main():
    parser = argparse.ArgumentParser(description='Watchlist 信号扫描器')
    parser.add_argument('--file', '-f', default=DEFAULT_WATCHLIST, help='Watchlist 文件路径')
    parser.add_argument('--json', '-j', action='store_true', help='JSON 输出')
    parser.add_argument('--top', '-t', type=int, default=20, help='只显示前 N 个有信号的标的')
    args = parser.parse_args()

    # 北京时间校准
    bj = timezone(timedelta(hours=8))
    now = datetime.now(bj)
    print(f'⏰ 扫描时间：{now.strftime("%Y-%m-%d %H:%M:%S")} 北京时间')

    # 解析 watchlist
    watchlist = parse_watchlist(args.file)
    print(f'📋 共 {len(watchlist)} 个标的')

    # 批量取行情（用 qt_quote 的 quote_many）
    codes = [w[0] for w in watchlist]
    quotes = quote_many(codes)

    # 逐个分析信号
    results = []
    for code, name in watchlist:
        klines = _fetch_kline(code)
        sig = detect_signals(code, name, klines)
        # 合并实时行情
        if code in quotes:
            sig['realtime'] = quotes[code]
        results.append(sig)

    # 按优先级排序：🔴 > 🟡 > 🟢
    priority_order = {'🔴': 0, '🟡': 1, '🟢': 2, '—': 3}
    results.sort(key=lambda x: priority_order.get(x['priority'], 3))

    # 输出
    if args.json:
        print(json.dumps(results[:args.top], ensure_ascii=False, indent=2))
    else:
        print(f'\n{"="*80}')
        print(f'{"代码":<10} {"名称":<18} {"收盘":<8} {"MA5":<8} {"量比":<6} {"信号":<30} {"级别"}')
        print(f'{"="*80}')
        for r in results[:args.top]:
            signals_str = ' | '.join(r['signals'])
            print(f'{r["code"]:<10} {r["name"]:<18} {r.get("close","—"):<8} {r.get("ma5","—"):<8} '
                  f'{r.get("vol_ratio","—"):<6} {signals_str:<30} {r["priority"]}')

    # 摘要
    red = sum(1 for r in results if r['priority'] == '🔴')
    yellow = sum(1 for r in results if r['priority'] == '🟡')
    print(f'\n📊 信号摘要：🔴 强信号 {red} 个 | 🟡 关注 {yellow} 个 | 其余无明显信号')


if __name__ == '__main__':
    main()
