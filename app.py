import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import sqlite3
from datetime import datetime

combo_view_class = None
combo_view_section = None
combo_view_student = None


# -------------------- Database Setup --------------------
DB = "attendance.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Tables
cur.execute('''
CREATE TABLE IF NOT EXISTS classes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name TEXT NOT NULL UNIQUE
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS sections(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    section_name TEXT NOT NULL,
    FOREIGN KEY(class_id) REFERENCES classes(id)
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    section_id INTEGER NOT NULL,
    FOREIGN KEY(class_id) REFERENCES classes(id),
    FOREIGN KEY(section_id) REFERENCES sections(id)
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS attendance(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(student_id) REFERENCES students(id)
)
''')
conn.commit()

# -------------------- App Setup --------------------
root = tk.Tk()
root.title("Attendance Management System (CRUD)")
root.geometry("1150x700")

nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True, padx=8, pady=8)

frm_class = ttk.Frame(nb)
frm_section = ttk.Frame(nb)
frm_student = ttk.Frame(nb)
frm_attendance = ttk.Frame(nb)
frm_view = ttk.Frame(nb)

nb.add(frm_class, text="Manage Classes")
nb.add(frm_section, text="Manage Sections")
nb.add(frm_student, text="Manage Students")
nb.add(frm_attendance, text="Take & Edit Attendance")
nb.add(frm_view, text="View Attendance")

# -------------------- Utility --------------------
def simple_input(title, prompt, default=""):
    popup = tk.Toplevel(root)
    popup.title(title)
    popup.transient(root)
    popup.grab_set()
    ttk.Label(popup, text=prompt).pack(padx=10, pady=8)
    e = ttk.Entry(popup, width=40)
    e.insert(0, default)
    e.pack(padx=10, pady=5)
    result = {"value": None}
    def ok():
        result["value"] = e.get().strip()
        popup.destroy()
    ttk.Button(popup, text="OK", command=ok).pack(pady=8)
    popup.wait_window()
    return result["value"]

def confirm(msg):
    return messagebox.askyesno("Confirm", msg)

def refresh_all():
    load_classes_table()
    load_sections_table()
    load_students_table()
    load_attendance_table()
    load_class_combos()

# -------------------- CLASS CRUD --------------------
def add_class():
    name = ent_class_name.get().strip()
    if not name: 
        messagebox.showwarning("Input", "Enter class name.")
        return
    try:
        cur.execute("INSERT INTO classes(class_name) VALUES(?)", (name,))
        conn.commit()
        ent_class_name.delete(0, tk.END)
        refresh_all()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def load_classes_table():
    tree_class.delete(*tree_class.get_children())
    cur.execute("SELECT id, class_name FROM classes ORDER BY class_name")
    for r in cur.fetchall():
        tree_class.insert("", tk.END, values=r)

def edit_class():
    sel = tree_class.selection()
    if not sel:
        messagebox.showwarning("Select", "Select a class to edit.")
        return
    cid, old = tree_class.item(sel, "values")
    new = simple_input("Edit Class", "New class name:", old)
    if new:
        try:
            cur.execute("UPDATE classes SET class_name=? WHERE id=?", (new, cid))
            conn.commit()
            refresh_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

def delete_class():
    sel = tree_class.selection()
    if not sel:
        messagebox.showwarning("Select", "Select a class to delete.")
        return
    cid = tree_class.item(sel, "values")[0]
    if not confirm("Deleting a class will delete its sections, students and related attendance. Continue?"):
        return
    # Delete attendance for students in this class
    cur.execute("SELECT id FROM students WHERE class_id=?", (cid,))
    sids = [r[0] for r in cur.fetchall()]
    if sids:
        cur.executemany("DELETE FROM attendance WHERE student_id=?", [(sid,) for sid in sids])
    # Delete students
    cur.execute("DELETE FROM students WHERE class_id=?", (cid,))
    # Delete sections
    cur.execute("DELETE FROM sections WHERE class_id=?", (cid,))
    # Delete class
    cur.execute("DELETE FROM classes WHERE id=?", (cid,))
    conn.commit()
    refresh_all()

ttk.Label(frm_class, text="New Class Name:").pack(padx=10, pady=(12,4), anchor="w")
ent_class_name = ttk.Entry(frm_class, width=36)
ent_class_name.pack(padx=10, pady=4, anchor="w")
ttk.Button(frm_class, text="Add Class", command=add_class).pack(padx=10, pady=6, anchor="w")

