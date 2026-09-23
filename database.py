import sqlite3
from pathlib import Path

DB_PATH = Path("research.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    #documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        session_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        company TEXT,
        file_path TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id)
        REFERENCES research_sessions(session_id)
        )
    """)
    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_tables()
    print("Database and tables created successfully!")
