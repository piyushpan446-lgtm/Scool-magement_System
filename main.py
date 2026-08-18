import io
import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# Set up page config
st.set_page_config(
    page_title="School Management Portal",
    page_icon="🏫",
    layout="centered"
)

# --- DATABASE SETUP ---
DB_NAME = "school_data.db"

def init_db():
    """Creates SQLite database tables for auth, school info, fees, salaries, and rate settings."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS school_info (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            admin_id TEXT NOT NULL,
            admin_pass TEXT NOT NULL,
            school_name TEXT NOT NULL,
            authority_name TEXT NOT NULL DEFAULT 'Principal / Admin'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            reg_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            father_name TEXT NOT NULL DEFAULT '',
            mother_name TEXT NOT NULL DEFAULT '',
            grade INTEGER NOT NULL,
            roll_no INTEGER NOT NULL,
            section TEXT NOT NULL,
            address TEXT NOT NULL DEFAULT '',
            bus_no INTEGER DEFAULT NULL,
            photo BLOB
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            classes_taught TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            photo BLOB
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_fee_rates (
            session TEXT NOT NULL,
            installment TEXT NOT NULL,
            amount REAL NOT NULL,
            PRIMARY KEY (session, installment)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_salary_rates (
            session TEXT NOT NULL,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            PRIMARY KEY (session, month)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_no TEXT NOT NULL,
            session TEXT NOT NULL,
            installment TEXT NOT NULL,
            amount REAL NOT NULL,
            paid REAL NOT NULL DEFAULT 0,
            fine REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (reg_no) REFERENCES students(reg_no)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fee_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_no TEXT NOT NULL,
            session TEXT NOT NULL,
            recpt_date TEXT NOT NULL,
            recpt_time TEXT NOT NULL DEFAULT '',
            installment TEXT NOT NULL,
            amount REAL NOT NULL,
            receipt_no TEXT NOT NULL,
            FOREIGN KEY (reg_no) REFERENCES students(reg_no)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT NOT NULL,
            session TEXT NOT NULL,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            paid REAL NOT NULL DEFAULT 0,
            bonus REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salary_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT NOT NULL,
            session TEXT NOT NULL,
            recpt_date TEXT NOT NULL,
            recpt_time TEXT NOT NULL DEFAULT '',
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            receipt_no TEXT NOT NULL,
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def get_saved_school_info():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT admin_id, admin_pass, school_name, authority_name FROM school_info WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row

def save_initial_setup(admin_id, admin_pass, school_name, authority_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO school_info (id, admin_id, admin_pass, school_name, authority_name)
        VALUES (1, ?, ?, ?, ?)
    """, (admin_id, admin_pass, school_name, authority_name))
    conn.commit()
    conn.close()

def get_current_system_session():
    now = datetime.now()
    year = now.year
    if now.month < 4:
        return f"{year-1}-{year}"
    return f"{year}-{year+1}"

def generate_next_student_reg_no():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT reg_no FROM students")
    rows = cursor.fetchall()
    conn.close()
    nums = [int(r) for (r,) in rows if r.isdigit()]
    return str(max(nums) + 1) if nums else "1001"

def generate_next_teacher_id():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT teacher_id FROM teachers")
    rows = cursor.fetchall()
    conn.close()
    nums = [int(t) for (t,) in rows if t.isdigit()]
    return str(max(nums) + 1) if nums else "101"

def check_roll_no_exists_in_grade(grade, roll_no, current_reg_no=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if current_reg_no:
        cursor.execute("SELECT name FROM students WHERE grade = ? AND roll_no = ? AND reg_no != ?", (grade, roll_no, str(current_reg_no)))
    else:
        cursor.execute("SELECT name FROM students WHERE grade = ? AND roll_no = ?", (grade, roll_no))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# --- RATE SETTINGS HELPERS ---
MONTH_LIST = ["APR", "MAY", "JUNE", "JULY", "AUG", "SEP", "OCT", "NOV", "DEC", "JAN", "FEB", "MAR"]

def get_session_fee_rates(session):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT installment, amount FROM student_fee_rates WHERE session = ?", (session,))
    rows = dict(cursor.fetchall())
    conn.close()

    default_rates = [("APR", 18550.0), ("MAY", 5600.0), ("JUNE", 3800.0), ("JULY", 5600.0),
                     ("AUG", 5600.0), ("SEP", 5600.0), ("OCT", 5600.0), ("NOV", 5600.0),
                     ("DEC", 5600.0), ("JAN", 5600.0), ("FEB", 5600.0), ("MAR", 3100.0)]
    
    return {m: rows.get(m, default_amt) for m, default_amt in default_rates}

def set_session_fee_rates(session, rate_dict):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for inst, amt in rate_dict.items():
        cursor.execute("""
            INSERT OR REPLACE INTO student_fee_rates (session, installment, amount)
            VALUES (?, ?, ?)
        """, (session, inst, amt))
        
        cursor.execute("""
            UPDATE student_fees SET amount = ? WHERE session = ? AND installment = ? AND paid = 0
        """, (amt, session, inst))
        
    conn.commit()
    conn.close()

def get_session_salary_rates(session):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT month, amount FROM teacher_salary_rates WHERE session = ?", (session,))
    rows = dict(cursor.fetchall())
    conn.close()

    return {m: rows.get(m, 25000.0) for m in MONTH_LIST}

def set_session_salary_rates(session, rate_dict):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for month, amt in rate_dict.items():
        cursor.execute("""
            INSERT OR REPLACE INTO teacher_salary_rates (session, month, amount)
            VALUES (?, ?, ?)
        """, (session, month, amt))
        
        cursor.execute("""
            UPDATE teacher_salaries SET amount = ? WHERE session = ? AND month = ? AND paid = 0
        """, (amt, session, month))
        
    conn.commit()
    conn.close()

# --- FEE HELPERS ---
def populate_student_fees_for_session(reg_no, session):
    rates = get_session_fee_rates(session)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM student_fees WHERE reg_no = ? AND session = ?", (str(reg_no), session))
    if cursor.fetchone()[0] == 0:
        for m in MONTH_LIST:
            cursor.execute("INSERT INTO student_fees (reg_no, session, installment, amount, paid, fine) VALUES (?, ?, ?, ?, 0, 0)", (str(reg_no), session, m, rates[m]))
    conn.commit()
    conn.close()

def save_student(reg_no, name, father_name, mother_name, grade, roll_no, section, address, bus_no, photo_bytes, active_session):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO students (reg_no, name, father_name, mother_name, grade, roll_no, section, address, bus_no, photo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(reg_no), name, father_name, mother_name, grade, roll_no, section, address, bus_no, photo_bytes))
    conn.commit()
    conn.close()
    populate_student_fees_for_session(reg_no, active_session)