cols = ["Class"]
tree_class = ttk.Treeview(frm_class, columns=cols, show="headings", height=10)
for c in cols:
    tree_class.heading(c, text=c, anchor="center")
    tree_class.column(c, width=180, anchor="center")
tree_class.pack(padx=10, pady=8, fill="x", anchor="center")
btnf = ttk.Frame(frm_class); btnf.pack(padx=10, pady=6, anchor="w")
ttk.Button(btnf, text="Edit Class", command=edit_class).grid(row=0, column=0, padx=6)
ttk.Button(btnf, text="Delete Class", command=delete_class).grid(row=0, column=1, padx=6)

# -------------------- SECTION CRUD --------------------
def load_class_combos():
    cur.execute("SELECT class_name FROM classes ORDER BY class_name")
    classes = cur.fetchall()
    cat = [f"{r[0]}" for r in classes]
    combo_section_class['values'] = cat
    combo_student_class['values'] = cat
    combo_att_class['values'] = cat
    if combo_view_class:
        combo_view_class['values'] = cat

def add_section():
    class_info = combo_section_class.get()
    if not class_info or "-" not in class_info:
        messagebox.showwarning("Select", "Select a class first.")
        return
    cid = class_info.split("-",1)[0].strip()
    name = ent_section_name.get().strip()
    if not name:
        messagebox.showwarning("Input", "Enter section name.")
        return
    cur.execute("INSERT INTO sections(class_id, section_name) VALUES(?,?)", (cid, name))
    conn.commit()
    ent_section_name.delete(0, tk.END)
    refresh_all()

def load_sections_table():
    tree_section.delete(*tree_section.get_children())
    cur.execute("SELECT c.class_name, s.section_name FROM sections s JOIN classes c ON s.class_id=c.id ORDER BY c.class_name, s.section_name")
    for r in cur.fetchall():
        tree_section.insert("", tk.END, values=r)

def edit_section():
    sel = tree_section.selection()
    if not sel:
        messagebox.showwarning("Select", "Select a section to edit.")
        return
    sid, classname, old = tree_section.item(sel, "values")
    new = simple_input("Edit Section", f"New name for section (Class: {classname}):", old)
    if new:
        cur.execute("UPDATE sections SET section_name=? WHERE id=?", (new, sid))
        conn.commit()
        refresh_all()

def delete_section():
    sel = tree_section.selection()
    if not sel:
        messagebox.showwarning("Select", "Select a section to delete.")
        return
    sid = tree_section.item(sel, "values")[0]
    if not confirm("Deleting a section will delete its students and attendance. Continue?"):
        return
    cur.execute("SELECT id FROM students WHERE section_id=?", (sid,))
    sids = [r[0] for r in cur.fetchall()]
    if sids:
        cur.executemany("DELETE FROM attendance WHERE student_id=?", [(x,) for x in sids])
    cur.execute("DELETE FROM students WHERE section_id=?", (sid,))
    cur.execute("DELETE FROM sections WHERE id=?", (sid,))
    conn.commit()
    refresh_all()

ttk.Label(frm_section, text="Select Class:").pack(padx=10, pady=(12,2), anchor="w")
combo_section_class = ttk.Combobox(frm_section, width=36, state="readonly")
combo_section_class.pack(padx=10, pady=4, anchor="w")
ttk.Label(frm_section, text="New Section Name:").pack(padx=10, pady=(8,2), anchor="w")
ent_section_name = ttk.Entry(frm_section, width=36)
ent_section_name.pack(padx=10, pady=4, anchor="w")
ttk.Button(frm_section, text="Add Section", command=add_section).pack(padx=10, pady=6, anchor="w")

cols2 = ("Class", "Section")
tree_section = ttk.Treeview(frm_section, columns=cols2, show="headings", height=10)
for c in cols2:
    tree_section.heading(c, text=c,anchor="center")
    tree_section.column(c, width=220,anchor="center")
tree_section.pack(padx=10, pady=8, fill="x",anchor="center")
btnf2 = ttk.Frame(frm_section); btnf2.pack(padx=10, pady=6, anchor="w")
ttk.Button(btnf2, text="Edit Section", command=edit_section).grid(row=0, column=0, padx=6)
ttk.Button(btnf2, text="Delete Section", command=delete_section).grid(row=0, column=1, padx=6)

