#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
qt_quote.py — 腾讯财经 qt.gtimg.cn 一手行情取数工具
===================================================
固化自 2026-06-16 实测验证。当前环境中最稳定的 A 股/指数行情源。

数据源对比（2026-06-16 实测）：
  - 腾讯 qt.gtimg.cn   ✅ 可用，无风控，批量快   ← 本工具
  - 东财 push2 实时报价 ❌ 502（sandbox 出口拦）
  - 东财 push2his 日K   ❌ rc:102（IP 风控）
  - 东财 push2his 分时  ✅ 可用（见 get_em_trends）
  - kimi-datasource MCP ❌ 本会话未挂载

用法：
  # 命令行：代码用逗号/空格分隔，sh/sz 前缀可省（自动推断）
  python tools/qt_quote.py 600183 002916 sh000001
  python tools/qt_quote.py 600183,002463
  python tools/qt_quote.py @watchlist.txt        # @文件，每行一个代码

  # 作为模块
  from qt_quote import quote, quote_many

输出：
  默认打印表格；--json 输出 JSON；--csv 输出 CSV

字段说明（腾讯经典协议 v_xxxxx="a~b~c..."）：
  p[1]名称 p[2]代码 p[3]现价 p[4]昨收 p[5]今开
  p[6]成交量(手) p[33]最高 p[34]最低 p[37]成交额(元) p[38]换手率
  p[43]市盈率(动) p[44]振幅 p[49]流通市值(元) p[45]总市值(元)  # 字段位置随源可能微调
