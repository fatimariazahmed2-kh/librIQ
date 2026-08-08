import os
from datetime import datetime, timedelta
import sqlite3
from tkinter import filedialog
from database.db_manager import db
from utils.email_service import EmailService
from utils.excel_exporter import ExcelExporter
from modules.settings import SettingsManager


class StudentManager:
    """Handles Student Book Issuance, Returns, Automated 1-Day Advance Reminders, Settings Rules, and Excel Backups."""

    @staticmethod
    def issue_book(
        student_id: str,
        student_name: str,
        department: str,
        semester: str,
        email: str,
        contact: str,
        book_id: int,
        expected_return_datetime_str: str,
    ):
        """Issues a book to student, enforces max books setting limit, validates return date, decreases available quantity, and logs timestamp."""
        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # 1. Check max allowed books limit from Settings Rule
            max_allowed = int(SettingsManager.get_setting("max_books_per_student", 3))
            cursor.execute(
                "SELECT COUNT(*) as active_issues FROM student_issues WHERE student_id = ? AND status = 'Issued'",
                (student_id,),
            )
            count_row = cursor.fetchone()
            if count_row and count_row["active_issues"] >= max_allowed:
                return {
                    "success": False,
                    "message": f"Limit Reached! Student already has {count_row['active_issues']} active issued book(s). (Max Allowed: {max_allowed})",
                }

            # 2. Check book availability
            cursor.execute(
                "SELECT available_quantity, title FROM books WHERE book_id = ?",
                (book_id,),
            )
            book = cursor.fetchone()

            if not book:
                return {"success": False, "message": "Selected Book ID does not exist."}

            # Validate return date format
            valid_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%d %b %Y"]
            parsed_date = None
            for fmt in valid_formats:
                try:
                    parsed_date = datetime.strptime(expected_return_datetime_str, fmt)
                    break
                except ValueError:
                    continue

            if not parsed_date:
                return {
                    "success": False,
                    "message": "Expected return date format invalid. Use YYYY-MM-DD HH:MM:SS or YYYY-MM-DD.",
                }

            expected_return_datetime_str = parsed_date.strftime("%Y-%m-%d %H:%M:%S")

            if book["available_quantity"] < 1:
                return {
                    "success": False,
                    "message": "Book unavailable! All copies currently issued.",
                }

            if book_id <= 0:
                return {"success": False, "message": "Book ID must be greater than 0."}

            # 3. Deduct available quantity
            cursor.execute(
                """
                UPDATE books SET available_quantity = available_quantity - 1 
                WHERE book_id = ?
                """,
                (book_id,),
            )

            # 4. Record issue entry
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO student_issues 
                (student_id, student_name, department, semester, email, contact_number, book_id, issue_date_time, expected_return_date_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Issued')
                """,
                (
                    student_id,
                    student_name,
                    department,
                    semester,
                    email,
                    contact,
                    book_id,
                    now_str,
                    expected_return_datetime_str,
                ),
            )

            conn.commit()
            StudentManager._export_backup()
            return {
                "success": True,
                "message": (
                    f"Book '{book['title']}' successfully issued to {student_name}!"
                ),
            }

        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def get_student_issues(search_query: str = None, status_filter: str = None, department_filter: str = None):
        """Retrieves student issue & return records, searchable by Student ID, Name, Department, or Semester."""
        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            query = """
                SELECT i.*, b.title as book_title, r.return_id, r.return_date_time, COALESCE(r.fine_amount, 0.0) as fine_amount
                FROM student_issues i
                JOIN books b ON i.book_id = b.book_id
                LEFT JOIN book_returns r ON i.issue_id = r.issue_id
            """
            conditions = []
            params = []

            if search_query and search_query.strip():
                term = f"%{search_query.strip()}%"
                conditions.append(
                    "(i.student_id LIKE ? OR i.student_name LIKE ? OR i.department LIKE ? OR i.semester LIKE ? OR b.title LIKE ?)"
                )
                params.extend([term, term, term, term, term])

            if status_filter and status_filter.strip() and status_filter.lower() != "all":
                conditions.append("i.status = ?")
                params.append(status_filter.strip())

            if department_filter and department_filter.strip():
                conditions.append("LOWER(i.department) = LOWER(?)")
                params.append(department_filter.strip())

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY i.issue_id ASC"
            cursor.execute(query, params)
            rows = [dict(r) for r in cursor.fetchall()]

            # Real-time overdue detection: a still-Issued record past its due
            # date should show as Overdue with a live estimated fine, instead
            # of silently showing Rs 0.00 until it's actually returned.
            now = datetime.now()
            fine_per_day = float(SettingsManager.get_setting("fine_per_day", 100.0))
            max_fine = float(SettingsManager.get_setting("max_fine_limit", 500.0))
            for row in rows:
                if row["status"] == "Issued" and row.get("expected_return_date_time"):
                    try:
                        due = datetime.strptime(row["expected_return_date_time"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            due = datetime.strptime(row["expected_return_date_time"].split()[0], "%Y-%m-%d")
                        except ValueError:
                            due = None
                    if due and now > due:
                        overdue_days = (now - due).days + 1
                        row["status"] = "Overdue"
                        row["fine_amount"] = min(overdue_days * fine_per_day, max_fine)

            return rows
        except sqlite3.Error as e:
            print(f"Error fetching student issues: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def update_issue_record(issue_id: int, department: str, semester: str, email: str, contact_number: str, expected_return_datetime_str: str):
        """Updates only the editable fields of an active issue record.

        Student ID, Student Name, Book, and Issue Date remain locked (identity/audit fields).
        Only records with status 'Issued' can be edited — returned records stay locked.
        """
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT status FROM student_issues WHERE issue_id = ?", (issue_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "Issue record not found."}
            if row["status"] != "Issued":
                return {"success": False, "message": "Only active (Issued) records can be edited. Returned records are locked."}

            department = (department or "").strip()
            semester = (semester or "").strip()
            email = (email or "").strip()
            contact_number = (contact_number or "").strip()

            valid_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%d %b %Y"]
            parsed_date = None
            for fmt in valid_formats:
                try:
                    parsed_date = datetime.strptime(expected_return_datetime_str, fmt)
                    break
                except ValueError:
                    continue
            if not parsed_date:
                return {
                    "success": False,
                    "message": "Expected return date format invalid. Use YYYY-MM-DD HH:MM:SS or YYYY-MM-DD.",
                }
            expected_return_datetime_str = parsed_date.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                """
                UPDATE student_issues
                SET department = ?, semester = ?, email = ?, contact_number = ?, expected_return_date_time = ?
                WHERE issue_id = ?
                """,
                (department, semester, email, contact_number, expected_return_datetime_str, issue_id),
            )
            conn.commit()
            StudentManager._export_backup()
            return {"success": True, "message": "Issue record updated successfully!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def process_return_book(student_id: str):
        """Retrieves record, calculates fine dynamically from Settings rules, updates status to Returned, and restores book quantity."""
        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT * FROM student_issues 
                WHERE student_id = ? AND status = 'Issued'
                ORDER BY issue_id DESC LIMIT 1
                """,
                (student_id,),
            )
            issue = cursor.fetchone()

            if not issue:
                return {
                    "success": False,
                    "message": "No active issued book record found for this Student ID.",
                }

            issue_dict = dict(issue)
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            # Fine Calculation based on Settings rules
            fine_amount = 0.0
            try:
                expected_date = datetime.strptime(
                    issue_dict["expected_return_date_time"], "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                expected_date = datetime.strptime(
                    issue_dict["expected_return_date_time"].split()[0], "%Y-%m-%d"
                )

            if now > expected_date:
                overdue_days = (now - expected_date).days + 1
                if overdue_days > 0:
                    fine_per_day = float(SettingsManager.get_setting("fine_per_day", 100.0))
                    max_fine = float(SettingsManager.get_setting("max_fine_limit", 500.0))
                    fine_amount = min(overdue_days * fine_per_day, max_fine)

            # Restore book quantity
            cursor.execute(
                """
                UPDATE books SET available_quantity = available_quantity + 1 
                WHERE book_id = ?
                """,
                (issue_dict["book_id"],),
            )

            # Update issue status
            cursor.execute(
                """
                UPDATE student_issues 
                SET status = 'Returned' 
                WHERE issue_id = ?
                """,
                (issue_dict["issue_id"],),
            )

            # Log return entry with computed fine
            cursor.execute(
                """
                INSERT INTO book_returns (issue_id, student_id, book_id, return_date_time, fine_amount, status)
                VALUES (?, ?, ?, ?, ?, 'Returned')
                """,
                (issue_dict["issue_id"], student_id, issue_dict["book_id"], now_str, fine_amount),
            )

            conn.commit()
            StudentManager._export_backup()

            msg = f"Book return processed successfully for Student ID {student_id}!"
            if fine_amount > 0:
                msg += f" Overdue Fine Charged: Rs. {fine_amount:.2f}"

            return {
                "success": True,
                "message": msg,
                "record": issue_dict,
                "fine_amount": fine_amount,
            }

        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def delete_issue_record(issue_id: int, user_role: str = "staff"):
        if str(user_role).lower() != "admin":
            return {"success": False, "message": "Only admin users can delete issued book records."}

        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT book_id, status FROM student_issues WHERE issue_id = ?",
                (issue_id,),
            )
            issue = cursor.fetchone()
            if not issue:
                return {"success": False, "message": "Issue record not found."}

            if issue["status"] != "Issued":
                return {"success": False, "message": "Only active issued records may be deleted using the issue record path."}

            cursor.execute(
                "UPDATE books SET available_quantity = available_quantity + 1 WHERE book_id = ?",
                (issue["book_id"],),
            )
            cursor.execute("DELETE FROM student_issues WHERE issue_id = ?", (issue_id,))
            conn.commit()
            StudentManager._export_backup()
            return {"success": True, "message": "Issued book record deleted and inventory restored."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def delete_return_record(return_id: int, user_role: str = "staff"):
        if str(user_role).lower() != "admin":
            return {"success": False, "message": "Only admin users can delete return records."}

        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT issue_id, book_id FROM book_returns WHERE return_id = ?",
                (return_id,),
            )
            return_entry = cursor.fetchone()
            if not return_entry:
                return {"success": False, "message": "Return record not found."}

            cursor.execute(
                "SELECT status FROM student_issues WHERE issue_id = ?",
                (return_entry["issue_id"],),
            )
            issue = cursor.fetchone()
            if issue and issue["status"] == "Returned":
                cursor.execute(
                    "UPDATE student_issues SET status = 'Issued' WHERE issue_id = ?",
                    (return_entry["issue_id"],),
                )
                cursor.execute(
                    "UPDATE books SET available_quantity = available_quantity - 1 WHERE book_id = ? AND available_quantity > 0",
                    (return_entry["book_id"],),
                )

            cursor.execute("DELETE FROM book_returns WHERE return_id = ?", (return_id,))
            conn.commit()
            StudentManager._export_backup()
            return {"success": True, "message": "Return record deleted and issue state restored."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def send_advance_reminders(librarian_email: str, librarian_password: str):
        """Checks for books due tomorrow and sends reminder emails."""
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT i.*, b.title as book_title 
                FROM student_issues i
                JOIN books b ON i.book_id = b.book_id
                WHERE i.status = 'Issued' AND DATE(i.expected_return_date_time) = ?
                """,
                (tomorrow_date,),
            )
            due_records = cursor.fetchall()

            sent_count = 0
            for rec in due_records:
                res = EmailService.send_return_reminder(
                    librarian_email,
                    librarian_password,
                    rec["email"],
                    rec["student_name"],
                    rec["department"],
                    rec["book_title"],
                    rec["expected_return_date_time"],
                )
                if res["success"]:
                    sent_count += 1

            return {
                "success": True,
                "message": f"Sent {sent_count} reminder emails to students.",
            }
        except Exception as e:
            return {"success": False, "message": f"Reminder Execution Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def _export_backup():
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_path = os.path.join(root_dir, "data", "issue_return_backup.xlsx")
        issues = StudentManager.get_student_issues()
        if not issues:
            return
        columns = [
            "Issue ID",
            "Student ID",
            "Student Name",
            "Department",
            "Semester",
            "Email",
            "Contact",
            "Book ID",
            "Book Title",
            "Issue Date",
            "Expected Return",
            "Status",
            "Actual Return Date",
            "Fine (PKR)",
        ]
        rows = [
            [
                s["issue_id"],
                s["student_id"],
                s["student_name"],
                s["department"],
                s["semester"],
                s["email"],
                s["contact_number"],
                s["book_id"],
                s["book_title"],
                s["issue_date_time"],
                s["expected_return_date_time"],
                s["status"],
                s.get("return_date_time") if s.get("return_date_time") else "N/A",
                f"Rs. {s.get('fine_amount', 0.0):.2f}",
            ]
            for s in issues
        ]
        result = ExcelExporter.export_table_to_excel(columns, rows, backup_path, backup_path)
        if not result.get("success"):
            print(f"[Issue/Return Auto-Backup Warning] {result.get('message')}")
        return result

    @staticmethod
    def export_to_excel(file_path: str = None):
        """Exports all student issue and return records to an Excel workbook."""
        issues = StudentManager.get_student_issues()
        if not issues:
            return {"success": False, "message": "No student records to export."}

        if not file_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
                initialfile="student_records_backup.xlsx",
                title="Save Issue/Return Backup",
            )

            if not file_path:
                return {"success": False, "message": "Export cancelled by user."}

        columns = [
            "Issue ID",
            "Student ID",
            "Student Name",
            "Department",
            "Semester",
            "Email",
            "Contact",
            "Book ID",
            "Book Title",
            "Issue Date",
            "Expected Return",
            "Status",
            "Actual Return Date",
            "Fine (PKR)",
        ]
        rows = [
            [
                s["issue_id"],
                s["student_id"],
                s["student_name"],
                s["department"],
                s["semester"],
                s["email"],
                s["contact_number"],
                s["book_id"],
                s["book_title"],
                s["issue_date_time"],
                s["expected_return_date_time"],
                s["status"],
                s.get("return_date_time") if s.get("return_date_time") else "N/A",
                f"Rs. {s.get('fine_amount', 0.0):.2f}",
            ]
            for s in issues
        ]

        return ExcelExporter.export_table_to_excel(
            columns,
            rows,
            "student_records_backup.xlsx",
            file_path=file_path,
        )