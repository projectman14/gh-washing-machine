from flask import Flask, request, jsonify, g
from flask import render_template
from flask_cors import CORS
import sqlite3
import hashlib
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import traceback
from dotenv import load_dotenv
load_dotenv()



app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Email configuration
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = 'lnmiit.hostel@gmail.com'  # Replace with actual email
EMAIL_PASSWORD = 'your_app_password'    # Replace with actual app password
EMAIL_FROM = 'LNMIIT Girls Hostel <lnmiit.hostel@gmail.com>'

# Database configuration
DATABASE = 'washing_machine_booking.db'

def get_db():
    """Get database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with tables"""
    with app.app_context():
        db = get_db()
        
        # Create Users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create Washing_Machines table
        db.execute('''
            CREATE TABLE IF NOT EXISTS washing_machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                last_used_by INTEGER,
                last_used_time DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (last_used_by) REFERENCES users (id)
            )
        ''')
        
        # Create Bookings table
        db.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                machine_id INTEGER NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (machine_id) REFERENCES washing_machines (id)
            )
        ''')
        
        # Insert default admin user
        admin_password = hash_password('admin123')
        db.execute('''
            INSERT OR IGNORE INTO users (student_id, username, password, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'Administrator', admin_password, 'admin'))
        
        # Insert default washing machines
        machines = [
            ('Machine 1', 'available'),
            ('Machine 2', 'available'),
            ('Machine 3', 'available'),
            ('Machine 4', 'available'),
            ('Machine 5', 'available'),
            ('Machine 6', 'available'),
            ('Machine 7', 'available'),
            ('Machine 8', 'available')
        ]
        
        for machine_name, status in machines:
            db.execute('''
                INSERT OR IGNORE INTO washing_machines (machine_name, status)
                VALUES (?, ?)
            ''', (machine_name, status))
        
        db.commit()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

