# -*- coding: utf-8 -*-
"""
实战三配图：#中国航天# 话题 每小时评论数柱状图
数据：weibo_comments.csv（一级评论）+ weibo_sub_comments.csv（二级评论）
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# 中文字体（Windows 自带微软雅黑，防止中文变方框）
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 读两级评论，合并到一张图上对比
c1 = pd.read_csv("weibo_comments.csv")
c2 = pd.read_csv("weibo_sub_comments.csv")

c1["小时"] = pd.to_datetime(c1["评论时间"]).dt.floor("h")
c2["小时"] = pd.to_datetime(c2["二级评论时间"]).dt.floor("h")

cnt1 = c1.groupby("小时").size()
cnt2 = c2.groupby("小时").size()

hours = sorted(set(cnt1.index) | set(cnt2.index))
v1 = [int(cnt1.get(h, 0)) for h in hours]
v2 = [int(cnt2.get(h, 0)) for h in hours]
labels = [h.strftime("%m-%d %H时") for h in hours]

plt.figure(figsize=(14, 6))
plt.bar(range(len(hours)), v1, label="一级评论", color="#4C72B0")
plt.bar(range(len(hours)), v2, bottom=v1, label="二级评论", color="#DD8452")
plt.xticks(range(len(hours)), labels, rotation=60, fontsize=8)
plt.xlabel("时间（小时）")
plt.ylabel("评论条数")
plt.title("#中国航天# 话题每小时评论数分布（爬取样本）")
plt.legend()
plt.tight_layout()
plt.savefig("每小时评论数柱状图.png", dpi=150)
print(f"一级评论 {len(c1)} 条，二级评论 {len(c2)} 条")
print(f"覆盖 {len(hours)} 个小时段，已保存：每小时评论数柱状图.png")
