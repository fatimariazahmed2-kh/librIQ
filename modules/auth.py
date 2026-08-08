import hashlib
import sqlite3
from database.db_manager import db


class AuthManager:
    """Handles authentication and role-based user credentials using SQLite."""

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_password(password: str) -> str:
        if not password:
            return AuthManager._hash_password("")
        normalized = password.strip()
        if len(normalized) == 64 and all(c in "0123456789abcdefABCDEF" for c in normalized):
            return normalized.lower()
        return AuthManager._hash_password(normalized)

    @staticmethod
    def initialize_users_table():
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    name TEXT,
                    email TEXT,
                    is_authorized INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            conn.commit()

            cursor.execute("PRAGMA table_info(users)")
            existing_columns = [row["name"] for row in cursor.fetchall()]
            needs_migration = (
                set(existing_columns) !=
                {"username", "password", "role", "name", "email", "is_authorized", "created_at"}
            )

            if needs_migration:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users_temp (
                        username TEXT PRIMARY KEY,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        name TEXT,
                        email TEXT,
                        is_authorized INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT (datetime('now', 'localtime'))
                    )
                    """
                )

                try:
                    cursor.execute("SELECT * FROM users")
                    rows = cursor.fetchall()
                except sqlite3.Error:
                    rows = []

                for row in rows:
                    row_data = dict(row)
                    username = row_data.get("username")
                    password = AuthManager._normalize_password(row_data.get("password", ""))
                    role = row_data.get("role", "Staff")
                    name = row_data.get("name") if "name" in row_data else None
                    email = row_data.get("email") if "email" in row_data else None
                    is_authorized = row_data.get("is_authorized", 1)
                    created_at = row_data.get("created_at") if "created_at" in row_data else None

                    if username:
                        cursor.execute(
                            "INSERT OR REPLACE INTO users_temp (username, password, role, name, email, is_authorized, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                username,
                                password,
                                role,
                                name,
                                email,
                                is_authorized,
                                created_at,
                            ),
                        )

                cursor.execute("DROP TABLE users")
                cursor.execute("ALTER TABLE users_temp RENAME TO users")
                conn.commit()

            cursor.execute("PRAGMA table_info(users)")
            existing_columns = [row["name"] for row in cursor.fetchall()]
            if "email" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            if "name" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")
            if "is_authorized" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_authorized INTEGER DEFAULT 1")
            if "created_at" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT (datetime('now', 'localtime'))")
            conn.commit()

            cursor.execute("SELECT username, password FROM users")
            for row in cursor.fetchall():
                username = row["username"]
                password = row["password"]
                normalized_password = AuthManager._normalize_password(password)
                if normalized_password != password:
                    cursor.execute(
                        "UPDATE users SET password = ? WHERE username = ?",
                        (normalized_password, username),
                    )
            conn.commit()

            default_users = {
                "admin": {
                    "password": AuthManager._hash_password("admin123"),
                    "role": "Admin",
                    "name": "System Administrator",
                    "email": "admin@library.com",
                },
                "librarian": {
                    "password": AuthManager._hash_password("lib123"),
                    "role": "Librarian",
                    "name": "Head Librarian",
                    "email": "librarian@library.com",
                },
                "STF-101": {
                    "password": AuthManager._hash_password("staff123"),
                    "role": "Staff",
                    "name": "John Doe",
                    "email": "john@library.com",
                },
            }

            for username, user_meta in default_users.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO users (username, password, role, name, email, is_authorized) VALUES (?, ?, ?, ?, ?, 1)",
                    (
                        username,
                        user_meta["password"],
                        user_meta["role"],
                        user_meta["name"],
                        user_meta["email"],
                    ),
                )
            conn.commit()
        except sqlite3.Error as e:
            print(f"Auth Table Initialization Error: {e}")
        finally:
            conn.close()

    @staticmethod
    def _get_user_record(username_or_id: str):
        AuthManager.initialize_users_table()
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)",
                (username_or_id.strip(), username_or_id.strip()),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    @staticmethod
    def login(username_or_id: str, password: str):
        """Authenticates user login across all roles (Admin, Librarian, Staff)."""
        if not username_or_id or not password:
            return {
                "success": False,
                "user": None,
                "uid": None,
                "message": "Please enter both username and password.",
            }

        user = AuthManager._get_user_record(username_or_id)
        if not user:
            return {
                "success": False,
                "user": None,
                "uid": None,
                "message": "Invalid credentials or account not found.",
            }

        if user.get("is_authorized", 1) != 1:
            return {
                "success": False,
                "user": None,
                "uid": None,
                "message": "This user is not authorized to log in.",
            }

        if user["password"] != AuthManager._hash_password(password):
            return {
                "success": False,
                "user": None,
                "uid": None,
                "message": "Invalid credentials or account not found.",
            }

        return {
            "success": True,
            "user": {
                "username": user["username"],
                "role": user["role"],
                "name": user.get("name", ""),
                "email": user.get("email", ""),
            },
            "uid": user["username"],
            "message": "Login successful!",
        }

    @staticmethod
    def authenticate(role: str, username_or_id: str, password: str):
        """Authenticates the user and verifies the chosen role matches the stored role."""
        result = AuthManager.login(username_or_id, password)
        if not result["success"]:
            return result

        if result["user"].get("role", "").lower() != role.lower():
            return {
                "success": False,
                "user": None,
                "uid": None,
                "message": "Role mismatch. Please select the correct role.",
            }

        return result

    @staticmethod
    def register_user(user_id: str, name: str, email: str, role: str, raw_password: str = "staff123"):
        """Registers a new staff or user with login access."""
        if not user_id or not raw_password:
            return {"success": False, "message": "Username and password are required."}

        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO users (username, password, role, name, email, is_authorized) VALUES (?, ?, ?, ?, ?, 1)",
                (
                    user_id.strip(),
                    AuthManager._hash_password(raw_password),
                    role.title(),
                    name.strip(),
                    email.strip(),
                ),
            )
            conn.commit()
            return {"success": True, "message": f"User {user_id} registered successfully!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def change_password(username_or_id: str, current_pass: str, new_pass: str):
        """Validates current password and updates to new password."""
        if not current_pass or not new_pass:
            return {"success": False, "message": "Both current and new password are required."}

        user = AuthManager._get_user_record(username_or_id)
        if not user:
            return {"success": False, "message": "User account not found!"}

        if user["password"] != AuthManager._hash_password(current_pass):
            return {"success": False, "message": "Current password does not match!"}

        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (AuthManager._hash_password(new_pass), user["username"]),
            )
            conn.commit()
            return {"success": True, "message": "Password changed successfully!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def update_name(username_or_id: str, new_name: str):
        """Updates the display name for a user account."""
        if not new_name:
            return {"success": False, "message": "Name cannot be empty."}

        user = AuthManager._get_user_record(username_or_id)
        if not user:
            return {"success": False, "message": "User account not found!"}

        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET name = ? WHERE username = ?",
                (new_name.strip(), user["username"]),
            )
            conn.commit()
            return {"success": True, "message": "Account name updated successfully!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def revoke_user(username_or_id: str):
        """Revokes access for a user account immediately."""
        user = AuthManager._get_user_record(username_or_id)
        if not user:
            return {"success": False, "message": "User account not found!"}

        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET is_authorized = 0 WHERE username = ?",
                (user["username"],),
            )
            conn.commit()
            return {"success": True, "message": "User access revoked successfully."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()
