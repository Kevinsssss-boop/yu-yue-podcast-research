# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 打标工作台生成脚本  （第 1 版）
============================================================

【这个脚本在干什么？】
  把采集来的 450 个节目，做成一张「你填得动」的表 —— 让你判断每档节目
  是不是主要用粤语讲的。

  它做四件事：
    1) 用「判定规则」给每个节目一个自动初判（粤语 / 非粤语）
    2) 按需要人工介入的程度分档（哪些必须你看、哪些抽查就行）
    3) 从官方分类映射出「内容形态」（谈话/教学/有声书…）
    4) 洗掉简介里的 HTML / CDATA，取 3 条单集标题样例 —— 让你一眼能判

  产出：../05-打标/语言打标工作台.csv
        （你在 Excel 里只填最后两列 ★你的语言判定 / ★你的备注）

【判定规则来自 00-研究设计.md 的 3.1 节】
【怎么运行：看同目录下的《如何运行.md》】
============================================================

改动记录：
  2026-10-17  第 1 版
"""

import os
import re
import sys
import csv

# Windows 控制台防中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE    = os.path.dirname(os.path.abspath(__file__))
RAWDIR  = os.path.join(HERE, '..', '01-原始数据')
OUTDIR  = os.path.join(HERE, '..', '05-打标')
os.makedirs(OUTDIR, exist_ok=True)

# 复用清洗工具箱里的 strip_html（洗 HTML 和 CDATA）
sys.path.insert(0, HERE)
from cy_utils import strip_html


# ============================================================
#  判定规则 —— 和研究设计 3.1 节一一对应
# ============================================================

# A 类：显式声明「这是粤语」
A_WORDS = ['粤语', '粵語', '粤語', '廣東話', '广东话', 'Cantonese', 'Cantonés', 'cantonese']

# B 类：粤语特有字（几乎只出现在粤语文本里）
B_CHARS = set('嘅咁係喺唔嗰啲嘢乜睇冇咗哋佢畀嚟喇吓啩囉嘞噉咪咩')

# 辅助：反向标志（出现这些，基本可确定不是粤语）
BACK_WORDS = ['台語', '台语', '閩南', '闽南', '客家', '講客', '世新', '高雄',
              '国语', '國語', '普通话', 'BL中文', 'GL中文']

# 辅助：地域线索（只用来提醒你，不单独判定）
GEO_WORDS = ['香港', '澳門', '澳门', '廣州', '广州', '廣府', '广府',
             '栋笃笑', '棟篤笑', '港樂', '广东歌', '廣東歌']


def auto_judge(row):
    """
    按 4 个字段判定，返回 (自动判定, 判定依据)。
    判定依据写成「A类「粤语」@简介」这种，让你能直接看到机器凭什么这么判。
    """
    fields = [('节目名', row['节目名']), ('简介', row['节目简介']),
              ('主播', row['主播']),    ('平台', row['平台'])]

    for fname, val in fields:
        if not val:
            continue
        for w in A_WORDS:
            if w in val:
                return '粤语', f'A类「{w}」@{fname}'
        for c in B_CHARS:
            if c in val:
                return '粤语', f'B类「{c}」@{fname}'

    geo = [w for w in GEO_WORDS if any(w in (v or '') for _, v in fields)]
    suffix = f'（地域线索：{"/".join(geo)}）' if geo else ''
    return '非粤语', '无标志' + suffix


def map_form(category):
    """
    官方分类 → 内容形态。这是「形态分层」（研究设计 3.1.1 方案 B）的自动部分。
    苹果的分类体系见 https://podcasters.apple.com/support/1691-apple-podcasts-categories
    """
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
    if c.startswith(('Society', 'Leisure', 'Comedy', 'Health', 'TV',
                     'Business', 'Sports', 'Technology', 'Science',
                     'History', 'other', 'Arts')):
        return '谈话/访谈'
    return '未分类'


# ============================================================
#  写出 Excel 版（带下拉框）
# ============================================================

def write_xlsx(rows, columns, path, drop_col=None):
    """
    生成 .xlsx。

    为什么不让你用 Excel 打开 CSV 再另存为 xlsx？
      那样会经过 Excel 的【类型推断】，把两类值搞坏：
        · 以 @ 开头的单元格  → 可能被当公式，变成 #NAME?
        · 纯数字的 节目ID    → 可能被当数字，显示成科学计数法
      用程序直接写 xlsx，每个值都按【字符串】存，Excel 就没法瞎猜了。

    drop_col: 用它算出下拉框挂在哪一列。
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.worksheet.datavalidation import DataValidation
        from openpyxl.utils import get_column_letter
    except ImportError:
        print('  ⚠️ 没装 openpyxl，跳过 xlsx（CSV 已经生成，不影响）')
        print('     要装的话：pip install openpyxl')
        return False

    wb = Workbook()
    ws = wb.active
    ws.title = '语言打标'

    # 列宽（让表打开就能看清，不用手动拉）
    widths = {'序号': 6, '优先级': 10, '节目ID': 14, '节目名': 34, '主播': 24,
              '集数': 7, '官方分类': 26, '内容形态': 12, '自动判定': 9,
              '判定依据': 24, '简介': 60, '单集标题样例': 60,
              '★你的语言判定': 15, '★你的备注': 22}
    for i, col in enumerate(columns, 1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(col, 14)

    # 表头样式
    head_font = Font(bold=True, color='FFFFFF')
    head_fill = PatternFill('solid', fgColor='305496')
    todo_fill = PatternFill('solid', fgColor='FFF2CC')   # ★列用浅黄底，一眼找到
    thin = Side(style='thin', color='D9D9D9')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for i, col in enumerate(columns, 1):
        c = ws.cell(1, i, col)
        c.font = head_font
        c.fill = head_fill
        c.alignment = Alignment(horizontal='center', vertical='center')
        c.border = border

    # 数据行
    for r, row in enumerate(rows, 2):
        for i, col in enumerate(columns, 1):
            v = row.get(col, '')

            # 集数 存成真正的数字，方便你按集数排序
            if col == '集数' and str(v).isdigit():
                c = ws.cell(r, i, int(v))
            else:
                c = ws.cell(r, i, str(v))

            # 节目ID 强制文本格式（防止被转成科学计数法）
            if col == '节目ID':
                c.number_format = '@'

            # 长文本自动换行
            if col in ('简介', '单集标题样例'):
                c.alignment = Alignment(wrap_text=True, vertical='top')
            else:
                c.alignment = Alignment(vertical='top')

            c.border = border
            if col.startswith('★'):
                c.fill = todo_fill

    # ---- 下拉框：★你的语言判定 只能选这三个值 ----
    claim = columns.index(drop_col) + 1
    letter = get_column_letter(claim)
    dv = DataValidation(
        type='list',
        formula1='"粤语,非粤语,不确定"',
        allow_blank=True,
        showDropDown=False,          # False = 显示下拉箭头（openpyxl 这个参数是反的）
    )
    dv.error = '只能填：粤语 / 非粤语 / 不确定'
    dv.errorTitle = '填错了'
    dv.prompt = '选一个：粤语 / 非粤语 / 不确定'
    dv.promptTitle = '语言判定'
    ws.add_data_validation(dv)
    dv.add(f'{letter}2:{letter}{len(rows) + 1}')

    # ---- 冻结：滚动时序号/优先级/节目ID/节目名一直可见 ----
    ws.freeze_panes = 'E2'

    ws.auto_filter.ref = f'A1:{get_column_letter(len(columns))}{len(rows) + 1}'

    wb.save(path)
    return True


# ============================================================
#  主流程
# ============================================================

def main():
    # ---------- 第 0 步：先确认输出文件没被 Excel 占着 ----------
    # Windows 上一个文件同时只能被一个程序写。Excel 打开 CSV 会占住它，
    # 不提前检查的话，会白等十几秒读完单集表，最后一步才崩。
    locked = []
    for name in ('语言打标工作台.csv', '语言打标工作台.xlsx'):
        p = os.path.join(OUTDIR, name)
        if os.path.exists(p):
            try:
                open(p, 'r+b').close()
            except PermissionError:
                locked.append(name)
    if locked:
        print('✗ 这些文件正被 Excel / WPS 占用，写不进去：')
        for n in locked:
            print(f'    · {n}')
        print()
        print('  → 在 Excel 里把它们关掉，再跑一次。')
        return

    # ---------- 第 1 步：读节目表 ----------
    p_prog = os.path.join(RAWDIR, '内容侧_节目表.csv')
    if not os.path.exists(p_prog):
        print(f'✗ 找不到节目表：{p_prog}')
        print('  请先跑 01-采集粤语播客.py')
        return

    with open(p_prog, encoding='utf-8-sig', newline='') as f:
        progs = list(csv.DictReader(f))
    print(f'读入节目表：{len(progs)} 个节目')

    # ---------- 第 2 步：读单集表，收集每个节目的单集标题 ----------
    p_ep = os.path.join(RAWDIR, '内容侧_单集表.csv')
    ep_titles = {}
    n_ep = 0
    if os.path.exists(p_ep):
        print('读入单集表（有几十 MB，要等十几秒）...')
        with open(p_ep, encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                n_ep += 1
                name = r['所属节目']
                t = r['单集标题']
                if t:
                    ep_titles.setdefault(name, []).append(t)
        print(f'  共 {n_ep} 集，覆盖 {len(ep_titles)} 个节目')

    # ---------- 第 3 步：逐条判定、分档 ----------
    def pick3(name):
        """均匀取 3 条单集标题当样例（取头/中/尾，避免只看到前几集）"""
        lst = ep_titles.get(name, [])
        if not lst:
            return '(无单集)'
        if len(lst) <= 3:
            sel = lst
        else:
            n = len(lst)
            sel = [lst[0], lst[n // 2], lst[-1]]
        return ' ｜ '.join(t[:40] for t in sel)

    def has_ep_signal(name):
        """单集标题里有没有粤语信号（用于待复核堆的二次判定）"""
        lst = ep_titles.get(name, [])
        if not lst:
            return 0, 0
        hit = sum(1 for t in lst
                  if any(w in t for w in A_WORDS) or any(c in t for c in B_CHARS))
        return hit, len(lst)

    rows = []
    for i, r in enumerate(progs, 1):
        verdict, why = auto_judge(r)
        total = int(r['集数']) if (r['集数'] or '').strip().isdigit() else -1

        # ---- 分档：决定这一行要不要你人工介入 ----
        if verdict == '粤语':
            priority = '⑤抽查'                 # 已自动判粤语，你抽 20 个就行
        elif total == 0:
            priority = '③坏数据'               # 0 集，RSS 是空壳/错误页
        else:
            hit, tot = has_ep_signal(r['节目名'])
            if tot and hit / tot >= 0.05:
                priority = '④单集救回'         # 单集标题有粤语信号 → 直接算粤语
            elif any(w in (r['节目名'] or '') + (r['节目简介'] or '')
                     + (r['主播'] or '') for w in BACK_WORDS):
                priority = '②反向标志'         # 台语/客家/世新… → 基本可确认非粤语
            else:
                priority = '①逐个看'           # ★ 只有这些必须你逐个判断

        rows.append({
            '序号':        i,
            '优先级':      priority,
            '节目ID':      r['节目ID'],
            '节目名':      r['节目名'],
            '主播':        r['主播'],
            '集数':        r['集数'],
            '官方分类':    r['官方分类'],
            '内容形态':    map_form(r['官方分类']),
            '自动判定':    verdict,
            '判定依据':    why,
            '简介':        strip_html(r['节目简介'])[:300],
            '单集标题样例': pick3(r['节目名']),
            '★你的语言判定': '',
            '★你的备注':   '',
        })

    # ---------- 第 4 步：排序（最需要你看的排最前）----------
    rows.sort(key=lambda x: (x['优先级'], x['序号']))

    # ---------- 第 5 步：写出 ----------
    columns = ['序号', '优先级', '节目ID', '节目名', '主播', '集数',
               '官方分类', '内容形态', '自动判定', '判定依据',
               '简介', '单集标题样例', '★你的语言判定', '★你的备注']

    p_out = os.path.join(OUTDIR, '语言打标工作台.csv')
    with open(p_out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)

    # 再生成一份 Excel 版（带下拉框），你在这份里填
    p_xlsx = os.path.join(OUTDIR, '语言打标工作台.xlsx')
    xlsx_ok = write_xlsx(rows, columns, p_xlsx, drop_col='★你的语言判定')

    # ---------- 打印汇总 ----------
    from collections import Counter
    cnt = Counter(x['优先级'] for x in rows)
    print()
    print('=' * 56)
    print('分档结果（按这个顺序排在工作台里）')
    print('=' * 56)
    for k in ['①逐个看', '②反向标志', '③坏数据', '④单集救回', '⑤抽查']:
        print(f'  {k}   {cnt.get(k, 0):>4} 个')

    print()
    from collections import Counter as C2
    forms = C2(x['内容形态'] for x in rows)
    print('内容形态分布：')
    for k, v in forms.most_common():
        print(f'  {k:<12} {v:>4}')

    print()
    print(f'  [OK] CSV 版：{p_out}')
    if xlsx_ok:
        print(f'  [OK] Excel 版：{p_xlsx}')
        print('        ↑ 带下拉框，请在这份里填')
    print()
    print('  下一步：')
    print('   1. 双击打开 xlsx（带下拉框的那份）')
    print('   2. 从上往下过，重点看「①逐个看」那一堆')
    print('   3. 只填最后两列：★你的语言判定 / ★你的备注')
    print('      ★你的语言判定 有下拉框，只能选：粤语 / 非粤语 / 不确定')
    print('   4. 存盘（Ctrl+S，保持 xlsx 格式），告诉我，我来做合并')


if __name__ == '__main__':
    main()
