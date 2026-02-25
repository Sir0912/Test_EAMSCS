from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_socketio import SocketIO
from datetime import datetime
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
import io, csv

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
app.secret_key = "blackpower"


connection = pymysql.connect(
    host="localhost",
    user="root",
    password="Myservermybestfriend09941991294",
    database="opti_test",  
    cursorclass=pymysql.cursors.DictCursor
)
cursor = connection.cursor()

# Admin Credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")


def get_salary_per_minute():
    cursor.execute("SELECT salary_per_minute FROM opti_settings WHERE id = 1")
    result = cursor.fetchone()
    if result:
        return float(result["salary_per_minute"])
    return 5.00  # Default


@app.route("/", methods=["GET"])
def landing_page():
    return render_template("admin_login.html", error=None)

@app.route("/log_in_admin", methods=["POST"])
def log_in_admin():
    admin = request.form.get('username')
    password = request.form.get('password')
    if admin == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        session["admin"] = admin
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html", error="Invalid credentials")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("landing_page"))

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT opti.name, opti_rec.time_in, opti_rec.time_out, 
               opti_rec.duration, opti_rec.salary,
               opti_rec.late_minutes, opti_rec.undertime_minutes,
               opti_rec.id, opti_rec.id_employee
        FROM opti_rec
        JOIN opti ON opti_rec.id_employee = opti.id_employee
        WHERE DATE(opti_rec.time_in)=%s
        ORDER BY opti_rec.id DESC
    """, (today,))
    records = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS total FROM opti")
    total_employees = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS present FROM opti_rec WHERE DATE(time_in)=%s", (today,))
    present_today = cursor.fetchone()["present"]

    cursor.execute("SELECT IFNULL(SUM(salary),0) AS total_salary FROM opti_rec WHERE DATE(time_in)=%s", (today,))
    total_salary = cursor.fetchone()["total_salary"]

    cursor.execute("SELECT * FROM opti ORDER BY id_employee ASC")
    employees = cursor.fetchall()
    
    # Get salary rate from database
    salary_rate = get_salary_per_minute()

    return render_template(
        "admin_dashboard.html",
        admin_name=session.get("admin","Admin"),
        total_employees=total_employees,
        present_today=present_today,
        total_salary=total_salary,
        records=records,
        employees=employees,
        salary_rate=salary_rate
    )

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("landing_page"))


# ============================================
# SALARY RATE API ROUTES
# ============================================
@app.route("/api/get_salary_rate", methods=["GET"])
def get_salary_rate():
    salary_rate = get_salary_per_minute()
    return jsonify({"salary_per_minute": salary_rate})

@app.route("/api/update_salary_rate", methods=["POST"])
def update_salary_rate():
    data = request.json
    new_rate = float(data.get("salary_per_minute", 5.00))
    
    cursor.execute("UPDATE opti_settings SET salary_per_minute = %s WHERE id = 1", (new_rate,))
    connection.commit()
    
    return jsonify({
        "status": "success",
        "salary_per_minute": new_rate
    })


# ============================================
# EMPLOYEE MANAGEMENT ROUTES
# ============================================
@app.route("/add_employee", methods=["POST"])
def add_employee():
    data = request.form
    name = data.get('name_inp')
    age = data.get('age_inp')
    sex = data.get('sex_inp')
    email = data.get('email_inp')
    number = data.get("num_inp")
    rfid = data.get('rfid_inp')

    # Get next available ID
    cursor.execute("SELECT id_employee FROM opti ORDER BY id_employee ASC")
    existing_ids = [row['id_employee'] for row in cursor.fetchall()]
    next_id = 1
    for eid in existing_ids:
        if eid == next_id: 
            next_id += 1
        else: 
            break

    cursor.execute(
        "INSERT INTO opti (id_employee, name, age, sex, email, number, rfid) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (next_id, name, age, sex, email, number, rfid)
    )
    connection.commit()
    cursor.execute("SELECT * FROM opti WHERE id_employee=%s", (next_id,))
    new_emp = cursor.fetchone()
    return jsonify(new_emp)

@app.route("/drop_employee", methods=["POST"])
def drop_employee():
    emp_id = int(request.form.get("employ_id"))
    cursor.execute("DELETE FROM opti WHERE id_employee=%s", (emp_id,))
    connection.commit()
    cursor.execute("SELECT id_employee FROM opti ORDER BY id_employee ASC")
    employees = cursor.fetchall()
    for index, emp in enumerate(employees, start=1):
        if emp['id_employee'] != index:
            cursor.execute("UPDATE opti SET id_employee=%s WHERE id_employee=%s", (index, emp['id_employee']))
    connection.commit()
    return jsonify({"status": "success"})


# ============================================
# EXPORT TO EXCEL
# ============================================
@app.route("/export_excel")
def export_excel():
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT opti.name, opti_rec.time_in, opti_rec.time_out, opti_rec.duration, opti_rec.salary
        FROM opti_rec
        JOIN opti ON opti_rec.id_employee = opti.id_employee
        WHERE DATE(opti_rec.time_in)=%s
        ORDER BY opti_rec.id DESC
    """, (today,))
    records = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Time In", "Time Out", "Duration (min)", "Salary"])
    for r in records:
        writer.writerow([
            r["name"],
            r["time_in"].strftime("%H:%M") if r["time_in"] else "",
            r["time_out"].strftime("%H:%M") if r["time_out"] else "",
            r.get("duration",""),
            r.get("salary","")
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"attendance_{today}.csv"
    )


# ============================================
# SCAN API
# ============================================
@app.route("/scan", methods=["POST"])
def scan():
    uid = request.json.get("uid")

    # Check RFID
    cursor.execute("SELECT * FROM opti WHERE rfid=%s", (uid,))
    employee = cursor.fetchone()
    if not employee:
        return jsonify({"status": "not_found"})

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d")

    # Check today's record
    cursor.execute(
        "SELECT * FROM opti_rec WHERE id_employee=%s AND DATE(time_in)=%s",
        (employee["id_employee"], now_str)
    )
    record = cursor.fetchone()

    # First scan → Time In
    if not record:
        cursor.execute(
            "INSERT INTO opti_rec (id_employee, time_in) VALUES (%s, %s)",
            (employee["id_employee"], now)
        )
        connection.commit()
        
        # Get the new record ID
        cursor.execute("SELECT id FROM opti_rec WHERE id_employee=%s AND time_in=%s", 
                      (employee["id_employee"], now))
        new_record = cursor.fetchone()

        # Emit real-time attendance - NEW ROW
        socketio.emit("attendance_update", {
            "action": "time_in",
            "record_id": new_record["id"],
            "employee_id": employee["id_employee"],
            "name": employee["name"],
            "time_in": now.strftime("%I:%M %p"),
            "time_out": "-",
            "duration": "0h 0m",
            "salary": 0
        })

        return jsonify({
            "status": "time_in",
            "time": now.strftime("%Y-%m-%d %I:%M %p")
        })

    # Second scan → Time Out
    elif record and not record["time_out"]:
        time_in_db = record["time_in"]
        if isinstance(time_in_db, str):
            time_in_db = datetime.strptime(time_in_db, "%Y-%m-%d %H:%M:%S")

        duration_min = int((now - time_in_db).total_seconds() // 60)
        
        # Get salary rate from database
        salary_per_minute = get_salary_per_minute()
        salary = duration_min * salary_per_minute

        cursor.execute(
            "UPDATE opti_rec SET time_out=%s, duration=%s, salary=%s WHERE id=%s",
            (now, duration_min, salary, record["id"])
        )
        connection.commit()

        # Convert duration to h m format
        hours = duration_min // 60
        minutes = duration_min % 60
        duration_str = f"{hours}h {minutes}m"

        # Emit real-time attendance - UPDATE EXISTING ROW
        socketio.emit("attendance_update", {
            "action": "time_out",
            "record_id": record["id"],
            "employee_id": employee["id_employee"],
            "name": employee["name"],
            "time_in": time_in_db.strftime("%I:%M %p"),
            "time_out": now.strftime("%I:%M %p"),
            "duration": duration_str,
            "salary": salary
        })

        return jsonify({
            "status": "time_out",
            "time": now.strftime("%Y-%m-%d %I:%M %p"),
            "duration": duration_str,
            "salary": salary
        })

    else:
        return jsonify({"status": "already_done"})


# ============================================
# MONTHLY PAYROLL
# ============================================
@app.route("/monthly_payroll")
def monthly_payroll():
    if "admin" not in session:
        return redirect(url_for("landing_page"))

    today = datetime.now()
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    month_end = today.strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT o.name, 
               SUM(r.duration) AS total_minutes, 
               SUM(r.salary) AS total_salary,
               SUM(r.late_minutes) AS total_late,
               SUM(r.undertime_minutes) AS total_undertime
        FROM opti_rec r
        JOIN opti o ON r.id_employee = o.id_employee
        WHERE DATE(r.time_in) BETWEEN %s AND %s
        GROUP BY o.id_employee
        ORDER BY o.id_employee ASC
    """, (month_start, month_end))

    payrolls = cursor.fetchall()
    return render_template("monthly_payroll.html", payrolls=payrolls, month=today.strftime("%B %Y"))


if __name__ == "__main__":
    socketio.run(app, port=5000, debug=True)