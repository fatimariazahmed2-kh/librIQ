import sqlite3
import os

class DatabaseManager:
    """Manages SQLite database connections and table initializations."""

    def __init__(self, db_path="data/library.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_connection(self):
        """Returns a sqlite3 connection object with Row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """Creates all required database tables if they do not exist."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    isbn TEXT,
                    category TEXT,
                    total_quantity INTEGER DEFAULT 1,
                    available_quantity INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student_issues (
                    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    student_name TEXT NOT NULL,
                    department TEXT,
                    semester TEXT,
                    email TEXT,
                    contact_number TEXT,
                    book_id INTEGER,
                    issue_date_time TEXT,
                    expected_return_date_time TEXT,
                    status TEXT DEFAULT 'Issued',
                    is_frozen INTEGER DEFAULT 0,
                    FOREIGN KEY (book_id) REFERENCES books (book_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS book_returns (
                    return_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id INTEGER,
                    student_id TEXT,
                    book_id INTEGER,
                    return_date_time TEXT,
                    fine_amount REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'Returned',
                    FOREIGN KEY (issue_id) REFERENCES student_issues (issue_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_full_name TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    department TEXT,
                    check_in_time TEXT,
                    check_out_time TEXT,
                    date TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    name TEXT,
                    email TEXT UNIQUE,
                    is_authorized INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staff (
                    staff_id TEXT PRIMARY KEY,
                    staff_name TEXT NOT NULL,
                    staff_contact TEXT,
                    email TEXT UNIQUE,
                    password TEXT,
                    is_authorized INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    message TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role TEXT,
                    module_key TEXT,
                    allowed INTEGER DEFAULT 1,
                    PRIMARY KEY (role, module_key)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    reason TEXT,
                    priority TEXT DEFAULT 'Medium',
                    category TEXT,
                    related_record_id TEXT,
                    status TEXT DEFAULT 'Pending',
                    generated_at TEXT DEFAULT (datetime('now', 'localtime')),
                    resolved_at TEXT,
                    resolved_by TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_username TEXT NOT NULL,
                    receiver_username TEXT NOT NULL,
                    message TEXT,
                    attachment_path TEXT,
                    attachment_type TEXT,
                    sent_at TEXT DEFAULT (datetime('now', 'localtime')),
                    is_read INTEGER DEFAULT 0,
                    edited INTEGER DEFAULT 0,
                    deleted_by_sender INTEGER DEFAULT 0,
                    deleted_by_receiver INTEGER DEFAULT 0
                )
            """)

            conn.commit()
        except sqlite3.Error as e:
            print(f"Database Initialization Error: {e}")
        finally:
            conn.close()

# Single global instance
db = DatabaseManager()