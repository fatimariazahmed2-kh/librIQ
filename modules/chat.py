import os
import shutil
import uuid
import sqlite3
from datetime import datetime
from database.db_manager import db

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATTACHMENTS_DIR = os.path.join(ROOT_DIR, "data", "chat_attachments")


class ChatManager:
    """Internal WhatsApp-style chat between Admin, Librarian, and Staff.

    Permission rules:
      - Admin can message everyone.
      - Librarian can message Admin and Staff.
      - Staff can message Admin and Librarian.

    Display names always come live from the users table (the name they use
    to log in), never a stored snapshot, so a later name change is reflected
    automatically in old messages too.
    """

    # ------------------------------------------------------------------
    # Permissions / contact directory
    # ------------------------------------------------------------------

    @staticmethod
    def _can_message(role_a: str, role_b: str) -> bool:
        role_a = (role_a or "").strip().lower()
        role_b = (role_b or "").strip().lower()
        if role_a == role_b:
            return False  # no same-role peer chat per the defined rules (e.g. staff-to-staff)
        if "admin" in (role_a, role_b):
            return True
        # remaining combination is librarian <-> staff
        return {role_a, role_b} == {"librarian", "staff"}

    @staticmethod
    def get_contacts(current_username: str, current_role: str):
        """Returns everyone the current user is allowed to message, each with
        their last message preview, last message time, and unread count."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT username, name, role FROM users WHERE username != ? AND is_authorized = 1",
                (current_username,),
            )
            all_users = [dict(r) for r in cursor.fetchall()]
            contacts = [u for u in all_users if ChatManager._can_message(current_role, u["role"])]

            for c in contacts:
                cursor.execute(
                    """
                    SELECT message, attachment_type, sent_at FROM chat_messages
                    WHERE ((sender_username = ? AND receiver_username = ? AND deleted_by_sender = 0)
                        OR (sender_username = ? AND receiver_username = ? AND deleted_by_receiver = 0))
                    ORDER BY sent_at DESC LIMIT 1
                    """,
                    (current_username, c["username"], c["username"], current_username),
                )
                last = cursor.fetchone()
                if last:
                    preview = last["message"] if last["message"] else f"📎 {last['attachment_type'] or 'Attachment'}"
                    c["last_message"] = preview
                    c["last_message_time"] = last["sent_at"]
                else:
                    c["last_message"] = ""
                    c["last_message_time"] = ""

                cursor.execute(
                    """
                    SELECT COUNT(*) as c FROM chat_messages
                    WHERE sender_username = ? AND receiver_username = ? AND is_read = 0 AND deleted_by_receiver = 0
                    """,
                    (c["username"], current_username),
                )
                c["unread_count"] = cursor.fetchone()["c"]

            contacts.sort(key=lambda x: x["last_message_time"], reverse=True)
            return contacts
        except sqlite3.Error as e:
            print(f"Get Contacts Error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def get_total_unread(username: str) -> int:
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) as c FROM chat_messages WHERE receiver_username = ? AND is_read = 0 AND deleted_by_receiver = 0",
                (username,),
            )
            return cursor.fetchone()["c"]
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    @staticmethod
    def get_conversation(user_a: str, user_b: str, viewer_username: str):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT cm.*, u.name as sender_name, u.role as sender_role
                FROM chat_messages cm
                JOIN users u ON cm.sender_username = u.username
                WHERE ((sender_username = ? AND receiver_username = ?)
                    OR (sender_username = ? AND receiver_username = ?))
                ORDER BY cm.sent_at ASC, cm.message_id ASC
                """,
                (user_a, user_b, user_b, user_a),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            visible = []
            for r in rows:
                if r["sender_username"] == viewer_username and r["deleted_by_sender"] == 1:
                    continue
                if r["receiver_username"] == viewer_username and r["deleted_by_receiver"] == 1:
                    continue
                visible.append(r)
            return visible
        except sqlite3.Error as e:
            print(f"Get Conversation Error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def mark_conversation_read(receiver_username: str, sender_username: str):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE chat_messages SET is_read = 1 WHERE sender_username = ? AND receiver_username = ? AND is_read = 0",
                (sender_username, receiver_username),
            )
            conn.commit()
        except sqlite3.Error:
            pass
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Send / Edit / Delete
    # ------------------------------------------------------------------

    @staticmethod
    def send_message(sender_username: str, sender_role: str, receiver_username: str, receiver_role: str,
                      message: str = "", attachment_source_path: str = None):
        message = (message or "").strip()
        if not message and not attachment_source_path:
            return {"success": False, "message": "Cannot send an empty message."}

        if not ChatManager._can_message(sender_role, receiver_role):
            return {"success": False, "message": "You are not permitted to message this user."}

        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT username FROM users WHERE username = ?", (receiver_username,))
            if not cursor.fetchone():
                return {"success": False, "message": "Invalid receiver."}

            attachment_path = None
            attachment_type = None
            if attachment_source_path and os.path.isfile(attachment_source_path):
                os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
                ext = os.path.splitext(attachment_source_path)[1].lower()
                unique_name = f"{uuid.uuid4().hex}{ext}"
                dest_path = os.path.join(ATTACHMENTS_DIR, unique_name)
                shutil.copyfile(attachment_source_path, dest_path)
                attachment_path = dest_path
                attachment_type = "image" if ext in IMAGE_EXTENSIONS else "file"

            cursor.execute(
                """
                INSERT INTO chat_messages (sender_username, receiver_username, message, attachment_path, attachment_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sender_username, receiver_username, message, attachment_path, attachment_type),
            )
            conn.commit()
            return {"success": True, "message": "Message sent."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def edit_message(message_id: int, editor_username: str, new_text: str):
        new_text = (new_text or "").strip()
        if not new_text:
            return {"success": False, "message": "Message cannot be empty."}

        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT sender_username FROM chat_messages WHERE message_id = ?", (message_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "Message not found."}
            if row["sender_username"] != editor_username:
                return {"success": False, "message": "You can only edit your own messages."}

            cursor.execute(
                "UPDATE chat_messages SET message = ?, edited = 1 WHERE message_id = ?",
                (new_text, message_id),
            )
            conn.commit()
            return {"success": True, "message": "Message updated."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def delete_message_for_me(message_id: int, username: str):
        """Deletes only from the requesting user's own view — WhatsApp 'Delete for me'."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT sender_username, receiver_username FROM chat_messages WHERE message_id = ?", (message_id,)
            )
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "Message not found."}

            if row["sender_username"] == username:
                cursor.execute("UPDATE chat_messages SET deleted_by_sender = 1 WHERE message_id = ?", (message_id,))
            elif row["receiver_username"] == username:
                cursor.execute("UPDATE chat_messages SET deleted_by_receiver = 1 WHERE message_id = ?", (message_id,))
            else:
                return {"success": False, "message": "You are not part of this conversation."}

            conn.commit()
            return {"success": True, "message": "Message deleted."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()
