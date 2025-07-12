# Project Weave: Status & Development Log

## Project Overview

**Goal:** "Weave" is a personal enrichment and conversation-sparking tool. It helps users process, reflect on, and generate insights from various text snippets (sujets).

**Core Components:**
*   **`weave_batch.py`:** Handles initial data ingestion from CSV, enriches sujets using OpenAI, and populates the initial `sujets.db`.
*   **Flask Web Application (`app.py`):**
    *   Serves a web interface for manual review and enrichment of sujets.
    *   Manages sujet data in an SQLite database (`instance/sujets.db`).
    *   Logs user interactions and sujet status to a Google Sheet.
*   **SQLite Database:** Stores sujet information, including original text, AI suggestions, user notes, user tags, status, and view count.

## Current Status
**Date:** 2025-07-12
**Summary:** All core features and UI are working in Chrome after successful navigation functionality restoration. The app is stable for desktop use but requires mobile optimization.

## Completed Features
- **Sujet Enrichment:** Core UI for viewing, editing notes, and assigning tags.
- **Google Sheets Logging:** All enrichment actions are logged to a Google Sheet for external tracking (though the necessity of this dual-logging is being reconsidered).
- **Database Backend:** SQLite database for storing and managing sujets.
- **Delete Functionality:** Users can permanently delete sujets from the database via the UI.
- **Reverse Sort:** Users can toggle the order in which sujets are presented (ascending/descending ID).
- **Quick Spark:** Users can fetch a random sujet for enrichment, breaking the linear flow.
- **Continuous Enrichment Model:** Removed the `needs_enrichment` filter. The app now uses offset-based fetching, allowing users to continuously cycle through, review, and edit all sujets.
- **Static Tagging System:** Using a curated, static list of tags to ensure consistency.
- **People Tagging System:** Integrated a "Person" field with multi-select capabilities.
- **PWA Functionality:** The application can be installed on devices for a more native-like experience.
- **First/Last Sujet Navigation:** Quick navigation to the beginning and end of the sujet list.

## Current TODO List (Priority Order)
1. **Database & Schema**
   - Introduce Alembic migrations for schema changes
   - Add date_created column to sujets table
   - Add favourite column/functionality
   - Decide whether to keep/drop `source_file` column
   - **Note:** All existing enrichment data must be preserved during migration

2. **UI Improvements**
   - Change reverse button into clearer ASC/DESC toggle
   - Layout & wording tweaks, compact info rows
   - Mobile optimization

3. **New Features**
   - In-app editing/creation: Allow editing a sujet's title or adding new sujets directly
   - Keyword search functionality
   - Favourite button/system (could be implemented as a tag)

4. **Bug Fixes**
   - Fix "Random Sujet" JSON Error (`Unexpected token '<'`)

## Data Flow and Persistence

1. **Initial Ingestion:** Raw sujets are imported from a CSV file (`initial_sujets.csv`) using `flask init-db`. This populates the SQLite database.
2. **Enrichment in the App:** Changes are saved directly to the database when clicking "Save".
3. **Google Sheets Logging:** Changes are also logged to a Google Sheet as a secondary backup (though this dual-persistence strategy is being reconsidered).

## Future Considerations
- Advanced filtering and retrieval (by recency, person, tags, topic depth)
- Interactive "conversation openers" and conversation training module
- Spaced repetition system for sujets
- Vector DB integration for more sophisticated retrieval

## Known Issues
- **Firefox Delete Confirmation Issue:**
  - When attempting to delete a sujet in Firefox, the `window.confirm()` dialog appears but immediately returns `false`
  - All other core functionalities work correctly in Chrome

## Refactoring Status
- Database interaction logic has been extracted from `app.py` into `db_operations.py`
- Google Sheets interaction logic has been extracted into `gsheet_operations.py`
- Previous refactoring attempts caused navigation button functionality issues that required rollback

## Deployment Lessons Learned
1. **Render persistent-disk rule:** Application image is read-only; use `/var/data` for persistent files
2. **Environment variables:** Use `os.getenv("DATABASE_PATH", "instance/sujets.db")` for flexibility
3. **Git remote hygiene:** Verify remote URLs and branch names with `git remote -v`
4. **Render deploy cycle:** Push → Render builds → new pod picks up env-vars and persistent disk
