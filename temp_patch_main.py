from pathlib import Path

p = Path('main.py')
text = p.read_text(encoding='utf-8')
text = text.replace(
    'from database.db_manager import db\nfrom modules.settings import SettingsManager\nfrom views.dashboard_view import DashboardView\nfrom views.login_view import LoginView\n',
    'from database.db_manager import db\nfrom modules.auth import AuthManager\nfrom modules.settings import SettingsManager\nfrom views.dashboard_view import DashboardView\nfrom views.login_view import LoginView\n'
)
text = text.replace(
    'if __name__ == "__main__":\n    # Ensure database structure & settings are ready before GUI launch\n    db.initialize_database()\n    SettingsManager.initialize_settings_table()\n\n    app = LibraryManagementApp()\n    app.mainloop()\n',
    'if __name__ == "__main__":\n    # Ensure database structure, auth users, and settings are ready before GUI launch\n    db.initialize_database()\n    SettingsManager.initialize_settings_table()\n    AuthManager.initialize_users_table()\n\n    app = LibraryManagementApp()\n    app.mainloop()\n'
)
p.write_text(text, encoding='utf-8')
print('patched')
