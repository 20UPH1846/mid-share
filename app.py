from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, datetime

app = Flask(__name__)
app.secret_key = 'medishare_secret_2024'

# ── MySQL Config ──────────────────────────────────────────────
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'your_password'   # ← Change this
app.config['MYSQL_DB'] = 'medishare'

mysql = MySQL(app)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Home ──────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ── Register ─────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        phone    = request.form['phone']
        address  = request.form['address']
        role     = request.form['role']        # donor / ngo
        password = generate_password_hash(request.form['password'])

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))

        cur.execute("""
            INSERT INTO users (name, email, phone, address, role, password)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (name, email, phone, address, role, password))
        mysql.connection.commit()
        cur.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ── Login ─────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[6], password):
            session['user_id']   = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[5]
            if user[5] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user[5] == 'ngo':
                return redirect(url_for('ngo_dashboard'))
            else:
                return redirect(url_for('donor_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

# ── Logout ────────────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Donor Dashboard ───────────────────────────────────────────
@app.route('/donor')
def donor_dashboard():
    if session.get('user_role') != 'donor':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT m.*, u.name as ngo_name FROM medicines m
        LEFT JOIN requests r ON r.medicine_id = m.id
        LEFT JOIN users u ON u.id = r.ngo_id
        WHERE m.donor_id = %s
        ORDER BY m.created_at DESC
    """, (session['user_id'],))
    medicines = cur.fetchall()
    cur.close()
    return render_template('donor_dashboard.html', medicines=medicines)

# ── Donate Medicine ───────────────────────────────────────────
@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if session.get('user_role') != 'donor':
        return redirect(url_for('login'))
    if request.method == 'POST':
        name     = request.form['medicine_name']
        qty      = request.form['quantity']
        expiry   = request.form['expiry_date']
        desc     = request.form['description']
        photo    = request.files.get('photo')
        filename = ''

        # Expiry check: must be > 30 days from today
        exp_date = datetime.datetime.strptime(expiry, '%Y-%m-%d').date()
        min_date = datetime.date.today() + datetime.timedelta(days=30)
        if exp_date < min_date:
            flash('Expiry date must be at least 30 days from today.', 'error')
            return redirect(url_for('donate'))

        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO medicines (donor_id, name, quantity, expiry_date, description, photo, status)
            VALUES (%s,%s,%s,%s,%s,%s,'pending')
        """, (session['user_id'], name, qty, expiry, desc, filename))
        mysql.connection.commit()
        cur.close()
        flash('Medicine submitted for verification!', 'success')
        return redirect(url_for('donor_dashboard'))
    min_date = (datetime.date.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    return render_template('donate.html', min_date=min_date)

# ── NGO Dashboard ─────────────────────────────────────────────
@app.route('/ngo')
def ngo_dashboard():
    if session.get('user_role') != 'ngo':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    # Approved medicines available
    cur.execute("""
        SELECT m.*, u.name as donor_name FROM medicines m
        JOIN users u ON u.id = m.donor_id
        WHERE m.status = 'approved'
        ORDER BY m.created_at DESC
    """)
    medicines = cur.fetchall()
    # This NGO's requests
    cur.execute("""
        SELECT r.*, m.name as med_name, m.quantity, m.expiry_date
        FROM requests r JOIN medicines m ON m.id = r.medicine_id
        WHERE r.ngo_id = %s ORDER BY r.created_at DESC
    """, (session['user_id'],))
    my_requests = cur.fetchall()
    cur.close()
    return render_template('ngo_dashboard.html', medicines=medicines, my_requests=my_requests)

# ── NGO Request Medicine ──────────────────────────────────────
@app.route('/request/<int:med_id>', methods=['POST'])
def request_medicine(med_id):
    if session.get('user_role') != 'ngo':
        return redirect(url_for('login'))
    note = request.form.get('note', '')
    cur = mysql.connection.cursor()
    # Check not already requested
    cur.execute("SELECT id FROM requests WHERE ngo_id=%s AND medicine_id=%s",
                (session['user_id'], med_id))
    if cur.fetchone():
        flash('You already requested this medicine.', 'error')
    else:
        cur.execute("""
            INSERT INTO requests (ngo_id, medicine_id, note, status)
            VALUES (%s,%s,%s,'pending')
        """, (session['user_id'], med_id, note))
        mysql.connection.commit()
        flash('Request submitted successfully!', 'success')
    cur.close()
    return redirect(url_for('ngo_dashboard'))

# ── Admin Dashboard ───────────────────────────────────────────
@app.route('/admin')
def admin_dashboard():
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()

    # Stats
    cur.execute("SELECT COUNT(*) FROM medicines WHERE status='pending'")
    pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM medicines WHERE status='approved'")
    approved = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM requests")
    total_req = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE role='donor'")
    donors = cur.fetchone()[0]

    # Pending medicines
    cur.execute("""
        SELECT m.*, u.name as donor_name FROM medicines m
        JOIN users u ON u.id = m.donor_id
        WHERE m.status='pending' ORDER BY m.created_at DESC
    """)
    pending_meds = cur.fetchall()

    # All medicines
    cur.execute("""
        SELECT m.*, u.name as donor_name FROM medicines m
        JOIN users u ON u.id = m.donor_id
        ORDER BY m.created_at DESC
    """)
    all_meds = cur.fetchall()

    # All requests
    cur.execute("""
        SELECT r.*, m.name as med_name, u.name as ngo_name
        FROM requests r
        JOIN medicines m ON m.id = r.medicine_id
        JOIN users u ON u.id = r.ngo_id
        ORDER BY r.created_at DESC
    """)
    all_requests = cur.fetchall()

    cur.close()
    return render_template('admin_dashboard.html',
        pending=pending, approved=approved,
        total_req=total_req, donors=donors,
        pending_meds=pending_meds, all_meds=all_meds,
        all_requests=all_requests)

# ── Admin: Approve/Reject Medicine ───────────────────────────
@app.route('/admin/medicine/<int:med_id>/<action>')
def admin_action(med_id, action):
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    status = 'approved' if action == 'approve' else 'rejected'
    cur = mysql.connection.cursor()
    cur.execute("UPDATE medicines SET status=%s WHERE id=%s", (status, med_id))
    mysql.connection.commit()
    cur.close()
    flash(f'Medicine {status}.', 'success')
    return redirect(url_for('admin_dashboard'))

# ── Admin: Update Delivery Status ────────────────────────────
@app.route('/admin/request/<int:req_id>/status', methods=['POST'])
def update_delivery(req_id):
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    status = request.form['status']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE requests SET status=%s WHERE id=%s", (status, req_id))
    mysql.connection.commit()
    cur.close()
    flash('Delivery status updated.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
