from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import sqlite3
from datetime import date

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
MEMBER_REPORT_TEMPLATE_FILE = BASE_DIR / "member_report_template.html"
FLEETSCOUT_ICON_FILE = BASE_DIR / "Fleetscout_icon.png"
FLEETSCOUT_LOGO_FILE = BASE_DIR / "fleetsout-logo.png"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect("db.sqlite3")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        team_id INTEGER,
        profile_image TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS annotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        batch_name TEXT,
        image_count INTEGER,
        created_at DATE
    )
    """)

    conn.commit()

    # Insert default data
    cur.execute("SELECT COUNT(*) FROM teams")
    if cur.fetchone()[0] == 0:
        teams = ['Team 3','Team 5','Team 6','Team 7','Team 8']
        for t in teams:
            cur.execute("INSERT INTO teams (name) VALUES (?)", (t,))

        members = [
            ('Sandeep',1),('Adity',1),
            ('Koushik',2),('Bhaskar',2),
            ('Himanshu',3),('Shivam',3),
            ('Druvh',4),('Ashis',4),
            ('Partha',5),('Piyush',5)
        ]

        for m in members:
            cur.execute("INSERT INTO members (name, team_id) VALUES (?,?)", m)

        conn.commit()

    # Backward-compatible migration for existing databases.
    try:
        cur.execute("ALTER TABLE members ADD COLUMN profile_image TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists.
        pass

init_db()

@app.get("/")
def root():
    return FileResponse(INDEX_FILE)

@app.get("/annotation-dashboard")
def annotation_dashboard_page():
    return FileResponse(INDEX_FILE)

@app.get("/team-report-dashboard")
def team_report_dashboard_page():
    return FileResponse(INDEX_FILE)

@app.get("/date-range-report-dashboard")
def date_range_report_dashboard_page():
    return FileResponse(INDEX_FILE)

@app.get("/member-settings-dashboard")
def member_settings_dashboard_page():
    return FileResponse(INDEX_FILE)

@app.get("/member-report-template")
def member_report_template():
    return FileResponse(MEMBER_REPORT_TEMPLATE_FILE)

@app.get("/fleetscout-icon")
def fleetscout_icon():
    return FileResponse(FLEETSCOUT_ICON_FILE)

@app.get("/fleetscout-logo")
def fleetscout_logo():
    return FileResponse(FLEETSCOUT_LOGO_FILE)

@app.get("/teams")
def get_teams():
    conn = get_db()
    return conn.execute("SELECT * FROM teams").fetchall()

@app.get("/members/{team_id}")
def get_members(team_id: int):
    conn = get_db()
    return conn.execute(
        "SELECT * FROM members WHERE team_id=?",
        (team_id,)
    ).fetchall()

@app.get("/members-directory")
def get_members_directory():
    conn = get_db()
    return conn.execute("""
        SELECT
            m.id,
            m.name,
            m.team_id,
            m.profile_image,
            t.name as team_name
        FROM members m
        JOIN teams t ON t.id = m.team_id
        ORDER BY t.id, m.id
    """).fetchall()

@app.put("/members/{member_id}")
def update_member(member_id: int, data: dict):
    conn = get_db()
    name = (data.get("name") or "").strip()
    profile_image = (data.get("profile_image") or "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Member name is required")

    existing = conn.execute(
        "SELECT id FROM members WHERE id = ?",
        (member_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Member not found")

    conn.execute(
        "UPDATE members SET name = ?, profile_image = ? WHERE id = ?",
        (name, profile_image, member_id)
    )
    conn.commit()
    return {"status": "ok"}

@app.post("/add")
def add_entry(data: dict):
    conn = get_db()
    entry_date = data.get("created_at", str(date.today()))
    batch_name = (data.get("batch_name") or "").strip()

    duplicate = conn.execute(
        """
        SELECT 1
        FROM annotations
        WHERE LOWER(TRIM(batch_name)) = LOWER(TRIM(?))
        LIMIT 1
        """,
        (batch_name,)
    ).fetchone()

    if duplicate:
        raise HTTPException(status_code=409, detail="Batch Alredy exist")

    conn.execute(
        "INSERT INTO annotations (member_id, batch_name, image_count, created_at) VALUES (?,?,?,?)",
        (data["member_id"], batch_name, data["image_count"], entry_date)
    )
    conn.commit()
    return {"status": "ok"}

@app.put("/annotations/{annotation_id}")
def update_annotation(annotation_id: int, data: dict):
    conn = get_db()
    batch_name = (data.get("batch_name") or "").strip()
    image_count = data.get("image_count")

    if not batch_name or image_count is None:
        raise HTTPException(status_code=400, detail="Batch name and image count are required")
    try:
        image_count = int(image_count)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Image count must be a number")

    if image_count <= 0:
        raise HTTPException(status_code=400, detail="Image count must be greater than zero")

    existing = conn.execute(
        "SELECT id FROM annotations WHERE id = ?",
        (annotation_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found")

    duplicate = conn.execute(
        """
        SELECT 1
        FROM annotations
        WHERE LOWER(TRIM(batch_name)) = LOWER(TRIM(?))
          AND id != ?
        LIMIT 1
        """,
        (batch_name, annotation_id)
    ).fetchone()
    if duplicate:
        raise HTTPException(status_code=409, detail="Batch Alredy exist")

    conn.execute(
        "UPDATE annotations SET batch_name = ?, image_count = ? WHERE id = ?",
        (batch_name, image_count, annotation_id)
    )
    conn.commit()
    return {"status": "ok"}

@app.delete("/annotations/{annotation_id}")
def delete_annotation(annotation_id: int):
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM annotations WHERE id = ?",
        (annotation_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found")

    conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
    conn.commit()
    return {"status": "ok"}

@app.get("/report/person-by-date/{selected_date}")
def report_person_by_date(selected_date: str):
    conn = get_db()
    return conn.execute("""
        SELECT m.name, SUM(a.image_count) as total
        FROM annotations a
        JOIN members m ON a.member_id = m.id
        WHERE a.created_at = ?
        GROUP BY m.id
    """, (selected_date,)).fetchall()

@app.get("/report/team-detail/{selected_date}")
def report_team_detail(selected_date: str):
    conn = get_db()
    return conn.execute("""
        SELECT
            t.name as team,
            m.id as member_id,
            m.name as member,
            SUM(a.image_count) as total
        FROM annotations a
        JOIN members m ON a.member_id = m.id
        JOIN teams t ON m.team_id = t.id
        WHERE a.created_at = ?
        GROUP BY t.id, m.id
    """, (selected_date,)).fetchall()

@app.get("/report/person")
def report_person():
    conn = get_db()
    return conn.execute("""
        SELECT m.name, SUM(a.image_count) as total
        FROM annotations a
        JOIN members m ON a.member_id = m.id
        GROUP BY m.id
    """).fetchall()

@app.get("/report/team")
def report_team():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            t.id as team_id,
            t.name as name,
            m.id as member_id,
            m.name as member_name,
            COALESCE(SUM(a.image_count), 0) as member_total
        FROM teams t
        LEFT JOIN members m ON m.team_id = t.id
        LEFT JOIN annotations a ON a.member_id = m.id
        GROUP BY t.id, m.id
        ORDER BY t.id, member_total DESC, m.id
    """).fetchall()

    teams = {}
    for row in rows:
        team_id = row["team_id"]
        if team_id not in teams:
            teams[team_id] = {
                "team_id": team_id,
                "name": row["name"],
                "total": 0,
                "members": []
            }

        member_total = row["member_total"] or 0
        teams[team_id]["total"] += member_total

        if row["member_id"] is not None and member_total > 0:
            teams[team_id]["members"].append({
                "member_id": row["member_id"],
                "name": row["member_name"],
                "total": member_total
            })

    return list(teams.values())

