# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 作品集版图表  （15 张）
============================================================

【和 13 那版的区别】
  13 是"能看懂就行"的学术图：灰白底、细线、克制。
  这版是"放进作品集"的图：统一配色、粗线条、大字号、多点设计。

【产出】04-图表/v2/ 下 15 张

  01 平台格局        环形图
  02 内容形态        树图
  03 年度产出        堆叠面积
  04 形态演化        河流图
  05 存活率          棒棒糖
  06 存活×集数       渐变面积
  07 集数长尾        对数直方 + 累积
  08 时长分布        小提琴图
  09 播放集中度      帕累托
  10 供需象限        四象限散点
  11 样本偏差        蝴蝶图
  12 标题词云        词云
  13 主题×平台       热力图
  14 形态画像        雷达图
  15 主题播放分布     箱线图

【怎么运行】
      python 15-作品集图表.py
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

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import LinearSegmentedColormap
import squarify

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
CLEAN = os.path.join(ROOT, '02-清洗后数据')
ANA   = os.path.join(ROOT, '07-分析')
HANA  = os.path.join(ROOT, '06-听众侧')
OUT   = os.path.join(ROOT, '04-图表', 'v2')
os.makedirs(OUT, exist_ok=True)

# ── 统一视觉 ──────────────────────────────────────────────
C_DARK  = '#16365c'
C_MAIN  = '#2e75b6'
C_LIGHT = '#9dc3e6'
C_PALE  = '#dbe9f6'
C_ACC   = '#e8833a'
C_RED   = '#c00000'
C_GREEN = '#548235'
C_GREY  = '#8c8c8c'

PALETTE = [C_MAIN, C_ACC, C_GREEN, C_RED, '#7030a0', '#00b0f0',
           '#ffc000', '#a5a5a5', '#4472c4', '#ed7d31', '#70ad47']

plt.rcParams.update({
    'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
    'axes.unicode_minus': False,
    'font.size': 10,
    'axes.edgecolor': '#d0d0d0',
    'axes.labelcolor': '#333333',
    'xtick.color': '#555555',
    'ytick.color': '#555555',
    'figure.dpi': 200,
    'savefig.facecolor': 'white',
})

FONT_PATH = 'C:/Windows/Fonts/msyh.ttc'


def clean_axes(ax, keep=('left', 'bottom')):
    for s in ('top', 'right', 'left', 'bottom'):
        ax.spines[s].set_visible(s in keep)
    ax.grid(axis='y', alpha=0.15, linewidth=0.8, color='#999999')
    ax.set_axisbelow(True)


def title(ax, main, sub=None):
    """标题 + 副标题。pad 给够，否则两行会叠在一起。"""
    ax.set_title(main, fontsize=14, fontweight='bold', color=C_DARK,
                 pad=32 if sub else 16)
    if sub:
        ax.text(0.5, 1.018, sub, transform=ax.transAxes, ha='center',
                va='bottom', fontsize=9, color='#777777')


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=200, bbox_inches='tight',
                facecolor='white', pad_inches=0.25)
    plt.close(fig)
    print(f'  ✓ {name}')


