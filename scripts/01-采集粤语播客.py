# -*- coding: utf-8 -*-
"""
============================================================
 粤语播客研究 · 采集脚本  （第 2 版 · 支持增量补采）
============================================================

【这个脚本到底在干什么？】
  1) 用「苹果播客」的公开搜索接口，按一批关键词 × 一批地区，搜索播客节目
  2) 再加上「人工种子」清单（关键词搜不到、但你手动指定的节目）
  3) 去重，并【跳过已经采过的】—— 只采新增的
  4) 对每个新节目，下载它的 RSS（RSS 里就是这个节目的全部单集）
  5) 解析成两张表，【追加】到已有 CSV 末尾（老数据不动）：
       · 节目表 —— 1 行 = 1 个节目
       · 单集表 —— 1 行 = 1 集
  6) 放到 ../01-原始数据/ 文件夹里

【增量采集 = 可以反复跑】
  跑第 2 次、第 3 次都不会重复采。脚本会先读一遍已有的节目表，
  已经采过的 RSS 地址直接跳过，只采没见过的。

【你只需要改下面「配置区」的几行】
【怎么运行：看同目录下的《如何运行.md》】
============================================================
"""

# ============================================================
#  配置区 —— 只改这里
# ============================================================

# 要搜索的关键词。注意：繁体「廣東話」命中的是香港/海外那批，和简体不一样
KEYWORDS = ['粤语', '廣東話', '广东话', 'Cantonese', '粤语播客', '廣播劇']

# 要搜索的地区。cn=中国区  hk=香港区  tw=台湾区  us=美国区
# 实测：中国区被限制得厉害，必须加上 hk/tw/us 才能搜全
REGIONS = ['cn', 'hk', 'tw', 'us']

# 每个"关键词 × 地区"最多取多少条（苹果接口上限是 200）
LIMIT = 100

# ------------------------------------------------------------
#  ★ 人工种子清单：关键词搜不到的节目，直接把 RSS 地址写在这里 ★
# ------------------------------------------------------------
# 为什么需要这个？
#   苹果搜索只能按「关键词匹配元数据」。有些粤语播客的元数据里
#   根本不含"粤语/廣東話"（比如「见面倾啦」只写了"栋笃笑"），
#   关键词怎么调都搜不到，只能人工指定。
#
# 格式：(节目名, RSS地址)  —— 一行一个，逗号分隔，别忘引号
# 加进来后，脚本会把它和关键词搜到的结果合并去重，一起采集。
# 已经采过的会自动跳过，所以重复跑也安全。
SEED_FEEDS = [
    ('见面倾啦', 'https://feed.xyzfm.space/8xrynrfhcvuy'),

    # ↓↓↓ 以下 15 个 = 用「粤语口语字出现在节目名里」筛出来的高精度候选 ↓↓↓
    # 「嘅咁係喺唔嗰啲嘢乜睇冇咗」这类字几乎只出现在粤语里，
    # 所以名字带这些字的节目，基本可以确定是粤语节目。
    ('生而為人邊有咁簡單', 'https://feed.firstory.me/rss/user/ckp5k5iy8y0i40873k3rbittm'),
    # ❌ 已剔除「日常8點半—原來係咁」：苹果给的地址
    #    https://podcast.rthk.hk/podcast/830_teaser_i.xml 是个空壳 feed
    #    （只有 <channel>、一个 <item> 都没有，解析出来 0 集）。
    #    实测 RTHK 的几种地址格式全是空壳，属于平台自己的非标准方案，
    #    以后要补 RTHK 的节目得单独处理。
    ('投資唔講廢話', 'https://feeds.soundon.fm/podcasts/e0e275d9-9a69-49c2-8c16-cbdfb914e9e7.xml'),
    ('港一半唔講一半', 'https://anchor.fm/s/69ebdc8c/podcast/rss'),
    ('香港仔ON AIR—講男講女講乜鬼', 'https://www.rti.org.tw/programpodcasturl?id=1729'),
    ('聽多啲廣東歌', 'https://anchor.fm/s/8e45db50/podcast/rss'),
    ('戀咁Talk', 'https://feeds.soundon.fm/podcasts/6bda93ce-adff-4b88-be6e-99d9f0c49bc7.xml'),
    ('齋talk唔X', 'https://feed.firstory.me/rss/user/ckjwxy3nrxtjv08945ep2pdef'),
    ('SCI-FI全面睇', 'http://feeds.feedburner.com/blogspot/SFATW'),
    ('「電影敢咁感」第一季', 'https://feeds.soundon.fm/podcasts/05934ee6-041c-4d55-86b4-7b8d2608c28f.xml'),
    ('「電影敢咁感」第二季', 'https://feeds.soundon.fm/podcasts/585cf9cc-0ea9-4d45-a0be-0866e77a11ca.xml'),
    ('CAPITAL 958 讲呢啲!', 'https://www.omnycontent.com/d/playlist/7740012e-e1bd-4f85-81c4-a7f50047134a/41b09835-56be-427e-a5a4-ac47006deab4/27dfd406-73ff-46ba-b84b-ac47006e3a26/podcast.rss'),
    ('講講吓唔記得', 'https://feeds.acast.com/public/shows/654a5331cce18a00123dd5f3'),
    ('齋吹唔sell-首個香港保險Podcast', 'https://anchor.fm/s/40d32a80/podcast/rss'),
    ('Keep Roll 、嚟多個！', 'https://anchor.fm/s/ff840e54/podcast/rss'),
]

