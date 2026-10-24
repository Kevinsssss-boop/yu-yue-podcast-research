# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 导出喜马拉雅专辑链接  （第 1 版）
============================================================

【这个脚本在干什么？】
  从清洗后的节目表里，把「喜马拉雅」那一批节目挑出来，
  生成可以直接粘进后羿采集器的专辑页 URL 列表。

【为什么能做到「不用一个一个搜」】
  喜马拉雅的 RSS 地址本身就带着专辑 ID：

      http://www.ximalaya.com/album/13547886.xml
                                  ^^^^^^^^
                                  这就是专辑号

  把结尾的 .xml 去掉，就是专辑网页：

      https://www.ximalaya.com/album/13547886

  所以 57 个节目的专辑页链接，我们的数据里本来就有，不需要去搜。

【产出两个文件】
  06-听众侧/喜马拉雅专辑链接.csv     ← 带节目名/集数/形态，方便你核对
  06-听众侧/喜马拉雅专辑URL列表.txt  ← 纯 URL，一行一个，直接粘进后羿

【怎么运行】
  在本目录下打开 PowerShell，输入：
      python 04-导出喜马拉雅专辑链接.py
"""

import os
import re
import sys
import csv

# Windows 控制台防中文乱码（不写这行，print 中文会崩）
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE   = os.path.dirname(os.path.abspath(__file__))
INDIR  = os.path.join(HERE, '..', '02-清洗后数据')
OUTDIR = os.path.join(HERE, '..', '06-听众侧')
os.makedirs(OUTDIR, exist_ok=True)

# 从 RSS 地址里抠专辑 ID 的正则
#   http://www.ximalaya.com/album/13547886.xml  →  13547886
#   注意 (\d+) 只匹配数字，后面接 .xml 或 / 都行
_ALBUM_ID_RE = re.compile(r'album/(\d+)')

# 专辑网页的地址模板
ALBUM_URL_TPL = 'https://www.ximalaya.com/album/{}'

# 手工补漏：有些节目的 RSS 走的是第三方代理（wavpub.com 之类），
# 地址里压根没有喜马拉雅的专辑号，程序抠不出来，只能人工查一次填在这里。
# 格式：'节目名（必须和节目表里完全一致）': '专辑ID'
MANUAL_FIX = {
    # RSS 是 https://s1.proxy.wavpub.com/yueyubaihuaza.xml，只能去喜马拉雅搜出来
    '粤语白话杂 | 非典型广东佬播客': '31668016',
}


def main():
    p_in = os.path.join(INDIR, '节目表_粤语.csv')
    if not os.path.exists(p_in):
        print(f'✗ 找不到节目表：{p_in}')
        print('  请先跑 03-清洗数据.py')
        return

    with open(p_in, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    print(f'读入清洗后节目表：{len(rows)} 个节目')

    # ---------- 挑出喜马拉雅的 ----------
    xm = [r for r in rows if r['平台'] == '喜马拉雅']
    print(f'其中喜马拉雅：{len(xm)} 个')

    # ---------- 逐个抠专辑 ID ----------
    ok_rows   = []   # 抠成功的
    fail_rows = []   # 抠失败的（RSS 格式不对，或没有 album 路径）

    for r in xm:
        rss = (r.get('RSS地址') or '').strip()
        m = _ALBUM_ID_RE.search(rss)

        # 先从 RSS 里抠；抠不到就查手工补漏表
        if m:
            album_id = m.group(1)
        elif r['节目名'] in MANUAL_FIX:
            album_id = MANUAL_FIX[r['节目名']]
        else:
            fail_rows.append((r, rss))
            continue
        ok_rows.append({
            '节目名':   r['节目名'],
            '集数':     r['集数'],
            '内容形态': r['内容形态'],
            '主播':     r['主播'],
            '专辑页URL': ALBUM_URL_TPL.format(album_id),
            '专辑ID':   album_id,
        })

    # ---------- 按集数从多到少排（先采大的，万一中断也有收获）----------
    # 集数是字符串，要转 int 才能正确排序；转不了的当 0
    def _n(row):
        try:
            return int(row['集数'])
        except (TypeError, ValueError):
            return 0

    ok_rows.sort(key=_n, reverse=True)

    # ---------- 写 CSV（utf-8-sig：带 BOM，Excel 双击打开不乱码）----------
    p_csv = os.path.join(OUTDIR, '喜马拉雅专辑链接.csv')
    columns = ['节目名', '集数', '内容形态', '主播', '专辑页URL', '专辑ID']
    with open(p_csv, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(ok_rows)

    # ---------- 写纯 URL 列表（后羿的「批量 URL」模式直接吃这个）----------
    p_txt = os.path.join(OUTDIR, '喜马拉雅专辑URL列表.txt')
    with open(p_txt, 'w', encoding='utf-8', newline='') as f:
        for row in ok_rows:
            f.write(row['专辑页URL'] + '\n')

    # ---------- 打印结果 ----------
    print()
    print('=' * 60)
    print(f'[OK] 抠出 {len(ok_rows)} 个专辑链接（按集数从多到少）')
    print('=' * 60)

    total_eps = sum(_n(r) for r in ok_rows)
    print(f'这些节目合计 {total_eps} 集')
    print()
    print('集数最多的 10 个：')
    for r in ok_rows[:10]:
        print(f"  {_n(r):>5}集  {r['内容形态']:<8}  {r['节目名'][:28]}")

    # 抠失败的单独报，别静默丢掉
    if fail_rows:
        print()
        print(f'⚠️ 有 {len(fail_rows)} 个节目的 RSS 里没找到专辑 ID：')
        for r, rss in fail_rows:
            print(f"  · {r['节目名'][:30]}")
            print(f"      RSS = {rss[:70]}")
        print('  这些需要手动去喜马拉雅搜一下补上。')

    print()
    print(f'  → {p_csv}')
    print(f'  → {p_txt}')
    print()
    print('下一步：')
    print('  1. 先打开任意一个专辑页，确认列表上有没有「播放量」这一列')
    print('  2. 在后羿里用「批量 URL」模式，把那 57 行 URL 粘进去')
    print('  3. 采「单集标题 / 播放量 / 发布时间 / 时长」四个字段')
    print('     （如果播放量在列表页就有，就不要开深度采集）')


if __name__ == '__main__':
    main()