# -------------------- STUDENT CRUD --------------------
def on_class_selected_for_student(event=None):
    combo_student_section['values'] = []
    if not combo_student_class.get():
        return
    cid = combo_student_class.get()
    cur.execute("SELECT section_name FROM sections WHERE class_id=? ORDER BY section_name", (cid,))
    combo_student_section['values'] = [f"{r[0]}" for r in cur.fetchall()]

def add_student():
    name = ent_student_name.get().strip()
    if not name:
        messagebox.showwarning("Input", "Enter student name.")
        return
    if not combo_student_class.get() or not combo_student_section.get():
        messagebox.showwarning("Select", "Choose class and section.")
        return
    cid = combo_student_class.get()
    sid = combo_student_section.get()
    cur.execute("INSERT INTO students(name, class_id, section_id) VALUES(?,?,?)", (name, cid, sid))
    conn.commit()
    ent_student_name.delete(0, tk.END)
    refresh_all()

def load_students_table():
    tree_student.delete(*tree_student.get_children())
    cur.execute('''SELECT s.id, s.name, c.class_name, se.section_name
                   FROM students s
                   JOIN classes c ON s.class_id=c.id
                   JOIN sections se ON s.section_id=se.id
                   ORDER BY c.class_name, se.section_name, s.name''')
    for r in cur.fetchall():
        tree_student.insert("", tk.END, values=r)

def edit_student():
    sel = tree_student.selection()
    if not sel:
        messagebox.showwarning("Select", "Select a student to edit.")
        return
    sid, oldname, *_ = tree_student.item(sel, "values")
    new = simple_input("Edit Student", "New name:", oldname)
    if new:
        cur.execute("UPDATE students SET name=? WHERE id=?", (new, sid))
        conn.commit()
        refresh_all()

def delete_student():
    sel = tree_student.selection()
    if not sel:
        messagebox.showwarning("Select", "Select a student to delete.")
        return
    sid = tree_student.item(sel, "values")[0]
    if not confirm("Delete student and related attendance?"):
        return
    cur.execute("DELETE FROM attendance WHERE student_id=?", (sid,))
    cur.execute("DELETE FROM students WHERE id=?", (sid,))
    conn.commit()
    refresh_all()

def refresh_class_filter():
    cur.execute("SELECT class_name FROM classes ORDER BY class_name")
    combo_filter_class['values'] = [r[0] for r in cur.fetchall()]
    combo_filter_class.set('')

def on_filter_class_selected(event=None):
    combo_filter_section['values'] = []
    class_name = combo_filter_class.get().strip()
    if not class_name:
        return
    cur.execute("SELECT id FROM classes WHERE class_name=?", (class_name,))
    row = cur.fetchone()
    if not row:
        return
    cid = row[0]
    cur.execute("SELECT section_name FROM sections WHERE class_id=? ORDER BY section_name", (cid,))
    combo_filter_section['values'] = [r[0] for r in cur.fetchall()]
    combo_filter_section.set('')
    load_students()

def on_filter_section_selected(event=None):
    load_students()

def load_students():
    """Loads students according to selected filter"""
    tree_student.delete(*tree_student.get_children())
    if show_all_var.get():
        cur.execute("""
            SELECT s.id, s.name, c.class_name, sec.section_name
            FROM students s
            JOIN classes c ON s.class_id=c.id
            JOIN sections sec ON s.section_id=sec.id
            ORDER BY c.class_name, sec.section_name, s.name
        """)
    else:
        class_name = combo_filter_class.get().strip()
        section_name = combo_filter_section.get().strip()

        if not class_name:
            return

        cur.execute("SELECT id FROM classes WHERE class_name=?", (class_name,))
        c_row = cur.fetchone()
        if not c_row:
            return
        cid = c_row[0]

        if section_name:
            cur.execute("""
                SELECT s.id, s.name, c.class_name, sec.section_name
                FROM students s
                JOIN classes c ON s.class_id=c.id
                JOIN sections sec ON s.section_id=sec.id
                WHERE s.class_id=? AND s.section_id=(SELECT id FROM sections WHERE section_name=? AND class_id=?)
                ORDER BY s.name
            """, (cid, section_name, cid))
        else:
            cur.execute("""
                SELECT s.id, s.name, c.class_name, sec.section_name
                FROM students s
                JOIN classes c ON s.class_id=c.id
                JOIN sections sec ON s.section_id=sec.id
                WHERE s.class_id=?
                ORDER BY sec.section_name, s.name
            """, (cid,))

    for r in cur.fetchall():
        tree_student.insert("", tk.END, values=r)