# ★★ 测试开关 ★★
#   True  = 只处理前 3 个新节目，几十秒就能看到结果（第一次跑请保持 True）
#   False = 处理全部新节目
TEST_MODE = False


# ============================================================
#  以下内容不用改（除非你想调参数）
# ============================================================

import os
import re
import sys
import csv
import html
import time
import hashlib
import requests

# Windows 的控制台有时会把中文显示成乱码，这一句是保险
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 找出「这个脚本自己所在的文件夹」，
# 这样不管你在哪个目录运行它，输出路径都不会错
HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, '..', '01-原始数据')
os.makedirs(OUTDIR, exist_ok=True)   # 文件夹不存在就自动创建

# 伪装成普通浏览器 —— 很多网站不喜欢"一看就是机器人"的请求
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36')
}


# ------------------------------------------------------------
#  工具函数（小助手）
# ------------------------------------------------------------

def pick(xml_text, tag):
    """
    从一段 XML 文本里，取出 <tag>……</tag> 中间的内容。
    · 抓不到就返回空字符串（不报错，保证脚本能继续往下跑）
    · RSS 里经常有 <![CDATA[ ... ]]> 包着内容，这里也一并处理掉
    """
    pattern = ('<' + tag + r'[^>]*>'          # 开始标签，比如 <title>
               r'\s*'                         # ★ 允许标签后有换行 —— 见下方说明
               r'(?:<!\[CDATA\[)?'             # 可选的开头 <![CDATA[
               r'(.*?)'                        # 真正的内容（这是我们要的）
               r'(?:\]\]>)?'                   # 可选的结尾 ]]>
               r'</' + tag + '>')              # 结束标签
    m = re.search(pattern, xml_text, re.S)     # re.S 让 . 也能匹配换行
    if not m:
        return ''
    # 把换行、连续的空格压成一个空格，让表格更整齐
    text = re.sub(r'\s+', ' ', m.group(1)).strip()
    # ★ 保险：不管上面的可选 CDATA 有没有匹配上，这里再把 CDATA 标记剥一遍。
    #   起因：有些 RSS 写成 <description>\n<![CDATA[…]]></description>，
    #   标签和 <![CDATA[ 之间夹了换行，导致 group(1) 里残留 "<![CDATA["。
    #   实测 435 个原始节目里有 90 个踩到这个坑。
    text = text.replace('<![CDATA[', ' ').replace(']]>', ' ')
    # 把 &amp; &#39; 这类"网页转义字符"还原成正常符号（& ' 等）
    return html.unescape(re.sub(r'\s+', ' ', text)).strip()


# 单个字段最多保留多少字符。Excel 单元格上限约 32767，所以卡在 30000。
# 注意：这不会丢信息 —— RSS 是源头，随时能重新拉取；而且 3 万字的节目简介，
# 对分析来说早就"信息饱和"了。
MAX_FIELD = 30000


def clip(text, limit=MAX_FIELD):
    """字段太长就截断（防止 Excel 打不开），截断处留个标记，方便你知道被切过"""
    if len(text) > limit:
        return text[:limit] + ' …[已截断]'
    return text


