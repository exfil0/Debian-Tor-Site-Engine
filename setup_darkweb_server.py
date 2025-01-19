#!/usr/bin/env python3

import os
import sys
import subprocess
import time
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
    Ensure the script is running as root, otherwise exit.
    """
    if os.geteuid() != 0:
        logger.error("This script must be run as root or with sudo privileges!")
        sys.exit(1)

def ask_user(question):
    """
    Simple Y/N prompt. Returns True if user answers 'y'/'yes', False if 'n'/'no'.
    """
    while True:
        choice = input(f"{question} [y/n]: ").strip().lower()
        if choice in ["y", "yes"]:
            return True
        elif choice in ["n", "no"]:
            return False
        else:
            print("Please answer with y or n.")

def run_command(command, exit_on_fail=True):
    """
    Runs 'command' as 'sudo command' if not already root. Captures stdout/stderr in logs.
    Returns stdout if success, else None (exits if exit_on_fail=True).
    """
    # If already root, 'sudo' is optional, but we keep it for consistency
    cmd_string = f"sudo {command}" if os.geteuid() != 0 else command

    logger.info(f"Executing command: {command}")

    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"

    try:
        result = subprocess.run(
            cmd_string,
            shell=True,
            text=True,
            check=True,
            capture_output=True,
            env=env
        )
        stdout = result.stdout.strip()
        if stdout:
            for line in stdout.splitlines():
                logger.debug(f"CMD-OUT: {line}")
        return stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr.strip()}")
        if exit_on_fail:
            sys.exit(1)
        return None

def wizard_banner():
    """
    Prints a fancy banner for the wizard.
    """
    print("""
###################################################
##        Dark Web Server Wizard (Tor Only)      ##
##   Single-Instance Tor Hidden Service Setup    ##
###################################################
""")

def detect_selinux():
    """
    Returns True if SELinux is likely present/enabled, False otherwise.
    Checks for setenforce & /etc/selinux/config.
    """
    # Quick check if 'setenforce' is available and /etc/selinux/config exists
    if Path("/etc/selinux/config").is_file():
        setenforce_path = subprocess.run(
            ["which", "setenforce"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        ).stdout.strip()
        return bool(setenforce_path)
    return False

# -----------------------------------------------------------
# Primary Steps
# -----------------------------------------------------------

def purge_old_tor():
    """
    Stops & removes old Tor multi-instance or leftover configs/data.
    Ensures a fresh single-instance environment.
    """
    logger.info("Purging any old Tor or multi-instance config...")

    # Disable old services
    run_command("systemctl disable tor@default --now", exit_on_fail=False)
    run_command("systemctl disable tor --now", exit_on_fail=False)

    # Remove multi-instance directory if present
    run_command("rm -rf /etc/tor/instances", exit_on_fail=False)

    # Purge tor
    run_command("apt-get purge -y tor", exit_on_fail=False)

    # Clean leftover configs
    run_command("rm -f /etc/tor/torrc /etc/tor/torrc.*", exit_on_fail=False)
    run_command("rm -rf /var/lib/tor/*", exit_on_fail=False)

    logger.info("Old tor configs purged.")

def fix_time():
    """
    Installs ntpdate, forcibly syncs system clock, and enables NTP via timedatectl.
    """
    logger.info("Syncing system clock with ntpdate...")
    run_command("apt-get update && apt-get install -y ntpdate", exit_on_fail=False)
    out = run_command("ntpdate -u pool.ntp.org", exit_on_fail=False)
    if out:
        logger.info(f"ntpdate output: {out}")
    else:
        logger.warning("Time sync had no output; check network or logs.")
    run_command("timedatectl set-ntp true", exit_on_fail=False)

def disable_selinux_if_present():
    """
    Disables SELinux if the system has it.
    Safe to skip if not present (typical for Debian/Ubuntu).
    """
    logger.info("Checking if SELinux is present...")
    if detect_selinux():
        logger.info("SELinux detected; attempting to disable...")
        run_command("setenforce 0", exit_on_fail=False)
        run_command("sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config", exit_on_fail=False)
        logger.info("SELinux set to permissive/disabled. A reboot may be required on some systems.")
    else:
        logger.info("SELinux not detected or not applicable. Skipping SELinux disable.")

def install_tor_and_security():
    """
    Installs single-instance Tor plus security tools: UFW, Fail2Ban, Git, Build-Essential, OpenSSL.
    """
    logger.info("Installing Tor and security packages (ufw, fail2ban, etc.)...")
    packages = ["tor", "ufw", "fail2ban", "git", "build-essential", "openssl"]
    run_command(f"apt-get update && apt-get install -y {' '.join(packages)}")
    logger.info("Tor (single-instance) & security packages installed.")

def write_minimal_torrc():
    """
    Writes a minimal /etc/tor/torrc:
      - Single SocksPort, logs to /var/log/tor
      - HiddenServiceDir /var/lib/tor/hidden_service
      - HiddenServicePort 80 -> 127.0.0.1:80
    """
    logger.info("Writing minimal /etc/tor/torrc for single-instance hidden service...")
    minimal_conf = """\
