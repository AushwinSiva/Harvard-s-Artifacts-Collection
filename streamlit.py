import streamlit as st
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
import json

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Harvard Art Museum Data Explorer",
    layout="wide"
)

# ---------------- PREVENT TABLE SHRINK ----------------
st.markdown("""
<style>
[data-testid="stDataFrameResizable"] table {
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DB CONNECTION ----------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "harvard_artifacts"
}

engine = create_engine(
    f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
)

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

# ---------------- DATA FETCH WITH CACHING ----------------
@st.cache_data(show_spinner=True)
def load_from_db(classif, limit=2500):
    conn = engine.connect()

    meta_q = f"""
        SELECT id, title, culture, period, century, medium, dimensions, description,
               department, classification, accessionyear, accessionmethod
        FROM artifact_metadata
        WHERE classification=%s
        LIMIT %s
    """
    meta_df = pd.read_sql(meta_q, conn, params=(classif, limit))

    if meta_df.empty:
        conn.close()
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    ids = tuple(meta_df["id"].tolist())
    id_placeholders = ",".join(["%s"] * len(ids))

    # Media
    media_q = f"""
        SELECT objectid, imagecount, mediacount, colorcount, rank, datebegin, dateend
        FROM artifact_media
        WHERE objectid IN ({id_placeholders})
    """
    media_df = pd.read_sql(media_q, params=ids, con=conn)

    # Colors
    color_q = f"""
        SELECT objectid, color, spectrum, hue, percent, css3
        FROM artifact_colors
        WHERE objectid IN ({id_placeholders})
    """
    colors_df = pd.read_sql(color_q, params=ids, con=conn)

    conn.close()
    return meta_df, media_df, colors_df

# ---------------- MIGRATION (FIX DUPLICATES) ----------------
def insert_data_to_sql(meta_df, media_df, colors_df):
    conn = get_connection()
    cur = conn.cursor()

    # Metadata
    if not meta_df.empty:
        ids = tuple(meta_df['id'].tolist())
        cur.execute("DELETE FROM artifact_metadata WHERE id IN (" + ",".join(["%s"]*len(ids)) + ")", ids)
        conn.commit()
        cur.executemany("""
            INSERT INTO artifact_metadata
            (id, title, culture, period, century, medium, dimensions, description,
             department, classification, accessionyear, accessionmethod)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, meta_df.values.tolist())

    # Media
    if not media_df.empty:
        ids = tuple(media_df['objectid'].tolist())
        cur.execute("DELETE FROM artifact_media WHERE objectid IN (" + ",".join(["%s"]*len(ids)) + ")", ids)
        conn.commit()
        cur.executemany("""
            INSERT INTO artifact_media
            (objectid, imagecount, mediacount, colorcount, rank, datebegin, dateend)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, media_df.values.tolist())

    # Colors
    if not colors_df.empty:
        ids = tuple(colors_df['objectid'].tolist())
        cur.execute("DELETE FROM artifact_colors WHERE objectid IN (" + ",".join(["%s"]*len(ids)) + ")", ids)
        conn.commit()
        cur.executemany("""
            INSERT INTO artifact_colors
            (objectid, color, spectrum, hue, percent, css3)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, colors_df.values.tolist())

    conn.commit()
    conn.close()

# ---------------- JSON DISPLAY ----------------
def display_json_preview(df, max_rows=100):
    preview_df = df.head(max_rows)
    st.code(json.dumps(preview_df.to_dict(orient="records"), indent=4, ensure_ascii=False), language="json")

