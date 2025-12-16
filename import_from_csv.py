# import_from_csv.py
# 將 data/ 底下的 CSV 匯入 SQLite (kpop.db)
# tables: companies, groups, members, nationalities, member_nationalities, releases, songs

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path("kpop.db")
DATA_DIR = Path("data")

CSV_FILES = {
    "companies": "companies.csv",
    "groups": "groups.csv",
    "members": "members.csv",
    "nationalities": "nationalities.csv",
    "member_nationalities": "member_nationalities.csv",
    "releases": "releases.csv",
    "songs": "songs.csv",
}


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def norm(v):
    """把 NaN/空白字串 轉成 None，避免塞進資料庫變成 ''"""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s != "" else None
    return v


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / CSV_FILES[name]
    if not path.exists():
        raise FileNotFoundError(f"找不到 {path}，請確認 data/ 目錄與檔名。")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    return df


def reset_db(conn: sqlite3.Connection) -> None:
    """清空資料表（保留結構）"""
    conn.execute("PRAGMA foreign_keys = OFF;")
    for t in [
        "songs",
        "releases",
        "member_nationalities",
        "nationalities",
        "members",
        "groups",
        "companies",
    ]:
        conn.execute(f"DELETE FROM {t};")
        conn.execute("DELETE FROM sqlite_sequence WHERE name=?;", (t,))
    conn.execute("PRAGMA foreign_keys = ON;")


# -------------------------
# 匯入各表
# -------------------------