"""
import sys, os, json, urllib.request, io

# Windows cmd 默认 GBK，强制 stdout UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# ----------------------------- 核心取数 -----------------------------

def _fetch(url, timeout=12):
    """带 Referer/UA 的请求。腾讯返回 GBK。"""
    req = urllib.request.Request(url, headers={
        'Referer': 'https://gu.qq.com/',
        'User-Agent': 'Mozilla/5.0'
    })
    return urllib.request.urlopen(req, timeout=timeout).read().decode('gbk', 'ignore')


def _normalize_code(code):
    """600183 -> sh600183, 002916 -> sz002916, 000001 -> sz000001(指数sh000001)。
    已带 sh/sz/hs 前缀的保留。指数需调用方显式带 sh/sz。"""
    code = code.strip().lower()
    if code.startswith(('sh', 'sz', 'hs', 'hk', 'us')):
        return code
    if not code.isdigit():
        return code
    if code.startswith('6'):
        return 'sh' + code
    return 'sz' + code


def quote(symbols, batch_size=40):
    """取一只或多只股票行情。symbols 为字符串或列表。
    自动分批请求（每批 batch_size 只），避免 URL 过长被拒。
    返回 list[dict]。失败的单只置 {'code':x, 'err':...}。"""
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.replace(',', ' ').split() if s.strip()]
    codes = [_normalize_code(s) for s in symbols]
    results = []
    # 分批请求合并
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        url = 'http://qt.gtimg.cn/q=' + ','.join(batch)
        try:
            raw = _fetch(url)
        except Exception as e:
            # 整批失败：逐只标记错误
            for c in batch:
                results.append({'code': c, 'err': 'fetch: ' + str(e)})
            continue
        for line in raw.split(';'):
            line = line.strip()
            if not line or '="' not in line:
                continue
            try:
                results.append(_parse_line(line))
            except Exception as e:
                # 兜底：提取 code
                sc = ''
                if '~' in line:
                    p = line.split('="', 1)[1].rstrip('";').split('~')
                    if len(p) > 2:
                        sc = p[2]
                results.append({'code': sc or '?', 'err': str(e)})
    return results


def _parse_line(line):
    """解析单行 v_sh600183="1~生益科技~600183~179.4~..." """
    p = line.split('="', 1)[1].rstrip('";').split('~')
    if len(p) < 40:
        raise ValueError('字段不足: %d' % len(p))

    def f(i):
        try:
            return float(p[i])
        except (ValueError, IndexError):
            return 0.0

    name = p[1]
    code = p[2]
    price = f(3)
    preclose = f(4)
    open_ = f(5)
    vol_hand = f(6)            # 成交量(手)
    high = f(33)
    low = f(34)
    amt = f(37)                # 成交额(元)
    turnover = f(38)           # 换手率%
    pe = f(39) if len(p) > 39 else 0.0
    amplitude = f(43) if len(p) > 43 else (round((high-low)/preclose*100, 2) if preclose else 0.0)
    # 市值字段位置随源波动，做保护
    float_mcap = f(44) * 1e8 if len(p) > 44 and f(44) < 1e5 else f(44)
    total_mcap = f(45) * 1e8 if len(p) > 45 and f(45) < 1e5 else f(45)

    chg = round((price / preclose - 1) * 100, 2) if preclose else None
    intraday = round((price / open_ - 1) * 100, 2) if open_ else None  # 开→收（日内走势）
    gap = round((open_ / preclose - 1) * 100, 2) if preclose else None  # 昨收→今开（缺口）
    return {
        'name': name,
        'code': code,
        'price': price,
        'preclose': preclose,
        'open': open_,
        'high': high,
        'low': low,
        'chg_pct': chg,               # 昨收→今收（真实涨跌幅）
        'gap_pct': gap,               # 昨收→今开（高开/低开幅度）
        'intraday_pct': intraday,     # 今开→今收（日内走势）
        'amplitude_pct': round(amplitude, 2),
        'turnover_pct': round(turnover, 2),
        'vol_wan': round(vol_hand / 10000, 1),     # 万手
        'amt_yi': round(amt / 1e8, 2),             # 亿元
        'pe': round(pe, 1) if pe else None,
        'float_mcap_yi': round(float_mcap / 1e8, 1) if float_mcap else None,
        'total_mcap_yi': round(total_mcap / 1e8, 1) if total_mcap else None,
    }


def quote_many(symbols):
    """quote 的别名，语义更明确。"""
    return quote(symbols)


# ----------------------------- 输出格式化 -----------------------------

def _fmt_table(rows):
    """list[dict] -> 对齐表格字符串。"""
    if not rows:
        return '(无数据)'
    cols = ['name', 'code', 'price', 'chg_pct', 'gap_pct', 'intraday_pct', 'amplitude_pct',
            'high', 'low', 'turnover_pct', 'amt_yi']
    heads = ['名称', '代码', '现价', '涨跌%', '高开%', '日内%', '振幅%', '高', '低', '换手%', '额(亿)']
    data = []
    for r in rows:
        if 'err' in r:
            data.append(['ERR', r.get('code', ''), r['err'], '', '', '', '', '', '', '', ''])
        else:
            data.append([_s(r.get(c)) for c in cols])
    # 列宽
    widths = [max(len(heads[i]), max((len(row[i]) for row in data), default=0))
              for i in range(len(heads))]
    sep = '  '.join('-' * w for w in widths)
    out = ['  '.join(h.ljust(widths[i]) for i, h in enumerate(heads)), sep]
    for row in data:
        out.append('  '.join(c.ljust(widths[i]) for i, c in enumerate(row)))
    return '\n'.join(out)


def _s(v):
    if v is None:
        return '-'
    if isinstance(v, float):
        return ('%g' % v)
    return str(v)


# ----------------------------- 命令行 -----------------------------

def _expand_args(args):
    """支持 @file 和 逗号/空格分隔。
    文件内支持 # 注释（整行或行内），# 之后的内容会被忽略。"""
    out = []
    for a in args:
        if a.startswith('@'):
            path = a[1:]
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as fh:
                    for ln in fh:
                        # 剥离行内注释：取 # 之前的部分
                        ln = ln.split('#', 1)[0]
                        ln = ln.strip()
                        if ln:
                            out.extend(ln.replace(',', ' ').split())
        else:
            # 命令行参数也支持行内 # 注释
            a = a.split('#', 1)[0]
            out.extend(a.replace(',', ' ').split())
    return out


def main(argv):
    args = argv[1:]
    fmt = 'table'
    if '--json' in args:
        fmt = 'json'; args = [a for a in args if a != '--json']
    elif '--csv' in args:
        fmt = 'csv'; args = [a for a in args if a != '--csv']

    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return 0

    symbols = _expand_args(args)
    if not symbols:
        print('错误：未提供代码'); return 1

    rows = quote(symbols)
    if fmt == 'json':
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif fmt == 'csv':
        print('名称,代码,现价,昨收,今开,涨跌%,高开%,日内%,振幅%,高,低,换手%,成交额(亿)')
        for r in rows:
            if 'err' in r:
                print(f"ERR,{r.get('code','')},{r['err']},,,,,,,,,")
            else:
                print(f"{r['name']},{r['code']},{r['price']},{r['preclose']},{r['open']},"
                      f"{r['chg_pct']},{r.get('gap_pct','-')},{r.get('intraday_pct','-')},"
                      f"{r['amplitude_pct']},{r['high']},{r['low']},{r['turnover_pct']},{r['amt_yi']}")
    else:
        print(_fmt_table(rows))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
