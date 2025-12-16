import re
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit.components.v1 as components
import streamlit as st

DB_PATH = Path("kpop.db")

# 你目前的 release_type
RELEASE_TYPES = ["ALBUM", "EP", "SINGLE", "SINGLE_ALBUM"]
RELEASE_LANGS = ["KR", "JP", "EN"]

# 資料夾
GROUP_IMG_DIR = Path("images/groups")
MEMBER_IMG_DIR = Path("images/members")

# ---------------------------
# DB Helpers
# ---------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def norm(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s != "" else None
    return v


def run_df(sql: str, params=()):
    conn = get_conn()
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()


def run_exec(sql: str, params=()):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def run_many(sql: str, seq_params):
    conn = get_conn()
    try:
        conn.executemany(sql, seq_params)
        conn.commit()
    finally:
        conn.close()


def clear_cache():
    st.cache_data.clear()


def ensure_db():
    if not DB_PATH.exists():
        st.error("找不到 kpop.db。請先執行：python init_db.py 以及 python import_from_csv.py --wipe")
        st.stop()


def safe_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\-一-龥]+", "_", name)  # 避免奇怪字元
    return name

# ---------------------------
# Cached Lookups
# ---------------------------
@st.cache_data(show_spinner=False)
def get_companies():
    df = run_df(
        """
        SELECT company_id, company_name
        FROM companies
        ORDER BY company_name COLLATE NOCASE;
        """
    )
    return df


@st.cache_data(show_spinner=False)
def get_groups():
    df = run_df(
        """
        SELECT g.group_id, g.group_name, c.company_name, g.debut_date, g.fandom_name, g.image_path
        FROM groups g
        LEFT JOIN companies c ON g.company_id=c.company_id
        ORDER BY g.group_name COLLATE NOCASE;
        """
    )
    return df


@st.cache_data(show_spinner=False)
def get_nationalities():
    df = run_df(
        """
        SELECT nationality_code, nationality_name
        FROM nationalities
        ORDER BY nationality_code;
        """
    )
    return df


@st.cache_data(show_spinner=False)
def get_releases_for_group(group_id: int):
    df = run_df(
        """
        SELECT release_id, release_name, release_type, release_lang, release_date
        FROM releases
        WHERE group_id = ?
        ORDER BY release_date, release_name COLLATE NOCASE;
        """,
        (group_id,),
    )
    return df


# ---------------------------
# YouTube helpers
# ---------------------------
_YT_RE = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})")

def extract_youtube_id(url: str | None):
    if not url:
        return None
    m = _YT_RE.search(url)
    return m.group(1) if m else None


def show_youtube(url: str, width: int = 560, height: int = 315):
    # 支援 youtu.be / watch?v= / embed
    vid = None
    if "youtu.be/" in url:
        vid = url.split("youtu.be/")[-1].split("?")[0]
    elif "watch?v=" in url:
        vid = url.split("watch?v=")[-1].split("&")[0]
    elif "/embed/" in url:
        vid = url.split("/embed/")[-1].split("?")[0]

    if not vid:
        st.link_button("開啟 YouTube", url)
        return

    embed_url = f"https://www.youtube.com/embed/{vid}"
    components.iframe(embed_url, width=width, height=height)


