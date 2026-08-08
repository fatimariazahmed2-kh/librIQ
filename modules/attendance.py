import os
from datetime import datetime
import sqlite3
from database.db_manager import db
from utils.excel_exporter import ExcelExporter


class AttendanceManager:
  """Handles Student Entry Check-In and Check-Out Timings ONLY."""

  @staticmethod
  def check_in(student_name: str, student_id: str, department: str):
    """Logs student arrival with current date and check-in timestamp."""
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
      student_name = (student_name or "").strip()
      student_id = (student_id or "").strip()
      department = (department or "").strip()
      if not student_name or not student_id:
        return {"success": False, "message": "Student name and ID are required."}

      now = datetime.now()
      today_str = now.strftime("%Y-%m-%d")
      time_str = now.strftime("%Y-%m-%d %H:%M:%S")

      cursor.execute(
          """
                INSERT INTO attendance (student_full_name, student_id, department, check_in_time, date)
                VALUES (?, ?, ?, ?, ?)
            """,
          (student_name, student_id, department, time_str, today_str),
      )
      conn.commit()
      AttendanceManager._export_backup()
      return {
          "success": True,
          "message": f"Check-In successful for {student_name} at {now.strftime('%I:%M %p')}!",
      }
    except sqlite3.Error as e:
      return {"success": False, "message": f"Database Error: {str(e)}"}
    finally:
      conn.close()

  @staticmethod
  def check_out(student_id: str):
    """Fetches active check-in by Student ID and logs departure timestamp."""
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
      today_str = datetime.now().strftime("%Y-%m-%d")
      now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

      cursor.execute(
          """
                SELECT log_id, student_full_name
                FROM attendance
                WHERE student_id = ? AND date = ? AND check_out_time IS NULL
                ORDER BY log_id DESC LIMIT 1
            """,
          (student_id, today_str),
      )
      record = cursor.fetchone()

      if not record:
        return {
            "success": False,
            "message": "No active Check-In record found for today.",
        }

      log_id = record["log_id"]
      student_name = record["student_full_name"]

      cursor.execute(
          """
                UPDATE attendance
                SET check_out_time = ?
                WHERE log_id = ?
            """,
          (now_str, log_id),
      )

      conn.commit()
      AttendanceManager._export_backup()
      return {
          "success": True,
          "message": f"Check-Out complete for {student_name}!",
      }

    except sqlite3.Error as e:
      return {"success": False, "message": f"Database Error: {str(e)}"}
    finally:
      conn.close()

  @staticmethod
  def update_attendance(log_id: int, check_in_time: str, check_out_time: str = None):
    """Updates the check-in and check-out timestamps of an existing attendance log."""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
      check_in_time = (check_in_time or "").strip()
      check_out_time = (check_out_time or "").strip()

      if not check_in_time:
        return {"success": False, "message": "Check-In time is required."}

      valid_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]

      def _parse(value):
        for fmt in valid_formats:
          try:
            return datetime.strptime(value, fmt)
          except ValueError:
            continue
        return None

      parsed_in = _parse(check_in_time)
      if not parsed_in:
        return {"success": False, "message": "Invalid Check-In time format. Use YYYY-MM-DD HH:MM:SS."}

      parsed_out = None
      if check_out_time:
        parsed_out = _parse(check_out_time)
        if not parsed_out:
          return {"success": False, "message": "Invalid Check-Out time format. Use YYYY-MM-DD HH:MM:SS."}
        if parsed_out < parsed_in:
          return {"success": False, "message": "Check-Out time cannot be earlier than Check-In time."}

      cursor.execute("SELECT log_id FROM attendance WHERE log_id = ?", (log_id,))
      if not cursor.fetchone():
        return {"success": False, "message": "Attendance record not found."}

      cursor.execute(
          "UPDATE attendance SET check_in_time = ?, check_out_time = ?, date = ? WHERE log_id = ?",
          (check_in_time, check_out_time if check_out_time else None, parsed_in.strftime("%Y-%m-%d"), log_id),
      )
      conn.commit()
      AttendanceManager._export_backup()
      return {"success": True, "message": "Attendance record updated successfully!"}
    except sqlite3.Error as e:
      return {"success": False, "message": f"Database Error: {str(e)}"}
    finally:
      conn.close()

  @staticmethod
  def get_all_attendance(search_query: str = None, date_filter: str = None):
    """Retrieves all attendance logs."""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
      query = "SELECT * FROM attendance"
      conditions = []
      params = []

      if search_query and search_query.strip():
        term = f"%{search_query.strip()}%"
        conditions.append("(LOWER(student_full_name) LIKE ? OR LOWER(student_id) LIKE ? OR LOWER(department) LIKE ? OR date LIKE ?)")
        params.extend([term, term, term, term])

      if date_filter and date_filter.strip():
        conditions.append("date = ?")
        params.append(date_filter.strip())

      if conditions:
        query += " WHERE " + " AND ".join(conditions)

      query += " ORDER BY log_id ASC"
      cursor.execute(query, params)
      rows = cursor.fetchall()
      return [dict(r) for r in rows]
    except sqlite3.Error as e:
      print(f"Error fetching attendance: {e}")
      return []
    finally:
      conn.close()

  @staticmethod
  def delete_attendance_log(log_id: int, user_role: str = "staff"):
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
      if user_role.lower() != "admin":
        return {"success": False, "message": "Only admin users can delete attendance records."}

      cursor.execute("DELETE FROM attendance WHERE log_id = ?", (log_id,))
      conn.commit()
      AttendanceManager._export_backup()
      return {"success": True, "message": "Attendance record deleted successfully."}
    except sqlite3.Error as e:
      return {"success": False, "message": f"Database Error: {str(e)}"}
    finally:
      conn.close()

  @staticmethod
  def get_todays_summary():
    """Returns today's attendance check-in and check-out totals."""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
      today_str = datetime.now().strftime("%Y-%m-%d")
      cursor.execute(
          "SELECT COUNT(check_in_time) as total_checkins, COUNT(check_out_time) as total_checkouts FROM attendance WHERE date = ?",
          (today_str,),
      )
      row = cursor.fetchone()
      return {
          "total_checkins": row["total_checkins"] if row else 0,
          "total_checkouts": row["total_checkouts"] if row else 0,
      }
    except sqlite3.Error as e:
      print(f"Error fetching today\'s attendance summary: {e}")
      return {"total_checkins": 0, "total_checkouts": 0}
    finally:
      conn.close()

  @staticmethod
  def _export_backup():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backup_path = os.path.join(root_dir, "data", "attendance_backup.xlsx")
    logs = AttendanceManager.get_all_attendance()
    columns = [
        "Log ID",
        "Student Name",
        "Student ID",
        "Department",
        "Check-In Time",
        "Check-Out Time",
        "Date",
    ]
    rows = [
        [
            l["log_id"],
            l["student_full_name"],
            l["student_id"],
            l["department"],
            l["check_in_time"],
            l["check_out_time"] if l["check_out_time"] else "In Library",
            l["date"],
        ]
        for l in logs
    ]
    result = ExcelExporter.export_table_to_excel(columns, rows, backup_path, backup_path)
    if not result.get("success"):
        print(f"[Attendance Auto-Backup Warning] {result.get('message')}")
    return result

  @staticmethod
  def export_to_excel():
    """Exports attendance records to Excel."""
    logs = AttendanceManager.get_all_attendance()
    if not logs:
      return {"success": False, "message": "No attendance records to export."}

    columns = [
        "Log ID",
        "Student Name",
        "Student ID",
        "Department",
        "Check-In Time",
        "Check-Out Time",
        "Date",
    ]
    rows = [
        [
            l["log_id"],
            l["student_full_name"],
            l["student_id"],
            l["department"],
            l["check_in_time"],
            l["check_out_time"] if l["check_out_time"] else "In Library",
            l["date"],
        ]
        for l in logs
    ]

    return ExcelExporter.export_table_to_excel(
        columns, rows, "attendance_backup.xlsx"
    )