import customtkinter as ctk
from tkinter import messagebox
from modules.auth import AuthManager
from modules.settings import SettingsManager

class SettingsView(ctk.CTkFrame):
    """Interactive Settings module UI that drives system behavior and security."""

    def __init__(self, parent, user: dict):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        self.settings = SettingsManager.get_all_settings()

        # Layout Split: Left (System Rules & Appearance), Right (Password & Security)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_rules_and_theme_panel()
        self._build_security_panel()

    def _build_rules_and_theme_panel(self):
        # Use a scrollable frame so long settings content can be scrolled on small windows
        panel = ctk.CTkScrollableFrame(self, corner_radius=12, fg_color=("#F8F9FA", "#2B2B2B"))
        panel.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        title = ctk.CTkLabel(panel, text="⚙️ System Rules & Preferences", font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w", padx=20, pady=(20, 15))

        # 1. Theme Appearance
        ctk.CTkLabel(panel, text="App Theme Mode:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
        self.theme_var = ctk.StringVar(value=self.settings.get("app_theme", "Light"))
        theme_dropdown = ctk.CTkOptionMenu(
            panel, values=["Light", "Dark", "System"], variable=self.theme_var
        )
        theme_dropdown.pack(fill="x", padx=20, pady=(0, 15))

        # 2. Fine Rate Per Day
        ctk.CTkLabel(panel, text="Fine Charge Per Day (PKR):", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
        self.fine_entry = ctk.CTkEntry(panel, placeholder_text="e.g. 100")
        self.fine_entry.insert(0, self.settings.get("fine_per_day", "100.0"))
        self.fine_entry.pack(fill="x", padx=20, pady=(0, 15))

        # 3. Maximum Books Per Student
        ctk.CTkLabel(panel, text="Max Books Allowed Per Student:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
        self.max_books_entry = ctk.CTkEntry(panel, placeholder_text="e.g. 3")
        self.max_books_entry.insert(0, self.settings.get("max_books_per_student", "3"))
        self.max_books_entry.pack(fill="x", padx=20, pady=(0, 15))

        # 4. Default Issue Duration (Days)
        ctk.CTkLabel(panel, text="Default Issue Duration (Days):", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
        self.days_entry = ctk.CTkEntry(panel, placeholder_text="e.g. 7")
        self.days_entry.insert(0, self.settings.get("default_issue_days", "7"))
        self.days_entry.pack(fill="x", padx=20, pady=(0, 20))

        # Save Button
        save_btn = ctk.CTkButton(
            panel, text="💾 Save & Apply System Rules", fg_color="#107C41", hover_color="#0B5A2F",
            height=40, font=("Segoe UI", 13, "bold"), command=self._save_system_settings
        )
        save_btn.pack(fill="x", padx=20, pady=10)

    def _build_security_panel(self):
        panel = ctk.CTkScrollableFrame(self, corner_radius=12, fg_color=("#F8F9FA", "#2B2B2B"))
        panel.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")

        title = ctk.CTkLabel(panel, text="🔒 Password & Account Security", font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w", padx=20, pady=(20, 15))

        # User Info Label
        user_info = f"Logged in as: {self.user.get('username', 'N/A')} ({self.user.get('role', 'User').capitalize()})"
        ctk.CTkLabel(panel, text=user_info, font=("Segoe UI", 12, "italic"), text_color="gray").pack(anchor="w", padx=20, pady=(0, 15))

        if self.user.get('role', '').lower() in ('admin', 'librarian'):
            ctk.CTkLabel(panel, text="Account Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
            self.name_entry = ctk.CTkEntry(panel, placeholder_text="Enter account name")
            self.name_entry.insert(0, self.user.get('name', self.user.get('username', '')))
            self.name_entry.pack(fill="x", padx=20, pady=(0, 15))

            update_name_btn = ctk.CTkButton(
                panel,
                text="📝 Update Account Name",
                fg_color="#5B8C6D",
                hover_color="#4C7A5B",
                height=40,
                font=("Segoe UI", 13, "bold"),
                command=self._update_account_name,
            )
            update_name_btn.pack(fill="x", padx=20, pady=(0, 15))
            # Current Password
            ctk.CTkLabel(panel, text="Current Password:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
            self.curr_pass_entry = ctk.CTkEntry(panel, show="*", placeholder_text="Enter current password")
            self.curr_pass_entry.pack(fill="x", padx=20, pady=(0, 15))

            # New Password
            ctk.CTkLabel(panel, text="New Password:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
            self.new_pass_entry = ctk.CTkEntry(panel, show="*", placeholder_text="Enter new password")
            self.new_pass_entry.pack(fill="x", padx=20, pady=(0, 15))

            # Confirm New Password
            ctk.CTkLabel(panel, text="Confirm New Password:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
            self.confirm_pass_entry = ctk.CTkEntry(panel, show="*", placeholder_text="Re-enter new password")
            self.confirm_pass_entry.pack(fill="x", padx=20, pady=(0, 20))

            # Change Password Button
            change_btn = ctk.CTkButton(
                panel, text="🔑 Update Password", fg_color="#0078D4", hover_color="#005A9E",
                height=40, font=("Segoe UI", 13, "bold"), command=self._change_password
            )
            change_btn.pack(fill="x", padx=20, pady=10)

    def _update_account_name(self):
        # Handler for updating display name for admin/librarian accounts
        new_name = self.name_entry.get().strip()
        if not new_name:
            messagebox.showwarning("Validation Error", "Account name cannot be blank.")
            return

        username = self.user.get("username") or self.user.get("staff_id") or self.user.get("email")
        res = AuthManager.update_name(username, new_name)
        if res["success"]:
            messagebox.showinfo("Success", res["message"])
        else:
            messagebox.showerror("Error", res["message"])

    def _save_system_settings(self):
        updated_dict = {
            "app_theme": self.theme_var.get(),
            "fine_per_day": self.fine_entry.get().strip(),
            "max_books_per_student": self.max_books_entry.get().strip(),
            "default_issue_days": self.days_entry.get().strip(),
        }

        res = SettingsManager.update_settings(updated_dict)
        if res["success"]:
            messagebox.showinfo("Settings Saved", res["message"])
        else:
            messagebox.showerror("Error", res["message"])

    def _change_password(self):
        curr_pass = self.curr_pass_entry.get().strip()
        new_pass = self.new_pass_entry.get().strip()
        confirm_pass = self.confirm_pass_entry.get().strip()

        if not curr_pass or not new_pass or not confirm_pass:
            messagebox.showwarning("Validation Error", "Please fill in all password fields.")
            return

        if new_pass != confirm_pass:
            messagebox.showerror("Error", "New Password and Confirm Password do not match!")
            return

        username = self.user.get("username") or self.user.get("staff_id") or self.user.get("email")
        res = AuthManager.change_password(username, curr_pass, new_pass)

        if res["success"]:
            messagebox.showinfo("Success", res["message"])
            self.curr_pass_entry.delete(0, "end")
            self.new_pass_entry.delete(0, "end")
            self.confirm_pass_entry.delete(0, "end")
        else:
            messagebox.showerror("Password Change Failed", res["message"])