# ---------------------------
# Pages: Search
# ---------------------------
def page_search_groups():
    st.header("🔎 搜尋團體")

    companies = get_companies()
    groups = get_groups()

    # ------- 搜尋條件（用 form：按 Enter / 按按鈕 才會觸發） -------
    with st.form("group_search_form", clear_on_submit=False):
        c1, c2 = st.columns([1.3, 1])
        with c1:
            q_in = st.text_input("團體名稱 group name", placeholder="")
        with c2:
            company_opts = ["全部"] + companies["company_name"].tolist() + ["其他"]
            company_pick = st.selectbox("進階搜尋：公司 company", company_opts, index=0)

        submitted = st.form_submit_button("搜尋")

    # 只有送出後才把條件寫入 session_state
    if submitted:
        st.session_state["groups_q"] = q_in.strip()
        st.session_state["groups_company_pick"] = company_pick

        # ✅ 重要：每次按 Enter 重新搜尋，就清掉之前選過的團
        st.session_state.pop("selected_group_id", None)

    # 初次進入頁面：還沒搜尋就先停在這裡（不顯示結果/筆數/詳細資訊）
    if "groups_q" not in st.session_state and "groups_company_pick" not in st.session_state:
        st.info("請輸入關鍵字後按 Enter 進行搜尋。")
        return

    # 取得目前要用的搜尋條件（從 session_state 讀）
    q = st.session_state.get("groups_q", "").strip()
    company_pick = st.session_state.get("groups_company_pick", "全部")


    # ------- 篩選 -------
    df = groups.copy()

    if company_pick == "其他":
        df = df[df["company_name"].isna()]
    elif company_pick != "全部":
        df = df[df["company_name"] == company_pick]

    if q:
        df = df[df["group_name"].str.contains(q, case=False, na=False)]

    df = df.sort_values("group_name", key=lambda s: s.str.lower())

    st.caption(f"共找到 {len(df)} 個團體")
    if df.empty:
        st.info("沒有符合條件的團體。")
        return

    # ---------- UI helpers ----------
    def avatar_html(name: str):
        ch = (name[:1] if name else "?").upper()
        return f"""
        <div style="
            width:56px;height:56px;border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            background:#111827;color:white;font-weight:700;font-size:20px;
            margin-bottom:8px;">
            {ch}
        </div>
        """

    # ---------- 團體 ICON/圖片 卡片網格 ----------
    st.subheader("📌 團體列表（點擊查看資訊）")

    cols = st.columns(4, gap="small")
    for i, r in enumerate(df.itertuples()):
        with cols[i % 4]:

            if st.button(r.group_name, key=f"group_btn_{r.group_id}", use_container_width=True):
                st.session_state["selected_group_id"] = int(r.group_id)

            company_show = r.company_name if pd.notna(r.company_name) else "其他"
            debut_show = r.debut_date if pd.notna(r.debut_date) else ""
            st.caption(f"{company_show}" + (f" · {debut_show}" if debut_show else ""))

    st.divider()

    # 一開始不顯示詳細資訊：只有點了團體才顯示
    if "selected_group_id" not in st.session_state:
        st.info("請先點選上方任一團體，查看詳細資訊。")
        return

    gid = int(st.session_state["selected_group_id"])

    # ---------- 團體詳細資訊 + quick stats ----------
    gdetail = run_df(
        """
        SELECT g.group_id, g.group_name, c.company_name, g.debut_date, g.fandom_name, g.image_path
        FROM groups g
        LEFT JOIN companies c ON g.company_id=c.company_id
        WHERE g.group_id=?;
        """,
        (gid,),
    ).iloc[0]

    st.subheader("ℹ️ 團體詳細資訊")
    left, right = st.columns([1.3, 1])

    with left:
        img = norm(gdetail.get("image_path"))
        if img:
            st.image(img, width=220)
        st.markdown(f"### {gdetail['group_name']}")
        st.write("**公司：**", gdetail["company_name"] if pd.notna(gdetail["company_name"]) else "其他")
        st.write("**出道日：**", gdetail["debut_date"] if pd.notna(gdetail["debut_date"]) else "（未填）")
        st.write("**粉絲名：**", gdetail["fandom_name"] if pd.notna(gdetail["fandom_name"]) else "（未填）")

    with right:
        mem_cnt = run_df("SELECT COUNT(*) AS n FROM members WHERE group_id=?;", (gid,))["n"].iloc[0]
        rel_cnt = run_df("SELECT COUNT(*) AS n FROM releases WHERE group_id=?;", (gid,))["n"].iloc[0]
        song_cnt = run_df(
            """
            SELECT COUNT(*) AS n
            FROM songs s
            JOIN releases r ON s.release_id=r.release_id
            WHERE r.group_id=?;
            """,
            (gid,),
        )["n"].iloc[0]

        st.metric("成員數", int(mem_cnt))
        st.metric("發行作品數", int(rel_cnt))
        st.metric("歌曲數", int(song_cnt))

    st.divider()

    # ------- 成員列表（卡片網格：含 image_path） -------
    st.subheader("👥 成員列表")

    mem = run_df(
        """
        SELECT m.member_id, m.stage_name, m.real_name, m.birth_date, m.image_path,
               GROUP_CONCAT(mn.nationality_code, ',') AS nationalities
        FROM members m
        LEFT JOIN member_nationalities mn ON mn.member_id=m.member_id
        WHERE m.group_id=?
        GROUP BY m.member_id
        ORDER BY m.stage_name COLLATE NOCASE;
        """,
        (gid,),
    )

    if mem.empty:
        st.info("此團尚無成員資料。")
    else:
        mcols = st.columns(5, gap="small")
        for i, row in enumerate(mem.itertuples()):
            with mcols[i % 5]:
                mimg = norm(getattr(row, "image_path", None))
                if mimg:
                    st.image(mimg, width=120)
                else:
                    st.markdown(avatar_html(row.stage_name), unsafe_allow_html=True)

                st.write(f"**{row.stage_name}**")
                if row.real_name and str(row.real_name).strip():
                    st.caption(row.real_name)
                if row.birth_date and str(row.birth_date).strip():
                    st.caption(f"🎂 {row.birth_date}")
                if row.nationalities and str(row.nationalities).strip():
                    st.caption(f"🌍 {row.nationalities}")

    st.divider()

    # ------- 發行作品總覽（原本保留） -------
    st.subheader("📦 發行作品（releases）")

    rel = run_df(
        """
        SELECT release_name, release_type, release_lang, release_date
        FROM releases
        WHERE group_id=?
        ORDER BY release_date DESC, release_name COLLATE NOCASE;
        """,
        (gid,),
    )

    if rel.empty:
        st.info("此團尚無發行作品。")
    else:
        # 每列一個卡片
        for row in rel.itertuples(index=False):
            name, rtype, rlang, rdate = row

            left, right = st.columns([3, 1])
            with left:
                st.markdown(f"### {name}")
                meta = []
                if rdate:
                    meta.append(f"📅 {rdate}")
                meta.append(f"🏷️ {rtype}")
                meta.append(f"🗣️ {rlang}")
                st.caption(" · ".join(meta))

            with right:
                # 小 badge 느낌
                st.markdown(
                    f"""
                    <div style="
                        display:flex;
                        justify-content:flex-end;
                        gap:8px;
                        margin-top:10px;
                    ">
                    <span style="padding:6px 10px; border-radius:999px; background:#1f2937;">{rtype}</span>
                    <span style="padding:6px 10px; border-radius:999px; background:#111827;">{rlang}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.divider()


def page_search_members():
    st.header("🔎 搜尋成員")

    ensure_db()

    # 進階選單資料
    groups = get_groups()                 # 你已有：group_id, group_name...
    nat = get_nationalities()             # 你已有：nationality_code...

    group_opts = ["全部"] + (groups["group_name"].tolist() if not groups.empty else [])
    nat_opts = ["全部"] + (nat["nationality_code"].tolist() if not nat.empty else [])

    # ---- 1) 搜尋表單：按 Enter 送出（不顯示按鈕）----
    with st.form("member_search_form", clear_on_submit=False):
        c1, c2, c3 = st.columns([1.4, 1, 1])
        with c1:
            q_in = st.text_input("成員藝名 stage name", placeholder="")
        with c2:
            group_pick_in = st.selectbox("進階搜尋：團體 group", group_opts, index=0)
        with c3:
            nat_pick_in = st.selectbox("進階搜尋：國籍 nationality", nat_opts, index=0)

        submitted = st.form_submit_button("搜尋")

    if submitted:
        st.session_state["members_q"] = q_in.strip()
        st.session_state["members_group_pick"] = group_pick_in
        st.session_state["members_nat_pick"] = nat_pick_in
        st.session_state.pop("selected_member_id", None)  # 重新搜尋就清掉舊選取

    # 初次進入：不顯示任何結果
    if "members_q" not in st.session_state and "members_group_pick" not in st.session_state and "members_nat_pick" not in st.session_state:
        st.info("請輸入藝名後按 Enter 進行搜尋。")
        return

    q = st.session_state.get("members_q", "").strip()
    group_pick = st.session_state.get("members_group_pick", "全部")
    nat_pick = st.session_state.get("members_nat_pick", "全部")

    # ---- 2) 查詢：stage_name + 進階篩選（團體 / 國籍）----
    sql = """
    SELECT
      m.member_id,
      m.stage_name,
      g.group_name
    FROM members m
    JOIN groups g ON m.group_id = g.group_id
    WHERE 1=1
    """
    params = []

    if q:
        sql += " AND m.stage_name LIKE ? "
        params.append(f"%{q}%")

    if group_pick != "全部":
        sql += " AND g.group_name = ? "
        params.append(group_pick)

    if nat_pick != "全部":
        sql += """
        AND EXISTS (
          SELECT 1 FROM member_nationalities mn2
          WHERE mn2.member_id = m.member_id AND mn2.nationality_code = ?
        )
        """
        params.append(nat_pick)

    sql += " ORDER BY g.group_name COLLATE NOCASE, m.stage_name COLLATE NOCASE; "

    df = run_df(sql, tuple(params))

    st.caption(f"共找到 {len(df)} 位成員")
    if df.empty:
        st.info("沒有符合條件的成員。")
        return

    # ---- 3) 結果：只顯示名字（按鈕）----
    st.subheader("📌 成員列表（點名字查看）")

    cols = st.columns(4, gap="small")
    for i, r in enumerate(df.itertuples()):
        with cols[i % 4]:
            if st.button(r.stage_name, key=f"member_btn_{r.member_id}", use_container_width=True):
                st.session_state["selected_member_id"] = int(r.member_id)

    st.divider()

    # ---- 4) 未點選前，不顯示詳細資訊 ----
    if "selected_member_id" not in st.session_state:
        st.info("請先點選上方任一成員，查看詳細資訊。")
        return

    mid = int(st.session_state["selected_member_id"])

    # ---- 5) 詳細資訊（圖片左 / 資訊右）----
    detail = run_df(
        """
        SELECT
          m.member_id,
          m.stage_name,
          m.real_name,
          m.birth_date,
          m.image_path,
          g.group_name,
          c.company_name,
          GROUP_CONCAT(mn.nationality_code, ',') AS nationalities
        FROM members m
        JOIN groups g ON m.group_id = g.group_id
        LEFT JOIN companies c ON g.company_id = c.company_id
        LEFT JOIN member_nationalities mn ON mn.member_id = m.member_id
        WHERE m.member_id = ?
        GROUP BY m.member_id;
        """,
        (mid,),
    ).iloc[0]

    st.subheader("ℹ️ 成員資訊")

    left, right = st.columns([1, 2.2], gap="large")

    with left:
        img = norm(detail.get("image_path"))
        if img:
            try:
                st.image(img, width=260)
            except Exception:
                st.caption(f"⚠️ 圖片讀取失敗：{img}")
        else:
            st.caption("（此成員尚未提供圖片）")

    with right:
        st.markdown(f"### {detail['stage_name']}")
        if pd.notna(detail["real_name"]):
            st.write("**本名：**", detail["real_name"])
        st.write("**所屬團體：**", detail["group_name"])
        st.write("**所屬公司：**", detail["company_name"] if pd.notna(detail["company_name"]) else "其他")
        st.write("**生日：**", detail["birth_date"] if pd.notna(detail["birth_date"]) else "（未填）")
        st.write("**國籍：**", detail["nationalities"] if pd.notna(detail["nationalities"]) else "（未填）")


def page_search_songs():
    st.header("🔎 搜尋歌名")

    ensure_db()
    groups = get_groups()

    # ---- 1) 搜尋表單：按 Enter 送出（不顯示按鈕）----
    with st.form("song_search_form", clear_on_submit=False):
        col1, col2, col3 = st.columns([1.4, 1, 1])
        with col1:
            q_in = st.text_input("歌曲名稱 song title", placeholder="")
        with col2:
            group_opts = ["全部"] + groups["group_name"].tolist()
            group_pick_in = st.selectbox("進階搜尋：團體 group", group_opts, index=0)
        with col3:
            lang_opts = ["全部"] + RELEASE_LANGS 
            lang_pick_in = st.selectbox("進階搜尋：語言 language", lang_opts, index=0)

        submitted = st.form_submit_button("搜尋")

    if submitted:
        st.session_state["songs_q"] = q_in.strip()
        st.session_state["songs_group_pick"] = group_pick_in
        st.session_state["songs_lang_pick"] = lang_pick_in
        st.session_state.pop("selected_song_id", None)  # 重新搜尋就清掉舊選取

    # 初次進入：不顯示任何結果
    if "songs_q" not in st.session_state:
        st.info("請輸入歌名關鍵字後按 Enter 進行搜尋（可搭配進階篩選）。")
        return

    q = st.session_state.get("songs_q", "").strip()
    group_pick = st.session_state.get("songs_group_pick", "全部")
    lang_pick = st.session_state.get("songs_lang_pick", "全部")

    sql = """
    SELECT
      s.song_id,
      g.group_name,
      r.release_name,
      r.release_type,
      r.release_lang,
      r.release_date,
      s.title,
      s.youtube_url
    FROM songs s
    JOIN releases r ON s.release_id = r.release_id
    JOIN groups g ON r.group_id = g.group_id
    WHERE 1=1
    """
    params = []

    if q:
        sql += " AND s.title LIKE ? "
        params.append(f"%{q}%")

    # 保留進階：團體
    if group_pick != "全部":
        sql += " AND g.group_name = ? "
        params.append(group_pick)

    # 保留進階：語言
    if lang_pick != "全部":
        sql += " AND r.release_lang = ? "
        params.append(lang_pick)

    sql += " ORDER BY g.group_name COLLATE NOCASE, r.release_date, s.title COLLATE NOCASE; "

    df = run_df(sql, tuple(params))
    st.write(f"共找到 **{len(df)}** 首歌")
    if df.empty:
        st.info("沒有符合條件的歌曲。")
        return

    # ---- 2) 選一首歌顯示細節 + 內嵌YT ----
    labels = []
    id_by_label = {}
    for row in df.itertuples():
        label = f"{row.group_name} — {row.title}"
        labels.append(label)
        id_by_label[label] = int(row.song_id)

    # 若你想記住上次選的歌，可以用 session_state
    default_label = labels[0]
    pick = st.selectbox("選擇歌曲", labels, index=labels.index(default_label))
    sid = id_by_label[pick]

    one = df[df["song_id"] == sid].iloc[0]

    # ---- 3) 左：影片 / 右：歌曲資訊 ----
    left, right = st.columns([1.3, 1])  # 左邊大一點給影片

    with left:
        st.subheader("▶️ YouTube")
        if pd.notna(one["youtube_url"]):
            show_youtube(one["youtube_url"], width=760, height=428)  # 16:9
        else:
            st.caption("（此歌曲沒有 YouTube 連結）")

    with right:
        st.subheader("🎵 歌曲資訊")
        st.write(" ")
        st.write("**團體：**", one["group_name"])
        st.write("**歌名：**", one["title"])
        st.write("**發行作品：**", one["release_name"])
        st.write("**類型/語言：**", f'{one["release_type"]} / {one["release_lang"]}')
        if pd.notna(one["release_date"]):
            st.write("**發行日：**", one["release_date"])



# ---------------------------
# Pages: Add
# ---------------------------
def page_add_group():
    st.header("➕ 新增團體")

    ensure_db()

    companies = get_companies()
    company_opts = ["（不綁定）"] + companies["company_name"].tolist()

    with st.form("add_group", clear_on_submit=True):
        group_name = st.text_input("團體名稱 group name（必填，且不可和已經有的團名一樣）").strip()
        company_pick = st.selectbox("公司 company", company_opts, index=0)

        debut_date = st.text_input("出道日 debut date（YYYY-MM-DD，可空）").strip()
        fandom_name = st.text_input("粉絲名 fandom name（可空）").strip()
        img = st.file_uploader("團體 LOGO（可選，請上傳 jpg/png 檔）", type=["jpg", "jpeg", "png"])

        submit = st.form_submit_button("新增")

    # ✅ 沒按新增就不要往下跑（關鍵）
    if not submit:
        return

    # ✅ 按了新增才開始檢查/寫入
    if not group_name:
        st.error("group_name 不能空白")
        return

    # ---- company_name 決定 ----
    if company_pick == "（不綁定）":
        company_name = None
    else:
        company_name = company_pick

    # ---- 存圖片到資料夾，拿到 image_path ----
    image_path = None
    if img is not None:
        GROUP_IMG_DIR.mkdir(parents=True, exist_ok=True)

        ext = Path(img.name).suffix.lower()
        base = safe_filename(group_name)
        save_path = GROUP_IMG_DIR / f"{base}{ext}"

        i = 1
        while save_path.exists():
            save_path = GROUP_IMG_DIR / f"{base}_{i}{ext}"
            i += 1

        save_path.write_bytes(img.getvalue())
        image_path = save_path.as_posix()

    try:
        # 不用再 INSERT companies，因為你只能選既有公司
        run_exec(
            """
            INSERT INTO groups (company_id, group_name, debut_date, fandom_name, image_path)
            VALUES (
              (SELECT company_id FROM companies WHERE company_name = ?),
              ?, ?, ?, ?
            );
            """,
            (company_name, group_name, norm(debut_date), norm(fandom_name), norm(image_path)),
        )

        clear_cache()
        st.success("✅ 新增團體成功")
    except sqlite3.IntegrityError as e:
        st.error(f"新增失敗（可能團名重複）：{e}")


def page_add_member():
    st.header("➕ 新增成員（選擇團體）")

    groups = get_groups()
    nat = get_nationalities()

    if groups.empty:
        st.warning("目前沒有任何團體，請先新增團體。")
        return

    group_opts = groups["group_name"].tolist()
    nat_opts = nat["nationality_code"].tolist()

    with st.form("add_member", clear_on_submit=True):
        group_pick = st.selectbox("選擇團體 group", group_opts)
        stage_name = st.text_input("藝名 stage name（必填）").strip()
        real_name = st.text_input("本名 real name（可空）").strip()
        birth_date = st.text_input("生日 birth date（YYYY-MM-DD，可空）").strip()
        nat_pick = st.multiselect("國籍 nationality（可多選，可空）", nat_opts)

        img = st.file_uploader("成員照片 photo（可選，jpg/png）", type=["jpg", "jpeg", "png"])

        submit = st.form_submit_button("新增")

    if not submit:
        return

    if not stage_name:
        st.error("stage_name 不能空白")
        return

    gid = int(groups.loc[groups["group_name"] == group_pick, "group_id"].iloc[0])

    # ---- 存照片到資料夾，拿到 image_path ----
    image_path = None
    if img is not None:
        MEMBER_IMG_DIR.mkdir(parents=True, exist_ok=True)

        ext = Path(img.name).suffix.lower()
        base = safe_filename(f"{group_pick}_{stage_name}")  # 避免不同團同名
        save_path = MEMBER_IMG_DIR / f"{base}{ext}"

        i = 1
        while save_path.exists():
            save_path = MEMBER_IMG_DIR / f"{base}_{i}{ext}"
            i += 1

        save_path.write_bytes(img.getvalue())
        image_path = save_path.as_posix()  # 存相對路徑

    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO members (group_id, stage_name, real_name, birth_date, image_path)
            VALUES (?, ?, ?, ?, ?);
            """,
            (gid, stage_name, norm(real_name), norm(birth_date), norm(image_path)),
        )
        member_id = cur.lastrowid

        # 多國籍寫入關聯表
        if nat_pick:
            conn.executemany(
                """
                INSERT OR IGNORE INTO member_nationalities (member_id, nationality_code)
                VALUES (?, ?);
                """,
                [(member_id, code) for code in nat_pick],
            )

        conn.commit()
        clear_cache()
        st.success("✅ 新增成員成功")
    except sqlite3.IntegrityError as e:
        conn.rollback()
        st.error(f"新增失敗（可能同團藝名重複或外鍵問題）：{e}")
    finally:
        conn.close()