ttk.Label(frm_student, text="Select Class:").pack(padx=10, pady=(12,2), anchor="w")
combo_student_class = ttk.Combobox(frm_student, width=36, state="readonly")
combo_student_class.bind("<<ComboboxSelected>>", on_class_selected_for_student)
combo_student_class.pack(padx=10, pady=4, anchor="w")

ttk.Label(frm_student, text="Select Section:").pack(padx=10, pady=(8,2), anchor="w")
combo_student_section = ttk.Combobox(frm_student, width=36, state="readonly")
combo_student_section.pack(padx=10, pady=4, anchor="w")

ttk.Label(frm_student, text="Student Name:").pack(padx=10, pady=(8,2), anchor="w")
ent_student_name = ttk.Entry(frm_student, width=36)
ent_student_name.pack(padx=10, pady=4, anchor="w")
ttk.Button(frm_student, text="Add Student", command=add_student).pack(padx=10, pady=6, anchor="w")

# Filters row
filter_frame = ttk.Frame(frm_student)
filter_frame.pack(padx=10, pady=10, fill='x')

# Class Filter
lbl_filter_class = ttk.Label(filter_frame, text="Class:")
lbl_filter_class.grid(row=0, column=0, padx=5, pady=5)
combo_filter_class = ttk.Combobox(filter_frame, state='readonly', width=20)
combo_filter_class.grid(row=0, column=1, padx=5, pady=5)

# Section Filter
lbl_filter_section = ttk.Label(filter_frame, text="Section:")
lbl_filter_section.grid(row=0, column=2, padx=5, pady=5)
combo_filter_section = ttk.Combobox(filter_frame, state='readonly', width=20)
combo_filter_section.grid(row=0, column=3, padx=5, pady=5)
combo_filter_class.bind("<<ComboboxSelected>>", on_filter_class_selected)
combo_filter_section.bind("<<ComboboxSelected>>", on_filter_section_selected)



# Show All Checkbox
show_all_var = tk.BooleanVar(value=True)
chk_show_all = ttk.Checkbutton(filter_frame, text="Show All Students", variable=show_all_var, command=lambda: load_students())
chk_show_all.grid(row=0, column=4, padx=10)

# Treeview for Students
tree_student = ttk.Treeview(frm_student, columns=("ID", "Name", "Class", "Section"), show="headings", height=15)
tree_student.heading("ID", text="ID")
tree_student.heading("Name", text="Name")
tree_student.heading("Class", text="Class")
tree_student.heading("Section", text="Section")
tree_student.pack(padx=10, pady=10, fill='both', expand=True)

# Scrollbars
scroll_y = ttk.Scrollbar(frm_student, orient="vertical", command=tree_student.yview)
tree_student.configure(yscrollcommand=scroll_y.set)
scroll_y.pack(side='right', fill='y', padx=(0,10))
btns3 = ttk.Frame(frm_student); btns3.pack(padx=10, pady=6, anchor="w")
ttk.Button(btns3, text="Edit Student", command=edit_student).grid(row=0, column=0, padx=6)
ttk.Button(btns3, text="Delete Student", command=delete_student).grid(row=0, column=1, padx=6)

# -------------------- ATTENDANCE CRUD & TAKE --------------------
def on_att_class_selected(event=None):
    combo_att_section['values'] = []
    if not combo_att_class.get():
        return
    cid = combo_att_class.get()
    cur.execute("SELECT section_name FROM sections WHERE class_id=? ORDER BY section_name", (cid,))
    combo_att_section['values'] = [f"{r[0]}" for r in cur.fetchall()]

def load_students_for_attendance():
    tree_take.delete(*tree_take.get_children())
    if not combo_att_section.get():
        messagebox.showwarning("Select", "Select class & section")
        return
    secid = combo_att_section.get()
    cur.execute("SELECT id, name FROM students WHERE section_id=? ORDER BY name", (secid,))
    for r in cur.fetchall():
        tree_take.insert("", tk.END, values=r)
    # reset status_vars
    status_vars.clear()
    for item in tree_take.get_children():
        status_vars[item] = tk.StringVar(value="Present")

