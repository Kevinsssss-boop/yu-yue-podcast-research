# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 喜马拉雅播放量清洗  （第 1 版）
============================================================

【这个脚本在干什么？】
  把后羿导出的 3 个原始 CSV，洗成两张能直接分析的干净表：

    表1  单集级   —— 一行一集，带播放量、发布年月
    表2  节目级   —— 一行一个节目，两套口径（A 全量 / B 近12月）

【为什么需要它】
  原始导出有 5 个毛病，肉眼改不动：

    ① 播放量有两种写法：「89.9万」和「1808」
    ② 18 条日期是相对时间：「22天前」「1小时前」
    ③ 《小妇人》被拆成第一季/第二季两个节目名
    ④ 3 个节目名和内容侧对不上（改名 / 繁简 / 全角半角）
    ⑤ 粤语学习补采过，和主文件有 4038 条重复

【两个口径为什么都要】
  播放量是「累计值」——2020 年的节目攒了 6 年，2026 年的只攒了 3 个月。
  直接比总量，结论必然是「老节目更受欢迎」，这是假象。

    A 方案：只看最近 12 个月发布的单集  → 消除节目年龄
    B 方案：用「总播放 ÷ 集数」算场均     → 消除集数差异
    C 方案：不动，报告里标注局限         → 这里不实现，作为对照

  两套一起出，成本几乎为零，还能互相印证。

【怎么运行】
  在 03-脚本 目录下打开 PowerShell，输入：
      python 05-清洗喜马拉雅播放量.py