def page_add_release():
    st.header("➕ 新增發行作品（選擇團體）")

    ensure_db()
    groups = get_groups()
    if groups.empty:
        st.info("目前沒有團體資料。")
        return

    gpick = st.selectbox("所屬團體 group", groups["group_name"].tolist())
    gid = int(groups.loc[groups["group_name"] == gpick, "group_id"].iloc[0])

    with st.form("add_release_only", clear_on_submit=True):
        new_name = st.text_input("發行作品名稱 release name（必填）").strip()
        new_type = st.selectbox("發行作品類型 release type", RELEASE_TYPES)
        new_lang = st.selectbox("發行作品語言 release language", RELEASE_LANGS)
        new_date = st.text_input("發行日期 release date（可空）").strip()
        submit = st.form_submit_button("新增")

    if not submit:
        return

    if not new_name:
        st.error("release_name 不能空白")
        return

    try:
        run_exec(
            """
            INSERT INTO releases (group_id, release_name, release_type, release_lang, release_date)
            VALUES (?, ?, ?, ?, ?);
            """,
            (gid, new_name, new_type, new_lang, norm(new_date)),
        )
        clear_cache()
        st.success("✅ 新增 release 成功")
    except sqlite3.IntegrityError as e:
        st.error(f"新增失敗（可能 UNIQUE 或 CHECK 不符合）：{e}")


