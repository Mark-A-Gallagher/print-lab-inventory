# Raspberry Pi Deployment Guide

This document describes how the 3D Print Lab Inventory System is installed and run on a Raspberry Pi 3 Model B. It records the deployment approach, the commands used during setup, the configuration involved, and troubleshooting encountered along the way.

The guide is intended to help reproduce, maintain, and troubleshoot the deployment. Some values—such as the Linux username, home directory, IP address, and exact configuration-file paths—depend on the Raspberry Pi installation and must be checked on the device rather than copied blindly.

## 1. Deployment Overview

The Raspberry Pi is used as both:

1. A local web host that runs the inventory application's backend and serves its frontend.
2. A dedicated workstation that opens the inventory application in Chromium kiosk mode.

### Hardware and software

| Component | Specification |
|---|---|
| Device | Raspberry Pi 3 Model B |
| Processor | Quad-core ARM Cortex-A53 |
| RAM | 1 GB |
| Storage | 64 GB microSD card |
| Operating system | Raspberry Pi OS 32-bit with Desktop |
| Architecture reported by `uname -m` | `armv7l` |
| Python reported during setup | 3.13.4 |

The 32-bit operating system was retained. Reinstalling the operating system or switching to 64-bit was not required for this deployment.

### Services and responsibilities

| Component | Purpose |
|---|---|
| Raspberry Pi OS | Hardware, operating system, networking, and desktop |
| Git | Retrieves the project source from GitHub |
| Python virtual environment | Isolates backend Python dependencies |
| FastAPI | Implements the application's API and business logic |
| Uvicorn | Runs FastAPI as an ASGI application |
| SQLite | Stores the application's data in a local database file |
| React / Vite | Builds the browser-based frontend |
| Nginx | Serves the production frontend and can reverse-proxy API requests |
| systemd | Runs the backend as a managed background service |
| Chromium | Displays the application in kiosk mode |

### Request flow

```text
User's browser / Chromium
          |
          v
       Nginx
          |
     +----+----------------+
     |                     |
     v                     v
React production       API request
frontend files             |
                           v
                        Uvicorn
                           |
                           v
                        FastAPI
                           |
                           v
                       SQLAlchemy
                           |
                           v
                         SQLite
```

Nginx is the browser-facing web server. Uvicorn runs the backend locally. SQLite stores the data on the Raspberry Pi.

## 2. Prepare Raspberry Pi OS

Install Raspberry Pi OS with Desktop on the microSD card and complete the first-boot setup. Connect the Raspberry Pi to a monitor, keyboard, mouse, and network.

After opening a terminal, check the system architecture and Python version:

```bash
uname -m
python3 --version
```

During this setup, the reported values were:

```text
armv7l
Python 3.13.4
```

`armv7l` confirms that the system is running a 32-bit ARM userspace. The Pi remained on this 32-bit installation.

Update the package lists and installed packages:

```bash
sudo apt update
sudo apt full-upgrade -y
```

Install the tools and services needed by the deployment:

```bash
sudo apt install -y git python3 python3-venv python3-pip python3-dev build-essential nginx sqlite3 curl
```

Package names can vary across Raspberry Pi OS releases. If a package is unavailable, check the package name for the installed release rather than changing the operating system architecture.

## 3. Retrieve the Project from GitHub

Move to the home directory and clone the repository:

```bash
cd ~
git clone https://github.com/Mark-A-Gallagher/print-lab-inventory.git
cd ~/print-lab-inventory
```

The repository is:

`https://github.com/Mark-A-Gallagher/print-lab-inventory`

### If Git cannot connect to GitHub

During the original setup, the clone attempt failed with a connection error involving GitHub on port 443. This can happen when a school or managed network restricts outbound HTTPS traffic, although the error alone does not prove that the network is the cause.

Useful checks include:

```bash
curl -I https://github.com
```

and:

```bash
git ls-remote https://github.com/Mark-A-Gallagher/print-lab-inventory.git
```

If these fail on the school network but work on another permitted network, the issue is likely network filtering or a network policy. Do not repeatedly reinstall Git or Python to solve a network connection problem.

