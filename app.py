from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, datetime

app = Flask(__name__)
app.secret_key = 'medishare_secret_2024'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    return pymysql.connect(
        host     = os.environ.get('MYSQL_HOST',     'localhost'),
        user     = os.environ.get('MYSQL_USER',     'root'),
        password = os.environ.get('MYSQL_PASSWORD', ''),
        database = os.environ.get('MYSQL_DB',       'medishare'),
        port     = int(os.environ.get('MYSQL_PORT', 3306)),
        cursorclass = pymysql.cursors.DictCursor
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        phone    = request.form['phone']
        address  = request.form['address']
        role     = request.form['role']
        password = generate_password_hash(request.form['password'])
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash('Email already registered.', 'error')
            db.close()
            return redirect(url_for('register'))
        cur.execute("INSERT INTO users (name,email,phone,address,role,password) VALUES (%s,%s,%s,%s,%s,%s)",
                    (name, email, phone, address, role, password))
        db.commit()
        db.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'ngo':
                return redirect(url_for('ngo_dashboard'))
            else:
                return redirect(url_for('donor_dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/donor')
def donor_dashboard():
    if session.get('user_role') != 'donor':
        return redirect(url_for('login'))
    db = get_db()
    cur = db.cursor()
    cur.execute("""SELECT m.*, u.name as ngo_name FROM medicines m
        LEFT JOIN requests r ON r.medicine_id = m.id
        LEFT JOIN users u ON u.id = r.ngo_id
        WHERE m.donor_id = %s ORDER BY m.created_at DESC""", (session['user_id'],))
    medicines = cur.fetchall()
    db.close()
    return render_template('donor_dashboard.html', medicines=medicines)

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if session.get('user_role') != 'donor':
        return redirect(url_for('login'))
    if request.method == 'POST':
        name    = request.form['medicine_name']
        qty     = request.form['quantity']
        expiry  = request.form['expiry_date']
        desc    = request.form['description']
        photo   = request.files.get('photo')
        filename = ''
        exp_date = datetime.datetime.strptime(expiry, '%Y-%m-%d').date()
        min_date = datetime.date.today() + datetime.timedelta(days=30)
        if exp_date < min_date:
            flash('Expiry date must be at least 30 days from today.', 'error')
            return redirect(url_for('donate'))
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO medicines (donor_id,name,quantity,expiry_date,description,photo,status) VALUES (%s,%s,%s,%s,%s,%s,'pending')",
                    (session['user_id'], name, qty, expiry, desc, filename))
        db.commit()
        db.close()
        flash('Medicine submitted for verification!', 'success')
        return redirect(url_for('donor_dashboard'))
    min_date = (datetime.date.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    return render_template('donate.html', min_date=min_date)

@app.route('/ngo')
def ngo_dashboard():
    if session.get('user_role') != 'ngo':
        return redirect(url_for('login'))
    db = get_db()
    cur = db.cursor()
    cur.execute("""SELECT m.*, u.name as donor_name FROM medicines m
        JOIN users u ON u.id = m.donor_id
        WHERE m.status='approved' ORDER BY m.created_at DESC""")
    medicines = cur.fetchall()
    cur.execute("""SELECT r.*, m.name as med_name, m.quantity, m.expiry_date
        FROM requests r JOIN medicines m ON m.id = r.medicine_id
        WHERE r.ngo_id=%s ORDER BY r.created_at DESC""", (session['user_id'],))
    my_requests = cur.fetchall()
    db.close()
    return render_template('ngo_dashboard.html', medicines=medicines, my_requests=my_requests)

@app.route('/request/<int:med_id>', methods=['POST'])
def request_medicine(med_id):
    if session.get('user_role') != 'ngo':
        return redirect(url_for('login'))
    note = request.form.get('note', '')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM requests WHERE ngo_id=%s AND medicine_id=%s", (session['user_id'], med_id))
    if cur.fetchone():
        flash('You already requested this medicine.', 'error')
    else:
        cur.execute("INSERT INTO requests (ngo_id,medicine_id,note,status) VALUES (%s,%s,%s,'pending')",
                    (session['user_id'], med_id, note))
        db.commit()
        flash('Request submitted successfully!', 'success')
    db.close()
    return redirect(url_for('ngo_dashboard'))

@app.route('/admin')
def admin_dashboard():
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) as c FROM medicines WHERE status='pending'")
    pending = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM medicines WHERE status='approved'")
    approved = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM requests")
    total_req = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM users WHERE role='donor'")
    donors = cur.fetchone()['c']
    cur.execute("""SELECT m.*, u.name as donor_name FROM medicines m
        JOIN users u ON u.id=m.donor_id
        WHERE m.status='pending' ORDER BY m.created_at DESC""")
    pending_meds = cur.fetchall()
    cur.execute("""SELECT m.*, u.name as donor_name FROM medicines m
        JOIN users u ON u.id=m.donor_id ORDER BY m.created_at DESC""")
    all_meds = cur.fetchall()
    cur.execute("""SELECT r.*, m.name as med_name, u.name as ngo_name
        FROM requests r JOIN medicines m ON m.id=r.medicine_id
        JOIN users u ON u.id=r.ngo_id ORDER BY r.created_at DESC""")
    all_requests = cur.fetchall()
    db.close()
    return render_template('admin_dashboard.html',
        pending=pending, approved=approved, total_req=total_req, donors=donors,
        pending_meds=pending_meds, all_meds=all_meds, all_requests=all_requests)

@app.route('/admin/medicine/<int:med_id>/<action>')
def admin_action(med_id, action):
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    status = 'approved' if action == 'approve' else 'rejected'
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE medicines SET status=%s WHERE id=%s", (status, med_id))
    db.commit()
    db.close()
    flash(f'Medicine {status}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/request/<int:req_id>/status', methods=['POST'])
def update_delivery(req_id):
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    status = request.form['status']
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE requests SET status=%s WHERE id=%s", (status, req_id))
    db.commit()
    db.close()
    flash('Delivery status updated.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))