def page_add_song():
    st.header("➕ 新增歌曲（選擇團體 → 選擇發行作品）")

    groups = get_groups()
    if groups.empty:
        st.warning("目前沒有任何團體，請先新增團體。")
        return

    group_pick = st.selectbox("選擇團體 group", groups["group_name"].tolist())
    gid = int(groups.loc[groups["group_name"] == group_pick, "group_id"].iloc[0])

    rel = get_releases_for_group(gid)
    if rel.empty:
        st.warning("此團尚無發行作品（releases）。請先新增發行作品 release。")
        return

    rel_labels = []
    rel_id_by_label = {}
    for row in rel.itertuples():
        label = f"{row.release_name} ({row.release_type}-{row.release_lang})"
        rel_labels.append(label)
        rel_id_by_label[label] = int(row.release_id)

    rel_pick = st.selectbox("選擇發行作品 releases", rel_labels)
    release_id = rel_id_by_label[rel_pick]

    with st.form("add_song", clear_on_submit=True):
        title = st.text_input("歌曲名稱 song title（必填）").strip()
        youtube_url = st.text_input("YouTube Link（可空）").strip()
        submit = st.form_submit_button("新增")

    if not submit:
        return

    if not title:
        st.error("title 不能空白")
        return

    try:
        run_exec(
            """
            INSERT INTO songs (release_id, title, youtube_url)
            VALUES (?, ?, ?);
            """,
            (release_id, title, norm(youtube_url)),
        )
        clear_cache()
        st.success("✅ 新增歌曲成功")
    except sqlite3.IntegrityError as e:
        st.error(f"新增失敗：{e}")