"""

import os
import re
import sys
import csv
import time
import statistics
from collections import defaultdict, Counter

# Windows 控制台防中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.join(HERE, '..')
RAWDIR  = os.path.join(ROOT, '06-听众侧', '原始导出')
OUTDIR  = os.path.join(ROOT, '06-听众侧')
PROGDIR = os.path.join(ROOT, '02-清洗后数据')

# 复用清洗工具箱里已验证过的函数（播放量「89.9万」→ 899000 就是它）
sys.path.insert(0, HERE)
from cy_utils import cn_num_to_int

os.makedirs(OUTDIR, exist_ok=True)


# ============================================================
#  一、节目名归一
# ============================================================

# 为什么不能只做字符串清洗：
#   下面这 3 组差异，再怎么规整也对不上，只能人工登记。
#
#   抓取到的                              内容侧的
#   【粤语】得闲探讨-探讨你关心的      →   【粤语】得闲饮茶-探讨你关心的
#   习惯说-粤语90分钟深度访谈节目      →   習慣說-粤語60分鐘深度訪談節目
#   完结▶《小妇人》第二部（成熟）|粤语版 →   完结▶《小妇人》 第一部（成长）|粤语版
#
#   最后一条是「同名节目的第二季」，喜马拉雅上是独立专辑，
#   但研究里应该算同一个节目，所以归到第一季名下。
ALIAS = {
    '【粤语】得闲探讨-探讨你关心的':            '【粤语】得闲饮茶-探讨你关心的',
    '习惯说-粤语90分钟深度访谈节目':            '習慣說-粤語60分鐘深度訪談節目',
    '完结▶《小妇人》第二部（成熟）|粤语版':      '完结▶《小妇人》 第一部（成长）|粤语版',
}

# 全角 → 半角（「即兴Solo｜粤语播客」和「即兴Solo | 粤语播客」只差这一处）
_FULL2HALF = str.maketrans({
    '｜': '|', '：': ':', '（': '(', '）': ')',
    '，': ',', '　': ' ',
})

# 繁 → 简（只用于「比对」，不改写原名）
try:
    from opencc import OpenCC
    _t2s = OpenCC('t2s')
except ImportError:
    _t2s = None


def norm_name(s):
    """
    节目名归一化，只为了「能不能对上」，不为了好看。
    规则：全角转半角 → 去所有空白 → 繁转简（有 opencc 才做）。
    """
    if not s:
        return ''
    t = str(s).translate(_FULL2HALF)
    t = re.sub(r'\s+', '', t)
    if _t2s:
        t = _t2s.convert(t)
    return t


# ============================================================
#  二、日期解析
# ============================================================

# 相对时间：「1小时前」「22天前」「3周前」
_REL_RE = re.compile(r'^(\d+)\s*(分钟|小时|天|周|个?月)前$')
_REL_DAYS = {'分钟': 0, '小时': 0, '天': 1, '周': 7, '月': 30, '个月': 30}

# 英文月份（Excel 另存会把 2024-08 写成 Aug-24）
_EN_MONTH = {m: f'{i:02d}' for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}


def parse_month(raw, crawl_date):
    """
    把各种日期写法统一成 'YYYY-MM'。

    能处理：
        2024-08          → 2024-08
        2024-08-15       → 2024-08   （只要年月，日舍掉）
        Aug-24           → 2024-08   （Excel 改坏的那种）
        22天前            → 用采集日期倒推
        1小时前           → 采集当月
    crawl_date: datetime.date，这个文件是什么时候采的。
    返回 (YYYY-MM 或 '', 状态说明)
    """
    s = (raw or '').strip()
    if not s:
        return '', '空值'

    # ① 标准年月
    if re.match(r'^\d{4}-\d{2}$', s):
        return s, 'ok'

    # ② 标准年月日 → 截断
    if re.match(r'^\d{4}-\d{2}-\d{2}', s):
        return s[:7], '截断到月'

    # ③ 英文月份 Aug-24
    m = re.match(r'^([A-Za-z]{3})-(\d{2})$', s)
    if m and m.group(1).capitalize() in _EN_MONTH:
        return f'20{m.group(2)}-{_EN_MONTH[m.group(1).capitalize()]}', 'Excel格式修复'

    # ④ 相对时间 → 从采集日期倒推
    m = _REL_RE.match(s)
    if m:
        n = int(m.group(1)) * _REL_DAYS[m.group(2)]
        if n == 0:
            return crawl_date.strftime('%Y-%m'), '相对时间→采集当月'
        from datetime import timedelta
        return (crawl_date - timedelta(days=n)).strftime('%Y-%m'), '相对时间倒推'

    return '', f'无法解析:{s}'


def month_add(ym, n):
    """'2026-10' 往前推 n 个月 → '2025-11'。用于算「最近12个月」的起点。"""
    y, m = int(ym[:4]), int(ym[5:7])
    idx = y * 12 + (m - 1) + n
    return f'{idx // 12:04d}-{idx % 12 + 1:02d}'


# ============================================================
#  三、读原始文件
# ============================================================

def crawl_date_of(path):
    """
    这个文件是什么时候采的？
    优先用文件修改时间（copy2 会保留），备选从文件名末尾的 -1022 / -1024 读。
    """
    mt = time.localtime(os.path.getmtime(path))
    return __import__('datetime').date(mt.tm_year, mt.tm_mon, mt.tm_mday)


def load_raw():
    """读入全部原始 CSV，返回 (行列表, 跳过的文件列表)。"""
    if not os.path.isdir(RAWDIR):
        print(f'✗ 找不到原始数据目录：{RAWDIR}')
        return [], []

    rows, skipped = [], []
    for fn in sorted(os.listdir(RAWDIR)):
        if not fn.lower().endswith('.csv'):
            continue
        p = os.path.join(RAWDIR, fn)
        cd = crawl_date_of(p)
        with open(p, encoding='utf-8-sig', newline='') as f:
            part = list(csv.DictReader(f))

        # 列名不对就整份跳过（比如误放了小宇宙的导出）
        need = {'单集标题', '标题链接', '单集播放量', '单集发布日期', '节目名称'}
        if not need.issubset(part[0].keys() if part else {}):
            skipped.append((fn, '列名不符'))
            continue

        for r in part:
            r['_采集日期'] = cd
            r['_来源文件'] = fn
        rows += part
        print(f'  读入 {len(part):>6} 行  采集于 {cd}  {fn}')

    return rows, skipped


# ============================================================
#  四、主流程
# ============================================================

def main():
    print('=' * 68)
    print(' 第 1 步：读原始数据')
    print('=' * 68)
    raw, skipped = load_raw()
    if not raw:
        print('✗ 没有读到任何数据')
        return
    for fn, why in skipped:
        print(f'  ⚠️ 跳过 {fn}（{why}）')
    print(f'\n  合计 {len(raw)} 行')

    # ---------- 第 2 步：按链接去重 ----------
    print()
    print('=' * 68)
    print(' 第 2 步：按「标题链接」去重')
    print('=' * 68)
    seen, uniq = set(), []
    for r in raw:
        key = (r['标题链接'] or '').strip()
        if not key:
            continue                      # 没链接的行没法判断，直接丢
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    print(f'  {len(raw)} → {len(uniq)} 行（去掉重复 {len(raw) - len(uniq)}）')

    # ---------- 第 3 步：节目名归一 ----------
    print()
    print('=' * 68)
    print(' 第 3 步：节目名归一（对内容侧节目表）')
    print('=' * 68)

    # 内容侧的 57 个喜马拉雅节目，建「归一化名 → 标准名」索引
    p_prog = os.path.join(PROGDIR, '节目表_粤语.csv')
    prog_meta = {}          # 标准名 → 那一行
    for r in csv.DictReader(open(p_prog, encoding='utf-8-sig')):
        if r['平台'] == '喜马拉雅':
            prog_meta[r['节目名']] = r
    idx = {norm_name(n): n for n in prog_meta}
    print(f'  内容侧喜马拉雅节目：{len(prog_meta)} 个')

    unmatched = Counter()
    for r in uniq:
        raw_name = r['节目名称']
        # ① 先查人工别名表
        if raw_name in ALIAS:
            r['_标准名'] = ALIAS[raw_name]
            r['_归一方式'] = '别名表'
            continue
        # ② 再查归一化索引
        hit = idx.get(norm_name(raw_name))
        if hit:
            r['_标准名'] = hit
            r['_归一方式'] = '一致' if hit == raw_name else '归一化'
        else:
            r['_标准名'] = None
            unmatched[raw_name] += 1

    n_ok = sum(1 for r in uniq if r['_标准名'])
    print(f'  归一成功：{n_ok} / {len(uniq)} 行')
    if unmatched:
        print('  ⚠️ 这些节目名对不上内容侧：')
        for k, v in unmatched.most_common():
            print(f'      {v:>5} 行  {k}')

    # ---------- 第 4 步：播放量 + 日期 ----------
    print()
    print('=' * 68)
    print(' 第 4 步：播放量转数字 / 日期统一')
    print('=' * 68)

    date_status = Counter()
    n_bad_play = 0
    for r in uniq:
        # 播放量
        v = cn_num_to_int(r['单集播放量'])
        if v is None:
            n_bad_play += 1
            v = ''
        r['_播放量'] = v

        # 日期
        ym, st = parse_month(r['单集发布日期'], r['_采集日期'])
        r['_发布年月'] = ym
        date_status[st] += 1

    print(f'  播放量解析失败：{n_bad_play} 行')
    print('  日期处理：')
    for k, v in date_status.most_common():
        print(f'    {k:<18} {v:>6} 行')
    n_nodate = sum(1 for r in uniq if not r['_发布年月'])
    print(f'  最终没有发布年月：{n_nodate} 行')

    # ---------- 第 5 步：算 A / B 两套口径 ----------
    print()
    print('=' * 68)
    print(' 第 5 步：聚合成节目级（A 全量 + B 近12月）')
    print('=' * 68)

    # 最近 12 个月的起点：以最晚的采集日期为准
    latest_crawl = max(r['_采集日期'] for r in uniq)
    cutoff = month_add(latest_crawl.strftime('%Y-%m'), -11)
    print(f'  最新采集日：{latest_crawl}   →  近12个月起点：{cutoff}')

    by_prog = defaultdict(list)
    for r in uniq:
        if r['_标准名']:
            by_prog[r['_标准名']].append(r)

    summary = []
    for name, eps in by_prog.items():
        plays_all = [e['_播放量'] for e in eps if isinstance(e['_播放量'], int)]
        dated = [e for e in eps if e['_发布年月']]
        recent = [e['_播放量'] for e in dated
                  if e['_发布年月'] >= cutoff and isinstance(e['_播放量'], int)]

        meta = prog_meta.get(name, {})
        rss_n = meta.get('集数', '')
        try:
            rss_n = int(rss_n)
        except (TypeError, ValueError):
            rss_n = None

        summary.append({
            '节目名称':        name,
            '内容形态':        meta.get('内容形态', ''),
            # ---- 覆盖情况 ----
            '集数_RSS':        rss_n if rss_n is not None else '',
            '集数_爬取':       len(eps),
            '覆盖状态':        ('完整' if rss_n and abs(len(eps) - rss_n) <= 5
                                else '偏少' if rss_n and len(eps) < rss_n
                                else '多于RSS'),
            # ---- A 方案：全量 ----
            'A_集数':          len(plays_all),
            'A_总播放':        sum(plays_all),
            'A_场均播放':      round(sum(plays_all) / len(plays_all)) if plays_all else '',
            'A_中位播放':      round(statistics.median(plays_all)) if plays_all else '',
            'A_最高播放':      max(plays_all) if plays_all else '',
            '最早年月':        min((e['_发布年月'] for e in dated), default=''),
            '最晚年月':        max((e['_发布年月'] for e in dated), default=''),
            # ---- B 方案：近 12 个月 ----
            'B_集数':          len(recent),
            'B_总播放':        sum(recent),
            'B_场均播放':      round(sum(recent) / len(recent)) if recent else '',
        })

    # 按 B 的场均播放排序（没数据的排最后）
    summary.sort(key=lambda x: (-(x['B_场均播放'] if isinstance(x['B_场均播放'], int) else -1)))

    print(f'  聚合出 {len(summary)} 个节目')
    lack = [s for s in summary if s['集数_RSS'] and isinstance(s['集数_RSS'], int)
            and s['集数_爬取'] < s['集数_RSS'] - 5]
    print(f'  覆盖偏少的节目：{len(lack)} 个')
    for s in lack[:10]:
        print(f"      {s['集数_爬取']:>5} / RSS {s['集数_RSS']:>5}  {s['节目名称'][:34]}")

    # ---------- 第 6 步：写出 ----------
    print()
    print('=' * 68)
    print(' 第 6 步：写文件')
    print('=' * 68)

    # 表1：单集级
    p_ep = os.path.join(OUTDIR, '喜马拉雅单集_清洗后.csv')
    ep_cols = ['节目名称', '单集序号', '单集标题', '单集链接',
               '播放量', '发布年月', '采集日期', '来源文件']
    with open(p_ep, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(ep_cols)
        for r in sorted(uniq, key=lambda x: (x['_标准名'] or '~', x['_发布年月'])):
            w.writerow([
                r['_标准名'] or '(未匹配)',
                r['单集序号'], r['单集标题'], r['标题链接'],
                r['_播放量'] if r['_播放量'] != '' else '',
                r['_发布年月'], r['_采集日期'], r['_来源文件'],
            ])
    print(f'  [OK] {p_ep}')

    # 表2：节目级
    p_sum = os.path.join(OUTDIR, '喜马拉雅节目汇总_A+B.csv')
    sum_cols = ['节目名称', '内容形态', '集数_RSS', '集数_爬取', '覆盖状态',
                'A_集数', 'A_总播放', 'A_场均播放', 'A_中位播放', 'A_最高播放',
                '最早年月', '最晚年月',
                'B_集数', 'B_总播放', 'B_场均播放']
    with open(p_sum, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=sum_cols)
        w.writeheader()
        w.writerows(summary)
    print(f'  [OK] {p_sum}')

    # 报告
    p_rep = os.path.join(OUTDIR, '清洗报告_喜马拉雅.md')
    write_report(p_rep, raw, uniq, unmatched, date_status,
                 n_bad_play, summary, cutoff, latest_crawl)
    print(f'  [OK] {p_rep}')

    # ---------- 屏幕摘要 ----------
    print()
    print('=' * 68)
    print(' 摘要')
    print('=' * 68)
    tot_a = sum(s['A_总播放'] for s in summary)
    print(f"  节目数        {len(summary)}")
    print(f"  单集数        {len(uniq)}")
    print(f"  总播放量      {tot_a:,}")
    print(f"  场均播放      {round(tot_a / len(uniq)):,}")
    print()
    print('  B 方案（近12个月）播放量最高的 10 个节目：')
    for s in summary[:10]:
        b = s['B_场均播放'] if s['B_场均播放'] != '' else '-'
        print(f"    {str(b):>7}/集  {s['内容形态']:<8}  {s['节目名称'][:34]}")


def write_report(path, raw, uniq, unmatched, date_status,
                 n_bad_play, summary, cutoff, latest_crawl):
    """把清洗过程写成一份 Markdown 报告，方便回看和写论文时引用。"""
    lines = []
    lines.append('# 喜马拉雅播放量清洗报告\n')
    lines.append('> 由 `03-脚本/05-清洗喜马拉雅播放量.py` 自动生成\n')

    lines.append('## 一、行数变化\n')
    lines.append('| 步骤 | 行数 |')
    lines.append('|---|---:|')
    lines.append(f'| 原始读入 | {len(raw)} |')
    lines.append(f'| 按标题链接去重 | {len(uniq)} |')
    lines.append(f'| 去重剔除 | {len(raw) - len(uniq)} |')
    lines.append('')

    lines.append('## 二、节目名归一\n')
    matched = sum(1 for r in uniq if r['_标准名'])
    lines.append(f'- 归一成功：**{matched} / {len(uniq)}** 行')
    if unmatched:
        lines.append('- 对不上的节目名：')
        for k, v in unmatched.most_common():
            lines.append(f'  - {k}（{v} 行）')
    else:
        lines.append('- 全部对上 ✅')
    lines.append('')

    lines.append('## 三、日期处理\n')
    lines.append('| 处理方式 | 行数 |')
    lines.append('|---|---:|')
    for k, v in date_status.most_common():
        lines.append(f'| {k} | {v} |')
    lines.append('')
    lines.append(f'> 采集日期取文件修改时间；最近 12 个月起点 = **{cutoff}**（最新采集 {latest_crawl}）\n')

    lines.append('## 四、覆盖情况\n')
    lack = [s for s in summary if s['集数_RSS'] and isinstance(s['集数_RSS'], int)
            and s['集数_爬取'] < s['集数_RSS'] - 5]
    lines.append(f'- 节目数：**{len(summary)}**')
    lines.append(f'- 覆盖偏少（爬取 < RSS − 5）：**{len(lack)}** 个')
    for s in lack:
        lines.append(f"  - {s['节目名称']}：爬取 {s['集数_爬取']} / RSS {s['集数_RSS']}")
    lines.append('')

    lines.append('## 五、口径说明\n')
    lines.append('| 口径 | 定义 | 解决什么问题 |')
    lines.append('|---|---|---|')
    lines.append('| **A 全量** | 所有单集的播放量 | 看到总量，但受节目年龄影响 |')
    lines.append(f'| **B 近12月** | 仅 {cutoff} 之后发布的单集 | 消除节目年龄差异 |')
    lines.append('| 场均 | 总播放 ÷ 集数 | 消除集数差异 |')
    lines.append('')
    lines.append('> 播放量是累计值，老节目天然占优。'
                 '**结论以 B（近12月场均）为主，A 作参照。**\n')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    main()
