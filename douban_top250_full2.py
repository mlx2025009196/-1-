import os
import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/153.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

CSV_FILE = "douban_top250_full.csv"
MAX_NEW = 70               # 每次最多新爬 70 部，不碰限流红线
WAIT_RANGE = (5.0, 9.0)     # 每页等 5~9 秒


def parse_info_block(info):
    labels = ["导演", "编剧", "主演", "类型", "制片国家/地区",
              "语言", "上映日期", "片长", "又名", "IMDb"]
    data = {label: "" for label in labels}

    for label_span in info.find_all("span", class_="pl"):
        label_text = label_span.get_text(strip=True).rstrip(":：")
        if label_text not in labels:
            continue

        value_parts = []
        for sibling in label_span.next_siblings:
            if getattr(sibling, "name", None) == "br":
                break
            if getattr(sibling, "name", None) == "span" and "pl" in (sibling.get("class") or []):
                break
            if hasattr(sibling, "get_text"):
                value_parts.append(sibling.get_text())
            else:
                value_parts.append(str(sibling))

        data[label_text] = "".join(value_parts).strip(":： ")

    return data


def get_movie_links():
    links = []
    for start in range(0, 250, 25):
        url = f"https://movie.douban.com/top250?start={start}"
        resp = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("div", class_="item")
        print(f"列表页 start={start}，拿到 {len(items)} 部")
        for item in items:
            rank = item.find("em").text
            link = item.find("div", class_="hd").a["href"]
            links.append({"排名": rank, "链接": link})
        time.sleep(3)
    return links


def fetch_soup(driver, url, max_retry=3):
    """请求页面：卡死等60秒重试，被限流等120秒重试，绝不崩溃"""
    for attempt in range(1, max_retry + 1):
        try:
            driver.get(url)
        except Exception:
            print(f"    页面卡住（第 {attempt} 次），等 60 秒重试...")
            time.sleep(60)
            continue
        time.sleep(random.uniform(*WAIT_RANGE))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        if soup.find("span", property="v:itemreviewed") is not None:
            return soup
        print(f"    没拿到正常页面（第 {attempt} 次），等 120 秒重试...")
        time.sleep(120)
    return None


def parse_soup(soup):
    name = soup.find("span", property="v:itemreviewed").text
    year = soup.find("span", class_="year").text.strip("()")
    score = float(soup.find("strong", class_="rating_num").text)
    votes = int(soup.find("span", property="v:votes").text)

    pers = soup.find_all("span", class_="rating_per")

    def to_rate(i):
        if len(pers) > i:
            return round(float(pers[i].text.rstrip("%")) / 100, 4)
        return None

    info_dict = parse_info_block(soup.find("div", id="info"))

    summary_tag = soup.find("span", property="v:summary")
    summary = summary_tag.get_text(strip=True) if summary_tag else ""
    summary = summary.replace("©豆瓣", "").strip()

    return {
        "电影名称": name,
        "年份": year,
        "导演": info_dict.get("导演", ""),
        "编剧": info_dict.get("编剧", ""),
        "主演": info_dict.get("主演", ""),
        "类型": info_dict.get("类型", ""),
        "制片国家/地区": info_dict.get("制片国家/地区", ""),
        "语言": info_dict.get("语言", ""),
        "上映日期": info_dict.get("上映日期", ""),
        "片长": info_dict.get("片长", ""),
        "又名": info_dict.get("又名", ""),
        "IMDb": info_dict.get("IMDb", ""),
        "豆瓣评分": score,
        "评价人数": votes,
        "五星": to_rate(0),
        "四星": to_rate(1),
        "三星": to_rate(2),
        "两星": to_rate(3),
        "一星": to_rate(4),
        "剧情简介": summary,
    }


def save_csv(results):
    df = pd.DataFrame(results)
    cols = ["排名"] + [c for c in df.columns if c != "排名"]
    df = df[cols]
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    print("===== 第一层：爬列表页 =====")
    movie_links = get_movie_links()
    print(f"共 {len(movie_links)} 个详情页\n")

    results = []
    done = set()
    if os.path.exists(CSV_FILE):
        old = pd.read_csv(CSV_FILE)
        results = old.to_dict("records")
        done = {str(r["排名"]) for r in results}
        print(f"发现已有进度，{len(done)} 部已完成\n")

    print("===== 第二层：爬详情页 =====")
    opts = Options()
    opts.binary_location = r"D:\selenium_cache\chrome\win64\153.0.8010.52\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    service = Service(r"D:\selenium_cache\chromedriver\win64\153.0.8010.52\chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(90)   # 单页最多等90秒

    new_count = 0
    failed = []

    for item in movie_links:
        rank = item["排名"]
        url = item["链接"]

        if rank in done:
            continue

        if new_count >= MAX_NEW:
            print(f"\n本次已爬 {new_count} 部，主动收工（不碰限流红线）")
            print("过 2~3 小时或明早再运行一次本脚本，会自动接着爬")
            break

        print(f"[{rank}/250] 抓取中...（本次第 {new_count + 1} 部）")
        soup = fetch_soup(driver, url)
        if soup is None:
            print("  !! 重试多次仍失败，先跳过")
            failed.append(rank)
            continue

        try:
            detail = parse_soup(soup)
        except Exception as e:
            print(f"  !! 解析失败: {e}")
            failed.append(rank)
            continue

        detail["排名"] = rank
        results.append(detail)
        done.add(rank)
        new_count += 1
        save_csv(results)

    driver.quit()
    save_csv(results)

    print(f"\n本次新爬 {new_count} 部，总计完成 {len(results)} / 250 部")
    if failed:
        print("失败的排名:", failed)
    if len(results) < 250:
        print(f"还剩 {250 - len(results)} 部，过 2~3 小时或明早再运行一次即可")
    else:
        print("250 部全部完成！实战一数据到手")
