# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 供需矩阵  （第 1 版）
============================================================

【这个脚本在干什么？】
  回答研究的核心问题：
      「节目在做什么」   vs   「听众想听什么」
      是否匹配？

【怎么做】
  供给 = 该形态的集数占比（生产了多少内容）
  需求 = 该形态的播放量占比（被听了多少）

  核心指标：
      需求/供给 = 播放占比 ÷ 集数占比

      > 1  → 这类内容「供不应求」：生产占比不高，但吃掉了更多播放
      = 1  → 供给需求匹配
      < 1  → 「供过于求」：生产得多，但没人听

  数学上它等于：该形态的场均播放 ÷ 全局场均播放。

【两套口径】
  A 全量   —— 所有单集。受节目年龄影响（老节目攒得久）。
  B 近12月 —— 只算 2025-11 之后发布的。样本小（17 个节目）但干净。

【内容形态从哪来】
  不是苹果分类。57 个节目逐个核对过：
    16 处按简介重新判定 + 5 个拿不准的经确认
  改动全部记在 OVERRIDE 里，可追溯。

【怎么运行】
  在 03-脚本 目录下：
      python 07-供需矩阵.py
"""

import os
import sys
import csv
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.join(HERE, '..')
CLEAN  = os.path.join(ROOT, '06-听众侧')
OUTDIR = os.path.join(ROOT, '07-分析')
os.makedirs(OUTDIR, exist_ok=True)

# 近 12 个月的起点（采集日 2026-10-24 往前推 11 个月）
CUTOFF_B = '2025-11'


# ============================================================
#  手工修正表：苹果分类 → 我们的判定
# ============================================================
#  为什么要有这个：苹果的 <itunes:category> 是主播自己选的，
#  「谈话/访谈」被当成了垃圾桶，塞进去科普、有声书、育儿……
#
#  下面每一条都是看过简介之后改的，左列是原分类，右列是改后的。
OVERRIDE = {
    # ---- 有声书 → 谈话（简介里写着「杂谈」「独白」）----
    '【粤语】得闲饮茶-探讨你关心的':     '谈话/访谈',
    '即兴Solo | 粤语播客':             '谈话/访谈',
    '月经（粤语播客）':                  '谈话/访谈',
    # ---- 谈话 → 其他教育（科普 / 效率方法）----
    '科学在身边：宇宙专题｜粤语':          '其他教育',
    '科学在身边：未来科学家｜粤语':         '其他教育',
    '效率笔记本｜粤语':                   '其他教育',
    # ---- 其他 → 谈话（名字/简介写明了访谈、闲谈）----
    '習慣說-粤語60分鐘深度訪談節目':        '谈话/访谈',
    '开口及利（粤语）':                   '谈话/访谈',
    '無所事事講廣東話':                   '谈话/访谈',
    # ---- 有声书 → 其他教育（讲知识，不是朗读）----
    '粤语有段古 | 俚语背后的故事':          '其他教育',
    '今日广东·乡音（粤语）':                '其他教育',
    # ---- 进虚构叙事（小说 / 讲故事）----
    '小王子（精品粤语版）':                 '虚构叙事',
    '老豆上钟，每晚一个广东话故事':          '虚构叙事',
    '【粤语】惊奇异闻故事集 [每期15分钟的奇异故事]': '虚构叙事',
    # ---- 童话/寓言 → 儿童亲子 ----
    '励志寓言故事大全（粵語）':              '儿童亲子',
    # ---- 音乐 → 语言教学（名字里写着「学粤语」）----
    '粤乐堂|每日一句歌词轻松学粤语':         '语言教学',
    # ---- 谈话 → 有声书（主播自己讲 + 读书，不是访谈）----
    '晚安粤语 | 疯粤星空 好人好梦':          '书籍/有声书',
}

# 输出时的固定排序（按内容生产链条排，不是按数量）
FORM_ORDER = ['语言教学', '谈话/访谈', '虚构叙事', '书籍/有声书',
              '其他教育', '儿童亲子', '音乐', '新闻时事']


def main():
    # ---------- 1. 读节目表，套用修正 ----------
    prog_path = os.path.join(ROOT, '02-清洗后数据', '节目表_粤语.csv')
    progs = {}
    for r in csv.DictReader(open(prog_path, encoding='utf-8-sig')):
        if r['平台'] != '喜马拉雅':
            continue
        form = OVERRIDE.get(r['节目名'], r['内容形态'])
        progs[r['节目名']] = {
            '节目名': r['节目名'],
            '形态_原': r['内容形态'],
            '形态': form,
            '集数_RSS': r['集数'],
            '改动': '是' if r['节目名'] in OVERRIDE and form != r['内容形态'] else '',
        }
    print(f'节目数：{len(progs)}')
    n_change = sum(1 for p in progs.values() if p['改动'])
    print(f'形态被修正的：{n_change} 个')

    # 写出定稿
    p_final = os.path.join(OUTDIR, '内容形态_定稿.csv')
    with open(p_final, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['节目名', '形态_原', '形态', '集数_RSS', '改动'])
        w.writeheader()
        for name in sorted(progs):
            w.writerow(progs[name])
    print(f'[OK] {p_final}')

    # ---------- 2. 读单集数据 ----------
    ep_path = os.path.join(CLEAN, '喜马拉雅单集_清洗后.csv')
    eps = list(csv.DictReader(open(ep_path, encoding='utf-8-sig')))
    print(f'单集：{len(eps):,}')

    # ---------- 3. 按形态聚合 ----------
    def aggregate(only_recent=False):
        """返回 {形态: {'eps': 集数, 'plays': 总播放, 'progs': 节目数}}"""
        agg = defaultdict(lambda: {'eps': 0, 'plays': 0, 'progs': set()})
        for e in eps:
            name = e['节目名称']
            if name not in progs:
                continue
            if only_recent and (e['发布年月'] or '') < CUTOFF_B:
                continue
            pv = e['播放量']
            if not pv:
                continue
            form = progs[name]['形态']
            agg[form]['eps'] += 1
            agg[form]['plays'] += int(pv)
            agg[form]['progs'].add(name)
        return agg

    agg_a = aggregate(False)
    agg_b = aggregate(True)

    tot_eps_a = sum(v['eps'] for v in agg_a.values())
    tot_play_a = sum(v['plays'] for v in agg_a.values())
    tot_eps_b = sum(v['eps'] for v in agg_b.values())
    tot_play_b = sum(v['plays'] for v in agg_b.values())

    # ---------- 4. 打印 + 写报告 ----------
    lines = []
    lines.append('# 供需矩阵\n')
    lines.append('> 由 `03-脚本/07-供需矩阵.py` 自动生成\n')
    lines.append(f'- 样本：喜马拉雅 **{len(progs)}** 个节目 / **{tot_eps_a:,}** 集')
    lines.append(f'- 总播放：**{tot_play_a:,}**')
    lines.append(f'- 形态修正：**{n_change}** 处（见 `内容形态_定稿.csv`）')
    lines.append('')

    def block(title, agg, tot_e, tot_p, note=''):
        print()
        print('=' * 74)
        print(f' {title}')
        print('=' * 74)
        print(f' {"形态":<10}{"集数":>6}{"供给%":>8}{"播放量":>13}{"需求%":>8}{"需求/供给":>10}')
        print('-' * 74)

        L = [f'## {title}\n']
        if note:
            L.append(f'> {note}\n')
        L.append('| 形态 | 集数 | 供给占比 | 播放量 | 需求占比 | **需求/供给** |')
        L.append('|---|---:|---:|---:|---:|---:|')

        rows = []
        for form in FORM_ORDER + [f for f in agg if f not in FORM_ORDER]:
            if form not in agg:
                continue
            v = agg[form]
            if v['eps'] == 0:
                continue
            sup = v['eps'] / tot_e * 100
            dem = v['plays'] / tot_p * 100
            ratio = (dem / sup) if sup else 0
            rows.append((form, v, sup, dem, ratio))

        # 按需求/供给 从高到低排（最供不应求的排最前）
        rows.sort(key=lambda x: -x[4])
        for form, v, sup, dem, ratio in rows:
            flag = '🔥' if ratio >= 1.3 else ('💤' if ratio <= 0.7 else '  ')
            print(f' {form:<10}{v["eps"]:>6}{sup:>7.1f}%{v["plays"]:>13,}{dem:>7.1f}%{ratio:>9.2f} {flag}')
            L.append(f'| {form} | {v["eps"]} | {sup:.1f}% | {v["plays"]:,} | {dem:.1f}% | '
                     f'{"**" + format(ratio, ".2f") + "**" if flag != "  " else format(ratio, ".2f")} |')

        print('-' * 74)
        print(f' {"合计":<10}{tot_e:>6}{100:>7.1f}%{tot_p:>13,}{100:>7.1f}%')
        print('  🔥 = 需求大于供给（供不应求）   💤 = 供给大于需求（供过于求）')
        L.append('')
        L.append('> 🔥 需求/供给 ≥ 1.3 = 供不应求　💤 ≤ 0.7 = 供过于求\n')
        return L

    lines += block(
        f'A 方案：全量（{tot_eps_a:,} 集）',
        agg_a, tot_eps_a, tot_play_a,
        '所有单集。受节目年龄影响：老节目攒播放的时间更长。')

    lines += block(
        f'B 方案：近 12 个月（{tot_eps_b:,} 集）',
        agg_b, tot_eps_b, tot_play_b,
        f'只算 {CUTOFF_B} 之后发布的单集。消除节目年龄差异，但样本变小。')

    # ---------- 稳健版：中位数 ----------
    #  为什么还要这一版：
    #    上面两版用的是「总播放量」，而播放量极度集中 ——
    #    Top 3 节目吃掉 86.5%，「其他教育」这一行 98.5% 来自《粤语有段古》。
    #    所以总量口径算出来的「需求占比」，测的其实是
    #    「这个形态里有没有爆款」，不是「这个形态受不受欢迎」。
    #
    #    中位数不受极值影响，能回答更稳的问题：
    #    「这类节目的典型一集，有多少人听？」
    import statistics
    vals = defaultdict(list)          # 形态 -> 所有单集的播放量
    prog_avg = defaultdict(lambda: defaultdict(int))
    for e in eps:
        n = e['节目名称']
        if n not in progs or not e['播放量']:
            continue
        f = progs[n]['形态']
        vals[f].append(int(e['播放量']))
        prog_avg[n]['s'] += int(e['播放量'])
        prog_avg[n]['c'] += 1

    all_vals = [v for lst in vals.values() for v in lst]
    g_med = statistics.median(all_vals)
    prog_med_by_form = defaultdict(list)
    for n, v in prog_avg.items():
        prog_med_by_form[progs[n]['形态']].append(v['s'] / v['c'])
    g_prog_med = statistics.median([x for lst in prog_med_by_form.values() for x in lst])

    # 集中度：前 3 大节目占总播放多少
    prog_plays = sorted((v['s'] for v in prog_avg.values()), reverse=True)
    top3 = sum(prog_plays[:3]) / sum(prog_plays) * 100

    print()
    print('=' * 78)
    print(' 稳健版：单集播放中位数（不受爆款影响）')
    print('=' * 78)
    print(f' 全局单集播放中位数 {g_med:,.0f} ｜ 全局节目场均中位数 {g_prog_med:,.0f}')
    print(f' 集中度：Top3 节目占总播放 {top3:.1f}%')
    print()
    print(f' {"形态":<10}{"节目":>5}{"节目%":>7}{"集数%":>7}{"单集中位":>10}{"相对":>7}{"场均中位":>10}')
    print('-' * 78)

    lines.append('\n## 稳健版：用中位数（推荐以此为准）\n')
    lines.append(f'> 全局单集播放中位数 **{g_med:,.0f}**；'
                 f'全局节目场均中位数 **{g_prog_med:,.0f}**；'
                 f'**Top3 节目占总播放 {top3:.1f}%**\n')
    lines.append('| 形态 | 节目数 | 供给(节目数) | 供给(集数) | 单集中位 | 相对全局 | 场均中位 | 相对全局 |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|---:|')

    rows2 = []
    for f, lst in vals.items():
        med = statistics.median(lst)
        pmed = statistics.median(prog_med_by_form[f])
        rows2.append((f, len(prog_med_by_form[f]), len(prog_med_by_form[f]) / len(progs) * 100,
                      len(lst) / tot_eps_a * 100, med, med / g_med, pmed, pmed / g_prog_med))
    for r in sorted(rows2, key=lambda x: -x[5]):
        f, np_, pshare, eshare, med, rel, pmed, prel = r
        flag = '🔥' if rel >= 1.3 else ('💤' if rel <= 0.6 else '  ')
        print(f' {f:<10}{np_:>5}{pshare:>6.1f}%{eshare:>6.1f}%{med:>10,.0f}{rel:>6.2f}x{pmed:>10,.0f}')
        lines.append(f'| {f} | {np_} | {pshare:.1f}% | {eshare:.1f}% | {med:,} | '
                     f'**{rel:.2f}x** {flag} | {pmed:,.0f} | {prel:.2f}x |')
    lines.append('')
    lines.append('> 供给有两种算法：**按节目数**（多少人在做这个赛道）、'
                 '**按集数**（生产了多少内容）。两者会不一致，因为不同形态的更新频率差很多。\n')

    p_rep = os.path.join(OUTDIR, '供需矩阵.md')
    with open(p_rep, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'\n[OK] {p_rep}')


if __name__ == '__main__':
    main()