Possible workarounds, subject to school policy, include:
- Use another network that permits access to GitHub.
- Download the repository as a ZIP file on a computer with access and transfer it to the Raspberry Pi using a USB drive.
- Ask the school's IT administrator whether GitHub HTTPS access can be allowed for the project.

Once the repository is on the Pi, enter its directory:

```bash
cd ~/print-lab-inventory
```

## 4. Set Up the Python Backend

The backend is kept in its own Python virtual environment. A virtual environment isolates the project's installed Python packages from the operating system's Python packages.

Navigate to the backend directory:

```bash
cd ~/print-lab-inventory/backend
```

Create the virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

When it is active, the terminal prompt normally displays `(.venv)`.

Install the backend requirements:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Reactivate the environment later

Whenever a new terminal is opened and backend commands need to be run, activate the environment again:

```bash
cd ~/print-lab-inventory/backend
source .venv/bin/activate
```

To leave the virtual environment:

```bash
deactivate
```

### Run the backend manually for a test

From the backend directory, with the virtual environment active:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend should listen locally on port 8000. While it is running, API documentation may be available at:

`http://127.0.0.1:8000/docs`

Stop the foreground test server with `Ctrl+C`.

The production system later runs the backend through systemd rather than requiring a terminal to remain open.

## 5. Frontend Build

The frontend uses React, TypeScript, and Vite. The Raspberry Pi 3 Model B has only 1 GB of RAM, so the production frontend build is performed on a separate development computer rather than compiling it on the Pi.

On the development computer, open a terminal in the repository's `frontend` directory:

```bash
cd frontend
npm install
npm run build
```

Vite creates the production output in the frontend build directory, normally:

```text
frontend/dist/
```

Transfer the contents of `frontend/dist` to the Raspberry Pi. A USB drive is one option. Secure copy (`scp`) can also be used when the development computer can reach the Pi over the network.

Before deploying, make sure the frontend's production API requests use the intended API address and paths for the deployment. If the frontend calls the backend directly on a different port, the browser treats that as a different origin and CORS rules apply.

## 6. CORS and the `http://localhost` Origin

One of the problems encountered during setup was that the frontend loaded, but its API requests failed in the browser with a CORS error. The browser reported that the preflight request did not receive an `Access-Control-Allow-Origin` header.

The important detail is that a browser origin includes the scheme, host, and port. For example:

- `http://localhost`
- `http://localhost:5173`
- `http://localhost:8000`

These are different origins.

When the application was opened at `http://localhost`, the browser sent that origin with its API request. FastAPI's CORS configuration did not initially include it. The working correction was to add **`http://localhost`** to the allowed origins in the existing FastAPI CORS middleware configuration.

A typical FastAPI configuration looks like this:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost",  # Added for the Raspberry Pi localhost frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Use the existing middleware and preserve any origins already needed by development. The important deployment addition was the exact origin `http://localhost`.

**Do not add a trailing slash** to the origin. `http://localhost` is not the same string as `http://localhost/` for an origin allow-list.

After changing the backend file, save it and restart the FastAPI process so the new CORS configuration is loaded.

### Restart FastAPI during manual development

If FastAPI is running in the terminal, stop it with `Ctrl+C`, then start it again:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If the backend is running as a systemd service, restart that service instead. See Section 9.

### Important distinction

CORS is a browser security mechanism; it is not a firewall rule and it does not make the backend reachable if the server is stopped or the network is unavailable.

If the frontend and API are both served through Nginx under the same origin and the frontend uses relative API paths, CORS may not be needed for those requests. The `http://localhost` allow-list entry documents the fix used for the browser origin encountered during this deployment.

## 7. Install and Configure Nginx

Nginx serves the production frontend and provides the browser-facing entry point.

Create the directory for the built frontend:

```bash
sudo mkdir -p /var/www/printlab
```

Copy the production build files from the Pi's repository checkout:

```bash
sudo cp -r ~/print-lab-inventory/frontend/dist/. /var/www/printlab/
```

Set ownership so the web server can read the files:

```bash
sudo chown -R www-data:www-data /var/www/printlab
```

Create an Nginx site configuration:

```bash
sudo nano /etc/nginx/sites-available/printlab
```

A basic single-page React application configuration with API proxy locations can look like this:

