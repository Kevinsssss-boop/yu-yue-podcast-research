# -*- coding: utf-8 -*-
"""
粤语播客研究 — 文本清洗工具集

这里全是「数据无关」的通用函数：不管后羿导出的 Excel 列名是什么，都能用。
真实的清洗流水线（读哪张表、映射哪一列）等数据到位后再写，那时复用这里的函数。

用法：
    from cy_utils import to_simplified, denoise, cn_num_to_int, content_hash

    >>> to_simplified("廣東話 podcast 真係好聽")
    '广东话 podcast 真係好聽'      # 繁简统一，粤语口语字保留
    >>> cn_num_to_int("1.2万")
    12000

⚠️ 中文 Windows 编码提醒：读写文件一律显式 encoding="utf-8"，
   Excel/CSV 导出常带 BOM，用 encoding="utf-8-sig" 读。
"""

import re
import sys
import html
import hashlib

# ─────────────────────────────────────────────────────────────
# 1. 繁简统一
# ─────────────────────────────────────────────────────────────
try:
    from opencc import OpenCC
    _t2s = OpenCC("t2s")      # 繁体 → 简体
    _s2t = OpenCC("s2t")      # 简体 → 繁体（备用）
except ImportError:            # 没装 opencc 时不至于整个模块崩
    _t2s = _s2t = None


def to_simplified(text):
    """繁体 → 简体。香港/澳门用繁体（廣東話），广东用简体（广东话），不统一会被当成两个词。"""
    if text is None:
        return ""
    text = str(text)
    return _t2s.convert(text) if _t2s else text


# ─────────────────────────────────────────────────────────────
# 1b. 粤语安全的繁简转换（处理 OpenCC 改坏粤语字的问题）
# ─────────────────────────────────────────────────────────────
# 问题的两层：
#   ① 转成扩展区生僻字（如 嗰→𠮶 U+20BB6）—— 字体不支持、分词会错
#   ② 转成常用字但语义混淆（如 係→系，「係」是粤语"是"，「系」是"系统"）
#
# 解决思路（不手写字表，让程序自动找）：
#   ① 用户能看见的「扩展区字」：反向映射是唯一的（𠮶 只可能来自 嗰），
#      所以【转换后】直接 translate 回填即可，不需要占位符。
#   ② 有歧义的（係/系）：【转换前】用占位符保护，转完还原。
#
# 自动发现规则：扫 CJK 基本区（U+4E00–U+9FFF），凡是 t2s 后落到
# U+9FFF 以上的，说明转成了扩展区异体字 —— 这种转换对文本分析纯属损失。
_PUA_PLACEHOLDER = ""   # 私用区，实测全库只占用了 6 个私用区字符，E001 未被占用
_AMBIGUOUS = "係"             # 转换合法但语义会错的粤语功能字

_ext_table = None   # 懒加载：str.translate 用，一次扫完全文，比循环 replace 快得多


def is_rare_cjk(ch):
    """
    True = 生僻/异体字（扩展 A 区 U+3400–4DBF，或扩展 B 区及以上 U+20000+）。
    这些字很多字体显示成方框、分词器也容易切错，属于「转换只会帮倒忙」的情况。
    """
    cp = ord(ch)
    return (0x3400 <= cp <= 0x4DBF) or cp >= 0x20000


def _build_ext_table():
    """
    扫 CJK 三个区，建「生僻字 → 原字」的翻译表（只需建一次，实测共 0.2 秒）。

    三个区都要扫，少一个就漏：
      · 基本区 U+4E00–U+9FFF（嗰→𠮶 这类）
      · 扩展 A U+3400–U+4DBF
      · 扩展 B U+20000–U+2A6DF（𨋢→䢂 这类，粤语「电梯」）
    """
    global _ext_table
    if _ext_table is not None:
        return _ext_table
    mapping = {}
    if _t2s:                                    # 没装 opencc 就跳过
        for lo, hi in ((0x4E00, 0xA000), (0x3400, 0x4DC0), (0x20000, 0x2A6E0)):
            for cp in range(lo, hi):
                src = chr(cp)
                dst = _t2s.convert(src)
                if len(dst) == 1 and dst != src and is_rare_cjk(dst):
                    mapping[ord(dst)] = src      # 𠮶 -> 嗰
    _ext_table = mapping
    return _ext_table


def cantonese_t2s(text):
    """
    繁 → 简，但**不破坏粤语字**。

    比直接 to_simplified() 多两件事：
      · 转换后把扩展区异体字回填（𠮶→嗰、𩠌→餸、𡥧→孻 …）
      · 转换前保护 係，避免变成「系」

    >>> cantonese_t2s("呢個節目真係好聽，我哋一齊食飯")
    '呢个节目真係好听，我哋一齐食饭'
    >>> cantonese_t2s("嗰間舖頭買餸")
    '嗰间铺头买餸'
    """
    if text is None:
        return ""
    t = str(text)
    if not _t2s:
        return t

    table = _build_ext_table()

    # ① 转换前：护住有歧义的字
    t = t.replace(_AMBIGUOUS, _PUA_PLACEHOLDER)

    # ② 繁 → 简
    t = _t2s.convert(t)

    # ③ 转换后：扩展区异体字回填（一次 translate 扫完，性能好）
    if table:
        t = t.translate(table)

    # ④ 还原被保护的字
    t = t.replace(_PUA_PLACEHOLDER, _AMBIGUOUS)
    return t


