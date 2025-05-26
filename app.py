from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key'
socketio = SocketIO(app, async_mode='eventlet')

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        type TEXT,
        reason TEXT
    )''')
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    conn.commit()
    conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['username'] = user[0]
            session['role'] = user[2]
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for('home'))
        else:
            message = "Tên người dùng hoặc mật khẩu không đúng!"
    return render_template('login.html', message=message)

@app.route('/logout')
def logout():
    session.clear()
    flash("Đã đăng xuất!", "info")
    return redirect(url_for('login'))

@app.route('/chat')
def chat():
    if 'username' not in session:
        flash("Vui lòng đăng nhập để sử dụng chat!", "warning")
        return redirect(url_for('login'))
    username = session['username']
    role = session['role']
    users = []
    if role == 'admin':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE role = 'user'")
        users = c.fetchall()  # users là list các tuple [('user1',), ('user2',)...]
        conn.close()
    return render_template('chat.html', username=username, role=role, users=users)

@socketio.on('join')
def handle_join(data):
    username = session.get('username')
    role = session.get('role')
    if role == 'admin':
        join_room('admin')
        emit('status', {'msg': f'Admin {username} đã vào phòng admin'}, room='admin')
    else:
        user_room = f'user:{username}'
        join_room(user_room)
        emit('status', {'msg': f'{username} đã vào phòng chat riêng'}, room=user_room)

@socketio.on('send_message')
def handle_send_message(data):
    role = session.get('role')
    username = session.get('username')
    msg = data.get('message')
    if role == 'admin':
        to_user = data.get('to_user')
        if not to_user:
            emit('status', {'msg': 'Bạn cần chọn user để chat.'}, room='admin')
            return
        room = f'user:{to_user}'
        # Gửi tin nhắn tới phòng user đó và cho admin phòng admin
        emit('receive_message', {'username': f'Admin {username}', 'msg': msg}, room=room)
        emit('receive_message', {'username': f'Admin {username} (đã gửi đến {to_user})', 'msg': msg}, room='admin')
    else:
        room = 'admin'
        user_room = f'user:{username}'
        emit('receive_message', {'username': username, 'msg': msg}, room=room)
        emit('receive_message', {'username': username, 'msg': msg}, room=user_room)

@socketio.on('leave')
def handle_leave(data):
    username = session.get('username')
    role = session.get('role')
    if role == 'admin':
        leave_room('admin')
        emit('status', {'msg': f'Admin {username} đã rời phòng admin'}, room='admin')
    else:
        user_room = f'user:{username}'
        leave_room(user_room)
        emit('status', {'msg': f'{username} đã rời phòng chat riêng'}, room=user_room)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback_type = request.form['feedback_type']
        reason = request.form['reason']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO feedback (type, reason) VALUES (?, ?)", (feedback_type, reason))
        conn.commit()
        conn.close()
        flash("Phản hồi đã được gửi!", "success")
        return redirect(url_for('feedback'))
    return render_template('feedback.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        if password != confirm_password:
            message = "Mật khẩu xác nhận không khớp!"
        else:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'user')", (username, password))
                conn.commit()
                conn.close()
                flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                message = "Tên người dùng đã tồn tại!"
                conn.close()
    return render_template('register.html', message=message)

@app.route('/admin')
def admin():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT username, role FROM users WHERE role = 'user'")
    users = c.fetchall()
    c.execute("SELECT type, reason FROM feedback")
    feedbacks = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users, feedbacks=feedbacks)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)