def save_attendance():
    d = date_entry.get_date().strftime("%Y-%m-%d")
    # Before inserting, avoid duplicate entries for same student & date.
    for item in tree_take.get_children():
        sid, name = tree_take.item(item, "values")
        status = status_vars[item].get()
        # If an entry exists, update; else insert
        cur.execute("SELECT id FROM attendance WHERE student_id=? AND date=?", (sid, d))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE attendance SET status=? WHERE id=?", (status, row[0]))
        else:
            cur.execute("INSERT INTO attendance(student_id, date, status) VALUES(?,?,?)", (sid, d, status))
    conn.commit()
    load_attendance_table()
    messagebox.showinfo("Saved", "Attendance saved/updated for date: " + d)

def status_cell_click(event):
    # for convenience, toggle between Present/Absent on double-click on tree_take row
    item = tree_take.identify_row(event.y)
    if not item: return
    curval = status_vars.get(item)
    if not curval: return
    new = "Absent" if curval.get() == "Present" else "Present"
    curval.set(new)
    # also show in a small column (we will display status via separate listbox)
    # We don't have visible status column here; we rely on selection + radio in UI below.

def load_attendance_table():
    tree_att.delete(*tree_att.get_children())
    cur.execute('''SELECT a.id, s.name, c.class_name, se.section_name, a.date, a.status
                   FROM attendance a
                   JOIN students s ON a.student_id=s.id
                   JOIN classes c ON s.class_id=c.id
                   JOIN sections se ON s.section_id=se.id
                   ORDER BY a.date DESC, c.class_name, se.section_name, s.name''')
    for r in cur.fetchall():
        tree_att.insert("", tk.END, values=r)

def edit_attendance():
    sel = tree_att.selection()
    if not sel:
        messagebox.showwarning("Select", "Select attendance record.")
        return
    aid, name, cls, sec, date_, old = tree_att.item(sel, "values")
    new = simple_input("Edit Attendance", f"Status for {name} on {date_} (Present/Absent):", old)
    if new:
        cur.execute("UPDATE attendance SET status=? WHERE id=?", (new, aid))
        conn.commit()
        load_attendance_table()

def delete_attendance():
    sel = tree_att.selection()
    if not sel:
        messagebox.showwarning("Select", "Select attendance record.")
        return
    aid = tree_att.item(sel, "values")[0]
    if not confirm("Delete selected attendance record?"):
        return
    cur.execute("DELETE FROM attendance WHERE id=?", (aid,))
    conn.commit()
    load_attendance_table()

ttk.Label(frm_attendance, text="Select Class:").grid(row=0, column=0, padx=10, pady=(12,4), sticky="w")
combo_att_class = ttk.Combobox(frm_attendance, width=28, state="readonly")
combo_att_class.grid(row=0, column=1, padx=8, pady=(12,4), sticky="w")
combo_att_class.bind("<<ComboboxSelected>>", on_att_class_selected)

ttk.Label(frm_attendance, text="Select Section:").grid(row=1, column=0, padx=10, pady=4, sticky="w")
combo_att_section = ttk.Combobox(frm_attendance, width=28, state="readonly")
combo_att_section.grid(row=1, column=1, padx=8, pady=4, sticky="w")

ttk.Label(frm_attendance, text="Select Date:").grid(row=2, column=0, padx=10, pady=4, sticky="w")
date_entry = DateEntry(frm_attendance, width=18, date_pattern="yyyy-mm-dd")
date_entry.grid(row=2, column=1, padx=8, pady=4, sticky="w")

ttk.Button(frm_attendance, text="Load Students", command=load_students_for_attendance).grid(row=3, column=0, padx=10, pady=8, sticky="w")
ttk.Button(frm_attendance, text="Save Attendance", command=save_attendance).grid(row=3, column=1, padx=8, pady=8, sticky="w")

cols_take = ("Student ID", "Name")
tree_take = ttk.Treeview(frm_attendance, columns=cols_take, show="headings", height=12)
for i,c in enumerate(cols_take):
    tree_take.heading(c, text=c,anchor="center")
    tree_take.column(c, width=220,anchor="center")
tree_take.grid(row=4, column=0, columnspan=3, padx=10, pady=6, sticky="nsew")

