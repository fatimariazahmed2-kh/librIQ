import os
import subprocess
import sys
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

# Matplotlib integration for Enterprise Analytics Charts
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from config import (
    COLOR_BLUE,
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_PINK,
    COLOR_PRIMARY_SEA_GREEN,
    COLOR_SEA_GREEN_HOVER,
    COLOR_SIDEBAR_BG,
    COLOR_SILVER_BG,
    COLOR_TEXT_DARK,
    COLOR_TEXT_LIGHT,
    COLOR_TEXT_MUTED,
    FONT_BODY,
    FONT_HEADER,
    FONT_SMALL,
    FONT_SUBHEADER,
)

from modules.analytics import AnalyticsManager
from modules.attendance import AttendanceManager
from modules.auth import AuthManager
from modules.books import BookManager
from modules.chat import ChatManager
from modules.notifications import NotificationManager
from modules.reports import ReportManager
from modules.settings import SettingsManager
from modules.staff import StaffManager
from modules.students import StudentManager

from utils.decision_engine import DecisionEngine

from views.components import CustomDialog, HeaderBar, ModernTable, StatCard

# Shared button style used across every module's action bar (Books, Issue/Return,
# Attendance, Staff) so sizing, height, corner radius, and font stay consistent.
ACTION_BUTTON_STYLE = {
    "width": 110,
    "height": 38,
    "corner_radius": 12,
    "font": (FONT_BODY[0], 11),
}
ACTION_BUTTON_GAP = (0, 10)


