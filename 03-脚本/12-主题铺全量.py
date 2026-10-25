# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 把主题标签铺到全部 374 个节目  （第 1 版）
============================================================

【为什么这么做】
  现在有两套标签：
    描述统计（374 个）→ 形式（谈话/教学/有声书…）
    供需矩阵（57 个） → 主题（语言教学/社会人文…）
  同一份报告用两套，读起来会割裂。

  铺完之后还能多做三件事：
    ① 验证 57 个样本在主题维度上有没有偏
    ② 看「什么主题活得久」（比「什么形式活得久」更有解释力）
    ③ 看各平台的选题差异

【怎么判的】
  两级：
    ① 57 个喜马拉雅节目用【人工标注】（09 那版，已逐条看过简介）
    ② 其余 317 个用【关键词规则】，按优先级顺序命中即停

  为什么规则优先于逐个手打：
    374 个名字手打必然有错别字，匹配不上还查不出来。
    规则是透明的、可复现的、改一条就能重跑。

  规则判完会打印每类的样本，肉眼扫一遍就能发现错判。

【怎么运行】
      python 12-主题铺全量.py
"""

import os
import re
import sys
import csv
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.join(HERE, '..')
CLEAN  = os.path.join(ROOT, '02-清洗后数据')
OUTDIR = os.path.join(ROOT, '07-分析')

ORDER = ['语言教学', '宗教灵性', '儿童亲子', '故事虚构',
         '影视娱乐音乐', '商业科技', '社会人文', '自我成长', '闲聊']


# ============================================================
#  关键词规则
# ============================================================
#  顺序 = 优先级。命中第一条就停。
#
#  为什么「语言教学」排第一：它的标记最强（learn cantonese / 学粤语 /
#  零基础），而且容易和其他类混——「用粤语讲历史」算社会人文，
#  但名字里写「学粤语」的一定是教学。
#
#  为什么「闲聊」不放规则里：它是默认值，什么都不命中才归它。
RULES = [
    # 儿童排第一：否则「粤语儿童故事」会被语言教学抢走
    ('儿童亲子', [
        r'兒童|儿童|兒歌|儿歌|童謠|童谣|小朋友|親子|亲子',
        r'\bkids?\b|童話|童话|育兒|育儿|小王子|睡前故事',
    ]),
    # 语言教学只认【强标记】：名字里明确写「学/learn/教 + 粤语」，
    # 或者「零基础/发音/口语」。不能靠简介里随便一句「学习粤语」。
    ('语言教学', [
        r'learn\s*cantonese', r'cantonese\s*(lesson|class|course)',
        r'speak\s*cantonese', r'cantonese.*(beginner|intermediate|fluent)',
        r'学粤语|學粵語|学习粤语|學習粵語|学习广东话|學習廣東話',
        r'粤语学习|粵語學習|粤语教程|粵語教程|粤语课程|粵語課程|粤语入门',
        r'零基础|零基礎|發音|发音|口語|口语|練功房|练功房',
        r'coffee\s*break\s*cantonese', r'bite.?size\s*cantonese',
        r'popup\s*cantonese', r'cantonbee', r'chatty\s*cantonese',
    ]),
    ('宗教灵性', [
        r'耶穌|耶稣|基督|聖經|圣经|天主|福音|講道|讲道|神父|牧師|牧师',
        r'靈命|灵命|靈修|灵修|主日|崇拜|church|bible|佛|禪|禅',
        r'禱|祷|天路|嗎哪|吗哪|awr|慕道|宣教|傳道|传道',
    ]),
    ('故事虚构', [
        r'小說|小说|廣播劇|广播剧|有聲書|有声书|說書|说书|講古|讲古',
        r'聊齋|聊斋|傳說|传说|怪談|怪谈|靈異|灵异|故事集',
        r'\bstory\b|\bstories\b|神話|神话|奇幻|武俠|武侠|玄幻',
    ]),
    # 影视去掉光秃秃的「音乐」（太多简介顺带提一句）；
    # 体育去掉——「体育西」是广州地铁站名
    ('影视娱乐音乐', [
        r'電影|电影|影評|影评|劇集|剧集|韓劇|韩剧|港劇|港剧',
        r'歌單|歌单|綜藝|综艺|動漫|动漫|粵語歌|粤语歌|經典金曲',
        r'\bnba\b|足球|籃球|篮球|影意志|戲劇|戏剧',
    ]),
    # 商业去掉「商业」「经济」这类泛词
    ('商业科技', [
        r'財經|财经|投資|投资|股票|美股|港股|創業|创业',
        r'科技|數碼|数码|人工智能|web3|\bai\b',
    ]),
    ('社会人文', [
        r'歷史|历史|文化|新聞|新闻|時事|时事|社會|社会|政治',
        r'哲學|哲学|閱讀|阅读|讀書|读书|書評|书评|讀書會|读书会',
    ]),
    ('自我成长', [
        r'成長|成长|心理|健康|冥想|瑜珈|瑜伽|療癒|疗愈',
        r'情緒|情绪|職場|职场|效率|自我|人生|心靈|心灵',
        r'\byoga\b|mindful|香薰|芳療|芳疗',
    ]),
]

# 预编译
_RULES = [(topic, [re.compile(p, re.I) for p in pats]) for topic, pats in RULES]

# 否定词：命中词前面 6 个字里出现这些，说明这句话是在否定它
_NEG = re.compile(r'不含|不包括|不是|并非|並非|沒有|没有|唔係|无[关關]')


# 规则判错的，手工纠正（看过简介确认过的才写进来）
MANUAL_FIX = {
    '職女聲 (粵語/廣東話)':        '闲聊',    # 三个女人的职场/两性/美容对谈，不是儿童
    '用粵語傾偈':                  '闲聊',    # 名字就是「用粤语聊天」
    '粤语国际':                    '社会人文',  # 电台节目，讲世界各地华人
    '废话生产车间（粤语）':          '闲聊',    # 简介只是顺带提了「广播剧」
    '體育西A出口（粤语）':           '闲聊',    # 体育西是广州地铁站名
}


def classify(name, desc):
    """
    返回 (主题, 命中的规则)。都命中不了 → 闲聊。

    否定句要跳过：有的节目简介写「本节目不含任何学习粤语成分」，
    直接命中「学习粤语」的话，一档闲聊节目就被判成语言教学了。
    """
    if name in MANUAL_FIX:
        return MANUAL_FIX[name], '(手工纠正)'
    text = f'{name} {desc or ""}'
    for topic, pats in _RULES:
        for p in pats:
            for m in p.finditer(text):
                pre = text[max(0, m.start() - 8):m.start()]
                if _NEG.search(pre):
                    continue
                return topic, m.group(0)
    return '闲聊', '(无命中)'


def main():
    # ---------- 57 个人工标注（权威）----------
    manual = {}
    p_manual = os.path.join(OUTDIR, '内容主题_定稿.csv')
    if os.path.exists(p_manual):
        for r in csv.DictReader(open(p_manual, encoding='utf-8-sig')):
            manual[r['节目名']] = r['主题']
    print(f'人工标注（优先采用）：{len(manual)} 个')

    # ---------- 全部节目 ----------
    progs = list(csv.DictReader(open(os.path.join(CLEAN, '节目表_粤语.csv'),
                                     encoding='utf-8-sig')))
    print(f'全部节目：{len(progs)}')

    rows = []
    for r in progs:
        if r['节目名'] in manual:
            rows.append({'节目名': r['节目名'], '主题': manual[r['节目名']],
                         '来源': '人工', '命中': '', '平台': r['平台'],
                         '形态_旧': r['内容形态'], '集数': r['集数']})
        else:
            t, hit = classify(r['节目名'], r['节目简介'])
            rows.append({'节目名': r['节目名'], '主题': t, '来源': '规则',
                         '命中': hit, '平台': r['平台'],
                         '形态_旧': r['内容形态'], '集数': r['集数']})

    # ---------- 写文件 ----------
    p_out = os.path.join(OUTDIR, '主题_全量.csv')
    with open(p_out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['节目名', '主题', '来源', '命中',
                                          '平台', '形态_旧', '集数'])
        w.writeheader()
        for x in sorted(rows, key=lambda y: (ORDER.index(y['主题']),
                                             -int(y['集数'] or 0))):
            w.writerow(x)
    print(f'[OK] {p_out}')

    # ---------- 分布 ----------
    cnt = Counter(r['主题'] for r in rows)
    print()
    print('=' * 66)
    print(' 主题分布（全部 374）')
    print('=' * 66)
    print(f' {"主题":<12}{"节目数":>7}{"占比":>8}')
    for t in ORDER:
        n = cnt.get(t, 0)
        bar = '█' * int(n / len(rows) * 60)
        print(f' {t:<12}{n:>7}{n / len(rows) * 100:>7.1f}%  {bar}')

    # ---------- 规则命中样本（供人工审核）----------
    print()
    print('=' * 66)
    print(' 各类样本（规则判的，重点看这些判得对不对）')
    print('=' * 66)
    by = defaultdict(list)
    for r in rows:
        if r['来源'] == '规则':
            by[r['主题']].append(r)
    for t in ORDER:
        lst = by.get(t, [])
        if not lst:
            continue
        print(f'\n【{t}】规则判了 {len(lst)} 个，抽 8 个：')
        for x in lst[:8]:
            print(f"    [{x['命中'][:14]:<14}] {x['节目名'][:40]}")

    # ---------- 关键验证：57 个样本代表不代表全生态 ----------
    print()
    print('=' * 66)
    print(' 57 个喜马拉雅样本 vs 全部 374 —— 主题分布对比')
    print('=' * 66)
    print(f' {"主题":<12}{"57样本":>16}{"全部374":>16}{"差值":>8}')
    print('-' * 66)

    from_57 = Counter(r['主题'] for r in rows if r['来源'] == '人工')
    from_all = Counter(r['主题'] for r in rows)
    rows_cmp = []
    for t in ORDER:
        a = from_57.get(t, 0) / len(manual) * 100 if manual else 0
        b = from_all.get(t, 0) / len(rows) * 100
        rows_cmp.append((t, a, b, b - a))
        print(f' {t:<12}{a:>8.1f}%{"":>8}{b:>8.1f}%{"":>8}{b - a:>+7.1f}')

    # 差异最大的三个
    rows_cmp.sort(key=lambda x: -abs(x[3]))
    print()
    print(' 差异最大的三个：')
    for t, a, b, d in rows_cmp[:3]:
        print(f'   {t}: 样本 {a:.1f}% vs 全体 {b:.1f}%（差 {d:+.1f} 个百分点）')

    # ---------- 闲聊里可能有漏判 ----------
    print()
    print('=' * 66)
    print(' ⚠️ 归到「闲聊」但名字里带明确内容的（可能漏判）')
    print('=' * 66)
    watch = re.compile(r'歷史|历史|電影|电影|音樂|音乐|科技|投資|投资|健康|'
                       r'小孩|兒童|儿童|故事|書|书|教|學|学', re.I)
    n_watch = 0
    for r in rows:
        if r['主题'] == '闲聊' and watch.search(r['节目名']):
            print(f"    {r['节目名'][:46]}")
            n_watch += 1
            if n_watch >= 25:
                break


if __name__ == '__main__':
    main()
