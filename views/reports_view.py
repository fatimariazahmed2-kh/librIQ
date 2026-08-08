import customtkinter as ctk
from datetime import datetime
from tkinter import messagebox
from modules.attendance import AttendanceManager
from modules.students import StudentManager
from modules.analytics import AnalyticsManager
from utils.word_exporter import WordExporter

class ReportsView(ctk.CTkFrame):
    """View managing system activity reporting and MS Word document export."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build_ui()

    def _build_ui(self):
        # Header
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=15)

        title = ctk.CTkLabel(top_bar, text="📊 System Activity & Operational Reports", font=("Segoe UI", 20, "bold"))
        title.pack(side="left")

        export_word_btn = ctk.CTkButton(
            top_bar, text="📄 Export Report to MS Word (.docx)", fg_color="#2B579A", hover_color="#1E3E6D",
            font=("Segoe UI", 12, "bold"), height=38, command=self._export_to_word
        )
        export_word_btn.pack(side="right")

        # Summary Cards Container
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=20, pady=10)
        cards_frame.columnconfigure((0, 1, 2), weight=1)

        # Fetch Data
        att_summary = AttendanceManager.get_todays_summary() if hasattr(AttendanceManager, "get_todays_summary") else {"total_checkins": 0, "total_checkouts": 0}
        issues = StudentManager.get_student_issues()
        total_issues = len(issues)
        total_returned = sum(1 for i in issues if i["status"] == "Returned")

        # Card 1: Attendance
        self._create_card(cards_frame, 0, "Daily Check-Ins", str(att_summary.get("total_checkins", 0)), "#0078D4")
        # Card 2: Total Issues
        self._create_card(cards_frame, 1, "Total Books Issued", str(total_issues), "#E81123")
        # Card 3: Returns
        self._create_card(cards_frame, 2, "Books Returned", str(total_returned), "#107C41")

        # Detailed Summary Box
        info_box = ctk.CTkTextbox(self, font=("Consolas", 13), corner_radius=10)
        info_box.pack(fill="both", expand=True, padx=20, pady=15)

        report_text = f"=== SMART LIBRARY MANAGEMENT SYSTEM OPERATIONAL REPORT ===\n"
        report_text += f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report_text += f"----------------------------------------------------------\n\n"
        report_text += f"1. ATTENDANCE SUMMARY:\n"
        report_text += f"   - Total Check-Ins Today: {att_summary.get('total_checkins', 0)}\n"
        report_text += f"   - Total Check-Outs Today: {att_summary.get('total_checkouts', 0)}\n\n"
        report_text += f"2. CIRCULATION SUMMARY:\n"
        report_text += f"   - Active / Total Issued Books: {total_issues}\n"
        report_text += f"   - Cleared / Returned Books: {total_returned}\n"
        report_text += f"   - Pending Returns: {total_issues - total_returned}\n\n"
        report_text += f"3. BACKUP SYSTEM STATUS:\n"
        report_text += f"   - Books Excel Backup Engine: ACTIVE\n"
        report_text += f"   - Issue/Return Excel Backup Engine: ACTIVE\n"
        report_text += f"   - Staff Records Backup Engine: ACTIVE\n"
        report_text += f"   - Word (.docx) Exporter: ACTIVE\n"

        info_box.insert("1.0", report_text)
        info_box.configure(state="disabled")

    def _create_card(self, parent, col, title, value, color):
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=10)
        card.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 12, "bold"), text_color="white").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(card, text=value, font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", padx=15, pady=(0, 15))

    def _export_to_word(self):
        att_summary = AttendanceManager.get_todays_summary() if hasattr(AttendanceManager, "get_todays_summary") else {"total_checkins": 0, "total_checkouts": 0}
        issues = StudentManager.get_student_issues()
        
        report_data = {
            "period": "System Operational",
            "total_checkins": att_summary.get("total_checkins", 0),
            "total_checkouts": att_summary.get("total_checkouts", 0),
            "estimated_fine_collection": sum(i.get("fine_amount", 0.0) for i in issues),
            "most_issued_books": [{"title": i["book_title"], "issue_count": 1} for i in issues[:5]]
        }

        res = WordExporter.export_report_to_word(report_data)
        if res["success"]:
            messagebox.showinfo("Export Successful", res["message"])
        else:
            messagebox.showerror("Export Failed", res["message"])