def get_student(reg_no):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT reg_no, name, father_name, mother_name, grade, roll_no, section, address, bus_no, photo FROM students WHERE reg_no = ?", (str(reg_no).strip(),))
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_students():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT reg_no AS 'Reg No', name AS 'Name', father_name AS 'Father Name', mother_name AS 'Mother Name', grade AS 'Grade', roll_no AS 'Roll No', section AS 'Section', address AS 'Address', bus_no AS 'Bus No' FROM students ORDER BY CAST(reg_no AS INTEGER) ASC", conn)
    conn.close()
    return df

def get_student_fee_structure(reg_no, session):
    populate_student_fees_for_session(reg_no, session)
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, installment AS Installment, amount AS Amount, paid AS Paid, fine AS 'Fine/Excess', (amount + fine - paid) AS Balance FROM student_fees WHERE reg_no = ? AND session = ? ORDER BY id ASC", conn, params=(str(reg_no), session))
    conn.close()
    return df

def get_student_payments(reg_no, session):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT receipt_no AS Receipt, recpt_date AS 'Recpt Date', recpt_time AS 'Time', installment AS Installment, amount AS Amount FROM fee_payments WHERE reg_no = ? AND session = ? ORDER BY id DESC", conn, params=(str(reg_no), session))
    conn.close()
    return df

def process_cascade_fee_payment(reg_no, session, start_installment, total_payment):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, installment, amount, paid, fine, (amount + fine - paid) as balance 
        FROM student_fees 
        WHERE reg_no = ? AND session = ? 
        ORDER BY id ASC
    """, (str(reg_no), session))
    rows = cursor.fetchall()
    
    start_index = 0
    for idx, r in enumerate(rows):
        if r[1] == start_installment:
            start_index = idx
            break

    remaining_payment = float(total_payment)
    impacted_installments = []

    for i in range(start_index, len(rows)):
        if remaining_payment <= 0:
            break

        f_id, inst_name, amt, paid, fine, bal = rows[i]
        if bal <= 0:
            continue

        if remaining_payment >= bal:
            payment_for_this = bal
            remaining_payment -= bal
        else:
            payment_for_this = remaining_payment
            remaining_payment = 0

        cursor.execute("UPDATE student_fees SET paid = paid + ? WHERE id = ?", (payment_for_this, f_id))
        impacted_installments.append(inst_name)

    covered_str = f"{impacted_installments[0]}-{impacted_installments[-1]}" if len(impacted_installments) > 1 else impacted_installments[0]
    receipt_no = f"{int(datetime.now().timestamp()) % 10000:04d}"
    today_date = datetime.now().strftime("%d/%m/%Y")
    exact_time = datetime.now().strftime("%I:%M:%S %p")
    
    cursor.execute("""
        INSERT INTO fee_payments (reg_no, session, recpt_date, recpt_time, installment, amount, receipt_no)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (str(reg_no), session, today_date, exact_time, covered_str, total_payment, receipt_no))

    conn.commit()
    conn.close()
    return receipt_no, today_date, exact_time, covered_str

# --- SALARY HELPERS ---
def populate_teacher_salaries_for_session(teacher_id, session):
    rates = get_session_salary_rates(session)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM teacher_salaries WHERE teacher_id = ? AND session = ?", (str(teacher_id), session))
    if cursor.fetchone()[0] == 0:
        for m in MONTH_LIST:
            cursor.execute("INSERT INTO teacher_salaries (teacher_id, session, month, amount, paid, bonus) VALUES (?, ?, ?, ?, 0, 0)", (str(teacher_id), session, m, rates[m]))
    conn.commit()
    conn.close()

