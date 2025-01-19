#!/usr/bin/env python3
"""
Deploys a minimal Flask app that serves "Exfil0 Here we go" 
on the root URL (/) and optionally configures it as a systemd service.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# -----------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------

def check_root():
    """
    Ensure the script is running as root or with sudo.
    """
    if os.geteuid() != 0:
        logger.error("This script must be run as root (sudo)!")
        sys.exit(1)

def run_command(cmd, exit_on_fail=True):
    """
    Run a shell command with logging and optional exit on failure.
    """
    logger.info(f"Executing command: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr.strip()}")
        if exit_on_fail:
            sys.exit(1)
        return None

def ask_user(question):
    """
    Simple Y/N prompt returning True/False.
    """
    while True:
        choice = input(f"{question} [y/n]: ").strip().lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print("Please answer with y or n.")

# -----------------------------------------------------------
# Deployment Steps
# -----------------------------------------------------------

def install_flask():
    """
    Installs Flask using apt + pip (whichever approach is simplest).
    If python3-flask is available in apt, that might suffice.
    """
    logger.info("Updating apt and installing python3-flask...")
    run_command("apt-get update")
    run_command("apt-get install -y python3 python3-pip python3-flask")

def write_flask_app(target_dir="/opt/exfil0_landing", port=80):
    """
    Writes a minimal Flask application that displays 
    'Exfil0 Here we go' on the root URL.
    """
    logger.info(f"Creating Flask app directory: {target_dir}")
    Path(target_dir).mkdir(parents=True, exist_ok=True)

    app_py = f"""\
#!/usr/bin/env python3
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Exfil0 Here we go", 200

if __name__ == "__main__":
    # Listen on all interfaces (0.0.0.0) by default
    app.run(host="0.0.0.0", port={port})
"""

    app_path = Path(target_dir) / "app.py"
    app_path.write_text(app_py)
    logger.info(f"Flask app written to {app_path}")

def create_systemd_service(service_name="exfil0_flask", app_dir="/opt/exfil0_landing", user="root"):
    """
    Creates a systemd service that runs the Flask app in background.
    """
    logger.info(f"Creating systemd service '{service_name}.service'...")

    service_file = f"""\ 
[Unit]
Description=Exfil0 Flask App
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={app_dir}
ExecStart=/usr/bin/python3 {app_dir}/app.py
Restart=always

[Install]
WantedBy=multi-user.target
"""

    systemd_path = Path(f"/etc/systemd/system/{service_name}.service")
    systemd_path.write_text(service_file)

    logger.info("Reloading systemd daemon and enabling service...")
    run_command("systemctl daemon-reload")
    run_command(f"systemctl enable {service_name}")
    run_command(f"systemctl restart {service_name}")
    logger.info(f"Systemd service '{service_name}' started and enabled.")

# -----------------------------------------------------------
# Main
# -----------------------------------------------------------

def main():
    check_root()

    print("""
==============================================================
    Flask Deployment Wizard - "Exfil0 Here we go" Landing
==============================================================
""")

    # Step 1: Install Flask
    if ask_user("Install Flask (and prerequisites) via apt-get & pip?"):
        install_flask()
    else:
        logger.info("Skipping Flask installation. Make sure Flask is installed manually.")

    # Step 2: Write the minimal Flask application
    default_dir = "/opt/exfil0_landing"
    dir_choice = input(f"Where to deploy the Flask app? (default: {default_dir}): ").strip()
    if not dir_choice:
        dir_choice = default_dir

    default_port = "80"
    port_choice = input(f"Which port should Flask listen on? (default: {default_port}): ").strip()
    if not port_choice:
        port_choice = default_port

    try:
        port_num = int(port_choice)
    except ValueError:
        logger.error(f"Invalid port number: {port_choice}. Defaulting to 80.")
        port_num = 80

    write_flask_app(dir_choice, port_num)

    # Step 3: Optionally create a systemd service
    if ask_user("Create a systemd service to run Flask in the background?"):
        default_service_name = "exfil0_flask"
        srv_name = input(f"Service name? (default: {default_service_name}): ").strip()
        if not srv_name:
            srv_name = default_service_name

        # Optionally run under a specific user
        default_user = "root"
        run_user = input(f"Run service as user? (default: {default_user}): ").strip()
        if not run_user:
            run_user = default_user

        create_systemd_service(srv_name, dir_choice, run_user)
    else:
        logger.info("Skipping systemd service setup. You can manually run app.py with python3.")

    print(f"""
Deployment Complete!

Your Flask landing page says "Exfil0 Here we go" at the root URL.

- If you created a systemd service, it's named:
  {srv_name if 'srv_name' in locals() else '(none)'}

- If you didn't, run the app manually:
  cd {dir_choice}
  python3 app.py

- Flask is listening on port {port_num}.
  Access it at http://<server-IP>:{port_num}/
""")

# -----------------------------------------------------------
# Entry Point
# -----------------------------------------------------------

if __name__ == "__main__":
    main()
