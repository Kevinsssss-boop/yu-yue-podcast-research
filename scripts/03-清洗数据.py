# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 清洗脚本  （第 1 版）
============================================================

【这个脚本在干什么？】
  按《00-研究设计.md》第八节「清洗方案」的六步，把原始数据洗成
  可以直接做分析的干净表。

  六步（顺序不能乱）：
    ① 剔除非粤语           74 个节目
    ② 剔除《生命恩泉》       2 行 / 400 集（重名无法拆分）
    ③ 补 所属节目ID         单集表 ← 节目表（补上缺失的外键）
    ④ 去重                 同节目内 guid 重复的，保留发布时间最早一条
    ⑤ 逐列清洗             洗 HTML / 繁简 / 时间 / 时长 / 平台…
    ⑥ 写报告 + 验证

【输入】
  ../01-原始数据/内容侧_节目表.csv
  ../01-原始数据/内容侧_单集表.csv
  ../05-打标/语言打标工作台.xlsx        ← 你的打标结果

【输出】
  ../02-清洗后数据/节目表_粤语.csv
  ../02-清洗后数据/单集表_粤语.csv
  ../02-清洗后数据/清洗报告.md

【原始数据一个字都不动】
============================================================
"""

import os
import re
import sys
import csv
import html
import collections
from email.utils import parsedate_to_datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE   = os.path.dirname(os.path.abspath(__file__))
RAWDIR = os.path.join(HERE, '..', '01-原始数据')
MARKDIR = os.path.join(HERE, '..', '05-打标')
OUTDIR = os.path.join(HERE, '..', '02-清洗后数据')
os.makedirs(OUTDIR, exist_ok=True)

sys.path.insert(0, HERE)
from cy_utils import strip_html, cantonese_t2s, duration_to_seconds


# ============================================================
#  配置区
# ============================================================

# 要整体剔除的重名节目（粤语版 + 国语版同名，无法靠节目名拆分 → 方案 A）
DROP_NAME_KEYWORD = '生命恩泉'

# 平台识别规则：(标准名, 关键词列表)。按顺序匹配，先匹配到的算数。
# 同时检查「平台」列和「RSS地址」，因为有的节目平台列写的是主播名。
PLATFORM_RULES = [
    ('喜马拉雅',  ['喜马拉雅', 'ximalaya', 'xmcdn']),
    ('荔枝',      ['荔枝', 'lizhi.fm']),
    ('小宇宙',    ['小宇宙', 'xyzfm']),
    ('SoundOn',   ['soundon']),
    ('Firstory',  ['firstory']),
    ('Spotify/Anchor', ['anchor.fm', 'spotify']),
    ('Buzzsprout', ['buzzsprout']),
    ('Captivate', ['captivate']),
    ('Acast',     ['acast']),
    ('Omny',      ['omnycontent', 'omny.fm']),
    ('RSS.com',   ['rss.com']),
    ('Libsyn',    ['libsyn']),
    ('Transistor', ['transistor']),
    ('Apple',     ['apple.com', 'itunes']),
    ('RTHK',      ['rthk']),
]

# 官方分类 → 内容形态（和研究设计 3.1.1 一致）
def map_form(category):
    c = category or ''
    if c.startswith('Fiction'):
        return '虚构叙事'
    if 'Books' in c:
        return '书籍/有声书'
    if 'Language Learning' in c or 'Language Courses' in c:
        return '语言教学'
    if c.startswith('Religion'):
        return '宗教'
    if c.startswith('Kids'):
        return '儿童亲子'
    if c.startswith('News'):
        return '新闻时事'
    if c.startswith('Music'):
        return '音乐'
    if c.startswith('True Crime'):
        return '真实犯罪'
    if c.startswith('Education'):
        return '其他教育'
    if c.startswith(('Society', 'Leisure', 'Comedy', 'Health', 'TV', 'Business',
                     'Sports', 'Technology', 'Science', 'History', 'other', 'Arts')):
        return '谈话/访谈'
    return '未分类'


# ============================================================
#  工具函数
# ============================================================

_URL_RE  = re.compile(r'https?://\S+|www\.\S+')
_CTRL_RE = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')
_WS_RE   = re.compile(r'\s+')


def clean_text(s):
    """
    文本清洗的固定顺序（每一步都不能省）：
      ① 剥 HTML / CDATA    —— 78% 的单集简介是富文本
      ② 去 URL             —— 简介末尾常挂公众号/官网链接
      ③ 去控制字符
      ④ 繁 → 简（粤语安全版）
      ⑤ 压空白
    """
    if s is None:
        return ''
    t = strip_html(s)
    t = _URL_RE.sub(' ', t)
    t = _CTRL_RE.sub(' ', t)
    t = cantonese_t2s(t)
    return _WS_RE.sub(' ', t).strip()


def parse_platform(platform_raw, rss_url):
    """从「平台」列 + 「RSS地址」里认出托管平台；认不出归「其他」。"""
    hay = f'{platform_raw or ""} {rss_url or ""}'.lower()
    for name, keys in PLATFORM_RULES:
        if any(k.lower() in hay for k in keys):
            return name
    return '其他'


def parse_pubdate(s):
    """
    RFC822（Tue, 15 Oct 2026 10:00:00 +0800）→ (YYYY-MM-DD HH:MM:SS, YYYY-MM)
    解析不了返回 ('', '')。
    """
    s = (s or '').strip()
    if not s:
        return '', ''
    try:
        dt = parsedate_to_datetime(s)
        if dt is None:
            return '', ''
        return dt.strftime('%Y-%m-%d %H:%M:%S'), dt.strftime('%Y-%m')
    except Exception:
        return '', ''


# ============================================================
#  主流程
# ============================================================

def main():
    report = []          # 清洗报告的内容行
    def log(line=''):
        print(line)
        report.append(line)

    # ----------------------------------------------------------
    # 第 0 步：读你的打标结果 → 「节目名 → 语言」
    # ----------------------------------------------------------
    print('=' * 60)
    print('第 0 步：读入打标结果')
    print('=' * 60)

    from openpyxl import load_workbook
    wb = load_workbook(os.path.join(MARKDIR, '语言打标工作台.xlsx'), read_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    hdr = list(next(it))
    i_name, i_ver = hdr.index('节目名'), hdr.index('★你的语言判定')

    lang = {}
    for row in it:
        name, verdict = row[i_name], row[i_ver]
        # 空着 = 你在抽查时没填 = 认同自动判定（粤语）
        lang[name] = (verdict or '粤语').strip()
    wb.close()

    cnt = collections.Counter(lang.values())
    print(f'  打标结果：{dict(cnt)}')
    print()

    # ----------------------------------------------------------
    # 第 1 步：节目表 —— 筛语言、剔重名、逐列清洗
    # ----------------------------------------------------------
    print('=' * 60)
    print('第 1 步：清洗节目表')
    print('=' * 60)

    with open(os.path.join(RAWDIR, '内容侧_节目表.csv'), encoding='utf-8-sig', newline='') as f:
        raw_progs = list(csv.DictReader(f))
    n_raw = len(raw_progs)

    # ① 剔除非粤语
    kept = [r for r in raw_progs if lang.get(r['节目名'], '粤语') == '粤语']
    n_drop_lang = n_raw - len(kept)

    # ② 剔除重名节目
    dropped_dup = [r for r in kept if DROP_NAME_KEYWORD in r['节目名']]
    kept = [r for r in kept if DROP_NAME_KEYWORD not in r['节目名']]

    print(f'  原始 {n_raw} 行 → 剔除非粤语 {n_drop_lang} → 剔除重名 {len(dropped_dup)} → 剩 {len(kept)} 行')

    # ⑤ 逐列清洗
    name2id = {}             # 节目名 → 节目ID（第 3 步补外键要用）
    prog_rows = []
    for r in kept:
        cat = (r['官方分类'] or '').strip()
        parts = [p.strip() for p in cat.split(' / ')] if cat else []
        row = {
            '节目ID':   r['节目ID'],
            '节目名':   _WS_RE.sub(' ', r['节目名'] or '').strip(),   # 不做繁简转换（连接键）
            'RSS地址':  (r['RSS地址'] or '').strip(),
            '平台':     parse_platform(r['平台'], r['RSS地址']),
            '平台_原始': _WS_RE.sub(' ', r['平台'] or '').strip(),
            '主播':     clean_text(r['主播']),
            '节目简介': clean_text(r['节目简介']),
            '分类L1':   parts[0] if parts else '',
            '分类L2':   parts[1] if len(parts) > 1 else '',
            '内容形态': map_form(cat),
            '集数':     r['集数'] if (r['集数'] or '').strip().isdigit() else '',
            '语言':     '粤语',
            '主题':     '',        # 下一步打标
        }
        prog_rows.append(row)
        name2id[row['节目名']] = r['节目ID']

    prog_cols = ['节目ID', '节目名', 'RSS地址', '平台', '平台_原始', '主播',
                 '节目简介', '分类L1', '分类L2', '内容形态', '集数', '语言', '主题']
    p_prog_out = os.path.join(OUTDIR, '节目表_粤语.csv')
    with open(p_prog_out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=prog_cols)
        w.writeheader()
        w.writerows(prog_rows)
    print(f'  [OK] 节目表 → {p_prog_out}')
    print()

    # ----------------------------------------------------------
    # 第 2 步：单集表 —— 筛节目、补外键、去重、逐列清洗
    # ----------------------------------------------------------
    print('=' * 60)
    print('第 2 步：清洗单集表（4.7 万行，要等一两分钟）')
    print('=' * 60)

    keep_names = set(name2id)
    ep_rows = []             # 清洗后的行
    n_ep_raw = n_ep_drop = 0
    n_dur_fail = 0           # 有时长值、但解析失败的（真正的异常）
    n_dur_empty = 0          # 时长本来就空的（正常）
    n_desc_lost = 0          # 原本有内容、洗完变成空的（真正的异常）

    with open(os.path.join(RAWDIR, '内容侧_单集表.csv'), encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            n_ep_raw += 1
            name = r['所属节目']
            # ① 只留粤语节目的单集（② 的剔除也在这一步生效，因为那些节目不在 keep_names 里）
            if name not in keep_names:
                n_ep_drop += 1
                continue

            pub, ym = parse_pubdate(r['发布时间'])

            # 时长：区分「本来就没写」和「写了但解析不了」
            raw_dur = (r['时长'] or '').strip()
            if not raw_dur:
                sec = ''
                n_dur_empty += 1
            else:
                sec = duration_to_seconds(raw_dur)
                if sec is None:
                    n_dur_fail += 1
                    sec = ''

            desc = clean_text(r['单集简介'])
            # 原本有内容、洗完却空了 —— 说明清洗把内容吃掉，是 bug。
            # 注意：「<p>http://xxx.com</p><p><br></p>」这种原始简介里只有一个网址，
            # 去 URL 后变空是【预期行为】，不算洗丢，所以要先把 URL 也刨掉再判断。
            if not desc and _URL_RE.sub(' ', strip_html(r['单集简介'] or '')).strip():
                n_desc_lost += 1

            ep_rows.append({
                '单集ID':     (r['单集ID'] or '').strip(),
                '所属节目':   name,
                '所属节目ID': name2id[name],
                '单集标题':   clean_text(r['单集标题']),
                '单集简介':   desc,
                '发布时间':   pub,
                '发布年月':   ym,
                '时长_秒':    sec,
                '音频链接':   html.unescape((r['音频链接'] or '').strip()),
                '集号':       (r['集号'] or '').strip(),
            })
            if n_ep_raw % 10000 == 0:
                print(f'    …已处理 {n_ep_raw} 行')
    print(f'  原始 {n_ep_raw} 行 → 剔除非粤语节目 {n_ep_drop} → 剩 {len(ep_rows)} 行')
    print(f'  时长：空值 {n_dur_empty} 条（正常）／解析失败 {n_dur_fail} 条')

    # ④ 去重：同一节目内 单集ID 相同的，保留发布时间最早的一条
    before_dedup = len(ep_rows)
    best = {}
    for r in ep_rows:
        key = (r['所属节目ID'], r['单集ID'])
        old = best.get(key)
        # 发布时间为空排最后；否则取更早的
        if old is None or (r['发布时间'] and (not old['发布时间'] or r['发布时间'] < old['发布时间'])):
            best[key] = r
    ep_rows = list(best.values())
    n_dupe = before_dedup - len(ep_rows)
    print(f'  去重：删掉 {n_dupe} 条重复 → {len(ep_rows)} 行')

    # 新增「集序号」：每个节目内按发布时间排序，1..n
    by_prog = collections.defaultdict(list)
    for r in ep_rows:
        by_prog[r['所属节目ID']].append(r)
    for pid, lst in by_prog.items():
        lst.sort(key=lambda x: (x['发布时间'] or '9999'))
        for i, r in enumerate(lst, 1):
            r['集序号'] = i
    print(f'  已为 {len(by_prog)} 个节目生成「集序号」')

    ep_cols = ['单集ID', '所属节目', '所属节目ID', '单集标题', '单集简介',
               '发布时间', '发布年月', '时长_秒', '音频链接', '集号', '集序号']
    p_ep_out = os.path.join(OUTDIR, '单集表_粤语.csv')
    with open(p_ep_out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=ep_cols)
        w.writeheader()
        w.writerows(ep_rows)
    print(f'  [OK] 单集表 → {p_ep_out}')
    print()

    # ----------------------------------------------------------
    # 第 3 步：验证 + 写清洗报告
    # ----------------------------------------------------------
    print('=' * 60)
    print('第 3 步：验证与报告')
    print('=' * 60)

    checks = []

    def check(name, ok, detail):
        checks.append((name, ok, detail))
        print(f'  {"✅" if ok else "❌"} {name}：{detail}')

    # 残留检查 —— 只认「标签样」的尖括号：< + ASCII 字母，或 </
    # 注意不能用 <\w：Python 的 \w 也匹配汉字，会把 "<3"（爱心）、"<爱上…>"（强调）误判成标签
    resid_re = re.compile(r'<[a-zA-Z/]|&amp;|CDATA')
    resid = sum(1 for r in ep_rows
                if resid_re.search((r['单集标题'] or '') + (r['单集简介'] or '')))
    check('HTML/CDATA/&amp; 残留', resid == 0, f'{resid} 条')

    # 外键完整
    orphan = sum(1 for r in ep_rows if r['所属节目ID'] not in {p['节目ID'] for p in prog_rows})
    check('外键完整（所属节目ID）', orphan == 0, f'{orphan} 条孤儿')

    # 时间格式
    bad_time = sum(1 for r in ep_rows
                   if r['发布时间'] and not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', r['发布时间']))
    check('发布时间格式统一', bad_time == 0, f'{bad_time} 条异常')

    # 时长：有值的必须都转成数字；空值不算失败
    check('时长转换', n_dur_fail == 0,
          f'解析失败 {n_dur_fail} 条；空值 {n_dur_empty} 条（原始就没写）')

    # 简介：不能「原本有内容、洗完变空」
    empty_desc = sum(1 for r in ep_rows if not r['单集简介'])
    check('简介未被洗丢', n_desc_lost == 0,
          f'洗丢 {n_desc_lost} 条｜最终为空 {empty_desc} 条'
          f'（{empty_desc/max(len(ep_rows),1)*100:.1f}%，原始就是空壳的）')

    # ---- 写报告 ----
    p_rep = os.path.join(OUTDIR, '清洗报告.md')
    with open(p_rep, 'w', encoding='utf-8') as f:
        f.write('# 清洗报告\n\n')
        f.write(f'> 由 `03-脚本/03-清洗数据.py` 自动生成\n\n')
        f.write('## 行数变化\n\n')
        f.write('| 步骤 | 节目表 | 单集表 |\n|---|---:|---:|\n')
        f.write(f'| 原始 | {n_raw} | {n_ep_raw} |\n')
        f.write(f'| ① 剔除非粤语 | -{n_drop_lang} | -{n_ep_drop} |\n')
        f.write(f'| ② 剔除重名《{DROP_NAME_KEYWORD}》 | -{len(dropped_dup)} | （已含在上一步） |\n')
        f.write(f'| ④ 去重 | 0 | -{n_dupe} |\n')
        f.write(f'| **清洗后** | **{len(prog_rows)}** | **{len(ep_rows)}** |\n\n')

        f.write('## 内容形态分布（清洗后）\n\n')
        f.write('| 形态 | 节目数 |\n|---|---:|\n')
        for k, v in collections.Counter(p['内容形态'] for p in prog_rows).most_common():
            f.write(f'| {k} | {v} |\n')

        f.write('\n## 平台分布（清洗后）\n\n')
        f.write('| 平台 | 节目数 |\n|---|---:|\n')
        for k, v in collections.Counter(p['平台'] for p in prog_rows).most_common():
            f.write(f'| {k} | {v} |\n')

        f.write('\n## 验证结果\n\n')
        f.write('| 检查项 | 结果 | 详情 |\n|---|:---:|---|\n')
        for name, ok, detail in checks:
            f.write(f'| {name} | {"✅" if ok else "❌"} | {detail} |\n')

        f.write('\n## 被剔除的重名节目\n\n')
        for r in dropped_dup:
            f.write(f'- {r["节目名"]}（{r["集数"]} 集，{r["RSS地址"]}）\n')

    print()
    print(f'  [OK] 清洗报告 → {p_rep}')
    print()
    print('=' * 60)
    print('全部完成')
    print('=' * 60)
    print(f'  节目表：{len(prog_rows)} 行  →  {p_prog_out}')
    print(f'  单集表：{len(ep_rows)} 行  →  {p_ep_out}')
    print(f'  报告  ：{p_rep}')


if __name__ == '__main__':
    main()
