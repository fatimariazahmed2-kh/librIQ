import os
import sqlite3
from database.db_manager import db
from modules.auth import AuthManager
from utils.excel_exporter import ExcelExporter


class StaffManager:
    """Manages Staff registration, Admin authorization linkage, account suspension, and deletion."""

    @staticmethod
    def add_staff(staff_id: str, staff_name: str, contact: str, email: str, system_password: str):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            staff_id = (staff_id or "").strip()
            staff_name = (staff_name or "").strip()
            email = (email or "").strip()
            if not staff_id or not staff_name or not email:
                return {"success": False, "message": "Staff ID, name, and email are required."}

            cursor.execute("SELECT staff_id FROM staff WHERE staff_id = ?", (staff_id,))
            if cursor.fetchone():
                return {"success": False, "message": "A staff member with that ID already exists."}

            cursor.execute("SELECT username FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return {"success": False, "message": "The provided email is already associated with another account."}

            hashed_password = AuthManager._hash_password(system_password)

            cursor.execute(
                "INSERT INTO users (username, password, role, email, name, is_authorized) VALUES (?, ?, 'Staff', ?, ?, 1)",
                (staff_id, hashed_password, email, staff_name),
            )

            cursor.execute(
                "INSERT INTO staff (staff_id, staff_name, staff_contact, email, password, is_authorized) VALUES (?, ?, ?, ?, ?, 1)",
                (staff_id, staff_name, contact, email, hashed_password),
            )
            conn.commit()
            StaffManager._export_backup()
            return {"success": True, "message": f"Staff '{staff_name}' (ID: {staff_id}) successfully registered!"}
        except sqlite3.IntegrityError as e:
            return {"success": False, "message": f"Staff record conflict: {str(e)}"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def update_staff(staff_id: str, staff_name: str, contact: str, email: str, status: str = "Active", role: str = "Staff"):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            staff_id = (staff_id or "").strip()
            staff_name = (staff_name or "").strip()
            email = (email or "").strip()
            if not staff_id or not staff_name or not email:
                return {"success": False, "message": "Staff ID, name, and email are required."}

            cursor.execute("SELECT staff_id FROM staff WHERE staff_id = ?", (staff_id,))
            if not cursor.fetchone():
                return {"success": False, "message": "Staff record not found."}

            cursor.execute(
                "SELECT username FROM users WHERE email = ? AND username != ?",
                (email, staff_id),
            )
            if cursor.fetchone():
                return {"success": False, "message": "The provided email is already in use by another account."}

            is_authorized = 1 if str(status).lower() not in {"suspended", "inactive", "disabled", "0", "false"} else 0
            cursor.execute(
                """
                UPDATE staff
                SET staff_name = ?, staff_contact = ?, email = ?, is_authorized = ?
                WHERE staff_id = ?
                """,
                (staff_name, contact, email, is_authorized, staff_id),
            )
            cursor.execute(
                """
                UPDATE users
                SET name = ?, email = ?, is_authorized = ?, role = ?
                WHERE username = ?
                """,
                (staff_name, email, is_authorized, role or "Staff", staff_id),
            )
            conn.commit()
            StaffManager._export_backup()
            return {"success": True, "message": "Staff record updated successfully!"}
        except sqlite3.IntegrityError as e:
            return {"success": False, "message": f"Staff update conflict: {str(e)}"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def delete_staff(staff_id: str):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT email FROM staff WHERE staff_id = ?", (staff_id,))
            staff = cursor.fetchone()
            if staff:
                email = staff["email"]
                cursor.execute("DELETE FROM staff WHERE staff_id = ?", (staff_id,))
                cursor.execute("DELETE FROM users WHERE email = ? OR username = ?", (email, staff_id))
                conn.commit()
                StaffManager._export_backup()
                return {"success": True, "message": "Staff member deleted and login access revoked permanently!"}
            return {"success": False, "message": "Staff record not found."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def get_all_staff(search_query: str = None, status_filter: str = None):
        """Retrieves all staff members for table display."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM staff"
            conditions = []
            params = []

            if search_query and search_query.strip():
                term = f"%{search_query.strip().lower()}%"
                conditions.append(
                    "(LOWER(staff_id) LIKE ? OR LOWER(staff_name) LIKE ? OR LOWER(email) LIKE ?)"
                )
                params.extend([term, term, term])

            if status_filter and status_filter.strip() and status_filter.lower() != "all":
                expected = 1 if status_filter.lower() in {"active", "authorized"} else 0
                conditions.append("is_authorized = ?")
                params.append(expected)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY staff_id ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            print(f"Error fetching staff: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def _export_backup():
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_path = os.path.join(root_dir, "data", "staff_records_backup.xlsx")
        staff_members = StaffManager.get_all_staff()
        columns = ["Staff ID", "Name", "Contact", "Email", "Status"]
        rows = [
            [
                s["staff_id"],
                s["staff_name"],
                s["staff_contact"],
                s["email"],
                "Active" if s["is_authorized"] else "Suspended",
            ]
            for s in staff_members
        ]
        result = ExcelExporter.export_table_to_excel(columns, rows, backup_path, backup_path)
        if not result.get("success"):
            print(f"[Staff Auto-Backup Warning] {result.get('message')}")
        return result

    @staticmethod
    def export_to_excel():
        staff_members = StaffManager.get_all_staff()
        if not staff_members:
            return {"success": False, "message": "No staff records to export."}
        columns = ["Staff ID", "Name", "Contact", "Email", "Status"]
        rows = [
            [
                s["staff_id"],
                s["staff_name"],
                s["staff_contact"],
                s["email"],
                "Active" if s["is_authorized"] else "Suspended",
            ]
            for s in staff_members
        ]
        return ExcelExporter.export_table_to_excel(columns, rows, "staff_records_backup.xlsx")