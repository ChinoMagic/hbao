from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Đổi thành secret key của bạn
socketio = SocketIO(app, async_mode='eventlet', manage_session=True)

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    ''')
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'admin'))
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
            return redirect(url_for('chat'))
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
        users = [row[0] for row in c.fetchall()]  # lấy danh sách tên user dạng list string
        conn.close()

    return render_template('chat.html', username=username, role=role, users=users)

@socketio.on('join')
def handle_join(data=None):
    username = session.get('username')
    role = session.get('role')

    if role == 'admin':
        join_room('admin')
        emit('status', {'msg': f'Admin {username} đã vào phòng admin'}, room='admin')

        if data and 'room' in data:
            join_room(data['room'])
            emit('status', {'msg': f'Admin {username} đã vào phòng {data["room"]}'}, room=data['room'])
    else:
        user_room = f'chat:{username}'
        join_room(user_room)
        emit('status', {'msg': f'{username} đã vào phòng chat {user_room}'}, room=user_room)

@socketio.on('send_message')
def handle_send_message(data):
    role = session.get('role')
    username = session.get('username')
    msg = data.get('message')

    if not msg:
        emit('status', {'msg': 'Tin nhắn không được để trống!'}, room=request.sid)
        return

    if role == 'admin':
        to_user = data.get('to_user')
        if not to_user:
            emit('status', {'msg': 'Bạn cần chọn user để chat.'}, room='admin')
            return

        room = f'chat:{to_user}'
        emit('receive_message', {'username': f'Admin {username}', 'msg': msg}, room=room)
        emit('receive_message', {'username': f'Admin {username} (gửi đến {to_user})', 'msg': msg}, room='admin')
    else:
        room = f'chat:{username}'
        emit('receive_message', {'username': username, 'msg': msg}, room=room)

@socketio.on('leave')
def handle_leave(data=None):
    username = session.get('username')
    role = session.get('role')

    if role == 'admin':
        leave_room('admin')
        emit('status', {'msg': f'Admin {username} đã rời phòng admin'}, room='admin')
        if data and 'room' in data:
            leave_room(data['room'])
            emit('status', {'msg': f'Admin {username} đã rời phòng {data["room"]}'}, room=data['room'])
    else:
        user_room = f'chat:{username}'
        leave_room(user_room)
        emit('status', {'msg': f'{username} đã rời phòng chat'}, room=user_room)

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('chat'))
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
