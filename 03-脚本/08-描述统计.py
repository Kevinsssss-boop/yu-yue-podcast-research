# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 描述统计  （第 1 版）
============================================================

【这个脚本在干什么？】
  用【全部 374 个节目 / 46,721 集】画一张生态全景图，
  不限于有播放量的那 57 个喜马拉雅节目。

【六个部分】
  ① 平台分布    —— 粤语播客聚集在哪
  ② 内容形态    —— 各类节目有多少
  ③ 时间演化    —— 什么时候冒出来的
  ④ 存活率      —— 还有多少在更新（重点）
  ⑤ 集数长尾    —— 多少节目只做了几集
  ⑥ 单集时长    —— 内容形态和生产成本的关系

【产出】
  07-分析/描述统计.md        ← 所有数字
  04-图表/*.png              ← 四张图

【怎么运行】
  在 03-脚本 目录下：
      python 08-描述统计.py
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

# 采集时点（用于判断「还在更新吗」）
COLLECT_YM = '2026-10'
# 近 12 个月的起点
RECENT_FROM = '2025-11'

# 平台太多太长，图上放不下，先归并一下
def collapse_platform(p):
    if p in ('Spotify/Anchor',):
        return 'Spotify/Anchor'
    if p in ('SoundOn', 'Firstory'):
        return '台湾平台'
    if p in ('喜马拉雅', '小宇宙', '荔枝'):
        return p
    return '其他自建'


# ============================================================
#  画图设置
# ============================================================
def setup_matplotlib():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    return plt


def main():
    plt = setup_matplotlib()

    # ---------- 读数据 ----------
    progs = list(csv.DictReader(open(os.path.join(CLEAN, '节目表_粤语.csv'),
                                     encoding='utf-8-sig')))
    eps = list(csv.DictReader(open(os.path.join(CLEAN, '单集表_粤语.csv'),
                                   encoding='utf-8-sig')))
    print(f'节目 {len(progs)} 个，单集 {len(eps):,} 集')

    # 每个节目的最晚发布月 / 首次发布月
    last_ym = {}
    first_ym = {}
    for e in eps:
        p = e['所属节目']
        ym = e['发布年月']
        if not ym:
            continue
        if p not in last_ym or ym > last_ym[p]:
            last_ym[p] = ym
        if p not in first_ym or ym < first_ym[p]:
            first_ym[p] = ym

    L = ['# 描述统计\n', '> 由 `03-脚本/08-描述统计.py` 自动生成\n',
         f'- 样本：**{len(progs)}** 个节目 / **{len(eps):,}** 集',
         f'- 采集时点：{COLLECT_YM}\n']

    # ============================================================
    # ① 平台分布
    # ============================================================
    print()
    print('=' * 66)
    print(' ① 平台分布')
    print('=' * 66)

    plat_prog = Counter()
    plat_eps = Counter()
    plat_active = Counter()
    for p in progs:
        pl = collapse_platform(p['平台'])
        plat_prog[pl] += 1
        plat_eps[pl] += int(p['集数'] or 0)
        if last_ym.get(p['节目名'], '') >= RECENT_FROM:
            plat_active[pl] += 1

    L.append('## 一、平台分布\n')
    L.append('| 平台 | 节目数 | 占比 | 集数 | 近12月仍在更新 | 活跃率 |')
    L.append('|---|---:|---:|---:|---:|---:|')
    print(f' {"平台":<16}{"节目":>5}{"占比":>7}{"集数":>8}{"活跃":>6}{"活跃率":>8}')
    for pl, n in plat_prog.most_common():
        act = plat_active[pl]
        rate = act / n * 100
        L.append(f'| {pl} | {n} | {n / len(progs) * 100:.1f}% | {plat_eps[pl]:,} | {act} | {rate:.0f}% |')
        print(f' {pl:<16}{n:>5}{n / len(progs) * 100:>6.1f}%{plat_eps[pl]:>8,}{act:>6}{rate:>7.0f}%')
    L.append('')

    # 柱图
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = [k for k, _ in plat_prog.most_common()]
    vals = [plat_prog[k] for k in names]
    acts = [plat_active[k] for k in names]
    y = range(len(names))
    ax.barh(list(y), vals, color='#9dc3e6', label='节目数')
    ax.barh(list(y), acts, color='#2e75b6', label='近12月仍更新')
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel('节目数')
    ax.set_title('各平台节目数与活跃情况')
    ax.legend()
    for i, v in enumerate(vals):
        ax.text(v + 1, i, str(v), va='center', fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTFIG, '01-平台分布.png'), dpi=150)
    plt.close()

    # ============================================================
    # ② 内容形态
    # ============================================================
    print()
    print('=' * 66)
    print(' ② 内容形态（全部 374）')
    print('=' * 66)
    form_n = Counter(p['内容形态'] for p in progs)
    form_eps = Counter()
    for p in progs:
        form_eps[p['内容形态']] += int(p['集数'] or 0)

    L.append('## 二、内容形态（全部 374 个）\n')
    L.append('| 形态 | 节目数 | 占比 | 集数 | 平均集数/节目 |')
    L.append('|---|---:|---:|---:|---:|')
    print(f' {"形态":<12}{"节目":>5}{"占比":>7}{"集数":>8}{"均集/节目":>10}')
    for f, n in form_n.most_common():
        avg = form_eps[f] / n
        L.append(f'| {f} | {n} | {n / len(progs) * 100:.1f}% | {form_eps[f]:,} | {avg:.0f} |')
        print(f' {f:<12}{n:>5}{n / len(progs) * 100:>6.1f}%{form_eps[f]:>8,}{avg:>10.0f}')
    L.append('')

    # ============================================================
    # ③ 时间演化
    # ============================================================
    print()
    print('=' * 66)
    print(' ③ 时间演化')
    print('=' * 66)
    eps_by_year = Counter()
    for e in eps:
        y = (e['发布年月'] or '')[:4]
        if y.isdigit():
            eps_by_year[int(y)] += 1
    new_prog_by_year = Counter()
    for p in progs:
        y = first_ym.get(p['节目名'], '')[:4]
        if y.isdigit():
            new_prog_by_year[int(y)] += 1

    years = sorted(y for y in eps_by_year if y >= 2015)
    L.append('## 三、时间演化\n')
    L.append('| 年份 | 新增节目 | 新增单集 |')
    L.append('|---:|---:|---:|')
    print(f' {"年份":<6}{"新增节目":>8}{"新增单集":>9}')
    for y in years:
        L.append(f'| {y} | {new_prog_by_year.get(y, 0)} | {eps_by_year[y]:,} |')
        print(f' {y:<6}{new_prog_by_year.get(y, 0):>8}{eps_by_year[y]:>9,}')
    L.append('')

    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    ax1.bar(years, [eps_by_year[y] for y in years], color='#9dc3e6', label='新增单集')
    ax1.set_xlabel('年份')
    ax1.set_ylabel('新增单集数', color='#2e75b6')
    ax2 = ax1.twinx()
    ax2.plot(years, [new_prog_by_year.get(y, 0) for y in years],
             color='#c00000', marker='o', label='新增节目')
    ax2.set_ylabel('新增节目数', color='#c00000')
    ax1.set_title('粤语播客的时间演化（2015 年起）')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTFIG, '02-时间演化.png'), dpi=150)
    plt.close()

    # ============================================================
    # ④ 存活率（重点）
    # ============================================================
    print()
    print('=' * 66)
    print(' ④ 存活率')
    print('=' * 66)
    alive = [p for p in progs if last_ym.get(p['节目名'], '') >= RECENT_FROM]
    dead = [p for p in progs if p['节目名'] in last_ym and p['节目名'] not in
            {a['节目名'] for a in alive}]
    nodata = [p for p in progs if p['节目名'] not in last_ym]
    print(f' 近12月仍更新：{len(alive)}')
    print(f' 已停更      ：{len(dead)}')
    print(f' 无单集数据  ：{len(nodata)}')

    # 停更多久
    gap_months = []
    for p in dead:
        ym = last_ym[p['节目名']]
        gap = (int(COLLECT_YM[:4]) - int(ym[:4])) * 12 + (int(COLLECT_YM[5:]) - int(ym[5:]))
        gap_months.append(gap)

    L.append('## 四、存活率\n')
    L.append(f'- 近 12 个月仍在更新：**{len(alive)}**（{len(alive) / len(progs) * 100:.0f}%）')
    L.append(f'- 已停更：**{len(dead)}**（{len(dead) / len(progs) * 100:.0f}%）')
    L.append(f'- 无单集数据：{len(nodata)}')
    if gap_months:
        L.append(f'- 停更节目距今：中位数 **{statistics.median(gap_months):.0f}** 个月，'
                 f'最长 {max(gap_months)} 个月')
        print(f' 停更时间：中位 {statistics.median(gap_months):.0f} 个月，最长 {max(gap_months)} 个月')
    L.append('')

    # 按形态看存活率
    L.append('### 按内容形态看存活率\n')
    L.append('| 形态 | 节目数 | 仍更新 | 活跃率 |')
    L.append('|---|---:|---:|---:|')
    alive_set = {a['节目名'] for a in alive}
    by_form_alive = defaultdict(lambda: [0, 0])
    for p in progs:
        f = p['内容形态']
        by_form_alive[f][0] += 1
        if p['节目名'] in alive_set:
            by_form_alive[f][1] += 1
    for f, (n, a) in sorted(by_form_alive.items(), key=lambda x: -x[1][1] / x[1][0]):
        L.append(f'| {f} | {n} | {a} | {a / n * 100:.0f}% |')
    L.append('')

    # ============================================================
    # ⑤ 集数长尾
    # ============================================================
    print()
    print('=' * 66)
    print(' ⑤ 集数分布')
    print('=' * 66)
    ep_counts = sorted(int(p['集数'] or 0) for p in progs)
    buckets = [(1, 9), (10, 29), (30, 99), (100, 299), (300, 999), (1000, 999999)]
    L.append('## 五、集数分布（长尾）\n')
    L.append('| 集数区间 | 节目数 | 占比 |')
    L.append('|---|---:|---:|')
    print(f' {"区间":<12}{"节目":>5}{"占比":>8}')
    for lo, hi in buckets:
        n = sum(1 for x in ep_counts if lo <= x <= hi)
        label = f'{lo}–{hi}' if hi < 999999 else f'{lo}+'
        L.append(f'| {label} | {n} | {n / len(progs) * 100:.1f}% |')
        print(f' {label:<12}{n:>5}{n / len(progs) * 100:>7.1f}%')
    L.append(f'\n> 中位数 **{statistics.median(ep_counts):.0f}** 集，'
             f'平均 {sum(ep_counts) / len(ep_counts):.0f} 集，'
             f'最多 {max(ep_counts):,} 集\n')

    # ============================================================
    # ⑥ 单集时长
    # ============================================================
    print()
    print('=' * 66)
    print(' ⑥ 单集时长')
    print('=' * 66)
    durs = [int(e['时长_秒']) for e in eps if (e['时长_秒'] or '').isdigit()]
    print(f' 有时长数据 {len(durs):,} / {len(eps):,}')
    med_min = statistics.median(durs) / 60
    L.append('## 六、单集时长\n')
    L.append(f'- 有时长数据：**{len(durs):,}** / {len(eps):,}（缺 {(len(eps) - len(durs)) / len(eps) * 100:.0f}%）')
    L.append(f'- 中位时长：**{med_min:.1f} 分钟**')
    L.append(f'- 平均时长：{sum(durs) / len(durs) / 60:.1f} 分钟')
    L.append(f'- 四分位数：{statistics.quantiles(durs, n=4)[0] / 60:.0f} / '
             f'{med_min:.0f} / {statistics.quantiles(durs, n=4)[2] / 60:.0f} 分钟\n')

    # 按形态
    L.append('### 按形态看时长\n')
    L.append('| 形态 | 中位时长(分) | 平均(分) |')
    L.append('|---|---:|---:|')
    dur_by_form = defaultdict(list)
    form_of = {p['节目名']: p['内容形态'] for p in progs}
    for e in eps:
        d = e['时长_秒']
        if (d or '').isdigit():
            f = form_of.get(e['所属节目'])
            if f:
                dur_by_form[f].append(int(d))
    for f, lst in sorted(dur_by_form.items(), key=lambda x: -statistics.median(x[1])):
        L.append(f'| {f} | {statistics.median(lst) / 60:.0f} | {sum(lst) / len(lst) / 60:.0f} |')
        print(f' {f:<12} 中位 {statistics.median(lst) / 60:>5.0f} 分  平均 {sum(lst) / len(lst) / 60:>5.0f} 分')
    L.append('')

    # 时长直方图
    fig, ax = plt.subplots(figsize=(8, 4.5))
    cap = [d / 60 for d in durs if d / 60 <= 180]
    ax.hist(cap, bins=60, color='#9dc3e6', edgecolor='white')
    ax.axvline(med_min, color='#c00000', linestyle='--', label=f'中位数 {med_min:.0f} 分')
    ax.set_xlabel('单集时长（分钟）')
    ax.set_ylabel('集数')
    ax.set_title(f'单集时长分布（截到 180 分钟，覆盖 {len(cap) / len(durs) * 100:.0f}%）')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTFIG, '03-时长分布.png'), dpi=150)
    plt.close()

    # ---------- 写报告 ----------
    p_md = os.path.join(OUTMD, '描述统计.md')
    with open(p_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print()
    print(f'[OK] {p_md}')
    print(f'[OK] 图表 → {OUTFIG}')


if __name__ == '__main__':
    main()
