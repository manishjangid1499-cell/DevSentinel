"""
Track Logging Database Module.
Patched by DevSentinel: Converted raw string concatenation to secure parameterized queries.
"""
import sqlite3

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS track_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            duration INTEGER
        )
    """)
    conn.commit()

def log_track_event(title: str, duration: int) -> bool:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()
    # Security fix: Use parameterized query (? placeholder) instead of f-string
    cursor.execute("INSERT INTO track_logs (title, duration) VALUES (?, ?)", (title, duration))
    conn.commit()
    conn.close()
    return True
