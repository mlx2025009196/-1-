# -*- coding: utf-8 -*-
"""
实战一（补充）：XPath 版豆瓣 Top250 爬虫
与 douban_top250_full2.py（BeautifulSoup 版）形成对照：
- 两种解析方式都使用了，满足作业"多种方式爬取"的要求
- 本脚本用 lxml 的 XPath 解析 10 个列表页，拿到全部 250 部的
  排名 / 片名 / 链接 / 评分 / 评价人数
"""
import time
import requests
import pandas as pd
from lxml import etree

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/153.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# XPath 表达式（对照 BeautifulSoup 版的 find/find_all）
XPATH_ITEM   = '//div[@class="item"]'                        # 每部电影
XPATH_RANK   = './/em/text()'                                # 排名
XPATH_TITLE  = './/div[@class="hd"]/a/span[@class="title"][1]/text()'    # 片名（第一个title）
XPATH_LINK   = './/div[@class="hd"]/a/@href'                 # 详情页链接
XPATH_SCORE  = './/span[@class="rating_num"]/text()'         # 评分
XPATH_VOTES  = './/div[@class="bd"]/div/span[last()]/text()'  # 评价人数（bd下div里最后一个span）


def crawl_page(start):
    """爬一页列表页，用 XPath 解析，返回本页电影列表"""
    url = f"https://movie.douban.com/top250?start={start}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    tree = etree.HTML(resp.text)          # HTML → XPath 可查询的树

    movies = []
    for item in tree.xpath(XPATH_ITEM):
        movies.append({
            "排名":  int(item.xpath(XPATH_RANK)[0]),
            "片名":  item.xpath(XPATH_TITLE)[0],
            "链接":  item.xpath(XPATH_LINK)[0],
            "评分":  float(item.xpath(XPATH_SCORE)[0]),
            "评价人数": int(item.xpath(XPATH_VOTES)[0]
                            .replace("人评价", "").strip()),
        })
    return movies


if __name__ == "__main__":
    all_movies = []
    for start in range(0, 250, 25):
        page = crawl_page(start)
        print(f"start={start}，XPath 解析出 {len(page)} 部")
        all_movies.extend(page)
        time.sleep(3)

    df = pd.DataFrame(all_movies).sort_values("排名")
    df.to_csv("douban_top250_xpath.csv", index=False, encoding="utf-8-sig")
    print(f"\n共 {len(df)} 部，已保存 douban_top250_xpath.csv")