def save_teacher(teacher_id, name, subject, classes_taught, address, photo_bytes, active_session=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO teachers (teacher_id, name, subject, classes_taught, address, photo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (str(teacher_id), name, subject, classes_taught, address, photo_bytes))
    conn.commit()
    conn.close()
    if active_session:
        populate_teacher_salaries_for_session(teacher_id, active_session)

def get_teacher(teacher_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT teacher_id, name, subject, classes_taught, address, photo FROM teachers WHERE teacher_id = ?", (str(teacher_id).strip(),))
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_teachers():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT teacher_id AS 'Teacher ID', name AS 'Name', subject AS 'Subject', classes_taught AS 'Classes Taught', address AS 'Address' FROM teachers ORDER BY CAST(teacher_id AS INTEGER) ASC", conn)
    conn.close()
    return df

def get_teacher_salary_structure(teacher_id, session):
    populate_teacher_salaries_for_session(teacher_id, session)
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, month AS Month, amount AS Amount, paid AS Paid, bonus AS 'Bonus/Allowances', (amount + bonus - paid) AS Balance FROM teacher_salaries WHERE teacher_id = ? AND session = ? ORDER BY id ASC", conn, params=(str(teacher_id), session))
    conn.close()
    return df

def get_teacher_salary_payments(teacher_id, session):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT receipt_no AS Voucher, recpt_date AS 'Date', recpt_time AS 'Time', month AS Month, amount AS Amount FROM salary_payments WHERE teacher_id = ? AND session = ? ORDER BY id DESC", conn, params=(str(teacher_id), session))
    conn.close()
    return df

def process_cascade_salary_payment(teacher_id, session, start_month, total_payment):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, month, amount, paid, bonus, (amount + bonus - paid) as balance 
        FROM teacher_salaries 
        WHERE teacher_id = ? AND session = ? 
        ORDER BY id ASC
    """, (str(teacher_id), session))
    rows = cursor.fetchall()
    
    start_index = 0
    for idx, r in enumerate(rows):
        if r[1] == start_month:
            start_index = idx
            break

    remaining_payment = float(total_payment)
    impacted_months = []

    for i in range(start_index, len(rows)):
        if remaining_payment <= 0:
            break

        s_id, m_name, amt, paid, bonus, bal = rows[i]
        if bal <= 0:
            continue

        if remaining_payment >= bal:
            payment_for_this = bal
            remaining_payment -= bal
        else:
            payment_for_this = remaining_payment
            remaining_payment = 0

        cursor.execute("UPDATE teacher_salaries SET paid = paid + ? WHERE id = ?", (payment_for_this, s_id))
        impacted_months.append(m_name)

    covered_str = f"{impacted_months[0]}-{impacted_months[-1]}" if len(impacted_months) > 1 else impacted_months[0]
    receipt_no = f"SAL-{int(datetime.now().timestamp()) % 10000:04d}"
    today_date = datetime.now().strftime("%d/%m/%Y")
    exact_time = datetime.now().strftime("%I:%M:%S %p")
    
    cursor.execute("""
        INSERT INTO salary_payments (teacher_id, session, recpt_date, recpt_time, month, amount, receipt_no)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (str(teacher_id), session, today_date, exact_time, covered_str, total_payment, receipt_no))

    conn.commit()
    conn.close()
    return receipt_no, today_date, exact_time, covered_str

# --- HTML DIGITAL ID CARDS & RECEIPTS ---
def render_student_id_card(school_name, authority_name, name, father_name, mother_name, reg_no, grade, section, roll_no, bus_no, address, photo_base64, session):
    img_src = f"data:image/png;base64,{photo_base64}" if photo_base64 else "https://via.placeholder.com/110x130?text=No+Photo"
    bus_str = f"Bus No: #{bus_no}" if bus_no else "Transport: Self"
    
    return f"""
    <div id="student-card" style="width: 360px; border-radius: 16px; overflow: hidden; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #ffffff; border: 1px solid #e0e6ed; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.15); margin: 0 auto; color: #1e293b; position: relative;">
        <!-- Card Header Background Pattern -->
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); color: #ffffff; text-align: center; padding: 18px 14px 14px 14px; position: relative;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: rgba(255,255,255,0.05); border-radius: 50%;"></div>
            <h3 style="margin: 0; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #f8fafc;">{school_name}</h3>
            <div style="margin-top: 6px; display: inline-block;">
                <span style="font-size: 9px; background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); padding: 3px 10px; border-radius: 20px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;">STUDENT PASS</span>
            </div>
        </div>
        
        <!-- Photo & Primary Details -->
        <div style="text-align: center; padding: 16px 14px 8px 14px; background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);">
            <div style="position: relative; display: inline-block;">
                <img src="{img_src}" style="width: 100px; height: 120px; object-fit: cover; border-radius: 10px; border: 3px solid #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.12);">
            </div>
            <h3 style="margin: 10px 0 2px 0; color: #0f172a; font-size: 18px; font-weight: 700; letter-spacing: -0.2px;">{name}</h3>
            <div style="font-size: 11px; font-weight: 700; color: #2563eb; background: #eff6ff; display: inline-block; padding: 2px 8px; border-radius: 4px; margin-top: 2px;">
                REG: {reg_no}
            </div>
        </div>

        <!-- Student Attribute Grid -->
        <div style="padding: 10px 20px; font-size: 12px;">
            <table style="width: 100%; border-collapse: collapse; line-height: 1.6;">
                <tr style="border-bottom: 1px dashed #f1f5f9;">
                    <td style="padding: 4px 0; color: #64748b; font-weight: 600;">Father:</td>
                    <td style="padding: 4px 0; color: #1e293b; font-weight: 600; text-align: right;">{father_name if father_name else 'N/A'}</td>
                </tr>
                <tr style="border-bottom: 1px dashed #f1f5f9;">
                    <td style="padding: 4px 0; color: #64748b; font-weight: 600;">Mother:</td>
                    <td style="padding: 4px 0; color: #1e293b; font-weight: 600; text-align: right;">{mother_name if mother_name else 'N/A'}</td>
                </tr>
                <tr style="border-bottom: 1px dashed #f1f5f9;">
                    <td style="padding: 4px 0; color: #64748b; font-weight: 600;">Class & Sec:</td>
                    <td style="padding: 4px 0; color: #1e293b; font-weight: 700; text-align: right;">Grade {grade} ({section})</td>
                </tr>
                <tr style="border-bottom: 1px dashed #f1f5f9;">
                    <td style="padding: 4px 0; color: #64748b; font-weight: 600;">Roll & Session:</td>
                    <td style="padding: 4px 0; color: #1e293b; font-weight: 600; text-align: right;">#{roll_no} | {session}</td>
                </tr>
                <tr style="border-bottom: 1px dashed #f1f5f9;">
                    <td style="padding: 4px 0; color: #64748b; font-weight: 600;">Logistics:</td>
                    <td style="padding: 4px 0; color: #1e293b; font-weight: 600; text-align: right;">{bus_str}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #64748b; font-weight: 600; vertical-align: top;">Address:</td>
                    <td style="padding: 4px 0; color: #1e293b; font-weight: 500; text-align: right; word-break: break-word;">{address}</td>
                </tr>
            </table>
        </div>

        <!-- Card Footer -->
        <div style="background: #f8fafc; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e2e8f0; margin-top: 4px;">
            <div style="display: flex; align-items: center; gap: 4px;">
                <span style="font-size: 10px; color: #059669; font-weight: 700; background: #ecfdf5; border: 1px solid #a7f3d0; padding: 2px 6px; border-radius: 4px;">✔ AUTHENTICATED</span>
            </div>
            <div style="text-align: center;">
                <span style="font-size: 11px; font-weight: 700; color: #0f172a;">{authority_name}</span><br>
                <span style="font-size: 8px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; font-weight: 600;">Signatory</span>
            </div>
        </div>
    </div>
    <div style="text-align: center; margin-top: 15px;">
        <button onclick="printCard()" style="background: linear-gradient(135deg, #1e3a8a, #0f172a); color: white; border: none; padding: 10px 22px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; letter-spacing: 0.3px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            🖨️ Print Student ID Card
        </button>
    </div>
    <script>
        function printCard() {{
            var printContents = document.getElementById('student-card').outerHTML;
            var originalContents = document.body.innerHTML;
            document.body.innerHTML = '<html><head><title>Print Student ID Card</title></head><body style="display:flex; justify-content:center; align-items:center; height:100vh; margin:0; background:#fff;">' + printContents + '</body></html>';
            window.print();
            document.body.innerHTML = originalContents;
            location.reload();
        }}
    </script>
    """

def render_teacher_id_card(school_name, authority_name, name, teacher_id, subject, classes_taught, address, photo_base64, session):
    img_src = f"data:image/png;base64,{photo_base64}" if photo_base64 else "https://via.placeholder.com/110x130?text=No+Photo"
    
    return f"""
    <div id="teacher-card" style="width: 360px; border-radius: 16px; overflow: hidden; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #ffffff; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.15); margin: 0 auto; color: #1e293b; position: relative;">
        <!-- Card Header Background -->
        <div style="background: linear-gradient(135deg, #111827 0%, #374151 100%); color: #ffffff; text-align: center; padding: 18px 14px 14px 14px; position: relative;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: rgba(255,255,255,0.04); border-radius: 50%;"></div>
            <h3 style="margin: 0; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #f9fafb;">{school_name}</h3>
            <div style="margin-top: 6px; display: inline-block;">
                <span style="font-size: 9px; background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); padding: 3px 10px; border-radius: 20px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;">FACULTY CREDENTIAL</span>
            </div>
        </div>
        
        <!-- Photo & Primary Details -->
        <div style="text-align: center; padding: 16px 14px 8px 14px; background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);">
            <div style="position: relative; display: inline-block;">
                <img src="{img_src}" style="width: 100px; height: 120px; object-fit: cover; border-radius: 10px; border: 3px solid #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.12);">
            </div>
            <h3 style="margin: 10px 0 2px 0; color: #111827; font-size: 18px; font-weight: 700; letter-spacing: -0.2px;">{name}</h3>
            <div style="font-size: 11px; font-weight: 700; color: #d97706; background: #fffbeb; display: inline-block; padding: 2px 8px; border-radius: 4px; margin-top: 2px;">
                EMP ID: {teacher_id}
            </div>
        </div>

        <!-- Faculty Attribute Grid -->
        <div style="padding: 10px 20px; font-size: 12px;">
            <table style="width: 100%; border-collapse: collapse; line-height: 1.6;">
                <tr style="border-bottom: 1px dashed #f3f4f6;">
                    <td style="padding: 4px 0; color: #6b7280; font-weight: 600;">Department:</td>
                    <td style="padding: 4px 0; color: #111827; font-weight: 700; text-align: right;">{subject}</td>
                </tr>
                <tr style="border-bottom: 1px dashed #f3f4f6;">
                    <td style="padding: 4px 0; color: #6b7280; font-weight: 600;">Classes:</td>
                    <td style="padding: 4px 0; color: #111827; font-weight: 600; text-align: right;">{classes_taught}</td>
                </tr>
                <tr style="border-bottom: 1px dashed #f3f4f6;">
                    <td style="padding: 4px 0; color: #6b7280; font-weight: 600;">Session:</td>
                    <td style="padding: 4px 0; color: #111827; font-weight: 600; text-align: right;">{session}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #6b7280; font-weight: 600; vertical-align: top;">Address:</td>
                    <td style="padding: 4px 0; color: #111827; font-weight: 500; text-align: right; word-break: break-word;">{address}</td>
                </tr>
            </table>
        </div>

        <!-- Card Footer -->
        <div style="background: #f9fafb; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e7eb; margin-top: 4px;">
            <div style="display: flex; align-items: center; gap: 4px;">
                <span style="font-size: 10px; color: #2563eb; font-weight: 700; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 6px; border-radius: 4px;">✔ VERIFIED STAFF</span>
            </div>
            <div style="text-align: center;">
                <span style="font-size: 11px; font-weight: 700; color: #111827;">{authority_name}</span><br>
                <span style="font-size: 8px; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af; font-weight: 600;">Signatory</span>
            </div>
        </div>
    </div>
    <div style="text-align: center; margin-top: 15px;">
        <button onclick="printTeacherCard()" style="background: linear-gradient(135deg, #374151, #111827); color: white; border: none; padding: 10px 22px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; letter-spacing: 0.3px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            🖨️ Print Faculty ID Card
        </button>
    </div>
    <script>
        function printTeacherCard() {{
            var printContents = document.getElementById('teacher-card').outerHTML;
            var originalContents = document.body.innerHTML;
            document.body.innerHTML = '<html><head><title>Print Faculty ID Card</title></head><body style="display:flex; justify-content:center; align-items:center; height:100vh; margin:0; background:#fff;">' + printContents + '</body></html>';
            window.print();
            document.body.innerHTML = originalContents;
            location.reload();
        }}
    </script>
    """

def render_printable_receipt(school_name, authority_name, receipt_no, date_str, time_str, student_name, reg_no, grade, section, installment, amount, session):
    return f"""
    <div id="printable-receipt" style="border: 2px solid #333; padding: 20px; border-radius: 8px; font-family: Arial, sans-serif; background-color: #ffffff; max-width: 500px; margin: 0 auto; color: #000000;">
        <div style="text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 15px;">
            <h2 style="margin: 0; color: #1a252f;">{school_name}</h2>
            <p style="margin: 4px 0; font-weight: bold; font-size: 14px; color: #555;">FEE PAYMENT RECEIPT ({session})</p>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 14px;">
            <tr>
                <td><strong>Receipt No:</strong> #{receipt_no}</td>
                <td style="text-align: right;"><strong>Date:</strong> {date_str}</td>
            </tr>
            <tr>
                <td><strong>Reg No:</strong> {reg_no}</td>
                <td style="text-align: right;"><strong>Time:</strong> {time_str}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding-top: 5px;"><strong>Student Name:</strong> {student_name} (Class {grade}-{section})</td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px; border: 1px solid #ddd; font-size: 14px;">
            <thead>
                <tr style="background-color: #f2f2f2; border-bottom: 1px solid #ddd;">
                    <th style="padding: 8px; text-align: left;">Description</th>
                    <th style="padding: 8px; text-align: right;">Amount (₹)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">Tuition Fee ({installment})</td>
                    <td style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">₹{amount:,.2f}</td>
                </tr>
                <tr style="font-weight: bold; background-color: #fafafa;">
                    <td style="padding: 8px;">Total Paid</td>
                    <td style="padding: 8px; text-align: right; color: #27ae60;">₹{amount:,.2f}</td>
                </tr>
            </tbody>
        </table>
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 30px; font-size: 12px;">
            <div>Status: <strong style="color: #27ae60;">PAID (SUCCESSFUL)</strong></div>
            <div style="text-align: center;">
                <br>
                <span>_______________________</span><br>
                <strong>{authority_name}</strong><br>
                <span style="font-size: 10px; color: #666;">(Authorized Signatory)</span>
            </div>
        </div>
    </div>
    <div style="text-align: center; margin-top: 15px;">
        <button onclick="printReceipt()" style="background-color: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 15px; font-weight: bold;">
            🖨️ Print Receipt
        </button>
    </div>
    <script>
        function printReceipt() {{
            var printContents = document.getElementById('printable-receipt').outerHTML;
            var originalContents = document.body.innerHTML;
            document.body.innerHTML = '<html><head><title>Print Receipt</title></head><body style="padding: 20px;">' + printContents + '</body></html>';
            window.print();
            document.body.innerHTML = originalContents;
            location.reload();
        }}
    </script>
    """

def render_printable_salary_slip(school_name, authority_name, receipt_no, date_str, time_str, teacher_name, teacher_id, subject, month, amount, session):
    return f"""
    <div id="printable-salary-slip" style="border: 2px solid #333; padding: 20px; border-radius: 8px; font-family: Arial, sans-serif; background-color: #ffffff; max-width: 500px; margin: 0 auto; color: #000000;">
        <div style="text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 15px;">
            <h2 style="margin: 0; color: #1a252f;">{school_name}</h2>
            <p style="margin: 4px 0; font-weight: bold; font-size: 14px; color: #555;">TEACHER SALARY VOUCHER ({session})</p>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 14px;">
            <tr>
                <td><strong>Voucher No:</strong> #{receipt_no}</td>
                <td style="text-align: right;"><strong>Date:</strong> {date_str}</td>
            </tr>
            <tr>
                <td><strong>Teacher ID:</strong> {teacher_id}</td>
                <td style="text-align: right;"><strong>Time:</strong> {time_str}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding-top: 5px;"><strong>Teacher Name:</strong> {teacher_name} ({subject})</td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px; border: 1px solid #ddd; font-size: 14px;">
            <thead>
                <tr style="background-color: #f2f2f2; border-bottom: 1px solid #ddd;">
                    <th style="padding: 8px; text-align: left;">Description</th>
                    <th style="padding: 8px; text-align: right;">Amount (₹)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">Salary Disbursement ({month})</td>
                    <td style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">₹{amount:,.2f}</td>
                </tr>
                <tr style="font-weight: bold; background-color: #fafafa;">
                    <td style="padding: 8px;">Total Paid Out</td>
                    <td style="padding: 8px; text-align: right; color: #27ae60;">₹{amount:,.2f}</td>
                </tr>
            </tbody>
        </table>
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 30px; font-size: 12px;">
            <div>Status: <strong style="color: #27ae60;">DISBURSED (PAID)</strong></div>
            <div style="text-align: center;">
                <br>
                <span>_______________________</span><br>
                <strong>{authority_name}</strong><br>
                <span style="font-size: 10px; color: #666;">(Authorized Signatory)</span>
            </div>
        </div>
    </div>
    <div style="text-align: center; margin-top: 15px;">
        <button onclick="printSalarySlip()" style="background-color: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 15px; font-weight: bold;">
            🖨️ Print Salary Slip
        </button>
    </div>
    <script>
        function printSalarySlip() {{
            var printContents = document.getElementById('printable-salary-slip').outerHTML;
            var originalContents = document.body.innerHTML;
            document.body.innerHTML = '<html><head><title>Print Salary Voucher</title></head><body style="padding: 20px;">' + printContents + '</body></html>';
            window.print();
            document.body.innerHTML = originalContents;
            location.reload();
        }}
    </script>
    """

# --- AUTHENTICATION CHECK ---
db_info = get_saved_school_info()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not db_info:
    st.title("📝 First-Time Admin Registration & Setup")
    st.info("No administrator or school profiles were found. Please set up your credentials and school info to initialize the system.")

    with st.form("reg_form"):
        st.subheader("1. Admin Login Credentials")
        col_reg1, col_reg2 = st.columns(2)
        with col_reg1:
            reg_id = st.text_input("Create Register ID / Username*").strip()
        with col_reg2:
            reg_pass = st.text_input("Create Password*", type="password").strip()

        st.subheader("2. School & Receipt Settings")
        col_sch1, col_sch2 = st.columns(2)
        with col_sch1:
            sch_name = st.text_input("School Name*").strip()
        with col_sch2:
            auth_name = st.text_input("Authority Name / Title* (e.g. Principal)").strip()

        submit_setup = st.form_submit_button("Register & Initialize Portal", type="primary")

    if submit_setup:
        if not reg_id or not reg_pass or not sch_name or not auth_name:
            st.error("❌ All fields are required to complete initial setup!")
        else:
            save_initial_setup(reg_id, reg_pass, sch_name, auth_name)
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = reg_id
            st.success("✅ Registration complete! Portal initialized.")
            st.rerun()

    st.stop()

# LOGIN FORM
if not st.session_state["logged_in"]:
    admin_id_db, admin_pass_db, saved_school_db, saved_auth_db = db_info
    
    st.title("🔐 Portal Login")
    st.caption(f"Welcome to **{saved_school_db}**. Enter your registered credentials to log in.")

    with st.form("login_form"):
        username = st.text_input("Register ID / Username").strip()
        password = st.text_input("Password", type="password").strip()
        login_btn = st.form_submit_button("🔑 Login", type="primary")

    if login_btn:
        if username == admin_id_db and password == admin_pass_db:
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = username
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid Register ID or Password!")
    st.stop()

_, _, school_name, authority_name = db_info

# SIDEBAR & LOGOUT
with st.sidebar:
    st.markdown("### 👤 Staff User")
    st.write(f"Logged in as: **{st.session_state.get('current_user', 'Admin')}**")
    if st.button("🔒 Logout", type="secondary"):
        st.session_state["logged_in"] = False
        st.rerun()

# --- MAIN DASHBOARD APP ---
st.title("🏫 School Management Portal")

col_a, col_b = st.columns(2)
with col_a:
    st.text_input("School Name (Locked)", value=school_name, disabled=True)
with col_b:
    st.text_input("Authority Signatory (Locked)", value=authority_name, disabled=True)

# SESSION SELECTOR
default_session = get_current_system_session()
session_options = ["2024-2025", "2025-2026", "2026-2027", "2027-2028"]
if default_session not in session_options:
    session_options.append(default_session)

col_sess, _ = st.columns([1, 1])
with col_sess:
    selected_session = st.selectbox("📅 Academic Session", options=session_options, index=session_options.index(default_session))

st.caption(f"Active Academic Session: **{selected_session}**")
st.divider()

role = st.radio("Select Role:", ["🎓 Student", "👨‍🏫 Teacher"], horizontal=True)
st.write("")

# --- STUDENT SECTION ---
if role == "🎓 Student":
    st.markdown("## 🎓 Student Management")
    student_tab_add, student_tab_search, student_tab_rates, student_tab_all = st.tabs([
        "➕ Add New Student", "🔍 Find Profile & ID Card", "⚙️ Monthly Fee Rates Settings", "📋 All Students (Print/Export)"
    ])

    # ADD STUDENT
    with student_tab_add:
        next_reg_no = generate_next_student_reg_no()
        with st.form("student_form"):
            st.subheader("Enter Student Details")
            st.info(f"🆔 Auto-assigned Student Registration Number: **{next_reg_no}**")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Student Name*", value="Alex Smith")
                father_name = st.text_input("Father's Name*", value="John Smith")
                grade = st.number_input("Class / Grade*", min_value=1, max_value=12, step=1, value=10)
            with col2:
                mother_name = st.text_input("Mother's Name*", value="Sarah Smith")
                roll_no = st.number_input("Roll Number* (Unique in Class)", min_value=1, step=1, value=15)
                section = st.text_input("Section*", value="A")
                bus_no = st.number_input("Bus No. (Optional)", min_value=0, max_value=200, step=1, value=6)

            address = st.text_area("Address*", value="123 Park Avenue, City Name", height=80)
            student_photo = st.file_uploader("Upload Passport Size Photo (Optional)", type=["jpg", "jpeg", "png"], key="student_photo_add")
            submit_student = st.form_submit_button("Add Student", type="primary")

        if submit_student:
            existing_student = check_roll_no_exists_in_grade(grade, roll_no)
            if not name.strip() or not father_name.strip() or not mother_name.strip():
                st.error("❌ Student Name, Father Name, and Mother Name are required!")
            elif existing_student:
                st.error(f"❌ Roll No `{roll_no}` is already assigned to **{existing_student}** in Class {grade}.")
            elif not section.strip() or not address.strip():
                st.error("❌ Required fields cannot be empty!")
            else:
                final_bus_no = int(bus_no) if bus_no > 0 else None
                photo_bytes = student_photo.read() if student_photo is not None else None
                save_student(next_reg_no, name.strip(), father_name.strip(), mother_name.strip(), grade, roll_no, section.strip(), address.strip(), final_bus_no, photo_bytes, selected_session)
                st.success(f"✅ Student profile for '{name.strip()}' saved successfully with Reg No `{next_reg_no}`!")
                st.rerun()

    # FIND STUDENT & DIGITAL ID CARD
    with student_tab_search:
        st.subheader("Search Student Record")
        search_reg_no = st.text_input("Enter Student Registration Number (e.g. 1001)", value="1001").strip()
        
        if search_reg_no:
            record = get_student(search_reg_no)
            if record:
                s_reg, s_name, s_father, s_mother, s_grade, s_roll, s_section, s_address, s_bus_no, s_photo = record
                st.success(f"✅ Student Profile Found for Reg No `{s_reg}` ({s_name})")
                
                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["👤 Profile Information", f"💳 My Fees ({selected_session})", "🎴 Digital ID Card"])

                # PROFILE EDIT
                with sub_tab1:
                    with st.form("edit_student_form"):
                        st.markdown("### ✏️ Edit Student Details")
                        col_img, col_info = st.columns([1, 2])
                        new_photo_bytes = None
                        with col_img:
                            if s_photo:
                                st.image(s_photo, caption="Student Photo (Locked)", width=130)
                            else:
                                upload_edit_photo = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"], key="student_photo_edit")
                                if upload_edit_photo:
                                    new_photo_bytes = upload_edit_photo.read()

                        with col_info:
                            st.text_input("Registration Number (Locked)", value=s_reg, disabled=True)
                            st.text_input("Name (Locked)", value=s_name, disabled=True)
                            
                            f1, f2 = st.columns(2)
                            with f1:
                                up_father = st.text_input("Father's Name*", value=s_father if s_father else "")
                                up_grade = st.number_input("Grade / Class*", min_value=1, max_value=12, value=int(s_grade))
                                up_roll = st.number_input("Roll No*", min_value=1, value=int(s_roll))
                            with f2:
                                up_mother = st.text_input("Mother's Name*", value=s_mother if s_mother else "")
                                up_section = st.text_input("Section*", value=s_section)
                                up_bus_no = st.number_input("Bus No", min_value=0, max_value=200, value=int(s_bus_no) if s_bus_no else 0)

                            up_address = st.text_area("Address*", value=s_address if s_address else "", height=80)

                        update_btn = st.form_submit_button("💾 Save Updated Profile", type="primary")

                    if update_btn:
                        existing_student = check_roll_no_exists_in_grade(up_grade, up_roll, current_reg_no=s_reg)
                        if existing_student:
                            st.error(f"❌ Roll No `{up_roll}` is already assigned to **{existing_student}** in Class {up_grade}.")
                        elif not up_father.strip() or not up_mother.strip() or not up_section.strip() or not up_address.strip():
                            st.error("❌ All parent names, section, and address fields are required!")
                        else:
                            final_bus = int(up_bus_no) if up_bus_no > 0 else None
                            final_photo = s_photo if s_photo else new_photo_bytes
                            save_student(s_reg, s_name, up_father.strip(), up_mother.strip(), up_grade, up_roll, up_section.strip(), up_address.strip(), final_bus, final_photo, selected_session)
                            st.success("✅ Profile updated successfully!")
                            st.rerun()

                # FEES DASHBOARD
                with sub_tab2:
                    st.markdown(f"## 💳 Fee Dashboard ({selected_session})")
                    df_fees = get_student_fee_structure(s_reg, selected_session)
                    
                    st.markdown("### 📋 Fee Structure")
                    st.dataframe(
                        df_fees[['Installment', 'Amount', 'Paid', 'Fine/Excess', 'Balance']].style.format({
                            'Amount': '{:.2f}', 'Paid': '{:.2f}', 'Fine/Excess': '{:.2f}', 'Balance': '{:.2f}'
                        }), 
                        use_container_width=True, 
                        hide_index=True
                    )

                    total_due = df_fees['Amount'].sum() + df_fees['Fine/Excess'].sum()
                    total_paid = df_fees['Paid'].sum()
                    total_balance = df_fees['Balance'].sum()

                    st.markdown("### 📊 Fee Chart")
                    fig = go.Figure(data=[go.Pie(
                        labels=['Due', 'Paid', 'Balance'],
                        values=[total_due, total_paid, total_balance],
                        hole=.6,
                        marker_colors=['#F4B41A', '#A0C4FF', '#FF6B6B'],
                        textinfo='label+value'
                    )])
                    fig.update_layout(height=350, annotations=[dict(text=f"Paid ({selected_session})<br>₹{total_paid:,.2f}", x=0.5, y=0.5, font_size=14, showarrow=False)])
                    st.plotly_chart(fig, use_container_width=True)

                    st.divider()
                    st.markdown("### 🧾 Payment History & Printable Receipts")
                    df_payments = get_student_payments(s_reg, selected_session)
                    
                    if not df_payments.empty:
                        st.dataframe(df_payments.style.format({'Amount': '{:.2f}'}), use_container_width=True, hide_index=True)
                        
                        st.markdown("#### 🖨️ Select Receipt to Print")
                        receipt_list = df_payments['Receipt'].tolist()
                        selected_rcpt_no = st.selectbox("Choose Receipt Number", receipt_list)
                        
                        rcpt_row = df_payments[df_payments['Receipt'] == selected_rcpt_no].iloc[0]
                        rcpt_date = rcpt_row['Recpt Date']
                        rcpt_time = rcpt_row['Time']
                        rcpt_inst = rcpt_row['Installment']
                        rcpt_amt = float(rcpt_row['Amount'])

                        rcpt_html = render_printable_receipt(
                            school_name, authority_name, selected_rcpt_no, rcpt_date, rcpt_time, s_name, s_reg, s_grade, s_section, rcpt_inst, rcpt_amt, selected_session
                        )
                        components.html(rcpt_html, height=390, scrolling=True)
                    else:
                        st.info(f"ℹ️ No payment history found for session {selected_session}.")

                    st.divider()
                    st.markdown("### ⏳ Pending Fees & Smart Payment")
                    df_pending = df_fees[df_fees['Balance'] > 0]

                    if not df_pending.empty:
                        st.dataframe(df_pending[['Installment', 'Balance']].style.format({'Balance': '{:.2f}'}), use_container_width=True, hide_index=True)
                        st.error(f"**Total Outstanding Balance:** ₹{total_balance:,.2f}")

                        st.markdown("#### 💸 Record Custom Payment")
                        with st.form("cascade_pay_form"):
                            pending_installments = df_pending['Installment'].tolist()
                            selected_inst = st.selectbox("Starting Fee Installment", pending_installments)
                            
                            min_pay = 500.0
                            max_pay = float(total_balance)
                            
                            pay_amount = st.number_input(
                                f"Enter Amount to Pay (Min: ₹500, Max: ₹{max_pay:,.2f})",
                                min_value=min_pay,
                                max_value=max_pay,
                                value=min(min_pay, max_pay),
                                step=100.0
                            )
                            
                            pay_btn = st.form_submit_button("💳 Submit & Generate Receipt", type="primary")

                        if pay_btn:
                            rcpt_no, r_date, r_time, r_inst = process_cascade_fee_payment(s_reg, selected_session, selected_inst, pay_amount)
                            st.success(f"✅ Payment of ₹{pay_amount:,.2f} recorded under Receipt #{rcpt_no} at {r_time}!")
                            st.rerun()
                    else:
                        st.balloons()
                        st.success(f"🎉 All fees for session {selected_session} are fully paid!")

                # DIGITAL ID CARD
                with sub_tab3:
                    st.markdown("### 🎴 Student Digital Identity Card")
                    import base64
                    photo_b64 = base64.b64encode(s_photo).decode("utf-8") if s_photo else ""
                    id_card_html = render_student_id_card(
                        school_name, authority_name, s_name, s_father, s_mother, s_reg, s_grade, s_section, s_roll, s_bus_no, s_address, photo_b64, selected_session
                    )
                    components.html(id_card_html, height=520, scrolling=True)

            else:
                st.info(f"ℹ️ No record found for Reg No `{search_reg_no}`.")

    # MONTHLY FEE RATES SETTINGS TAB
    with student_tab_rates:
        st.subheader(f"⚙️ Configure Monthly Fee Rates ({selected_session})")
        st.info("💡 Adjusting these values updates the fee structure for new entries and unpaid months in this session.")
        
        current_rates = get_session_fee_rates(selected_session)
        
        with st.form("fee_rates_form"):
            st.markdown("#### ✏️ Set Installment Rates (₹)")
            updated_rates = {}
            cols = st.columns(3)
            for idx, m in enumerate(MONTH_LIST):
                with cols[idx % 3]:
                    updated_rates[m] = st.number_input(
                        f"Installment: {m}", 
                        min_value=0.0, 
                        value=float(current_rates.get(m, 5600.0)), 
                        step=100.0
                    )

            save_rates_btn = st.form_submit_button("💾 Save Fee Rate Structure", type="primary")

        if save_rates_btn:
            set_session_fee_rates(selected_session, updated_rates)
            st.success(f"✅ Fee rate structure for **{selected_session}** updated successfully!")
            st.rerun()

    # ALL STUDENTS TAB
    with student_tab_all:
        st.subheader("📋 All Registered Students")
        df_students = get_all_students()
        if not df_students.empty:
            st.dataframe(df_students, use_container_width=True)
            csv_data = df_students.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Student Records (CSV)", data=csv_data, file_name=f"{school_name}_Students.csv", mime="text/csv", type="primary")
        else:
            st.info("ℹ️ No student records found.")

