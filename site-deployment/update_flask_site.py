#!/usr/bin/env python3
"""
Wizard to modify the content or code of the existing Flask site.
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

def check_root():
    """
    Ensure the script is running as root or via sudo if we intend to manipulate systemd services.
    """
    if os.geteuid() != 0:
        logger.error("This script must be run as root (sudo) if you're using systemd services!")
        sys.exit(1)

def run_command(cmd, exit_on_fail=True):
    logger.info(f"Executing command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True, check=True)
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
        if choice in ["y", "yes"]:
            return True
        elif choice in ["n", "no"]:
            return False
        else:
            print("Please answer with y or n.")

def stop_service_if_running(service_name):
    """
    Check if systemd service is active; if yes, ask user to stop it.
    """
    logger.info(f"Checking status of service '{service_name}'...")
    status_cmd = f"systemctl is-active {service_name}"
    result = run_command(status_cmd, exit_on_fail=False)
    if result and "active" in result.lower():
        logger.info(f"Service '{service_name}' is currently active.")
        if ask_user(f"Stop service '{service_name}' before editing the site?"):
            run_command(f"systemctl stop {service_name}")
            logger.info(f"Service '{service_name}' stopped.")
    else:
        logger.info(f"Service '{service_name}' is not active or not found. Skipping stop.")

def restart_service(service_name):
    """
    Attempt to restart the systemd service.
    """
    logger.info(f"Restarting service '{service_name}'...")
    run_command(f"systemctl restart {service_name}", exit_on_fail=False)

def replace_entire_file(app_path):
    """
    Prompt user for a new file path or direct text input, then replace `app.py` entirely.
    """
    logger.info("You chose to replace the entire Flask application file.")
    print("Option 1: Provide the path to a local Python file with your new Flask code.")
    print("Option 2: Enter 'manual' to open a direct multiline text editor in the console.")
    choice = input("Enter file path or 'manual': ").strip()

    if choice.lower() == "manual":
        logger.info("Entering manual edit mode. Type your code below. End with an empty line + Ctrl+D (on Linux).")
        print("> Start typing your code (empty line to finish):")
        lines = []
        while True:
            try:
                line = input()
                if not line.strip() and len(lines) > 0:
                    # If user hits Enter on an empty line, assume end
                    break
                lines.append(line)
            except EOFError:
                break
        new_content = "\n".join(lines).strip()
    else:
        # Interpret choice as a path
        file_path = Path(choice)
        if not file_path.is_file():
            logger.error(f"File not found: {file_path}. Aborting replacement.")
            return
        new_content = file_path.read_text()

    # Backup existing file
    backup_path = app_path.with_suffix(".bak")
    if app_path.exists():
        logger.info(f"Backing up existing file to {backup_path}")
        app_path.replace(backup_path)

    # Write the new file
    logger.info(f"Writing new Flask code to {app_path}")
    app_path.write_text(new_content)
    logger.info("File replaced successfully.")

def edit_only_landing_content(app_path):
    """
    Edits only the string returned at the root route ('/') of the minimal Flask app.
    Looks for a line like `return "Exfil0 Here we go", 200` and replaces the string portion.
    """
    logger.info("You chose to only edit the landing page content (root route).")

    if not app_path.exists():
        logger.error(f"File not found: {app_path}")
        return

    new_message = input("Enter new site message (without quotes): ").strip()
    if not new_message:
        logger.info("No new message provided; skipping.")
        return

    original_content = app_path.read_text().splitlines()
    updated_lines = []
    replaced = False

    for line in original_content:
        # A naive approach: find a line that looks like 'return "xyz", 200'
        # You can adjust this parsing logic if your route code is more complex.
        if "return " in line and '"' in line and "," in line:
            # Attempt a simplistic parse:
            prefix = line.split('return')[0] + 'return '
            # We'll build the updated line
            new_line = f'{prefix}"{new_message}", 200'
            updated_lines.append(new_line)
            replaced = True
        else:
            updated_lines.append(line)

    if replaced:
        app_path.write_text("\n".join(updated_lines) + "\n")
        logger.info(f"Landing message updated to: {new_message}")
    else:
        logger.warning("Could not find a line to replace (no 'return \"...\", 200' pattern found).")

def main():
    check_root()

    print("""
===============================================================
    Wizard to Update Flask Site Content or Code
===============================================================
""")

    # 1) Ask user where the Flask app is located
    default_dir = "/opt/exfil0_landing"
    ask_dir = input(f"Path to your Flask app directory? (default: {default_dir}): ").strip()
    if not ask_dir:
        ask_dir = default_dir
    app_dir = Path(ask_dir)
    if not app_dir.is_dir():
        logger.error(f"Directory not found: {app_dir}")
        sys.exit(1)

    app_file = app_dir / "app.py"
    if not app_file.exists():
        logger.error(f"Flask app file not found at {app_file}")
        sys.exit(1)

    # 2) Ask for the systemd service name (if any)
    default_service = "exfil0_flask"
    ask_service = input(f"Systemd service name? (default: {default_service}, press Enter if none): ").strip()
    if not ask_service:
        ask_service = default_service

    # 3) Optionally stop service before editing
    if ask_user(f"Stop systemd service '{ask_service}' before proceeding?"):
        stop_service_if_running(ask_service)

    # 4) Choose how to modify the site
    print("""
Choose an edit mode:
1) Replace the entire file with new code.
2) Just update the landing page text (the string returned at '/').
""")
    mode = input("Select [1/2]: ").strip()

    if mode == "1":
        replace_entire_file(app_file)
    elif mode == "2":
        edit_only_landing_content(app_file)
    else:
        logger.info("Invalid selection. Exiting without changes.")
        return

    # 5) Restart service if the user wants
    if ask_user(f"Restart systemd service '{ask_service}' now?"):
        restart_service(ask_service)
    else:
        logger.info("Skipping service restart. Manual restart is required for changes to take effect.")

    print("""
Done!
If you've replaced the entire Flask code, make sure your app is valid Python code.
If you just changed the landing page text, your new content should be set.

To confirm everything, visit your Flask site or check:
  systemctl status {ask_service}
""")

if __name__ == "__main__":
    main()