SocksPort 9050
Log notice file /var/log/tor/notice.log
Log debug file /var/log/tor/debug.log

HiddenServiceDir /var/lib/tor/hidden_service
HiddenServicePort 80 127.0.0.1:80
"""
    run_command("rm -f /etc/tor/torrc", exit_on_fail=False)
    Path("/etc/tor/torrc").write_text(minimal_conf)
    logger.info("Minimal torrc ready.")

def enable_tor_single_instance():
    """
    Enables & restarts the 'tor' systemd service (single-instance),
    then waits up to 60s for /var/lib/tor/hidden_service/hostname to appear.
    Returns the onion address if found.
    """
    logger.info("Enabling single-instance tor.service...")
    run_command("systemctl enable tor")
    run_command("systemctl restart tor")

    # Ensure log directory exists
    run_command("mkdir -p /var/log/tor && chmod 755 /var/log/tor", exit_on_fail=False)

    hostname_file = Path("/var/lib/tor/hidden_service/hostname")
    max_wait = 60
    elapsed = 0
    while elapsed < max_wait:
        if hostname_file.exists():
            onion_addr = hostname_file.read_text().strip()
            logger.info(f"Your .onion address is: {onion_addr}")
            return onion_addr
        time.sleep(5)
        elapsed += 5

    logger.error("No /var/lib/tor/hidden_service/hostname found after 60s. Check 'journalctl -u tor'.")
    sys.exit(1)

def secure_server():
    """
    Configures UFW (default deny inbound except 22,9050,80),
    enables Fail2Ban, and ensures SSH password authentication is ON (for debugging).
    """
    logger.info("Configuring UFW, Fail2Ban, and SSH password auth...")

    run_command("ufw default allow outgoing")
    run_command("ufw default deny incoming")
    run_command("ufw allow 22/tcp")
    run_command("ufw allow 9050")
    run_command("ufw allow 80")
    run_command("ufw --force enable")
    logger.info("UFW enabled. Inbound allowed only on ports 22, 9050, and 80.")

    run_command("systemctl enable fail2ban && systemctl start fail2ban")
    logger.info("Fail2Ban enabled.")

    # Keep SSH password auth for easier debugging. You can disable later.
    run_command(r"sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config")
    run_command("systemctl restart ssh")
    logger.info("SSH password auth is ON (for debugging). Remember to disable if needed.")

# -----------------------------------------------------------
# Main Wizard Flow
# -----------------------------------------------------------

def main():
    check_root()       # Ensure script is run as root
    wizard_banner()    # Print the banner

    # Step A: Purge old Tor
    if ask_user("Purge old Tor configs (recommended for a clean setup)?"):
        purge_old_tor()
    else:
        logger.info("Skipping old Tor purge.")

    # Step B: Time sync
    if ask_user("Sync system clock with ntpdate?"):
        fix_time()
    else:
        logger.info("Skipping time sync. Make sure your system clock is correct, or Tor might fail.")

    # Step C: Disable SELinux (if present)
    if ask_user("Disable SELinux if present (recommended on RHEL/CentOS)?"):
        disable_selinux_if_present()
    else:
        logger.info("Skipping SELinux disable. If you have SELinux enforced, Tor might have issues.")

    # Step 1: Install Tor + security pkgs
    if ask_user("Install Tor, UFW, Fail2Ban, Git, and other packages now?"):
        install_tor_and_security()
    else:
        logger.info("Skipping Tor & security package installation. Ensure Tor is installed manually.")

    # Step 2: Write minimal torrc
    if ask_user("Write a minimal /etc/tor/torrc for a hidden service on port 80?"):
        write_minimal_torrc()
    else:
        logger.info("Skipping minimal torrc. Make sure you have your own config in /etc/tor/torrc.")

    # Step 3: Start Tor, wait for onion address
    if ask_user("Enable and start single-instance Tor now?"):
        onion_addr = enable_tor_single_instance()
    else:
        logger.info("Skipping Tor start. Please ensure you manually enable and start Tor.")
        onion_addr = "UNAVAILABLE"

    # Step 4: Secure server (UFW + Fail2Ban + SSH Password auth)
    if ask_user("Configure UFW, enable Fail2Ban, and ensure SSH password auth?"):
        secure_server()
    else:
        logger.info("Skipping security steps. Make sure you have a firewall and Fail2Ban configured.")

    # Final message
    print(f"""
All done!

Your onion address is: {onion_addr if onion_addr != "UNAVAILABLE" else "(not generated)"}

If you want to serve HTTP behind Tor, run a web server on 127.0.0.1:80.
Tor will map onion:80 → localhost:80. Then open:
  http://{onion_addr}
in Tor Browser (if you started Tor and have the onion address).

Check logs:
  sudo journalctl -u tor -n 100 --no-pager

Enjoy your single-instance Tor hidden service!
    """)

# -----------------------------------------------------------
# Entry Point
# -----------------------------------------------------------
if __name__ == "__main__":
    main()