# ---------------- PREDEFINED QUERIES (16–20 FIXED) ----------------
questions_queries = {
    "1. List all artifacts from the 11th century belonging to Byzantine culture":
        "SELECT * FROM artifact_metadata WHERE century='11th century' AND culture LIKE '%Byzantine%';",
    "2. Unique cultures represented in the artifacts":
        "SELECT DISTINCT culture FROM artifact_metadata;",
    "3. List all artifacts from the Archaic Period":
        "SELECT * FROM artifact_metadata WHERE period LIKE '%Archaic%';",
    "4. Artifact titles ordered by accession year in descending order":
        "SELECT title, accessionyear FROM artifact_metadata ORDER BY accessionyear DESC;",
    "5. How many artifacts are there per department":
        "SELECT department, COUNT(*) as total FROM artifact_metadata GROUP BY department;",
    "6. Which artifacts have less than 3 images?":
        "SELECT objectid, imagecount FROM artifact_media WHERE imagecount < 3;",
    "7. What is the average rank of all artifacts?":
        "SELECT AVG(rank) as avg_rank FROM artifact_media;",
    "8. Which artifacts have a lower media count than color count?":
        "SELECT objectid, mediacount, colorcount FROM artifact_media WHERE mediacount < colorcount;",
    "9. List all artifacts created between 2001 and 2002":
        "SELECT * FROM artifact_media WHERE datebegin >= 2001 AND dateend <= 2002;",
    "10. How many artifacts have no media files?":
        "SELECT COUNT(*) as no_media FROM artifact_media WHERE mediacount = 0;",
    "11. What are all the distinct hues used in the dataset?":
        "SELECT DISTINCT hue FROM artifact_colors;",
    "12. Top 5 most used colors by frequency":
        "SELECT color, COUNT(*) as freq FROM artifact_colors GROUP BY color ORDER BY freq DESC LIMIT 5;",
    "13. Average coverage percentage for each hue":
        "SELECT hue, AVG(percent) as avg_percent FROM artifact_colors GROUP BY hue;",
    "14. List all colors used for a given artifact ID (example: 352919)":
        "SELECT color, hue FROM artifact_colors WHERE objectid=352919;",
    "15. Total number of color entries":
        "SELECT COUNT(*) as total_colors FROM artifact_colors;",
    # 16–20 FIXED (LIMIT + case-insensitive)
    "16. Titles and hues for all Byzantine culture artifacts":
        "SELECT m.title, c.hue FROM artifact_metadata m JOIN artifact_colors c ON m.id=c.objectid WHERE LOWER(m.culture) LIKE '%byzantine%' LIMIT 100;",
    "17. Each artifact title with associated hues":
        "SELECT m.title, c.hue FROM artifact_metadata m LEFT JOIN artifact_colors c ON m.id=c.objectid LIMIT 100;",
    "18. Titles, cultures, and media ranks where period is not null":
        "SELECT m.title, m.culture, med.rank FROM artifact_metadata m JOIN artifact_media med ON m.id=med.objectid WHERE m.period IS NOT NULL LIMIT 100;",
    "19. Titles ranked in top 10 including color hue 'Grey'":
        "SELECT m.title, c.hue, med.rank FROM artifact_metadata m JOIN artifact_colors c ON m.id=c.objectid JOIN artifact_media med ON m.id=med.objectid WHERE LOWER(c.hue)='grey' ORDER BY med.rank ASC LIMIT 10;",
    "20. Artifacts per classification with average media count":
        "SELECT m.classification, AVG(med.mediacount) as avg_media FROM artifact_metadata m JOIN artifact_media med ON m.id=med.objectid GROUP BY m.classification LIMIT 100;"
}

# ---------------- UI ----------------
st.markdown("<h2 style='text-align: center;'>🎨 Harvard Art Museum Data Explorer</h2>", unsafe_allow_html=True)

tabs = st.tabs(["Select Your Choice", "Migrate to SQL", "SQL Queries"])

# ---------------- TAB 1 ----------------
with tabs[0]:
    st.subheader("Select Classification")

    conn = engine.connect()
    class_q = """
        SELECT classification, COUNT(*) as cnt
        FROM artifact_metadata
        GROUP BY classification
        HAVING cnt >= 2500
    """
    class_df = pd.read_sql(class_q, conn)
    conn.close()

    options = class_df["classification"].tolist()
    selected = st.selectbox("Choose Classification", options)

    if selected:
        meta_df, media_df, colors_df = load_from_db(selected)

        if not meta_df.empty:
            st.subheader("JSON View (Metadata | Media | Colors)")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Metadata**")
                display_json_preview(meta_df)

            with col2:
                st.markdown("**Media**")
                display_json_preview(media_df)

            with col3:
                st.markdown("**Colors**")
                display_json_preview(colors_df)

# ---------------- TAB 2 ----------------
with tabs[1]:
    st.subheader("Insert Collected Data")

    if "acc_meta" not in st.session_state:
        st.session_state.acc_meta = pd.DataFrame()
    if "acc_media" not in st.session_state:
        st.session_state.acc_media = pd.DataFrame()
    if "acc_colors" not in st.session_state:
        st.session_state.acc_colors = pd.DataFrame()

    if selected:
        meta_df, media_df, colors_df = load_from_db(selected)

        if st.button("Insert Data"):
            insert_data_to_sql(meta_df, media_df, colors_df)
            st.session_state.acc_meta = pd.concat([st.session_state.acc_meta, meta_df], ignore_index=True)
            st.session_state.acc_media = pd.concat([st.session_state.acc_media, media_df], ignore_index=True)
            st.session_state.acc_colors = pd.concat([st.session_state.acc_colors, colors_df], ignore_index=True)
            st.success(f"✅ Data Inserted for '{selected}' and combined with previous selections!")

        st.subheader("Metadata Table")
        st.dataframe(st.session_state.acc_meta, use_container_width=True, height=600)

        st.subheader("Media Table")
        st.dataframe(st.session_state.acc_media, use_container_width=True, height=600)

        st.subheader("Colors Table")
        st.dataframe(st.session_state.acc_colors, use_container_width=True, height=600)

# ---------------- TAB 3 ----------------
with tabs[2]:
    st.subheader("Run Predefined SQL Queries")

    question = st.selectbox("Choose a query", list(questions_queries.keys()))
    if st.button("Run Query"):
        try:
            query = questions_queries[question]
            conn = engine.connect()
            result_df = pd.read_sql(query, conn)
            conn.close()
            st.dataframe(result_df, use_container_width=True, height=600)
        except Exception as e:
            st.error(f"Error: {e}")