```nginx
server {
    listen 80;
    server_name _;

    root /var/www/printlab;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /spools {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /machines {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /requests {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

This is a configuration example based on the application's API route groups. Confirm the actual routes in the backend's OpenAPI page at `/docs` and include any additional route prefixes used by the current frontend. Do not remove or rename working API routes just to match this example.

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/printlab /etc/nginx/sites-enabled/printlab
```

If the default Nginx site is still enabled and conflicts with this configuration, remove its enabled-site symlink:

```bash
sudo rm /etc/nginx/sites-enabled/default
```

Test the configuration before reloading Nginx:

```bash
sudo nginx -t
```

If the test succeeds:

```bash
sudo systemctl restart nginx
sudo systemctl enable nginx
```

Nginx should now serve the production frontend on the Pi's HTTP address.

## 8. Run FastAPI as a systemd Service

Running Uvicorn in a terminal is useful for testing, but the production backend should run in the background and start automatically after a reboot.

First, determine the Linux username and home directory:

```bash
whoami
echo "$HOME"
```

The example below uses `/home/pi` and the user `pi` only as placeholders. Replace them with the actual username and paths on the Raspberry Pi.

Create the service file:

```bash
sudo nano /etc/systemd/system/printlab.service
```

Example service configuration:

```ini
[Unit]
Description=3D Print Lab Inventory Backend
After=network.target

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/print-lab-inventory/backend
ExecStart=/home/pi/print-lab-inventory/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Replace `pi` and `/home/pi` with the actual account and home directory. Keep the one-worker configuration appropriate for the Raspberry Pi's limited memory.

Tell systemd to reload its service definitions:

```bash
sudo systemctl daemon-reload
```

Enable the service at boot and start it now:

```bash
sudo systemctl enable printlab
sudo systemctl start printlab
```

Check its status:

```bash
sudo systemctl status printlab
```

View recent logs:

```bash
sudo journalctl -u printlab -n 50 --no-pager
```

Follow logs live:

```bash
sudo journalctl -u printlab -f
```

Restart the backend after changing backend code or configuration:

```bash
sudo systemctl restart printlab
```

The service name in these commands must match the filename `printlab.service`.

## 9. Chromium Kiosk Mode

The Raspberry Pi is also used as a dedicated workstation. Chromium kiosk mode opens the inventory application full-screen, without requiring someone to manually open a browser and enter the address.

The desktop should be configured to log in automatically to the intended local user. Raspberry Pi OS releases use different desktop environments and startup mechanisms, so check the installed release before choosing an autostart file.

Check the OS release and desktop session:

```bash
cat /etc/os-release
echo "$XDG_CURRENT_DESKTOP"
echo "$XDG_SESSION_TYPE"
```

Check which Chromium command is installed:

```bash
command -v chromium
command -v chromium-browser
```

The kiosk launch command is typically one of the following, depending on the installed executable:

```bash
chromium --kiosk --noerrdialogs --disable-infobars http://localhost
```

or:

```bash
chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost
```

Use the command that exists on the system. The desktop autostart configuration should launch it after the graphical session is ready. The exact autostart file depends on the Raspberry Pi OS release and desktop environment; do not assume that an LXDE autostart path and a labwc autostart path are interchangeable.

After configuring kiosk startup, reboot and verify that the desktop opens the inventory application automatically.

## 10. Verify the Deployment

Test each layer separately so that a failure can be narrowed down.

### Backend

Check the service:

```bash
sudo systemctl status printlab
```

Check the backend locally:

```bash
curl http://127.0.0.1:8000/health
```

The health endpoint must exist in the running application for this exact test to work. The interactive API documentation may also be available locally at:

`http://127.0.0.1:8000/docs`

### Nginx and frontend

Check Nginx:

```bash
sudo nginx -t
sudo systemctl status nginx
```

Open the application on the Pi:

`http://localhost`

### Network access from another device

Find the Pi's local IP address:

```bash
hostname -I
```

From another device permitted on the same network, open:

`http://<raspberry-pi-ip-address>`

Replace the placeholder with the Pi's actual local IP address. School networks may isolate wireless clients or block device-to-device traffic, so a working local browser does not automatically guarantee access from every other device.

### Reboot test

Restart the Pi:

```bash
sudo reboot
```

