from datetime import datetime, timedelta
import sqlite3
from database.db_manager import db
from modules.settings import SettingsManager
from utils.email_service import EmailService

class AnalyticsManager:
    """Handles data analytics for peak check-ins, department breakdown, borrowed categories, and fine collection."""

    @staticmethod
    def get_peak_checkin_trend():
        """Function 1: Peak check-in time and hourly trend for Line Chart.
        Falls back to the last 7 days combined if today has no check-ins yet,
        so the chart isn't empty on a fresh/quiet day."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")

            def _fetch_hourly(date_filter_sql, params):
                cursor.execute(
                    f"""
                    SELECT strftime('%H:00', check_in_time) as hour, COUNT(*) as count
                    FROM attendance
                    WHERE {date_filter_sql} AND check_in_time IS NOT NULL
                    GROUP BY hour
                    ORDER BY hour ASC
                    """,
                    params,
                )
                return cursor.fetchall()

            hourly_rows = _fetch_hourly("date = ?", (today_str,))
            data_scope = "Today"
            if not hourly_rows:
                seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                hourly_rows = _fetch_hourly("date >= ?", (seven_days_ago,))
                data_scope = "Last 7 Days"

            hourly_data = {r["hour"]: r["count"] for r in hourly_rows}

            peak_time = "No Data Yet"
            total_students = 0
            if hourly_data:
                peak_hour_str = max(hourly_data, key=hourly_data.get)
                hour_int = int(peak_hour_str.split(":")[0])
                am_pm = "AM" if hour_int < 12 else "PM"
                display_hour = hour_int if 1 <= hour_int <= 12 else (hour_int - 12 if hour_int > 12 else 12)
                peak_time = f"{display_hour}:00 {am_pm}"
                total_students = hourly_data[peak_hour_str]

            return {
                "peak_time": peak_time,
                "total_students": total_students,
                "hourly_distribution": hourly_data,
                "data_scope": data_scope,
            }
        except sqlite3.Error as e:
            print(f"Peak Check-In Error: {e}")
            return {"peak_time": "N/A", "total_students": 0, "hourly_distribution": {}, "data_scope": "Today"}
        finally:
            conn.close()

    @staticmethod
    def get_most_borrowed_categories():
        """Function 2: Calculates Borrowed Count = Total Quantity - Available Quantity for Scatter Chart."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT category, title, author_name, 
                       (total_quantity - available_quantity) as borrowed_count, 
                       total_quantity, available_quantity 
                FROM books 
                ORDER BY borrowed_count DESC
                """
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            print(f"Borrowed Categories Error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def calculate_fines_and_process_alerts(librarian_email: str = "", librarian_password: str = ""):
        """Function 3: Fine Collection Engine with status counts for Pie Chart."""
        conn = db.get_connection()
        cursor = conn.cursor()
        fine_summary = []
        pie_data = {"Active Fine": 0, "FROZEN (Pay with Fees)": 0, "Cleared": 0}

        try:
            cursor.execute(
                """
                SELECT i.*, b.title as book_title 
                FROM student_issues i 
                JOIN books b ON i.book_id = b.book_id 
                WHERE i.status = 'Issued'
                """
            )
            active_issues = cursor.fetchall()
            now = datetime.now()

            fine_per_day = float(SettingsManager.get_setting("fine_per_day", 100.0))
            max_fine_limit = float(SettingsManager.get_setting("max_fine_limit", 500.0))
            for issue in active_issues:
                exp_date = datetime.strptime(issue["expected_return_date_time"], "%Y-%m-%d %H:%M:%S")
                if now > exp_date:
                    overdue_days = (now - exp_date).days + 1
                    calculated_fine = overdue_days * fine_per_day
                    is_frozen = False
                    
                    if calculated_fine >= max_fine_limit:
                        calculated_fine = max_fine_limit
                        is_frozen = True
                        pie_data["FROZEN (Pay with Fees)"] += 1
                    else:
                        pie_data["Active Fine"] += 1

                    if calculated_fine >= 300.0 and librarian_email and librarian_password:
                        EmailService.send_fine_warning(
                            librarian_email, librarian_password, issue["email"],
                            issue["student_name"], issue["department"], calculated_fine
                        )

                    fine_summary.append({
                        "student_name": issue["student_name"],
                        "student_id": issue["student_id"],
                        "department": issue["department"],
                        "book_title": issue["book_title"],
                        "days_overdue": overdue_days,
                        "fine_amount": calculated_fine,
                        "status": "FROZEN (Pay with Fees)" if is_frozen else "Active Fine",
                    })

            # Fetch returned count
            cursor.execute("SELECT COUNT(*) as count FROM book_returns WHERE status = 'Returned'")
            returned_row = cursor.fetchone()
            pie_data["Cleared"] = returned_row["count"] if returned_row else 0

            return {
                "fine_records": sorted(fine_summary, key=lambda x: x["fine_amount"], reverse=True),
                "pie_chart_data": pie_data
            }
        except sqlite3.Error as e:
            print(f"Fine Calculation Error: {e}")
            return {"fine_records": [], "pie_chart_data": pie_data}
        finally:
            conn.close()

    @staticmethod
    def get_department_usage_breakdown():
        """Summarizes attendance check-ins by department for dashboard charts."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT department, COUNT(*) as checkin_count FROM attendance GROUP BY department ORDER BY checkin_count DESC"
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            print(f"Department Usage Breakdown Error: {e}")
            return []
        finally:
            conn.close()