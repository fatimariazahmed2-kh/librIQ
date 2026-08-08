import os
from datetime import datetime
import sqlite3
from database.db_manager import db
from utils.excel_exporter import ExcelExporter


class BookManager:
    """Backend logic for managing library book inventory and search operations."""

    @staticmethod
    def add_or_update_book(title: str, isbn: str, category: str, author_name: str, quantity: int = 1):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            title = (title or "").strip()
            isbn = (isbn or "").strip()
            category = (category or "").strip()
            author_name = (author_name or "").strip()
            quantity = int(quantity or 1)

            if not title or not author_name:
                return {"success": False, "message": "Title and author name are required."}
            if quantity <= 0:
                return {"success": False, "message": "Quantity must be greater than zero."}

            cursor.execute(
                """
                SELECT book_id, total_quantity, available_quantity
                FROM books
                WHERE LOWER(title) = LOWER(?)
                AND LOWER(isbn) = LOWER(?)
                AND LOWER(category) = LOWER(?)
                AND LOWER(author_name) = LOWER(?)
                """,
                (title, isbn, category, author_name),
            )
            existing = cursor.fetchone()
            if existing:
                book_id = existing["book_id"]
                new_total = existing["total_quantity"] + quantity
                new_available = existing["available_quantity"] + quantity
                cursor.execute(
                    "UPDATE books SET total_quantity = ?, available_quantity = ? WHERE book_id = ?",
                    (new_total, new_available, book_id),
                )
                conn.commit()
                BookManager._export_backup()
                return {"success": True, "message": f"Existing book record updated (+{quantity} quantity)."}

            cursor.execute(
                """
                INSERT INTO books (title, isbn, category, author_name, total_quantity, available_quantity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, isbn, category, author_name, quantity, quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            BookManager._export_backup()
            return {"success": True, "message": "New book record added successfully!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def update_book(book_id: int, title: str, isbn: str, category: str, author_name: str, quantity: int):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            if not book_id or int(book_id) <= 0:
                return {"success": False, "message": "Invalid book ID."}

            title = (title or "").strip()
            isbn = (isbn or "").strip()
            category = (category or "").strip()
            author_name = (author_name or "").strip()
            quantity = int(quantity or 1)

            if not title or not author_name:
                return {"success": False, "message": "Title and author name are required."}
            if quantity <= 0:
                return {"success": False, "message": "Quantity must be greater than zero."}

            cursor.execute(
                "SELECT total_quantity, available_quantity FROM books WHERE book_id = ?",
                (book_id,),
            )
            existing = cursor.fetchone()
            if not existing:
                return {"success": False, "message": "Book record not found."}

            current_total = existing["total_quantity"]
            current_available = existing["available_quantity"]
            delta = quantity - current_total
            new_available = max(0, min(current_available + delta, quantity))

            cursor.execute(
                """
                UPDATE books
                SET title = ?, isbn = ?, category = ?, author_name = ?, total_quantity = ?, available_quantity = ?
                WHERE book_id = ?
                """,
                (title, isbn, category, author_name, quantity, new_available, book_id),
            )
            conn.commit()
            BookManager._export_backup()
            return {"success": True, "message": "Book record updated successfully!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def get_all_books(search_query: str = None, category_filter: str = None):
        """Retrieves all books and dynamically filters when search or category filters are supplied."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            order_clause = "ORDER BY book_id ASC"
            query = "SELECT * FROM books"
            conditions = []
            params = []

            if search_query and search_query.strip():
                term = f"%{search_query.strip().lower()}%"
                conditions.append(
                    "(CAST(book_id AS TEXT) LIKE ? OR LOWER(title) LIKE ? OR LOWER(isbn) LIKE ? OR LOWER(category) LIKE ? OR LOWER(author_name) LIKE ?)"
                )
                params.extend([term, term, term, term, term])

            if category_filter and category_filter.strip():
                conditions.append("LOWER(category) = LOWER(?)")
                params.append(category_filter.strip())

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += f" {order_clause}"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"Error fetching books: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def delete_book(book_id: int):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM student_issues WHERE book_id = ? AND status = 'Issued' LIMIT 1",
                (book_id,),
            )
            if cursor.fetchone():
                return {"success": False, "message": "This book cannot be deleted because it is currently issued to a student."}

            cursor.execute("DELETE FROM books WHERE book_id = ?", (book_id,))
            conn.commit()
            BookManager._export_backup()
            return {"success": True, "message": "Book record deleted successfully."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database Error: {str(e)}"}
        finally:
            conn.close()

    @staticmethod
    def _export_backup():
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_path = os.path.join(root_dir, "data", "books_backup.xlsx")
        books = BookManager.get_all_books()
        columns = ["Book ID", "Title", "ISBN", "Category", "Author Name", "Total Qty", "Available Qty", "Date Added"]
        rows = [
            [
                b["book_id"],
                b["title"],
                b["isbn"],
                b["category"],
                b["author_name"],
                b["total_quantity"],
                b["available_quantity"],
                b["created_at"],
            ]
            for b in books
        ]
        result = ExcelExporter.export_table_to_excel(columns, rows, backup_path, backup_path)
        if not result.get("success"):
            print(f"[Books Auto-Backup Warning] {result.get('message')}")
        return result

    @staticmethod
    def export_to_excel():
        """Exports all book records to an Excel file."""
        books = BookManager.get_all_books()
        if not books:
            return {"success": False, "message": "No book records to export."}
        columns = ["Book ID", "Title", "ISBN", "Category", "Author Name", "Total Qty", "Available Qty", "Date Added"]
        rows = [
            [
                b["book_id"],
                b["title"],
                b["isbn"],
                b["category"],
                b["author_name"],
                b["total_quantity"],
                b["available_quantity"],
                b["created_at"],
            ]
            for b in books
        ]
        return ExcelExporter.export_table_to_excel(columns, rows, "books_backup.xlsx")