@app.get("/report/team-by-range/{start_date}/{end_date}")
def report_team_by_range(start_date: str, end_date: str):
    conn = get_db()
    return conn.execute("""
        SELECT
            t.id as team_id,
            t.name as team_name,
            COALESCE(SUM(a.image_count), 0) as total
        FROM teams t
        LEFT JOIN members m ON m.team_id = t.id
        LEFT JOIN annotations a
            ON a.member_id = m.id
            AND a.created_at BETWEEN ? AND ?
        GROUP BY t.id
        ORDER BY t.id
    """, (start_date, end_date)).fetchall()

@app.get("/report/member-by-range/{start_date}/{end_date}")
def report_member_by_range(start_date: str, end_date: str):
    conn = get_db()
    return conn.execute("""
        SELECT
            m.id as member_id,
            m.name as member_name,
            t.name as team_name,
            COALESCE(SUM(a.image_count), 0) as total
        FROM members m
        JOIN teams t ON t.id = m.team_id
        LEFT JOIN annotations a
            ON a.member_id = m.id
            AND a.created_at BETWEEN ? AND ?
        GROUP BY m.id
        ORDER BY t.id, m.id
    """, (start_date, end_date)).fetchall()

@app.get("/report/member-batches-by-range/{member_id}/{start_date}/{end_date}")
def report_member_batches_by_range(member_id: int, start_date: str, end_date: str):
    conn = get_db()
    return conn.execute("""
        SELECT
            id,
            batch_name,
            image_count,
            created_at
        FROM annotations
        WHERE member_id = ?
          AND created_at BETWEEN ? AND ?
        ORDER BY created_at DESC, id DESC
    """, (member_id, start_date, end_date)).fetchall()

