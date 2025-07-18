# Project Weave

> A mobile-first text curation tool for Chrome Android with touch-optimized navigation.

"Weave" is a personal enrichment and conversation-sparking tool. It helps the user process, reflect on, and generate insights from a database of text snippets ('sujets').

## 🚨 CRITICAL NAVIGATION INFO 🚨

### Long Press Navigation (Chrome Android)
- **Short tap (< 300ms)**: Single navigation forward/backward
- **Long press (≥ 300ms)**: Fast navigation (10 items/second)

### ⚠️ KNOWN ISSUE: Long Press Double Navigation
**STATUS**: Currently debugging - long press triggers fast forward BUT also single navigation on release.

**See LONG_PRESS_DEBUG.md for complete debugging history and failed approaches.**

**DO NOT attempt to "fix" this without reading the debug documentation first.**

## Table of Contents

- [Features](#features)
- [🚨 Long Press Navigation Issue](#-long-press-navigation-issue)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation & Setup](#installation--setup)
- [Usage](#usage)
  - [Running the Application](#running-the-application)
  - [Controls](#controls)
- [Testing](#testing)
- [Technical Details](#technical-details)
  - [API Endpoints](#api-endpoints)
  - [Utility Scripts](#utility-scripts)
  - [Deployment](#deployment)
  - [Development History](#development-history)
- [Future Direction](#future-direction)
- [TODO List](#todo-list)

## 🚨 Long Press Navigation Issue

**CRITICAL**: Before attempting to debug or modify the long press navigation:

1. **Read `LONG_PRESS_DEBUG.md`** - Contains complete history of failed approaches
2. **Don't repeat failed solutions** - 5+ approaches have already been tried
3. **Current Status**: Testing approach using `skipIsLongPressing` flag
4. **Test Protocol**: Use Chrome remote debugging to monitor console logs

### Current Behavior
- ✅ Long press timer (300ms) triggers correctly
- ✅ Fast forward navigation works 
- ❌ Extra single navigation fires when finger lifts
- ❌ Results in double navigation at end of long press

### Architecture Problem
Multiple async events (touchstart, timeout, touchend) with flag coordination create race conditions that are extremely difficult to solve reliably.

---

## Features

- **Navigate Sujets:** Browse through sujets sequentially (`<`, `>`), or jump to the first (`<<`) and last (`>>`) entries.
- **Save, Skip, Delete:** Save notes and tags to a sujet, skip it, or remove it from the database. All actions navigate to the next sujet based on the current sort order.
- **Sort:** Toggle the navigation order between ascending (`ASC`) and descending (`DESC`).
- **Create & Edit:** Add new sujets via the `+ New` button or double-click a sujet's title to edit it.

## Getting Started

### Prerequisites

- Python 3.x
- `pip` for package management

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd Weave
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Create the virtual environment
    python -m venv venv

    # Activate on Windows
    .\venv\Scripts\Activate.ps1

    # Activate on macOS/Linux
    # source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the database:**
    If running for the first time or with an empty database, initialize it with the sample data from `initial_sujets.csv`.
    ```bash
    flask init-db
    ```

## Usage

### Running the Application

Execute the development server script:

```bash
.\run_weave_dev.bat
```

The application will be available at `http://127.0.0.1:5000`.

### Controls

- **Navigation:** Use the `<<`, `<`, `>`, `>>` buttons for navigation.
- **Actions:** Use the `Save`, `Skip`, and `Delete` buttons to manage sujets.
- **Sorting:** Click the `ASC`/`DESC` button to toggle the sort order.
- **Add New:** Click `+ New` to open the dialog for creating a new sujet.

## Testing

To run the backend test suite, ensure the virtual environment is active and run `pytest`:

```bash
pytest tests/test_app.py -v
```

## Technical Details

### API Endpoints

- `GET /get_sujet`: Fetches sujet data with optional filtering.
- `POST /save_sujet`: Saves notes, tags, and person data for a sujet.
- `POST /skip_sujet`: Marks a sujet as skipped.
- `POST /add_sujet`: Creates a new sujet.
- `DELETE /delete_sujet`: Deletes a sujet.

### Utility Scripts

- `migrate_date_format.py`: One-time script to convert `date_created` fields to `YYYY-MM-DD` format.
- `migrate_add_fake_dates.py`: Assigns placeholder dates to legacy sujets for compatibility.
- `inspect_db.py`: A diagnostic tool for analyzing database content.

### Deployment

Key lessons learned from deploying to Render:
1.  **Persistent Storage:** The application image is read-only; use `/var/data` for the persistent database file.
2.  **Environment Variables:** Use `os.getenv()` to manage configuration (e.g., `DATABASE_PATH`).
3.  **Deployment Cycle:** Push to Git -> Render builds the new version -> the new service instance starts.

### Development History

For a detailed log of architectural decisions, bug fixes, and the reasoning behind major changes, please see the [Development Log](memory.md).

## Future Direction

- **AI-Powered Q&A:** Use an LLM to conduct question-and-answer sessions based on sujet content.
- **Relationship Analysis:** Employ a vector database to identify and explore relationships between sujets.

## TODO List

1.  **Database & Schema:**
    - Introduce Alembic for database migrations.
2.  **UI Improvements:**
    - General layout and wording tweaks.
    - Mobile optimization.
3.  **New Features:**
    - Keyword search functionality.