# ---------------------------
# Page: Modify (Update)
# ---------------------------
def page_modify():
    st.header("🛠️ 修改資料")

    mode = st.selectbox(
        "選擇要修改的資料類型",
        ["公司 companies", "團體 groups", "成員 members", "發行作品 releases", "歌曲 songs"],
    )

    if mode.startswith("公司"):
        companies = get_companies()
        if companies.empty:
            st.info("目前沒有公司資料。")
            return

        pick = st.selectbox("選擇要修改的公司 company", companies["company_name"].tolist())
        row = run_df(
            "SELECT company_id, company_name, founder, founded_date FROM companies WHERE company_name=?;",
            (pick,),
        ).iloc[0]

        with st.form("edit_company"):
            company_name = st.text_input("公司名稱 company name", value=row["company_name"]).strip()
            founder = st.text_input("創辦人 founder", value=row["founder"] if pd.notna(row["founder"]) else "").strip()
            founded_date = st.text_input("創辦日期 founded date", value=row["founded_date"] if pd.notna(row["founded_date"]) else "").strip()
            submit = st.form_submit_button("更新")

        if submit:
            try:
                run_exec(
                    """
                    UPDATE companies
                    SET company_name=?, founder=?, founded_date=?
                    WHERE company_id=?;
                    """,
                    (company_name, norm(founder), norm(founded_date), int(row["company_id"])),
                )
                clear_cache()
                st.success("✅ 更新成功")
            except sqlite3.IntegrityError as e:
                st.error(f"更新失敗：{e}")

    elif mode.startswith("團體 group"):
        groups = get_groups()
        companies = get_companies()
        if groups.empty:
            st.info("目前沒有團體資料。")
            return

        pick = st.selectbox("選擇要修改的團體 group", groups["group_name"].tolist())
        row = run_df(
            """
            SELECT g.group_id, g.group_name, g.debut_date, g.fandom_name, c.company_name
            FROM groups g
            LEFT JOIN companies c ON g.company_id=c.company_id
            WHERE g.group_name=?;
            """,
            (pick,),
        ).iloc[0]

        company_opts = ["（不綁定）"] + companies["company_name"].tolist()
        default_company = row["company_name"] if pd.notna(row["company_name"]) else "（不綁定）"
        default_idx = company_opts.index(default_company) if default_company in company_opts else 0

        with st.form("edit_group"):
            group_name = st.text_input("團體名字 group name", value=row["group_name"]).strip()
            company_pick = st.selectbox("公司 company", company_opts, index=default_idx)
            debut_date = st.text_input("出道日 debut date", value=row["debut_date"] if pd.notna(row["debut_date"]) else "").strip()
            fandom_name = st.text_input("粉絲名 fandom name", value=row["fandom_name"] if pd.notna(row["fandom_name"]) else "").strip()
            submit = st.form_submit_button("更新")

        if submit:
            company_name = None if company_pick == "（不綁定）" else company_pick
            try:
                run_exec(
                    """
                    UPDATE groups
                    SET company_id=(SELECT company_id FROM companies WHERE company_name=?),
                        group_name=?, debut_date=?, fandom_name=?
                    WHERE group_id=?;
                    """,
                    (company_name, group_name, norm(debut_date), norm(fandom_name), int(row["group_id"])),
                )
                clear_cache()
                st.success("✅ 更新成功")
            except sqlite3.IntegrityError as e:
                st.error(f"更新失敗：{e}")

    elif mode.startswith("成員"):
        groups = get_groups()
        nat = get_nationalities()

        if groups.empty:
            st.info("目前沒有團體資料。")
            return

        gpick = st.selectbox("選擇團體 group", groups["group_name"].tolist())
        gid = int(groups.loc[groups["group_name"] == gpick, "group_id"].iloc[0])

        mem = run_df(
            """
            SELECT member_id, stage_name, real_name, birth_date
            FROM members
            WHERE group_id=?
            ORDER BY stage_name COLLATE NOCASE;
            """,
            (gid,),
        )
        if mem.empty:
            st.info("此團沒有成員。")
            return

        mem_labels = mem["stage_name"].tolist()
        mpick = st.selectbox("選擇要修改的成員 member", mem_labels)
        mrow = mem[mem["stage_name"] == mpick].iloc[0]
        member_id = int(mrow["member_id"])

        current_nat = run_df(
            "SELECT nationality_code FROM member_nationalities WHERE member_id=? ORDER BY nationality_code;",
            (member_id,),
        )["nationality_code"].tolist()

        nat_opts = nat["nationality_code"].tolist()

        with st.form("edit_member"):
            stage_name = st.text_input("藝名 stage name", value=mrow["stage_name"]).strip()
            real_name = st.text_input("本名 real name", value=mrow["real_name"] if pd.notna(mrow["real_name"]) else "").strip()
            birth_date = st.text_input("生日 birth date", value=mrow["birth_date"] if pd.notna(mrow["birth_date"]) else "").strip()
            nat_pick = st.multiselect("國籍 nationality（多選）", nat_opts, default=current_nat)
            submit = st.form_submit_button("更新")

        if submit:
            conn = get_conn()
            try:
                conn.execute(
                    """
                    UPDATE members
                    SET stage_name=?, real_name=?, birth_date=?
                    WHERE member_id=?;
                    """,
                    (stage_name, norm(real_name), norm(birth_date), member_id),
                )

                # 國籍：先清掉再重插（簡單可靠）
                conn.execute("DELETE FROM member_nationalities WHERE member_id=?;", (member_id,))
                if nat_pick:
                    conn.executemany(
                        "INSERT OR IGNORE INTO member_nationalities (member_id, nationality_code) VALUES (?, ?);",
                        [(member_id, code) for code in nat_pick],
                    )

                conn.commit()
                clear_cache()
                st.success("✅ 更新成功")
            except sqlite3.IntegrityError as e:
                conn.rollback()
                st.error(f"更新失敗：{e}")
            finally:
                conn.close()

    elif mode.startswith("發行作品"):
        groups = get_groups()
        if groups.empty:
            st.info("目前沒有團體資料。")
            return

        gpick = st.selectbox("選擇團體 group", groups["group_name"].tolist())
        gid = int(groups.loc[groups["group_name"] == gpick, "group_id"].iloc[0])

        rel = get_releases_for_group(gid)
        if rel.empty:
            st.info("此團沒有 releases。你可以在這頁下方用『新增 release』新增。")
        else:
            rel_labels = []
            rid_by_label = {}
            for row in rel.itertuples():
                label = f"{row.release_name} ({row.release_type}-{row.release_lang})"
                rel_labels.append(label)
                rid_by_label[label] = int(row.release_id)

            rpick = st.selectbox("選擇要修改的發行作品 release", rel_labels)
            rid = rid_by_label[rpick]
            rrow = rel[rel["release_id"] == rid].iloc[0]

            with st.form("edit_release"):
                release_name = st.text_input("發行作品名稱 release name", value=rrow["release_name"]).strip()
                release_type = st.selectbox("發行作品類型 release type", RELEASE_TYPES, index=max(0, RELEASE_TYPES.index(rrow["release_type"])) if rrow["release_type"] in RELEASE_TYPES else 0)
                release_lang = st.selectbox("發行作品語言 release language", RELEASE_LANGS, index=max(0, RELEASE_LANGS.index(rrow["release_lang"])) if rrow["release_lang"] in RELEASE_LANGS else 0)
                release_date = st.text_input("發行日期 release date", value=rrow["release_date"] if pd.notna(rrow["release_date"]) else "").strip()
                submit = st.form_submit_button("更新")

            if submit:
                try:
                    run_exec(
                        """
                        UPDATE releases
                        SET release_name=?, release_type=?, release_lang=?, release_date=?
                        WHERE release_id=?;
                        """,
                        (release_name, release_type, release_lang, norm(release_date), rid),
                    )
                    clear_cache()
                    st.success("✅ 更新成功")
                except sqlite3.IntegrityError as e:
                    st.error(f"更新失敗（可能 UNIQUE 或 CHECK 不符合）：{e}")

    else:  # songs
        groups = get_groups()
        if groups.empty:
            st.info("目前沒有團體資料。")
            return

        gpick = st.selectbox("選擇團體 group", groups["group_name"].tolist())
        gid = int(groups.loc[groups["group_name"] == gpick, "group_id"].iloc[0])

        rel = get_releases_for_group(gid)
        if rel.empty:
            st.info("此團沒有 releases，無法管理 songs。")
            return

        rel_labels = []
        rid_by_label = {}
        for row in rel.itertuples():
            label = f"{row.release_name} ({row.release_type}-{row.release_lang})"
            rel_labels.append(label)
            rid_by_label[label] = int(row.release_id)

        rpick = st.selectbox("選擇發行作品 release", rel_labels)
        rid = rid_by_label[rpick]

        songs = run_df(
            """
            SELECT song_id, title, youtube_url
            FROM songs
            WHERE release_id=?
            ORDER BY title COLLATE NOCASE;
            """,
            (rid,),
        )

        if songs.empty:
            st.info("此 release 目前沒有歌曲。")
            return

        spick = st.selectbox("選擇要修改的歌曲 song", songs["title"].tolist())
        srow = songs[songs["title"] == spick].iloc[0]
        sid = int(srow["song_id"])

        with st.form("edit_song"):
            title = st.text_input("歌曲名稱 song title", value=srow["title"]).strip()
            youtube_url = st.text_input("Youtube Link（可空）", value=srow["youtube_url"] if pd.notna(srow["youtube_url"]) else "").strip()
            submit = st.form_submit_button("更新")

        if submit:
            try:
                run_exec(
                    """
                    UPDATE songs
                    SET title=?, youtube_url=?
                    WHERE song_id=?;
                    """,
                    (title, norm(youtube_url), sid),
                )
                clear_cache()
                st.success("✅ 更新成功")
            except sqlite3.IntegrityError as e:
                st.error(f"更新失敗：{e}")

        if pd.notna(srow["youtube_url"]):
            st.divider()
            st.subheader("▶️ 目前影片預覽")
            show_youtube(srow["youtube_url"])


