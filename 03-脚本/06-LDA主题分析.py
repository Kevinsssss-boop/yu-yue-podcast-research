# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · LDA 主题分析  （第 2 版）
============================================================

【第 1 版为什么失败】
  只用了「单集标题」，结果三件事同时爆了：
    ① 平均每篇只剩 6.1 个词 —— 标题太短，LDA 撑不起来
    ② 主题词被英文虚词占满：of / and / the / to / in
       （31% 的标题含英文，海外节目尤甚）
    ③ coherence 算成 nan（c_v 的除零问题）

【第 2 版的三个改动】
  ① 文本源改用「单集标题 + 单集简介」
     简介覆盖率 85%，中位 181 字，信息量是标题的十几倍。
     但要先剔掉模板 —— 有一段简介重复了 1297 次（"零基础学员专辑学习顺序…"），
     这类反复出现的简介不是内容，是灌水，必须整条丢掉。

  ② 补全停用词
     · 英文虚词表（the/of/and/to…）
     · 中文高频虚词（不是/没有/如何/其实…）
     · 节目里反复出现的人名/台名（陈老、SBS、癫台…）

  ③ coherence 改用 u_mass
     它直接基于语料库统计，不会出现 nan，适合用来比较不同 k。

【怎么运行】
  在 03-脚本 目录下：
      python 06-LDA主题分析.py

  大约 10-15 分钟（分词占大半）。
"""

import os
import re
import sys
import csv
import math
import random
from collections import Counter

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import jieba
from gensim import corpora, models
from gensim.models.coherencemodel import CoherenceModel

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.join(HERE, '..')
INDIR  = os.path.join(ROOT, '02-清洗后数据')
OUTDIR = os.path.join(ROOT, '07-分析')
os.makedirs(OUTDIR, exist_ok=True)

K_LIST = [8, 10, 12]
RANDOM_SEED = 42

# 一段简介出现超过这个次数，就认定是模板/灌水，整条丢掉
BOILERPLATE_THRESHOLD = 20


# ============================================================
# 一、停用词
# ============================================================

# 英文虚词。第 1 版最大的污染源，必须彻底清掉。
EN_STOP = set("""
a an the and or but if then than so as of to in on at by for from with without
is are was were be been being am do does did doing have has had having
i you he she it we they me him her us them my your his its our their
this that these those such
what how why when where who which whom whose
all any some more most other another each every both few many much
not no nor only own same just very too also again further once
can will would could should may might must shall
here there now up down out off over under again
one two three first last new day days live talk night episode part ft feat vs
get got make made see seen know known say said go going come came
www com http https html

# 托管平台的模板词（"Hosted by Acast" / "Powered by Firstory" / SoundOn 提供）
acast hosted hosting host provided powered privacy soundon firstory
fexingo onenighttalk nggayduck podbean libsyn buzzsprout transistor captivate omny
linktr discord clubhouse applepodcast apple spotify google youtube patreon
halfkong sparksine lucas luna sunny channel join take list air
information free perfect keep follow men god story about into license
""".split())

# 中文高频虚词（第 1 版漏掉那批，现在补上）
CN_STOP = set("""
不是 没有 如何 为何 为什么 什么 怎样 怎么 点解 点样 其实 原来 到底 一定 最后
开始 成为 最大 不同 分别 选择 也许 只是 关于 已经 可以 可能 应该 还是 就是
但是 因为 所以 如果 虽然 然后 而且 或者 不过 只是 这样 那样 这些 那些
我们 你们 他们 她们 它们 自己 大家 别人 朋友 听众 主播 主持 嘉宾 老师
时候 时间 一下 一起 一样 一直 一些 一个 每个 每天 每次
今天 明天 昨天 现在 最近 之后 之前 以后 以前 今天
系列 分钟 小时 第二 第一 第三 最新 更新
分享 介绍 聊聊 谈谈 说说 讲讲 看看 听听