def search_podcasts(keyword, region, limit):
    """调用苹果公开接口搜索播客，返回一个列表（每个元素是一档节目的信息）"""
    url = 'https://itunes.apple.com/search'
    params = {
        'term': keyword,      # 关键词
        'entity': 'podcast',  # 只要"播客"这一类
        'country': region,    # 地区
        'limit': limit,       # 最多多少条
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=25)
        return resp.json().get('results', [])
    except Exception as e:
        print(f'    × 搜索出错（{keyword} / {region}）：{e}')
        return []


def fetch_rss(feed_url):
    """
    下载一个 RSS 源，返回它的文字内容。
    · 会重试 2 次 —— 网络偶尔抖动，第一次超时不代表真的连不上
    · 每次给 20 秒（大部分源 1 秒就回来了，20 秒很宽裕）
    · 两次都失败就返回空字符串，让主流程跳过它、继续下一个，绝不中断
    """
    for attempt in range(2):
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=20)
            resp.encoding = 'utf-8'     # 明确按 UTF-8 解码，避免中文乱码
            return resp.text
        except Exception:
            if attempt == 0:
                time.sleep(2)           # 歇 2 秒，再试一次
    print(f'    × 连不上，已跳过：{feed_url[:60]}')
    return ''


def write_csv(path, rows, columns):
    """
    把一堆字典写成 CSV 文件。
    encoding='utf-8-sig' —— 加了这个，用 Excel 打开才不会中文乱码。
    """
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()    # 先写表头
        writer.writerows(rows)  # 再写每一行


def load_done_feeds(path):
    """
    读一遍已有的「节目表」，把里面已经采过的 RSS 地址收集起来。
    作用：下次跑脚本时，这些节目直接跳过，不重复采。
    文件不存在（第一次跑）就返回一个空集合。
    """
    if not os.path.exists(path):
        return set()
    done = set()
    with open(path, encoding='utf-8-sig', newline='') as f:   # 读的时候要带 sig，因为有 BOM
        for row in csv.DictReader(f):
            feed = (row.get('RSS地址') or '').strip()
            if feed:
                done.add(feed)
    return done


def find_locked_files(paths):
    """
    检查这几个文件能不能写，返回"被占用"的那些。

    为什么要在开头检查？因为 Windows 上一个文件同时只能被一个程序写。
    Excel / WPS 打开 CSV 时会占住它，这时脚本跑到【最后一步】才崩
    （前面下载全白跑）。不如一开始就查，给你一句人话提示。
    """
    locked = []
    for p in paths:
        if not os.path.exists(p):
            continue          # 文件还不存在，稍后会新建，不用管
        try:
            # 用"追加模式"打开只是为了试一下，不写任何东西，不会改到文件
            with open(p, 'a', encoding='utf-8'):
                pass
        except PermissionError:
            locked.append(p)
    return locked


