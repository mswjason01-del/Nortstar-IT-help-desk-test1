# Northstar Help Desk

A portfolio-ready internal IT support system built with Flask and SQLite. It models a real help desk workflow: employees submit and track requests, while IT staff triage, assign, document, and resolve them.

## What it demonstrates

- Python / Flask routing, forms, validation, and request handling
- SQL-backed CRUD operations with SQLite
- Relational data modelling: tickets and their troubleshooting notes
- A business-focused workflow with priorities, assignment, status, filtering, and resolution history
- Responsive, professional UI built with semantic HTML and custom CSS

## Run locally

1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Start the application: `flask --app app run --debug`
5. Open the local address shown in the terminal.

The app creates `helpdesk.db` automatically and seeds a few realistic tickets on first run. Delete that database file to start over with a fresh demo dataset.

## Data model

`tickets` stores the request, requester, category, priority, assignment, and lifecycle timestamps. `notes` stores a chronological troubleshooting history linked to its ticket by a foreign key.

## Portfolio talking point

> I designed and built a database-backed IT support portal that turns employee problems into trackable operational work. The system uses Flask and SQLite to manage ticket creation, filtering, assignment, troubleshooting history, and resolution status.
