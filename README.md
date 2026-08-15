# LibrIQ — Smart Data-Driven Library Management System

> *A library management system that doesn't just track books — it makes decisions.*

A full-featured desktop application for managing library operations, built around a real-time **Decision Engine** that automatically surfaces operational recommendations from live data — instead of just storing records.

---

## ✨ Features

### 📚 Core Management
- **Books** — full CRUD, search, category/quantity tracking, automatic Excel backup
- **Issue / Return** — book issuance, return processing, automatic overdue detection & fine calculation
- **Attendance** — student check-in/check-out logging with edit support
- **Staff** — role-based staff account management (Admin / Librarian / Staff)

### 🧠 Decision Engine
Event-driven rule engine that evaluates live data and raises recommendations — no manual monitoring required:
- Low book stock alerts
- High-demand book detection
- Overdue return patterns by department
- Fine-threshold borrowing freezes
- Occupancy-based facility suggestions (off-peak / peak hours)
- Dead-stock and usage-pattern detection

Every recommendation must be **Approved** or **Ignored** by a human — the engine informs decisions, it doesn't make them. Unresolved items stay flagged until reviewed, similar to a notification badge.

### 📊 Analytics
Live, auto-refreshing charts: peak check-in trends, most-borrowed titles, fine collection status, and department-wise usage — generated directly from current data, not a cached snapshot.

### 💬 Internal Chat
WhatsApp-style internal messaging between Admin, Librarian, and Staff — text, image/file attachments, edit, and delete-for-me, with role-based permissions.

### 📄 Reports
Auto-generated period reports (daily/weekly/monthly/yearly) with a matching premium Word (.docx) export.

### ⚙️ Settings
Admin-controlled role-based module visibility and access permissions.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| GUI | CustomTkinter |
| Database | SQLite |
| Data Export | Pandas, OpenPyXL |
| Charts | Matplotlib |
| Word Export | python-docx |
| Images | Pillow |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ installed

### Installation
```bash
git clone https://github.com/YOUR-USERNAME/libriq.git
cd libriq
pip install -r requirements.txt
```

## run
```bash
py main.py
```

On first launch, the database and default Admin/Librarian accounts are created automatically.

---

## 📁 Project Structure
```
libriq/
├── main.py                 # Application entry point
├── config.py                # Theme, colors, fonts
├── database/                 # SQLite connection & schema
├── modules/                   # Business logic (books, students, staff, chat, decision engine...)
├── views/                      # UI screens (dashboard, login, components)
├── utils/                       # Excel/Word export, decision engine rules
└── data/                        # SQLite DB & generated backups (not tracked in git)
```

---

🖼 Screenshots
<img width="960" height="488" alt="image" src="https://github.com/user-attachments/assets/e4bef919-7475-4263-8180-829fc3dba4a1" />



<img width="957" height="487" alt="image" src="https://github.com/user-attachments/assets/7690c6c7-792f-4eae-9b40-fd7cbdbfb38c" />



<img width="960" height="483" alt="image" src="https://github.com/user-attachments/assets/d6db3c19-df4c-4682-9409-ade26e261636" />



<img width="928" height="480" alt="image" src="https://github.com/user-attachments/assets/862bfc5c-15d3-46ae-bb38-10fcf76c54f5" />



---

## 📌 Roadmap
- [ ] Multi-branch/library support
- [ ] Predictive demand forecasting for high-turnover titles
- [ ] Web-based version

---

## 📄 License

This project is open source — feel free to fork and adapt it for your own institution.

---

## 👤 Author

Built by Mehak Fatima — https://www.linkedin.com/in/mehakfatimariazahmed?utm_source=share_via&utm_content=profile&utm_medium=member_android ·
