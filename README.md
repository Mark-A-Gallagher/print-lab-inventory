# 3D Print Lab Inventory System

A full-stack inventory and print-request management system for a school 3D printing lab. It manages individual filament spools, 3D printers, print requests, reservations, and an auditable history of inventory changes.

The system uses an event-sourced architecture: current inventory and reservations are derived from recorded events rather than maintained as manually edited totals.

## Project Status

**Version 1.0 — Deployed on Raspberry Pi**

The application is deployed and running on a Raspberry Pi 3 Model B for local use in the 3D printing lab. The Pi acts as a dedicated local host and workstation, allowing the inventory interface to be accessed locally and by other permitted devices on the same network.

## Features

- **Filament Inventory Management** — Track individual spools, including material, color, starting weight, remaining weight, and stock levels.
- **Inventory History** — Maintain an auditable record of inventory changes through an event-sourced system.
- **Print Request Management** — Create and manage print requests through their workflow statuses.
- **Filament Reservations** — Reserve filament for print requests while preventing over-commitment.
- **Printer Management** — Track 3D printers and spool assignments.
- **Inventory Validation** — Enforce business rules in the backend to prevent invalid operations and negative inventory.
- **Dashboard** — Provide an overview of lab inventory and operations.

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, FastAPI |
| ASGI Server | Uvicorn |
| Database | SQLite |
| ORM | SQLAlchemy |
| Frontend | React, TypeScript |
| Build Tool | Vite |
| Web Server / Reverse Proxy | Nginx |
| Process Management | systemd |
| Browser / Kiosk Interface | Chromium |
| API Communication | REST API over HTTP |

## Application Architecture

- **Frontend:** React and TypeScript provide the user interface and communicate with the backend through API requests.
- **Backend:** FastAPI handles API endpoints, business logic, request validation, and inventory calculations.
- **Application Server:** Uvicorn runs the FastAPI application.
- **Database:** SQLite stores inventory records, print requests, machine information, and event histories. SQLAlchemy manages database interactions.
- **Web Server:** Nginx serves the compiled frontend and forwards API requests to the backend.

### Event-Sourced Inventory

Rather than directly storing and modifying current filament quantities, the system records inventory changes as individual events. Current inventory is calculated from the accumulated history of those events.

Reservations are tracked separately from physical inventory changes. This distinguishes filament that has actually been used from filament allocated to pending print requests, and helps prevent over-reservation and inconsistent inventory calculations.

## Production Deployment

The production application runs on a Raspberry Pi 3 Model B.

| Component | Specification |
|---|---|
| Device | Raspberry Pi 3 Model B |
| Processor | Quad-core ARM Cortex-A53 |
| Memory | 1 GB RAM |
| Storage | 64 GB microSD card |
| Operating System | Raspberry Pi OS 32-bit |
| Python | 3.13.4 |

The React frontend is built on a separate development computer and the generated production files are transferred to the Pi. Nginx serves the frontend and acts as the entry point for API requests. FastAPI runs under Uvicorn as a systemd-managed service, and SQLite stores application data locally.

The Raspberry Pi desktop is configured to open the application in Chromium kiosk mode, allowing the device to function as a dedicated inventory workstation.

The deployment is intended for local lab use, not direct public-internet exposure. Access from other devices depends on the local network allowing communication with the Raspberry Pi.

For the complete installation procedure, configuration examples, troubleshooting notes, and maintenance instructions, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Getting Started: Local Development

The following instructions are for development on a separate computer. They are not required for ordinary users accessing the deployed Raspberry Pi application.

### Prerequisites

- Python compatible with the versions specified by the project dependencies
- Node.js and npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Mark-A-Gallagher/print-lab-inventory.git
cd print-lab-inventory
```

### 2. Start the Backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

Install dependencies and start the development server:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend will normally be available at `http://localhost:8000`.

Interactive API documentation: `http://localhost:8000/docs`.

### 3. Start the Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite will display the local frontend address, normally `http://localhost:5173`.

## Project Documentation

- **[DESIGN.md](DESIGN.md)** — Application architecture, domain model, event streams, invariants, business rules, database design, API operations, and production architecture.
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Raspberry Pi installation, configuration, deployment, troubleshooting, and maintenance.

## Operational Notes

- Do not commit the live SQLite database, virtual environments, local environment files, credentials, or generated secrets.
- Back up the live database regularly and periodically copy backups off the Raspberry Pi.
- Test application changes in development before deploying them to the lab system.
- Local network availability depends on the school's network configuration and device-to-device access policies.
