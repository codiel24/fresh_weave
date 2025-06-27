# Project Weave: Status & Development Log

This file is being updated to trigger a new deployment on Render.

## Current Status
**Date:** 2025-06-18
**Summary:** All core features and UI are working in both Chrome and Firefox after a successful rollback. The app is accessible on desktop, but not yet optimized for compact mobile use. The backend and frontend are stable and ready for UI/UX improvements. Next priority: UI optimization for mobile (compact buttons, eliminate wasted space, fit on one screen). PWA/Android deployment will resume after UI cleanup. (Rollback on 2025-06-18 restored all functionality and stability.)

## Completed Features
- **Sujet Enrichment:** Core UI for viewing, editing notes, and assigning tags.
- **Google Sheets Logging:** All enrichment actions are logged to a Google Sheet for external tracking.
- **Database Backend:** SQLite database for storing and managing sujets.
- **Delete Functionality:** Users can permanently delete sujets from the database via the UI.
- **Reverse Sort:** Users can toggle the order in which sujets are presented (ascending/descending ID).
- **Quick Spark:** Users can fetch a random sujet for enrichment, breaking the linear flow.
- **Continuous Enrichment Model (June 2025):** Removed the `needs_enrichment` filter. The app now uses offset-based fetching, allowing users to continuously cycle through, review, and edit all sujets in the database.
- **Static Tagging System (June 2025):** Replaced the dynamic, AI-generated tag buttons with a curated, static list of tags to ensure consistency.
- **People Tagging System (June 2025):** Integrated a "Person" field with multi-select capabilities, defaulting to all selected to streamline workflow.
- **PWA Functionality (June 2025):** The application is now a Progressive Web App, allowing it to be installed on desktop and mobile devices for a more native-like experience.
- **First/Last Sujet Navigation (June 2025):** Added 'First' and 'Last' buttons to the UI, allowing for quick navigation to the beginning and end of the sujet list.

## Next Steps (June 2025)
- **Finish Render SSH Access & Persistent-Disk Sync:** Generate an SSH key, add it to Render, and upload the five persistent files (`sujets.db`, two CSVs, the service-account JSON, and `last_processed_index.txt`) to `/var/data`.
- **Restore Full UI (per 2025-06-18 screenshot):** Bring back the filter/tag toggle and related counters that are currently hidden or broken.
- **Fix “Random Sujet” JSON Error:** Resolve the `Unexpected token '<'` error returned from `/get_random_sujet`.
- **UI Layout & Wording Cleanup:** Stabilise element positions, compact info rows, and ensure mobile responsiveness.
- **Advanced Filtering Enhancements:** Re-test tag & people combination filtering and polish the UX.
- **Database Migration Strategy:** Introduce Alembic (or similar) for schema changes and decide the fate of the `source_file` column.

## Known Issues / Backlog
- Review `source_file` column usage in the database.

## 1. Project Overview

**Goal:** "Weave" is a personal enrichment and conversation-sparking tool. It helps users process, reflect on, and generate insights from various text snippets (sujets).

**Core Components:**
*   **`weave_batch.py`:** Handles initial data ingestion from CSV, enriches sujets using OpenAI (e.g., AI suggestions, tags), and populates the initial `sujets.db`.
*   **Flask Web Application (`app.py`):**
    *   Serves a web interface (`templates/index.html`, `static/script.js`, `static/style.css`) for manual review and enrichment of sujets.
    *   Manages sujet data in an SQLite database (`instance/sujets.db`).
    *   Logs user interactions and sujet status to a Google Sheet.
*   **SQLite Database (`instance/sujets.db`):** Stores sujet information, including original text, AI suggestions, user notes, user tags, status, and view count.
*   **Google Sheets Integration:** Used for logging and tracking the enrichment process.

## 2. Key Features & Milestones

### Completed
*   **Initial Batch Enrichment:** `weave_batch.py` processes CSV and uses OpenAI.
*   **Web UI for Manual Enrichment:** Users can view sujets, AI suggestions, add notes, and tags.
*   **Status Tracking:** Sujets can be 'needs_enrichment', 'enriched', or 'skipped'.
*   **Google Sheets Logging:** Basic logging of sujet processing.
*   **Navigation Improvements (Back Button & Re-Enrichment - May 2025):**
    *   Implemented a robust "Back" button functionality allowing users to navigate to previously viewed sujets.
    *   Enabled "Re-Enrichment": Users can modify notes and tags of already 'enriched' or 'skipped' sujets. The backend (`/save_sujet`, `/skip_sujet`) now updates sujets regardless of their prior status, and `log_sujet_to_sheet` is called to reflect these updates.
    *   Frontend `script.js` updated to manage history, enable buttons appropriately, and handle actions for revisited sujets.

### In Progress / Next Up
*   (See Current TODO List)

## 3. Data Flow and Persistence

To ensure that no enrichment work is lost, the application follows a clear data flow:

1.  **Initial Ingestion:** Raw sujets are imported into the system from a CSV file (`initial_sujets.csv`) using a command-line script (`flask init-db`). This populates the SQLite database (`instance/sujets.db`), which serves as the single source of truth for all sujet data.
2.  **Enrichment in the App:** As you use the web interface to add notes, tags, and assign a person to a sujet, these changes are saved directly to the `sujets.db` database when you click "Save".
3.  **Google Sheets Logging:** As a secondary backup and for external analysis, every saved change (including skips and deletions) is logged as a new row in a designated Google Sheet. This provides a complete, timestamped history of all actions taken.

