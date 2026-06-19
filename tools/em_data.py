# -*- coding: utf-8 -*-
"""
em_data.py — 东方财富数据工具（整合版）

整合自 em_probe/em_probe2/em_probe3/em_final/em_v5/em_v6/em_trends 等临时脚本。
提供复盘所需的、腾讯API不覆盖的数据：板块涨跌/资金流向/融资融券/板块历史K线。

用法:
    # 当日板块涨幅TOP（概念+行业）
    python tools/em_data.py sector

    # 板块历史K线周涨幅（校验本周主线）
    python tools/em_data.py sector-kline

    # 融资融券全市场汇总（分页聚合）
    python tools/em_data.py margin

    # 个股/指数分时收盘（腾讯缓存时用这个交叉验证）
    python tools/em_data.py trends 1.000001 0.399006 0.159558

    # 全部（一键体检）
    python tools/em_data.py all

数据源:
    - 板块涨跌/资金: push2.eastmoney.com/api/qt/clist/get
    - 板块历史K线:    push2his.eastmoney.com/api/qt/stock/kline/get
    - 融资融券:        datacenter-web.eastmoney.com/api/data/v1/get (RPTA_WEB_RZRQ_GGMX)
    - 分时收盘:        push2his.eastmoney.com/api/qt/stock/trends2/get

注意:
    - 北向资金净额已数据真空（港交所2024/8取消实时披露），本工具不提供
    - push2ex涨停池接口(rc=102)参数失效，涨停家数暂不可API获取，用akshare补
    - 腾讯API对ETF(51/56/588开头)盘中可能返回空，用本工具trends交叉验证
"""
import sys
import json
import time
import urllib.request
from collections import defaultdict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "http://data.eastmoney.com/",
}