class DashboardView(ctk.CTkFrame):

  def __init__(self, parent, user: dict, on_logout):
    super().__init__(parent, fg_color=COLOR_SILVER_BG)
    self.user = user
    self.role = user.get("role", "staff").lower()
    self.on_logout = on_logout

    # Fetch module permissions for current logged-in role
    self.permissions = SettingsManager.get_role_permissions(self.role)

    # Layout Configuration: Sidebar (Left), Content Area (Right)
    self.grid_columnconfigure(0, weight=0, minsize=220)
    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(0, weight=1)

    self._setup_sidebar()
    self._setup_main_container()

    # Run decision engine on startup to check trends & trigger notifications
    DecisionEngine.run_analysis()

    # Load default active screen (Dashboard Home)
    self._switch_tab("Dashboard")

  def _build_scrollable_dialog(self, title: str, width: int = 440, height: int = 560):
    """Creates a CTkToplevel with a scrollable content area and a footer that
    always stays visible (for the Save/Submit button), regardless of screen
    size or how many fields the form has. Returns (window, scroll_frame, footer_frame).
    """
    win = ctk.CTkToplevel(self)
    win.title(title)

    # Never make the popup taller than what actually fits on the user's screen.
    screen_h = win.winfo_screenheight()
    max_h = int(screen_h * 0.85)
    height = min(height, max_h)
    win.geometry(f"{width}x{height}")
    win.grab_set()

    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)

    scroll_frame = ctk.CTkScrollableFrame(win, fg_color="transparent")
    scroll_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

    footer_frame = ctk.CTkFrame(win, fg_color="transparent")
    footer_frame.grid(row=1, column=0, sticky="ew")

    return win, scroll_frame, footer_frame

  def _setup_sidebar(self):
    """Creates the dark-slate enterprise sidebar navigation with role-based visibility."""
    self.sidebar = ctk.CTkFrame(
        self, fg_color=COLOR_SIDEBAR_BG, corner_radius=0
    )
    self.sidebar.grid(row=0, column=0, sticky="nsew")

    # App Branding Header in Sidebar
    brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
    brand_frame.pack(fill="x", padx=15, pady=20)

    lbl_logo = ctk.CTkLabel(
        brand_frame,
        text="📚 Smart Library",
        font=FONT_HEADER,
        text_color=COLOR_TEXT_LIGHT,
    )
    lbl_logo.pack(anchor="w")

    lbl_role = ctk.CTkLabel(
        brand_frame,
        text=f"Role: {self.role.upper()}",
        font=FONT_SMALL,
        text_color=COLOR_PRIMARY_SEA_GREEN,
    )
    lbl_role.pack(anchor="w")

    ctk.CTkFrame(self.sidebar, height=1, fg_color="#334155").pack(
        fill="x", padx=10, pady=(0, 15)
    )

    # Logout Button at bottom (packed first so remaining space goes to nav scroll area)
    logout_btn = ctk.CTkButton(
        self.sidebar,
        text="  🚪  Logout",
        anchor="w",
        font=(FONT_BODY[0], 12, "bold"),
        fg_color="#EF4444",
        hover_color="#DC2626",
        text_color="white",
        height=40,
        corner_radius=8,
        command=self._confirm_logout,
    )
    logout_btn.pack(side="bottom", fill="x", padx=10, pady=20)

    # Scrollable nav area so all modules stay reachable even on shorter screens
    nav_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
    nav_scroll.pack(fill="both", expand=True, padx=0, pady=0)

    # Navigation Buttons Mapping
    self.nav_buttons = {}
    modules_list = [
        ("Dashboard", "🏠"),
        ("Decision Engine", "🧠"),
        ("Books", "📖"),
        ("Issue/Return", "🔄"),
        ("Attendance", "🕒"),
        ("Staff", "👥"),
        ("Analytics", "📈"),
        ("Reports", "📄"),
        ("Chat", "💬"),
        ("Settings", "⚙️"),
    ]

    for mod_name, icon in modules_list:
      # Check if role has visibility permission
      if self.permissions.get(mod_name, 1) == 1:
        label_text = f"  {icon}  {mod_name}"
        if mod_name == "Decision Engine":
          pending = DecisionEngine.get_pending_count()
          if pending > 0:
            label_text = f"  {icon}  {mod_name} ({pending})"
        elif mod_name == "Chat":
          unread = ChatManager.get_total_unread(self.user.get("username", ""))
          if unread > 0:
            label_text = f"  {icon}  {mod_name} ({unread})"
        btn = ctk.CTkButton(
            nav_scroll,
            text=label_text,
            anchor="w",
            font=(FONT_BODY[0], 12, "bold"),
            fg_color="transparent",
            hover_color="#334155",
            text_color="#94A3B8",
            height=42,
            corner_radius=8,
            command=lambda m=mod_name: self._switch_tab(m),
        )
        btn.pack(fill="x", padx=10, pady=3)
        self.nav_buttons[mod_name] = btn

  def _update_decision_badge(self):
    btn = self.nav_buttons.get("Decision Engine")
    if btn:
      pending = DecisionEngine.get_pending_count()
      label_text = "  🧠  Decision Engine" + (f" ({pending})" if pending > 0 else "")
      btn.configure(text=label_text)

    chat_btn = self.nav_buttons.get("Chat")
    if chat_btn:
      unread = ChatManager.get_total_unread(self.user.get("username", ""))
      label_text = "  💬  Chat" + (f" ({unread})" if unread > 0 else "")
      chat_btn.configure(text=label_text)

  def _setup_main_container(self):
    """Creates the right side main content frame."""
    self.main_container = ctk.CTkFrame(self, fg_color=COLOR_SILVER_BG)
    self.main_container.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
    self.main_container.grid_rowconfigure(1, weight=1)
    self.main_container.grid_columnconfigure(0, weight=1)

  def _refresh_current_module(self):
    """Rebuilds the active module and refreshes dashboard/analytics data after record changes."""
    DecisionEngine.run_analysis()
    active_tab = getattr(self, "current_tab", None) or "Dashboard"
    self._switch_tab("Dashboard")
    self._switch_tab(active_tab)

  def _switch_tab(self, tab_name: str):
    """Switches active module screen with menu highlights."""
    self.current_tab = tab_name
    self._update_decision_badge()
    # Reset button styles
    for name, btn in self.nav_buttons.items():
      if name == tab_name:
        btn.configure(
            fg_color=COLOR_PRIMARY_SEA_GREEN, text_color=COLOR_TEXT_LIGHT
        )
      else:
        btn.configure(fg_color="transparent", text_color="#94A3B8")

    # Clear container
    for child in self.main_container.winfo_children():
      child.destroy()

    # Header Bar
    header = HeaderBar(
        self.main_container,
        title=f"{tab_name} Module",
        subtitle=f"Smart Data-Driven Management / {tab_name}",
        current_user=self.user,
    )
    header.grid(row=0, column=0, sticky="ew", pady=(0, 15))

    # Content View Frame
    content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
    content_frame.grid(row=1, column=0, sticky="nsew")

    # Dispatch to Module Loader
    if tab_name == "Dashboard":
      self._render_dashboard_home(content_frame)
    elif tab_name == "Decision Engine":
      self._render_decision_engine_module(content_frame)
    elif tab_name == "Books":
      self._render_books_module(content_frame)
    elif tab_name == "Issue/Return":
      self._render_issue_return_module(content_frame)
    elif tab_name == "Attendance":
      self._render_attendance_module(content_frame)
    elif tab_name == "Staff":
      self._render_staff_module(content_frame)
    elif tab_name == "Analytics":
      self._render_analytics_module(content_frame)
    elif tab_name == "Reports":
      self._render_reports_module(content_frame)
    elif tab_name == "Chat":
      self._render_chat_module(content_frame)
    elif tab_name == "Settings":
      self._render_settings_module(content_frame)

  # --------------------------------------------------------------------------
  # 1. DASHBOARD HOME
  # --------------------------------------------------------------------------
  def _render_dashboard_home(self, parent):
    parent.grid_columnconfigure((0, 1, 2, 3), weight=1)
    parent.grid_rowconfigure(2, weight=1)

    # Calculate live stats
    books = BookManager.get_all_books()
    total_books = sum(b["total_quantity"] for b in books)
    available_books = sum(b["available_quantity"] for b in books)
    issued_books = total_books - available_books
    low_stock_books = [b for b in books if b["available_quantity"] <= 2]

    attendance_logs = AttendanceManager.get_all_attendance()
    peak_data = AnalyticsManager.get_peak_checkin_trend()
    pending_decisions = DecisionEngine.get_pending_count()
    unread_chats = ChatManager.get_total_unread(self.user.get("username", ""))

    issues = StudentManager.get_student_issues()
    overdue_issues = [i for i in issues if i.get("status") == "Overdue"]

    # Row 1: Primary KPI Cards
    StatCard(
        parent, title="TOTAL BOOKS", value=str(total_books),
        subtext="Available: " + str(available_books), icon="📚", accent_color=COLOR_PRIMARY_SEA_GREEN,
    ).grid(row=0, column=0, padx=5, pady=5, sticky="ew")

    StatCard(
        parent, title="ISSUED BOOKS", value=str(issued_books),
        subtext="Active Circulation", icon="📖", accent_color=COLOR_BLUE,
    ).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    StatCard(
        parent, title="TODAY VISITORS", value=str(len(attendance_logs)),
        subtext="Check-In Activity", icon="🕒", accent_color=COLOR_PINK,
    ).grid(row=0, column=2, padx=5, pady=5, sticky="ew")

    StatCard(
        parent, title="PEAK TIME", value=peak_data["peak_time"],
        subtext=f"{peak_data['total_students']} Students", icon="⚡", accent_color="#8B5CF6",
    ).grid(row=0, column=3, padx=5, pady=5, sticky="ew")

    # Row 2: Secondary KPI Cards
    StatCard(
        parent, title="OVERDUE BOOKS", value=str(len(overdue_issues)),
        subtext="Not Yet Returned", icon="⏰", accent_color="#F59E0B",
    ).grid(row=1, column=0, padx=5, pady=5, sticky="ew")

    StatCard(
        parent, title="LOW STOCK BOOKS", value=str(len(low_stock_books)),
        subtext="2 or Fewer Copies", icon="📉", accent_color=COLOR_PINK,
    ).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    StatCard(
        parent, title="PENDING DECISIONS", value=str(pending_decisions),
        subtext="Needs Approve/Ignore", icon="🧠", accent_color="#8B5CF6",
    ).grid(row=1, column=2, padx=5, pady=5, sticky="ew")

    StatCard(
        parent, title="UNREAD MESSAGES", value=str(unread_chats),
        subtext="In Chat", icon="💬", accent_color=COLOR_BLUE,
    ).grid(row=1, column=3, padx=5, pady=5, sticky="ew")

    # Row 3: Two clean text-based panels — no charts/graphs (Analytics owns those)
    bottom_frame = ctk.CTkFrame(parent, fg_color="transparent")
    bottom_frame.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=(15, 0))
    bottom_frame.grid_columnconfigure((0, 1), weight=1)
    bottom_frame.grid_rowconfigure(0, weight=1)

    # Left panel: Quick Overview (needs-attention list)
    overview_card = ctk.CTkFrame(
        bottom_frame, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_BORDER,
    )
    overview_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    ctk.CTkLabel(
        overview_card, text="  ⚠️ Needs Attention", font=FONT_SUBHEADER, text_color=COLOR_TEXT_DARK,
    ).pack(anchor="w", padx=15, pady=10)

    overview_scroll = ctk.CTkScrollableFrame(overview_card, fg_color="transparent")
    overview_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    attention_items = []
    for b in low_stock_books[:5]:
      attention_items.append(("📉", f"'{b['title']}' has only {b['available_quantity']} copies left"))
    for i in overdue_issues[:5]:
      attention_items.append(("⏰", f"{i['student_name']} ({i['student_id']}) — '{i['book_title']}' is overdue"))

    if attention_items:
      for icon, text in attention_items:
        row = ctk.CTkFrame(overview_scroll, fg_color=COLOR_SILVER_BG, corner_radius=8)
        row.pack(fill="x", pady=4, padx=2)
        ctk.CTkLabel(
            row, text=f"{icon}  {text}", font=FONT_SMALL, text_color=COLOR_TEXT_DARK,
            wraplength=320, justify="left", anchor="w",
        ).pack(anchor="w", padx=10, pady=8)
    else:
      ctk.CTkLabel(
          overview_scroll, text="Nothing needs attention right now.", font=FONT_BODY, text_color=COLOR_TEXT_MUTED,
      ).pack(pady=20)

    # Right panel: Recent Activity (latest attendance check-ins)
    activity_card = ctk.CTkFrame(
        bottom_frame, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_BORDER,
    )
    activity_card.grid(row=0, column=1, sticky="nsew")

    ctk.CTkLabel(
        activity_card, text="  🕒 Recent Activity", font=FONT_SUBHEADER, text_color=COLOR_TEXT_DARK,
    ).pack(anchor="w", padx=15, pady=10)

    activity_scroll = ctk.CTkScrollableFrame(activity_card, fg_color="transparent")
    activity_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    recent_logs = sorted(attendance_logs, key=lambda l: l["check_in_time"] or "", reverse=True)[:8]
    if recent_logs:
      for log in recent_logs:
        row = ctk.CTkFrame(activity_scroll, fg_color=COLOR_SILVER_BG, corner_radius=8)
        row.pack(fill="x", pady=4, padx=2)
        status_text = "checked out" if log.get("check_out_time") else "checked in"
        ctk.CTkLabel(
            row, text=f"👤 {log['student_full_name']} {status_text} — {log['check_in_time']}",
            font=FONT_SMALL, text_color=COLOR_TEXT_DARK, wraplength=320, justify="left", anchor="w",
        ).pack(anchor="w", padx=10, pady=8)
    else:
      ctk.CTkLabel(
          activity_scroll, text="No recent activity yet.", font=FONT_BODY, text_color=COLOR_TEXT_MUTED,
      ).pack(pady=20)

  # --------------------------------------------------------------------------
  # DECISION ENGINE MODULE
  # --------------------------------------------------------------------------
  def _render_decision_engine_module(self, parent):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    ctrl_frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctrl_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ctrl_frame.grid_columnconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    left_panel.grid(row=0, column=0, sticky="w")

    right_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    right_panel.grid(row=0, column=1, sticky="e")

    self.decision_search_entry = ctk.CTkEntry(
        left_panel, placeholder_text="Search decisions...", width=220, height=38
    )
    self.decision_search_entry.pack(side="left", padx=(0, 10))
    self.decision_search_entry.bind("<KeyRelease>", lambda event: self._load_decision_list())

    self.decision_priority_var = ctk.StringVar(value="All")
    ctk.CTkComboBox(
        left_panel, variable=self.decision_priority_var, values=["All", "Low", "Medium", "High", "Critical"],
        width=120, height=38, command=lambda v: self._load_decision_list(),
    ).pack(side="left", padx=(0, 10))

    self.decision_status_var = ctk.StringVar(value="Pending")
    ctk.CTkComboBox(
        left_panel, variable=self.decision_status_var, values=["All", "Pending", "Approved", "Ignored"],
        width=130, height=38, command=lambda v: self._load_decision_list(),
    ).pack(side="left")

    ctk.CTkButton(
        right_panel, text="🔄 Refresh Now", fg_color=COLOR_PRIMARY_SEA_GREEN, command=self._run_decision_engine_now, **ACTION_BUTTON_STYLE
    ).pack(side="left")

    self.decision_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    self.decision_scroll.grid(row=1, column=0, sticky="nsew")

    self._load_decision_list()

  def _run_decision_engine_now(self):
    DecisionEngine.run_analysis()
    self._update_decision_badge()
    self._load_decision_list()

  def _load_decision_list(self):
    for child in self.decision_scroll.winfo_children():
      child.destroy()

    search_query = self.decision_search_entry.get().strip() if hasattr(self, "decision_search_entry") else None
    priority_filter = self.decision_priority_var.get() if hasattr(self, "decision_priority_var") else "All"
    status_filter = self.decision_status_var.get() if hasattr(self, "decision_status_var") else "All"

    decisions = DecisionEngine.get_all_decisions(
        search_query=search_query, priority_filter=priority_filter, status_filter=status_filter
    )

    if not decisions:
      ctk.CTkLabel(
          self.decision_scroll, text="No decisions match the current filters.",
          font=FONT_BODY, text_color=COLOR_TEXT_MUTED,
      ).pack(pady=30)
      return

    priority_colors = {
        "Low": "#64748B",
        "Medium": COLOR_BLUE,
        "High": "#F59E0B",
        "Critical": COLOR_PINK,
    }

    for d in decisions:
      card = ctk.CTkFrame(self.decision_scroll, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
      card.pack(fill="x", pady=6, padx=2)

      top_row = ctk.CTkFrame(card, fg_color="transparent")
      top_row.pack(fill="x", padx=15, pady=(12, 4))

      priority_badge = ctk.CTkLabel(
          top_row, text=d["priority"], font=(FONT_SMALL[0], 10, "bold"), text_color="white",
          fg_color=priority_colors.get(d["priority"], COLOR_BLUE), corner_radius=6, width=70, height=22,
      )
      priority_badge.pack(side="left", padx=(0, 10))

      ctk.CTkLabel(top_row, text=d["title"], font=FONT_SUBHEADER, text_color=COLOR_TEXT_DARK, anchor="w").pack(side="left", fill="x", expand=True)

      status_lbl = ctk.CTkLabel(
          top_row, text=d["status"], font=(FONT_SMALL[0], 10, "bold"),
          text_color=COLOR_PRIMARY_SEA_GREEN if d["status"] == "Approved" else ("#94A3B8" if d["status"] == "Ignored" else COLOR_PINK),
      )
      status_lbl.pack(side="right")

      ctk.CTkLabel(
          card, text=d["description"], font=FONT_BODY, text_color=COLOR_TEXT_DARK, anchor="w", justify="left", wraplength=700,
      ).pack(fill="x", padx=15, pady=(0, 4))

      if d.get("reason"):
        ctk.CTkLabel(
            card, text=f"Recommendation: {d['reason']}", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED, anchor="w", justify="left", wraplength=700,
        ).pack(fill="x", padx=15, pady=(0, 8))

      meta_row = ctk.CTkFrame(card, fg_color="transparent")
      meta_row.pack(fill="x", padx=15, pady=(0, 12))

      ctk.CTkLabel(
          meta_row, text=f"{d['category']}  •  {d['generated_at']}", font=(FONT_SMALL[0], 9), text_color=COLOR_TEXT_MUTED,
      ).pack(side="left")

      btn_frame = ctk.CTkFrame(meta_row, fg_color="transparent")
      btn_frame.pack(side="right")

      if d["status"] == "Pending":
        ctk.CTkButton(
            btn_frame, text="✅ Approve", width=90, height=30, fg_color=COLOR_PRIMARY_SEA_GREEN,
            command=lambda did=d["decision_id"]: self._handle_decision_action(did, "Approved"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_frame, text="🙈 Ignore", width=90, height=30, fg_color="#94A3B8",
            command=lambda did=d["decision_id"]: self._handle_decision_action(did, "Ignored"),
        ).pack(side="left", padx=(0, 8))

      if self.role == "admin":
        ctk.CTkButton(
            btn_frame, text="🗑️ Delete", width=90, height=30, fg_color=COLOR_PINK,
            command=lambda did=d["decision_id"]: self._handle_decision_delete(did),
        ).pack(side="left")

  def _handle_decision_action(self, decision_id, status):
    res = DecisionEngine.set_decision_status(decision_id, status, self.user.get("name", self.role))
    if res["success"]:
      self._update_decision_badge()
      self._load_decision_list()
    else:
      CustomDialog(self, title="Decision Engine", message=res["message"], dialog_type="warning")

  def _handle_decision_delete(self, decision_id):
    def confirm_delete():
      res = DecisionEngine.delete_decision(decision_id, self.role)
      if res["success"]:
        self._update_decision_badge()
        self._load_decision_list()
      else:
        CustomDialog(self, title="Decision Engine", message=res["message"], dialog_type="warning")

    CustomDialog(self, title="Confirm Delete", message="Are you sure you want to delete this decision?", dialog_type="confirm", on_confirm=confirm_delete)

  # --------------------------------------------------------------------------
  # 2. BOOKS MODULE
  # --------------------------------------------------------------------------
  def _render_books_module(self, parent):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    # Top Control Bar (Search + Action Buttons)
    ctrl_frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctrl_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ctrl_frame.grid_columnconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    left_panel.grid(row=0, column=0, sticky="w")

    right_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    right_panel.grid(row=0, column=1, sticky="e")

    self.book_search_entry = ctk.CTkEntry(
        left_panel,
        placeholder_text="Search by Book ID, Title, or ISBN...",
        width=280,
        height=38,
    )
    self.book_search_entry.pack(side="left", padx=(0, 10))
    self.book_search_entry.bind("<Return>", lambda event: self._load_books_table(show_no_results=True))
    self.book_search_entry.bind("<KeyRelease>", lambda event: self._load_books_table())

    btn_search = ctk.CTkButton(
        left_panel,
        text="Search",
        width=110,
        height=38,
        fg_color=COLOR_BLUE,
        command=lambda: self._load_books_table(show_no_results=True),
        corner_radius=12,
        font=(FONT_BODY[0], 11),
    )
    btn_search.pack(side="left", padx=(0, 10))

    button_kwargs = {
        "width": 110,
        "height": 38,
        "corner_radius": 12,
        "font": (FONT_BODY[0], 11),
    }

    if self.role == "admin":
      btn_edit = ctk.CTkButton(
          right_panel,
          text="✏️ Edit",
          fg_color=COLOR_BLUE,
          command=self._edit_selected_book,
          **button_kwargs,
      )
      btn_edit.pack(side="left", padx=(0, 10))

      btn_delete = ctk.CTkButton(
          right_panel,
          text="🗑️ Delete",
          fg_color=COLOR_PINK,
          command=self._delete_selected_book,
          **button_kwargs,
      )
      btn_delete.pack(side="left", padx=(0, 10))

      btn_add = ctk.CTkButton(
          right_panel,
          text="+ Add Book",
          fg_color=COLOR_PRIMARY_SEA_GREEN,
          command=lambda: self._open_book_dialog(),
          **button_kwargs,
      )
      btn_add.pack(side="left", padx=(0, 10))

    btn_export = ctk.CTkButton(
        right_panel,
        text="Excel Backup",
        fg_color=COLOR_BLUE,
        command=self._handle_books_backup,
        **button_kwargs,
    )
    btn_export.pack(side="left", padx=(0, 10))

    # Table Grid
    cols = [
        "S.No",
        "Title",
        "ISBN",
        "Category",
        "Author Name",
        "Total Qty",
        "Available Qty",
        "Created Date",
    ]
    self.books_table = ModernTable(parent, columns=cols)
    self.books_table.grid(row=1, column=0, sticky="nsew")

    self._load_books_table()

  def _load_books_table(self, show_no_results: bool = False):
    query = self.book_search_entry.get().strip()
    books = BookManager.get_all_books(query if query else None, None)
    self.books_table.clear_table()
    for idx, b in enumerate(books, start=1):
      self.books_table.insert_row([
          idx,
          b["title"],
          b["isbn"],
          b["category"],
          b["author_name"],
          b["total_quantity"],
          b["available_quantity"],
          b["created_at"],
      ], real_id=b["book_id"])

    if show_no_results and query and not books:
      CustomDialog(self, title="Books Search", message="No matching book found.", dialog_type="info")

  def _handle_books_backup(self):
    res = BookManager.export_to_excel()
    CustomDialog(
        self,
        title="Books Backup",
        message=res.get("message", "Export finished."),
        dialog_type="success" if res.get("success") else "warning",
    )

  def _edit_selected_book(self):
    selected = self.books_table.get_selected_row()
    book_id = self.books_table.get_selected_id()
    if not selected or not book_id:
      CustomDialog(self, title="Edit Book", message="Please select a book row to edit.", dialog_type="warning")
      return

    book = {
        "book_id": int(book_id),
        "title": selected[1],
        "isbn": selected[2],
        "category": selected[3],
        "author_name": selected[4],
        "quantity": selected[5],
    }
    self._open_book_dialog(book=book)

  def _delete_selected_book(self):
    book_id = self.books_table.get_selected_id()
    if not book_id:
      CustomDialog(self, title="Delete Book", message="Please select a book row to delete.", dialog_type="warning")
      return

    book_id = int(book_id)
    def confirm_delete():
      res = BookManager.delete_book(book_id)
      CustomDialog(self, title="Delete Book", message=res["message"], dialog_type="success" if res["success"] else "warning")
      if res["success"]:
        self._refresh_current_module()

    CustomDialog(self, title="Confirm Delete", message="Are you sure you want to delete this record?", dialog_type="confirm", on_confirm=confirm_delete)

  def _open_book_dialog(self, book: dict = None):
    is_edit = bool(book)
    win, body, footer = self._build_scrollable_dialog(
        "Edit Book Record" if is_edit else "Add New Book Record", width=420, height=480
    )

    fields = ["Title", "ISBN", "Category", "Author Name", "Quantity"]
    entries = {}

    for f in fields:
      lbl = ctk.CTkLabel(body, text=f, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED)
      lbl.pack(anchor="w", padx=20, pady=(10, 2))
      entry = ctk.CTkEntry(body, height=36)
      entry.pack(fill="x", padx=20)
      if f == "Quantity":
        entry.insert(0, str(book["quantity"] if is_edit else "1"))
      elif is_edit:
        key = f.lower().replace(" ", "_")
        entry.insert(0, book.get(key, ""))
      entries[f] = entry

    def save():
      values = {
          "title": entries["Title"].get().strip(),
          "isbn": entries["ISBN"].get().strip(),
          "category": entries["Category"].get().strip(),
          "author_name": entries["Author Name"].get().strip(),
          "quantity": int(entries["Quantity"].get().strip() or 1),
      }
      if is_edit:
        res = BookManager.update_book(
            book_id=book["book_id"],
            title=values["title"],
            isbn=values["isbn"],
            category=values["category"],
            author_name=values["author_name"],
            quantity=values["quantity"],
        )
      else:
        res = BookManager.add_or_update_book(
            title=values["title"],
            isbn=values["isbn"],
            category=values["category"],
            author_name=values["author_name"],
            quantity=values["quantity"],
        )
      win.destroy()
      CustomDialog(
          self,
          title="Book Update" if is_edit else "Book Save",
          message=res["message"],
          dialog_type="success" if res["success"] else "warning",
      )
      if res["success"]:
        self._refresh_current_module()

    btn_save = ctk.CTkButton(
        footer,
        text="Save Changes" if is_edit else "Save Book",
        height=40,
        fg_color=COLOR_PRIMARY_SEA_GREEN,
        command=save,
    )
    btn_save.pack(fill="x", padx=20, pady=25)

  # --------------------------------------------------------------------------
  # 3. ISSUE / RETURN MODULE
  # --------------------------------------------------------------------------
  def _render_issue_return_module(self, parent):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    # Top Control Bar (Search + Action Buttons) — matches Books module layout
    ctrl_frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctrl_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ctrl_frame.grid_columnconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    left_panel.grid(row=0, column=0, sticky="w")

    right_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    right_panel.grid(row=0, column=1, sticky="e")

    self.issue_search_entry = ctk.CTkEntry(
        left_panel,
        placeholder_text="Search by Student ID, Name, Department, or Book...",
        width=280,
        height=38,
    )
    self.issue_search_entry.pack(side="left", padx=(0, 10))
    self.issue_search_entry.bind("<Return>", lambda event: self._load_issue_return_table())
    self.issue_search_entry.bind("<KeyRelease>", lambda event: self._load_issue_return_table())
    btn_search = ctk.CTkButton(
        left_panel,
        text="Search",
        command=lambda: self._load_issue_return_table(),
        **ACTION_BUTTON_STYLE,
    )
    btn_search.pack(side="left", padx=(0, 10))

    if self.role == "admin":
      btn_edit = ctk.CTkButton(
          right_panel,
          text="✏️ Edit",
          fg_color=COLOR_BLUE,
          command=self._edit_selected_issue_record,
          **ACTION_BUTTON_STYLE,
      )
      btn_edit.pack(side="left", padx=(0, 10))

      btn_delete = ctk.CTkButton(
          right_panel,
          text="🗑️ Delete",
          fg_color=COLOR_PINK,
          command=self._delete_selected_issue_record,
          **ACTION_BUTTON_STYLE,
      )
      btn_delete.pack(side="left", padx=(0, 10))

    btn_issue = ctk.CTkButton(
        right_panel,
        text="+ Issue Book",
        fg_color=COLOR_PRIMARY_SEA_GREEN,
        command=self._open_issue_book_dialog,
        **ACTION_BUTTON_STYLE,
    )
    btn_issue.pack(side="left", padx=(0, 10))

    btn_return = ctk.CTkButton(
        right_panel,
        text="Return Book",
        fg_color=COLOR_PRIMARY_SEA_GREEN,
        command=self._open_return_book_dialog,
        **ACTION_BUTTON_STYLE,
    )
    btn_return.pack(side="left", padx=(0, 10))

    btn_export = ctk.CTkButton(
        right_panel,
        text="Excel Backup",
        fg_color=COLOR_BLUE,
        command=self._handle_issue_return_backup,
        **ACTION_BUTTON_STYLE,
    )
    btn_export.pack(side="left")

    cols = [
        "S.No",
        "Student ID",
        "Student Name",
        "Department",
        "Semester",
        "Book Title",
        "Status",
        "Issue Date",
        "Expected Return",
        "Return Date",
        "Fine (PKR)",
    ]
    self.issue_return_table = ModernTable(parent, columns=cols)
    self.issue_return_table.grid(row=1, column=0, sticky="nsew")
    self.issue_return_lookup = {}
    self._load_issue_return_table()

  def _open_issue_book_dialog(self):
    win, body, footer = self._build_scrollable_dialog("Issue Book", width=440, height=620)

    fields = [
        ("Student ID", "s_id"),
        ("Student Name", "s_name"),
        ("Department", "s_dept"),
        ("Semester", "s_sem"),
        ("Email Address", "s_email"),
        ("Contact Number", "s_contact"),
        ("Book ID to Issue", "b_id"),
        ("Return Date (YYYY-MM-DD HH:MM:SS)", "r_date"),
    ]
    entries = {}
    for label_text, key in fields:
      ctk.CTkLabel(body, text=label_text, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(8, 2))
      entry = ctk.CTkEntry(body, height=36)
      entry.pack(fill="x", padx=20)
      if key == "r_date":
        entry.insert(0, (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"))
      entries[key] = entry

    def submit():
      try:
        book_id_value = int(entries["b_id"].get().strip() or 0)
      except ValueError:
        CustomDialog(self, title="Issue Result", message="Book ID must be a valid number.", dialog_type="warning")
        return

      return_date_value = entries["r_date"].get().strip()
      if not return_date_value:
        CustomDialog(self, title="Issue Result", message="Please provide a valid return date.", dialog_type="warning")
        return

      res = StudentManager.issue_book(
          student_id=entries["s_id"].get().strip(),
          student_name=entries["s_name"].get().strip(),
          department=entries["s_dept"].get().strip(),
          semester=entries["s_sem"].get().strip(),
          email=entries["s_email"].get().strip(),
          contact=entries["s_contact"].get().strip(),
          book_id=book_id_value,
          expected_return_datetime_str=return_date_value,
      )
      CustomDialog(self, title="Issue Result", message=res["message"], dialog_type="success" if res["success"] else "warning")
      if res["success"]:
        win.destroy()
        self._refresh_current_module()

    ctk.CTkButton(footer, text="Issue Book Now", height=42, fg_color=COLOR_PRIMARY_SEA_GREEN, command=submit).pack(fill="x", padx=20, pady=20)

  def _open_return_book_dialog(self):
    win = ctk.CTkToplevel(self)
    win.title("Return Book")
    win.geometry("360x220")
    win.grab_set()

    ctk.CTkLabel(win, text="Student ID", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(15, 2))
    ent_ret_id = ctk.CTkEntry(win, height=38)
    ent_ret_id.pack(fill="x", padx=20)

    def submit():
      s_id = ent_ret_id.get().strip()
      res = StudentManager.process_return_book(s_id)
      CustomDialog(self, title="Book Return", message=res["message"], dialog_type="success" if res["success"] else "warning")
      if res["success"]:
        win.destroy()
        self._refresh_current_module()

    ctk.CTkButton(win, text="Process Return & Update Stock", height=42, fg_color=COLOR_PINK, command=submit).pack(fill="x", padx=20, pady=20)
  # 4. ATTENDANCE MODULE
  # --------------------------------------------------------------------------
  def _render_attendance_module(self, parent):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    ctrl_frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctrl_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ctrl_frame.grid_columnconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    left_panel.grid(row=0, column=0, sticky="w")

    right_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    right_panel.grid(row=0, column=1, sticky="e")

    self.attendance_search_entry = ctk.CTkEntry(
        left_panel,
        placeholder_text="Search by name, student ID, or date...",
        width=280,
        height=38,
    )
    self.attendance_search_entry.pack(side="left", padx=(0, 10))
    self.attendance_search_entry.bind("<Return>", lambda event: self._load_attendance_table())
    self.attendance_search_entry.bind("<KeyRelease>", lambda event: self._load_attendance_table())

    btn_search = ctk.CTkButton(
        left_panel,
        text="Search",
        command=lambda: self._load_attendance_table(),
        **ACTION_BUTTON_STYLE,
    )
    btn_search.pack(side="left", padx=(0, 10))

    if self.role == "admin":
      btn_edit = ctk.CTkButton(
          right_panel, text="✏️ Edit", fg_color=COLOR_BLUE, command=self._edit_selected_attendance, **ACTION_BUTTON_STYLE
      )
      btn_edit.pack(side="left", padx=(0, 10))

      btn_delete = ctk.CTkButton(
          right_panel, text="🗑️ Delete", fg_color=COLOR_PINK, command=self._delete_selected_attendance, **ACTION_BUTTON_STYLE
      )
      btn_delete.pack(side="left", padx=(0, 10))

    btn_checkin = ctk.CTkButton(
        right_panel, text="+ Check-In", fg_color=COLOR_PRIMARY_SEA_GREEN, command=self._open_checkin_dialog, **ACTION_BUTTON_STYLE
    )
    btn_checkin.pack(side="left", padx=(0, 10))

    btn_checkout = ctk.CTkButton(
        right_panel, text="Check-Out", fg_color=COLOR_PINK, command=self._open_checkout_dialog, **ACTION_BUTTON_STYLE
    )
    btn_checkout.pack(side="left", padx=(0, 10))

    btn_export = ctk.CTkButton(
        right_panel, text="Excel Backup", fg_color=COLOR_BLUE, command=self._handle_attendance_backup, **ACTION_BUTTON_STYLE
    )
    btn_export.pack(side="left")

    cols = [
        "S.No",
        "Student Name",
        "Student ID",
        "Department",
        "Check-In Time",
        "Check-Out Time",
        "Date",
    ]
    self.att_table = ModernTable(parent, columns=cols)
    self.att_table.grid(row=1, column=0, sticky="nsew")
    self.attendance_lookup = {}

    self._load_attendance_table()

  def _load_attendance_table(self):
    search_query = self.attendance_search_entry.get().strip() if hasattr(self, "attendance_search_entry") else None
    logs = AttendanceManager.get_all_attendance(search_query=search_query)
    self.att_table.clear_table()
    self.attendance_lookup = {}
    for idx, l in enumerate(logs, start=1):
      self.attendance_lookup[l["log_id"]] = l
      self.att_table.insert_row([
          idx,
          l["student_full_name"],
          l["student_id"],
          l["department"],
          l["check_in_time"],
          l["check_out_time"] if l["check_out_time"] else "In Library",
          l["date"],
      ], real_id=l["log_id"])

  def _handle_attendance_backup(self):
    res = AttendanceManager.export_to_excel()
    CustomDialog(
        self,
        title="Attendance Backup",
        message=res.get("message", "Export finished."),
        dialog_type="success" if res.get("success") else "warning",
    )

  def _edit_selected_attendance(self):
    log_id = self.att_table.get_selected_id()
    if not log_id:
      CustomDialog(self, title="Edit Attendance", message="Please select a row to edit.", dialog_type="warning")
      return

    log_id = int(log_id)
    log = self.attendance_lookup.get(log_id)
    if not log:
      CustomDialog(self, title="Edit Attendance", message="Selected record could not be found.", dialog_type="warning")
      return

    win, body, footer = self._build_scrollable_dialog("Edit Attendance Record", width=400, height=440)

    # Locked identity fields (display only, not editable)
    for label, value in [
        ("Student Name (locked)", log["student_full_name"]),
        ("Student ID (locked)", log["student_id"]),
        ("Department (locked)", log.get("department") or ""),
    ]:
      ctk.CTkLabel(body, text=label, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(10, 2))
      locked_entry = ctk.CTkEntry(body, height=36, state="disabled")
      locked_entry.pack(fill="x", padx=20)
      locked_entry.configure(state="normal")
      locked_entry.insert(0, value)
      locked_entry.configure(state="disabled")

    ctk.CTkLabel(body, text="Check-In Time (YYYY-MM-DD HH:MM:SS)", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(10, 2))
    checkin_entry = ctk.CTkEntry(body, height=36)
    checkin_entry.pack(fill="x", padx=20)
    checkin_entry.insert(0, log.get("check_in_time") or "")

    ctk.CTkLabel(body, text="Check-Out Time (YYYY-MM-DD HH:MM:SS, blank = still inside)", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(10, 2))
    checkout_entry = ctk.CTkEntry(body, height=36)
    checkout_entry.pack(fill="x", padx=20)
    checkout_entry.insert(0, log.get("check_out_time") or "")

    def save():
      try:
        res = AttendanceManager.update_attendance(
            log_id=log_id,
            check_in_time=checkin_entry.get().strip(),
            check_out_time=checkout_entry.get().strip(),
        )
      except Exception as e:
        CustomDialog(self, title="Edit Attendance", message=f"Unexpected error: {str(e)}", dialog_type="warning")
        return

      if res["success"]:
        # Refresh BEFORE destroying the popup, and make destroy itself
        # defensive — CustomTkinter buttons can throw a harmless internal
        # error when destroyed right after being clicked, which must never
        # be allowed to stop the data refresh from happening.
        self._refresh_current_module()
        try:
          win.destroy()
        except Exception:
          pass
      CustomDialog(self, title="Edit Attendance", message=res["message"], dialog_type="success" if res["success"] else "warning")

    ctk.CTkButton(footer, text="Save Changes", height=40, fg_color=COLOR_PRIMARY_SEA_GREEN, command=save).pack(fill="x", padx=20, pady=20)

  def _delete_selected_attendance(self):
    log_id = self.att_table.get_selected_id()
    if not log_id:
      CustomDialog(self, title="Delete Attendance", message="Please select a log row to delete.", dialog_type="warning")
      return

    log_id = int(log_id)
    def confirm_delete():
      res = AttendanceManager.delete_attendance_log(log_id, self.role)
      CustomDialog(self, title="Delete Attendance", message=res["message"], dialog_type="success" if res["success"] else "warning")
      if res["success"]:
        self._refresh_current_module()

    CustomDialog(self, title="Confirm Delete", message="Are you sure you want to delete this record?", dialog_type="confirm", on_confirm=confirm_delete)

  def _open_checkin_dialog(self):
    win = ctk.CTkToplevel(self)
    win.title("Student Check-In")
    win.geometry("350x320")
    win.grab_set()

    entries = {}
    for f in ["Full Name", "Student ID", "Department"]:
      ctk.CTkLabel(
          win, text=f, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED
      ).pack(anchor="w", padx=20, pady=(10, 2))
      e = ctk.CTkEntry(win, height=36)
      e.pack(fill="x", padx=20)
      entries[f] = e

    def submit():
      res = AttendanceManager.check_in(
          entries["Full Name"].get().strip(),
          entries["Student ID"].get().strip(),
          entries["Department"].get().strip(),
      )
      win.destroy()
      self._load_attendance_table()
      CustomDialog(self, title="Check-In", message=res["message"])

    ctk.CTkButton(
        win,
        text="Complete Check-In",
        height=40,
        fg_color=COLOR_PRIMARY_SEA_GREEN,
        command=submit,
    ).pack(fill="x", padx=20, pady=20)

  def _open_checkout_dialog(self):
    win = ctk.CTkToplevel(self)
    win.title("Student Check-Out")
    win.geometry("350x200")
    win.grab_set()

    ctk.CTkLabel(
        win, text="Student ID", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED
    ).pack(anchor="w", padx=20, pady=(15, 2))
    e = ctk.CTkEntry(win, height=36)
    e.pack(fill="x", padx=20)

    def submit():
      res = AttendanceManager.check_out(e.get().strip())
      win.destroy()
      self._load_attendance_table()
      CustomDialog(self, title="Check-Out", message=res["message"])

    ctk.CTkButton(
        win,
        text="Complete Check-Out",
        height=40,
        fg_color=COLOR_PINK,
        command=submit,
    ).pack(fill="x", padx=20, pady=20)

  # --------------------------------------------------------------------------
  # 5. STAFF MODULE
  # --------------------------------------------------------------------------
  def _render_staff_module(self, parent):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    ctrl_frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctrl_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ctrl_frame.grid_columnconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    left_panel.grid(row=0, column=0, sticky="w")

    right_panel = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
    right_panel.grid(row=0, column=1, sticky="e")

    self.staff_search_entry = ctk.CTkEntry(
        left_panel,
        placeholder_text="Search by Staff ID, Name, or Email...",
        width=280,
        height=38,
    )
    self.staff_search_entry.pack(side="left", padx=(0, 10))
    self.staff_search_entry.bind("<Return>", lambda event: self._load_staff_table())
    self.staff_search_entry.bind("<KeyRelease>", lambda event: self._load_staff_table())

    btn_search = ctk.CTkButton(
        left_panel,
        text="Search",
        command=lambda: self._load_staff_table(),
        **ACTION_BUTTON_STYLE,
    )
    btn_search.pack(side="left", padx=(0, 10))

    if self.role == "admin":
      btn_edit = ctk.CTkButton(right_panel, text="✏️ Edit", fg_color=COLOR_BLUE, command=self._edit_selected_staff, **ACTION_BUTTON_STYLE)
      btn_edit.pack(side="left", padx=(0, 10))

      btn_delete = ctk.CTkButton(right_panel, text="🗑️ Delete", fg_color=COLOR_PINK, command=self._delete_selected_staff, **ACTION_BUTTON_STYLE)
      btn_delete.pack(side="left", padx=(0, 10))

      btn_add = ctk.CTkButton(right_panel, text="+ Register", fg_color=COLOR_PRIMARY_SEA_GREEN, command=self._open_add_staff_dialog, **ACTION_BUTTON_STYLE)
      btn_add.pack(side="left", padx=(0, 10))

    btn_export = ctk.CTkButton(right_panel, text="Excel Backup", fg_color=COLOR_BLUE, command=self._handle_staff_backup, **ACTION_BUTTON_STYLE)
    btn_export.pack(side="left")

    cols = [
        "Staff ID",
        "Name",
        "Contact",
        "Email",
        "Status",
    ]
    self.staff_table = ModernTable(parent, columns=cols)
    self.staff_table.grid(row=1, column=0, sticky="nsew")
    self.staff_lookup = {}
    self._load_staff_table()

  def _open_add_staff_dialog(self):
    win, body, footer = self._build_scrollable_dialog("Register Staff", width=420, height=520)

    entries = {}
    fields = [
        "Staff ID",
        "Staff Name",
        "Contact Number",
        "Email (Must match User Auth)",
        "System Password",
    ]
    for f in fields:
      ctk.CTkLabel(
          body, text=f, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED
      ).pack(anchor="w", padx=20, pady=(8, 2))
      e = ctk.CTkEntry(body, height=36)
      e.pack(fill="x", padx=20)
      entries[f] = e

    def save():
      res = StaffManager.add_staff(
          staff_id=entries["Staff ID"].get().strip(),
          staff_name=entries["Staff Name"].get().strip(),
          contact=entries["Contact Number"].get().strip(),
          email=entries["Email (Must match User Auth)"].get().strip(),
          system_password=entries["System Password"].get().strip(),
      )
      if res["success"]:
        win.destroy()
        self._load_staff_table()
      CustomDialog(self, title="Staff Authorization", message=res["message"], dialog_type="success" if res["success"] else "warning")

    ctk.CTkButton(
        footer,
        text="Register Staff",
        height=40,
        fg_color=COLOR_PRIMARY_SEA_GREEN,
        command=save,
    ).pack(fill="x", padx=20, pady=20)

  def _handle_staff_backup(self):
    res = StaffManager.export_to_excel()
    CustomDialog(
        self,
        title="Staff Backup",
        message=res["message"],
        dialog_type="success" if res["success"] else "warning",
    )

  def _edit_selected_staff(self):
    selected = self.staff_table.get_selected_row()
    if not selected:
      CustomDialog(self, title="Edit Staff", message="Please select a staff row to edit.", dialog_type="warning")
      return

    win, body, footer = self._build_scrollable_dialog("Edit Staff Record", width=420, height=500)

    staff_id = selected[0]
    entries = {}
    fields = [
        ("Staff Name", selected[1]),
        ("Contact Number", selected[2]),
        ("Email", selected[3]),
        ("Status", "Active" if selected[4] == "Active" else "Suspended"),
    ]

    for label, value in fields:
      ctk.CTkLabel(body, text=label, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(10, 2))
      entry = ctk.CTkEntry(body, height=36)
      entry.pack(fill="x", padx=20)
      entry.insert(0, value)
      entries[label] = entry

    def save():
      res = StaffManager.update_staff(
          staff_id=staff_id,
          staff_name=entries["Staff Name"].get().strip(),
          contact=entries["Contact Number"].get().strip(),
          email=entries["Email"].get().strip(),
          status=entries["Status"].get().strip(),
      )
      if res["success"]:
        win.destroy()
        self._refresh_current_module()
      CustomDialog(self, title="Staff Update", message=res["message"], dialog_type="success" if res["success"] else "warning")

    ctk.CTkButton(footer, text="Save Changes", height=40, fg_color=COLOR_PRIMARY_SEA_GREEN, command=save).pack(fill="x", padx=20, pady=25)

  def _delete_selected_staff(self):
    selected = self.staff_table.get_selected_row()
    if not selected:
      CustomDialog(self, title="Delete Staff", message="Please select a staff row to delete.", dialog_type="warning")
      return

    staff_id = selected[0]
    def confirm_delete():
      res = StaffManager.delete_staff(staff_id)
      CustomDialog(self, title="Delete Staff", message=res["message"], dialog_type="success" if res["success"] else "warning")
      if res["success"]:
        self._refresh_current_module()

    CustomDialog(self, title="Confirm Delete", message="Are you sure you want to delete this record?", dialog_type="confirm", on_confirm=confirm_delete)

  def _load_staff_table(self):
    self.staff_table.clear_table()
    self.staff_lookup = {}
    search_query = self.staff_search_entry.get().strip() if hasattr(self, "staff_search_entry") else None
    for staff in StaffManager.get_all_staff(search_query=search_query):
      self.staff_lookup[staff["staff_id"]] = staff
      self.staff_table.insert_row([
          staff["staff_id"],
          staff["staff_name"],
          staff["staff_contact"],
          staff["email"],
          "Active" if staff.get("is_authorized", 1) else "Suspended",
      ])

  def _load_issue_return_table(self):
    self.issue_return_table.clear_table()
    self.issue_return_lookup = {}
    search_query = self.issue_search_entry.get().strip() if hasattr(self, "issue_search_entry") else None
    for idx, issue in enumerate(StudentManager.get_student_issues(search_query=search_query), start=1):
      self.issue_return_lookup[issue["issue_id"]] = issue
      self.issue_return_table.insert_row([
          idx,
          issue["student_id"],
          issue["student_name"],
          issue["department"],
          issue["semester"],
          issue["book_title"],
          issue["status"],
          issue["issue_date_time"],
          issue["expected_return_date_time"],
          issue.get("return_date_time") or "N/A",
          f"Rs. {issue.get('fine_amount', 0.0):.2f}",
      ], real_id=issue["issue_id"])

  def _edit_selected_issue_record(self):
    selected_id = self.issue_return_table.get_selected_id()
    if not selected_id:
      CustomDialog(self, title="Edit Record", message="Please select a record to edit.", dialog_type="warning")
      return
    issue_id = int(selected_id)
    issue = self.issue_return_lookup.get(issue_id)
    if not issue:
      CustomDialog(self, title="Edit Record", message="Selected issue record could not be found.", dialog_type="warning")
      return

    if issue.get("status") not in ("Issued", "Overdue"):
      CustomDialog(self, title="Edit Record", message="This book has already been returned. Returned records are locked and cannot be edited.", dialog_type="info")
      return

    win, body, footer = self._build_scrollable_dialog("Edit Issue Record", width=440, height=560)

    # Locked identity/audit fields (display only)
    for label, value in [
        ("Student ID (locked)", issue["student_id"]),
        ("Student Name (locked)", issue["student_name"]),
        ("Book (locked)", issue["book_title"]),
        ("Issue Date (locked)", issue["issue_date_time"]),
    ]:
      ctk.CTkLabel(body, text=label, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(8, 2))
      locked_entry = ctk.CTkEntry(body, height=34)
      locked_entry.pack(fill="x", padx=20)
      locked_entry.insert(0, value)
      locked_entry.configure(state="disabled")

    # Editable fields
    entries = {}
    for label, key, current in [
        ("Department", "department", issue.get("department") or ""),
        ("Semester", "semester", issue.get("semester") or ""),
        ("Email", "email", issue.get("email") or ""),
        ("Contact Number", "contact_number", issue.get("contact_number") or ""),
        ("Expected Return (YYYY-MM-DD HH:MM:SS)", "expected_return", issue.get("expected_return_date_time") or ""),
    ]:
      ctk.CTkLabel(body, text=label, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(8, 2))
      entry = ctk.CTkEntry(body, height=34)
      entry.pack(fill="x", padx=20)
      entry.insert(0, current)
      entries[key] = entry

    def save():
      res = StudentManager.update_issue_record(
          issue_id=issue_id,
          department=entries["department"].get().strip(),
          semester=entries["semester"].get().strip(),
          email=entries["email"].get().strip(),
          contact_number=entries["contact_number"].get().strip(),
          expected_return_datetime_str=entries["expected_return"].get().strip(),
      )
      if res["success"]:
        win.destroy()
        self._refresh_current_module()
      CustomDialog(self, title="Edit Record", message=res["message"], dialog_type="success" if res["success"] else "warning")

    ctk.CTkButton(footer, text="Save Changes", height=40, fg_color=COLOR_PRIMARY_SEA_GREEN, command=save).pack(fill="x", padx=20, pady=20)

  def _delete_selected_issue_record(self):
    selected_id = self.issue_return_table.get_selected_id()
    if not selected_id:
      CustomDialog(self, title="Delete Record", message="Please select a record to delete.", dialog_type="warning")
      return
    issue_id = int(selected_id)
    issue = self.issue_return_lookup.get(issue_id)
    if not issue:
      CustomDialog(self, title="Delete Record", message="Selected issue record could not be found.", dialog_type="warning")
      return

    def confirm_delete():
      if issue.get("status") in ("Issued", "Overdue"):
        res = StudentManager.delete_issue_record(issue_id, self.role)
      else:
        res = StudentManager.delete_return_record(issue.get("return_id"), self.role)
      CustomDialog(self, title="Delete Record", message=res["message"], dialog_type="success" if res["success"] else "warning")
      if res["success"]:
        self._refresh_current_module()

    CustomDialog(self, title="Confirm Delete", message="Are you sure you want to delete this record?", dialog_type="confirm", on_confirm=confirm_delete)

  def _handle_issue_return_backup(self):
    res = StudentManager.export_to_excel()
    CustomDialog(
        self,
        title="Issue/Return Backup",
        message=res.get("message", "Export finished."),
        dialog_type="success" if res.get("success") else "warning",
    )

  # --------------------------------------------------------------------------
  # 6. ANALYTICS MODULE
  # --------------------------------------------------------------------------
  def _render_analytics_module(self, parent):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    tabview = ctk.CTkTabview(parent, fg_color=COLOR_CARD_BG)
    tabview.grid(row=0, column=0, rowspan=2, sticky="nsew")

    t1_outer = tabview.add("Peak Check-Ins")
    t2_outer = tabview.add("Most Borrowed")
    t3_outer = tabview.add("Fine Collection Engine")
    t4_outer = tabview.add("Department Usage")

    t1 = ctk.CTkScrollableFrame(t1_outer, fg_color="transparent")
    t1.pack(fill="both", expand=True)
    t2 = ctk.CTkScrollableFrame(t2_outer, fg_color="transparent")
    t2.pack(fill="both", expand=True)
    t3 = ctk.CTkScrollableFrame(t3_outer, fg_color="transparent")
    t3.pack(fill="both", expand=True)
    t4 = ctk.CTkScrollableFrame(t4_outer, fg_color="transparent")
    t4.pack(fill="both", expand=True)

    # Peak Check-In Line Chart
    peak = AnalyticsManager.get_peak_checkin_trend()
    ctk.CTkLabel(
        t1,
        text=f"Busiest Peak Hour ({peak.get('data_scope', 'Today')}): {peak['peak_time']}",
        font=FONT_HEADER,
        text_color=COLOR_PRIMARY_SEA_GREEN,
    ).pack(pady=(20, 5))
    ctk.CTkLabel(
        t1,
        text=f"Total Check-ins during peak hour: {peak['total_students']}",
        font=FONT_SUBHEADER,
    ).pack(pady=(0, 15))

    fig1, ax1 = plt.subplots(figsize=(6, 3.2), dpi=100)
    hours = list(peak["hourly_distribution"].keys())
    counts = list(peak["hourly_distribution"].values())
    if hours:
      ax1.plot(hours, counts, marker="o", color=COLOR_PRIMARY_SEA_GREEN, linewidth=2)
      ax1.fill_between(range(len(hours)), counts, alpha=0.15, color=COLOR_PRIMARY_SEA_GREEN)
      ax1.set_title(f"Hourly Check-In Trend ({peak.get('data_scope', 'Today')})")
      ax1.set_xlabel("Hour")
      ax1.set_ylabel("Check-Ins")
      ax1.set_xticks(range(len(hours)))
      ax1.set_xticklabels(hours, rotation=45, ha="right")
      ax1.grid(True, linestyle="--", alpha=0.4)
    else:
      ax1.text(0.5, 0.5, "No attendance data yet.", ha="center", va="center", color=COLOR_TEXT_MUTED)

    fig1.tight_layout()
    canvas1 = FigureCanvasTkAgg(fig1, master=t1)
    canvas1.draw()
    canvas1.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # Most Borrowed Bar Chart
    most_borrowed = AnalyticsManager.get_most_borrowed_categories()
    fig2, ax2 = plt.subplots(figsize=(6, 3.2), dpi=100)
    if most_borrowed:
      x = [m["title"] for m in most_borrowed]
      y = [m["borrowed_count"] for m in most_borrowed]
      bars = ax2.bar(x, y, color=COLOR_BLUE, alpha=0.85)
      for bar in bars:
        height = bar.get_height()
        ax2.annotate(f"{int(height)}", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)
      ax2.set_title("Most Borrowed Books")
      ax2.set_xlabel("Book Title")
      ax2.set_ylabel("Times Borrowed")
      ax2.set_xticks(range(len(x)))
      ax2.set_xticklabels(x, rotation=45, ha="right")
      ax2.grid(True, axis="y", linestyle="--", alpha=0.4)
    else:
      ax2.text(0.5, 0.5, "No borrowed book data available.", ha="center", va="center", color=COLOR_TEXT_MUTED)

    fig2.tight_layout()
    canvas2 = FigureCanvasTkAgg(fig2, master=t2)
    canvas2.draw()
    canvas2.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    tbl_b = ModernTable(
        t2,
        columns=[
            "Category",
            "Title",
            "Author",
            "Borrowed Copies",
            "Total Stock",
        ],
    )
    tbl_b.pack(fill="both", expand=True, padx=10, pady=(10, 10))
    for b in most_borrowed:
      tbl_b.insert_row([
          b["category"],
          b["title"],
          b["author_name"],
          b["borrowed_count"],
          b["total_quantity"],
      ])

    # Fine Collection Column Chart
    fine_data = AnalyticsManager.calculate_fines_and_process_alerts()
    pie_data = fine_data.get("pie_chart_data", {})
    fig3, ax3 = plt.subplots(figsize=(6, 3.2), dpi=100)
    fig3.patch.set_facecolor("white")
    labels = list(pie_data.keys())
    sizes = list(pie_data.values())
    if sizes and sum(sizes) > 0:
      palette = [COLOR_PRIMARY_SEA_GREEN, COLOR_PINK, COLOR_BLUE, "#F59E0B", "#8B5CF6"]
      colors = [palette[i % len(palette)] for i in range(len(labels))]

      ax3.clear()
      bars = ax3.bar(labels, sizes, color=colors, alpha=0.9)
      for bar in bars:
        height = bar.get_height()
        ax3.annotate(f"{height:.0f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)
      ax3.set_title("Fine Collection Status")
      ax3.set_ylabel("Amount (Rs.)")
      ax3.grid(True, axis="y", linestyle="--", alpha=0.4)
    else:
      ax3.clear()
      ax3.text(0.5, 0.5, "No fine data available.", ha="center", va="center", color=COLOR_TEXT_MUTED)

    fig3.tight_layout()
    canvas3 = FigureCanvasTkAgg(fig3, master=t3)
    canvas3.draw()
    canvas3.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    tbl_f = ModernTable(
        t3,
        columns=[
            "Student Name",
            "Student ID",
            "Department",
            "Book Title",
            "Overdue Days",
            "Fine (Rs.)",
            "Account Status",
        ],
    )
    tbl_f.pack(fill="both", expand=True, padx=10, pady=(10, 10))
    for record in fine_data.get("fine_records", []):
      tbl_f.insert_row([
          record["student_name"],
          record["student_id"],
          record["department"],
          record["book_title"],
          record["days_overdue"],
          f"Rs. {record['fine_amount']:.2f}",
          record["status"],
      ])

    # Department Usage Line Chart
    dept_data = AnalyticsManager.get_department_usage_breakdown()
    fig4, ax4 = plt.subplots(figsize=(6, 3.5), dpi=100)
    if dept_data:
      depts = [d["department"] or "Unknown" for d in dept_data]
      checkins = [d["checkin_count"] for d in dept_data]

      top_dept = depts[0] if depts else "N/A"
      ctk.CTkLabel(
          t4, text=f"Most Active Department: {top_dept}", font=FONT_HEADER, text_color=COLOR_PRIMARY_SEA_GREEN,
      ).pack(pady=(15, 5))

      ax4.plot(depts, checkins, marker="o", color=COLOR_PRIMARY_SEA_GREEN, linewidth=2)
      ax4.fill_between(range(len(depts)), checkins, alpha=0.15, color=COLOR_PRIMARY_SEA_GREEN)
      for i, count in enumerate(checkins):
        ax4.annotate(str(count), xy=(i, count), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8)
      ax4.set_title("Department-Wise Library Usage")
      ax4.set_xlabel("Department")
      ax4.set_ylabel("Total Check-Ins")
      ax4.set_xticks(range(len(depts)))
      ax4.set_xticklabels(depts, rotation=30, ha="right")
      ax4.grid(True, linestyle="--", alpha=0.4)
    else:
      ax4.text(0.5, 0.5, "No attendance data available yet.", ha="center", va="center", color=COLOR_TEXT_MUTED)

    fig4.tight_layout()
    canvas4 = FigureCanvasTkAgg(fig4, master=t4)
    canvas4.draw()
    canvas4.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    tbl_d = ModernTable(t4, columns=["Department", "Total Check-Ins"])
    tbl_d.pack(fill="both", expand=True, padx=10, pady=(10, 10))
    for d in dept_data:
      tbl_d.insert_row([d["department"] or "Unknown", d["checkin_count"]])

  # 7. REPORTS MODULE
  # --------------------------------------------------------------------------
  def _render_reports_module(self, parent):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    top = ctk.CTkFrame(parent, fg_color="transparent")
    top.grid(row=0, column=0, sticky="ew", pady=(0, 10))

    self.report_period_var = ctk.StringVar(value="Daily")
    for period in ["Daily", "Weekly", "Monthly", "Yearly"]:
      ctk.CTkButton(
          top,
          text=period,
          fg_color=COLOR_BLUE,
          width=90,
          command=lambda p=period: self._display_report(p),
      ).pack(side="left", padx=5)

    ctk.CTkButton(
        top,
        text="📄 Export to Word",
        fg_color=COLOR_PRIMARY_SEA_GREEN,
        command=lambda: self._handle_report_word_export(),
    ).pack(side="right")

    self.report_scroll = ctk.CTkScrollableFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12)
    self.report_scroll.grid(row=1, column=0, sticky="nsew")

    self._display_report("Daily")

  def _report_add_section(self, title_text, lines):
    """Renders one dark-blue header bar + white text, followed by a bordered
    content box with black text — matching the Word export design."""
    header = ctk.CTkFrame(self.report_scroll, fg_color="#1F3864", corner_radius=6)
    header.pack(fill="x", padx=15, pady=(15, 0))
    ctk.CTkLabel(
        header, text=f"  {title_text}", font=(FONT_BODY[0], 13, "bold"), text_color="white",
    ).pack(anchor="w", pady=8)

    box = ctk.CTkFrame(self.report_scroll, fg_color="white", corner_radius=0, border_width=1, border_color=COLOR_BORDER)
    box.pack(fill="x", padx=15, pady=(0, 5))

    if not lines:
      lines = ["No data available for this period."]
    for line in lines:
      ctk.CTkLabel(
          box, text=line, font=FONT_BODY, text_color="black", anchor="w", justify="left", wraplength=800,
      ).pack(fill="x", padx=15, pady=6)

  def _display_report(self, period: str):
    self.report_period_var.set(period)
    for child in self.report_scroll.winfo_children():
      child.destroy()

    data = ReportManager.generate_report(period)

    # Branding + Title
    ctk.CTkLabel(
        self.report_scroll, text="📘  Smart Library System", font=(FONT_BODY[0], 14, "bold"), text_color="#1F3864",
    ).pack(anchor="w", padx=15, pady=(15, 0))
    ctk.CTkLabel(
        self.report_scroll, text=f"{period} Activity Report", font=(FONT_HEADER[0], 20, "bold"), text_color="#1F3864",
    ).pack(anchor="w", padx=15, pady=(0, 10))

    # Metadata table (dark blue label / light gray value, matches Word doc)
    meta_frame = ctk.CTkFrame(self.report_scroll, fg_color="transparent")
    meta_frame.pack(fill="x", padx=15, pady=(0, 10))
    meta_rows = [
        ("Report Type", f"{period} Report"),
        ("Generated On", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Generated By", self.user.get("name", self.role)),
    ]
    for label, value in meta_rows:
      row = ctk.CTkFrame(meta_frame, fg_color="transparent")
      row.pack(fill="x", pady=1)
      ctk.CTkLabel(row, text=label, font=(FONT_BODY[0], 10, "bold"), text_color="white", fg_color="#1F3864", width=160, anchor="w").pack(side="left", ipady=6, padx=(0, 1))
      ctk.CTkLabel(row, text=value, font=FONT_BODY, text_color="black", fg_color="#F2F2F2", anchor="w").pack(side="left", fill="x", expand=True, ipady=6, padx=(1, 0))

    # Sections matching the Word export
    self._report_add_section("Attendance Summary", [
        f"Total Check-Ins: {data.get('total_checkins', 0)}",
        f"Total Check-Outs: {data.get('total_checkouts', 0)}",
    ])

    dept_lines = [f"{d['department']}: {d['count']} books issued" for d in data.get("department_issues", [])]
    self._report_add_section("Department-Wise Book Issuance", dept_lines)

    book_lines = [f"{idx + 1}. {b['title']} — issued {b['issue_count']} times" for idx, b in enumerate(data.get("most_issued_books", []))]
    self._report_add_section("Most Issued Books", book_lines)

    overdue_lines = [
        f"{s['student_name']} ({s['student_id']}, {s['department']}) — due {s['expected_return_date_time']}"
        for s in data.get("unreturned_students", [])
    ]
    self._report_add_section("Overdue / Unreturned Books", overdue_lines)

    self._report_add_section("Fine Collection Estimate", [
        f"Estimated Fine Collection: Rs. {data.get('estimated_fine_collection', 0):.2f}",
    ])

    ctk.CTkLabel(self.report_scroll, text="", height=10).pack()

  def _handle_report_word_export(self):
    period = self.report_period_var.get() if hasattr(self, "report_period_var") else "Daily"
    res = ReportManager.export_to_word(period, generated_by=self.user.get("name", self.role))
    CustomDialog(
        self, title="Word Export", message=res.get("message", "Export finished."),
        dialog_type="success" if res.get("success") else "warning",
    )

  # --------------------------------------------------------------------------
  # 8. CHAT MODULE
  # --------------------------------------------------------------------------
  def _render_chat_module(self, parent):
    parent.grid_columnconfigure(0, weight=0)
    parent.grid_columnconfigure(1, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    if not hasattr(self, "chat_active_contact"):
      self.chat_active_contact = None
    self.chat_pending_attachment = None
    self._chat_contacts_snapshot = None
    self._chat_messages_snapshot = None

    left_panel = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12, width=290)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left_panel.grid_propagate(False)

    ctk.CTkLabel(left_panel, text="Conversations", font=FONT_SUBHEADER, text_color=COLOR_TEXT_DARK).pack(
        anchor="w", padx=15, pady=(15, 10)
    )

    self.chat_contacts_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
    self.chat_contacts_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 10))

    self.chat_right_panel = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12)
    self.chat_right_panel.grid(row=0, column=1, sticky="nsew")

    self._load_chat_contacts(force=True)
    self._render_chat_conversation_area()

    # Only one refresh loop may ever run at a time — bump the token so any
    # previously scheduled loop (from an earlier visit to this tab) sees a
    # mismatch and stops itself instead of stacking up.
    self._chat_refresh_token = getattr(self, "_chat_refresh_token", 0) + 1
    self.after(4000, lambda token=self._chat_refresh_token: self._chat_auto_refresh(token))

  def _chat_auto_refresh(self, token):
    if token != getattr(self, "_chat_refresh_token", None):
      return  # a newer loop has taken over; this one stops here
    if getattr(self, "current_tab", None) != "Chat":
      return
    try:
      self._load_chat_contacts()
      if self.chat_active_contact:
        self._render_chat_conversation_area(preserve_scroll=True)
      self._update_decision_badge()
    except Exception:
      pass
    self.after(4000, lambda: self._chat_auto_refresh(token))

  def _load_chat_contacts(self, force=False):
    contacts = ChatManager.get_contacts(self.user.get("username", ""), self.role)
    snapshot = tuple(
        (c["username"], c["unread_count"], c["last_message_time"], self.chat_active_contact == c["username"])
        for c in contacts
    )
    if not force and snapshot == getattr(self, "_chat_contacts_snapshot", None):
      return  # nothing changed — skip the rebuild to avoid flicker
    self._chat_contacts_snapshot = snapshot

    for child in self.chat_contacts_scroll.winfo_children():
      child.destroy()

    if not contacts:
      ctk.CTkLabel(
          self.chat_contacts_scroll, text="No contacts available for your role.",
          font=FONT_SMALL, text_color=COLOR_TEXT_MUTED, wraplength=250,
      ).pack(pady=20, padx=10)
      return

    for c in contacts:
      is_active = self.chat_active_contact == c["username"]
      row_color = COLOR_PRIMARY_SEA_GREEN if is_active else COLOR_CARD_BG
      text_color_main = COLOR_TEXT_LIGHT if is_active else COLOR_TEXT_DARK

      row = ctk.CTkFrame(self.chat_contacts_scroll, fg_color=row_color, corner_radius=8, height=58, cursor="hand2")
      row.pack(fill="x", padx=5, pady=3)
      row.pack_propagate(False)

      inner = ctk.CTkFrame(row, fg_color="transparent")
      inner.pack(fill="both", expand=True, padx=12, pady=6)

      name_row = ctk.CTkFrame(inner, fg_color="transparent")
      name_row.pack(fill="x")
      name_lbl = ctk.CTkLabel(
          name_row, text=f"{c['name']} ({c['role']})", font=(FONT_BODY[0], 12, "bold"),
          text_color=text_color_main, anchor="w",
      )
      name_lbl.pack(side="left")

      widgets_to_bind = [row, inner, name_row, name_lbl]

      if c["unread_count"] > 0:
        unread_lbl = ctk.CTkLabel(
            name_row, text=str(c["unread_count"]), font=(FONT_SMALL[0], 9, "bold"), text_color="white",
            fg_color=COLOR_PINK, corner_radius=10, width=20, height=20,
        )
        unread_lbl.pack(side="right")
        widgets_to_bind.append(unread_lbl)

      preview = (c["last_message"] or "No messages yet")[:38]
      preview_lbl = ctk.CTkLabel(
          inner, text=preview, font=FONT_SMALL,
          text_color=text_color_main if is_active else COLOR_TEXT_MUTED, anchor="w",
      )
      preview_lbl.pack(fill="x")
      widgets_to_bind.append(preview_lbl)

      # Clicking anywhere on the row (not just the button's exposed edge)
      # opens the conversation — bind every child widget, not just the frame.
      for w in widgets_to_bind:
        w.bind("<Button-1>", lambda e, u=c["username"]: self._open_chat_conversation(u))

  def _open_chat_conversation(self, username):
    self.chat_active_contact = username
    ChatManager.mark_conversation_read(self.user.get("username", ""), username)
    self._load_chat_contacts()
    self._render_chat_conversation_area()
    self._update_decision_badge()

  def _render_chat_conversation_area(self, preserve_scroll=False):
    if not self.chat_active_contact:
      for child in self.chat_right_panel.winfo_children():
        child.destroy()
      ctk.CTkLabel(
          self.chat_right_panel, text="Select a conversation to start chatting.",
          font=FONT_BODY, text_color=COLOR_TEXT_MUTED,
      ).pack(expand=True)
      self._chat_messages_snapshot = None
      return

    my_username = self.user.get("username", "")
    messages = ChatManager.get_conversation(my_username, self.chat_active_contact, my_username)
    snapshot = (
        self.chat_active_contact,
        tuple((m["message_id"], m["message"], m["edited"]) for m in messages),
    )
    if preserve_scroll and snapshot == getattr(self, "_chat_messages_snapshot", None):
      return  # nothing new in this conversation — skip rebuild to avoid flicker
    self._chat_messages_snapshot = snapshot

    for child in self.chat_right_panel.winfo_children():
      child.destroy()

    contacts = {c["username"]: c for c in ChatManager.get_contacts(self.user.get("username", ""), self.role)}
    contact = contacts.get(self.chat_active_contact)
    contact_name = contact["name"] if contact else self.chat_active_contact
    contact_role = contact["role"] if contact else ""

    self.chat_right_panel.grid_rowconfigure(1, weight=1)
    self.chat_right_panel.grid_columnconfigure(0, weight=1)

    header = ctk.CTkFrame(self.chat_right_panel, fg_color=COLOR_SILVER_BG, corner_radius=10, height=55)
    header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    ctk.CTkLabel(
        header, text=f"  {contact_name}  ({contact_role})", font=FONT_SUBHEADER, text_color=COLOR_TEXT_DARK,
    ).pack(anchor="w", pady=12)

    messages_scroll = ctk.CTkScrollableFrame(self.chat_right_panel, fg_color="transparent")
    messages_scroll.grid(row=1, column=0, sticky="nsew", padx=10)

    for m in messages:
      is_mine = m["sender_username"] == my_username
      bubble_wrap = ctk.CTkFrame(messages_scroll, fg_color="transparent")
      bubble_wrap.pack(fill="x", pady=4)

      bubble = ctk.CTkFrame(
          bubble_wrap,
          fg_color=COLOR_PRIMARY_SEA_GREEN if is_mine else COLOR_SILVER_BG,
          corner_radius=12,
      )
      bubble.pack(side="right" if is_mine else "left", padx=10, anchor="e" if is_mine else "w")

      text_color = COLOR_TEXT_LIGHT if is_mine else COLOR_TEXT_DARK

      if m.get("attachment_path") and os.path.exists(m["attachment_path"]):
        if m.get("attachment_type") == "image":
          try:
            img = Image.open(m["attachment_path"])
            img.thumbnail((220, 220))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            img_lbl = ctk.CTkLabel(bubble, image=ctk_img, text="")
            img_lbl.pack(padx=8, pady=(8, 2))
            img_lbl.bind("<Button-1>", lambda e, p=m["attachment_path"]: self._open_file_external(p))
          except Exception:
            ctk.CTkLabel(bubble, text="📎 (image unavailable)", text_color=text_color).pack(padx=10, pady=6)
        else:
          fname = os.path.basename(m["attachment_path"])
          file_btn = ctk.CTkButton(
              bubble, text=f"📎 {fname}", fg_color="transparent", text_color=text_color,
              hover=False, anchor="w", command=lambda p=m["attachment_path"]: self._open_file_external(p),
          )
          file_btn.pack(padx=6, pady=(6, 0))

      if m.get("message"):
        msg_text = m["message"] + ("  (edited)" if m.get("edited") else "")
        ctk.CTkLabel(
            bubble, text=msg_text, font=FONT_BODY, text_color=text_color,
            wraplength=340, justify="left", anchor="w",
        ).pack(padx=10, pady=(6, 2), anchor="w")

      time_str = m["sent_at"].split(" ")[1][:5] if " " in m["sent_at"] else m["sent_at"]
      footer_row = ctk.CTkFrame(bubble, fg_color="transparent")
      footer_row.pack(fill="x", padx=10, pady=(0, 6))
      ctk.CTkLabel(footer_row, text=time_str, font=(FONT_SMALL[0], 8), text_color=text_color).pack(side="left")

      if is_mine and m.get("message"):
        ctk.CTkButton(
            footer_row, text="✏️", width=22, height=18, fg_color="transparent", hover=False,
            command=lambda mid=m["message_id"], cur=m["message"]: self._chat_edit_message(mid, cur),
        ).pack(side="right", padx=(4, 0))
      ctk.CTkButton(
          footer_row, text="🗑️", width=22, height=18, fg_color="transparent", hover=False,
          command=lambda mid=m["message_id"]: self._chat_delete_message(mid),
      ).pack(side="right")

    if not preserve_scroll:
      def _scroll_to_bottom():
        try:
          messages_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
          pass
      self.after(50, _scroll_to_bottom)

    # Input bar
    input_bar = ctk.CTkFrame(self.chat_right_panel, fg_color="transparent")
    input_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
    input_bar.grid_columnconfigure(0, weight=1)

    self.chat_input_entry = ctk.CTkEntry(input_bar, placeholder_text="Type a message...", height=42)
    self.chat_input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    self.chat_input_entry.bind("<Return>", lambda e: self._chat_send())

    ctk.CTkButton(input_bar, text="📎", width=42, height=42, fg_color=COLOR_BLUE, command=self._chat_pick_attachment).grid(row=0, column=1, padx=(0, 8))
    ctk.CTkButton(input_bar, text="Send", width=80, height=42, fg_color=COLOR_PRIMARY_SEA_GREEN, command=self._chat_send).grid(row=0, column=2)

  def _open_file_external(self, path):
    try:
      if sys.platform == "win32":
        os.startfile(path)
      elif sys.platform == "darwin":
        subprocess.call(["open", path])
      else:
        subprocess.call(["xdg-open", path])
    except Exception as e:
      CustomDialog(self, title="Open File", message=f"Could not open file: {str(e)}", dialog_type="warning")

  def _chat_pick_attachment(self):
    path = filedialog.askopenfilename(title="Select an image or file to send")
    if path:
      self.chat_pending_attachment = path
      self._chat_send()

  def _chat_send(self):
    message = self.chat_input_entry.get().strip()
    attachment = self.chat_pending_attachment
    if not message and not attachment:
      return

    contacts = {c["username"]: c for c in ChatManager.get_contacts(self.user.get("username", ""), self.role)}
    contact = contacts.get(self.chat_active_contact)
    if not contact:
      CustomDialog(self, title="Send Message", message="This contact is no longer available.", dialog_type="warning")
      return

    res = ChatManager.send_message(
        sender_username=self.user.get("username", ""),
        sender_role=self.role,
        receiver_username=self.chat_active_contact,
        receiver_role=contact["role"],
        message=message,
        attachment_source_path=attachment,
    )
    if res["success"]:
      self.chat_input_entry.delete(0, "end")
      self.chat_pending_attachment = None
      self._load_chat_contacts()
      self._render_chat_conversation_area()
    else:
      CustomDialog(self, title="Send Message", message=res["message"], dialog_type="warning")

  def _chat_edit_message(self, message_id, current_text):
    win, body, footer = self._build_scrollable_dialog("Edit Message", width=380, height=220)
    ctk.CTkLabel(body, text="Message", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(10, 2))
    entry = ctk.CTkEntry(body, height=38)
    entry.pack(fill="x", padx=20)
    entry.insert(0, current_text)

    def save():
      res = ChatManager.edit_message(message_id, self.user.get("username", ""), entry.get().strip())
      if res["success"]:
        win.destroy()
        self._render_chat_conversation_area()
      else:
        CustomDialog(self, title="Edit Message", message=res["message"], dialog_type="warning")

    ctk.CTkButton(footer, text="Save", height=38, fg_color=COLOR_PRIMARY_SEA_GREEN, command=save).pack(fill="x", padx=20, pady=15)

  def _chat_delete_message(self, message_id):
    def confirm_delete():
      res = ChatManager.delete_message_for_me(message_id, self.user.get("username", ""))
      if res["success"]:
        self._render_chat_conversation_area()
      else:
        CustomDialog(self, title="Delete Message", message=res["message"], dialog_type="warning")

    CustomDialog(
        self, title="Delete Message",
        message="Delete this message for you? The other person will still see it, just like WhatsApp's 'Delete for me'.",
        dialog_type="confirm", on_confirm=confirm_delete,
    )

  # --------------------------------------------------------------------------
  # 9. SETTINGS MODULE
  # --------------------------------------------------------------------------
  def _render_settings_module(self, parent):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    card = ctk.CTkScrollableFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12)
    card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    ctk.CTkLabel(
        card, text="Role Visibility Controls", font=FONT_HEADER
    ).pack(anchor="w", padx=20, pady=15)

    if self.role == "admin":
      ctk.CTkLabel(
          card,
          text="Admin Permission Manager (Toggle Modules for Roles):",
          font=FONT_SUBHEADER,
      ).pack(anchor="w", padx=20, pady=(10, 5))
      # store checkbox variables so admin can review and save in one action
      self.role_permission_vars = {}
      for role_name in ["Librarian", "Staff"]:
        frame = ctk.CTkFrame(card, fg_color=COLOR_SILVER_BG)
        frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(
            frame, text=f"Role: {role_name}", font=(FONT_BODY[0], 11, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        permissions = SettingsManager.get_role_permissions(role_name.lower())
        self.role_permission_vars[role_name.lower()] = {}
        for mod in ["Dashboard", "Decision Engine", "Books", "Issue/Return", "Attendance", "Staff", "Analytics", "Reports", "Chat", "Settings"]:
          chk_var = ctk.IntVar(value=1 if permissions.get(mod, True) else 0)
          self.role_permission_vars[role_name.lower()][mod] = chk_var
          cb = ctk.CTkCheckBox(
            frame,
            text=mod,
            variable=chk_var,
          )
          cb.pack(anchor="w", padx=10, pady=4)

      # Save permissions button to batch-persist chosen toggles
      ctk.CTkButton(
        card,
        text="Save Permissions",
        fg_color=COLOR_PRIMARY_SEA_GREEN,
        command=self._save_role_permissions,
      ).pack(anchor="e", padx=20, pady=(8, 20))
    else:
      ctk.CTkLabel(
          card,
          text="Only an Administrator can change module visibility settings.",
          font=FONT_SMALL,
          text_color=COLOR_TEXT_MUTED,
          wraplength=600,
      ).pack(anchor="w", padx=20, pady=(10, 20))

  def _save_role_permissions(self):
    if not hasattr(self, "role_permission_vars"):
      CustomDialog(self, title="Save Permissions", message="No permission changes to save.", dialog_type="warning")
      return

    failures = []
    for role, mods in self.role_permission_vars.items():
      for mod, var in mods.items():
        try:
          SettingsManager.update_role_permission(role, mod, var.get())
        except Exception as e:
          failures.append(f"{role}:{mod} -> {str(e)}")

    if failures:
      CustomDialog(self, title="Save Permissions", message="Some permissions failed to save.", dialog_type="warning")
    else:
      CustomDialog(self, title="Save Permissions", message="Role permissions saved successfully!", dialog_type="success")

  def _confirm_logout(self):
    CustomDialog(
        self,
        title="Logout Confirmation",
        message="Are you sure you want to log out of the system?",
        dialog_type="confirm",
        on_confirm=self.on_logout,
    )