This dual-persistence strategy (SQLite for the live app, Google Sheets for historical logging) ensures that your enrichments are securely stored and recoverable.

## 4. Current TODO List (updated 2025-06-26)

1. **Render Deployment**  
   • Create SSH key → add to Render → run five `scp` uploads to `/var/data`.  
2. **UI Restoration**  
   • Re-enable filter/tag toggle and counters as seen on 2025-06-18 screenshot.  
3. **Bug Fixes**  
   • Resolve JSON parsing error when fetching a random sujet.  
4. **UI/UX Polish**  
   • Layout & wording tweaks, compact info rows, mobile optimisation.  
5. **Advanced Filtering**  
   • Verify & refine combined tag/people filtering; add recency filter.  
6. **Database & Schema**  
   • Introduce Alembic migrations.  
   • Decide whether to keep/drop `source_file` column.

_Completed since last update: Delete button, Reverse-sort toggle, Person field integration._
6.  **Implement Better Post-Completion UI:** Enhance the user experience when all sujets have been processed (currently shows "No more sujets to display").
- **Implement "Best Of" Retrieval:** Develop a feature to quickly retrieve a particularly engaging sujet (e.g., based on view count or other metrics).
- **In-App Editing/Creation:** Allow users to edit a sujet's title or add a completely new sujet directly from the web interface.

## 5. Future Considerations / Larger Features

*   Advanced filtering and retrieval in the UI (by recency, person, tags, topic depth).
*   Interactive "conversation openers" and conversation training module with grading.
*   Evaluate the role of manual tags if/when a Vector DB is integrated.

## 6. Architectural Notes & Decisions

*   **Frontend-Backend Communication:** Uses Fetch API for asynchronous calls from `script.js` to Flask routes.
*   **History Management (Frontend):** `script.js` maintains a `history` array of `sujet.id`s for back navigation.
*   **Tagging:** Switched to a static, curated list of tags for consistency. The UI now presents a fixed set of tag buttons. The underlying AI tag suggestion logic is preserved but currently disabled in the UI.

## 7. Known Issues / Bugs
*   **Firefox Delete Confirmation Issue (as of 2025-06-19):**
    *   **Symptom:** When attempting to delete a sujet in Firefox, the `window.confirm()` dialog appears, but the JavaScript code immediately receives a `false` result (as if "Cancel" was clicked), even if the user takes no action or clicks "OK". This prevents sujet deletion in Firefox.
    *   **Debugging:** The issue is confirmed by console logs in `static/script.js` showing `window.confirm result: false`.
    *   **Status:** All other core functionalities (save, skip, delete) are working correctly in Chrome.
    *   **Next Steps for Troubleshooting:**
        1.  Test delete functionality in Firefox Safe Mode (to rule out extension interference).
        2.  Test delete functionality in a new, clean Firefox profile (to rule out profile corruption).
        3.  Investigate Firefox settings related to pop-ups, dialogs, or site-specific permissions for `127.0.0.1` or `localhost` that might be auto-cancelling the confirmation.
        4.  If the above steps don't resolve it, consider implementing a custom modal dialog for delete confirmation as an alternative to `window.confirm` for broader compatibility.

*   **Refactoring Status (June 2025):**
    *   **Completed:** Database interaction logic has been extracted from `app.py` into `db_operations.py`. Google Sheets interaction logic has been extracted into `gsheet_operations.py`.
    *   **Assessment:** While the refactoring process introduced significant temporary instability and consumed considerable debugging time (primarily due to errors in managing import changes), the resulting modular code structure is an improvement for long-term maintainability and separation of concerns. `app.py` is now more focused on request handling and core application flow.

---

## 8. Lessons Learned (June 2025)

1. **Render persistent-disk rule of thumb**  The application image is read-only; anything you `scp` into a running pod disappears on the next deploy. Always mount or reference files from `/var/data` (the persistent disk) or set an env-var (`DATABASE_PATH=/var/data/sujets.db`) so the code points there.
2. **Code > copy**  Hard-coding `instance/sujets.db` inside the code caused the mysterious `no such table` error. One-line fix: read the path from `os.getenv("DATABASE_PATH", "instance/sujets.db")` so the same code works locally and on Render.
3. **Symlinks are stop-gaps**  Copying/ linking the DB into the container worked until the next restart. Refactor the code instead of relying on manual copies.
4. **Git remote hygiene**  A miss-typed remote URL (`fresh_weav`) and mismatched branch names (`master` vs `main`) blocked pushes. Use `git remote -v`, `git remote set-url`, and `git branch -M main` to verify.
5. **Scope your repo**  The original repository’s root included unrelated personal projects, making `git add .` painful. Starting a fresh repo inside the `Weave` folder kept history clean.
6. **Stashing vs new repo**  Windows file locks can break `git stash --include-untracked`. When that happens, renaming the parent `.git` and running `git init` in the project folder is faster.
7. **Render deploy cycle**  Push → Render builds → new pod picks up env-vars and persistent disk. No need to `scp` code files; let Git trigger the deploy.

These points are living knowledge—feel free to extend or refine as the project evolves.

---
*This document should be updated regularly as the project evolves.*
