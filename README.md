# 🏫 School Management Portal

A full-featured, desktop-friendly Streamlit web application designed for managing student and teacher records, tracking custom fee payment schedules, and generating printable/downloadable payment receipts.

---

## ✨ Features

* **🔐 Custom Setup & Authentication**: First-time registration locks down your Admin Register ID, Password, School Name, and Authority Signatory. Subsequent runs automatically route users to the login screen.
* **🎓 Student Management**:
  * Auto-assign unique registration numbers (`Reg No`).
  * Enforce class-level uniqueness for student roll numbers.
  * Store and update student records, address, bus numbers, and profile photos.
* **💳 Fee Dashboard & Cascade Payments**:
  * Track monthly tuition fees dynamically across academic sessions.
  * Pay customized amounts that automatically cascade through pending monthly installments.
  * Visualize fee breakdowns (Paid, Due, Balance) using interactive Plotly charts.
* **🧾 Receipts & Timestamping**:
  * Printable HTML receipts with authorized signatory signatures and exact system timestamps (`HH:MM:SS AM/PM`).
  * Export receipts to plain text (`.txt`) files.
* **👨‍🏫 Teacher Management**:
  * Auto-assign Teacher IDs.
  * Manage teacher profiles, subject assignments, assigned classes, and contact details.
* **📥 CSV Data Export**: Export complete student and teacher lists directly to CSV format.

---

## 🛠️ Tech Stack

* **Frontend/UI**: [Streamlit](https://streamlit.io/)
* **Database**: SQLite3
* **Data Processing & Visualization**: Pandas, Plotly
* **Receipt Rendering**: HTML/CSS embedded via Streamlit Components

---

## 🚀 Getting Started

### Prerequisites

Ensure you have Python 3.8+ installed on your system.

### Installation

1. **Clone the repository or download the project files**:
   ```bash
   git clone [https://github.com/your-username/school-management-portal.git](https://github.com/your-username/school-management-portal.git)
   cd school-management-portal
   pip install streamlit pandas plotly
   streamlit run app.py
📖 Usage Workflow
1. First-Time Setup:

Open the app in your browser.

Fill in the Admin Register ID, Password, School Name, and Authority Signatory Title.

Click Register & Initialize Portal to lock in your credentials.

2. Login:

Log in using your registered Admin credentials.

3. Manage Students & Fees:

Navigate to the Student tab to register new students or modify existing profiles.

Access the My Fees tab under a student's profile to record fee payments or print receipts.

4. Manage Teachers:

Switch to the Teacher tab to add new faculty, assign subjects/classes, or export the teacher directory.

🗄️ Database Structure
The application automatically initializes an SQLite3 database (school_data.db) containing the following tables:

school_info: Stores login credentials, school name, and signatory details.

students: Stores student demographic and profile data.

teachers: Stores faculty records and class assignments.

student_fees: Stores monthly installment breakdowns per student and session.

fee_payments: Stores payment transactions, receipt numbers, dates, and exact timestamps.

📄 License
This project is open-source and available under the MIT License.
