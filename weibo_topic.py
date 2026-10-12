# -*- coding: utf-8 -*-
"""
实战三：微博话题爬虫
话题：#中国航天#（正能量话题）
爬三层：话题博文 → 一级评论 → 二级评论
输出：weibo_posts.csv / weibo_comments.csv / weibo_sub_comments.csv（分表存储）
"""
import re
import time
import random
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import quote

# ================= 可调参数 =================
TOPIC = "#中国航天#"       # 要爬的话题
POST_PAGES = 12            # 爬博文几页（每页10条）
COMMENTS_PER_POST = 50     # 每条博文最多爬多少条评论
SUB_PER_COMMENT = 20       # 每条评论最多爬多少条二级评论
COOKIE_FILE = "weibo_cookie.txt"

# ================= 请求头（伪装手机浏览器 + 带上你的登录Cookie） =================
with open(COOKIE_FILE, encoding="utf-8") as f:
    COOKIE = f.read().strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Referer": "https://m.weibo.cn/",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": COOKIE,
}

session = requests.Session()
session.headers.update(HEADERS)


# ================= 工具函数 =================
def api_get(url):
    """请求接口，失败自动重试3次"""
    for i in range(3):
        try:
            r = session.get(url, timeout=15)
            d = r.json()
            if d.get("ok") == 1:
                return d
            print(f"    接口返回异常 ok={d.get('ok')}，等5秒重试...")
        except Exception as e:
            print(f"    请求出错: {type(e).__name__}，等5秒重试...")
        time.sleep(5)
    return None


def strip_html(text):
    """去掉微博文本里的HTML标签（表情、@链接等）"""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def parse_time(s):
    """'Sat Oct 11 20:08:31 +0800 2026' → '2026-10-11 20:08:31'"""
    try:
        return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return s


def ip_of(comment):
    """评论的 source 字段就是IP属地：'来自 辽宁' → '辽宁'"""
    src = comment.get("source", "")
    return src.replace("来自", "").strip() if src else ""


# ================= 第一层：话题博文 =================
def crawl_posts():
    posts = []
    seen_mid = set()                     # 去重：翻页时同一博文可能重复出现
    for page in range(1, POST_PAGES + 1):
        url = ("https://m.weibo.cn/api/container/getIndex"
               "?containerid=100103type%3D61%26q%3D" + quote(TOPIC) +
               "%26t%3D0&page=" + str(page))
        d = api_get(url)
        if not d:
            print(f"第 {page} 页博文获取失败，跳过")
            continue

        cards = d.get("data", {}).get("cards", [])
        got = 0
        for c in cards:
            mb = c.get("mblog")
            if not mb or mb["mid"] in seen_mid:
                continue
            seen_mid.add(mb["mid"])
            got += 1

            # 形式判断：page_info.type=video 是视频，有 pics 是图片，否则文字
            if (mb.get("page_info") or {}).get("type") == "video":
                form = "视频"
            elif mb.get("pics"):
                form = "图片"
            else:
                form = "文字"

            posts.append({
                "博文id": mb["mid"],
                "发布者": mb["user"]["screen_name"],
                "发布时间": parse_time(mb.get("created_at", "")),
                "微博内容": strip_html(mb.get("text", "")),
                "形式": form,
                "转发数": mb.get("reposts_count", 0),
                "评论数": mb.get("comments_count", 0),
                "点赞数": mb.get("attitudes_count", 0),
            })
        print(f"博文第 {page} 页：{got} 条")
        time.sleep(random.uniform(1.0, 2.0))
    return posts


