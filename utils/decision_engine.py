from datetime import datetime, timedelta
import sqlite3
from database.db_manager import db


class DecisionEngine:
    """Intelligent Decision Engine.

    Monitors live SQLite data (Books, Issue/Return, Attendance, Staff, Fines)
    and generates operational recommendations based on business rules. It
    never performs actions automatically — it only raises recommendations for
    a human (Admin/Librarian) to Approve or Ignore.

    Call `DecisionEngine.run_analysis()` after any data-changing action
    (book add/delete, issue, return, check-in/check-out, fine payment, staff
    activity) so decisions appear immediately rather than on a timer.
    """

    @staticmethod
    def run_analysis():
        conn = db.get_connection()
        cursor = conn.cursor()
        new_decisions = []
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            checks = [
                DecisionEngine._rule_low_occupancy,
                DecisionEngine._rule_high_occupancy,
                DecisionEngine._rule_sustained_high_occupancy,
                DecisionEngine._rule_low_stock,
                DecisionEngine._rule_high_demand_book,
                DecisionEngine._rule_department_overdue,
                DecisionEngine._rule_student_fine_freeze,
                DecisionEngine._rule_no_issues_7_days,
                DecisionEngine._rule_low_season,
                DecisionEngine._rule_peak_afternoon,
                DecisionEngine._rule_dead_stock,
                DecisionEngine._rule_weekend_low,
                DecisionEngine._rule_repeat_fine_pending,
            ]

            for check in checks:
                try:
                    for decision in check(cursor, now, today_str):
                        if DecisionEngine._insert_if_new(cursor, decision):
                            new_decisions.append((decision["title"], decision["description"]))
                except sqlite3.Error:
                    continue

            conn.commit()
            return new_decisions
        except sqlite3.Error as e:
            print(f"Decision Engine Database Error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def _insert_if_new(cursor, decision: dict) -> bool:
        cursor.execute(
            "SELECT decision_id FROM decisions WHERE rule_key = ? AND status = 'Pending'",
            (decision["rule_key"],),
        )
        if cursor.fetchone():
            return False
        cursor.execute(
            """
            INSERT INTO decisions (rule_key, title, description, reason, priority, category, related_record_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision["rule_key"],
                decision["title"],
                decision["description"],
                decision.get("reason", ""),
                decision.get("priority", "Medium"),
                decision.get("category", "General"),
                decision.get("related_record_id", ""),
            ),
        )
        return True

    # ------------------------------------------------------------------
    # Individual rules — each returns a list of decision dicts (usually 0 or 1)
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_low_occupancy(cursor, now, today_str):
        one_hour_ago = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT COUNT(*) as c FROM attendance WHERE check_in_time >= ?", (one_hour_ago,))
        count = cursor.fetchone()["c"]
        if count <= 5:
            return [{
                "rule_key": f"low_occupancy_{now.strftime('%Y-%m-%d_%H')}",
                "title": "Library Occupancy Is Very Low",
                "description": f"Only {count} check-ins in the last hour.",
                "reason": "Turn OFF unnecessary lights, fans, and electrical equipment to save electricity.",
                "priority": "Medium",
                "category": "Occupancy",
            }]
        return []

    @staticmethod
    def _rule_high_occupancy(cursor, now, today_str):
        one_hour_ago = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT COUNT(*) as c FROM attendance WHERE check_in_time >= ?", (one_hour_ago,))
        count = cursor.fetchone()["c"]
        if count > 20:
            return [{
                "rule_key": f"high_occupancy_{now.strftime('%Y-%m-%d_%H')}",
                "title": "Library Occupancy Has Increased",
                "description": f"{count} check-ins in the last hour.",
                "reason": "Turn ON additional fans and lights for better comfort.",
                "priority": "Medium",
                "category": "Occupancy",
            }]
        return []

    @staticmethod
    def _rule_sustained_high_occupancy(cursor, now, today_str):
        thirty_min_ago = (now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE check_in_time <= ? AND check_out_time IS NULL",
            (thirty_min_ago,),
        )
        count = cursor.fetchone()["c"]
        if count > 100:
            return [{
                "rule_key": f"sustained_high_occupancy_{now.strftime('%Y-%m-%d_%H')}",
                "title": "Library Occupancy Is Very High",
                "description": f"{count} students have remained inside for 30+ minutes without checking out.",
                "reason": "Assign additional staff for monitoring and student assistance.",
                "priority": "High",
                "category": "Occupancy",
            }]
        return []

    @staticmethod
    def _rule_low_stock(cursor, now, today_str):
        cursor.execute("SELECT book_id, title, available_quantity FROM books WHERE available_quantity <= 2")
        decisions = []
        for book in cursor.fetchall():
            decisions.append({
                "rule_key": f"low_stock_book_{book['book_id']}",
                "title": "Book Stock Is Critically Low",
                "description": f"'{book['title']}' (Book ID #{book['book_id']}) has only {book['available_quantity']} copies left.",
                "reason": "Purchase additional copies.",
                "priority": "High",
                "category": "Inventory",
                "related_record_id": str(book["book_id"]),
            })
        return decisions

    @staticmethod
    def _rule_high_demand_book(cursor, now, today_str):
        last_24h = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "SELECT book_id, COUNT(*) as c FROM student_issues WHERE issue_date_time >= ? GROUP BY book_id HAVING c >= 10",
            (last_24h,),
        )
        decisions = []
        for row in cursor.fetchall():
            cursor.execute("SELECT title FROM books WHERE book_id = ?", (row["book_id"],))
            book = cursor.fetchone()
            title = book["title"] if book else f"Book #{row['book_id']}"
            decisions.append({
                "rule_key": f"high_demand_book_{row['book_id']}_{now.strftime('%Y-%m-%d')}",
                "title": "Exceptionally High Book Demand",
                "description": f"'{title}' was issued {row['c']} times in the last 24 hours.",
                "reason": "Increase the number of available copies.",
                "priority": "High",
                "category": "Inventory",
                "related_record_id": str(row["book_id"]),
            })
        return decisions

    @staticmethod
    def _rule_department_overdue(cursor, now, today_str):
        cursor.execute(
            """
            SELECT department, COUNT(*) as c FROM student_issues
            WHERE status = 'Issued' AND expected_return_date_time < ?
            GROUP BY department HAVING c >= 5
            """,
            (now.strftime("%Y-%m-%d %H:%M:%S"),),
        )
        decisions = []
        for row in cursor.fetchall():
            dept = row["department"] or "Unknown"
            decisions.append({
                "rule_key": f"dept_overdue_{dept}",
                "title": "Repeated Late Returns Detected",
                "description": f"{dept} has {row['c']} overdue book returns.",
                "reason": f"Temporarily restrict further book borrowing for {dept} until pending books are returned.",
                "priority": "High",
                "category": "Issue/Return",
                "related_record_id": dept,
            })
        return decisions

    @staticmethod
    def _rule_student_fine_freeze(cursor, now, today_str):
        cursor.execute(
            """
            SELECT student_id, SUM(fine_amount) as total_fine FROM book_returns
            WHERE status != 'Fine Paid'
            GROUP BY student_id HAVING total_fine >= 500
            """
        )
        decisions = []
        for row in cursor.fetchall():
            decisions.append({
                "rule_key": f"fine_freeze_{row['student_id']}",
                "title": "Borrowing Privileges Should Remain Frozen",
                "description": f"Student {row['student_id']} has an unpaid fine of Rs. {row['total_fine']:.2f}.",
                "reason": "Student must clear all pending fines before issuing another book.",
                "priority": "Critical",
                "category": "Fines",
                "related_record_id": row["student_id"],
            })
        return decisions

    @staticmethod
    def _rule_no_issues_7_days(cursor, now, today_str):
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT COUNT(*) as c FROM student_issues WHERE issue_date_time >= ?", (seven_days_ago,))
        count = cursor.fetchone()["c"]
        if count == 0:
            return [{
                "rule_key": f"no_issues_7days_{now.strftime('%Y-%m-%d')}",
                "title": "Library Usage Has Significantly Decreased",
                "description": "No books have been issued in the last 7 consecutive days.",
                "reason": "Investigate possible reasons and encourage students to use library resources.",
                "priority": "Medium",
                "category": "Usage",
            }]
        return []

    @staticmethod
    def _rule_low_season(cursor, now, today_str):
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute("SELECT date, COUNT(*) as c FROM attendance WHERE date >= ? GROUP BY date", (seven_days_ago,))
        rows = cursor.fetchall()
        if len(rows) < 7:
            return []
        avg = sum(r["c"] for r in rows) / len(rows)
        if 3 <= avg <= 5:
            return [{
                "rule_key": f"low_season_{now.strftime('%Y-%m-%d')}",
                "title": "Off-Season Low Attendance Pattern",
                "description": f"Daily visitors have averaged {avg:.1f} per day over the last 7 days.",
                "reason": "Consider reducing library operating hours during this low-traffic period.",
                "priority": "Medium",
                "category": "Usage",
            }]
        return []

    @staticmethod
    def _rule_peak_afternoon(cursor, now, today_str):
        cursor.execute(
            """
            SELECT COUNT(*) as c FROM attendance
            WHERE date = ? AND strftime('%H:%M', check_in_time) >= '15:00'
              AND strftime('%H:%M', check_in_time) <= '17:00'
            """,
            (today_str,),
        )
        count = cursor.fetchone()["c"]
        if count >= 25:
            return [{
                "rule_key": f"peak_afternoon_{today_str}",
                "title": "Peak Afternoon Demand Detected",
                "description": f"{count} students checked in between 3:00 PM and 5:00 PM today.",
                "reason": "Consider extending library operating hours to accommodate peak afternoon demand.",
                "priority": "Medium",
                "category": "Usage",
            }]
        return []

    @staticmethod
    def _rule_dead_stock(cursor, now, today_str):
        cutoff_60 = (now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            SELECT b.book_id, b.title FROM books b
            WHERE b.book_id NOT IN (SELECT book_id FROM student_issues WHERE issue_date_time >= ?)
            AND b.created_at <= ?
            """,
            (cutoff_60, cutoff_60),
        )
        decisions = []
        for book in cursor.fetchall():
            decisions.append({
                "rule_key": f"dead_stock_book_{book['book_id']}",
                "title": "Low-Demand Book Identified",
                "description": f"'{book['title']}' (Book ID #{book['book_id']}) has not been issued in over 60 days.",
                "reason": "Consider promoting this title or reviewing whether to keep it in circulation.",
                "priority": "Low",
                "category": "Inventory",
                "related_record_id": str(book["book_id"]),
            })
        return decisions

    @staticmethod
    def _rule_weekend_low(cursor, now, today_str):
        if now.weekday() not in (5, 6):
            return []
        cursor.execute("SELECT COUNT(*) as c FROM attendance WHERE date = ?", (today_str,))
        count = cursor.fetchone()["c"]
        if count <= 5:
            return [{
                "rule_key": f"weekend_low_{today_str}",
                "title": "Consistently Low Weekend Attendance",
                "description": f"Only {count} check-ins recorded today ({now.strftime('%A')}).",
                "reason": "Consider adjusting weekend operating hours.",
                "priority": "Low",
                "category": "Usage",
            }]
        return []

    @staticmethod
    def _rule_repeat_fine_pending(cursor, now, today_str):
        cursor.execute(
            "SELECT student_id, COUNT(*) as c FROM book_returns WHERE status = 'Fine Pending' GROUP BY student_id HAVING c >= 3"
        )
        decisions = []
        for row in cursor.fetchall():
            decisions.append({
                "rule_key": f"repeat_fine_pending_{row['student_id']}",
                "title": "Repeated Unpaid Fines",
                "description": f"Student {row['student_id']} has {row['c']} separate pending fine records.",
                "reason": "Issue a formal warning to this student regarding repeated unpaid fines.",
                "priority": "Medium",
                "category": "Fines",
                "related_record_id": row["student_id"],
            })
        return decisions

    # ------------------------------------------------------------------
    # Management API (used by the Decision Engine UI module)
    # ------------------------------------------------------------------

    @staticmethod
    def get_all_decisions(search_query: str = None, priority_filter: str = None, status_filter: str = None):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM decisions WHERE 1=1"
            params = []
            if search_query and search_query.strip():
                term = f"%{search_query.strip().lower()}%"
                query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)"
                params.extend([term, term, term])
            if priority_filter and priority_filter != "All":
                query += " AND priority = ?"
                params.append(priority_filter)
            if status_filter and status_filter != "All":
                query += " AND status = ?"
                params.append(status_filter)
            query += " ORDER BY generated_at DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Get Decisions Error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def get_pending_count():
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) as c FROM decisions WHERE status = 'Pending'")
            return cursor.fetchone()["c"]
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    @staticmethod
    def set_decision_status(decision_id: int, status: str, resolved_by: str):
        """status must be 'Approved' or 'Ignored'."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE decisions SET status = ?, resolved_at = ?, resolved_by = ? WHERE decision_id = ?",
                (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), resolved_by, decision_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Decision not found."}
            return {"success": True, "message": f"Decision marked as {status}."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def delete_decision(decision_id: int, role: str):
        if role != "admin":
            return {"success": False, "message": "Only Admin can delete decisions."}
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM decisions WHERE decision_id = ?", (decision_id,))
            conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Decision not found."}
            return {"success": True, "message": "Decision deleted successfully."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()
