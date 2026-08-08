import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

from config import (
    COLOR_BLUE,
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_PINK,
    COLOR_PRIMARY_SEA_GREEN,
    COLOR_SEA_GREEN_HOVER,
    COLOR_SILVER_BG,
    COLOR_TABLE_ROW_ALT,
    COLOR_TEXT_DARK,
    COLOR_TEXT_LIGHT,
    COLOR_TEXT_MUTED,
    FONT_BODY,
    FONT_HEADER,
    FONT_SMALL,
    FONT_SUBHEADER,
)


class StatCard(ctk.CTkFrame):
  """Enterprise statistic card with rounded corners and themed accent badge."""

  def __init__(
      self,
      parent,
      title: str,
      value: str,
      subtext: str = "",
      icon: str = "📊",
      accent_color: str = COLOR_PRIMARY_SEA_GREEN,
      **kwargs,
  ):
    super().__init__(
        parent,
        fg_color=COLOR_CARD_BG,
        corner_radius=12,
        border_width=1,
        border_color=COLOR_BORDER,
        **kwargs,
    )

    self.grid_columnconfigure(0, weight=1)

    # Top layout (Title + Icon Badge)
    top_frame = ctk.CTkFrame(self, fg_color="transparent")
    top_frame.pack(fill="x", padx=16, pady=(14, 4))

    title_label = ctk.CTkLabel(
        top_frame,
        text=title,
        font=FONT_SMALL,
        text_color=COLOR_TEXT_MUTED,
        anchor="w",
    )
    title_label.pack(side="left", fill="x", expand=True)

    icon_badge = ctk.CTkFrame(
        top_frame,
        fg_color=accent_color,
        width=36,
        height=36,
        corner_radius=8,
    )
    icon_badge.pack(side="right")
    icon_badge.pack_propagate(False)

    icon_label = ctk.CTkLabel(
        icon_badge, text=icon, font=("Segoe UI Emoji", 16), text_color="white"
    )
    icon_label.place(relx=0.5, rely=0.5, anchor="center")

    # Main Metric Value
    val_label = ctk.CTkLabel(
        self,
        text=str(value),
        font=("Segoe UI", 22, "bold"),
        text_color=COLOR_TEXT_DARK,
        anchor="w",
    )
    val_label.pack(fill="x", padx=16, pady=(0, 2))

    # Optional Subtext / Trend indicator
    if subtext:
      sub_label = ctk.CTkLabel(
          self,
          text=subtext,
          font=(FONT_SMALL[0], 9, "normal"),
          text_color=accent_color,
          anchor="w",
      )
      sub_label.pack(fill="x", padx=16, pady=(0, 12))
    else:
      ctk.CTkFrame(self, height=8, fg_color="transparent").pack()


class ModernTable(ctk.CTkFrame):
  """Custom styled data grid with alternate row highlighting and smooth scrollbars."""

  def __init__(self, parent, columns: list, **kwargs):
    super().__init__(
        parent,
        fg_color=COLOR_CARD_BG,
        corner_radius=10,
        border_width=1,
        border_color=COLOR_BORDER,
        **kwargs,
    )

    self.columns = columns

    # Configure Tkinter TTK styling
    self.style = ttk.Style()
    self.style.theme_use("clam")

    self.style.configure(
        "Treeview",
        background="#FFFFFF",
        foreground=COLOR_TEXT_DARK,
        rowheight=35,
        fieldbackground="#FFFFFF",
        font=FONT_BODY,
        borderwidth=0,
    )

    self.style.configure(
        "Treeview.Heading",
        background=COLOR_SILVER_BG,
        foreground=COLOR_TEXT_DARK,
        font=(FONT_BODY[0], 10, "bold"),
        borderwidth=0,
        relief="flat",
    )

    self.style.map(
        "Treeview",
        background=[("selected", COLOR_PRIMARY_SEA_GREEN)],
        foreground=[("selected", "#FFFFFF")],
    )

    self.tree = ttk.Treeview(
        self, columns=columns, show="headings", selectmode="browse"
    )

    # Scrollbars integration
    vsb = ctk.CTkScrollbar(self, orientation="vertical", command=self.tree.yview)
    hsb = ctk.CTkScrollbar(
        self, orientation="horizontal", command=self.tree.xview
    )
    self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # Setup Columns
    for col in columns:
      self.tree.heading(col, text=col, anchor="w", command=lambda c=col: self.sort_by_column(c))
      self.tree.column(
          col, anchor="w", width=120, minwidth=80, stretch=tk.YES
      )

    # Grid positioning
    self.tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    vsb.grid(row=0, column=1, sticky="ns", pady=10, padx=(0, 5))
    hsb.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))

    self.grid_rowconfigure(0, weight=1)
    self.grid_columnconfigure(0, weight=1)

    # Alternate row colors configuration
    self.tree.tag_configure("evenrow", background="#FFFFFF")
    self.tree.tag_configure("oddrow", background=COLOR_TABLE_ROW_ALT)

  def insert_row(self, values: list, real_id=None):
    count = len(self.tree.get_children())
    tag = "evenrow" if count % 2 == 0 else "oddrow"
    if real_id is not None:
      return self.tree.insert("", "end", iid=str(real_id), values=values, tags=(tag,))
    return self.tree.insert("", "end", values=values, tags=(tag,))

  def clear_table(self):
    for item in self.tree.get_children():
      self.tree.delete(item)

  def sort_by_column(self, column: str):
    items = [(self.tree.set(child, column), child) for child in self.tree.get_children("")]
    items.sort(key=lambda item: item[0] if item[0] is not None else "", reverse=False)
    for index, (_, child) in enumerate(items):
      self.tree.move(child, "", index)

  def get_selected_row(self):
    selected = self.tree.selection()
    if selected:
      values = self.tree.item(selected[0])["values"]
      # Tkinter/ttk auto-converts numeric-looking cell text back into int/float.
      # Always return plain strings so callers get predictable, consistent types.
      return [str(v) for v in values]
    return None

  def get_selected_id(self):
    """Returns the stable real ID (Treeview iid) for the selected row, which
    stays correct even though the displayed row number is just a sequential
    position (1, 2, 3...) rather than the underlying database ID."""
    selected = self.tree.selection()
    if selected:
      return selected[0]
    return None


