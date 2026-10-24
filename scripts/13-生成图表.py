# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 报告用图表生成  （第 1 版）
============================================================

【为什么单独一个脚本】
  08/11 那两个脚本里的图是"边算边画"，样式不统一、尺寸也不适合 PDF/Word。
  这里统一出一套：同样的配色、同样的字号、同样的画布比例，直接插进报告。

【产出】04-图表/ 下 11 张图

  图1  平台分布与活跃率
  图2  内容形态分布
  图3  时间演化（新增节目 / 新增单集）
  图4  形态演化（活跃节目数）
  图5  存活率 × 内容形态
  图6  存活率 × 集数
  图7  集数长尾分布
  图8  单集时长分布
  图9  播放量集中度（帕累托）
  图10 主题供需散点
  图11 主题分布：样本 vs 全量

【怎么运行】
      python 13-生成图表.py
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

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.join(HERE, '..')
CLEAN  = os.path.join(ROOT, '02-清洗后数据')
ANA    = os.path.join(ROOT, '06-听众侧')
OUT    = os.path.join(ROOT, '04-图表')
os.makedirs(OUT, exist_ok=True)

# ---- 统一视觉 ----
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 10
plt.rcParams['axes.edgecolor'] = '#888888'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['figure.dpi'] = 200

BLUE   = '#2e75b6'
LBLUE  = '#9dc3e6'
RED    = '#c00000'
ORANGE = '#ed7d31'
GREEN  = '#70ad47'
GREY   = '#bfbfbf'

W, H = 7.2, 4.0      # 英寸，约 18cm 宽，适合 A4 竖排

ALIVE_FROM = '2025-11'
COLLECT_YM = '2026-10'


