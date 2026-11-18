# 3D Print Lab Inventory System

A full-stack inventory and print-request management system designed for a school 3D printing lab. The application helps manage filament inventory, track individual spools, monitor 3D printers, and handle print requests while maintaining an auditable history of inventory changes.

The system uses an event-sourced architecture to ensure inventory quantities and reservations remain accurate, traceable, and consistent.

## Project Status

**Version 1.0 — Initial Usable Release (Teacher Handoff)**

The project has reached its initial usable release, following the development and release sequence outlined in [DESIGN.md](DESIGN.md). Version 1.0 represents the teacher handoff stage, with the goal of deploying the application locally for real-world testing and gathering feedback for future improvements.

## Features

- **Filament Inventory Management** — Track individual filament spools, including material, color, starting weight, remaining weight, and stock levels.
- **Inventory History** — Maintain an auditable record of inventory changes through an event-sourced system rather than directly modifying stored quantities.
- **Print Request Management** — Create and manage print requests with different statuses throughout the printing process.
- **Filament Reservations** — Reserve filament for print requests while preventing multiple requests from overcommitting available inventory.
- **Printer Management** — Track 3D printers and manage spool assignments.
- **Inventory Validation** — Enforce inventory constraints through backend business logic to prevent invalid operations and negative inventory.
- **Dashboard** — Provide an overview of the lab's inventory and operations.

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Frontend | React, TypeScript |
| Build Tool | Vite |
| API Communication | REST API |

## Architecture

The application follows a client-server architecture:

- **Frontend:** React and TypeScript provide the user interface and communicate with the backend through API requests.
- **Backend:** FastAPI handles API endpoints, business logic, request validation, and inventory calculations.
- **Database:** SQLite stores inventory records, print requests, machine information, and event histories. SQLAlchemy manages database interactions.

### Event-Sourced Inventory

Rather than directly storing and modifying current filament quantities, the system records inventory changes as individual events.

Current inventory is calculated from the accumulated history of these events. Reservations are tracked separately from physical inventory changes, allowing the system to distinguish between filament that has been used and filament that has been allocated to pending print requests.

This approach provides a traceable inventory history and helps prevent over-reservation, incorrect inventory calculations, and other inconsistencies.

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js and npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Mark-A-Gallagher/print-lab-inventory.git
cd print-lab-inventory
```

### 2. Start the Backend

Navigate to the backend directory:

```bash
cd backend
```

Create and activate a virtual environment:

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The backend will be available at:

`http://localhost:8000`

Interactive API documentation:

`http://localhost:8000/docs`

### 3. Start the Frontend

Open a second terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

The frontend will be available at:

`http://localhost:5173`

## Project Documentation

For additional technical details, see [DESIGN.md](DESIGN.md), which documents the project's:

- Architecture and design decisions
- Database schema and domain models
- Inventory and reservation event streams
- Core invariants and business rules
- API operations
- Transaction and concurrency requirements
- Testing requirements and release sequence

## Future Development

Version 1.0 establishes the initial usable foundation for the 3D printing lab. Future development will be guided by real-world testing, teacher feedback, and additional requirements identified during use.

Potential areas for continued improvement include usability, deployment, reporting, and additional inventory-management functionality.