def send_email(to_email, subject, body):
    """Send email notification"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False

def send_booking_confirmation_email(user_email, username, machine_name, start_time, end_time, booking_id):
    """Send booking confirmation email"""
    subject = "Washing Machine Booking Confirmation - LNMIIT Girls Hostel"
    
    body = f"""
    <html>
    <body>
        <h2>Booking Confirmation</h2>
        <p>Dear {username},</p>
        
        <p>Your washing machine booking has been confirmed successfully!</p>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Booking Details:</h3>
            <p><strong>Booking ID:</strong> #{booking_id}</p>
            <p><strong>Machine:</strong> {machine_name}</p>
            <p><strong>Start Time:</strong> {start_time}</p>
            <p><strong>End Time:</strong> {end_time}</p>
        </div>
        
        <p><strong>Important Notes:</strong></p>
        <ul>
            <li>Please arrive on time for your slot</li>
            <li>Ensure you complete your laundry within the allocated time</li>
            <li>If you need to cancel, please do so at least 30 minutes before your slot</li>
        </ul>
        
        <p>Thank you for using the LNMIIT Girls Hostel Washing Machine Booking System!</p>
        
        <p>Best regards,<br>
        LNMIIT Girls Hostel Management</p>
    </body>
    </html>
    """
    
    return send_email(user_email, subject, body)

# API Routes

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        username = data.get('username')
        password = data.get('password')
        
        if not all([student_id, username, password]):
            return jsonify({'message': 'All fields are required'}), 400
        
        db = get_db()
        
        # Check if student ID already exists
        existing_user = db.execute(
            'SELECT id FROM users WHERE student_id = ?', (student_id,)
        ).fetchone()
        
        if existing_user:
            return jsonify({'message': 'Student ID already registered'}), 400
        
        # Hash password and insert user
        hashed_password = hash_password(password)
        cursor = db.execute('''
            INSERT INTO users (student_id, username, password, role)
            VALUES (?, ?, ?, ?)
        ''', (student_id, username, hashed_password, 'user'))
        
        db.commit()
        
        return jsonify({
            'message': 'Registration successful',
            'user_id': cursor.lastrowid
        }), 201
        
    except Exception as e:
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        password = data.get('password')
        
        if not all([student_id, password]):
            return jsonify({'message': 'Student ID and password are required'}), 400
        
        db = get_db()
        user = db.execute('''
            SELECT id, student_id, username, password, role
            FROM users WHERE student_id = ? AND role = 'user'
        ''', (student_id,)).fetchone()
        
        if not user or not verify_password(password, user['password']):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'student_id': user['student_id'],
                'username': user['username'],
                'role': user['role']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Login failed: {str(e)}'}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login"""
    try:
        data = request.get_json()
        admin_id = data.get('admin_id')
        password = data.get('password')
        
        if not all([admin_id, password]):
            return jsonify({'message': 'Admin ID and password are required'}), 400
        
        db = get_db()
        admin = db.execute('''
            SELECT id, student_id, username, password, role
            FROM users WHERE student_id = ? AND role = 'admin'
        ''', (admin_id,)).fetchone()
        
        if not admin or not verify_password(password, admin['password']):
            return jsonify({'message': 'Invalid admin credentials'}), 401
        
        return jsonify({
            'message': 'Admin login successful',
            'admin': {
                'id': admin['id'],
                'student_id': admin['student_id'],
                'username': admin['username'],
                'role': admin['role']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Admin login failed: {str(e)}'}), 500

@app.route('/api/machines', methods=['GET'])
def get_machines():
    """Get all washing machines"""
    try:
        db = get_db()
        machines = db.execute('''
            SELECT id, machine_name, status, last_used_by, last_used_time
            FROM washing_machines
            ORDER BY id
        ''').fetchall()
        
        machines_list = []
        for machine in machines:
            machines_list.append({
                'id': machine['id'],
                'machine_name': machine['machine_name'],
                'status': machine['status'],
                'last_used_by': machine['last_used_by'],
                'last_used_time': machine['last_used_time']
            })
        
        return jsonify({'machines': machines_list}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get machines: {str(e)}'}), 500

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Create a new booking"""
    try:
        data = request.get_json()
        user_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        machine_id = data.get('machine_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not all([user_id, machine_id, start_time, end_time]):
            return jsonify({'message': 'All fields are required'}), 400
        
        db = get_db()
        
        # Check if machine is available
        machine = db.execute(
            'SELECT status FROM washing_machines WHERE id = ?', (machine_id,)
        ).fetchone()
        
        if not machine:
            return jsonify({'message': 'Machine not found'}), 404
        
        if machine['status'] != 'available':
            return jsonify({'message': 'Machine is not available'}), 400
        
        # Check for conflicting bookings
        conflicts = db.execute('''
            SELECT id FROM bookings 
            WHERE machine_id = ? AND status IN ('pending', 'confirmed')
            AND (
                (start_time <= ? AND end_time > ?) OR
                (start_time < ? AND end_time >= ?) OR
                (start_time >= ? AND end_time <= ?)
            )
        ''', (machine_id, start_time, start_time, end_time, end_time, start_time, end_time)).fetchall()
        
        if conflicts:
            return jsonify({'message': 'Time slot conflicts with existing booking'}), 400
        
        # Check 10-day booking restriction per user
        from datetime import datetime, timedelta
        current_time = datetime.now()
        ten_days_from_now = current_time + timedelta(days=10)
        
        # Count existing bookings for this user in the next 10 days
        existing_bookings = db.execute('''
            SELECT COUNT(*) as count FROM bookings 
            WHERE user_id = ? AND status IN ('pending', 'confirmed')
            AND start_time BETWEEN ? AND ?
        ''', (user_id, current_time.isoformat(), ten_days_from_now.isoformat())).fetchone()
        
        if existing_bookings['count'] >= 1:
            return jsonify({'message': 'You can only book one slot in the next 10 days'}), 400
        
        # Create booking
        cursor = db.execute('''
            INSERT INTO bookings (user_id, machine_id, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, machine_id, start_time, end_time, 'confirmed'))
        
        booking_id = cursor.lastrowid
        
        # Get user and machine details for email
        user = db.execute('''
            SELECT username, email FROM users WHERE id = ?
        ''', (user_id,)).fetchone()
        
        machine = db.execute('''
            SELECT machine_name FROM washing_machines WHERE id = ?
        ''', (machine_id,)).fetchone()
        
        db.commit()
        
        # Send email notification if user has email
        if user and user['email'] and machine:
            send_booking_confirmation_email(
                user['email'], 
                user['username'], 
                machine['machine_name'], 
                start_time, 
                end_time, 
                booking_id
            )
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking_id': booking_id
        }), 201
        
    except Exception as e:
        return jsonify({'message': f'Booking failed: {str(e)}'}), 500

@app.route('/api/bookings/user/<int:user_id>', methods=['GET'])
def get_user_bookings(user_id):
    """Get bookings for a specific user"""
    try:
        db = get_db()
        bookings = db.execute('''
            SELECT b.id, b.start_time, b.end_time, b.status, b.created_at,
                   m.machine_name
            FROM bookings b
            JOIN washing_machines m ON b.machine_id = m.id
            WHERE b.user_id = ?
            ORDER BY b.start_time DESC
        ''', (user_id,)).fetchall()
        
        bookings_list = []
        for booking in bookings:
            bookings_list.append({
                'id': booking['id'],
                'machine_name': booking['machine_name'],
                'start_time': booking['start_time'],
                'end_time': booking['end_time'],
                'status': booking['status'],
                'created_at': booking['created_at']
            })
        
        return jsonify({'bookings': bookings_list}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get bookings: {str(e)}'}), 500

@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    """Cancel a booking"""
    try:
        user_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        db = get_db()
        
        # Check if booking exists and belongs to user
        booking = db.execute('''
            SELECT id, user_id, status FROM bookings 
            WHERE id = ? AND user_id = ?
        ''', (booking_id, user_id)).fetchone()
        
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        if booking['status'] == 'completed':
            return jsonify({'message': 'Cannot cancel completed booking'}), 400
        
        # Update booking status to cancelled
        db.execute('''
            UPDATE bookings SET status = 'cancelled' WHERE id = ?
        ''', (booking_id,))
        
        db.commit()
        
        return jsonify({'message': 'Booking cancelled successfully'}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to cancel booking: {str(e)}'}), 500

@app.route('/api/admin/machines', methods=['GET'])
def get_admin_machines():
    """Get all machines for admin"""
    try:
        db = get_db()
        machines = db.execute('''
            SELECT m.id, m.machine_name, m.status, m.last_used_by, m.last_used_time,
                   u.username as last_used_by_name
            FROM washing_machines m
            LEFT JOIN users u ON m.last_used_by = u.id
            ORDER BY m.id
        ''').fetchall()
        
        machines_list = []
        # Limit to only 8 machines for admin portal
        limited_machines = machines[:8]
        for machine in limited_machines:
            machines_list.append({
                'id': machine['id'],
                'machine_name': machine['machine_name'],
                'status': machine['status'],
                'last_used_by': machine['last_used_by'],
                'last_used_by_name': machine['last_used_by_name'],
                'last_used_time': machine['last_used_time']
            })
        
        return jsonify({'machines': machines_list}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get machines: {str(e)}'}), 500

@app.route('/api/admin/machines/<int:machine_id>/status', methods=['PUT'])
def update_machine_status(machine_id):
    """Update machine status"""
    try:
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['available', 'in_use', 'broken']:
            return jsonify({'message': 'Invalid status'}), 400
        
        db = get_db()
        
        # Check if machine exists
        machine = db.execute(
            'SELECT id FROM washing_machines WHERE id = ?', (machine_id,)
        ).fetchone()
        
        if not machine:
            return jsonify({'message': 'Machine not found'}), 404
        
        # Update machine status
        db.execute('''
            UPDATE washing_machines SET status = ? WHERE id = ?
        ''', (status, machine_id))
        
        db.commit()
        
        return jsonify({'message': 'Machine status updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to update machine status: {str(e)}'}), 500

@app.route('/api/admin/machines', methods=['POST'])
def add_machine():
    """Add a new machine"""
    try:
        data = request.get_json()
        machine_name = data.get('machine_name')
        
        if not machine_name:
            return jsonify({'message': 'Machine name is required'}), 400
        
        db = get_db()
        
        # Insert new machine
        cursor = db.execute('''
            INSERT INTO washing_machines (machine_name, status)
            VALUES (?, ?)
        ''', (machine_name, 'available'))
        
        db.commit()
        
        return jsonify({
            'message': 'Machine added successfully',
            'machine_id': cursor.lastrowid
        }), 201
        
    except Exception as e:
        return jsonify({'message': f'Failed to add machine: {str(e)}'}), 500

@app.route('/api/admin/bookings', methods=['GET'])
def get_all_bookings():
    """Get all bookings for admin"""
    try:
        db = get_db()
        bookings = db.execute('''
            SELECT b.id, b.start_time, b.end_time, b.status, b.created_at,
                   u.username, u.student_id, m.machine_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN washing_machines m ON b.machine_id = m.id
            ORDER BY b.start_time DESC
        ''').fetchall()
        
        bookings_list = []
        for booking in bookings:
            bookings_list.append({
                'id': booking['id'],
                'username': booking['username'],
                'student_id': booking['student_id'],
                'machine_name': booking['machine_name'],
                'start_time': booking['start_time'],
                'end_time': booking['end_time'],
                'status': booking['status'],
                'created_at': booking['created_at']
            })
        
        return jsonify({'bookings': bookings_list}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get bookings: {str(e)}'}), 500

@app.route('/api/machines/<int:machine_id>/bookings', methods=['GET'])
def get_machine_bookings(machine_id):
    """Get all bookings for a specific machine"""
    try:
        db = get_db()
        
        # Check if machine exists
        machine = db.execute(
            'SELECT machine_name FROM washing_machines WHERE id = ?', (machine_id,)
        ).fetchone()
        
        if not machine:
            return jsonify({'message': 'Machine not found'}), 404
        
        # Get all bookings for this machine
        bookings = db.execute('''
            SELECT b.id, b.start_time, b.end_time, b.status, b.created_at,
                   u.username, u.student_id
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.machine_id = ? AND b.status IN ('pending', 'confirmed')
            ORDER BY b.start_time ASC
        ''', (machine_id,)).fetchall()
        
        bookings_list = []
        for booking in bookings:
            bookings_list.append({
                'id': booking['id'],
                'username': booking['username'],
                'student_id': booking['student_id'],
                'start_time': booking['start_time'],
                'end_time': booking['end_time'],
                'status': booking['status'],
                'created_at': booking['created_at']
            })
        
        return jsonify({
            'machine_name': machine['machine_name'],
            'bookings': bookings_list
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get machine bookings: {str(e)}'}), 500


def verify_google_id_token(token):
    try:
        idinfo = id_token.verify_oauth2_token(token, grequests.Request(), "624690583385-s3cnmv6iro5kjjror5oq6t4iulerrcde.apps.googleusercontent.com")

        email = idinfo['email']
        if not email.endswith('@lnmiit.ac.in'):
            return None, 'Unauthorized domain'

        return {
            'student_id': email.split('@')[0],
            'email': email,
            'name': idinfo.get('name', '')
        }, None

    except ValueError as e:
        return None, f'Invalid token: {str(e)}'


@app.route('/api/google-login', methods=['POST'])
def google_login():
    """Google Sign-In login"""
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'message': 'Google ID token is required'}), 400

        user_data, error = verify_google_id_token(token)
        if error:
            return jsonify({'message': error}), 401

        db = get_db()
        user = db.execute('''
            SELECT id, student_id, username, email, role
            FROM users WHERE student_id = ? AND role = 'user'
        ''', (user_data['student_id'],)).fetchone()

        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Update missing email if needed
        if not user['email']:
            db.execute('''
                UPDATE users SET email = ? WHERE id = ?
            ''', (user_data['email'], user['id']))
            db.commit()

        return jsonify({
            'message': 'Google login successful',
            'user': {
                'id': user['id'],
                'student_id': user['student_id'],
                'username': user['username'],
                'email': user_data['email'],
                'role': user['role']
            }
        }), 200

    except Exception as e:
        print("Google login error:", e)
        traceback.print_exc()  # <-- this will show the exact crash line
        return jsonify({'message': f'Google login failed: {str(e)}'}), 500


@app.route('/api/google-register', methods=['POST'])
def google_register():
    """Google Sign-In registration"""
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'message': 'Google ID token is required'}), 400

        user_data, error = verify_google_id_token(token)
        if error:
            return jsonify({'message': error}), 401

        db = get_db()
        existing_user = db.execute(
            'SELECT id FROM users WHERE student_id = ?', (user_data['student_id'],)
        ).fetchone()

        if existing_user:
            return jsonify({'message': 'Student ID already registered'}), 400

        cursor = db.execute('''
            INSERT INTO users (student_id, username, password, email, role)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_data['student_id'], user_data['name'], 'google_auth', user_data['email'], 'user'))

        db.commit()

        return jsonify({
            'message': 'Google registration successful',
            'user': {
                'id': cursor.lastrowid,
                'student_id': user_data['student_id'],
                'username': user_data['name'],
                'email': user_data['email'],
                'role': 'user'
            }
        }), 201

    except Exception as e:
        return jsonify({'message': f'Google registration failed: {str(e)}'}), 500

@app.route('/api/config')
def get_config():
    return jsonify({
        'google_client_id': "624690583385-s3cnmv6iro5kjjror5oq6t4iulerrcde.apps.googleusercontent.com"
    })


@app.route('/')
def home():
    """Serve the main HTML file"""
    return app.render_template('index.html')

@app.route('/api')
def api_docs():
    """API documentation"""
    return '''
    <h1>LNMIIT Girls Hostel - Washing Machine Booking API</h1>
    <h2>Available Endpoints:</h2>
    <ul>
        <li>POST /api/register - User registration</li>
        <li>POST /api/login - User login</li>
        <li>POST /api/google-login - Google Sign-In login</li>
        <li>POST /api/google-register - Google Sign-In registration</li>
        <li>POST /api/admin/login - Admin login</li>
        <li>GET /api/machines - Get all machines</li>
        <li>POST /api/bookings - Create booking</li>
        <li>GET /api/bookings/user/&lt;user_id&gt; - Get user bookings</li>
        <li>DELETE /api/bookings/&lt;booking_id&gt; - Cancel booking</li>
        <li>GET /api/admin/machines - Get machines (admin)</li>
        <li>PUT /api/admin/machines/&lt;machine_id&gt;/status - Update machine status</li>
        <li>POST /api/admin/machines - Add new machine</li>
        <li>GET /api/admin/bookings - Get all bookings (admin)</li>
    </ul>
    '''

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True)

