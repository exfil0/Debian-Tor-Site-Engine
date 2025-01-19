# Debian Tor Site Engine

A comprehensive wizard-style tool to install and configure a **single-instance Tor hidden service** on Debian/Ubuntu systems. It also sets up basic security (UFW, Fail2Ban), synchronizes the system clock, and optionally disables SELinux if present.

> **Disclaimer:**  
> This script is intended for legitimate uses only. Operating hidden services or servers may be restricted or illegal in your jurisdiction. Always follow your local laws, and use Tor responsibly.

---

## Description

The **Dark Web Server Wizard** (`setup_darkweb_server.py`) is an automated script that:

1. **Purges old Tor configurations** to avoid conflicts with multi-instance setups.  
2. **Installs single-instance Tor** alongside security packages (`ufw`, `fail2ban`, `git`, `build-essential`, `openssl`).  
3. **Sets up a minimal Tor configuration** (`/etc/tor/torrc`) that maps an `.onion` address to local port 80.  
4. **Enables UFW** firewall rules (allowing inbound on ports `22`, `9050`, and `80` only).  
5. **Enables Fail2Ban** to mitigate brute-force attacks.  
6. **Optionally disables SELinux**, if detected.  
7. **Synchronizes the system clock** with `ntpdate` (important for Tor’s correct operation).
8. **Flask Addons**:  
   - **`flask.py`**: Deploys a minimal Flask site (“Exfil0 Here we go”) behind Tor.  
   - **`update_flask_site.py`**: A wizard to change or replace the Flask site content/code after deployment.

This script interacts with you via yes/no prompts, making it easy to skip or include specific steps.

![dtse](dtse.png)

---

## Features

- **Wizard-Style Prompts**: Step-by-step approach, giving you full control over each operation.  
- **Fresh Tor Setup**: Ensures no leftover multi-instance configs.  
- **Security Tools**: Quickly hardens your server with UFW and Fail2Ban.  
- **Time Sync**: Avoids Tor clock-related issues by installing and running `ntpdate`.  
- **SELinux Handling**: Gracefully disables SELinux if present; otherwise, it’s skipped.  
- **SSH Convenience**: Optionally keeps SSH password authentication enabled for debugging (which you can disable later).  
- **Flask Deployment & Management**:  
  - **`flask.py`** sets up a simple site.  
  - **`update_flask_site.py`** provides a wizard to edit or replace the site’s content.

---

## Installation

1. **Clone or Download the Repository**

   ```bash
   git clone https://github.com/exfil0/Debian-Tor-Site-Engine.git
   cd Debian-Tor-Site-Engine
   ```

2. **Make Scripts Executable**

   ```bash
   chmod +x setup_darkweb_server.py
   chmod +x site-deployment/flask.py
   chmod +x site-deployment/update_flask_site.py
   ```

3. **Run the Main Wizard as Root**

   ```bash
   sudo ./setup_darkweb_server.py
   ```

   You will be prompted with yes/no questions for each major step.

4. **(Optional) Deploy the Flask Addon**

   ```bash
   sudo ./site-deployment/flask.py
   ```

   - Installs Flask if not already present.
   - Creates a simple “Exfil0 Here we go” landing page on port 80.
   - (Optional) Sets up a systemd service to keep the Flask app running continuously.

5. **(Optional) Modify the Flask Site Later**

   ```bash
   sudo ./site-deployment/update_flask_site.py
   ```

   - Provides a wizard to replace the entire `app.py` or just edit the homepage text.
   - Optionally stops the systemd service before changes and restarts it afterward.

6. **Python 3 Requirement**

   On some systems, you may need to install Python 3 if it isn’t already present:

   ```bash
   sudo apt-get update && sudo apt-get install -y python3
   ```

---

## Usage

### 1. Follow the Prompts (in `setup_darkweb_server.py`)

- **Purge Old Tor?** Recommended unless you need your existing Tor config.
- **Sync Time?** Highly recommended to ensure Tor works properly.
- **Disable SELinux?** Primarily for SELinux-enabled systems (like CentOS).
- **Install Tor & Security Packages?** Installs single-instance Tor, UFW, Fail2Ban, Git, etc.
- **Write Minimal `torrc`?** Creates `/etc/tor/torrc` mapping `.onion` to `127.0.0.1:80`.
- **Enable & Start Tor?** Waits for Tor to generate a `.onion` hostname.
- **Configure Security (UFW, Fail2Ban, SSH)?** Locks down inbound ports except `22`, `9050`, `80`.

### 2. Host Your Web Service

Once complete, you’ll have a `.onion` address printed to your screen. To serve content:

- Run any server on `127.0.0.1:80` (e.g., `apache2` or `python3 -m http.server`).
- Access your hidden service in Tor Browser at `http://YOUR_ONION_ADDRESS.onion`.

### 3. Flask Landing Page (Optional)

- Run `sudo ./site-deployment/flask.py` to install a minimal Flask app listening on port `80`.
- The landing page will display “Exfil0 Here we go.”

### 4. Update/Change Flask Code (Optional)

If you want to modify your Flask site’s text or upload a new code file, run:

   ```bash
   sudo ./site-deployment/update_flask_site.py
   ```

   This wizard can:

   - Stop the systemd service (if configured).
   - Replace your entire `app.py` or just edit the landing page message.
   - Restart the service so changes take effect immediately.

### 5. Check Logs

   ```bash
   sudo journalctl -u tor -n 100 --no-pager
   ```

   Shows the latest Tor logs. Adjust `-n` as needed.

---

## Roadmap

### 1. Flask Integration

Enhance the sample Flask app with templating, user authentication, or database integration.

### 2. Crawlers

Optionally add scripts to index or monitor hidden services, or to crawl external onion links for research.

### 3. Monitors

Integrate monitoring tools (like `monit` or `prometheus-node-exporter`) to track Tor uptime, server performance, and intrusion attempts.

---

## Contributing

1. **Fork this repository.**
2. **Create a branch:**

   ```bash
   git checkout -b feature/new-feature
   ```

3. **Commit your changes:**

   ```bash
   git commit -am 'Add some feature'
   ```

4. **Push to your fork:**

   ```bash
   git push origin feature/new-feature
   ```

5. **Open a Pull Request.**

   We appreciate bug reports, feature requests, and pull requests!

---

## License

This project is open-source under the MIT License.  
Feel free to fork and adapt it while attributing the original author(s).

---

**Enjoy your new Tor hidden service and Flask site!**