# Status radio frame (maps to selected row in the tree)
status_vars = {}
status_frame = ttk.Frame(frm_attendance)
status_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=6, sticky="w")
ttk.Label(status_frame, text="(When you 'Load Students' each row gets default status 'Present'. To change status before saving, select a row and choose:)").pack(anchor="w")
status_radio_frame = ttk.Frame(status_frame); status_radio_frame.pack(anchor="w", pady=4)
status_choice = tk.StringVar(value="Present")
ttk.Radiobutton(status_radio_frame, text="Present", variable=status_choice, value="Present").grid(row=0,column=0, padx=6)
ttk.Radiobutton(status_radio_frame, text="Absent", variable=status_choice, value="Absent").grid(row=0,column=1, padx=6)

def apply_status_to_selected():
    sel = tree_take.selection()
    if not sel:
        messagebox.showwarning("Select", "Select a student row to change status.")
        return
    for item in sel:
        if item in status_vars:
            status_vars[item].set(status_choice.get())
    messagebox.showinfo("Applied", f"Status set to '{status_choice.get()}' for selected rows.")

ttk.Button(status_frame, text="Apply Status to Selected Rows", command=apply_status_to_selected).pack(anchor="w", pady=4)

# Attendance table for edit/delete operations
cols_att = ("AID", "Student", "Class", "Section", "Date", "Status")
tree_att = ttk.Treeview(frm_attendance, columns=cols_att, show="headings", height=10)
for c in cols_att:
    tree_att.heading(c, text=c,anchor="center")
    tree_att.column(c, width=160,anchor="center")
tree_att.grid(row=6, column=0, columnspan=3, padx=10, pady=8, sticky="nsew")
btn_att = ttk.Frame(frm_attendance); btn_att.grid(row=7, column=0, columnspan=3, pady=6)
ttk.Button(btn_att, text="Edit Attendance Record", command=edit_attendance).grid(row=0, column=0, padx=6)
ttk.Button(btn_att, text="Delete Attendance Record", command=delete_attendance).grid(row=0, column=1, padx=6)

# -------------------- CLASS-WISE MONTHLY REPORT --------------------
def generate_class_month_report():
    tree_class_report.delete(*tree_class_report.get_children())
    txt_class_summary.delete("1.0", tk.END)

    selected_class = combo_class_report.get().strip()
    year = combo_year_report.get().strip()
    month = combo_month_report.get().strip()

    if not selected_class or not year or not month:
        messagebox.showwarning("Select", "Please select Class, Month and Year.")
        return

    # Get month number
    month_num = datetime.strptime(month, "%B").strftime("%m")

    # Fetch students belonging to that class
    try:
        cur.execute("""
            SELECT s.id, s.name 
            FROM students s
            JOIN classes c ON s.class_id = c.id
            WHERE c.class_name = ?
            ORDER BY s.name
        """, (selected_class,))
    except sqlite3.OperationalError:
        # fallback if 'class_name' column is 'name' in classes table
        cur.execute("""
            SELECT s.id, s.name 
            FROM students s
            JOIN classes c ON s.class_id = c.id
            WHERE c.name = ?
            ORDER BY s.name
        """, (selected_class,))

    students = cur.fetchall()
    if not students:
        messagebox.showinfo("Info", "No students found in selected class.")
        return

    # Get total working days for that class in the given month
    cur.execute('''
        SELECT COUNT(DISTINCT date)
        FROM attendance
        WHERE strftime('%Y', date)=? AND strftime('%m', date)=?
    ''', (year, month_num))
    total_class_days = cur.fetchone()[0] or 0

    for sid, name in students:
        # Count student's attendance in that month
        cur.execute('''
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present_days
            FROM attendance
            WHERE student_id=? AND strftime('%Y', date)=? AND strftime('%m', date)=?
        ''', (sid, year, month_num))
        res = cur.fetchone()
        total = res[0] or 0
        present = res[1] or 0
        absent = (total_class_days - present) if total_class_days else 0
        percent = (present / total_class_days * 100) if total_class_days else 0
        tree_class_report.insert("", tk.END, values=(sid, name, total_class_days, present, absent, f"{percent:.2f}%"))

    txt_class_summary.insert(tk.END, f"Total Working Days in {month} {year}: {total_class_days}\n")
    txt_class_summary.insert(tk.END, "Click a student row to check their yearly percentage.\n")