粤语 粵語 广东话 廣東話 广府 廣府 湖南 普通话 国語 国语 cantonese podcast
播客 節目 节目 頻道 频道 电台 電台 声音 聲音 音频 音頻
支持 收听 收聽 訂閱 订阅 关注 關注 欢迎 歡迎 会员 會員
本集 今集 一集 每集 这集 這集 本期 上集 下集
营运 營運 内容 內容 资料 資料 補充 补充 详尽 詳盡 三位
专属 專屬 定期 上载 上載 留言 记得 記得 告诉 告訴 显示 顯示
免费 免費 小小 全面 甚么 甚麼 凌晨 下午 星期 每日 一齐 一齊
同埋 好似 觉得 覺得 喜欢 喜歡 好多 知道 钟意 鍾意
""".split())

# 节目/主播专名：在简介里到处出现，但对主题没信息量
NAME_STOP = set("""
陈老 陈老c 癫台 澳门癫台 sbs 香港电台 rthk 温哥华 多伦多 ont
宇婷 nj宇婷 粤语学院 玩转粤语 港你知 河马叔叔 车理 洛宾
微信 公众号 订阅 关注 加微 邮箱 邮件 instagram youtube patreon 爱发电
""".split())

STOPWORDS = EN_STOP | CN_STOP | NAME_STOP


# ============================================================
# 二、清洗
# ============================================================

# 集号：「第209期」「E12」「Vol.5」「209.」
_EP_NUM_RE = re.compile(
    r'第\s*\d+\s*[集期課课講讲話话回]\s*'
    r'|\bNo\.?\s*\d+\b'
    r'|\bVol\.?\s*\d+\b'
    r'|\b[Ee][Pp]?\.?\s*\d+\b'
    r'|^\s*\[?\d+\]?\s*[\.、:：\-—]',
    re.I)

# 括号补充（【粤语】【完整版】这类标签）
_BRACKET_RE = re.compile(r'[\[\(【〔]([^\]\)】〕]{1,20})[\]\)】〕]')

# 只保留字母数字和汉字
_KEEP_RE = re.compile(r'[^\w一-鿿]+')

# 纯标点/纯数字
_DIGIT_RE = re.compile(r'^\d+$')


def clean_text(s):
    t = str(s or '')
    t = _EP_NUM_RE.sub(' ', t)
    t = _BRACKET_RE.sub(' ', t)
    t = _KEEP_RE.sub(' ', t)
    return t.strip()


def tokenize(text):
    out = []
    for w in jieba.lcut(clean_text(text)):
        w = w.strip()
        if len(w) < 2:
            continue
        if _DIGIT_RE.match(w):
            continue
        wl = w.lower()
        if wl in STOPWORDS or w in STOPWORDS:
            continue
        # 纯英文的，要求至少 3 个字母，且不是常见虚词（已在上表）
        if w.isascii() and len(w) < 3:
            continue
        out.append(wl if w.isascii() else w)
    return out


# ============================================================
# 三、主流程
# ============================================================

def main():
    print('=' * 70)
    print(' 第 1 步：读数据 + 剔模板简介')
    print('=' * 70)

    p = os.path.join(INDIR, '单集表_粤语.csv')
    rows = []
    with open(p, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    print(f'  单集总数 {len(rows):,}')

    # 统计简介出现次数，找出模板
    desc_count = Counter((r['单集简介'] or '').strip() for r in rows)
    boiler = {d for d, c in desc_count.items() if d and c >= BOILERPLATE_THRESHOLD}
    n_boiler_docs = sum(1 for r in rows
                        if (r['单集简介'] or '').strip() in boiler)
    print(f'  识别出模板简介 {len(boiler)} 段，涉及 {n_boiler_docs:,} 条单集')
    print('    最常见的一段：')
    if boiler:
        top = max(boiler, key=lambda d: desc_count[d])
        print(f'      {desc_count[top]} 次 | {top[:56]}')

    print()
    print('=' * 70)
    print(' 第 2 步：分词（要等几分钟）')
    print('=' * 70)

    for w in ['栋笃笑', '港剧', '港劇', '广东歌', '廣東歌', '茶餐厅', '茶餐廳',
              '粤语歌', '粵語歌', '香港人', '广州人', '廣州人', '大湾区', '大灣區',
              '心灵', '心靈', '职场', '職場', '亲子', '親子', '理财', '理財',
              '广播剧', '廣播劇', '占卜', '塔罗', '塔羅', '移民', '灵性', '靈性']:
        jieba.add_word(w)

    docs, kept_idx = [], []
    for i, r in enumerate(rows):
        title = r['单集标题'] or ''
        # 简介截到前 300 字：真正的介绍在开头，结尾多半是
        # 「关注公众号」「Hosted by Acast」这类无关内容
        desc = '' if (r['单集简介'] or '').strip() in boiler else (r['单集简介'] or '')[:300]
        toks = tokenize(title + ' ' + desc)
        if len(toks) >= 3:
            docs.append(toks)
            kept_idx.append(i)
        if (i + 1) % 10000 == 0:
            print(f'  已处理 {i + 1:,} 条')

    n_tok = sum(len(d) for d in docs)
    print(f'  有效文档 {len(docs):,}  总词数 {n_tok:,}  平均每篇 {n_tok / len(docs):.1f} 词')

    print()
    print('=' * 70)
    print(' 第 3 步：建词典')
    print('=' * 70)
    dictionary = corpora.Dictionary(docs)
    before = len(dictionary)
    dictionary.filter_extremes(no_below=30, no_above=0.4)
    print(f'  词表 {before:,} → {len(dictionary):,}')
    corpus = [dictionary.doc2bow(d) for d in docs]

    # ---------- 训练 ----------
    results = []
    for k in K_LIST:
        print()
        print('=' * 70)
        print(f' 训练 k = {k}')
        print('=' * 70)
        lda = models.LdaModel(
            corpus=corpus, id2word=dictionary, num_topics=k,
            passes=3, iterations=50, random_state=RANDOM_SEED,
        )
        # u_mass：基于语料共现，稳定不会 nan
        cm = CoherenceModel(model=lda, corpus=corpus, dictionary=dictionary,
                            coherence='u_mass')
        coh = cm.get_coherence()
        if math.isnan(coh):
            coh = float('-inf')
        print(f'  coherence (u_mass) = {coh:.4f}   （越接近 0 越好）')

        topics = [[w for w, _ in lda.show_topic(t, topn=12)] for t in range(k)]
        dom = [max(lda.get_document_topics(b), key=lambda x: x[1])[0] for b in corpus]
        share = Counter(dom)

        print(f'  {"主题":<5}{"占比":>7}  前 10 词')
        for t in range(k):
            pct = share.get(t, 0) / len(corpus) * 100
            print(f'  T{t:<4}{pct:>6.1f}%  {" / ".join(topics[t][:10])}')

        results.append(dict(k=k, coh=coh, topics=topics, share=share,
                            n=len(corpus), model=lda))

    print()
    print('=' * 70)
    print(' k 值对比（u_mass，越接近 0 越好）')
    print('=' * 70)
    for r in results:
        print(f"  k={r['k']:>2}   {r['coh']:.4f}")
    best = max(results, key=lambda r: r['coh'])
    print(f"\n  → 数值最好的是 k={best['k']}，但最终要靠人工看主题词是否讲得通")

    # ---------- 节目级归类 ----------
    # 思路：一集有主题分布，一个节目是很多集的集合，
    # 所以把该节目所有集的分布加起来、归一化，最大的那个就是它的主导主题。
    print()
    print('=' * 70)
    print(' 节目级归类（k = 10）')
    print('=' * 70)

    target = next((r for r in results if r['k'] == 10), best)
    kmodel = target['model']
    K = target['k']
    print(f"  用的是 k={K} 的模型")

    # 每篇文章的主题分布
    doc_dists = []
    for b in corpus:
        d = dict(kmodel.get_document_topics(b, minimum_probability=0))
        doc_dists.append(d)

    # 按节目累加
    prog_sum = {}
    prog_n = Counter()
    for j, ri in enumerate(kept_idx):
        name = rows[ri]['所属节目']
        if name not in prog_sum:
            prog_sum[name] = [0.0] * K
        for t, v in doc_dists[j].items():
            prog_sum[name][t] += v
        prog_n[name] += 1

    # 读节目表补平台/形态
    meta = {}
    for r in csv.DictReader(open(os.path.join(INDIR, '节目表_粤语.csv'),
                                 encoding='utf-8-sig')):
        meta[r['节目名']] = r

    # 归一化 + 取主导/次导主题
    assign = []
    for name, vec in prog_sum.items():
        s = sum(vec) or 1
        norm = [v / s for v in vec]
        order = sorted(range(K), key=lambda t: -norm[t])
        m = meta.get(name, {})
        assign.append({
            '节目名':     name,
            '平台':       m.get('平台', ''),
            '内容形态_原': m.get('内容形态', ''),
            '集数':       m.get('集数', ''),
            '主导主题':   f'T{order[0]}',
            '主导概率':   round(norm[order[0]], 3),
            '次主题':     f'T{order[1]}',
            '次概率':     round(norm[order[1]], 3),
            '_vec':       norm,
        })

    assign.sort(key=lambda x: (x['主导主题'], -x['主导概率']))
    print(f"  归类了 {len(assign)} 个节目")

    # 每个主题下有多少节目
    cnt = Counter(a['主导主题'] for a in assign)
    print()
    print(f"  {'主题':<5}{'节目数':>6}  权重词")
    for t in range(K):
        ws = ' / '.join(target['topics'][t][:6])
        print(f"  T{t:<4}{cnt.get(f'T{t}', 0):>6}  {ws}")

    # 写 CSV
    p_assign = os.path.join(OUTDIR, '节目主题归类.csv')
    with open(p_assign, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['节目名', '平台', '内容形态_原',
                                          '集数', '主导主题', '主导概率',
                                          '次主题', '次概率'])
        w.writeheader()
        for a in assign:
            w.writerow({k: v for k, v in a.items() if not k.startswith('_')})
    print(f'\n  [OK] {p_assign}')

    # 写分组 Markdown，方便肉眼核对
    p_group = os.path.join(OUTDIR, '节目主题归类_分组.md')
    with open(p_group, 'w', encoding='utf-8') as f:
        L = [f'# 节目主题归类（k={K}）\n',
             '> 由 `03-脚本/06-LDA主题分析.py` 自动生成\n']
        for t in range(K):
            ws = ' · '.join(target['topics'][t][:10])
            members = [a for a in assign if a['主导主题'] == f'T{t}']
            L.append(f'\n## T{t}　{len(members)} 个节目\n')
            L.append(f'**权重词**：{ws}\n')
            L.append('| 节目 | 平台 | 集数 | 主导概率 |')
            L.append('|---|---|---:|---:|')
            for a in sorted(members, key=lambda x: -x['主导概率']):
                # 节目名里可能带竖线（如「即兴Solo | 粤语播客」），
                # 直接写进表格会被当成列分隔符，整张表错位 —— 必须转义
                nm = a['节目名'][:40].replace('|', r'\|')
                L.append(f"| {nm} | {a['平台']} | {a['集数']} | {a['主导概率']:.2f} |")
        f.write('\n'.join(L))
    print(f'  [OK] {p_group}')

    # ---------- 写报告 ----------
    p_out = os.path.join(OUTDIR, 'LDA主题分析.md')
    with open(p_out, 'w', encoding='utf-8') as f:
        L = ['# LDA 主题分析结果\n',
             '> 由 `03-脚本/06-LDA主题分析.py` 自动生成\n',
             f'- 文档数：**{len(docs):,}**（标题 + 简介）',
             f'- 总词数：**{n_tok:,}**，平均每篇 **{n_tok / len(docs):.1f}** 词',
             f'- 词表：**{len(dictionary):,}**',
             f'- 剔除模板简介：**{len(boiler)}** 段 / **{n_boiler_docs:,}** 条单集\n',
             '## k 值对比\n',
             '| k | coherence (u_mass) |', '|---:|---:|']
        for r in results:
            mark = ' ⭐' if r['k'] == best['k'] else ''
            L.append(f"| {r['k']}{mark} | {r['coh']:.4f} |")
        L.append('')
        for r in results:
            L.append(f"\n## k = {r['k']}\n")
            L.append('| 主题 | 占比 | 权重词 |')
            L.append('|---:|---:|---|')
            for t, ws in enumerate(r['topics']):
                pct = r['share'].get(t, 0) / r['n'] * 100
                L.append(f"| T{t} | {pct:.1f}% | {' · '.join(ws[:10])} |")
        f.write('\n'.join(L))
    print(f'\n  [OK] {p_out}')


if __name__ == '__main__':
    main()