# ---------------------------
# Pages: Delete
# ---------------------------
def page_delete():
    st.header("🗑️ 刪除資料")

    ensure_db()

    mode = st.selectbox(
        "選擇要刪除的資料類型",
        ["團體 groups", "成員 members", "發行作品 releases", "歌曲 songs"],
    )

    # -------------------------
    # 刪除：成員
    # -------------------------
    if mode.startswith("成員"):
        groups = get_groups()
        if groups.empty:
            st.info("目前沒有團體。")
            return

        gpick = st.selectbox("選擇團體 group", groups["group_name"].tolist())
        gid = int(groups.loc[groups["group_name"] == gpick, "group_id"].iloc[0])

        mem = run_df(
            """
            SELECT member_id, stage_name
            FROM members
            WHERE group_id=?
            ORDER BY stage_name COLLATE NOCASE;
            """,
            (gid,),
        )
        if mem.empty:
            st.info("此團沒有成員。")
            return

        mpick = st.selectbox("選擇要刪除的成員 member", mem["stage_name"].tolist())
        mid = int(mem.loc[mem["stage_name"] == mpick, "member_id"].iloc[0])

        st.warning("⚠️ 刪除後無法復原。")
        if st.button("確認刪除成員", type="primary"):
            conn = get_conn()
            try:
                # 先刪關聯表，避免外鍵限制
                conn.execute("DELETE FROM member_nationalities WHERE member_id=?;", (mid,))
                conn.execute("DELETE FROM members WHERE member_id=?;", (mid,))
                conn.commit()
                clear_cache()
                st.success("✅ 已刪除成員")
            except sqlite3.IntegrityError as e:
                conn.rollback()
                st.error(f"刪除失敗：{e}")
            finally:
                conn.close()

    # -------------------------
    # 刪除：歌曲
    # -------------------------
    elif mode.startswith("歌曲"):
        groups = get_groups()
        if groups.empty:
            st.info("目前沒有團體。")
            return

        gpick = st.selectbox("選擇團體 group", groups["group_name"].tolist())
        gid = int(groups.loc[groups["group_name"] == gpick, "group_id"].iloc[0])

        rel = get_releases_for_group(gid)
        if rel.empty:
            st.info("此團沒有 releases。")
            return

        rel_labels, rid_by_label = [], {}
        for row in rel.itertuples():
            label = f"{row.release_name} ({row.release_type}-{row.release_lang})"
            rel_labels.append(label)
            rid_by_label[label] = int(row.release_id)

        rpick = st.selectbox("選擇發行作品 release", rel_labels)
        rid = rid_by_label[rpick]

        songs = run_df(
            """
            SELECT song_id, title, youtube_url
            FROM songs
            WHERE release_id=?
            ORDER BY title COLLATE NOCASE;
            """,
            (rid,),
        )
        if songs.empty:
            st.info("此 release 沒有歌曲。")
            return

        spick = st.selectbox("選擇要刪除的歌曲 song", songs["title"].tolist())
        sid = int(songs.loc[songs["title"] == spick, "song_id"].iloc[0])

        st.warning("⚠️ 刪除後無法復原。")
        if st.button("確認刪除歌曲", type="primary"):
            try:
                run_exec("DELETE FROM songs WHERE song_id=?;", (sid,))
                clear_cache()
                st.success("✅ 已刪除歌曲")
            except sqlite3.IntegrityError as e:
                st.error(f"刪除失敗：{e}")

    # -------------------------
    # 刪除：發行作品（會連帶 songs）
    # -------------------------
    elif mode.startswith("發行作品"):
        groups = get_groups()
        if groups.empty:
            st.info("目前沒有團體。")
            return

        gpick = st.selectbox("選擇團體 group", groups["group_name"].tolist())
        gid = int(groups.loc[groups["group_name"] == gpick, "group_id"].iloc[0])

        rel = get_releases_for_group(gid)
        if rel.empty:
            st.info("此團沒有 releases。")
            return

        rel_labels, rid_by_label = [], {}
        for row in rel.itertuples():
            label = f"{row.release_name} ({row.release_type}-{row.release_lang})"
            rel_labels.append(label)
            rid_by_label[label] = int(row.release_id)

        rpick = st.selectbox("選擇要刪除的發行作品 release", rel_labels)
        rid = rid_by_label[rpick]

        st.warning("⚠️ 刪除該發行作品 release 會一併刪除該 release 底下的所有歌曲（songs）。")
        if st.button("確認刪除發行作品", type="primary"):
            conn = get_conn()
            try:
                # 若 DB 沒設 CASCADE，手動先刪 songs
                conn.execute("DELETE FROM songs WHERE release_id=?;", (rid,))
                conn.execute("DELETE FROM releases WHERE release_id=?;", (rid,))
                conn.commit()
                clear_cache()
                st.success("✅ 已刪除發行作品")
            except sqlite3.IntegrityError as e:
                conn.rollback()
                st.error(f"刪除失敗：{e}")
            finally:
                conn.close()

    # -------------------------
    # 刪除：團體（會連帶 members / releases / songs / member_nationalities）
    # -------------------------
    else:  # 團體
        groups = get_groups()
        if groups.empty:
            st.info("目前沒有團體。")
            return

        gpick = st.selectbox("選擇要刪除的團體 group", groups["group_name"].tolist())
        gid = int(groups.loc[groups["group_name"] == gpick, "group_id"].iloc[0])

        st.warning("⚠️ 刪除團體 group 會一併刪除：該團成員、發行作品、歌曲。不可復原。")
        if st.button("確認刪除團體", type="primary"):
            conn = get_conn()
            try:
                # 1) 刪 member_nationalities（先找出該團所有 member_id）
                mids = run_df("SELECT member_id FROM members WHERE group_id=?;", (gid,))["member_id"].tolist()
                if mids:
                    conn.executemany("DELETE FROM member_nationalities WHERE member_id=?;", [(int(x),) for x in mids])

                # 2) 刪 songs（透過 releases）
                conn.execute(
                    """
                    DELETE FROM songs
                    WHERE release_id IN (SELECT release_id FROM releases WHERE group_id=?);
                    """,
                    (gid,),
                )

                # 3) 刪 releases、members、groups
                conn.execute("DELETE FROM releases WHERE group_id=?;", (gid,))
                conn.execute("DELETE FROM members WHERE group_id=?;", (gid,))
                conn.execute("DELETE FROM groups WHERE group_id=?;", (gid,))

                conn.commit()
                clear_cache()
                st.success("✅ 已刪除團體（含關聯資料）")
            except sqlite3.IntegrityError as e:
                conn.rollback()
                st.error(f"刪除失敗：{e}")
            finally:
                conn.close()