def fetch(url, timeout=15):
    """通用JSON请求"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ============================================================
# 1. 板块涨跌幅排行（概念 + 行业）
# ============================================================
def get_sector_rank(market="90", sec_type="3", top=15):
    """
    market: 90=板块
    sec_type: 3=概念板块, 2=行业板块
    """
    url = (
        f"http://push2.eastmoney.com/api/qt/clist/get?"
        f"pn=1&pz={top}&po=1&np=1&fltt=2&invt=2&fid=f3&"
        f"fs=m:{market}+t:{sec_type}&fields=f2,f3,f4,f62,f12,f14"
    )
    d = fetch(url)
    diff = d.get("data", {}).get("diff", {})
    items = list(diff.values()) if isinstance(diff, dict) else (diff or [])
    return items


def cmd_sector():
    print("=" * 60)
    print("【板块涨幅排行】概念板块 TOP15（按涨幅降序）")
    print("=" * 60)
    items = get_sector_rank("90", "3", 15)
    print(f"{'排名':>4} {'板块':<16} {'涨幅':>8} {'主力净流入(亿)':>14} {'代码':<10}")
    for i, it in enumerate(items, 1):
        name = it.get("f14", "?")
        chg = it.get("f3", 0)
        flow = (it.get("f62", 0) or 0) / 1e8
        code = it.get("f12", "?")
        print(f"{i:>4} {name:<16} {chg:>+7.2f}% {flow:>14.1f} {code:<10}")

    print()
    print("=" * 60)
    print("【板块涨幅排行】行业板块 TOP15")
    print("=" * 60)
    items = get_sector_rank("90", "2", 15)
    for i, it in enumerate(items, 1):
        name = it.get("f14", "?")
        chg = it.get("f3", 0)
        flow = (it.get("f62", 0) or 0) / 1e8
        code = it.get("f12", "?")
        print(f"{i:>4} {name:<16} {chg:>+7.2f}% {flow:>14.1f} {code:<10}")


# ============================================================
# 2. 板块历史K线（周涨幅验证）
# ============================================================
SECTOR_CODES = {
    "稀土": "90.BK1626",
    "钨": "90.BK1625",
    "半导体": "90.BK1036",
    "集成电路制造": "90.BK1329",
    "CPO概念": "90.BK1128",
    "PCB": "90.BK0474",
    "消费电子": "90.BK1035",
    "光伏设备": "90.BK1333",
    "医疗器械": "90.BK1039",
    "电池": "90.BK1031",
}


def get_sector_kline(secid, beg="20260610", end="20260630"):
    """拉板块日K线"""
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
        f"secid={secid}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56&"
        f"klt=101&fqt=1&beg={beg}&end={end}"
    )
    d = fetch(url)
    kls = d.get("data", {}).get("klines", [])
    name = d.get("data", {}).get("name", "?")
    return name, kls


def cmd_sector_kline():
    print("=" * 60)
    print("【板块历史K线】本周（6/13收 → 6/18收）周涨幅验证")
    print("=" * 60)
    print(f"{'板块':<12} {'周涨幅':>8} {'6/15开':>10} {'6/18收':>10}")
    for name, secid in SECTOR_CODES.items():
        try:
            nm, kls = get_sector_kline(secid)
            if not kls:
                print(f"{name:<12} 无数据")
                continue
            rows = [r.split(",") for r in kls]
            wk = [r for r in rows if r[0] >= "2026-06-13"]
            if len(wk) >= 2:
                fo = float(wk[0][1])
                lc = float(wk[-1][2])
                chg = (lc - fo) / fo * 100
                print(f"{name:<12} {chg:>+7.2f}% {fo:>10.0f} {lc:>10.0f}")
            time.sleep(0.3)
        except Exception as e:
            print(f"{name:<12} ERR: {e}")


# ============================================================
# 3. 融资融券全市场汇总（分页聚合）
# ============================================================
def get_margin_summary(max_pages=12, min_date="2026-06-08"):
    """
    分页拉取个股融资融券明细，按日期聚合。
    返回 {date: {rzye, rqye, rzjme, n}}
    """
    agg = defaultdict(lambda: {"rzye": 0.0, "rqye": 0.0, "rzjme": 0.0, "n": 0})
    for page in range(1, max_pages + 1):
        url = (
            f"https://datacenter-web.eastmoney.com/api/data/v1/get?"
            f"sortColumns=DATE&sortTypes=-1&pageSize=500&pageNumber={page}&"
            f"reportName=RPTA_WEB_RZRQ_GGMX&columns=ALL&source=WEB&client=WEB"
        )
        try:
            d = fetch(url)
            data = d.get("result", {}).get("data", []) if d.get("result") else []
            if not data:
                break
            earliest = (data[-1].get("DATE") or "")[:10]
            for row in data:
                dt = (row.get("DATE") or "")[:10]
                if dt < min_date:
                    continue
                agg[dt]["rzye"] += row.get("RZYE", 0) or 0
                agg[dt]["rqye"] += row.get("RQYE", 0) or 0
                agg[dt]["rzjme"] += row.get("RZJME", 0) or 0
                agg[dt]["n"] += 1
            if earliest <= min_date:
                break
            time.sleep(0.3)
        except Exception as e:
            print(f"  page{page} ERR: {e}", file=sys.stderr)
            break
    return agg


def cmd_margin():
    print("=" * 60)
    print("【融资融券】全市场汇总（datacenter 分页聚合）")
    print("=" * 60)
    agg = get_margin_summary()
    print(f"{'日期':<12} {'融资余额(亿)':>12} {'融券余额(亿)':>12} {'融资净买(亿)':>12} {'样本数':>8}")
    for dt in sorted(agg.keys()):
        v = agg[dt]
        # 样本数 < 3000 说明分页不完整，标注
        warn = " ⚠️不完整" if v["n"] < 3000 else ""
        print(
            f"{dt:<12} {v['rzye']/1e8:>12.0f} {v['rqye']/1e8:>12.1f} "
            f"{v['rzjme']/1e8:>+12.1f} {v['n']:>8}{warn}"
        )
    print()
    print("注: 样本数<3000表示接口分页未拉全(全市场约4020只),该日数据不完整")


# ============================================================
# 4. 分时收盘（腾讯缓存时交叉验证）
# ============================================================
def get_trends(secid):
    """东财 trends2 分时数据，返回收盘信息"""
    url = (
        f"http://push2his.eastmoney.com/api/qt/stock/trends2/get?"
        f"secid={secid}&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&"
        f"fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&iscr=0&ndays=1"
    )
    d = fetch(url)
    data = d.get("data")
    if not data:
        return f"{secid}: NO DATA"
    name = data.get("name")
    pre = data.get("preClose")
    trends = data.get("trends", [])
    if not trends:
        return f"{secid} {name}: 无分时"
    last = trends[-1].split(",")
    last_close = float(last[2])
    chg = (last_close - pre) / pre * 100 if pre else 0
    high = max(float(t.split(",")[3]) for t in trends)
    low = min(float(t.split(",")[4]) for t in trends)
    return f"{secid} {name}: 收{last_close} ({chg:+.2f}%) 高{high} 低{low} 前收{pre}"


def cmd_trends(secids):
    print("=" * 60)
    print("【分时收盘】东财 trends2（腾讯缓存时交叉验证）")
    print("=" * 60)
    for secid in secids:
        try:
            print(get_trends(secid))
        except Exception as e:
            print(f"{secid}: ERR {e}")


# ============================================================
# 5. 一键体检
# ============================================================
def cmd_all():
    cmd_sector()
    print("\n")
    cmd_sector_kline()
    print("\n")
    cmd_margin()


USAGE = """\
em_data.py — 东方财富数据工具

用法:
    python tools/em_data.py sector        # 当日板块涨幅TOP(概念+行业)
    python tools/em_data.py sector-kline  # 板块本周K线周涨幅
    python tools/em_data.py margin        # 融资融券全市场汇总
    python tools/em_data.py trends 1.000001 0.399006 0.159558  # 分时收盘
    python tools/em_data.py all           # 全部(板块+K线+融资)

注意: 北向资金净额已数据真空(港交所2024/8取消实时披露)
"""


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "sector":
        cmd_sector()
    elif cmd == "sector-kline":
        cmd_sector_kline()
    elif cmd == "margin":
        cmd_margin()
    elif cmd == "trends":
        if len(sys.argv) < 3:
            print("用法: python tools/em_data.py trends 1.000001 0.399006 ...")
            sys.exit(1)
        cmd_trends(sys.argv[2:])
    elif cmd == "all":
        cmd_all()
    else:
        print(f"未知命令: {cmd}")
        print(USAGE)
        sys.exit(1)
