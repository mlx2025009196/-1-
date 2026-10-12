# -*- coding: utf-8 -*-
"""
把三个实战的 CSV 导入本地 MySQL8
库：crawler_data
表：douban_top250 / weibo_posts / weibo_comments / weibo_sub_comments
"""
import math
import pandas as pd
import pymysql

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "123456",
    "port": 3306,
    "charset": "utf8mb4",
}
DB_NAME = "crawler_data"


def clean(val):
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def read_csv(path):
    df = pd.read_csv(path)
    for col in df.columns:
        if "时间" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        if df[col].dtype.name == "string":
            df[col] = df[col].astype(object)
    return df


def quote_cols(cols):
    """给列名加反引号，防止特殊字符（如 制片国家/地区）出错"""
    return ", ".join(f"`{c}`" for c in cols)


def connect():
    conn = pymysql.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute(f"USE {DB_NAME}")
    conn.commit()
    return conn


def run(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def insert_many(conn, table, cols, rows):
    col_str = quote_cols(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT IGNORE INTO `{table}` ({col_str}) VALUES ({placeholders})"
    rows = [[clean(r[c]) for c in cols] for r in rows]
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()


def main():
    conn = connect()

    print("[1/4] 导入 douban_top250")
    run(conn, """
    CREATE TABLE IF NOT EXISTS `douban_top250` (
        `排名` INT PRIMARY KEY,
        `电影名称` VARCHAR(100),
        `年份` INT,
        `导演` TEXT,
        `编剧` TEXT,
        `主演` TEXT,
        `类型` VARCHAR(100),
        `制片国家/地区` VARCHAR(100),
        `语言` VARCHAR(100),
        `上映日期` VARCHAR(100),
        `片长` VARCHAR(50),
        `又名` TEXT,
        `IMDb` VARCHAR(20),
        `豆瓣评分` FLOAT,
        `评价人数` INT,
        `五星` FLOAT,
        `四星` FLOAT,
        `三星` FLOAT,
        `两星` FLOAT,
        `一星` FLOAT,
        `剧情简介` TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    df = read_csv("douban_top250_full.csv")
    insert_many(conn, "douban_top250", df.columns.tolist(), df.to_dict("records"))

    print("[2/4] 导入 weibo_posts")
    run(conn, """
    CREATE TABLE IF NOT EXISTS `weibo_posts` (
        `博文id` BIGINT PRIMARY KEY,
        `发布者` VARCHAR(100),
        `发布时间` DATETIME,
        `微博内容` TEXT,
        `形式` VARCHAR(20),
        `转发数` INT,
        `评论数` INT,
        `点赞数` INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    df = read_csv("weibo_posts.csv")
    insert_many(conn, "weibo_posts", df.columns.tolist(), df.to_dict("records"))

    print("[3/4] 导入 weibo_comments")
    run(conn, """
    CREATE TABLE IF NOT EXISTS `weibo_comments` (
        `评论id` BIGINT PRIMARY KEY,
        `博文id` BIGINT,
        `评论人` VARCHAR(100),
        `评论内容` TEXT,
        `评论时间` DATETIME,
        `评论人IP` VARCHAR(50),
        `二级评论数` INT,
        FOREIGN KEY (`博文id`) REFERENCES `weibo_posts`(`博文id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    df = read_csv("weibo_comments.csv")
    insert_many(conn, "weibo_comments", df.columns.tolist(), df.to_dict("records"))

    print("[4/4] 导入 weibo_sub_comments")
    run(conn, """
    CREATE TABLE IF NOT EXISTS `weibo_sub_comments` (
        `二级评论id` BIGINT PRIMARY KEY,
        `父评论id` BIGINT,
        `博文id` BIGINT,
        `二级评论人` VARCHAR(100),
        `二级评论内容` TEXT,
        `二级评论时间` DATETIME,
        `二级评论人IP` VARCHAR(50),
        FOREIGN KEY (`父评论id`) REFERENCES `weibo_comments`(`评论id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    df = read_csv("weibo_sub_comments.csv")
    insert_many(conn, "weibo_sub_comments", df.columns.tolist(), df.to_dict("records"))

    conn.close()
    print("\n全部导入完成！库名：crawler_data")


if __name__ == "__main__":
    main()