# ─────────────────────────────────────────────────────────────
# 2. 去噪
# ─────────────────────────────────────────────────────────────
_URL_RE     = re.compile(r"https?://\S+|www\.\S+")
_TOPIC_RE   = re.compile(r"#[^#\s]{1,40}#")            # #话题#
_MENTION_RE = re.compile(r"@[\w一-鿿\-_]{1,30}")  # @某人
_CTRL_RE    = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")  # 控制字符

# 只保留：CJK 汉字 + 英数 + 常见中文标点 + 空白。其余（emoji、特殊符号）全删。
_KEEP_CHARS = (
    "一-鿿㐀-䶿"                          # CJK 基本区 + 扩展 A
    "A-Za-z0-9"
    "，。！？、；：（）《》〈〉【】—…·"      # 中文标点
    "“”‘’"                 # 中文引号 “ ” ‘ ’
)
_KEEP_RE = re.compile("[^" + _KEEP_CHARS + r"\s]")


def denoise(text, keep_topic=False, keep_mention=False, aggressive=False):
    """
    去噪。默认删 URL / #话题# / @用户 / 控制字符。
    - keep_topic=True    保留 #话题#（有时话题词本身是信号）
    - aggressive=True    再删掉 emoji 和一切非汉字/英数/中文标点（做词频/词云前用）
    """
    if text is None:
        return ""
    t = str(text)
    t = _URL_RE.sub(" ", t)
    if not keep_topic:
        t = _TOPIC_RE.sub(" ", t)
    if not keep_mention:
        t = _MENTION_RE.sub(" ", t)
    t = _CTRL_RE.sub(" ", t)
    if aggressive:
        t = _KEEP_RE.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


# 去 HTML 标签（RSS 的简介大量是 HTML 富文本，如 <p style="...">文字</p>）
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
# CDATA 的包裹标记。它本身不是 HTML 标签，_TAG_RE 匹配不到，
# 所以必须单独剥 —— 否则简介开头会残留 "<![CDATA["、结尾残留 "]]>"
_CDATA_OPEN_RE = re.compile(r"<!\[CDATA\[")
_CDATA_CLOSE_RE = re.compile(r"\]\]>")

# 「被截断的标签」：采集时字段超过 30000 字会被 clip，可能正好切在标签中间，
# 于是留下 "<img src=\"data:image/jpeg;base64,..."（永远等不到闭合的 ">"）。
# _TAG_RE 要求有 ">"，所以匹配不到，会残留。
#
# 规则要收窄：只删「< + 字母或斜杠 + 到结尾都没有 >」的。
# 这样不会误伤正文里的 "<3"（爱心）、"<)"（表情）、"<爱上了一个人>"（书名号式强调）。
_UNCLOSED_TAG_RE = re.compile(r"<[a-zA-Z/][^>]*$")


def strip_html(text):
    """
    把 HTML 剥成纯文本。
    播客简介在后台是"富文本"编辑的（带字号/颜色/对齐），RSS 存的就是那段 HTML 原文。

    例：'<p style="color:#333">你好</p>' → '你好'
        '<![CDATA[<p>你好</p>]]>'       → '你好'   ← CDATA 也要剥掉

    ⚠️ 实测：450 个节目里有 90 个（20%）的 RSS 简介带 CDATA 包裹，
       而且往往在 <description> 和 <![CDATA[ 之间夹一个换行。
    """
    if text is None:
        return ""
    t = str(text)
    t = _SCRIPT_STYLE_RE.sub(" ", t)   # 先去掉 <script>/<style> 整块
    # ★ 顺序很重要：CDATA 必须在去标签【之前】剥！
    #   否则 _TAG_RE 的 <[^>]+> 会把 "<![CDATA[纯文本没有标签]]>" 整段吃掉
    #   —— 因为里面没有别的 ">"，正则一路匹配到结尾的 ">"，文字就全没了。
    t = _CDATA_OPEN_RE.sub(" ", t)     # 剥 <![CDATA[
    t = _CDATA_CLOSE_RE.sub(" ", t)    # 剥 ]]>
    t = _TAG_RE.sub(" ", t)            # 再去掉所有完整的 <...> 标签
    t = _UNCLOSED_TAG_RE.sub(" ", t)   # 再删被截断、没有闭合的标签
    t = html.unescape(t)               # &amp; &nbsp; 等还原成正常符号
    return re.sub(r"\s+", " ", t).strip()


