import sqlite3

def init_db(db_name):
    """Creates the database and the translations table for the current session."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_text TEXT NOT NULL,
            translated_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_translation(db_name, original, translated):
    """Saves a new translation into the session's database."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (original_text, translated_text) VALUES (?, ?)",
        (original, translated)
    )
    conn.commit()
    conn.close()

def get_all_translations(db_name):
    """Retrieves all saved translations from the session."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT original_text, translated_text FROM history ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_last_entry(db_name):
    """Deletes the most recently added translation from the session database."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    # Find the highest ID (the last inserted row) and delete it
    cursor.execute("DELETE FROM history WHERE id = (SELECT MAX(id) FROM history)")
    conn.commit()
    conn.close()