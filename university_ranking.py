import requests
import pandas as pd

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
}

url = "https://www.shanghairanking.cn/api/pub/v1/bcur?bcur_type=11&year=2024"
resp = requests.get(url, headers=headers)
data = resp.json()          # 接口返回 JSON，直接 .json() 变成字典

rankings = data["data"]["rankings"]
print(f"共拿到 {len(rankings)} 所大学")

rows = []
for univ in rankings:
    rows.append({
        "排名": univ["ranking"],
        "学校名称": univ["univNameCn"],
        "英文名称": univ["univNameEn"],
        "省份": univ["province"],
        "评分": univ["score"],
        "办学层次": "/".join(univ["univTags"]),   # 列表拼成字符串
    })

df = pd.DataFrame(rows)
df.to_csv("university_ranking_2024.csv", index=False, encoding="utf-8-sig")
print("已保存 university_ranking_2024.csv")
print(df.head())