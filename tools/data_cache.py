#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
data_cache.py — 数据缓存与健康检查
===================================
每日收盘后缓存关键数据到本地 JSON，防止 API 挂掉时无数据可用。
同时检查各数据源可用性，提前告警。

用法：
  python tools/data_cache.py save          # 保存今日数据到缓存
  python tools/data_cache.py load          # 加载最近缓存
  python tools/data_cache.py health        # 数据源健康检查
  python tools/data_cache.py health --all  # 检查所有数据源

缓存位置：tools/cache/YYYY-MM-DD.json
创建：2026-06-24
"""

import sys
import os
import json
import io
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ========================= 配置 =========================

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')

# 关键标的（核心监控 + 主要指数）
KEY_CODES = [
    'sh000001',  # 上证指数
    'sz399001',  # 深证成指
    'sz399006',  # 创业板指
    'sh000688',  # 科创50
    'sh000300',  # 沪深300
    'sh000905',  # 中证500
    '159558',    # 半导体设备ETF
    '588000',    # 科创50ETF
    '515880',    # 通信ETF
    '515260',    # 电子ETF
    '512400',    # 有色金属ETF
]

# 数据源配置
DATA_SOURCES = {
    'qt_quote': {
        'name': '腾讯实时行情',
        'url': 'https://qt.gtimg.cn/q=sh000001',
        'check': lambda resp: 'sh000001' in resp,
    },
    'em_sector': {
        'name': '东财板块数据',
        'url': 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f2,f3,f14',
        'check': lambda resp: '"data"' in resp,
    },
    'kline': {
        'name': '腾讯K线API',
        'url': 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000001,day,,5,qfq',
        'check': lambda resp: '"data"' in resp,
    },
}


# ========================= 缓存操作 =========================

def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(date_str: str = None) -> str:
    if not date_str:
        bj = timezone(timedelta(hours=8))
        date_str = datetime.now(bj).strftime('%Y-%m-%d')
    return os.path.join(CACHE_DIR, f'{date_str}.json')


def save_cache(data: dict, date_str: str = None):
    """保存数据到缓存"""
    _ensure_cache_dir()
    path = _cache_path(date_str)
    data['_cached_at'] = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, ensure_ascii=False, indent=2, fp=f)
    print(f'✅ 已缓存到 {path}')


def load_cache(date_str: str = None) -> dict:
    """加载缓存数据，优先指定日期，否则取最近的"""
    if date_str:
        path = _cache_path(date_str)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    # 取最近的缓存
    if not os.path.exists(CACHE_DIR):
        return {}
    files = sorted([f for f in os.listdir(CACHE_DIR) if f.endswith('.json')], reverse=True)
    if not files:
        return {}
    with open(os.path.join(CACHE_DIR, files[0]), 'r', encoding='utf-8') as f:
        return json.load(f)


# ========================= 数据采集 =========================

def _fetch_quote_batch(codes: list) -> dict:
    """批量获取实时行情（复用 qt_quote 的逻辑）"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from qt_quote import quote_many
    return quote_many(codes)


def save_daily_snapshot():
    """保存今日收盘数据快照"""
    bj = timezone(timedelta(hours=8))
    now = datetime.now(bj)
    date_str = now.strftime('%Y-%m-%d')

    print(f'📊 正在保存 {date_str} 数据快照...')

    # 1. 实时行情
    print('  → 拉取实时行情...')
    quotes = _fetch_quote_batch(KEY_CODES)

    # 2. 组装缓存数据
    snapshot = {
        'date': date_str,
        'beijing_time': now.strftime('%H:%M:%S'),
        'quotes': quotes,
        'key_indices': {},
        'key_etfs': {},
    }

    # 分类
    for code, data in quotes.items():
        if code.startswith(('sh000', 'sz399')):
            snapshot['key_indices'][code] = data
        else:
            snapshot['key_etfs'][code] = data

    save_cache(snapshot, date_str)
    return snapshot


# ========================= 健康检查 =========================

def health_check(check_all: bool = False) -> dict:
    """检查各数据源可用性"""
    bj = timezone(timedelta(hours=8))
    now = datetime.now(bj)
    print(f'🏥 数据源健康检查 — {now.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*60}')

    results = {}
    sources = DATA_SOURCES if check_all else {'qt_quote': DATA_SOURCES['qt_quote']}

    for key, cfg in sources.items():
        status = '✅'
        detail = ''
        try:
            req = urllib.request.Request(cfg['url'], headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://gu.qq.com/',
            })
            resp = urllib.request.urlopen(req, timeout=8).read().decode('utf-8', errors='ignore')
            if cfg['check'](resp):
                detail = f'正常 ({len(resp)} bytes)'
            else:
                status = '⚠️'
                detail = f'返回格式异常 ({len(resp)} bytes)'
        except Exception as e:
            status = '❌'
            detail = str(e)[:60]

        results[key] = {'status': status, 'detail': detail}
        print(f'  {status} {cfg["name"]:<16} {detail}')

    # 汇总
    ok = sum(1 for r in results.values() if r['status'] == '✅')
    total = len(results)
    print(f'\n{"="*60}')
    if ok == total:
        print(f'🟢 全部正常 ({ok}/{total})')
    elif ok > 0:
        print(f'🟡 部分可用 ({ok}/{total})，建议用 MCP/WebSearch 兜底')
    else:
        print(f'🔴 全部不可用 ({ok}/{total})，使用本地缓存兜底')

    return results


# ========================= CLI =========================

def main():
    if len(sys.argv) < 2:
        print('用法: python data_cache.py [save|load|health]')
        print('  save          保存今日数据快照')
        print('  load          加载最近缓存')
        print('  health        腾讯API健康检查')
        print('  health --all  检查所有数据源')
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'save':
        save_daily_snapshot()
    elif cmd == 'load':
        data = load_cache()
        if data:
            print(f'📅 缓存日期: {data.get("date", "未知")}')
            print(f'⏰ 缓存时间: {data.get("_cached_at", "未知")}')
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        else:
            print('❌ 无缓存数据')
    elif cmd == 'health':
        check_all = '--all' in sys.argv
        health_check(check_all)
    else:
        print(f'未知命令: {cmd}')
        sys.exit(1)


if __name__ == '__main__':
    main()
