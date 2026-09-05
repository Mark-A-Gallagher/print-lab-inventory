# 3D Print Lab Inventory System

Event-sourced inventory and print-request management system for a school
3D printing lab. See [DESIGN.md](./DESIGN.md) for the full specification —
architecture, domain model, event streams, invariants, business rules, and
testing requirements. Read that before touching code; it's the contract
everything here is built against.

## Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: React + TypeScript

## Project status

Release 0.1 (Foundation) — see DESIGN.md Section 10 for the full release
sequence.

## Getting started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