def import_companies(conn: sqlite3.Connection) -> None:
    """
    companies.csv 欄位：
    company_name, founder, founded_date
    """
    df = load_csv("companies")
    required = {"company_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"companies.csv 缺少欄位：{missing}")

    sql = """
    INSERT OR IGNORE INTO companies (company_name, founder, founded_date)
    VALUES (?, ?, ?)
    """
    for _, r in df.iterrows():
        conn.execute(sql, (
            norm(r.get("company_name")),
            norm(r.get("founder")),
            norm(r.get("founded_date")),
        ))


def import_groups(conn: sqlite3.Connection) -> None:
    """
    groups.csv 欄位：
    group_name, company_name, debut_date, fandom_name, image_path(可選)

    company_name 會自動對應到 companies.company_id（可空）
    """
    df = load_csv("groups")
    required = {"group_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"groups.csv 缺少欄位：{missing}")

    # image_path 不是必填；沒有也 OK
    sql = """
    INSERT OR IGNORE INTO groups (company_id, group_name, debut_date, fandom_name, image_path)
    VALUES (
      (SELECT company_id FROM companies WHERE company_name = ?),
      ?, ?, ?, ?
    )
    """
    for _, r in df.iterrows():
        conn.execute(sql, (
            norm(r.get("company_name")),
            norm(r.get("group_name")),
            norm(r.get("debut_date")),
            norm(r.get("fandom_name")),
            norm(r.get("image_path")),
        ))



def import_members(conn: sqlite3.Connection) -> None:
    """
    members.csv 欄位（目前狀況）：
    group_name, stage_name, real_name, birth_date, image_path(可選)
    """
    df = load_csv("members")
    required = {"group_name", "stage_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"members.csv 缺少欄位：{missing}")

    # 檢查 group_name 是否存在
    group_names = set(pd.read_sql_query("SELECT group_name FROM groups", conn)["group_name"].tolist())
    bad = []
    for _, r in df.iterrows():
        gname = norm(r.get("group_name"))
        if gname not in group_names:
            bad.append(gname)
    if bad:
        raise ValueError(f"members.csv 有找不到的 group_name：{sorted(set(bad))}")

    sql = """
    INSERT OR IGNORE INTO members (group_id, stage_name, real_name, birth_date, image_path)
    VALUES (
      (SELECT group_id FROM groups WHERE group_name = ?),
      ?, ?, ?, ?
    )
    """
    for _, r in df.iterrows():
        conn.execute(sql, (
            norm(r.get("group_name")),
            norm(r.get("stage_name")),
            norm(r.get("real_name")),
            norm(r.get("birth_date")),
            norm(r.get("image_path")),
        ))



def import_nationalities(conn: sqlite3.Connection) -> None:
    """
    nationalities.csv 欄位：
    nationality_code, nationality_name
    """
    df = load_csv("nationalities")
    required = {"nationality_code"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"nationalities.csv 缺少欄位：{missing}")

    sql = """
    INSERT OR IGNORE INTO nationalities (nationality_code, nationality_name)
    VALUES (?, ?)
    """
    for _, r in df.iterrows():
        conn.execute(sql, (
            norm(r.get("nationality_code")),
            norm(r.get("nationality_name")),
        ))


def import_member_nationalities(conn: sqlite3.Connection) -> None:
    """
    member_nationalities.csv 欄位（建議用可定位 member 的欄位）：
    group_name, stage_name, nationality_code

    會用 (group_name, stage_name) 找到 member_id
    """
    df = load_csv("member_nationalities")
    required = {"group_name", "stage_name", "nationality_code"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"member_nationalities.csv 缺少欄位：{missing}")

    # 建 member lookup: (group_name, stage_name) -> member_id
    mem_df = pd.read_sql_query("""
        SELECT m.member_id, g.group_name, m.stage_name
        FROM members m
        JOIN groups g ON m.group_id = g.group_id
    """, conn)
    member_lookup = {
        (row["group_name"], row["stage_name"]): int(row["member_id"])
        for _, row in mem_df.iterrows()
    }

    # 建 nationality set
    nat_set = set(pd.read_sql_query("SELECT nationality_code FROM nationalities", conn)["nationality_code"].tolist())

    missing_member = []
    missing_nat = []
    for _, r in df.iterrows():
        key = (norm(r.get("group_name")), norm(r.get("stage_name")))
        nat = norm(r.get("nationality_code"))
        if key not in member_lookup:
            missing_member.append(key)
        if nat not in nat_set:
            missing_nat.append(nat)

    if missing_member:
        preview = sorted(set(missing_member))[:10]
        raise ValueError(f"member_nationalities.csv 有找不到的 member（group_name, stage_name）：前幾筆 {preview}")
    if missing_nat:
        preview = sorted(set(missing_nat))[:10]
        raise ValueError(f"member_nationalities.csv 有找不到的 nationality_code：前幾筆 {preview}")

    sql = """
    INSERT OR IGNORE INTO member_nationalities (member_id, nationality_code)
    VALUES (?, ?)
    """
    for _, r in df.iterrows():
        key = (norm(r.get("group_name")), norm(r.get("stage_name")))
        member_id = member_lookup[key]
        conn.execute(sql, (member_id, norm(r.get("nationality_code"))))


def import_releases(conn: sqlite3.Connection) -> None:
    """
    releases.csv 欄位：
    group_name, release_name, release_type, release_lang, release_date

    release_type：ALBUM / EP / SINGLE / SINGLE_ALBUM
    release_lang：KR / JP / EN
    """
    df = load_csv("releases")
    required = {"group_name", "release_name", "release_type", "release_lang"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"releases.csv 缺少欄位：{missing}")

    group_names = set(pd.read_sql_query("SELECT group_name FROM groups", conn)["group_name"].tolist())
    bad_group = []
    for _, r in df.iterrows():
        gname = norm(r.get("group_name"))
        if gname not in group_names:
            bad_group.append(gname)
    if bad_group:
        raise ValueError(f"releases.csv 有找不到的 group_name：{sorted(set(bad_group))}")

    valid_type = {"ALBUM", "EP", "SINGLE", "SINGLE_ALBUM"}
    valid_lang = {"KR", "JP", "EN"}

    bad_type, bad_lang = [], []
    for _, r in df.iterrows():
        t = norm(r.get("release_type"))
        l = norm(r.get("release_lang"))
        if t not in valid_type:
            bad_type.append(t)
        if l not in valid_lang:
            bad_lang.append(l)

    if bad_type:
        raise ValueError(f"releases.csv 有不合法 release_type：{sorted(set(bad_type))}（只能 {sorted(valid_type)}）")
    if bad_lang:
        raise ValueError(f"releases.csv 有不合法 release_lang：{sorted(set(bad_lang))}（只能 {sorted(valid_lang)}）")

    sql = """
    INSERT OR IGNORE INTO releases (group_id, release_name, release_type, release_lang, release_date)
    VALUES (
      (SELECT group_id FROM groups WHERE group_name = ?),
      ?, ?, ?, ?
    )
    """
    for _, r in df.iterrows():
        conn.execute(sql, (
            norm(r.get("group_name")),
            norm(r.get("release_name")),
            norm(r.get("release_type")),
            norm(r.get("release_lang")),
            norm(r.get("release_date")),
        ))


def import_songs(conn: sqlite3.Connection) -> None:
    """
    songs.csv 欄位（目前狀況）：
    group_name, release_name, release_type, release_lang, title, youtube_url

    songs 需要用 (group_name, release_name, release_type, release_lang) 找到 release_id
    """
    df = load_csv("songs")
    required = {"group_name", "release_name", "release_type", "release_lang", "title"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"songs.csv 缺少欄位：{missing}")

    valid_type = {"ALBUM", "EP", "SINGLE", "SINGLE_ALBUM"}
    valid_lang = {"KR", "JP", "EN"}

    for col, valid_set in [("release_type", valid_type), ("release_lang", valid_lang)]:
        bad = []
        for _, r in df.iterrows():
            v = norm(r.get(col))
            if v not in valid_set:
                bad.append(v)
        if bad:
            raise ValueError(f"songs.csv 有不合法 {col}：{sorted(set(bad))}（只能 {sorted(valid_set)}）")

    rel_df = pd.read_sql_query("""
        SELECT r.release_id, g.group_name, r.release_name, r.release_type, r.release_lang
        FROM releases r
        JOIN groups g ON r.group_id = g.group_id
    """, conn)

    lookup = {
        (row["group_name"], row["release_name"], row["release_type"], row["release_lang"]): int(row["release_id"])
        for _, row in rel_df.iterrows()
    }

    missing_rel = []
    for _, r in df.iterrows():
        key = (
            norm(r.get("group_name")),
            norm(r.get("release_name")),
            norm(r.get("release_type")),
            norm(r.get("release_lang")),
        )
        if key not in lookup:
            missing_rel.append(key)

    if missing_rel:
        preview = sorted(set(missing_rel))[:10]
        raise ValueError(
            "songs.csv 有找不到對應 releases 的資料（請先在 releases.csv 建立對應發行作品）。\n"
            f"前幾筆：{preview}"
        )

    sql = """
    INSERT OR IGNORE INTO songs (release_id, title, youtube_url)
    VALUES (?, ?, ?)
    """
    for _, r in df.iterrows():
        key = (
            norm(r.get("group_name")),
            norm(r.get("release_name")),
            norm(r.get("release_type")),
            norm(r.get("release_lang")),
        )
        release_id = lookup[key]
        conn.execute(sql, (
            release_id,
            norm(r.get("title")),
            norm(r.get("youtube_url")),
        ))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wipe", action="store_true", help="匯入前先清空資料表（保留結構）")
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise FileNotFoundError("找不到 kpop.db。請先執行：python init_db.py")

    conn = connect()
    try:
        if args.wipe:
            reset_db(conn)

        # 依外鍵順序匯入
        import_companies(conn)
        import_groups(conn)
        import_members(conn)
        import_nationalities(conn)
        import_member_nationalities(conn)
        import_releases(conn)
        import_songs(conn)

        conn.commit()

        summary = {}
        for t in ["companies", "groups", "members", "nationalities", "member_nationalities", "releases", "songs"]:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            summary[t] = n

        print("✅ 匯入完成！表格筆數：")
        for k, v in summary.items():
            print(f"  - {k}: {v}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
