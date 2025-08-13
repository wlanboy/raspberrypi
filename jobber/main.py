import sqlite3
import subprocess
import time
from flask import Flask, render_template, request, redirect, url_for, session, g

app = Flask(__name__)
app.secret_key = 'your_secret_key_job'  # Wichtig für Sessions!

DATABASE = 'jobs.db'

def get_db_connection():
    """Stellt eine Verbindung zur Datenbank her und gibt sie zurück."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Ermöglicht den Zugriff auf Spalten per Name
    return db

def create_table():
    """
    Erstellt die 'jobs'-Tabelle, falls sie nicht existiert.
    Die Tabelle enthält nun Spalten für Laufzeitinformationen und die Ausgabe.
    """
    with app.app_context():
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator TEXT NOT NULL,
                name TEXT NOT NULL,
                image TEXT NOT NULL,
                params TEXT,
                docker_command TEXT,
                last_run_start_time TEXT,
                last_run_duration REAL,
                last_run_output TEXT
            )
        """)
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    """Schließt die Datenbankverbindung am Ende jeder Anfrage."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('jobs_page'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            session['username'] = username
            return redirect(url_for('jobs_page'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/jobs', methods=['GET', 'POST'])
def jobs_page():
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = session['username']
    db = get_db_connection()

    # Formular zum Hinzufügen eines neuen Jobs verarbeiten
    if request.method == 'POST':
        job_name = request.form.get('job_name')
        docker_image = request.form.get('docker_image')
        optional_params = request.form.get('optional_params')

        if job_name and docker_image:
            # Docker-Befehl generieren
            docker_command = f"docker run --rm --name {job_name} {docker_image}"
            if optional_params:
                docker_command += f" {optional_params}"

            db.execute(
                'INSERT INTO jobs (creator, name, image, params, docker_command) VALUES (?, ?, ?, ?, ?)',
                (current_user, job_name, docker_image, optional_params, docker_command)
            )
            db.commit()
            return redirect(url_for('jobs_page'))

    # Alle Jobs für den aktuellen Benutzer abrufen
    cursor = db.execute('SELECT * FROM jobs WHERE creator = ?', (current_user,))
    user_jobs = cursor.fetchall()
    
    return render_template('jobs.html', username=current_user, user_jobs=user_jobs)

@app.route('/delete_job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    """Löscht einen Job aus der Datenbank."""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = session['username']
    db = get_db_connection()
    
    # Sicherstellen, dass nur der Ersteller den Job löschen kann
    job = db.execute('SELECT * FROM jobs WHERE id = ? AND creator = ?', (job_id, current_user)).fetchone()
    if job:
        db.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
        db.commit()

    return redirect(url_for('jobs_page'))

@app.route('/run_job/<int:job_id>', methods=['POST'])
def run_job(job_id):
    """
    Führt den Docker-Befehl eines Jobs aus, erfasst die Ausgabe und Laufzeit
    und speichert die Ergebnisse in der Datenbank.
    """
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = session['username']
    db = get_db_connection()

    job = db.execute('SELECT * FROM jobs WHERE id = ? AND creator = ?', (job_id, current_user)).fetchone()
    
    if job:
        try:
            start_time = time.time()
            # Der Docker-Befehl wird aus der Datenbank gelesen
            command = job['docker_command'].split()
            
            # Subprocess ausführen und Ausgabe erfassen
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                shell=False
            )
            duration = time.time() - start_time
            
            # Ausgabe und Laufzeit in der Datenbank aktualisieren
            db.execute(
                'UPDATE jobs SET last_run_start_time = ?, last_run_duration = ?, last_run_output = ? WHERE id = ?',
                (time.strftime('%Y-%m-%d %H:%M:%S'), duration, result.stdout, job_id)
            )
            db.commit()
        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            error_output = f"Error: Command failed with exit code {e.returncode}\n{e.stderr}"
            db.execute(
                'UPDATE jobs SET last_run_start_time = ?, last_run_duration = ?, last_run_output = ? WHERE id = ?',
                (time.strftime('%Y-%m-%d %H:%M:%S'), duration, error_output, job_id)
            )
            db.commit()
        except FileNotFoundError:
            error_output = "Error: Docker command not found. Is Docker installed and in your PATH?"
            db.execute(
                'UPDATE jobs SET last_run_start_time = ?, last_run_duration = ?, last_run_output = ? WHERE id = ?',
                (time.strftime('%Y-%m-%d %H:%M:%S'), 0, error_output, job_id)
            )
            db.commit()
    
    return redirect(url_for('jobs_page'))


if __name__ == '__main__':
    create_table()
    app.run(debug=True)
