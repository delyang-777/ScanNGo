from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import mysql.connector
import qrcode
from io import BytesIO
import secrets
from flask import request, redirect, url_for, flash
from flask import jsonify
from datetime import datetime
import pandas as pd
from flask import Response
import qrcode
from flask import send_file
from flask import request, redirect, url_for, flash, render_template
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from flask import make_response
from fpdf import FPDF







app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # replace with your own

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/scanngo'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Login Manager ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Database Connection ---
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='scanngo'
    )

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    email = db.Column(db.String(150), unique=True)
    # full_name = db.Column(db.String(150))
    # age = db.Column(db.Integer)
    # year_level = db.Column(db.String(50))
    # status = db.Column(db.String(50))
    # citizenship = db.Column(db.String(100))
    # address = db.Column(db.String(255))
    # place_of_birth = db.Column(db.String(150))
    role = db.Column(db.String(50), nullable=False, default="user")
    
    
class PendingProfileUpdate(db.Model):
    __tablename__ = 'pending_profile_updates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(150))
    email = db.Column(db.String(150))
    full_name = db.Column(db.String(150))
    age = db.Column(db.Integer)
    year_level = db.Column(db.String(50))
    status = db.Column(db.String(50))
    citizenship = db.Column(db.String(100))
    address = db.Column(db.String(255))
    place_of_birth = db.Column(db.String(150))
    role = db.Column(db.String(50), nullable=False, default="user")
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)  # admin will approve
    
    
with app.app_context():
    db.create_all()

        
# --- Load User ---
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return User(id=row['id'], username=row['username'], email=row['email'], role=row['role'])
    return None

# --- Home ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard' if current_user.role == 'admin' else 'student_dashboard'))
    return redirect(url_for('login'))

# --- Admin Dashboard ---
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Connect to MySQL
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user_row = cursor.fetchone()
        cursor.close()
        conn.close()

        if user_row:
            # Check password
            if check_password_hash(user_row['password_hash'], password):
                # Create a User instance properly
                user_obj = User()
                user_obj.id = user_row['id']
                user_obj.username = user_row['username']
                user_obj.email = user_row['email']
                user_obj.role = user_row['role']
                # Log in user
                login_user(user_obj)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid email or password.', 'danger')
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


# --- Logout ---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- Register ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash('Email already registered.', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('login'))

        cursor.execute(
            'INSERT INTO users (username, email, password_hash, role, approved, active) VALUES (%s,%s,%s,%s,1,1)',
            (username, email, password, role)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# --- Manage Events ---
@app.route('/manage_events', methods=['GET'])
@login_required
def manage_events():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Upcoming events = today and future events
    cursor.execute("""
        SELECT * FROM events
        WHERE event_date >= CURDATE()
        ORDER BY event_date ASC
    """)
    upcoming_events = cursor.fetchall()

    # Recent (past) events = dates before today
    cursor.execute("""
        SELECT * FROM events
        WHERE event_date < CURDATE()
        ORDER BY event_date DESC
    """)
    recent_events = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'manage_events.html',
        upcoming_events=upcoming_events,
        recent_events=recent_events
    )


# --- Add Event ---
@app.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        event_date = request.form.get('event_date')
        location = request.form.get('location')

        if not title or not description or not event_date:
            flash("Please fill in all required fields!", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('add_event'))

        try:
            cursor.execute(
                "INSERT INTO events (title, description, event_date, location) "
                "VALUES (%s, %s, %s, %s)",
                (title, description, event_date, location)
            )
            conn.commit()
            flash("Event added successfully!", "success")
            return redirect(url_for('manage_events'))
        except mysql.connector.Error as e:
            flash(f"Database error: {e}", "danger")
            return redirect(url_for('add_event'))
        finally:
            cursor.close()
            conn.close()

    cursor.close()
    conn.close()
    return render_template('add_event.html')

