# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 作品集图表 v3
============================================================

【v3 改了什么】
  1. 换配色：扔掉默认 Office 蓝，改用一套对比更强、更有辨识度的七色盘
  2. 词云重做：用「粵」字做形状遮罩，深色底 + 高饱和配色
  3. 布局重做：所有图统一用 subplots_adjust 预留边距，
     图例一律放到绘图区外，旋转标签加 rotation_mode='anchor'，
     彻底解决坐标轴重叠、图例压数据的问题
  4. 加装饰：渐变填充、数据标签、四象限着色、参考线

【产出】04-图表/v3/ 下 15 张
============================================================
"""

import os
import sys
import csv
import re
import random
import statistics
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
import squarify

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
CLEAN = os.path.join(ROOT, '02-清洗后数据')
ANA   = os.path.join(ROOT, '07-分析')
HANA  = os.path.join(ROOT, '06-听众侧')
OUT   = os.path.join(ROOT, '04-图表', 'v3')
os.makedirs(OUT, exist_ok=True)

# ══════════════════════════════════════════════════════
#  配色：一套自定的七色盘（蓝 / 橙 / 砖红 / 绿 / 灰蓝 / 黄 / 紫）
# ══════════════════════════════════════════════════════
C = {
    'ink':   '#1A1A2E',
    'blue':  '#2E86AB',
    'orange': '#F18F01',
    'red':   '#C73E1D',
    'green': '#6BAA75',
    'steel': '#A9BCD0',
    'yellow': '#E8C547',
    'plum':  '#3B1F2B',
    'grey':  '#7A8B99',
}
PALETTE = [C['blue'], C['orange'], C['red'], C['green'],
           C['plum'], C['yellow'], C['steel'], C['grey']]

# 双色渐变（用于热力图、面积图）
GRAD_BO = LinearSegmentedColormap.from_list('bo', ['#FDF6E3', C['orange'], C['red']])
GRAD_BG = LinearSegmentedColormap.from_list('bg', ['#F7FAFC', C['steel'], C['blue'], C['ink']])

plt.rcParams.update({
    'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
    'axes.unicode_minus': False,
    'font.size': 10,
    'axes.edgecolor': '#D8DEE4',
    'axes.labelcolor': C['ink'],
    'axes.titlecolor': C['ink'],
    'xtick.color': '#5A6570',
    'ytick.color': '#5A6570',
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'figure.dpi': 200,
    'savefig.facecolor': 'white',
})

FONT = 'C:/Windows/Fonts/msyh.ttc'
FONT_B = 'C:/Windows/Fonts/msyhbd.ttc'


def title(ax, main, sub=None):
    """标题与副标题分开摆，副标题紧贴绘图区上方。"""
    ax.set_title(main, fontsize=15, fontweight='bold', color=C['ink'],
                 pad=30 if sub else 14, loc='left')
    if sub:
        ax.text(0, 1.014, sub, transform=ax.transAxes, ha='left', va='bottom',
                fontsize=9, color=C['grey'])


def tidy(ax, left=0.13, right=0.97, bottom=0.16, top=0.84):
    """统一留边，避免标签被裁掉或和图例打架。"""
    ax.figure.subplots_adjust(left=left, right=right, bottom=bottom, top=top)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=200, bbox_inches='tight',
                facecolor='white', pad_inches=0.3)
    plt.close(fig)
    print(f'  ✓ {name}')


def bare(ax, keep=('bottom',)):
    for s in ('top', 'right', 'left', 'bottom'):
        ax.spines[s].set_visible(s in keep)
    ax.tick_params(length=0)


# ══════════════════════════════════════════════════════
def main():
    progs = list(csv.DictReader(open(os.path.join(CLEAN, '节目表_粤语.csv'),
                                     encoding='utf-8-sig')))
    eps = list(csv.DictReader(open(os.path.join(CLEAN, '单集表_粤语.csv'),
                                   encoding='utf-8-sig')))
    print(f'节目 {len(progs)} / 单集 {len(eps):,}')

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

    alive = lambda n: last_ym.get(n, '') >= '2025-11'

    def plat(p):
        if p == 'Spotify/Anchor':
            return 'Spotify / Anchor'
        if p in ('SoundOn', 'Firstory'):
            return '台湾平台'
        if p in ('喜马拉雅', '小宇宙', '荔枝'):
            return p
        return '其他自建'

    # ══════════════════════════════════════════════
    # 01 平台格局 —— 环形 + 引线标注
    # ══════════════════════════════════════════════
    pc = Counter(plat(r['平台']) for r in progs)
    pa = Counter(plat(r['平台']) for r in progs if alive(r['节目名']))
    items = pc.most_common()
    labels, vals = [k for k, _ in items], [v for _, v in items]

    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    wedges, _ = ax.pie(
        vals, colors=PALETTE[:len(vals)], startangle=90, counterclock=False,
        wedgeprops=dict(width=0.40, edgecolor='white', linewidth=3))
    ax.text(0, 0.10, f'{len(progs)}', ha='center', va='center',
            fontsize=40, fontweight='bold', color=C['ink'])
    ax.text(0, -0.16, '档节目', ha='center', va='center',
            fontsize=11, color=C['grey'])

    total = sum(vals)
    for w, (name, v) in zip(wedges, items):
        ang = (w.theta2 + w.theta1) / 2
        rad = np.deg2rad(ang)
        # 小扇区（<5%）的标签挤在顶部会互相压住，把它们拨到右侧并错开高度
        small = v / total < 0.05
        if small:
            ang = ang - 26
            rad = np.deg2rad(ang)
        x, y = np.cos(rad) * 1.55, np.sin(rad) * 1.55
        if small:
            x = abs(x) + 0.55
        ha = 'left' if x >= 0 else 'right'
        ax.annotate(
            f'{name}\n{v} 档 · {pa[name] / v * 100:.0f}% 活跃',
            xy=(np.cos(np.deg2rad((w.theta2 + w.theta1) / 2)) * 0.99,
                np.sin(np.deg2rad((w.theta2 + w.theta1) / 2)) * 0.99),
            xytext=(x, y), ha=ha, va='center', fontsize=9, color=C['ink'],
            arrowprops=dict(arrowstyle='-', color='#C5CDD5', lw=1.1,
                            connectionstyle='arc3,rad=0.12'))
    ax.set_xlim(-2.35, 2.35)
    ax.set_ylim(-1.75, 1.75)
    title(ax, '粤语播客的平台格局', '外圈百分比 = 该平台近 12 个月的活跃节目占比')
    save(fig, '01-平台格局.png')

    # ══════════════════════════════════════════════
    # 02 内容形态 —— 树图
    # ══════════════════════════════════════════════
    fc = Counter(r['内容形态'] for r in progs)
    items = fc.most_common()
    names, sizes = [k for k, _ in items], [v for _, v in items]

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    cmap = LinearSegmentedColormap.from_list('t', ['#123C5A', C['blue'], '#8FC1D4', '#E8F1F5'])
    colors = [cmap(0.15 + i / max(len(sizes) - 1, 1) * 0.7) for i in range(len(sizes))]
    lab = [f'{n}\n{s}' if s >= 8 else '' for n, s in zip(names, sizes)]
    squarify.plot(sizes=sizes, label=lab, color=colors, ax=ax, pad=True,
                  text_kwargs={'fontsize': 9.5, 'color': 'white',
                               'fontweight': 'bold'})
    ax.axis('off')
    ax.set_title('内容形态的构成', fontsize=15, fontweight='bold',
                 color=C['ink'], pad=16, loc='left')
    ax.text(0, 1.02, '面积 = 节目数，共 374 档', transform=ax.transAxes,
            fontsize=9, color=C['grey'])
    save(fig, '02-内容形态.png')

    # ══════════════════════════════════════════════
    # 03 年度产出 —— 堆叠面积
    # ══════════════════════════════════════════════
    form_of = {p['节目名']: p['内容形态'] for p in progs}
    yf = defaultdict(lambda: defaultdict(int))
    for e in eps:
        y = (e['发布年月'] or '')[:4]
        if not y.isdigit() or int(y) < 2015:
            continue
        f = form_of.get(e['所属节目'])
        if f:
            yf[int(y)][f] += 1
    years = sorted(yf)
    tot = Counter()
    for y in years:
        for f, v in yf[y].items():
            tot[f] += v
    top = [f for f, _ in tot.most_common(6)]
    other = [f for f in tot if f not in top]

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ys = [[yf[y].get(f, 0) for y in years] for f in top]
    ys.append([sum(yf[y].get(f, 0) for f in other) for y in years])
    ax.stackplot(years, *ys, labels=top + ['其他'], colors=PALETTE[:7],
                 alpha=0.92, edgecolor='white', linewidth=0.8)
    ax.set_xlim(min(years), max(years))
    ax.set_ylim(0, max(sum(v) for v in zip(*ys)) * 1.3)
    ax.grid(axis='y', alpha=0.18)
    ax.set_axisbelow(True)
    bare(ax)
    ax.set_xlabel('年份', labelpad=8)
    ax.set_ylabel('新增单集数', labelpad=8)
    ax.legend(loc='upper left', bbox_to_anchor=(0.01, 1.0), frameon=False,
              fontsize=9, ncol=3, columnspacing=1.2, handlelength=1.4)
    title(ax, '内容生产的结构演化', '各形态每年新增的单集数（2015–2026）')
    tidy(ax, left=0.09, right=0.98, bottom=0.14, top=0.76)
    save(fig, '03-年度产出.png')

    # ══════════════════════════════════════════════
    # 04 形态演化 —— 强调线
    # ══════════════════════════════════════════════
    yfa = defaultdict(lambda: defaultdict(set))
    for e in eps:
        y = (e['发布年月'] or '')[:4]
        if not y.isdigit() or int(y) < 2015:
            continue
        f = form_of.get(e['所属节目'])
        if f:
            yfa[int(y)][f].add(e['所属节目'])

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    for i, f in enumerate(top):
        v = [len(yfa[y].get(f, ())) for y in years]
        lw, z = (3.2, 3) if f == top[0] else (1.6, 2)
        ax.plot(years, v, color=PALETTE[i], linewidth=lw, marker='o',
                markersize=4.5, label=f, zorder=z, alpha=1 if f == top[0] else 0.75)
        ax.annotate(f'{v[-1]}', (years[-1], v[-1]), textcoords='offset points',
                    xytext=(8, 0), fontsize=8.5, color=PALETTE[i],
                    va='center', fontweight='bold')
    ax.set_xlim(min(years), max(years) + 0.6)
    ax.grid(axis='y', alpha=0.18)
    ax.set_axisbelow(True)
    bare(ax)
    ax.set_xlabel('年份', labelpad=8)
    ax.set_ylabel('当年活跃节目数', labelpad=8)
    ax.legend(loc='upper left', bbox_to_anchor=(0.01, 1.0), frameon=False,
              fontsize=9, ncol=3, columnspacing=1.2, handlelength=1.4)
    title(ax, '各形态的活跃节目数', '一档节目只计一次，避免高产节目扭曲曲线')
    tidy(ax, left=0.09, right=0.92, bottom=0.14, top=0.76)
    save(fig, '04-形态演化.png')

    # ══════════════════════════════════════════════
    # 05 存活率 —— 棒棒糖
    # ══════════════════════════════════════════════
    sf = defaultdict(lambda: [0, 0])
    for r in progs:
        f = r['内容形态']
        sf[f][0] += 1
        if alive(r['节目名']):
            sf[f][1] += 1
    items = sorted(((k, v) for k, v in sf.items() if v[0] >= 8),
                   key=lambda x: x[1][1] / x[1][0])
    names = [k for k, _ in items]
    rates = [v[1] / v[0] * 100 for _, v in items]

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for i, rate in enumerate(rates):
        col = C['green'] if rate >= 50 else (C['orange'] if rate >= 40 else C['red'])
        ax.hlines(i, 0, rate, color=col, alpha=0.28, linewidth=4)
        ax.scatter(rate, i, s=210, color=col, zorder=3,
                   edgecolor='white', linewidth=2.4)
        ax.text(rate + 2.4, i, f'{rate:.0f}%', va='center', fontsize=10,
                fontweight='bold', color=col)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([f'{n}（{sf[n][0]}）' for n in names], fontsize=9.5)
    ax.set_xlim(0, 70)
    ax.set_ylim(-0.7, len(names) - 0.3)
    ax.grid(axis='x', alpha=0.15)
    ax.set_axisbelow(True)
    bare(ax)
    ax.set_xlabel('近 12 个月仍在更新的比例（%）', labelpad=10)
    title(ax, '谁活下来了', '颜色：≥50% 绿 · 40–50% 橙 · <40% 红；括号内为节目数')
    tidy(ax, left=0.20, right=0.95, bottom=0.16, top=0.82)
    save(fig, '05-存活率.png')

    # ══════════════════════════════════════════════
    # 06 存活 × 集数 —— 渐变面积
    # ══════════════════════════════════════════════
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
    rs = [bg[l][1] / bg[l][0] * 100 for l in labels]

    fig, ax = plt.subplots(figsize=(8.0, 4.3))
    x = np.arange(len(labels))
    ax.fill_between(x, rs, color=C['blue'], alpha=0.14)
    ax.plot(x, rs, color=C['blue'], linewidth=3.4, marker='o', markersize=10,
            markerfacecolor='white', markeredgewidth=3, zorder=3)
    for i, l in enumerate(labels):
        ax.text(i, rs[i] + 6, f'{rs[i]:.0f}%', ha='center', fontsize=12,
                fontweight='bold', color=C['ink'])
        ax.text(i, 6, f'n = {bg[l][0]}', ha='center', fontsize=8.5, color=C['grey'])
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.15)
    ax.set_axisbelow(True)
    bare(ax)
    ax.set_xlabel('节目总集数', labelpad=8)
    ax.set_ylabel('存活率（%）', labelpad=8)
    title(ax, '做得越久，越可能还在做', '存活率随节目集数单调上升')
    tidy(ax, left=0.09, right=0.97, bottom=0.14, top=0.82)
    save(fig, '06-存活-集数.png')

    # ══════════════════════════════════════════════
    # 07 集数长尾
    # ══════════════════════════════════════════════
    counts = sorted(int(r['集数'] or 0) for r in progs)
    fig, ax1 = plt.subplots(figsize=(8.0, 4.3))
    ax1.hist([c for c in counts if c <= 400], bins=50, color=C['steel'],
             edgecolor='white', linewidth=0.7)
    ax1.set_yscale('log')
    ax1.set_xlabel('节目总集数', labelpad=8)
    ax1.set_ylabel('节目数（对数）', labelpad=8)
    ax1.grid(axis='y', alpha=0.15)
    ax1.set_axisbelow(True)
    ax2 = ax1.twinx()
    ax2.plot(np.sort(counts), np.arange(1, len(counts) + 1) / len(counts) * 100,
             color=C['red'], linewidth=2.6)
    ax2.set_ylabel('累积占比（%）', color=C['red'], labelpad=8)
    ax2.tick_params(axis='y', labelcolor=C['red'])
    ax2.set_ylim(0, 105)
    for a in (ax1, ax2):
        a.spines['top'].set_visible(False)
    med = statistics.median(counts)
    ax1.axvline(med, color=C['ink'], linestyle='--', linewidth=1.6, alpha=0.7)
    ax1.annotate(f'中位 {med:.0f} 集', xy=(med, 30), xytext=(med + 45, 12),
                 fontsize=9, color=C['ink'],
                 arrowprops=dict(arrowstyle='->', color=C['ink'], lw=1.2))
    title(ax1, '极少数撑起了总量', '横轴为集数，纵轴为对数尺度；红线是累积占比')
    fig.subplots_adjust(left=0.09, right=0.90, bottom=0.14, top=0.80)
    save(fig, '07-集数长尾.png')

    # ══════════════════════════════════════════════
    # 08 时长小提琴
    # ══════════════════════════════════════════════
    dur = defaultdict(list)
    for e in eps:
        d = e['时长_秒']
        if (d or '').isdigit():
            f = form_of.get(e['所属节目'])
            if f:
                dur[f].append(int(d) / 60)
    # 只保留样本量足够的形态；「未分类」只有 3 档节目却贡献 611 集，
    # 放进来会形成一条误导性的小提琴，直接排除
    keep = sorted([f for f in dur if len(dur[f]) >= 200 and f != '未分类'],
                  key=lambda f: statistics.median(dur[f]))

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    data = [[min(x, 90) for x in dur[f]] for f in keep]
    parts = ax.violinplot(data, showmedians=True, widths=0.8, showextrema=False)
    for i, b in enumerate(parts['bodies']):
        b.set_facecolor(PALETTE[i % len(PALETTE)])
        b.set_alpha(0.7)
        b.set_edgecolor('white')
        b.set_linewidth(1.6)
    parts['cmedians'].set_color(C['ink'])
    parts['cmedians'].set_linewidth(2.2)
    ax.set_xticks(range(1, len(keep) + 1))
    ax.set_xticklabels(keep, rotation=22, ha='right', rotation_mode='anchor')
    ax.set_ylabel('单集时长（分钟，截到 90）', labelpad=8)
    ax.grid(axis='y', alpha=0.15)
    ax.set_axisbelow(True)
    bare(ax)
    title(ax, '不同形态的长度差异', '小提琴宽度 = 该时长上的集数密度')
    tidy(ax, left=0.09, right=0.98, bottom=0.30, top=0.84)
    save(fig, '08-时长分布.png')

    # ══════════════════════════════════════════════
    # 09 帕累托
    # ══════════════════════════════════════════════
    h_eps = list(csv.DictReader(open(os.path.join(HANA, '喜马拉雅单集_清洗后.csv'),
                                    encoding='utf-8-sig')))
    topic = {}
    tp = os.path.join(ANA, '内容主题_定稿.csv')
    if os.path.exists(tp):
        topic = {r['节目名']: r['主题']
                 for r in csv.DictReader(open(tp, encoding='utf-8-sig'))}
    psum = Counter()
    for e in h_eps:
        if e['播放量']:
            psum[e['节目名称']] += int(e['播放量'])
    total = sum(psum.values())
    ranked = sorted(psum.values(), reverse=True)
    cum, s = [], 0
    for v in ranked:
        s += v
        cum.append(s / total * 100)

    fig, ax1 = plt.subplots(figsize=(8.4, 4.6))
    xs = np.arange(1, len(ranked) + 1)
    cols = [C['red'] if i < 3 else C['steel'] for i in range(len(ranked))]
    ax1.bar(xs, [v / 1e4 for v in ranked], color=cols, width=0.8)
    ax1.set_xlabel('节目（按播放量降序）', labelpad=8)
    ax1.set_ylabel('播放量（万）', labelpad=8)
    ax2 = ax1.twinx()
    ax2.plot(xs, cum, color=C['orange'], linewidth=2.8)
    ax2.set_ylabel('累积占比（%）', color=C['orange'], labelpad=8)
    ax2.tick_params(axis='y', labelcolor=C['orange'])
    ax2.set_ylim(0, 108)
    ax2.axhline(86.6, color=C['ink'], linestyle=':', linewidth=1.4, alpha=0.5)
    ax2.annotate('前 3 档 = 86.6%', xy=(3, 86.6), xytext=(18, 55),
                 fontsize=10.5, fontweight='bold', color=C['ink'],
                 arrowprops=dict(arrowstyle='->', color=C['ink'], lw=1.4,
                                 connectionstyle='arc3,rad=-0.2'))
    for a in (ax1, ax2):
        a.spines['top'].set_visible(False)
    title(ax1, '赢家通吃', '57 档节目的播放量：前 3 档吃掉近九成')
    fig.subplots_adjust(left=0.09, right=0.90, bottom=0.14, top=0.82)
    save(fig, '09-播放集中度.png')

    # ══════════════════════════════════════════════
    # 10 供需象限
    # ══════════════════════════════════════════════
    form_n = Counter(topic.values())
    plays = defaultdict(list)
    for e in h_eps:
        if e['播放量'] and e['节目名称'] in topic:
            plays[topic[e['节目名称']]].append(int(e['播放量']))
    gmed = statistics.median([v for l in plays.values() for v in l])

    pts = [(n / len(topic) * 100, statistics.median(plays[t]) / gmed, t, n)
           for t, n in form_n.items() if plays.get(t)]
    xm = statistics.mean([p[0] for p in pts])

    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    ax.axhspan(1.0, 2.0, xmin=0, xmax=1, color=C['green'], alpha=0.05)
    ax.axhspan(0.0, 1.0, xmin=0, xmax=1, color=C['red'], alpha=0.04)
    ax.axhline(1.0, color=C['red'], linestyle='--', linewidth=1.5, alpha=0.75)
    ax.axvline(xm, color=C['grey'], linestyle=':', linewidth=1.2, alpha=0.7)
    for x, y, t, n in pts:
        col = C['green'] if y >= 1 else C['red']
        ax.scatter(x, y, s=90 + n * 36, color=col, alpha=0.45,
                   edgecolor=col, linewidth=2, zorder=3)
        ax.annotate(t, (x, y), textcoords='offset points',
                    xytext=(12, 9), fontsize=10, fontweight='bold',
                    color=C['ink'])
    ax.text(0.35, 1.03, '需求线 = 全局中位', fontsize=8.5, color=C['red'])
    ax.text(0.35, 1.86, '供给多 · 需求强', fontsize=10, color=C['green'],
            alpha=0.8, style='italic')
    ax.text(0.35, 0.05, '供给少 · 需求弱', fontsize=10, color=C['red'],
            alpha=0.65, style='italic')
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 2.0)
    ax.set_xlabel('供给：该主题的节目占比（%）', labelpad=10)
    ax.set_ylabel('需求：单集播放中位数 / 全局中位数', labelpad=10)
    ax.grid(alpha=0.14)
    ax.set_axisbelow(True)
    bare(ax, keep=())
    title(ax, '供给与需求的错位', '气泡越大 = 该主题的节目越多')
    tidy(ax, left=0.11, right=0.97, bottom=0.13, top=0.84)
    save(fig, '10-供需象限.png')

    # ══════════════════════════════════════════════
    # 11 样本偏差 —— 蝴蝶图
    # ══════════════════════════════════════════════
    tp_all = os.path.join(ANA, '主题_全量.csv')
    allrows = list(csv.DictReader(open(tp_all, encoding='utf-8-sig')))
    c_all = Counter(r['主题'] for r in allrows)
    c57 = Counter(topic.values())
    ORDER = ['闲聊', '故事虚构', '自我成长', '社会人文', '语言教学',
             '宗教灵性', '儿童亲子', '商业科技', '影视娱乐音乐']
    va = [c57.get(t, 0) / len(topic) * 100 for t in ORDER]
    vb = [c_all.get(t, 0) / len(allrows) * 100 for t in ORDER]

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    y = np.arange(len(ORDER))
    ax.barh(y, [-v for v in va], color=C['orange'], height=0.64, label='喜马拉雅样本（57）')
    ax.barh(y, vb, color=C['blue'], height=0.64, label='全部样本（374）')
    ax.axvline(0, color=C['ink'], linewidth=1.1)
    for i, (a, b) in enumerate(zip(va, vb)):
        if a > 0:
            ax.text(-a - 0.7, i, f'{a:.1f}', va='center', ha='right', fontsize=8.8)
        else:
            ax.text(-0.7, i, '缺失', va='center', ha='right', fontsize=8.5,
                    color=C['red'], fontweight='bold')
        ax.text(b + 0.7, i, f'{b:.1f}', va='center', ha='left', fontsize=8.8)
    ax.set_yticks(y)
    ax.set_yticklabels(ORDER, fontsize=9.5)
    ax.invert_yaxis()
    ax.set_xlim(-34, 34)
    ax.set_xticks([-30, -20, -10, 0, 10, 20, 30])
    ax.set_xticklabels(['30', '20', '10', '0', '10', '20', '30'])
    ax.set_xlabel('占比（%）', labelpad=10)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.19), frameon=False,
              fontsize=9.5, ncol=2)
    ax.grid(axis='x', alpha=0.12)
    ax.set_axisbelow(True)
    bare(ax, keep=())
    title(ax, '需求侧样本的系统性偏斜', '语言教学被高估 2.5 倍，宗教类完全缺失')
    tidy(ax, left=0.16, right=0.97, bottom=0.26, top=0.84)
    save(fig, '11-样本偏差.png')

    # ══════════════════════════════════════════════
    # 12 词云 —— 「粵」字遮罩
    # ══════════════════════════════════════════════
    import jieba
    from wordcloud import WordCloud
    from PIL import Image, ImageDraw, ImageFont

    STOP = set('粤语 粵語 广东话 廣東話 podcast 播客 节目 節目 频道 頻道 '
               '我们 你们 他们 自己 大家 一个 这个 那个 这样 那样 '
               '什么 怎么 可以 就是 但是 因为 所以 如果 虽然 今天 明天 昨天 '
               '现在 时候 时间 一下 一起 一样 分享 聊聊 谈谈 说说 欢迎 订阅 '
               '收听 关注 支持 本集 今集 一集 最新 更新 全集 完整版 系列 '
               '两个 三个 这么 那么 还是 已经 知道 觉得 喜欢 真的 很多 '
               '第一 第二 第三 一次 一种 一天 一位 之间 之后 之前 '
               '不是 应该 一切 真正 可能 到底 原来 今日 没有 必须 当然 '
               '其实 问题 事情 东西 地方 感觉 需要 开始 最后 现在'.split())
    NAMES = set('陈老 燕城 梁燕城 宇婷 车理 洛宾 河马 玛利奥 癫台 '
                '温哥华 多伦多 九点半 晚间新闻 sbs ont'.split())

    texts = [(e['单集标题'] or '').strip() for e in eps]
    texts = [t for t in texts if t]
    random.seed(42)
    sample = random.sample(texts, min(40000, len(texts)))
    words = []
    for t in sample:
        for w in jieba.lcut(t):
            w = w.strip()
            if len(w) < 2 or w.isdigit():
                continue
            if not re.search(r'[一-鿿]', w):
                continue
            if w in STOP or w.lower() in NAMES:
                continue
            words.append(w)
    freq = Counter(words)

    # 麦克风剪影遮罩：白底 → 画黑色形状 → 黑色区域才允许填词
    # （「粵」字笔画太密，填满后看不出字形，所以改用图形）
    # 画布用竖版，让麦克风撑满，不留大片空白
    S_W, S_H = 1180, 1480
    mask_img = Image.new('L', (S_W, S_H), 255)
    d = ImageDraw.Draw(mask_img)
    cx = S_W // 2
    # 话筒头（竖长胶囊）
    d.rounded_rectangle([cx - 245, 55, cx + 245, 790], radius=245, fill=0)
    # 托架（半圆环）
    d.arc([cx - 415, 380, cx + 415, 1105], start=0, end=180, fill=0, width=88)
    # 立杆
    d.rectangle([cx - 42, 1085, cx + 42, 1285], fill=0)
    # 底座
    d.rounded_rectangle([cx - 315, 1285, cx + 315, 1395], radius=52, fill=0)
    mask = np.array(mask_img)

    VIVID = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#F7FFF7',
             '#A8E6CF', '#FFD3B6', '#95E1D3', '#F38181', '#AA96DA']

    def color_func(word, font_size, position, orientation, random_state=None, **kw):
        return random.choice(VIVID)

    wc = WordCloud(font_path=FONT, mask=mask, background_color='#0B1A2B',
                   max_words=170, prefer_horizontal=0.84,
                   relative_scaling=0.34, min_font_size=10,
                   max_font_size=230, collocations=False,
                   color_func=color_func, contour_width=0,
                   margin=3).generate_from_frequencies(freq)

    fig, ax = plt.subplots(figsize=(6.6, 8.3))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    fig.text(0.5, 0.962, '粤语播客在讲什么', ha='center', fontsize=19,
             fontweight='bold', color='#F7FFF7')
    fig.text(0.5, 0.035, '46,721 条单集标题的词频', ha='center', fontsize=9.5,
             color='#8FA6BA')
    fig.patch.set_facecolor('#0B1A2B')
    ax.set_facecolor('#0B1A2B')
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.055, top=0.945)
    fig.savefig(os.path.join(OUT, '12-词云.png'), dpi=200,
                facecolor='#0B1A2B', bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print('  ✓ 12-词云.png')

    # ══════════════════════════════════════════════
    # 13 热力图
    # ══════════════════════════════════════════════
    plats = ['Spotify / Anchor', '台湾平台', '其他自建', '喜马拉雅', '小宇宙', '荔枝']
    ORD2 = ['语言教学', '社会人文', '自我成长', '商业科技', '故事虚构',
            '影视娱乐音乐', '儿童亲子', '宗教灵性', '闲聊']
    m = defaultdict(int)
    prof = {r['节目名']: r for r in progs}
    for r in allrows:
        p = prof.get(r['节目名'])
        if p:
            m[(r['主题'], plat(p['平台']))] += 1
    M = np.array([[m.get((t, p), 0) for p in plats] for t in ORD2], dtype=float)
    Mn = M / np.maximum(M.sum(axis=0, keepdims=True), 1) * 100

    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    im = ax.imshow(Mn, cmap=GRAD_BO, aspect='auto', vmin=0, vmax=65)
    ax.set_xticks(range(len(plats)))
    ax.set_xticklabels(plats, rotation=20, ha='right', rotation_mode='anchor',
                       fontsize=9.5)
    ax.set_yticks(range(len(ORD2)))
    ax.set_yticklabels(ORD2, fontsize=9.5)
    ax.set_xticks(np.arange(-.5, len(plats), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(ORD2), 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=2.4)
    ax.tick_params(which='minor', length=0)
    for i in range(len(ORD2)):
        for j in range(len(plats)):
            v = Mn[i, j]
            ax.text(j, i, f'{v:.0f}' if v > 0 else '·', ha='center', va='center',
                    fontsize=9.5, fontweight='bold',
                    color='white' if v > 26 else C['ink'])
    cb = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    cb.set_label('该平台内占比（%）', fontsize=9)
    cb.outline.set_visible(False)
    ax.set_title('各平台的选题偏好', fontsize=15, fontweight='bold',
                 color=C['ink'], pad=16, loc='left')
    ax.text(0, 1.025, '每列 = 一个平台，格子数字是该主题在本平台节目中的占比',
            transform=ax.transAxes, fontsize=9, color=C['grey'])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    fig.subplots_adjust(left=0.18, right=0.93, bottom=0.22, top=0.86)
    save(fig, '13-主题平台热力.png')

    # ══════════════════════════════════════════════
    # 14 雷达
    # ══════════════════════════════════════════════
    dims = ['平均集数', '平均时长', '存活率', '节目数量']
    radar = []
    for f in top:
        n = sf[f][0]
        radar.append([
            sum(int(p['集数'] or 0) for p in progs if p['内容形态'] == f) / n,
            statistics.mean(dur.get(f) or [0]),
            sf[f][1] / n * 100,
            n,
        ])
    radar = np.array(radar, dtype=float)
    lo, hi = radar.min(axis=0), radar.max(axis=0)
    norm = (radar - lo) / np.maximum(hi - lo, 1e-9) * 0.82 + 0.18

    ang = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    ang += ang[:1]
    fig = plt.figure(figsize=(7.4, 6.2))
    ax = fig.add_subplot(111, polar=True)
    for i, f in enumerate(top[:5]):
        v = norm[i].tolist() + [norm[i][0]]
        ax.plot(ang, v, linewidth=2.4, color=PALETTE[i], label=f, zorder=3)
        ax.fill(ang, v, color=PALETTE[i], alpha=0.07)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(dims, fontsize=11, fontweight='bold', color=C['ink'])
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['', '', '', '', ''])
    ax.set_ylim(0, 1.10)
    ax.grid(alpha=0.22)
    ax.spines['polar'].set_color('#DDE3E8')
    fig.legend(loc='lower center', bbox_to_anchor=(0.5, 0.02), ncol=5,
               frameon=False, fontsize=9.5)
    fig.text(0.5, 0.935, '五大形态的画像对比', ha='center', fontsize=15,
             fontweight='bold', color=C['ink'])
    fig.text(0.5, 0.900, '四个维度各自归一化后横向比较，绝对值见正文第四章',
             ha='center', fontsize=9, color=C['grey'])
    fig.subplots_adjust(left=0.12, right=0.88, bottom=0.14, top=0.86)
    save(fig, '14-形态雷达.png')

    # ══════════════════════════════════════════════
    # 15 箱线图
    # ══════════════════════════════════════════════
    order15 = sorted([t for t in plays if len(plays[t]) >= 20],
                     key=lambda t: -statistics.median(plays[t]))
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    data = [[min(v, 80000) for v in plays[t]] for t in order15]
    bp = ax.boxplot(data, patch_artist=True, widths=0.62, showfliers=False,
                    medianprops=dict(color=C['ink'], linewidth=2.4),
                    whiskerprops=dict(color='#B0BAC4'),
                    capprops=dict(color='#B0BAC4'))
    for i, b in enumerate(bp['boxes']):
        b.set_facecolor(PALETTE[i % len(PALETTE)])
        b.set_alpha(0.72)
        b.set_edgecolor('white')
        b.set_linewidth(1.4)
    ax.set_xticks(range(1, len(order15) + 1))
    ax.set_xticklabels(order15, rotation=22, ha='right', rotation_mode='anchor')
    ax.set_ylabel('单集播放量（截到 8 万）', labelpad=8)
    ax.set_yscale('symlog', linthresh=1000)
    ax.grid(axis='y', alpha=0.15)
    ax.set_axisbelow(True)
    bare(ax)
    title(ax, '各主题的单集播放分布', '箱体为四分位区间，中位线标黑')
    tidy(ax, left=0.10, right=0.98, bottom=0.30, top=0.84)
    save(fig, '15-主题播放箱线.png')

    print(f'\n全部输出：{OUT}')


if __name__ == '__main__':
    main()
