import customtkinter as ctk
from config import COLOR_SILVER_BG
from database.db_manager import db
from modules.auth import AuthManager
from modules.settings import SettingsManager
from views.dashboard_view import DashboardView
from views.login_view import LoginView

# Global CustomTkinter Application Configurations
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class LibraryManagementApp(ctk.CTk):
    """Main application controller managing window state and views."""
    def __init__(self):
        super().__init__()
        # Window Setup — size to the user's actual screen so nothing is ever
        # cut off on smaller laptop displays, instead of a fixed 1280x760.
        self.title("Smart Data-Driven Library Management System")
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1280, int(screen_w * 0.92))
        win_h = min(760, int(screen_h * 0.88))
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(min(900, screen_w - 40), min(600, screen_h - 80))
        self.configure(fg_color=COLOR_SILVER_BG)

        # CustomTkinter buttons schedule internal hover/animation callbacks via
        # after(); if a dialog is closed quickly those can fire on an
        # already-destroyed widget. This is a known, harmless CTk library
        # quirk (it doesn't affect data or app state) — suppress just the
        # console noise instead of letting it spam the terminal.
        def _quiet_callback_exception_handler(exc_type, exc_value, exc_traceback):
            if exc_type is __import__("tkinter").TclError and "bad window path name" in str(exc_value):
                return
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback)
        self.report_callback_exception = _quiet_callback_exception_handler

        # Current logged in user object
        self.current_user = None
        
        # Load initial Login Screen
        self.show_login_view()

    def show_login_view(self):
        """Destroys current view and displays the Login screen."""
        self._clear_views()
        self.current_user = None
        self.login_view = LoginView(self, on_login_success=self.on_login_success)
        self.login_view.pack(fill="both", expand=True)

    def on_login_success(self, user: dict):
        """Callback triggered upon successful authentication."""
        self.current_user = user
        self.show_dashboard_view()

    def show_dashboard_view(self):
        """Destroys login screen and launches the main enterprise dashboard."""
        self._clear_views()
        self.dashboard_view = DashboardView(
            self, user=self.current_user, on_logout=self.show_login_view
        )
        self.dashboard_view.pack(fill="both", expand=True)

    def _clear_views(self):
        """Clears active frame components from root application window."""
        for child in self.winfo_children():
            child.destroy()

if __name__ == "__main__":
    # Ensure database structure & settings are ready before GUI launch
    db.initialize_database()
    SettingsManager.initialize_settings_table()
    AuthManager.initialize_users_table()

    app = LibraryManagementApp()
    app.mainloop()