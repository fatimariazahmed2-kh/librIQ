import sqlite3
from database.db_manager import db
from utils.word_exporter import WordExporter

class ReportManager:
    """Generates analytics reports and handles MS Word exports."""

    @staticmethod
    def generate_report(period: str = "Daily"):
        conn = db.get_connection()
        cursor = conn.cursor()

        period_sql = {
            "Daily": "date('now')",
            "Weekly": "date('now', '-7 days')",
            "Monthly": "date('now', '-1 month')",
            "Yearly": "date('now', '-1 year')",
        }.get(period, "date('now')")

        try:
            # 1. Total Check-Ins & Check-Outs
            cursor.execute(
                f"""
                SELECT 
                    COUNT(check_in_time) as total_checkins,
                    COUNT(check_out_time) as total_checkouts
                FROM attendance 
                WHERE date >= {period_sql}
                """
            )
            att_data = cursor.fetchone()

            # 2. Total Books Issued (Department-wise)
            cursor.execute(
                f"""
                SELECT department, COUNT(*) as count 
                FROM student_issues 
                WHERE DATE(issue_date_time) >= {period_sql} 
                GROUP BY department
                """
            )
            dept_issues = [dict(r) for r in cursor.fetchall()]

            # 3. Most Issued Books
            cursor.execute(
                f"""
                SELECT b.title, COUNT(i.issue_id) as issue_count 
                FROM student_issues i 
                JOIN books b ON i.book_id = b.book_id 
                WHERE DATE(i.issue_date_time) >= {period_sql} 
                GROUP BY b.book_id 
                ORDER BY issue_count DESC LIMIT 5
                """
            )
            most_issued = [dict(r) for r in cursor.fetchall()]

            # 4. Students Who Did Not Return Books
            cursor.execute(
                """
                SELECT student_name, student_id, department, expected_return_date_time 
                FROM student_issues 
                WHERE status = 'Issued' AND expected_return_date_time < datetime('now')
                """
            )
            unreturned = [dict(r) for r in cursor.fetchall()]

            # 5. Estimated Fine
            total_fine = sum(100 for _ in unreturned)

            report_data = {
                "period": period,
                "total_checkins": att_data["total_checkins"] if att_data else 0,
                "total_checkouts": att_data["total_checkouts"] if att_data else 0,
                "department_issues": dept_issues,
                "most_issued_books": most_issued,
                "unreturned_students": unreturned,
                "estimated_fine_collection": total_fine,
            }
            return report_data
        except sqlite3.Error as e:
            print(f"Report Generation Error: {e}")
            return {}
        finally:
            conn.close()

    @staticmethod
    def export_to_word(period: str = "Daily", generated_by: str = "System"):
        """Generates report and exports to MS Word document."""
        report_data = ReportManager.generate_report(period)
        if not report_data:
            return {"success": False, "message": "Failed to generate report data for export."}
        report_data["generated_by"] = generated_by
        return WordExporter.export_report_to_word(report_data)