# ============================================================
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

    def alive(n):
        return last_ym.get(n, '') >= '2025-11'

    # ── 01 平台格局 环形图 ────────────────────────────────
    def plat(p):
        if p == 'Spotify/Anchor':
            return 'Spotify / Anchor'
        if p in ('SoundOn', 'Firstory'):
            return '台湾平台'
        if p in ('喜马拉雅', '小宇宙', '荔枝'):
            return p
        return '其他自建'

    pc = Counter(plat(r['平台']) for r in progs)
    items = pc.most_common()
    labels = [k for k, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    wedges, _, autot = ax.pie(
        vals, colors=PALETTE[:len(vals)], startangle=95,
        wedgeprops=dict(width=0.42, edgecolor='white', linewidth=2.5),
        autopct=lambda p: f'{p:.1f}%', pctdistance=0.79,
        textprops=dict(fontsize=9, color='white', fontweight='bold'))
    ax.text(0, 0.08, f'{len(progs)}', ha='center', va='center',
            fontsize=34, fontweight='bold', color=C_DARK)
    ax.text(0, -0.14, '档节目', ha='center', va='center',
            fontsize=11, color='#666666')
    ax.legend(wedges, [f'{k}  {v}' for k, v in items],
              loc='center left', bbox_to_anchor=(1.0, 0.5),
              frameon=False, fontsize=9.5)
    title(ax, '粤语播客的平台格局', '按节目数量占比（N = 374）')
    save(fig, '01-平台格局.png')

    # ── 02 内容形态 树图 ─────────────────────────────────
    fc = Counter(r['内容形态'] for r in progs)
    items = fc.most_common()
    names = [k for k, _ in items]
    sizes = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    cmap = LinearSegmentedColormap.from_list('b', [C_DARK, C_MAIN, C_LIGHT, C_PALE])
    colors = [cmap(i / max(len(sizes) - 1, 1) * 0.85) for i in range(len(sizes))]
    # 小块放不下两行字，只给 8 以上的块加标签
    lab = [f'{n}\n{s}' if s >= 8 else '' for n, s in zip(names, sizes)]
    squarify.plot(sizes=sizes, label=lab,
                  color=colors, ax=ax, pad=True,
                  text_kwargs={'fontsize': 9, 'color': 'white', 'fontweight': 'bold'})
    ax.axis('off')
    ax.set_title('内容形态的构成', fontsize=14, fontweight='bold',
                 color=C_DARK, pad=16)
    save(fig, '02-内容形态.png')

    # ── 03 年度产出 堆叠面积 ─────────────────────────────
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
    totals = Counter()
    for y in years:
        for f, v in yf[y].items():
            totals[f] += v
    top = [f for f, _ in totals.most_common(6)]
    other = [f for f in totals if f not in top]

    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    ys = [[yf[y].get(f, 0) for y in years] for f in top]
    ys.append([sum(yf[y].get(f, 0) for f in other) for y in years])
    ax.stackplot(years, *ys, labels=top + ['其他'], colors=PALETTE[:7], alpha=0.88,
                 edgecolor='white', linewidth=0.6)
    ax.set_xlim(min(years), max(years))
    ax.legend(loc='upper left', frameon=False, fontsize=9, ncol=2)
    clean_axes(ax)
    ax.set_xlabel('年份')
    ax.set_ylabel('新增单集数')
    title(ax, '内容生产的结构演化', '各形态每年新增单集（2015–2026）')
    save(fig, '03-年度产出.png')

    # ── 04 形态演化 河流图 ───────────────────────────────
    yfa = defaultdict(lambda: defaultdict(set))
    for e in eps:
        y = (e['发布年月'] or '')[:4]
        if not y.isdigit() or int(y) < 2015:
            continue
        f = form_of.get(e['所属节目'])
        if f:
            yfa[int(y)][f].add(e['所属节目'])

    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    data = [[len(yfa[y].get(f, ())) for y in years] for f in top]
    data.append([len(set().union(*[yfa[y].get(f, set()) for f in other])) for y in years])
    ax.stackplot(years, *data, labels=top + ['其他'], colors=PALETTE[:7], alpha=0.9)
    ax.legend(loc='upper left', frameon=False, fontsize=9, ncol=2)
    clean_axes(ax)
    ax.set_xlabel('年份')
    ax.set_ylabel('当年活跃节目数')
    title(ax, '各形态的活跃节目数', '一档节目只计一次，避免高产节目扭曲曲线')
    save(fig, '04-形态演化.png')

    # ── 05 存活率 棒棒糖 ─────────────────────────────────
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

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    yy = np.arange(len(names))
    for i, (name, rate) in enumerate(zip(names, rates)):
        col = C_GREEN if rate >= 50 else (C_ACC if rate >= 40 else C_RED)
        ax.hlines(i, 0, rate, color=col, alpha=0.35, linewidth=3)
        ax.scatter(rate, i, s=180, color=col, zorder=3, edgecolor='white', linewidth=2)
        ax.text(rate + 2.2, i, f'{rate:.0f}%', va='center', fontsize=9.5,
                fontweight='bold', color=col)
    ax.set_yticks(yy)
    ax.set_yticklabels([f'{n}（n={sf[n][0]}）' for n in names])
    ax.set_xlim(0, 72)
    clean_axes(ax, keep=('bottom',))
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.set_xlabel('近 12 个月仍在更新的比例')
    title(ax, '谁活下来了', '各内容形态的存活率')
    save(fig, '05-存活率.png')

    # ── 06 存活 × 集数 渐变面积 ──────────────────────────
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

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    x = np.arange(len(labels))
    ax.fill_between(x, rs, color=C_MAIN, alpha=0.18)
    ax.plot(x, rs, color=C_MAIN, linewidth=3, marker='o', markersize=9,
            markerfacecolor='white', markeredgewidth=2.5)
    for i, l in enumerate(labels):
        ax.text(i, rs[i] + 4.5, f'{rs[i]:.0f}%', ha='center', fontsize=11,
                fontweight='bold', color=C_DARK)
        ax.text(i, 5, f'n={bg[l][0]}', ha='center', fontsize=8.5, color='#888888')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 95)
    clean_axes(ax)
    ax.set_xlabel('节目总集数')
    ax.set_ylabel('存活率（%）')
    title(ax, '做得越久，越可能还在做', '存活率随节目集数单调上升')
    save(fig, '06-存活-集数.png')

    # ── 07 集数长尾 ─────────────────────────────────────
    counts = sorted(int(r['集数'] or 0) for r in progs)
    fig, ax1 = plt.subplots(figsize=(7.4, 4.2))
    ax1.hist([c for c in counts if c <= 400], bins=48, color=C_LIGHT,
             edgecolor='white', linewidth=0.6)
    ax1.set_xlabel('节目总集数')
    ax1.set_ylabel('节目数')
    ax1.set_yscale('log')
    ax1.grid(axis='y', alpha=0.15)
    ax1.set_axisbelow(True)
    ax2 = ax1.twinx()
    cn = np.sort(counts)
    ax2.plot(cn, np.arange(1, len(cn) + 1) / len(cn) * 100,
             color=C_ACC, linewidth=2.4, label='累积占比')
    ax2.set_ylabel('累积占比（%）', color=C_ACC)
    ax2.tick_params(axis='y', labelcolor=C_ACC)
    ax2.set_ylim(0, 105)
    ax2.spines['top'].set_visible(False)
    ax1.spines['top'].set_visible(False)
    ax1.axvline(statistics.median(counts), color=C_RED, linestyle='--', linewidth=1.6)
    ax1.text(statistics.median(counts) + 6, ax1.get_ylim()[1] * 0.4,
             f'中位 {statistics.median(counts):.0f} 集', color=C_RED, fontsize=9)
    title(ax1, '极少数撑起了总量', '节目集数的长尾结构（含累积曲线）')
    save(fig, '07-集数长尾.png')

    # ── 08 时长 小提琴图 ─────────────────────────────────
    dur = defaultdict(list)
    for e in eps:
        d = e['时长_秒']
        if (d or '').isdigit():
            f = form_of.get(e['所属节目'])
            if f:
                dur[f].append(int(d) / 60)
    keep = [f for f in dur if len(dur[f]) >= 200]
    keep.sort(key=lambda f: statistics.median(dur[f]))

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    data = [[min(x, 90) for x in dur[f]] for f in keep]
    parts = ax.violinplot(data, showmedians=True, widths=0.78, showextrema=False)
    for i, pc_ in enumerate(parts['bodies']):
        pc_.set_facecolor(PALETTE[i % len(PALETTE)])
        pc_.set_alpha(0.65)
        pc_.set_edgecolor('white')
        pc_.set_linewidth(1.5)
    parts['cmedians'].set_color(C_DARK)
    parts['cmedians'].set_linewidth(2)
    ax.set_xticks(range(1, len(keep) + 1))
    ax.set_xticklabels(keep, rotation=20, ha='right', fontsize=9)
    ax.set_ylabel('单集时长（分钟，截到 90）')
    clean_axes(ax)
    title(ax, '不同形态的长度差异', '小提琴图：宽度表示该时长上的集数密度')
    save(fig, '08-时长分布.png')

    # ── 09 播放集中度 帕累托 ─────────────────────────────
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
    tot = sum(psum.values())
    ranked = sorted(psum.values(), reverse=True)
    cum, s = [], 0
    for v in ranked:
        s += v
        cum.append(s / tot * 100)

    fig, ax1 = plt.subplots(figsize=(7.6, 4.4))
    xs = np.arange(1, len(ranked) + 1)
    cols = [C_RED if i < 3 else C_LIGHT for i in range(len(ranked))]
    ax1.bar(xs, [v / 1e4 for v in ranked], color=cols, width=0.78)
    ax1.set_xlabel('节目（按播放量降序）')
    ax1.set_ylabel('播放量（万）')
    ax2 = ax1.twinx()
    ax2.plot(xs, cum, color=C_ACC, linewidth=2.6, marker='o', markersize=2.5)
    ax2.set_ylabel('累积占比（%）', color=C_ACC)
    ax2.tick_params(axis='y', labelcolor=C_ACC)
    ax2.set_ylim(0, 105)
    ax2.axhline(86.6, color=C_GREY, linestyle=':', linewidth=1.4)
    ax2.annotate('前 3 档 = 86.6%', xy=(3, 86.6), xytext=(14, 62),
                 fontsize=10, color=C_DARK, fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color=C_DARK, lw=1.3))
    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    title(ax1, '赢家通吃', '喜马拉雅 57 档节目的播放量分布')
    save(fig, '09-播放集中度.png')

    # ── 10 供需四象限 ───────────────────────────────────
    form_n = Counter(topic.values())
    plays = defaultdict(list)
    for e in h_eps:
        if e['播放量'] and e['节目名称'] in topic:
            plays[topic[e['节目名称']]].append(int(e['播放量']))
    gmed = statistics.median([v for l in plays.values() for v in l])

    pts = []
    for t, n in form_n.items():
        if not plays.get(t):
            continue
        pts.append((n / len(topic) * 100, statistics.median(plays[t]) / gmed, t, n))

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    xm = statistics.mean([p[0] for p in pts])
    ym = 1.0
    ax.axvspan(xm, 32, ymin=0, ymax=1, color=C_GREEN, alpha=0.06)
    ax.axhline(ym, color=C_RED, linestyle='--', linewidth=1.4, alpha=0.7)
    ax.axvline(xm, color=C_GREY, linestyle=':', linewidth=1.2)
    for x, y, t, n in pts:
        col = C_GREEN if y >= ym else C_RED
        ax.scatter(x, y, s=60 + n * 30, color=col, alpha=0.55,
                   edgecolor=col, linewidth=1.5, zorder=3)
        ax.annotate(t, (x, y), textcoords='offset points', xytext=(10, 7),
                    fontsize=9.5, fontweight='bold', color=C_DARK)
    ax.text(29, 1.03, '需求 = 全局中位', ha='right', fontsize=8.5, color=C_RED)
    ax.text(29, 0.08, '供给多 · 需求弱', ha='right', fontsize=9,
            color=C_RED, alpha=0.6, style='italic')
    ax.text(xm + 0.6, 1.72, '供给多 · 需求强', fontsize=9,
            color=C_GREEN, alpha=0.75, style='italic')
    ax.set_xlim(0, 31)
    ax.set_xlabel('供给：该主题的节目占比（%）')
    ax.set_ylabel('需求：单集播放中位数 / 全局中位数')
    ax.grid(alpha=0.12)
    ax.set_axisbelow(True)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
    title(ax, '供给与需求的错位', '气泡大小 = 该主题的节目数')
    save(fig, '10-供需象限.png')

    # ── 11 样本偏差 蝴蝶图 ──────────────────────────────
    tp_all = os.path.join(ANA, '主题_全量.csv')
    if os.path.exists(tp_all):
        allrows = list(csv.DictReader(open(tp_all, encoding='utf-8-sig')))
        c_all = Counter(r['主题'] for r in allrows)
        c_57 = Counter(topic.values())
        ORDER = ['闲聊', '故事虚构', '自我成长', '社会人文', '语言教学',
                 '宗教灵性', '儿童亲子', '商业科技', '影视娱乐音乐']
        va = [c_57.get(t, 0) / len(topic) * 100 for t in ORDER]
        vb = [c_all.get(t, 0) / len(allrows) * 100 for t in ORDER]

        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        y = np.arange(len(ORDER))
        ax.barh(y, [-v for v in va], color=C_ACC, alpha=0.9, height=0.62,
                label='喜马拉雅样本（57）')
        ax.barh(y, vb, color=C_MAIN, alpha=0.9, height=0.62,
                label='全部样本（374）')
        ax.axvline(0, color='#333333', linewidth=1)
        for i, (a, b) in enumerate(zip(va, vb)):
            if a > 0:
                ax.text(-a - 0.6, i, f'{a:.1f}', va='center', ha='right', fontsize=8.5)
            ax.text(b + 0.6, i, f'{b:.1f}', va='center', ha='left', fontsize=8.5)
            if a == 0:
                ax.text(-0.6, i, '0', va='center', ha='right',
                        fontsize=8.5, color=C_RED, fontweight='bold')
        ax.set_yticks(y)
        ax.set_yticklabels(ORDER)
        ax.invert_yaxis()
        ax.set_xlim(-32, 32)
        ax.set_xticks([-30, -20, -10, 0, 10, 20, 30])
        ax.set_xticklabels(['30', '20', '10', '0', '10', '20', '30'])
        ax.set_xlabel('占比（%）')
        ax.legend(frameon=False, fontsize=9, loc='lower right')
        ax.grid(axis='x', alpha=0.12)
        ax.set_axisbelow(True)
        for sp in ('top', 'right', 'left'):
            ax.spines[sp].set_visible(False)
        ax.tick_params(axis='y', length=0)
        title(ax, '需求侧样本的系统性偏斜',
              '语言教学被高估 2.5 倍，宗教类完全缺失')
        save(fig, '11-样本偏差.png')

    # ── 12 词云 ────────────────────────────────────────
    import jieba
    from wordcloud import WordCloud

    import re as _re
    import random

    STOP = set('粤语 粵語 广东话 廣東話 podcast 播客 节目 節目 频道 頻道 '
               '我们 你们 他们 自己 大家 一个 这个 那个 这样 那样 '
               '什么 怎么 可以 就是 但是 因为 所以 如果 虽然 今天 明天 昨天 '
               '现在 时候 时间 一下 一起 一样 分享 聊聊 谈谈 说说 欢迎 订阅 '
               '收听 关注 支持 本集 今集 一集 最新 更新 全集 完整版 系列 '
               '两个 三个 这么 那么 还是 已经 知道 觉得 喜欢 真的 很多 '
               '第一 第二 第三 一次 一种 一天 一位 之间 之后 之前 '
               '不是 应该 一切 真正 可能 到底 原来 今日 没有 必须 当然 '
               '其实 问题 事情 东西 地方 感觉 需要 开始 最后 现在'.split())

    # 主持人 / 台名：在语料里出现频率极高，但对"讲什么"没有信息量
    NAME_STOP = set('陈老 燕城 梁燕城 宇婷 车理 洛宾 河马 玛利奥 癫台 '
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
            # ★ 必须含汉字：否则英文虚词（One / Talk / of / and）会把词云占满
            if not _re.search(r'[一-鿿]', w):
                continue
            if w in STOP or w.lower() in NAME_STOP:
                continue
            words.append(w)
    freq = Counter(words)

    wc = WordCloud(font_path=FONT_PATH, width=1800, height=1000,
                   background_color='white', max_words=160,
                   colormap='Blues', prefer_horizontal=0.95,
                   relative_scaling=0.38, min_font_size=12,
                   collocations=False,
                   contour_width=0).generate_from_frequencies(freq)
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('粤语播客在讲什么', fontsize=16, fontweight='bold',
                 color=C_DARK, pad=14)
    ax.text(0.5, -0.03, '基于 46,721 条单集标题的词频（前 180 词）',
            transform=ax.transAxes, ha='center', fontsize=9, color='#777777')
    save(fig, '12-词云.png')

    # ── 13 主题 × 平台 热力图 ───────────────────────────
    if os.path.exists(tp_all):
        # 注意：必须和 plat() 的返回值逐字一致（plat 返回的是带空格的 'Spotify / Anchor'）
        plats = ['Spotify / Anchor', '台湾平台', '其他自建', '喜马拉雅', '小宇宙', '荔枝']
        ORD2 = ['语言教学', '社会理想' if False else '社会人文', '自我成长', '商业科技',
                '故事虚构', '影视娱乐音乐', '儿童亲子', '宗教灵性', '闲聊']
        m = defaultdict(int)
        prof = {r['节目名']: r for r in progs}
        for r in allrows:
            p = prof.get(r['节目名'])
            if p:
                m[(r['主题'], plat(p['平台']))] += 1
        M = np.array([[m.get((t, p), 0) for p in plats] for t in ORD2], dtype=float)
        Mn = M / np.maximum(M.sum(axis=0, keepdims=True), 1) * 100

        fig, ax = plt.subplots(figsize=(7.8, 4.8))
        im = ax.imshow(Mn, cmap='YlGnBu', aspect='auto', vmin=0, vmax=65)
        ax.set_xticks(range(len(plats)))
        ax.set_xticklabels(plats, rotation=18, ha='right', fontsize=9)
        ax.set_yticks(range(len(ORD2)))
        ax.set_yticklabels(ORD2, fontsize=9)
        # 白色网格线：否则低值格子（浅黄）里数字看不清
        ax.set_xticks(np.arange(-.5, len(plats), 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(ORD2), 1), minor=True)
        ax.grid(which='minor', color='white', linewidth=2)
        ax.tick_params(which='minor', length=0)
        for i in range(len(ORD2)):
            for j in range(len(plats)):
                v = Mn[i, j]
                ax.text(j, i, f'{v:.0f}' if v > 0 else '—',
                        ha='center', va='center', fontsize=9,
                        fontweight='bold',
                        color='white' if v > 18 else '#333333')
        cb = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cb.set_label('该平台内占比（%）', fontsize=8.5)
        ax.set_title('各平台的选题偏好', fontsize=14, fontweight='bold',
                     color=C_DARK, pad=14)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(length=0)
        save(fig, '13-主题平台热力.png')

    # ── 14 形态画像 雷达图 ───────────────────────────────
    dims = ['平均集数', '平均时长', '存活率', '节目数量']
    radar = []
    mx = {}
    for f in top:
        n = sf[f][0]
        mx.setdefault('平均集数', []).append(sum(int(p['集数'] or 0) for p in progs
                                            if p['内容形态'] == f) / n)
        d = dur.get(f) or [0]
        mx.setdefault('平均时长', []).append(statistics.mean(d))
        mx.setdefault('存活率', []).append(sf[f][1] / n * 100)
        mx.setdefault('节目数量', []).append(n)
    for f in top:
        radar.append([
            sum(int(p['集数'] or 0) for p in progs if p['内容形态'] == f) / sf[f][0],
            statistics.mean(dur.get(f) or [0]),
            sf[f][1] / sf[f][0] * 100,
            sf[f][0],
        ])
    radar = np.array(radar, dtype=float)
    # 每个维度各自归一化到 [0.15, 1.0]：
    #   除以最大值会让「最大值那个顶点」全部顶到 1，差异被压平；
    #   留 0.15 的下限，避免某个维度的最小值塌到圆心。
    lo = radar.min(axis=0)
    hi = radar.max(axis=0)
    norm = (radar - lo) / np.maximum(hi - lo, 1e-9) * 0.85 + 0.15

    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(6.8, 5.6), subplot_kw=dict(polar=True))
    # 只画前 5 个，6 条线以上就看不清了
    for i, f in enumerate(top[:5]):
        v = norm[i].tolist() + [norm[i][0]]
        ax.plot(angles, v, linewidth=2.2, color=PALETTE[i], label=f)
        ax.fill(angles, v, color=PALETTE[i], alpha=0.08)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims, fontsize=10.5, fontweight='bold', color='#333333')
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['', '', '', '', ''])
    ax.set_ylim(0, 1.08)
    ax.grid(alpha=0.25)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22),
              frameon=False, fontsize=9.5, ncol=5)
    ax.set_title('五大形态的画像对比', fontsize=14, fontweight='bold',
                 color=C_DARK, pad=46)
    save(fig, '14-形态雷达.png')

    # ── 15 主题播放 箱线图 ───────────────────────────────
    order15 = sorted([t for t in plays if len(plays[t]) >= 20],
                     key=lambda t: -statistics.median(plays[t]))
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    data = [[min(v, 80000) for v in plays[t]] for t in order15]
    bp = ax.boxplot(data, patch_artist=True, widths=0.62,
                    showfliers=False, medianprops=dict(color=C_DARK, linewidth=2))
    for i, box in enumerate(bp['boxes']):
        box.set_facecolor(PALETTE[i % len(PALETTE)])
        box.set_alpha(0.65)
        box.set_edgecolor('white')
    ax.set_xticks(range(1, len(order15) + 1))
    ax.set_xticklabels(order15, rotation=18, ha='right', fontsize=9)
    ax.set_ylabel('单集播放量（截到 8 万）')
    ax.set_yscale('symlog', linthresh=1000)
    clean_axes(ax)
    title(ax, '各主题的单集播放分布', '箱体为四分位区间，中位线标黑')
    save(fig, '15-主题播放箱线.png')

    print(f'\n全部输出：{OUT}')


if __name__ == '__main__':
    main()