class HeaderBar(ctk.CTkFrame):
  """Top header navigation bar with title and active user role badge."""

  def __init__(
      self,
      parent,
      title: str,
      subtitle: str = "",
      current_user: dict = None,
      **kwargs,
  ):
    super().__init__(
        parent, fg_color=COLOR_CARD_BG, height=65, corner_radius=0, **kwargs
    )
    self.pack_propagate(False)

    # Title & Subtitle
    text_frame = ctk.CTkFrame(self, fg_color="transparent")
    text_frame.pack(side="left", padx=20, pady=10)

    title_lbl = ctk.CTkLabel(
        text_frame,
        text=title,
        font=FONT_HEADER,
        text_color=COLOR_TEXT_DARK,
        anchor="w",
    )
    title_lbl.pack(anchor="w")

    if subtitle:
      sub_lbl = ctk.CTkLabel(
          text_frame,
          text=subtitle,
          font=FONT_SMALL,
          text_color=COLOR_TEXT_MUTED,
          anchor="w",
      )
      sub_lbl.pack(anchor="w")

    # Active User Profile Badge
    if current_user:
      user_frame = ctk.CTkFrame(
          self,
          fg_color=COLOR_SILVER_BG,
          corner_radius=20,
          border_width=1,
          border_color=COLOR_BORDER,
      )
      user_frame.pack(side="right", padx=20, pady=10)

      username = current_user.get("username", "User").capitalize()
      role = current_user.get("role", "Staff").upper()

      badge = ctk.CTkLabel(
          user_frame,
          text=f" 👤  {username} ({role}) ",
          font=(FONT_BODY[0], 11, "bold"),
          text_color=COLOR_PRIMARY_SEA_GREEN,
      )
      badge.pack(padx=12, pady=6)


class CustomDialog(ctk.CTkToplevel):
  """Modern modal pop-up dialog for alerts, success toasts, and confirm actions."""

  def __init__(
      self,
      parent,
      title: str = "Notification",
      message: str = "",
      dialog_type: str = "info",
      on_confirm=None,
  ):
    super().__init__(parent)
    self.title(title)
    self.geometry("400x220")
    self.resizable(False, False)
    self.configure(fg_color=COLOR_CARD_BG)

    self.on_confirm = on_confirm
    self.transient(parent)
    self.grab_set()

    # Icon Selection according to alert type
    icons = {
        "info": ("ℹ️", COLOR_BLUE),
        "success": ("✅", COLOR_PRIMARY_SEA_GREEN),
        "warning": ("⚠️", COLOR_PINK),
        "confirm": ("❓", COLOR_PRIMARY_SEA_GREEN),
    }
    icon_str, accent = icons.get(dialog_type, ("ℹ️", COLOR_PRIMARY_SEA_GREEN))

    # Header
    header = ctk.CTkFrame(self, fg_color="transparent")
    header.pack(fill="x", padx=20, pady=(20, 10))

    icon_lbl = ctk.CTkLabel(
        header, text=icon_str, font=("Segoe UI Emoji", 24)
    )
    icon_lbl.pack(side="left", padx=(0, 10))

    title_lbl = ctk.CTkLabel(
        header,
        text=title,
        font=FONT_SUBHEADER,
        text_color=COLOR_TEXT_DARK,
        anchor="w",
    )
    title_lbl.pack(side="left", fill="x")

    # Message text
    msg_lbl = ctk.CTkLabel(
        self,
        text=message,
        font=FONT_BODY,
        text_color=COLOR_TEXT_MUTED,
        wraplength=350,
        justify="left",
    )
    msg_lbl.pack(fill="both", expand=True, padx=20, pady=10)

    # Action Buttons
    btn_frame = ctk.CTkFrame(self, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))

    if dialog_type == "confirm":
      btn_cancel = ctk.CTkButton(
          btn_frame,
          text="Cancel",
          fg_color="#CBD5E1",
          hover_color="#94A3B8",
          text_color=COLOR_TEXT_DARK,
          width=100,
          command=self.destroy,
      )
      btn_cancel.pack(side="right", padx=(10, 0))

      btn_yes = ctk.CTkButton(
          btn_frame,
          text="Confirm",
          fg_color=accent,
          hover_color=COLOR_SEA_GREEN_HOVER,
          width=100,
          command=self._confirm_and_close,
      )
      btn_yes.pack(side="right")
    else:
      btn_ok = ctk.CTkButton(
          btn_frame,
          text="OK",
          fg_color=accent,
          hover_color=COLOR_SEA_GREEN_HOVER,
          width=100,
          command=self.destroy,
      )
      btn_ok.pack(side="right")

  def _confirm_and_close(self):
    if self.on_confirm:
      self.on_confirm()
    self.destroy()