@app.get("/report/batch-submitter/{batch_name}")
def report_batch_submitter(batch_name: str):
    normalized_batch = (batch_name or "").strip()
    if not normalized_batch:
        raise HTTPException(status_code=400, detail="Batch number is required")

    conn = get_db()
    row = conn.execute("""
        SELECT
            a.id,
            a.batch_name,
            a.image_count,
            a.created_at,
            m.id as member_id,
            m.name as member_name,
            t.id as team_id,
            t.name as team_name
        FROM annotations a
        JOIN members m ON a.member_id = m.id
        JOIN teams t ON m.team_id = t.id
        WHERE LOWER(TRIM(a.batch_name)) = LOWER(TRIM(?))
        ORDER BY a.id DESC
        LIMIT 1
    """, (normalized_batch,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Batch number not found")

    return dict(row)

@app.get("/report/batch-search/{batch_query}")
def report_batch_search(batch_query: str):
    normalized_query = (batch_query or "").strip()
    if not normalized_query:
        return []

    conn = get_db()
    rows = conn.execute("""
        SELECT
            a.id,
            a.batch_name,
            a.image_count,
            a.created_at,
            m.id as member_id,
            m.name as member_name,
            t.id as team_id,
            t.name as team_name
        FROM annotations a
        JOIN members m ON a.member_id = m.id
        JOIN teams t ON m.team_id = t.id
        WHERE LOWER(TRIM(a.batch_name)) LIKE '%' || LOWER(TRIM(?)) || '%'
        ORDER BY
            CASE
                WHEN LOWER(TRIM(a.batch_name)) = LOWER(TRIM(?)) THEN 0
                WHEN LOWER(TRIM(a.batch_name)) LIKE LOWER(TRIM(?)) || '%' THEN 1
                ELSE 2
            END,
            a.id DESC
        LIMIT 20
    """, (normalized_query, normalized_query, normalized_query)).fetchall()

    return [dict(row) for row in rows]

@app.get("/report/team-member-batches/{team_id}/{selected_date}")
def report_team_member_batches(team_id: int, selected_date: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT
            m.id as member_id,
            m.name as member_name,
            a.id as annotation_id,
            a.batch_name,
            a.image_count
        FROM members m
        LEFT JOIN annotations a
            ON a.member_id = m.id
            AND a.created_at = ?
        WHERE m.team_id = ?
        ORDER BY m.id, a.id
    """, (selected_date, team_id)).fetchall()

    members = {}
    for row in rows:
        member_id = row["member_id"]
        if member_id not in members:
            members[member_id] = {
                "member_id": member_id,
                "member_name": row["member_name"],
                "total_images": 0,
                "batches": []
            }

        if row["batch_name"] is not None:
            image_count = row["image_count"] or 0
            members[member_id]["total_images"] += image_count
            members[member_id]["batches"].append({
                "id": row["annotation_id"],
                "batch_name": row["batch_name"],
                "image_count": image_count
            })

    return list(members.values())