def append_csv(path, rows, columns):
    """
    把新采到的几行【追加】到 CSV 末尾（不覆盖老数据）。

    ⚠️ 这里有个坑：BOM（文件开头那几个隐藏字节）只能出现在文件最开头。
       所以——新建文件时用 utf-8-sig（写 BOM），追加时用 utf-8（不写 BOM）。
       否则会在文件中途插进一个 BOM，把那一行弄乱。
    """
    is_new = not os.path.exists(path)

    # 文件还不存在、这次又没有数据 —— 也建一个只有表头的空文件，
    # 免得你去找「采集失败清单.csv」却发现它不在
    if is_new and not rows:
        write_csv(path, [], columns)
        return

    if not rows:
        return

    encoding = 'utf-8-sig' if is_new else 'utf-8'
    with open(path, 'a', encoding=encoding, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if is_new:
            writer.writeheader()    # 只有新文件才需要写表头
        writer.writerows(rows)      # 老文件直接把新行接在后面


# ------------------------------------------------------------
#  主流程
# ------------------------------------------------------------

def main():

    # 三个输出文件的完整路径
    path_program = os.path.join(OUTDIR, '内容侧_节目表.csv')
    path_episode = os.path.join(OUTDIR, '内容侧_单集表.csv')
    path_failed  = os.path.join(OUTDIR, '采集失败清单.csv')

    # 表头（每张表有哪些列）。
    # ⚠️ 这里必须和已有的 CSV 列【完全一致】—— 增量追加时，
    #    一旦列数对不上，新数据的每一列都会串位。
    PROGRAM_COLUMNS = ['节目ID', '节目名', 'RSS地址', '平台', '主播',
                       '节目简介', '官方分类', '集数', '语言', '主题']
    EPISODE_COLUMNS = ['单集ID', '所属节目', '单集标题', '单集简介',
                       '发布时间', '时长', '音频链接', '集号']
    FAILED_COLUMNS  = ['节目名', 'RSS地址', '原因']

    # ---------- 第 0 步：读已有数据，算出"哪些已经采过了" ----------
    print('=' * 52)
    print('第 0 步：检查已有数据')
    print('=' * 52)

    # 0a) 先确认要写的文件没被 Excel 之类的程序占着。
    #     不查的话，会白下载几百个 RSS，最后一步才崩。
    locked = find_locked_files([path_program, path_episode, path_failed])
    if locked:
        print('  ✗ 下面这些文件正被别的程序占用，写不进去：')
        for p in locked:
            print(f'      · {os.path.basename(p)}')
        print()
        print('  最常见的原因：Excel 或 WPS 正开着它。')
        print('  → 在 Excel 里【关掉这几个表格的窗口】，然后重新跑一次。')
        print('  → 不用退出 Excel，关掉那个文件就行。')
        return

    done_feeds = load_done_feeds(path_program)   # 已采过的 RSS 地址集合

    if done_feeds:
        print(f'  发现已经采过 {len(done_feeds)} 个节目')
        print('  → 这些会【自动跳过】，不重复采')
        print('  → 新采到的会【追加】到文件末尾，老数据一个字节都不动')
    else:
        print('  没有发现已有数据，这次是全量采集')
    print()

    # ---------- 第 1 步：搜索 + 人工种子，收集候选节目 ----------
    print('=' * 52)
    print('第 1 步：收集候选节目')
    print('=' * 52)

    # candidates 是个"字典"：键 = RSS 地址，值 = 节目信息
    # 用字典的好处是天然去重 —— 同一个 RSS 地址只会存一条
    candidates = {}

    # 1a) 关键词 × 地区 搜索
    for kw in KEYWORDS:
        for rg in REGIONS:
            results = search_podcasts(kw, rg, LIMIT)
            newly = 0
            for p in results:
                feed = (p.get('feedUrl') or '').strip()   # 每档节目都带一个 RSS 地址
                if not feed:
                    continue
                if feed in candidates or feed in done_feeds:
                    continue          # 见过 / 采过 —— 跳过
                candidates[feed] = {
                    '节目名':   p.get('collectionName') or p.get('trackName') or '',
                    '苹果ID':   p.get('collectionId', ''),
                    '来源关键词': kw,
                    '来源地区':  rg,
                }
                newly += 1
            print(f'  「{kw}」× {rg} → 返回 {len(results)} 个，其中新的 {newly} 个')
            time.sleep(0.5)   # 每次请求之间歇半秒，对服务器礼貌一点

    # 1b) 人工种子清单
    if SEED_FEEDS:
        print()
        print(f'  人工种子清单（共 {len(SEED_FEEDS)} 个）：')
        for name, feed in SEED_FEEDS:
            feed = (feed or '').strip()
            if not feed:
                continue
            if feed in done_feeds:
                print(f'    · {name}  —— 已采过，跳过')
                continue
            if feed in candidates:
                print(f'    · {name}  —— 本次搜索已包含，跳过')
                continue
            candidates[feed] = {
                '节目名':   name,
                '苹果ID':   '',
                '来源关键词': '人工种子',
                '来源地区':  '',
            }
            print(f'    + {name}')

    print()
    print(f'  >>> 本次需要新采：{len(candidates)} 个节目')
    print(f'      （已采过 {len(done_feeds)} 个，自动跳过）')
    print()

    # 如果没有任何新节目，就没必要往下跑了
    if not candidates:
        print('  没有新节目要采，直接结束。所有数据都是最新的。')
        return

    # ---------- 第 2 步：逐个下载 RSS，解析成两张表 ----------
    feed_list = list(candidates.items())
    if TEST_MODE:
        feed_list = feed_list[:3]       # 测试模式：只跑前 3 个
        print('  ⚠️  当前是【测试模式】，只处理前 3 个节目\n')

    program_rows = []   # 节目表的每一行
    episode_rows = []   # 单集表的每一行
    failed = []         # 下载失败的节目（记下来，方便事后补采）
    empty_feeds = []    # 连上了、但一个单集都没解析出来的节目（多半是地址本身有问题）

    print('=' * 52)
    print('第 2 步：下载并解析每个节目的 RSS')
    print('=' * 52)

    for i, (feed, info) in enumerate(feed_list, 1):
        name = info['节目名']
        print(f'  [{i}/{len(feed_list)}] {name[:32]}')

        xml = fetch_rss(feed)
        if not xml:
            failed.append({'节目名': name, 'RSS地址': feed, '原因': '连接超时/失败'})
            continue

        # 把 XML 切成两块：
        #   · channel 部分（第一个 <item> 之前）= 整个节目的信息
        #   · 每个 <item>……</item> = 一集
        items   = re.findall(r'<item>(.*?)</item>', xml, re.S)
        channel = xml.split('<item>')[0]

        # 给这个节目算一个短编号（用 RSS 地址做 MD5 再取前 12 位）。
        # 用地址而不是节目名做编号 —— 因为节目名可能重复，RSS 地址不会。
        pid = hashlib.md5(feed.encode('utf-8')).hexdigest()[:12]

        # ----- 给「节目表」写一行 -----
        program_rows.append({
            '节目ID':   pid,
            '节目名':   pick(channel, 'title') or name,
            'RSS地址':  feed,
            '平台':     pick(channel, 'copyright') or pick(channel, 'link'),
            '主播':     pick(channel, 'itunes:author'),
            '节目简介': clip(pick(channel, 'description')),
            '官方分类': html.unescape(' / '.join(
                re.findall(r'<itunes:category[^>]*text="([^"]+)"', channel))),
            '集数':     len(items),
            '语言':     '',    # 先留空 → 后面 AI 初标 + 你人工终标
            '主题':     '',    # 先留空 → 同上
        })

        # ----- 给「单集表」写若干行（这一集一集地写）-----
        for item in items:
            m = re.search(r'<enclosure[^>]*url="([^"]+)"', item)   # 音频文件的地址
            episode_rows.append({
                '单集ID':   pick(item, 'guid') or pick(item, 'link'),
                '所属节目': pick(channel, 'title') or name,
                '单集标题': pick(item, 'title'),
                '单集简介': clip(pick(item, 'description')),
                '发布时间': pick(item, 'pubDate'),
                '时长':     pick(item, 'itunes:duration'),
                '音频链接': m.group(1) if m else '',
                '集号':     pick(item, 'itunes:episode'),
            })

        # ★ 保险：连上了、但一集都没解析出来 —— 说明这个 RSS 地址有问题
        #   （常见于电台/平台的"空壳 feed"：只有节目信息，没有单集）
        if not items:
            empty_feeds.append({'节目名': name, 'RSS地址': feed, '原因': 'feed 里没有任何单集'})
            print('          ⚠️  这个 feed 一集都没有！地址可能有问题，已记录')
        else:
            print(f'          → 解析出 {len(items)} 集')
        time.sleep(0.5)

    # ---------- 第 3 步：追加写入 CSV ----------
    print()
    print('=' * 52)
    print('第 3 步：保存结果（追加到已有文件末尾）')
    print('=' * 52)

    # 两种"没采好"的情况合并进同一张失败清单，方便你一次性排查
    all_failed = failed + empty_feeds

    append_csv(path_program, program_rows, PROGRAM_COLUMNS)
    append_csv(path_episode, episode_rows, EPISODE_COLUMNS)
    append_csv(path_failed,  all_failed,    FAILED_COLUMNS)

    print(f'  [OK] 新增节目：{len(program_rows)} 行  →  {os.path.basename(path_program)}')
    print(f'  [OK] 新增单集：{len(episode_rows)} 行  →  {os.path.basename(path_episode)}')
    print(f'  [OK] 失败清单：{len(all_failed)} 个节目  →  {os.path.basename(path_failed)}')
    print()
    print(f'  现在节目表共 {len(done_feeds) + len(program_rows)} 个节目。')

    if all_failed:
        print()
        print(f'  ⚠️  有 {len(all_failed)} 个节目没采好，已记进「采集失败清单.csv」：')
        if failed:
            print(f'       · {len(failed)} 个是连不上（域名被墙/停运）')
        if empty_feeds:
            print(f'       · {len(empty_feeds)} 个是 feed 里没有单集（地址本身有问题）')
        print('     都不影响其他节目，想看漏了谁就打开那个文件。')

    if TEST_MODE:
        print()
        print('  ★ 确认没问题后，把脚本最上面的 TEST_MODE 改成 False，')
        print('    再跑一次，就能采集全部节目了。')


# 这是 Python 的固定写法：直接运行这个文件时，就执行 main()
if __name__ == '__main__':
    main()