# --- Edit Event ---
@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
    event = cursor.fetchone()

    if not event:
        flash("Event not found.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('manage_events'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        event_date = request.form.get('event_date')
        location = request.form.get('location')

        if not title or not event_date:
            flash("Please fill in the required fields: title and date!", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('edit_event', event_id=event_id))

        cursor.execute("""
            UPDATE events
            SET title=%s, description=%s, event_date=%s, location=%s
            WHERE id=%s
        """, (title, description, event_date, location, event_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Event updated successfully!", "success")
        return redirect(url_for('manage_events'))

    cursor.close()
    conn.close()
    return render_template('edit_event.html', event=event)

# --- Delete Event ---
@app.route('/delete_event/<int:event_id>')
@login_required
def delete_event(event_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE id=%s", (event_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Event deleted successfully!", "success")
    return redirect(url_for('manage_events'))

# --- Event List ---
@app.route('/event_list')
@login_required
def event_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('event_list.html', events=events)

@app.route('/view_dashboard')
@login_required
def view_dashboard():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Total members
    cursor.execute("SELECT COUNT(*) AS total_members FROM users")
    total_members = cursor.fetchone()['total_members']

    # Total check-ins
    cursor.execute("SELECT COUNT(*) AS total_checkins FROM attendance")
    total_checkins = cursor.fetchone()['total_checkins']

    # Calculate attendance percentage safely
    attendance_percentage = (total_checkins / total_members * 100) if total_members > 0 else 0

    # Upcoming 3 events
    cursor.execute("SELECT * FROM events ORDER BY event_date ASC LIMIT 3")
    upcoming_events = cursor.fetchall()

    # Most recent 3 scans
    cursor.execute("SELECT * FROM attendance ORDER BY checked_at DESC LIMIT 3")
    recent_scans = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'view_dashboard.html',
        total_members=total_members,
        attendance_percentage=attendance_percentage,
        upcoming_events=upcoming_events,
        recent_scans=recent_scans
    )


# --- Manage Members ---
@app.route('/manage_members')
@login_required
def manage_members():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users ORDER BY username ASC")
    members = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('manage_members.html', members=members)


@app.route('/admin/members/add', methods=['GET', 'POST'])
@login_required
def add_member():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        # add other fields as needed

        if not username or not email:
            flash("Please fill in all required fields.", "warning")
            return redirect(url_for('add_member'))

        conn = get_db_connection()  # create connection
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "INSERT INTO users (username, email, role, approved, active) VALUES (%s, %s, %s, 1, 1)",
                (username, email, 'student')  # you can adjust role if needed
            )
            conn.commit()
            flash(f"Member {username} added successfully!", "success")
            return redirect(url_for('manage_members'))
        except Exception as e:
            flash(f"Error adding member: {str(e)}", "danger")
            return redirect(url_for('add_member'))
        finally:
            cursor.close()
            conn.close()

    return render_template('add_member.html')



@app.route('/admin/members/edit/<int:member_id>', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s", (member_id,))
    member = cursor.fetchone()

    if not member:
        flash("Member not found.", "warning")
        return redirect(url_for('manage_members'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        # update other fields as needed

        cursor.execute("""
            UPDATE users SET username=%s, email=%s WHERE id=%s
        """, (username, email, member_id))
        conn.commit()
        flash("Member updated successfully!", "success")
        return redirect(url_for('manage_members'))

    cursor.close()
    conn.close()
    return render_template('edit_member.html', member=member)


@app.route('/admin/members/delete/<int:member_id>')
@login_required
def remove_member(member_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id=%s", (member_id,))
        conn.commit()
        flash("Member deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting member: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_members'))


@app.route('/admin/members/qrcode/<int:student_id>')
@login_required
def generate_qrcode(student_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s", (student_id,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()

    if not student:
        flash("Student not found.", "warning")
        return redirect(url_for('manage_members'))

    # Generate QR code with student's info
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"ID:{student['id']}, Name:{student['username']}")
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)

    return send_file(buf, mimetype='image/png', download_name=f"{student['username']}_qrcode.png")






@app.route('/check_attendance')
@login_required
def check_attendance():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.id, u.username AS member_name, e.title AS event_title, a.checked_at
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        JOIN events e ON a.event_id = e.id
        ORDER BY a.checked_at DESC
    """)
    
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('check_attendance.html', records=records)


@app.route('/admin/members/checkin', methods=['POST'])
@login_required
def checkin_member():
    if current_user.role != 'admin':
        return jsonify({"message": "Access denied."}), 403

    data = request.get_json()
    qr_data = data.get('qr_data', '')

    # Expected QR format: "ID:1, Name:John Doe"
    try:
        student_id = int(qr_data.split(",")[0].split(":")[1])
    except Exception:
        return jsonify({"message": "Invalid QR code format."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if student exists
    cursor.execute("SELECT * FROM users WHERE id=%s", (student_id,))
    student = cursor.fetchone()
    if not student:
        cursor.close()
        conn.close()
        return jsonify({"message": "Student not found."}), 404

    # Check if already checked in today
    today = datetime.now().date()
    cursor.execute(
        "SELECT * FROM attendance WHERE user_id=%s AND DATE(checked_at)=%s",
        (student_id, today)
    )
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"message": f"{student[1]} already checked in today."})

    # Insert attendance record
    cursor.execute(
        "INSERT INTO attendance (user_id, username, checked_at) VALUES (%s, %s, NOW())",
        (student_id, student[1])
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": f"Attendance recorded for {student[1]}!"})


@app.route('/export_attendance/<file_type>')
@login_required
def export_attendance(file_type):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.id, u.username AS member_name, e.title AS event_title, a.checked_at
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        JOIN events e ON a.event_id = e.id
        ORDER BY a.checked_at DESC
    """)
    records = cursor.fetchall()
    cursor.close()
    conn.close()

    df = pd.DataFrame(records)

    if file_type.lower() == 'excel':
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment;filename=attendance.xlsx"}
        )
    elif file_type.lower() == 'pdf':
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

    # Optional: Add a header
        pdf.cell(0, 10, "Attendance Report", ln=True, align='C')
        pdf.ln(5)

    # Table header
        pdf.cell(10, 10, "ID", 1)
        pdf.cell(50, 10, "Member Name", 1)
        pdf.cell(50, 10, "Event Title", 1)
        pdf.cell(40, 10, "Checked At", 1)
        pdf.ln()
    # Table rows
    for i, row in df.iterrows():
        pdf.cell(10, 10, str(row['id']), 1)
        pdf.cell(50, 10, str(row['member_name']), 1)
        pdf.cell(50, 10, str(row['event_title']), 1)
        pdf.cell(40, 10, str(row['checked_at']), 1)
        pdf.ln()

    # Output PDF to a string and wrap in BytesIO
    pdf_bytes = pdf.output(dest='S').encode('latin1')  # FPDF outputs str, encode to bytes
    output = BytesIO(pdf_bytes)
    output.seek(0)

    return Response(
        output,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=attendance.pdf"}
    )



# --- Settings ---
@app.route('/setting')
@login_required
def setting():
    return render_template('setting.html')

@app.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html')

@app.route('/change_password')
@login_required
def change_password():
    return render_template('change_password.html')

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/terms')
@login_required
def terms():
    return render_template('terms.html')


# --- Privacy ---
@app.route('/privacy')
@login_required
def privacy():
    return render_template('privacy.html')


# --- Student Dashboard ---
@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch student's attendance
    cursor.execute("""
        SELECT a.id, e.title AS event_title, a.checked_at
        FROM attendance a
        JOIN events e ON a.event_id = e.id
        WHERE a.user_id = %s
        ORDER BY a.checked_at DESC
    """, (current_user.id,))
    attendance_records = cursor.fetchall()

    # Fetch upcoming events (optional)
    cursor.execute("SELECT * FROM events WHERE event_date >= NOW() ORDER BY event_date ASC LIMIT 3")
    upcoming_events = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'student_dashboard.html',
        attendance_records=attendance_records,
        upcoming_events=upcoming_events
    )


@app.route('/personal_qrcode')
@login_required
def personal_qrcode():
    if current_user.role != 'student':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"ID:{current_user.id}, Name:{current_user.username}")
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")

    buf = BytesIO()
    img.save(buf)
    buf.seek(0)

    return send_file(buf, mimetype='image/png', download_name=f"{current_user.username}_qrcode.png")


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE users SET username=%s, email=%s WHERE id=%s
            """, (username, email, current_user.id))
            conn.commit()

            # Update current_user object for session
            current_user.username = username
            current_user.email = email

            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f"Error updating profile: {str(e)}", 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('profile'))

    return render_template('profile.html')


@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    current_user.username = data.get('username')
    current_user.email = data.get('email')
    current_user.full_name = data.get('full_name')
    current_user.age = data.get('age')
    current_user.year_level = data.get('year_level')
    current_user.status = data.get('status')
    current_user.citizenship = data.get('citizenship')
    current_user.address = data.get('address')
    current_user.place_of_birth = data.get('place_of_birth')

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated!", "user": {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "age": current_user.age,
        "year_level": current_user.year_level,
        "status": current_user.status,
        "citizenship": current_user.citizenship,
        "address": current_user.address,
        "place_of_birth": current_user.place_of_birth
    }})
    
    
    
@app.route('/submit_profile_update', methods=['POST'])
@login_required
def submit_profile_update():
    # Check if there is already a pending update
    pending = PendingProfileUpdate.query.filter_by(user_id=current_user.id, approved=False).first()
    if pending:
        flash("You already have a pending update. Please wait for admin approval.", "danger")
        return redirect(url_for('profile'))

    # Create a new pending update
    pending_update = PendingProfileUpdate(
        user_id=current_user.id,
        username=request.form['username'],
        email=request.form['email'],
        full_name=request.form['full_name'],
        age=request.form['age'],
        year_level=request.form['year_level'],
        status=request.form['status'],
        citizenship=request.form['citizenship'],
        address=request.form['address'],
        place_of_birth=request.form['place_of_birth']
    )

    db.session.add(pending_update)
    db.session.commit()
    flash("Profile update submitted to admin for approval.", "success")
    return redirect(url_for('profile'))


@app.route('/scan_qr', methods=['POST'])
def scan_qr_result():
    data = request.get_json() or {}
    qr_data = data.get('qr_data', '')

    # Parse QR format: "ID:1, Name:John"
    user_id = None
    if isinstance(qr_data, dict):
        user_id = qr_data.get('ID')
    elif isinstance(qr_data, str):
        try:
            user_id = int(qr_data.split(",")[0].split(":")[1].strip())
        except Exception:
            return jsonify({"error": "Invalid QR code format."}), 400

    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({"error": "Invalid or missing ID in QR data."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, email FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        return jsonify({"error": "User not found."}), 404
    
    # print(user)

    return jsonify(user)
    


@app.route('/approve_update/<int:update_id>', methods=['POST'])
@login_required
def approve_update(update_id):
    update = PendingProfileUpdate.query.get_or_404(update_id)
    user = User.query.get(update.user_id)

    # Update user info
    user.username = update.username
    user.email = update.email
    user.full_name = update.full_name
    user.age = update.age
    user.year_level = update.year_level
    user.status = update.status
    user.citizenship = update.citizenship
    user.address = update.address
    user.place_of_birth = update.place_of_birth

    # Mark as approved
    update.approved = True
    db.session.commit()
    flash(f"{user.username}'s profile update approved.", "success")
    return redirect(url_for('manage_members'))


@app.route('/reject_update/<int:update_id>', methods=['POST'])
@login_required
def reject_update(update_id):
    update = PendingProfileUpdate.query.get_or_404(update_id)
    db.session.delete(update)
    db.session.commit()
    flash("Profile update rejected.", "danger")
    return redirect(url_for('manage_members'))


ngrok_url = "https://delmar-hesperidate-swimmingly.ngrok-free.dev/check_attendance"
img = qrcode.make(ngrok_url)
img.save("attendance_qr.png")



if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