def on_student_select(event):
    selected = tree_class_report.focus()
    if not selected:
        return
    sid = tree_class_report.item(selected)["values"][0]
    year = combo_year_report.get().strip()

    # Fetch student ID
    cur.execute("SELECT name FROM students WHERE id=?", (sid,))
    student_name = cur.fetchone()[0]

    # Yearly stats for that student
    cur.execute('''
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present
        FROM attendance
        WHERE student_id=? AND strftime('%Y', date)=?
    ''', (sid, year))
    total, present = cur.fetchone()
    percent = (present / total * 100) if total else 0

    txt_class_summary.delete("1.0", tk.END)
    txt_class_summary.insert(tk.END, f"Student: {student_name}\n")
    txt_class_summary.insert(tk.END, f"Year: {year}\n")
    txt_class_summary.insert(tk.END, f"Total Days Recorded: {total}\n")
    txt_class_summary.insert(tk.END, f"Total Presents: {present}\n")
    txt_class_summary.insert(tk.END, f"Overall Attendance: {percent:.2f}%\n")


# ----------- UI for Class-wise Monthly Report -------------
frame_class_report = ttk.LabelFrame(frm_view, text="Class-wise Monthly Attendance Report")
frame_class_report.pack(fill="both", expand=True, padx=10, pady=10)

# Class dropdown
ttk.Label(frame_class_report, text="Select Class:").grid(row=0, column=0, padx=6, pady=4, sticky="w")
combo_class_report = ttk.Combobox(frame_class_report, width=12, state="readonly")
combo_class_report.grid(row=0, column=1, padx=6, pady=4, sticky="w")

# Year dropdown
ttk.Label(frame_class_report, text="Select Year:").grid(row=0, column=2, padx=6, pady=4, sticky="w")
combo_year_report = ttk.Combobox(frame_class_report, width=10, state="readonly")
combo_year_report['values'] = [str(y) for y in range(2023, datetime.now().year + 1)]
combo_year_report.grid(row=0, column=3, padx=6, pady=4, sticky="w")

# Month dropdown
ttk.Label(frame_class_report, text="Select Month:").grid(row=0, column=4, padx=6, pady=4, sticky="w")
combo_month_report = ttk.Combobox(frame_class_report, width=12, state="readonly")
combo_month_report['values'] = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
combo_month_report.grid(row=0, column=5, padx=6, pady=4, sticky="w")

ttk.Button(frame_class_report, text="Generate Report", command=generate_class_month_report).grid(row=0, column=6, padx=10, pady=4)

# Treeview for Class Report
cols_class_report = ("ID", "Student", "Total Days", "Present", "Absent", "Percentage")
tree_class_report = ttk.Treeview(frame_class_report, columns=cols_class_report, show="headings", height=12)
for c in cols_class_report:
    tree_class_report.heading(c, text=c, anchor="center")
    tree_class_report.column(c, width=150, anchor="center")
tree_class_report.grid(row=1, column=0, columnspan=7, padx=10, pady=6, sticky="nsew")

tree_class_report.bind("<<TreeviewSelect>>", on_student_select)

# Summary box
txt_class_summary = tk.Text(frame_class_report, height=5)
txt_class_summary.grid(row=2, column=0, columnspan=7, padx=10, pady=6, sticky="ew")

frame_class_report.grid_rowconfigure(1, weight=1)
frame_class_report.grid_columnconfigure(6, weight=1)


# -------------------- Load Class Names into Dropdown --------------------
def load_class_report_classes():
    try:
        cur.execute("""
            SELECT DISTINCT c.class_name
            FROM classes c
            JOIN students s ON s.class_id = c.id
            ORDER BY c.class_name
        """)
    except sqlite3.OperationalError:
        cur.execute("""
            SELECT DISTINCT c.name
            FROM classes c
            JOIN students s ON s.class_id = c.id
            ORDER BY c.name
        """)
    combo_class_report['values'] = [r[0] for r in cur.fetchall()]

# Call once at startup
load_class_report_classes()






# -------------------- Initial load --------------------
status_vars = {}
load_class_combos()
refresh_all()

# Make tree_take selectable and attach selection to status radio
def on_take_select(event):
    sel = tree_take.selection()
    if sel:
        # synchronize single selection to radio display
        item = sel[0]
        val = status_vars.get(item, tk.StringVar("Present")).get()
        status_choice.set(val)

tree_take.bind("<<TreeviewSelect>>", on_take_select)

# Make sure UI expands nicely
for f in [frm_attendance, frm_view]:
    f.grid_columnconfigure(2, weight=1)
    f.grid_rowconfigure(4, weight=1)
    
refresh_class_filter()
load_students()

root.mainloop()