# ================= 第二层：一级评论 =================
def crawl_comments(mid, limit):
    comments = []
    seen_cmt = set()                     # 去重：同一博文不重复入库
    max_id, max_id_type = 0, 0
    while len(comments) < limit:
        url = f"https://m.weibo.cn/comments/hotflow?id={mid}&mid={mid}"
        if max_id:
            url += f"&max_id={max_id}&max_id_type={max_id_type}"
        else:
            url += "&max_id_type=0"
        d = api_get(url)
        if not d:
            break
        data = d.get("data", {})
        cmts = data.get("data", [])
        if not cmts:
            break
        for c in cmts:
            if c["id"] in seen_cmt:      # 去重
                continue
            seen_cmt.add(c["id"])
            comments.append({
                "评论id": c["id"],
                "博文id": mid,                      # 外键：属于哪条博文
                "评论人": c["user"]["screen_name"],
                "评论内容": strip_html(c.get("text", "")),
                "评论时间": parse_time(c.get("created_at", "")),
                "评论人IP": ip_of(c),
                "二级评论数": c.get("total_number", 0),
            })
        max_id = data.get("max_id", 0)
        max_id_type = data.get("max_id_type", 0)
        if not max_id:
            break
        time.sleep(random.uniform(1.0, 2.0))
    return comments[:limit]


# ================= 第三层：二级评论 =================
def crawl_sub_comments(mid, cid, limit):
    subs = []
    seen_sub = set()                     # 去重：同一二级评论不重复入库
    max_id, max_id_type = 0, 0
    while len(subs) < limit:
        url = f"https://m.weibo.cn/comments/hotflow?id={mid}&mid={mid}&cid={cid}"
        if max_id:
            url += f"&max_id={max_id}&max_id_type={max_id_type}"
        else:
            url += "&max_id_type=0"
        d = api_get(url)
        if not d:
            break
        data = d.get("data", {})
        cmts = data.get("data", [])
        if not cmts:
            break
        for c in cmts:
            if c["id"] in seen_sub:      # 去重
                continue
            seen_sub.add(c["id"])
            text = strip_html(c.get("text", ""))
            text = re.sub(r"^回复@.*?:", "", text)     # 去掉 '回复@某某:' 前缀
            subs.append({
                "二级评论id": c["id"],
                "父评论id": cid,                       # 外键：挂在哪条一级评论下
                "博文id": mid,
                "二级评论人": c["user"]["screen_name"],
                "二级评论内容": text,
                "二级评论时间": parse_time(c.get("created_at", "")),
                "二级评论人IP": ip_of(c),
            })
        max_id = data.get("max_id", 0)
        max_id_type = data.get("max_id_type", 0)
        if not max_id:
            break
        time.sleep(random.uniform(1.0, 2.0))
    return subs[:limit]


# ================= 主流程 =================
if __name__ == "__main__":
    print(f"===== 实战三：微博话题爬虫 话题 {TOPIC} =====\n")

    print("【第一层】爬话题博文...")
    posts = crawl_posts()
    print(f"共拿到 {len(posts)} 条博文\n")

    print("【第二层】爬评论...")
    all_comments = []
    all_subs = []
    for i, p in enumerate(posts, 1):
        if p["评论数"] <= 0:
            continue
        print(f"  ({i}/{len(posts)}) 博文 {p['博文id']}（{p['发布者']}）评论数 {p['评论数']}，爬取中...")
        cmts = crawl_comments(p["博文id"], min(COMMENTS_PER_POST, p["评论数"]))
        all_comments.extend(cmts)
        time.sleep(random.uniform(1.0, 2.0))

        # 【第三层】对有二级评论的一级评论，爬取二级评论
        for c in cmts:
            if c["二级评论数"] > 0:
                subs = crawl_sub_comments(c["博文id"], c["评论id"],
                                          min(SUB_PER_COMMENT, c["二级评论数"]))
                all_subs.extend(subs)
                time.sleep(random.uniform(1.0, 2.0))

    print(f"\n博文 {len(posts)} 条，一级评论 {len(all_comments)} 条，二级评论 {len(all_subs)} 条")

    # 分表存储（三个CSV对应MySQL的三张表）
    pd.DataFrame(posts).to_csv("weibo_posts.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(all_comments).to_csv("weibo_comments.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(all_subs).to_csv("weibo_sub_comments.csv", index=False, encoding="utf-8-sig")
    print("已保存：weibo_posts.csv / weibo_comments.csv / weibo_sub_comments.csv")