After it boots, verify that:
- Nginx is running.
- The FastAPI systemd service is running.
- The application loads at `http://localhost`.
- Chromium opens in kiosk mode, if kiosk autostart is enabled.
- Existing inventory data is still present.

## 11. Common Troubleshooting

### Git clone fails on port 443

A message such as `Failed to connect to github.com port 443` indicates that the Pi could not establish the HTTPS connection to GitHub. A school network may block or restrict this connection. Test with `curl -I https://github.com`, then try an approved alternative network or download-and-transfer workflow if permitted.

### Python virtual environment is not active

Navigate to the backend directory and activate it:

```bash
cd ~/print-lab-inventory/backend
source .venv/bin/activate
```

If the command reports that the file does not exist, check that `.venv` was created in the backend directory.

### Frontend loads but API calls fail

1. Open the browser developer tools and inspect the Console and Network tabs.
2. Read the exact failed request URL and browser error.
3. Confirm that FastAPI is running.
4. Confirm that Nginx forwards the API route to the backend.
5. If the browser reports a CORS preflight error and the page origin is `http://localhost`, confirm that `http://localhost` is included in FastAPI's `allow_origins` list.
6. Restart FastAPI after changing its CORS configuration.

A CORS error is different from a backend connection-refused error. The former concerns the browser's permission to read a cross-origin response; the latter usually means the target service is not reachable at the requested address and port.

### FastAPI code or configuration changed

For a foreground test server, stop it with `Ctrl+C` and start it again. For the systemd-managed production service:

```bash
sudo systemctl restart printlab
```

### Nginx configuration changed

Test the configuration first:

```bash
sudo nginx -t
```

Then reload or restart Nginx:

```bash
sudo systemctl reload nginx
```

If reload fails, inspect the error output and Nginx logs before proceeding.

### Check service logs

Backend:

```bash
sudo journalctl -u printlab -n 100 --no-pager
```

Nginx service:

```bash
sudo journalctl -u nginx -n 100 --no-pager
```

## 12. Maintenance and Data Protection

### Database location

The SQLite database path is determined by the backend configuration and its working directory. Do not assume the location: inspect the backend settings and confirm which database file the running service uses.

The live database must not be committed to Git.

### Backups

Create regular SQLite backups and store copies somewhere other than the same microSD card. A backup left only on the Raspberry Pi does not protect against microSD failure.

SQLite provides a backup command through its command-line utility. Once the actual database path is confirmed, a backup can be made with:

```bash
sqlite3 /path/to/lab_inventory.db ".backup '/path/to/backup/lab_inventory_backup.db'"
```

Replace both paths with real paths. Test restoration using a separate test database file before relying on a backup for recovery.

### Updating the application

A typical update process is:

1. Back up the live database.
2. Retrieve the intended source-code revision on the development computer or Pi, as appropriate.
3. Install any changed backend dependencies in the virtual environment.
4. Build the frontend on the development computer.
5. Transfer the new production build to the Pi.
6. Update backend files and configuration carefully.
7. Restart the backend service.
8. Test the application through Nginx.
9. Confirm that existing inventory data remains intact.

Do not overwrite the database when deploying application code.

## 13. Security and Network Considerations

- Keep the application on the intended local network.
- Do not expose the development server or backend port directly to the public internet.
- Keep the backend bound to `127.0.0.1` when Nginx is the intended entry point.
- Do not commit administrator credentials, `.env` files, tokens, or database files.
- Kiosk mode does not provide authentication or authorization.
- A local network is not automatically a trusted network. Review access control and the school's network policies before allowing broader access.
- Keep off-device database backups and periodically test restoration.

## 14. Deployment Summary

The Raspberry Pi 3 Model B runs the 3D Print Lab Inventory System using Raspberry Pi OS 32-bit. Nginx serves the production React frontend and forwards API requests to FastAPI. Uvicorn runs FastAPI as a systemd-managed service, while SQLAlchemy communicates with the local SQLite database. Chromium launches the application in kiosk mode to provide a dedicated inventory workstation.

The frontend is built on a separate computer to reduce resource use on the Pi. The deployment is intended for local lab use and is documented here so the installation, configuration, troubleshooting, and maintenance process can be repeated.
