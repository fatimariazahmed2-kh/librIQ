import sqlite3
from database.db_manager import db

class NotificationManager:
    """Manages system notification history, alerts, and deletion."""

    @staticmethod
    def add_notification(category: str, message: str):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO notifications (category, message) VALUES (?, ?)",
                (category, message),
            )
            conn.commit()
            return {"success": True}
        except sqlite3.Error as e:
            return {"success": False, "message": str(e)}
        finally:
            conn.close()

    @staticmethod
    def get_all_notifications():
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM notifications ORDER BY notification_id DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            print(f"Fetch Notifications Error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def delete_notification(notification_id: int):
        """Deletes a specific notification record by ID."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM notifications WHERE notification_id = ?", (notification_id,))
            conn.commit()
            return {"success": True, "message": "Notification deleted successfully!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()