import sqlite3
import customtkinter as ctk
from database.db_manager import db

class SettingsManager:
    """Handles system settings persistence, configuration loading, role permissions, and application rules."""

    DEFAULT_SETTINGS = {
        "fine_per_day": "100.0",
        "max_fine_limit": "500.0",
        "max_books_per_student": "3",
        "default_issue_days": "7",
        "app_theme": "Light",
        "allow_librarian_reports": "1",
        "allow_staff_analytics": "0"
    }

    @staticmethod
    def initialize_settings_table():
        """Ensures the settings table exists with initial default configurations."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT
                )
            """)
            # Insert defaults if table is empty
            for key, val in SettingsManager.DEFAULT_SETTINGS.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
                    (key, val)
                )
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database Settings Init Error: {e}")
        finally:
            conn.close()

    @staticmethod
    def initialize_role_permissions():
        """Ensures role permissions table is present and seeded with default permissions."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            # Migration guard: an older run of this app may have already created
            # role_permissions with a different schema (missing module_key).
            # CREATE TABLE IF NOT EXISTS would silently keep that old table and
            # every query below would fail. Detect and fix that here.
            cursor.execute("PRAGMA table_info(role_permissions)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            if existing_columns and "module_key" not in existing_columns:
                cursor.execute("DROP TABLE role_permissions")
                conn.commit()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role TEXT,
                    module_key TEXT,
                    allowed INTEGER DEFAULT 1,
                    PRIMARY KEY (role, module_key)
                )
                """
            )
            default_roles = {
                "admin": {
                    "Dashboard": 1,
                    "Books": 1,
                    "Issue/Return": 1,
                    "Attendance": 1,
                    "Staff": 1,
                    "Analytics": 1,
                    "Reports": 1,
                    "Chat": 1,
                    "Settings": 1,
                },
                "librarian": {
                    "Dashboard": 1,
                    "Books": 1,
                    "Issue/Return": 1,
                    "Attendance": 1,
                    "Staff": 0,
                    "Analytics": 1,
                    "Reports": 1,
                    "Chat": 1,
                    "Settings": 1,
                },
                "staff": {
                    "Dashboard": 1,
                    "Books": 1,
                    "Issue/Return": 1,
                    "Attendance": 1,
                    "Staff": 0,
                    "Analytics": 0,
                    "Reports": 0,
                    "Chat": 1,
                    "Settings": 0,
                },
            }
            for role, modules in default_roles.items():
                for module_key, allowed in modules.items():
                    cursor.execute(
                        "INSERT OR IGNORE INTO role_permissions (role, module_key, allowed) VALUES (?, ?, ?)",
                        (role, module_key, allowed),
                    )
            conn.commit()
        except sqlite3.Error as e:
            print(f"Role Permissions Init Error: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_role_permissions(role: str = "admin"):
        """Returns module access permissions based on user role and database overrides."""
        SettingsManager.initialize_settings_table()
        SettingsManager.initialize_role_permissions()
        role_str = str(role).lower() if role else "admin"
        conn = db.get_connection()
        cursor = conn.cursor()
        permissions = {}
        try:
            cursor.execute(
                "SELECT module_key, allowed FROM role_permissions WHERE role = ?",
                (role_str,),
            )
            rows = cursor.fetchall()
            if rows:
                permissions = {r["module_key"]: bool(r["allowed"]) for r in rows}
        except sqlite3.Error as e:
            print(f"Fetch Role Permissions Error: {e}")
        finally:
            conn.close()

        if not permissions:
            return {
                "Dashboard": True,
                "Books": True,
                "Issue/Return": True,
                "Attendance": True,
                "Staff": True if role_str == "admin" else False,
                "Analytics": True if role_str in ("admin", "librarian") else False,
                "Reports": True if role_str in ("admin", "librarian") else False,
                "Chat": True,
                "Settings": True if role_str in ("admin", "librarian") else False,
            }
        return permissions

    @staticmethod
    def update_role_permission(role: str, module_key: str, allowed: int):
        """Updates a specific module permission for a given role."""
        SettingsManager.initialize_role_permissions()
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO role_permissions (role, module_key, allowed) VALUES (?, ?, ?)",
                (role.lower(), module_key, 1 if allowed else 0),
            )
            conn.commit()
            return {"success": True, "message": "Role permissions updated successfully."}
        except sqlite3.Error as e:
            return {"success": False, "message": str(e)}
        finally:
            conn.close()

    @staticmethod
    def get_all_settings():
        """Fetches all system configuration settings as a dictionary."""
        SettingsManager.initialize_settings_table()
        conn = db.get_connection()
        cursor = conn.cursor()
        settings = dict(SettingsManager.DEFAULT_SETTINGS)
        try:
            cursor.execute("SELECT setting_key, setting_value FROM system_settings")
            rows = cursor.fetchall()
            for r in rows:
                settings[r["setting_key"]] = r["setting_value"]
        except sqlite3.Error as e:
            print(f"Fetch Settings Error: {e}")
        finally:
            conn.close()
        return settings

    @staticmethod
    def get_setting(key: str, default=None):
        """Fetches a single setting value by key."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["setting_value"]
        except sqlite3.Error as e:
            print(f"Get Setting Error: {e}")
        finally:
            conn.close()
        return default if default is not None else SettingsManager.DEFAULT_SETTINGS.get(key, "")

    @staticmethod
    def update_settings(settings_dict: dict):
        """Saves updated settings to database and immediately applies global configurations like Theme."""
        SettingsManager.initialize_settings_table()
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            for key, val in settings_dict.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
                    (str(key), str(val))
                )
            conn.commit()

            # Apply Theme immediately if changed
            if "app_theme" in settings_dict:
                ctk.set_appearance_mode(settings_dict["app_theme"])

            return {"success": True, "message": "System Settings updated and applied successfully!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()