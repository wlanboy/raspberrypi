from flask import Flask, render_template, redirect, url_for, request, session
from flask_socketio import SocketIO, emit, send
from collections import deque

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Ersetze dies durch einen sicheren Schlüssel
socketio = SocketIO(app)

# In-memory Speicherung der letzten 50 Nachrichten
chat_history = deque(maxlen=50)

# Temporäre Liste der aktuell eingeloggten User
active_users = set()

# Home-Route: Überprüft die Session und leitet weiter
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

# Login-Route: Benutzername eingeben
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        # Prüfen, ob der Benutzername schon vergeben ist
        if username in active_users:
            return render_template('login.html', error='Dieser Name wird bereits verwendet.')
        
        session['username'] = username
        active_users.add(username)
        return redirect(url_for('chat'))
    return render_template('login.html')

# Chat-Route: Der eigentliche Chat-Raum
@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', chat_history=list(chat_history))

# Logout-Route
@app.route('/logout')
def logout():
    username = session.pop('username', None)
    if username in active_users:
        active_users.remove(username)
    return redirect(url_for('login'))

# SocketIO-Events: Für Echtzeit-Kommunikation
@socketio.on('message')
def handle_message(msg):
    username = session.get('username')
    if username:
        message_data = {'username': username, 'message': msg}
        chat_history.append(message_data)
        send(message_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)