# ─────────────────────────────────────────────────────────────
# 3. 带单位数字 → 整数
# ─────────────────────────────────────────────────────────────
_UNIT = {"万": 10_000, "萬": 10_000, "w": 10_000, "W": 10_000,
         "千": 1_000, "k": 1_000, "K": 1_000, "百": 100}
_NUM_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*([万萬wW千kK百]?)")


def cn_num_to_int(s):
    """
    '1.2万'→12000  '10w+'→100000  '3千'→3000  '1,234'→1234  '暂无'→None
    一个字符串里多个数就取第一个（点赞数一般只有一个）。
    """
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    m = _NUM_RE.search(str(s).replace(",", "").replace("，", ""))
    if not m:
        return None
    num, unit = float(m.group(1)), m.group(2)
    try:  # 「万」「萬」等非 ASCII 直接查表
        return int(num * _UNIT.get(unit, 1))
    except (TypeError, ValueError):
        return int(num)


# ─────────────────────────────────────────────────────────────
# 4. 时长 → 秒
# ─────────────────────────────────────────────────────────────
def duration_to_seconds(s):
    """'1:05:30'→3930  '05:30'→330  '90'→90  解析不了返回 None。"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    parts = str(s).strip().split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 1:
        return nums[0]
    return None


# ─────────────────────────────────────────────────────────────
# 5. 去重
# ─────────────────────────────────────────────────────────────
def content_hash(text, normalize=True):
    """评论内容 MD5。normalize=True 先繁简统一+去噪再哈希，避免「同一条不同写法」漏去重。"""
    if text is None:
        return ""
    t = str(text)
    if normalize:
        t = denoise(to_simplified(t), aggressive=True)
    return hashlib.md5(t.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────
# 6. 粤语特有字（jieba 分词用得上，别当停用词删）
# ─────────────────────────────────────────────────────────────
CY_CHARS = set(
    "嘅咁係喺唔嗰啲嘢乜睇冧攰冇咗緊哋俾佢畀哋嚟咗嘅嘞喇囉囖噉"
    "咩哋俾咁嘅唔係喺嗰啲乜嘢睇冧攰冇咗"
)


def contains_cantonese(text):
    """粗判一条文本里有没有粤语口语字（用来快速看粤语浓度）。"""
    if not text:
        return False
    return any(ch in CY_CHARS for ch in str(text))


# ─────────────────────────────────────────────────────────────
# 自测
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:                          # 中文 Windows 控制台防 UnicodeEncodeError
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    cases = [
        ("繁简", to_simplified("廣東話 podcast 真係好聽，好多香港人聽"),
                 to_simplified("广东话 podcast 真係好聽，好多香港人聽")),
        ("去噪", denoise("好聽！ https://t.co/abc @小明 #粤语播客# 真係正 👍"),
                 "好聽！ 真係正 👍"),
        ("激进", denoise("好聽！ 👍🎧", aggressive=True), "好聽！"),
        ("万",   cn_num_to_int("1.2万"), 12000),
        ("w+",   cn_num_to_int("10w+"), 100000),
        ("逗号", cn_num_to_int("1,234"), 1234),
        ("无量", cn_num_to_int("567"), 567),
        ("暂无", cn_num_to_int("暂无"), None),
        ("时长", duration_to_seconds("1:05:30"), 3930),
        ("分秒", duration_to_seconds("05:30"), 330),
        ("粤语", contains_cantonese("呢個節目真係好好聽㗎"), True),
        ("去HTML", strip_html('<p style="color:#333">你好</p>好聽'), "你好 好聽"),
        ("去CDATA", strip_html('<![CDATA[<p>你好</p>]]>'), "你好"),
        # 纯文本 CDATA（里面没有别的 ">"）—— 曾经被 <[^>]+> 整段吃掉，返回空
        ("纯文本CDATA", strip_html('<![CDATA[有知有行出品的首个广播剧]]>'), "有知有行出品的首个广播剧"),
        # 被 clip 截断、没有闭合的标签（采集时切在 30000 字处）
        ("截断标签", strip_html('你好 <span style="color:red;font-fami'), "你好"),
        # 正文里的尖括号不能被误删
        ("尖括号正文", strip_html('我爱你 <3 同 <) 表情'), "我爱你 <3 同 <) 表情"),
        # ---- 粤语安全的繁简转换 ----
        ("粤-繁简",  cantonese_t2s("呢個節目真係好聽"), "呢个节目真係好听"),
        ("粤-嗰",    cantonese_t2s("嗰間舖頭"), "嗰间舖头"),          # 不能变 𠮶
        ("粤-餸孻",  cantonese_t2s("買餸、孻仔"), "买餸、孻仔"),        # 不能变 𩠌/𡥧
        ("粤-係",    cantonese_t2s("呢個係系統嘅問題"), "呢个係系统嘅问题"),  # 係 不能变 系
    ]
    ok = 0
    for name, got, want in cases:
        flag = "✅" if got == want else "❌"
        ok += got == want
        print(f"{flag} {name:<4} got={got!r:<20} want={want!r}")
    print(f"\n{ok}/{len(cases)} 通过")
