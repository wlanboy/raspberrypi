import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24) 

MC_BINARY = "./mc"
MINIO_ALIAS = os.getenv("MINIO_ALIAS")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

def run_mc_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"MC Alias Command: {result.stdout}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"

def setup_mc_alias():
    command = [MC_BINARY, "alias", "set", MINIO_ALIAS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY]
    output = run_mc_command(command)
    print(f"MC Alias Setup: {output}")

def list_users():
    output = run_mc_command([MC_BINARY, "admin", "user", "list", MINIO_ALIAS])

    users = []
    for line in output.split('\n'):
        parts = line.split()
        if len(parts) >= 2:
            users.append(parts[1])
    return users

def list_buckets():
    output = run_mc_command([MC_BINARY, "ls", MINIO_ALIAS])
    return [line.strip().split()[-1] for line in output.split('\n') if line.strip() and not line.startswith("mc: <") and not line.startswith("mc: ERROR")]

setup_mc_alias()

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        action = request.form.get("action")
        
        # Benutzerverwaltung
        if action == "create_user":
            user = request.form.get("access_key")
            secret = request.form.get("secret_key")

            if len(secret) < 12:
                message = "Fehler: Das Secret muss mindestens 12 Zeichen lang sein."
            else:
                result = run_mc_command([MC_BINARY, "admin", "user", "add", MINIO_ALIAS, user, secret])
                message = result if "Error" in result else f"Benutzer '{user}' erstellt."
        elif action == "delete_user":
            user = request.form.get("access_key")
            result = run_mc_command([MC_BINARY, "admin", "user", "remove", MINIO_ALIAS, user])
            message = result if "Error" in result else f"Benutzer '{user}' gelöscht."
            
        # Bucket-Verwaltung
        elif action == "create_bucket":
            bucket = request.form.get("bucket_name")
            result = run_mc_command([MC_BINARY, "mb", f"{MINIO_ALIAS}/{bucket}"])
            message = result if "Error" in result else f"Bucket '{bucket}' erstellt."
        elif action == "delete_bucket":
            bucket = request.form.get("bucket_name")
            result = run_mc_command([MC_BINARY, "rb", "--force", f"{MINIO_ALIAS}/{bucket}"])
            message = result if "Error" in result else f"Bucket '{bucket}' gelöscht."
            
        # Policy-Verwaltung
        elif action == "set_policy":
            user = request.form.get("policy_user")
            bucket = request.form.get("policy_bucket")
            policy = request.form.get("policy_name")
            result = run_mc_command([MC_BINARY, "admin", "policy", "attach", MINIO_ALIAS, policy, "--user", user])
            
            message = result if "Error" in result else f"Policy '{policy}' für Benutzer '{user}' gesetzt."
        
        session['message'] = message
        return redirect(url_for("index", message=message))

    message = session.pop('message', None)

    users = list_users()
    buckets = list_buckets()
    
    return render_template("index.html", users=users, buckets=buckets, message=message)

if __name__ == "__main__":
    setup_mc_alias()
    app.run(debug=False)