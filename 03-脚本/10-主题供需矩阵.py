# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 主题供需矩阵  （第 1 版）
============================================================

【和 07 那版的区别】
  07 用的是「形式」（谈话/朗读/教学），是「怎么讲」。
  这一版用「主题」（语言教学/社会人文/故事虚构…），是「讲什么」。

  行业报告（小宇宙 19 类、CPA 19 类、嘉世 6 类）用的全是主题。
  换成主题之后，才能和行业数据对照，也才能回答
  「听众想听什么」vs「节目在讲什么」。

【核心指标】
  供给 = 该主题占了多少节目 / 多少集
  需求 = 该主题的单集播放中位数，相对全局的倍数

  为什么用中位数不用总量：
    播放量极度集中，Top3 节目占了 86.6%。
    用总量算出来的是「这个主题里有没有爆款」，
    用中位数算的才是「这个主题的典型一集有多少人听」。

【两套口径】
  A 全量   —— 13,595 集全部
  B 近12月 —— 只算 2025-11 之后（样本小，作稳健性检验）

【怎么运行】
      python 10-主题供需矩阵.py
"""

import os
import sys
import csv
import statistics
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.join(HERE, '..')
OUTDIR = os.path.join(ROOT, '07-分析')
CLEAN  = os.path.join(ROOT, '06-听众侧')

CUTOFF_B = '2025-11'

ORDER = ['语言教学', '社会人文', '自我成长', '商业科技',
         '故事虚构', '影视娱乐音乐', '儿童亲子', '宗教灵性', '闲聊']


def main():
    # ---------- 读主题标签 ----------
    topic = {}
    for r in csv.DictReader(open(os.path.join(OUTDIR, '内容主题_定稿.csv'),
                                 encoding='utf-8-sig')):
        topic[r['节目名']] = r['主题']
    print(f'节目：{len(topic)}')

    # ---------- 读单集 ----------
    eps = list(csv.DictReader(open(os.path.join(CLEAN, '喜马拉雅单集_清洗后.csv'),
                                  encoding='utf-8-sig')))
    print(f'单集：{len(eps):,}')

    # ---------- 月龄 ----------
    #  为什么需要这个：播放量是【累计值】。
    #    2020 年的单集攒了 6 年，2026 年的只攒了 3 个月，
    #    直接比就是拿「老」比「新」。
    #  月均播放 = 播放量 ÷ 上线月数，把累积时间折掉。
    #
    #  注意它也有偏向：老节目早就停涨了，分母大 → 月均偏低；
    #  所以这个指标对【老节目不利】。三个口径要一起看。
    NOW_Y, NOW_M = 2026, 10

    def age_months(ym):
        if not ym or len(ym) < 7:
            return None
        return max((NOW_Y - int(ym[:4])) * 12 + (NOW_M - int(ym[5:7])), 1)

    # ---------- 聚合 ----------
    def agg(only_recent=False):
        d = defaultdict(lambda: {'plays': [], 'progs': set(), 'eps': 0, 'monthly': []})
        for e in eps:
            n = e['节目名称']
            if n not in topic or not e['播放量']:
                continue
            if only_recent and (e['发布年月'] or '') < CUTOFF_B:
                continue
            t = topic[n]
            pv = int(e['播放量'])
            d[t]['plays'].append(pv)
            d[t]['progs'].add(n)
            d[t]['eps'] += 1
            a = age_months(e['发布年月'])
            if a:
                d[t]['monthly'].append(pv / a)
        return d

    all_plays = [int(e['播放量']) for e in eps
                 if e['播放量'] and e['节目名称'] in topic]
    g_med = statistics.median(all_plays)
    print(f'全局单集播放中位数：{g_med:,.0f}')

    _allmon = []
    for _v in agg(False).values():
        _allmon += _v['monthly']
    g_month = statistics.median(_allmon)
    print(f'全局月均播放中位数：{g_month:,.0f}')

    # 节目级场均（用于集中度）
    prog_sum = defaultdict(int)
    for e in eps:
        if e['播放量'] and e['节目名称'] in topic:
            prog_sum[e['节目名称']] += int(e['播放量'])
    top3 = sum(sorted(prog_sum.values(), reverse=True)[:3]) / sum(prog_sum.values()) * 100
    print(f'集中度：Top3 节目占 {top3:.1f}%')

    L = ['# 主题供需矩阵\n', '> 由 `03-脚本/10-主题供需矩阵.py` 自动生成\n',
         f'- 样本：喜马拉雅 **{len(topic)}** 个节目 / **{len(all_plays):,}** 集',
         f'- 全局单集播放中位数：**{g_med:,.0f}**',
         f'- 集中度：**Top3 节目占 {top3:.1f}%** 的总播放\n']

    def block(title, d, note=''):
        tot_eps = sum(v['eps'] for v in d.values())
        rows = []
        for t in ORDER:
            if t not in d:
                continue
            v = d[t]
            med = statistics.median(v['plays'])
            mon = statistics.median(v['monthly']) if v['monthly'] else 0
            rows.append({
                't': t,
                'n_prog': len(v['progs']),
                'eps': v['eps'],
                'sup_prog': len(v['progs']) / len(topic) * 100,
                'sup_eps': v['eps'] / tot_eps * 100,
                'med': med,
                'rel': med / g_med,
                'mon': mon,
                'monrel': mon / g_month if g_month else 0,
                'total': sum(v['plays']),
            })
        rows.sort(key=lambda x: -x['monrel'])

        print()
        print('=' * 84)
        print(f' {title}')
        print('=' * 84)
        print(f' {"主题":<12}{"节目":>4}{"集数":>7}{"供给节目%":>9}{"供给集数%":>9}'
              f'{"原始中位":>10}{"相对":>8}{"月均中位":>10}{"相对":>8}')
        print('-' * 84)
        for r in rows:
            flag = '🔥' if r['monrel'] >= 1.3 else ('💤' if r['monrel'] <= 0.6 else '  ')
            print(f" {r['t']:<12}{r['n_prog']:>4}{r['eps']:>7}{r['sup_prog']:>8.1f}%"
                  f"{r['sup_eps']:>8.1f}%{r['med']:>10,.0f}{r['rel']:>7.2f}x"
                  f"{r['mon']:>10,.0f}{r['monrel']:>7.2f}x {flag}")
        print('-' * 84)

        L.append(f'\n## {title}\n')
        if note:
            L.append(f'> {note}\n')
        L.append('| 主题 | 节目数 | 集数 | 供给(节目%) | 供给(集数%) | 原始中位 | 相对 | 月均中位 | **相对** |')
        L.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
        for r in rows:
            flag = '🔥' if r['monrel'] >= 1.3 else ('💤' if r['monrel'] <= 0.6 else '')
            L.append(f"| {r['t']} | {r['n_prog']} | {r['eps']:,} | {r['sup_prog']:.1f}% | "
                     f"{r['sup_eps']:.1f}% | {r['med']:,} | {r['rel']:.2f}x | "
                     f"{r['mon']:,.0f} | **{r['monrel']:.2f}x** {flag} |")
        L.append('')
        L.append('> 🔥 ≥ 1.3 = 需求旺　💤 ≤ 0.6 = 供过于求\n')
        return rows

    ra = block('A 方案：全量（13,595 集）', agg(False),
               '所有单集。播放量是累计值，老节目天然占优，所以看中位数不看总量。')
    rb = block('B 方案：近 12 个月', agg(True),
               f'只算 {CUTOFF_B} 之后发布的单集。样本小，仅作稳健性检验。')

    # ---------- 宗教灵性说明 ----------
    L.append('\n## 关于「宗教灵性」\n')
    L.append('喜马拉雅的 57 个节目里**没有任何宗教类节目**。'
             '全部 33 个宗教节目都在海外平台（多伦多教会、Syndal Baptist、靈命日糧等）。')
    L.append('')
    L.append('所以这一行在矩阵里是空的——**不是数据缺失，是平台差异**。')

    p = os.path.join(OUTDIR, '主题供需矩阵.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print(f'\n[OK] {p}')


if __name__ == '__main__':
    main()
