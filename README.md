# MediShare — Full Stack Setup Guide

## Project Structure
```
medishare/
├── app.py               ← Flask backend (all routes)
├── schema.sql           ← MySQL database setup
├── requirements.txt     ← Python packages
├── templates/
│   ├── base.html        ← Navbar + layout
│   ├── index.html       ← Landing page
│   ├── login.html       ← Login page
│   ├── register.html    ← Register (Donor / NGO)
│   ├── donate.html      ← Donate medicine form
│   ├── donor_dashboard.html
│   ├── ngo_dashboard.html
│   └── admin_dashboard.html
└── static/
    ├── css/style.css    ← All styles
    └── uploads/         ← Medicine photos saved here
```

---

## Step 1 — Install Python & MySQL

Make sure you have:
- Python 3.8+ → https://python.org
- MySQL 8.0+  → https://dev.mysql.com/downloads/

---

## Step 2 — Install Python Packages

Open terminal inside the `medishare/` folder:

```bash
pip install -r requirements.txt
```

If flask-mysqldb gives error on Windows, try:
```bash
pip install flask flask-mysqldb mysqlclient werkzeug
```

---

## Step 3 — Set Up MySQL Database

Open MySQL and run:

```bash
mysql -u root -p < schema.sql
```

Or open MySQL Workbench and paste the contents of `schema.sql`.

---

## Step 4 — Set Admin Password

After running schema.sql, set a real admin password:

```bash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"
```

Copy the output hash, then in MySQL run:
```sql
USE medishare;
UPDATE users SET password='PASTE_HASH_HERE' WHERE email='admin@medishare.com';
```

---

## Step 5 — Configure app.py

Open `app.py` and update line 13:
```python
app.config['MYSQL_PASSWORD'] = 'your_actual_mysql_password'
```

---

## Step 6 — Run the Website

```bash
python app.py
```

Open your browser at: https://mid-share-production.up.railway.app/

---

## User Accounts

| Role  | Email                 | Password   |
|-------|-----------------------|------------|
| Admin | admin@medishare.com   | admin123   |
| Donor | Register on website   | your choice |
| NGO   | Register on website   | your choice |

---

## How to Use

### As a Donor:
1. Register → select "Donor"
2. Login → click "+ Donate Medicine"
3. Fill medicine name, quantity, expiry, upload photo
4. Submit → wait for admin to verify

### As an NGO:
1. Register → select "NGO"
2. Login → browse available medicines
3. Click "Request This" on any medicine
4. Track status in "My Requests" tab

### As Admin:
1. Login with admin@medishare.com
2. See all pending donations → Approve or Reject
3. Manage NGO requests → update delivery status

---

## Common Errors

**MySQL connection error:**  
Check MYSQL_PASSWORD in app.py, make sure MySQL is running.

**ModuleNotFoundError:**  
Run `pip install flask flask-mysqldb werkzeug`

**Upload folder error:**  
Make sure `static/uploads/` folder exists.