def style(ax, title=None, xlabel=None, ylabel=None, grid='y'):
    if title:
        ax.set_title(title, fontsize=11, pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)
    if grid:
        ax.grid(axis=grid, alpha=0.25, linewidth=0.6)
        ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(p, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  [OK] {name}')


def main():
    progs = list(csv.DictReader(open(os.path.join(CLEAN, '节目表_粤语.csv'),
                                     encoding='utf-8-sig')))
    eps = list(csv.DictReader(open(os.path.join(CLEAN, '单集表_粤语.csv'),
                                   encoding='utf-8-sig')))
    print(f'节目 {len(progs)}，单集 {len(eps):,}')

    # 每档节目的首末发布月、集数
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

    def alive(n):
        return last_ym.get(n, '') >= ALIVE_FROM

    # =========================================================
    # 图1 平台分布与活跃率
    # =========================================================
    def plat(p):
        if p == 'Spotify/Anchor':
            return 'Spotify/Anchor'
        if p in ('SoundOn', 'Firstory'):
            return '台湾平台'
        if p in ('喜马拉雅', '小宇宙', '荔枝'):
            return p
        return '其他自建'

    pc, pa = Counter(), Counter()
    for r in progs:
        k = plat(r['平台'])
        pc[k] += 1
        if alive(r['节目名']):
            pa[k] += 1
    order = [k for k, _ in pc.most_common()]

    fig, ax = plt.subplots(figsize=(W, H))
    y = range(len(order))
    vals = [pc[k] for k in order]
    acts = [pa[k] for k in order]
    ax.barh(list(y), vals, color=LBLUE, label='节目总数')
    ax.barh(list(y), acts, color=BLUE, label='近12个月仍更新')
    ax.set_yticks(list(y))
    ax.set_yticklabels(order)
    ax.invert_yaxis()
    for i, k in enumerate(order):
        ax.text(pc[k] + 2, i, f'{pc[k]}（{pa[k] / pc[k] * 100:.0f}%）',
                va='center', fontsize=9, color='#333333')
    ax.set_xlim(0, max(vals) * 1.28)
    style(ax, '各平台的节目数量与活跃情况', '节目数', None, grid='x')
    ax.legend(frameon=False, fontsize=9, loc='lower right')
    save(fig, '图1-平台分布.png')

    # =========================================================
    # 图2 内容形态分布
    # =========================================================
    fc, fe = Counter(), Counter()
    for r in progs:
        fc[r['内容形态']] += 1
        fe[r['内容形态']] += int(r['集数'] or 0)
    forms = [k for k, _ in fc.most_common()]

    fig, ax = plt.subplots(figsize=(W, H))
    yy = range(len(forms))
    ax.barh(list(yy), [fc[f] for f in forms], color=BLUE)
    ax.set_yticks(list(yy))
    ax.set_yticklabels(forms)
    ax.invert_yaxis()
    for i, f in enumerate(forms):
        ax.text(fc[f] + 2, i, str(fc[f]), va='center', fontsize=9)
    ax.set_xlim(0, max(fc.values()) * 1.18)
    style(ax, '各内容形态的节目数量（全样本）', '节目数', None, grid='x')
    save(fig, '图2-内容形态.png')

    # =========================================================
    # 图3 时间演化
    # =========================================================
    by_year, prog_year = Counter(), Counter()
    for e in eps:
        y = (e['发布年月'] or '')[:4]
        if y.isdigit() and int(y) >= 2015:
            by_year[int(y)] += 1
    for n, ym in first_ym.items():
        if ym[:4].isdigit() and int(ym[:4]) >= 2015:
            prog_year[int(ym[:4])] += 1
    years = sorted(by_year)

    fig, ax1 = plt.subplots(figsize=(W, H))
    ax1.bar(years, [by_year[y] for y in years], color=LBLUE, label='新增单集（左轴）')
    ax1.set_xlabel('年份', fontsize=9)
    ax1.set_ylabel('新增单集数', fontsize=9, color=BLUE)
    ax1.tick_params(axis='y', labelcolor=BLUE)
    ax2 = ax1.twinx()
    ax2.plot(years, [prog_year.get(y, 0) for y in years], color=RED,
             marker='o', markersize=4, linewidth=1.6, label='新开播节目（右轴）')
    ax2.set_ylabel('新增节目数', fontsize=9, color=RED)
    ax2.tick_params(axis='y', labelcolor=RED)
    ax1.set_title('粤语播客的时间演化（2015–2026）', fontsize=11, pad=10)
    ax1.grid(axis='y', alpha=0.25, linewidth=0.6)
    ax1.set_axisbelow(True)
    for s in ('top',):
        ax1.spines[s].set_visible(False)
        ax2.spines[s].set_visible(False)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8.5, loc='upper left')
    save(fig, '图3-时间演化.png')

    # =========================================================
    # 图4 形态演化（活跃节目数）
    # =========================================================
    form_of = {p['节目名']: p['内容形态'] for p in progs}
    yf = defaultdict(lambda: defaultdict(set))
    for e in eps:
        y = (e['发布年月'] or '')[:4]
        if not y.isdigit() or int(y) < 2015:
            continue
        f = form_of.get(e['所属节目'])
        if f:
            yf[int(y)][f].add(e['所属节目'])
    totals = Counter()
    for y in yf:
        for f, s in yf[y].items():
            totals[f] += len(s)
    top6 = [f for f, _ in totals.most_common(6)]

    fig, ax = plt.subplots(figsize=(W, H))
    colors = [BLUE, RED, ORANGE, GREEN, '#7030a0', '#00b0f0']
    for i, f in enumerate(top6):
        ys = [len(yf[y].get(f, ())) for y in years]
        ax.plot(years, ys, marker='o', markersize=3.5, linewidth=1.6,
                color=colors[i], label=f)
    style(ax, '各内容形态的活跃节目数（2015–2026）', '年份', '当年活跃节目数')
    ax.legend(frameon=False, fontsize=8.5, ncol=2)
    save(fig, '图4-形态演化.png')

    # =========================================================
    # 图5 存活率 × 形态
    # =========================================================
    sf = defaultdict(lambda: [0, 0])
    for r in progs:
        f = r['内容形态']
        sf[f][0] += 1
        if alive(r['节目名']):
            sf[f][1] += 1
    items = sorted(((k, v) for k, v in sf.items() if v[0] >= 8),
                   key=lambda x: x[1][1] / x[1][0])

    fig, ax = plt.subplots(figsize=(W, H))
    names = [k for k, _ in items]
    rates = [v[1] / v[0] * 100 for _, v in items]
    bars = ax.barh(names, rates, color=BLUE)
    for i, (k, v) in enumerate(items):
        ax.text(rates[i] + 1, i, f'{rates[i]:.0f}%  (n={v[0]})', va='center', fontsize=8.5)
    ax.set_xlim(0, 100)
    style(ax, '各内容形态的存活率（近12个月仍在更新）', '存活率（%）', None, grid='x')
    save(fig, '图5-存活率-形态.png')

    # =========================================================
    # 图6 存活率 × 集数
    # =========================================================
    buckets = [(1, 9), (10, 29), (30, 99), (100, 299), (300, 10 ** 9)]
    labels = ['1–9', '10–29', '30–99', '100–299', '300+']
    bg = defaultdict(lambda: [0, 0])
    for r in progs:
        n = int(r['集数'] or 0)
        for i, (lo, hi) in enumerate(buckets):
            if lo <= n <= hi:
                bg[labels[i]][0] += 1
                if alive(r['节目名']):
                    bg[labels[i]][1] += 1
                break

    fig, ax = plt.subplots(figsize=(W, H * 0.85))
    rs = [bg[l][1] / bg[l][0] * 100 for l in labels]
    bars = ax.bar(labels, rs, color=BLUE, width=0.6)
    for i, l in enumerate(labels):
        ax.text(i, rs[i] + 2, f'{rs[i]:.0f}%', ha='center', fontsize=9)
        ax.text(i, 3, f'n={bg[l][0]}', ha='center', fontsize=8, color='white')
    ax.set_ylim(0, 100)
    style(ax, '存活率随节目集数的变化', '节目总集数', '存活率（%）')
    save(fig, '图6-存活率-集数.png')

    # =========================================================
    # 图7 集数长尾
    # =========================================================
    counts = sorted(int(r['集数'] or 0) for r in progs)
    fig, ax = plt.subplots(figsize=(W, H * 0.85))
    ax.hist([c for c in counts if c <= 500], bins=50, color=LBLUE,
            edgecolor='white', linewidth=0.6)
    ax.axvline(statistics.median(counts), color=RED, linestyle='--',
               linewidth=1.4, label=f'中位数 {statistics.median(counts):.0f} 集')
    ax.set_yscale('log')
    style(ax, '节目总集数的分布（对数纵轴，截到 500 集）', '节目集数', '节目数（对数）')
    ax.legend(frameon=False, fontsize=9)
    save(fig, '图7-集数长尾.png')

    # =========================================================
    # 图8 时长分布
    # =========================================================
    durs = [int(e['时长_秒']) / 60 for e in eps if (e['时长_秒'] or '').isdigit()]
    fig, ax = plt.subplots(figsize=(W, H * 0.9))
    cap = [d for d in durs if d <= 120]
    ax.hist(cap, bins=60, color=LBLUE, edgecolor='white', linewidth=0.5)
    ax.axvline(statistics.median(durs), color=RED, linestyle='--', linewidth=1.4,
               label=f'中位 {statistics.median(durs):.1f} 分钟')
    style(ax, '单集时长分布（截到 120 分钟）', '单集时长（分钟）', '集数')
    ax.legend(frameon=False, fontsize=9)
    save(fig, '图8-时长分布.png')

    # =========================================================
    # 图9 播放量帕累托（57 个喜马拉雅节目）
    # =========================================================
    topic = {}
    tp = os.path.join(ROOT, '07-分析', '内容主题_定稿.csv')
    if os.path.exists(tp):
        topic = {r['节目名']: r['主题']
                 for r in csv.DictReader(open(tp, encoding='utf-8-sig'))}
    h_eps = list(csv.DictReader(open(os.path.join(ANA, '喜马拉雅单集_清洗后.csv'),
                                    encoding='utf-8-sig')))
    psum = Counter()
    for e in h_eps:
        if e['播放量']:
            psum[e['节目名称']] += int(e['播放量'])
    tot = sum(psum.values())
    ranked = sorted(psum.values(), reverse=True)
    cum = []
    s = 0
    for v in ranked:
        s += v
        cum.append(s / tot * 100)

    fig, ax1 = plt.subplots(figsize=(W, H))
    xs = range(1, len(ranked) + 1)
    ax1.bar(list(xs), [v / 1e4 for v in ranked], color=LBLUE, width=0.75)
    ax1.set_xlabel('节目（按播放量降序）', fontsize=9)
    ax1.set_ylabel('播放量（万）', fontsize=9, color=BLUE)
    ax1.tick_params(axis='y', labelcolor=BLUE)
    ax2 = ax1.twinx()
    ax2.plot(list(xs), cum, color=RED, marker='o', markersize=2.5, linewidth=1.4)
    ax2.set_ylabel('累计占比（%）', fontsize=9, color=RED)
    ax2.tick_params(axis='y', labelcolor=RED)
    ax2.set_ylim(0, 105)
    ax2.axhline(86.6, color=GREY, linestyle=':', linewidth=1.2)
    ax2.text(30, 88, '前 3 档占 86.6%', fontsize=8.5, color='#555555')
    ax1.set_title('播放量的集中度（喜马拉雅 57 档节目）', fontsize=11, pad=10)
    for a in (ax1, ax2):
        a.spines['top'].set_visible(False)
    save(fig, '图9-播放量帕累托.png')

    # =========================================================
    # 图10 主题供需散点
    # =========================================================
    form_n = Counter(topic.values())
    plays = defaultdict(list)
    for e in h_eps:
        if e['播放量'] and e['节目名称'] in topic:
            plays[topic[e['节目名称']]].append(int(e['播放量']))
    gmed = statistics.median([v for l in plays.values() for v in l])

    pts = []
    for t, n in form_n.items():
        if t == '宗教灵性' or not plays.get(t):
            continue
        pts.append((n / len(topic) * 100,
                    statistics.median(plays[t]) / gmed, t, n))

    fig, ax = plt.subplots(figsize=(W, H))
    for x, y, t, n in pts:
        ax.scatter(x, y, s=40 + n * 22, color=BLUE, alpha=0.55, edgecolor=BLUE)
        ax.annotate(t, (x, y), textcoords='offset points', xytext=(8, 6),
                    fontsize=8.5)
    ax.axhline(1, color=RED, linestyle='--', linewidth=1.1)
    ax.text(24, 1.04, '需求 = 全局中位', fontsize=8, color=RED)
    style(ax, '主题的供给与需求（气泡大小 = 节目数）',
          '供给：节目占比（%）', '需求：单集播放中位数 / 全局中位数', grid='both')
    ax.set_xlim(0, 30)
    save(fig, '图10-供需散点.png')

    # =========================================================
    # 图11 主题分布：样本 vs 全量
    # =========================================================
    tp_all = os.path.join(ROOT, '07-分析', '主题_全量.csv')
    if os.path.exists(tp_all):
        allrows = list(csv.DictReader(open(tp_all, encoding='utf-8-sig')))
        c_all = Counter(r['主题'] for r in allrows)
        c_57 = Counter(topic.values())
        ORDER = ['语言教学', '宗教灵性', '儿童亲子', '故事虚构',
                 '影视娱乐音乐', '商业科技', '社会人文', '自我成长', '闲聊']
        a = [c_57.get(t, 0) / len(topic) * 100 for t in ORDER]
        b = [c_all.get(t, 0) / len(allrows) * 100 for t in ORDER]

        import numpy as np
        x = np.arange(len(ORDER))
        fig, ax = plt.subplots(figsize=(W, H))
        ax.bar(x - 0.2, a, 0.4, color=ORANGE, label='喜马拉雅样本（57）')
        ax.bar(x + 0.2, b, 0.4, color=BLUE, label='全部样本（374）')
        ax.set_xticks(x)
        ax.set_xticklabels(ORDER, fontsize=8, rotation=18, ha='right')
        style(ax, '主题分布：需求侧样本 vs 全样本', None, '占比（%）')
        ax.legend(frameon=False, fontsize=9)
        save(fig, '图11-主题分布对比.png')

    print(f'\n全部图表输出到：{OUT}')


if __name__ == '__main__':
    main()
