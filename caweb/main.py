import subprocess
import os
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

SCRIPT_PATH = "./create.sh"
CERT_DIR = os.getenv("LOCAL_CA_PATH", "/local-ca")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        hostname = request.form.get("hostname")
        alt_names_input = request.form.get("alt_names")
        
        alt_names = [name.strip() for name in alt_names_input.split(',') if name.strip()]
        
        command = [SCRIPT_PATH, hostname] + alt_names
        
        try:
            # Ausführen des Skripts
            subprocess.run(command, check=True, capture_output=True, text=True)
            
            # Die Pfade müssen den neuen Ordner `local-ca` berücksichtigen
            cert_file = os.path.join(CERT_DIR, hostname, f"{hostname}.crt")
            key_file = os.path.join(CERT_DIR, hostname, f"{hostname}.key")
            
            with open(cert_file, "r") as f:
                cert_content = f.read()
            
            with open(key_file, "r") as f:
                key_content = f.read()

            return render_template("results.html", hostname=hostname, cert_content=cert_content, key_content=key_content)
        
        except subprocess.CalledProcessError as e:
            return f"Fehler bei der Ausführung des Skripts: {e.stderr}"
    
    return render_template("form.html")

@app.route("/download/<path:filename>")
def download_file(filename):
    # Der Download-Pfad muss ebenfalls angepasst werden
    full_path = os.path.join(CERT_DIR, filename)
    return send_file(full_path, as_attachment=True)

if __name__ == "__main__":
    if not os.access(SCRIPT_PATH, os.X_OK):
        os.chmod(SCRIPT_PATH, 0o755)
    
    app.run(debug=True)