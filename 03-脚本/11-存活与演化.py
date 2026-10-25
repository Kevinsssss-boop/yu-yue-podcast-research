# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 存活率与时间演化  （第 1 版）
============================================================

【补这两个分析是为了什么】
  08 的描述统计告诉我们「51% 的节目停更了」「2020 年爆发」，
  但那只是快照。这两个分析回答「为什么」：

    ① 存活率 —— 什么样的节目活得久？
       按形态 / 平台 / 集数 / 更新频率分组，看哪组死得快。

    ② 演化 —— 各类内容是同时起来的，还是先后起来的？
       按年统计各形态的新增单集，看兴衰曲线。

【一个必须写进报告的统计陷阱】
  存活率是在【单一时点】（2026-10）测的，属于「右删失」：
    2026 年才开播的节目，本来就没机会"停更"，
    所以它们的存活率必然虚高。
  所以「按首播年份看存活率」那张表，只能说明趋势，
  不能得出「新节目更持久」的结论。

【怎么运行】
      python 11-存活与演化.py
"""

import os
import sys
import csv
import statistics
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.join(HERE, '..')
CLEAN  = os.path.join(ROOT, '02-清洗后数据')
OUTMD  = os.path.join(ROOT, '07-分析')
OUTFIG = os.path.join(ROOT, '04-图表')
os.makedirs(OUTMD, exist_ok=True)
os.makedirs(OUTFIG, exist_ok=True)

COLLECT_YM = '2026-10'      # 采集时点
ALIVE_FROM = '2025-11'      # 这个月之后还有更新 = 存活


def setup_mpl():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    return plt


def collapse_platform(p):
    if p == 'Spotify/Anchor':
        return 'Spotify/Anchor'
    if p in ('SoundOn', 'Firstory'):
        return '台湾平台'
    if p in ('喜马拉雅', '小宇宙', '荔枝'):
        return p
    return '其他自建'


def month_diff(a, b):
    """a 比 b 晚几个月。"""
    return (int(a[:4]) - int(b[:4])) * 12 + (int(a[5:7]) - int(b[5:7]))


def main():
    plt = setup_mpl()

    progs = list(csv.DictReader(open(os.path.join(CLEAN, '节目表_粤语.csv'),
                                     encoding='utf-8-sig')))
    eps = list(csv.DictReader(open(os.path.join(CLEAN, '单集表_粤语.csv'),
                                   encoding='utf-8-sig')))
    print(f'节目 {len(progs)}，单集 {len(eps):,}')

    # 每个节目的首末发布月 + 集数（去重后实际抓到的）
    first_ym, last_ym, ep_n = {}, {}, Counter()
    for e in eps:
        n, ym = e['所属节目'], e['发布年月']
        if not ym:
            continue
        ep_n[n] += 1
        if n not in first_ym or ym < first_ym[n]:
            first_ym[n] = ym
        if n not in last_ym or ym > last_ym[n]:
            last_ym[n] = ym

    # 给每个节目算好字段
    data = []
    for p in progs:
        n = p['节目名']
        if n not in last_ym:
            continue                       # 没有单集数据的跳过
        alive = last_ym[n] >= ALIVE_FROM
        n_ep = ep_n[n]
        span = month_diff(last_ym[n], first_ym[n]) + 1
        data.append({
            '名': n,
            '形态': p['内容形态'],
            '平台': collapse_platform(p['平台']),
            '集数': n_ep,
            '首播年': int(first_ym[n][:4]),
            '跨度月': span,
            '频率': n_ep / span,          # 集/月
            '存活': alive,
            '停更月': 0 if alive else month_diff(COLLECT_YM, last_ym[n]),
        })
    print(f'有效节目（有单集）：{len(data)}')

    L = ['# 存活率与时间演化\n', '> 由 `03-脚本/11-存活与演化.py` 自动生成\n',
         f'- 样本：**{len(data)}** 个节目（有单集数据的）',
         f'- 存活定义：`{ALIVE_FROM}` 之后仍有更新\n']

    # ============================================================
    # ① 存活率 × 形态
    # ============================================================
    def surv_table(key, title, order=None):
        g = defaultdict(lambda: [0, 0])
        for d in data:
            g[d[key]][0] += 1
            if d['存活']:
                g[d[key]][1] += 1
        items = sorted(g.items(), key=lambda x: (-x[1][1] / x[1][0], -x[1][0]))
        if order:
            items = [(k, g[k]) for k in order if k in g]

        print()
        print('=' * 62)
        print(f' {title}')
        print('=' * 62)
        print(f' {"分组":<14}{"节目":>5}{"存活":>5}{"存活率":>8}')
        print('-' * 62)
        L.append(f'\n## {title}\n')
        L.append('| 分组 | 节目数 | 存活 | 存活率 |')
        L.append('|---|---:|---:|---:|')
        for k, (n, a) in items:
            print(f' {k:<14}{n:>5}{a:>5}{a / n * 100:>7.0f}%')
            L.append(f'| {k} | {n} | {a} | {a / n * 100:.0f}% |')
        L.append('')
        return items

    items_form = surv_table('形态', '一、存活率 × 内容形态')

    # 图：形态存活率
    fig, ax = plt.subplots(figsize=(9, 4.5))
    names = [k for k, _ in items_form]
    rates = [v[1] / v[0] * 100 for _, v in items_form]
    ns = [v[0] for _, v in items_form]
    bars = ax.barh(names, rates, color='#2e75b6')
    ax.invert_yaxis()
    ax.set_xlabel('存活率（%）')
    ax.set_title('各内容形态的存活率（近 12 个月仍在更新）')
    for i, (r, n) in enumerate(zip(rates, ns)):
        ax.text(r + 1, i, f'{r:.0f}%  (n={n})', va='center', fontsize=9)
    ax.set_xlim(0, 100)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTFIG, '04-存活率-形态.png'), dpi=150)
    plt.close()

    surv_table('平台', '二、存活率 × 平台')

    # ============================================================
    # ② 存活率 × 集数
    # ============================================================
    buckets = [(1, 9), (10, 29), (30, 99), (100, 299), (300, 99999)]
    g = defaultdict(lambda: [0, 0])
    for d in data:
        for lo, hi in buckets:
            if lo <= d['集数'] <= hi:
                label = f'{lo}–{hi}' if hi < 99999 else f'{lo}+'
                g[label][0] += 1
                if d['存活']:
                    g[label][1] += 1
                break
    labels = [f'{lo}–{hi}' if hi < 99999 else f'{lo}+' for lo, hi in buckets]

    print()
    print('=' * 62)
    print(' 三、存活率 × 集数')
    print('=' * 62)
    L.append('## 三、存活率 × 集数\n')
    L.append('| 集数 | 节目数 | 存活 | 存活率 |')
    L.append('|---|---:|---:|---:|')
    print(f' {"集数":<12}{"节目":>5}{"存活":>5}{"存活率":>8}')
    for lb in labels:
        n, a = g[lb]
        if n == 0:
            continue
        print(f' {lb:<12}{n:>5}{a:>5}{a / n * 100:>7.0f}%')
        L.append(f'| {lb} | {n} | {a} | {a / n * 100:.0f}% |')
    L.append('')

    # ============================================================
    # ③ 存活 vs 更新频率
    # ============================================================
    alive_f = [d['频率'] for d in data if d['存活']]
    dead_f = [d['频率'] for d in data if not d['存活']]
    print()
    print('=' * 62)
    print(' 四、更新频率：存活 vs 停更')
    print('=' * 62)
    print(f' 存活节目 更新频率中位 {statistics.median(alive_f):.2f} 集/月（n={len(alive_f)}）')
    print(f' 停更节目 更新频率中位 {statistics.median(dead_f):.2f} 集/月（n={len(dead_f)}）')
    L.append('## 四、更新频率\n')
    L.append(f'- 存活节目：中位 **{statistics.median(alive_f):.2f}** 集/月')
    L.append(f'- 停更节目：中位 **{statistics.median(dead_f):.2f}** 集/月\n')

    # ============================================================
    # ④ 时间演化 × 形态
    # ============================================================
    print()
    print('=' * 62)
    print(' 五、时间演化 × 形态（新增单集数）')
    print('=' * 62)
    form_of = {p['节目名']: p['内容形态'] for p in progs}
    year_form = defaultdict(Counter)
    for e in eps:
        y, ym = (e['发布年月'] or '')[:4], e['发布年月']
        if not y.isdigit() or int(y) < 2015:
            continue
        f = form_of.get(e['所属节目'])
        if f:
            year_form[int(y)][f] += 1

    years = sorted(year_form)
    # 取总量最大的 6 个形态，其余合并
    totals = Counter()
    for y in years:
        totals.update(year_form[y])
    top_forms = [f for f, _ in totals.most_common(6)]
    others = [f for f in totals if f not in top_forms]

    L.append('## 五、时间演化 × 形态\n')
    L.append('各形态每年的新增单集数（前六大形态）\n')
    header = '| 年份 | ' + ' | '.join(top_forms) + ' | 其他 |'
    L.append(header)
    L.append('|---:|' + '---:|' * (len(top_forms) + 1))
    print(f' {"年份":<6}' + ''.join(f'{f[:6]:>8}' for f in top_forms) + f'{"其他":>7}')
    for y in years:
        row = [str(year_form[y].get(f, 0)) for f in top_forms]
        oth = sum(year_form[y].get(f, 0) for f in others)
        L.append(f'| {y} | ' + ' | '.join(row) + f' | {oth} |')
        print(f' {y:<6}' + ''.join(f'{int(v):>8}' for v in row) + f'{oth:>7}')
    L.append('')

    # 图：形态演化折线
    fig, ax = plt.subplots(figsize=(9.5, 5))
    for f in top_forms:
        ys = [year_form[y].get(f, 0) for y in years]
        ax.plot(years, ys, marker='o', markersize=3, label=f)
    ax.set_xlabel('年份')
    ax.set_ylabel('新增单集数')
    ax.set_title('各内容形态的时间演化（2015–2026）')
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTFIG, '05-形态演化.png'), dpi=150)
    plt.close()

    # ============================================================
    # ⑤ 各形态的首播年份
    # ============================================================
    first_year_by_form = defaultdict(list)
    for d in data:
        first_year_by_form[d['形态']].append(d['首播年'])
    # ---------- 稳健版：按「当年活跃节目数」统计 ----------
    #  为什么不用集数：
    #    单个节目就能扭曲整条曲线 ——
    #    2025 年「新闻时事」2,039 集，其中 2,036 来自 SBS 一档节目；
    #    2026 年「其他教育」1,736 集，其中 1,470 来自陈老C 一个人。
    #    按节目数统计，一档节目永远只算 1，不会被高产节目带偏。
    print()
    print('=' * 62)
    print(' 六、时间演化 × 形态（按当年活跃节目数，稳健）')
    print('=' * 62)

    year_form_prog = defaultdict(lambda: defaultdict(set))
    for e in eps:
        y = (e['发布年月'] or '')[:4]
        if not y.isdigit() or int(y) < 2015:
            continue
        f = form_of.get(e['所属节目'])
        if f:
            year_form_prog[int(y)][f].add(e['所属节目'])

    L.append('\n## 六、时间演化 × 形态（按活跃节目数，推荐用这个）\n')
    L.append('> 按集数统计会被单档高产节目带偏（SBS 2025 年 2,036 集、'
             '陈老C 2026 年 1,470 集）。按节目数统计，一档节目只算 1。\n')
    L.append('| 年份 | ' + ' | '.join(top_forms) + ' | 合计 |')
    L.append('|---:|' + '---:|' * (len(top_forms) + 1))
    print(f' {"年份":<6}' + ''.join(f'{f[:6]:>8}' for f in top_forms) + f'{"合计":>7}')
    for y in years:
        cells = [len(year_form_prog[y].get(f, ())) for f in top_forms]
        tot = len(set().union(*[year_form_prog[y].get(f, set()) for f in top_forms])) if y in year_form_prog else 0
        L.append(f'| {y} | ' + ' | '.join(str(c) for c in cells) + f' | {tot} |')
        print(f' {y:<6}' + ''.join(f'{c:>8}' for c in cells) + f'{tot:>7}')
    L.append('')

    fig, ax = plt.subplots(figsize=(9.5, 5))
    for f in top_forms:
        ys = [len(year_form_prog[y].get(f, ())) for y in years]
        ax.plot(years, ys, marker='o', markersize=4, label=f)
    ax.set_xlabel('年份')
    ax.set_ylabel('当年活跃节目数')
    ax.set_title('各内容形态的时间演化（按活跃节目数，2015–2026）')
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTFIG, '05-形态演化.png'), dpi=150)
    plt.close()

    L.append('### 各形态的首播年份中位数\n')
    L.append('| 形态 | 节目数 | 首播年中位 | 最早 |')
    L.append('|---|---:|---:|---:|')
    for f, ys in sorted(first_year_by_form.items(),
                        key=lambda x: statistics.median(x[1])):
        L.append(f'| {f} | {len(ys)} | {statistics.median(ys):.0f} | {min(ys)} |')
    L.append('')

    # 删失说明
    L.append('\n## 六、统计陷阱（必读）\n')
    L.append('存活率是在 **单一时点**（2026-10）测的，属于**右删失**：')
    L.append('2026 年才开播的节目本来就没机会停更，存活率必然虚高。')
    L.append('所以「按首播年份看存活率」只能说明趋势，'
             '**不能得出「新节目更持久」的结论**。\n')

    p = os.path.join(OUTMD, '存活与演化.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print(f'\n[OK] {p}')
    print(f'[OK] 图表 → {OUTFIG}')


if __name__ == '__main__':
    main()
