# build.py

import re
import pandas as pd
from pathlib import Path
import mysql.connector as mc

PARQUET_PATH = Path(__file__).resolve().parent / "database" / "libgub.zstd.parquet"

def _norm(name):
    n = name.strip().replace("\ufeff", "")
    low = n.lower()
    m = {
        "id": "ID",
        "title": "Title",
        "author": "Author",
        "year": "Year",
        "edition": "Edition",
        "md5": "MD5",
        "filesize": "Filesize",
        "extension": "Extension",
        "ext": "Extension",
        "identifier": "Identifier",
        "isbn": "Identifier",
        "doi": "Identifier",
    }
    return m.get(low, re.sub(r"\W+", "_", n).strip("_") or "col")

def build_db(
    host="localhost",
    user="root",
    password="",
    db="libgub",
    table="libgub",
    batch_size=50_000,
):
    df = pd.read_parquet(PARQUET_PATH)
    src_cols = list(df.columns)
    cols = [_norm(c) for c in src_cols]

    conn = mc.connect(host=host, user=user, password=password, autocommit=True)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cur.execute(f"USE `{db}`;")

    defs = []
    for c in cols:
        if c == "ID":
            defs.append("`ID` BIGINT NULL")
        elif c == "Filesize":
            defs.append("`Filesize` BIGINT NULL")
        elif c == "Year":
            defs.append("`Year` VARCHAR(32) NULL")
        else:
            defs.append(f"`{c}` MEDIUMTEXT NULL")

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS `{table}` (
          `_pk` BIGINT NOT NULL AUTO_INCREMENT,
          {", ".join(defs)},
          PRIMARY KEY (`_pk`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    col_list = ", ".join(f"`{c}`" for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))
    ins = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"

    d = df.to_dict(orient="list")
    n = len(df)

    for i0 in range(0, n, batch_size):
        i1 = min(i0 + batch_size, n)
        rows = []
        for i in range(i0, i1):
            rows.append(tuple(d[src_cols[j]][i] for j in range(len(src_cols))))
        cur.executemany(ins, rows)

    for idx in ("ft_title", "ft_author", "idx_ext", "idx_year"):
        try:
            cur.execute(f"ALTER TABLE `{table}` DROP INDEX `{idx}`;")
        except Exception:
            pass

    cur.execute(f"ALTER TABLE `{table}` ADD FULLTEXT INDEX `ft_title` (`Title`);")
    cur.execute(f"ALTER TABLE `{table}` ADD FULLTEXT INDEX `ft_author` (`Author`);")
    try:
        cur.execute(f"CREATE INDEX `idx_ext` ON `{table}` (`Extension`(8));")
    except Exception:
        pass
    try:
        cur.execute(f"CREATE INDEX `idx_year` ON `{table}` (`Year`(8));")
    except Exception:
        pass

    cur.execute(f"SELECT COUNT(*) FROM `{table}`;")
    count = cur.fetchone()[0]

    cur.close()
    conn.close()
    return count