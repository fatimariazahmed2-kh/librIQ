import customtkinter as ctk
from config import (
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_PRIMARY_SEA_GREEN,
    COLOR_SEA_GREEN_HOVER,
    COLOR_SILVER_BG,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_LIGHT,
    FONT_BODY,
    FONT_HEADER,
    FONT_SMALL,
    FONT_SUBHEADER,
)
from modules.auth import AuthManager


class LoginView(ctk.CTkFrame):

  def __init__(self, parent, on_login_success):
    super().__init__(parent, fg_color=COLOR_SILVER_BG)
    self.on_login_success = on_login_success

    # Grid Configuration for 2-Panel Split (Left Form 45%, Right Hero 55%)
    self.grid_columnconfigure(0, weight=4, uniform="split")
    self.grid_columnconfigure(1, weight=5, uniform="split")
    self.grid_rowconfigure(0, weight=1)

    self._setup_left_panel()
    self._setup_right_panel()

  def _setup_left_panel(self):
    """Creates the clean, modern login form panel on the left."""
    self.left_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=0)
    self.left_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

    # Inner container for center alignment
    inner = ctk.CTkFrame(self.left_frame, fg_color="transparent")
    inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8)

    # Title & Subtitle
    title_label = ctk.CTkLabel(
        inner,
        text="Welcome Back",
        font=FONT_HEADER,
        text_color=COLOR_TEXT_DARK,
        anchor="w",
    )
    title_label.pack(fill="x", pady=(0, 4))

    sub_label = ctk.CTkLabel(
        inner,
        text="Sign in to access your Library System",
        font=FONT_BODY,
        text_color=COLOR_TEXT_MUTED,
        anchor="w",
    )
    sub_label.pack(fill="x", pady=(0, 25))

    # Role Selector (Segmented Button)
    role_label = ctk.CTkLabel(
        inner,
        text="SELECT ROLE",
        font=FONT_SMALL,
        text_color=COLOR_TEXT_MUTED,
        anchor="w",
    )
    role_label.pack(fill="x", pady=(0, 5))

    self.role_var = ctk.StringVar(value="Admin")
    self.role_selector = ctk.CTkSegmentedButton(
        inner,
        values=["Admin", "Librarian", "Staff"],
        variable=self.role_var,
        selected_color=COLOR_PRIMARY_SEA_GREEN,
        selected_hover_color=COLOR_SEA_GREEN_HOVER,
        unselected_color="#E2E8F0",
        unselected_hover_color="#CBD5E1",
        text_color=COLOR_TEXT_DARK,
        height=38,
        font=(FONT_BODY[0], 11, "bold"),
    )
    self.role_selector.pack(fill="x", pady=(0, 20))

    # Username Field
    user_label = ctk.CTkLabel(
        inner,
        text="USERNAME",
        font=FONT_SMALL,
        text_color=COLOR_TEXT_MUTED,
        anchor="w",
    )
    user_label.pack(fill="x", pady=(0, 5))

    self.username_entry = ctk.CTkEntry(
        inner,
        placeholder_text="Enter your username",
        height=45,
        corner_radius=8,
        border_color=COLOR_BORDER,
        font=FONT_BODY,
    )
    self.username_entry.pack(fill="x", pady=(0, 15))

    # Password Field
    pass_label = ctk.CTkLabel(
        inner,
        text="PASSWORD",
        font=FONT_SMALL,
        text_color=COLOR_TEXT_MUTED,
        anchor="w",
    )
    pass_label.pack(fill="x", pady=(0, 5))

    self.password_entry = ctk.CTkEntry(
        inner,
        placeholder_text="Enter your password",
        show="•",
        height=45,
        corner_radius=8,
        border_color=COLOR_BORDER,
        font=FONT_BODY,
    )
    self.password_entry.pack(fill="x", pady=(0, 20))

    # Feedback / Message Label
    self.msg_label = ctk.CTkLabel(
        inner, text="", font=FONT_SMALL, text_color="#E53E3E", anchor="w"
    )
    self.msg_label.pack(fill="x", pady=(0, 10))

    # Login Button
    self.login_btn = ctk.CTkButton(
        inner,
        text="LOGIN",
        font=(FONT_BODY[0], 13, "bold"),
        fg_color=COLOR_PRIMARY_SEA_GREEN,
        hover_color=COLOR_SEA_GREEN_HOVER,
        text_color=COLOR_TEXT_LIGHT,
        height=45,
        corner_radius=8,
        command=self._handle_login,
    )
    self.login_btn.pack(fill="x", pady=(0, 15))

  def _setup_right_panel(self):
    """Creates the right visual panel with custom Sea Green theme matching Image 1."""
    self.right_frame = ctk.CTkFrame(
        self, fg_color=COLOR_PRIMARY_SEA_GREEN, corner_radius=0
    )
    self.right_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

    center_container = ctk.CTkFrame(self.right_frame, fg_color="transparent")
    center_container.place(relx=0.5, rely=0.5, anchor="center")

    # Icon Placeholder / Branding Badge
    brand_badge = ctk.CTkFrame(
        center_container,
        fg_color="white",
        width=100,
        height=100,
        corner_radius=20,
    )
    brand_badge.pack(pady=(0, 20))
    brand_badge.pack_propagate(False)

    badge_icon = ctk.CTkLabel(
        brand_badge,
        text="📚",
        font=("Segoe UI Emoji", 48),
        text_color=COLOR_PRIMARY_SEA_GREEN,
    )
    badge_icon.place(relx=0.5, rely=0.5, anchor="center")

    # Main Branding Titles
    app_title = ctk.CTkLabel(
        center_container,
        text="Smart Library System",
        font=("Segoe UI", 26, "bold"),
        text_color=COLOR_TEXT_LIGHT,
    )
    app_title.pack(pady=(0, 5))

    app_desc = ctk.CTkLabel(
        center_container,
        text="Enterprise Data-Driven Automation & Analytics",
        font=FONT_SUBHEADER,
        text_color="#E0F2FE",
    )
    app_desc.pack(pady=(0, 0))

  def _handle_login(self):
    role = self.role_var.get()
    username = self.username_entry.get().strip()
    password = self.password_entry.get().strip()

    if not username or not password:
      self.msg_label.configure(
          text="Please enter both username and password.", text_color="#E53E3E"
      )
      return

    result = AuthManager.authenticate(role, username, password)

    if result["success"]:
      self.msg_label.configure(
          text="Login successful! Redirecting...", text_color="#38A169"
      )
      # Trigger callback to launch main application with logged-in user details
      self.after(500, lambda: self.on_login_success(result["user"]))
    else:
      self.msg_label.configure(text=result["message"], text_color="#E53E3E")