# init_db.py
# K-POP 寶典（最終定稿 Schema）
# tables: companies, groups, members, nationalities, member_nationalities, releases, songs

import sqlite3
from pathlib import Path

DB_PATH = Path("kpop.db")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- 1) 公司
CREATE TABLE IF NOT EXISTS companies (
  company_id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name TEXT NOT NULL UNIQUE,
  founder TEXT,
  founded_date TEXT
);

-- 2) 團體
CREATE TABLE IF NOT EXISTS groups (
  group_id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id INTEGER,
  group_name TEXT NOT NULL UNIQUE,
  debut_date TEXT,
  fandom_name TEXT,
  image_path TEXT,
  FOREIGN KEY (company_id) REFERENCES companies(company_id)
    ON UPDATE CASCADE
    ON DELETE SET NULL
);

-- 3) 成員（簡化：一位成員只屬於一個團；不含中文名字）
CREATE TABLE IF NOT EXISTS members (
  member_id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id INTEGER NOT NULL,
  stage_name TEXT NOT NULL,
  real_name TEXT,
  birth_date TEXT,
  image_path TEXT,
  FOREIGN KEY (group_id) REFERENCES groups(group_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  UNIQUE (group_id, stage_name)
);

-- 4) 國籍字典表
CREATE TABLE IF NOT EXISTS nationalities (
  nationality_code TEXT PRIMARY KEY,   -- KR / JP / US ...
  nationality_name TEXT
);

-- 5) 成員-國籍 多對多關聯表（複合主鍵）
CREATE TABLE IF NOT EXISTS member_nationalities (
  member_id INTEGER NOT NULL,
  nationality_code TEXT NOT NULL,
  PRIMARY KEY (member_id, nationality_code),
  FOREIGN KEY (member_id) REFERENCES members(member_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  FOREIGN KEY (nationality_code) REFERENCES nationalities(nationality_code)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

-- 6) 發行作品（統一表示：ALBUM / EP / SINGLE / SINGLE_ALBUM）
CREATE TABLE IF NOT EXISTS releases (
  release_id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id INTEGER NOT NULL,
  release_name TEXT NOT NULL,
  release_type TEXT NOT NULL CHECK (release_type IN ('ALBUM','EP','SINGLE','SINGLE_ALBUM')),
  release_lang TEXT NOT NULL CHECK (release_lang IN ('KR','JP','EN')),
  release_date TEXT,
  FOREIGN KEY (group_id) REFERENCES groups(group_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  UNIQUE (group_id, release_name, release_type, release_lang)
);

-- 7) 歌曲（不綁 album；綁 release）
CREATE TABLE IF NOT EXISTS songs (
  song_id INTEGER PRIMARY KEY AUTOINCREMENT,
  release_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  youtube_url TEXT,
  FOREIGN KEY (release_id) REFERENCES releases(release_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

-- 常用索引（加速 Join / 查詢）
CREATE INDEX IF NOT EXISTS idx_groups_company_id ON groups(company_id);
CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(group_name);

CREATE INDEX IF NOT EXISTS idx_members_group_id ON members(group_id);
CREATE INDEX IF NOT EXISTS idx_members_stage_name ON members(stage_name);

CREATE INDEX IF NOT EXISTS idx_member_nationalities_member_id ON member_nationalities(member_id);
CREATE INDEX IF NOT EXISTS idx_member_nationalities_nat_code ON member_nationalities(nationality_code);

CREATE INDEX IF NOT EXISTS idx_releases_group_id ON releases(group_id);
CREATE INDEX IF NOT EXISTS idx_songs_release_id ON songs(release_id);
CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);
"""

def reset_db(conn: sqlite3.Connection) -> None:
    """
    清空資料表（保留結構），方便重匯入 CSV。
    注意刪除順序：子表 -> 父表
    """
    conn.execute("PRAGMA foreign_keys = OFF;")

    # 子表先刪：songs -> releases、member_nationalities -> members -> groups -> companies
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

def init_db(wipe: bool = False) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(SCHEMA_SQL)

        if wipe:
            reset_db(conn)

        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    # wipe=True：清空所有資料（重匯入 CSV 前用）
    init_db(wipe=False)
    print(f"✅ Database initialized: {DB_PATH.resolve()}")