# --- TEACHER SECTION ---
else:
    st.markdown("## 👨‍🏫 Teacher Management")
    teacher_tab_add, teacher_tab_search, teacher_tab_rates, teacher_tab_all = st.tabs([
        "➕ Add New Teacher", "🔍 Find Profile & ID Card", "⚙️ Monthly Salary Rates Settings", "📋 All Teachers (Print/Export)"
    ])

    # ADD TEACHER
    with teacher_tab_add:
        next_teacher_id = generate_next_teacher_id()
        with st.form("teacher_form"):
            st.subheader("Enter Teacher Details")
            st.info(f"🆔 Auto-assigned Teacher ID: **{next_teacher_id}**")
            col1, col2 = st.columns(2)
            with col1:
                t_name = st.text_input("Teacher Name*", value="Jai Kant")
                t_subject = st.text_input("Subject*", value="Mathematics")
            with col2:
                t_classes = st.multiselect("Classes Taught*", options=[f"Class {i}" for i in range(1, 13)], default=["Class 7", "Class 8", "Class 9"])

            t_address = st.text_area("Address*", value="456 Main Street, City Name", height=100)
            teacher_photo = st.file_uploader("Upload Passport Size Photo (Optional)", type=["jpg", "jpeg", "png"], key="teacher_photo_add")
            submit_teacher = st.form_submit_button("Add Teacher", type="primary")

        if submit_teacher:
            if not t_name.strip() or not t_subject.strip() or not t_classes or not t_address.strip():
                st.error("❌ All required fields must be filled!")
            else:
                photo_bytes = teacher_photo.read() if teacher_photo is not None else None
                save_teacher(next_teacher_id, t_name.strip(), t_subject.strip(), ", ".join(t_classes), t_address.strip(), photo_bytes, selected_session)
                st.success(f"✅ Teacher saved successfully with ID `{next_teacher_id}`!")
                st.rerun()

    # FIND TEACHER & DIGITAL ID CARD
    with teacher_tab_search:
        st.subheader("Search Teacher Record")
        search_teacher_id = st.text_input("Enter Teacher ID (e.g. 101)", value="101").strip()
        if search_teacher_id:
            record = get_teacher(search_teacher_id)
            if record:
                t_id, t_name, t_subject, t_classes_taught, t_address, t_photo = record
                st.success(f"✅ Teacher Profile Found for ID `{t_id}` ({t_name})")
                
                sub_t_tab1, sub_t_tab2, sub_t_tab3 = st.tabs(["👤 Profile Information", f"💵 Salary Management ({selected_session})", "🎴 Digital ID Card"])

                # PROFILE EDIT
                with sub_t_tab1:
                    with st.form("edit_teacher_form"):
                        st.markdown("### ✏️ Edit Teacher Details")
                        col_img, col_info = st.columns([1, 2])
                        new_t_photo_bytes = None
                        with col_img:
                            if t_photo:
                                st.image(t_photo, caption="Teacher Photo (Locked)", width=130)
                            else:
                                upload_edit_t_photo = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"], key="teacher_photo_edit")
                                if upload_edit_t_photo:
                                    new_t_photo_bytes = upload_edit_t_photo.read()

                        with col_info:
                            st.text_input("Teacher ID (Locked)", value=t_id, disabled=True)
                            st.text_input("Name (Locked)", value=t_name, disabled=True)
                            up_t_subject = st.text_input("Subject*", value=t_subject)
                            current_classes = [c.strip() for c in t_classes_taught.split(",") if c.strip()]
                            up_t_classes = st.multiselect("Classes Taught*", options=[f"Class {i}" for i in range(1, 13)], default=current_classes)
                            up_t_address = st.text_area("Address*", value=t_address if t_address else "", height=80)

                        update_teacher_btn = st.form_submit_button("💾 Save Updated Profile", type="primary")

                    if update_teacher_btn:
                        if not up_t_subject.strip() or not up_t_classes or not up_t_address.strip():
                            st.error("❌ Fill all required fields!")
                        else:
                            final_t_photo = t_photo if t_photo else new_t_photo_bytes
                            save_teacher(t_id, t_name, up_t_subject.strip(), ", ".join(up_t_classes), up_t_address.strip(), final_t_photo, selected_session)
                            st.success("✅ Teacher profile updated!")
                            st.rerun()

                # SALARY DASHBOARD
                with sub_t_tab2:
                    st.markdown(f"## 💵 Salary Dashboard ({selected_session})")
                    df_salaries = get_teacher_salary_structure(t_id, selected_session)
                    
                    st.markdown("### 📋 Monthly Salary Structure")
                    st.dataframe(
                        df_salaries[['Month', 'Amount', 'Paid', 'Bonus/Allowances', 'Balance']].style.format({
                            'Amount': '{:.2f}', 'Paid': '{:.2f}', 'Bonus/Allowances': '{:.2f}', 'Balance': '{:.2f}'
                        }), 
                        use_container_width=True, 
                        hide_index=True
                    )

                    total_sal_due = df_salaries['Amount'].sum() + df_salaries['Bonus/Allowances'].sum()
                    total_sal_paid = df_salaries['Paid'].sum()
                    total_sal_balance = df_salaries['Balance'].sum()

                    st.markdown("### 📊 Salary Disbursement Chart")
                    fig_sal = go.Figure(data=[go.Pie(
                        labels=['Total Due', 'Paid Out', 'Remaining Salary'],
                        values=[total_sal_due, total_sal_paid, total_sal_balance],
                        hole=.6,
                        marker_colors=['#2A9D8F', '#E76F51', '#E9C46A'],
                        textinfo='label+value'
                    )])
                    fig_sal.update_layout(height=350, annotations=[dict(text=f"Disbursed ({selected_session})<br>₹{total_sal_paid:,.2f}", x=0.5, y=0.5, font_size=14, showarrow=False)])
                    st.plotly_chart(fig_sal, use_container_width=True)

                    st.divider()
                    st.markdown("### 🧾 Salary Payment History & Vouchers")
                    df_sal_payments = get_teacher_salary_payments(t_id, selected_session)
                    
                    if not df_sal_payments.empty:
                        st.dataframe(df_sal_payments.style.format({'Amount': '{:.2f}'}), use_container_width=True, hide_index=True)
                        
                        st.markdown("#### 🖨️ Select Salary Voucher to Print")
                        voucher_list = df_sal_payments['Voucher'].tolist()
                        selected_vchr_no = st.selectbox("Choose Voucher Number", voucher_list)
                        
                        vchr_row = df_sal_payments[df_sal_payments['Voucher'] == selected_vchr_no].iloc[0]
                        vchr_date = vchr_row['Date']
                        vchr_time = vchr_row['Time']
                        vchr_month = vchr_row['Month']
                        vchr_amt = float(vchr_row['Amount'])

                        sal_html = render_printable_salary_slip(
                            school_name, authority_name, selected_vchr_no, vchr_date, vchr_time, t_name, t_id, t_subject, vchr_month, vchr_amt, selected_session
                        )
                        components.html(sal_html, height=390, scrolling=True)
                    else:
                        st.info(f"ℹ️ No salary disbursement history found for session {selected_session}.")

                    st.divider()
                    st.markdown("### ⏳ Pending Salary & Disburse Payment")
                    df_sal_pending = df_salaries[df_salaries['Balance'] > 0]

                    if not df_sal_pending.empty:
                        st.dataframe(df_sal_pending[['Month', 'Balance']].style.format({'Balance': '{:.2f}'}), use_container_width=True, hide_index=True)
                        st.error(f"**Total Salary Due:** ₹{total_sal_balance:,.2f}")

                        st.markdown("#### 💸 Pay Teacher Salary")
                        with st.form("cascade_sal_pay_form"):
                            pending_months = df_sal_pending['Month'].tolist()
                            selected_month = st.selectbox("Starting Month", pending_months)
                            
                            min_sal_pay = 1000.0
                            max_sal_pay = float(total_sal_balance)
                            
                            sal_pay_amount = st.number_input(
                                f"Enter Amount to Pay Out (Min: ₹1000, Max: ₹{max_sal_pay:,.2f})",
                                min_value=min_sal_pay,
                                max_value=max_sal_pay,
                                value=min(min_sal_pay, max_sal_pay),
                                step=500.0
                            )
                            
                            sal_pay_btn = st.form_submit_button("💳 Submit & Generate Salary Voucher", type="primary")

                        if sal_pay_btn:
                            v_no, v_date, v_time, v_m = process_cascade_salary_payment(t_id, selected_session, selected_month, sal_pay_amount)
                            st.success(f"✅ Salary of ₹{sal_pay_amount:,.2f} disbursed under Voucher #{v_no} at {v_time}!")
                            st.rerun()
                    else:
                        st.balloons()
                        st.success(f"🎉 All salary payouts for session {selected_session} are fully disbursed!")

                # TEACHER DIGITAL ID CARD
                with sub_t_tab3:
                    st.markdown("### 🎴 Faculty Digital Identity Card")
                    import base64
                    photo_t_b64 = base64.b64encode(t_photo).decode("utf-8") if t_photo else ""
                    teacher_id_card_html = render_teacher_id_card(
                        school_name, authority_name, t_name, t_id, t_subject, t_classes_taught, t_address, photo_t_b64, selected_session
                    )
                    components.html(teacher_id_card_html, height=500, scrolling=True)

            else:
                st.info(f"ℹ️ No record found for Teacher ID `{search_teacher_id}`.")

    # MONTHLY SALARY RATES SETTINGS TAB
    with teacher_tab_rates:
        st.subheader(f"⚙️ Configure Monthly Salary Rates ({selected_session})")
        st.info("💡 Adjusting these values updates the salary payouts for new entries and unpaid months in this session.")
        
        current_sal_rates = get_session_salary_rates(selected_session)
        
        with st.form("salary_rates_form"):
            st.markdown("#### ✏️ Set Monthly Salary Rates (₹)")
            updated_sal_rates = {}
            cols = st.columns(3)
            for idx, m in enumerate(MONTH_LIST):
                with cols[idx % 3]:
                    updated_sal_rates[m] = st.number_input(
                        f"Month: {m}", 
                        min_value=0.0, 
                        value=float(current_sal_rates.get(m, 25000.0)), 
                        step=500.0
                    )

            save_sal_rates_btn = st.form_submit_button("💾 Save Salary Rate Structure", type="primary")

        if save_sal_rates_btn:
            set_session_salary_rates(selected_session, updated_sal_rates)
            st.success(f"✅ Teacher salary rate structure for **{selected_session}** updated successfully!")
            st.rerun()

    # ALL TEACHERS TAB
    with teacher_tab_all:
        st.subheader("📋 All Registered Teachers")
        df_teachers = get_all_teachers()
        if not df_teachers.empty:
            st.dataframe(df_teachers, use_container_width=True)
            csv_data = df_teachers.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Teacher Records (CSV)", data=csv_data, file_name=f"{school_name}_Teachers.csv", mime="text/csv", type="primary")
        else:
            st.info("ℹ️ No teacher records found.")