# ---------------------------
# App Shell
# ---------------------------
def main():
    st.set_page_config(page_title="K-POP 寶典", page_icon="🎧", layout="wide")
    ensure_db()

    st.title("🎧 K-POP 寶典")

    with st.sidebar:
        st.markdown("## 🎧 K-POP Admin")

        page = st.selectbox(
            "功能選單",
            [
                "🔎 搜尋團體",
                "👤 搜尋成員",
                "🎵 搜尋歌名",
                "➕ 新增團體",
                "➕ 新增成員",
                "➕ 新增發行作品",
                "➕ 新增歌曲",
                "🛠️ 修改資料",
                "🗑️ 刪除資料"
            ],
    )


    if page == "🔎 搜尋團體":
        page_search_groups()
    elif page == "👤 搜尋成員":
        page_search_members()
    elif page == "🎵 搜尋歌名":
        page_search_songs()
    elif page == "➕ 新增團體":
        page_add_group()
    elif page == "➕ 新增成員":
        page_add_member()
    elif page == "➕ 新增發行作品":
        page_add_release()
    elif page == "➕ 新增歌曲":
        page_add_song()
    elif page == "🛠️ 修改資料":
        page_modify()
    elif page == "🗑️ 刪除資料":
        page_delete()



if __name__ == "__main__":
    main()