# weave_webapp/app.py

from flask import Flask, render_template, request, jsonify, g
import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv
import sys

# --- Google Sheets Imports ---
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError as GspreadAPIError


# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)

# Define the path for the SQLite database
DATABASE = os.path.join(app.instance_path, 'sujets.db')
INITIAL_CSV = 'initial_sujets.csv'


# --- Google Sheets Configuration ---
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

ENRICHED_SHEET_NAME = "Enriched Sujets Log"


# --- Validate essential Configuration (Runs on import) ---
if not SERVICE_ACCOUNT_FILE:
    print("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
    print("Please check your .env file and ensure it points to your service account key.")
if SERVICE_ACCOUNT_FILE and not os.path.exists(SERVICE_ACCOUNT_FILE):
    print(
        f"Error: Google Service Account file not found at {SERVICE_ACCOUNT_FILE}.")
    print("Please double-check the GOOGLE_APPLICATION_CREDENTIALS path in your .env file.")
if not GOOGLE_SHEET_ID:
    print("Error: GOOGLE_SHEET_ID environment variable not set.")
    print("Please check your .env file.")


# --- Database Helper Functions ---

def get_db():
    """Connects to the specific database or returns the existing connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    """Closes the database connection at the end of the application context."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# --- Database Initialization Command ---
@app.cli.command('init-db')
def init_db():
    """Initialize the database from the initial CSV file."""
    print("Initializing database...")
    os.makedirs(app.instance_path, exist_ok=True)

    try:
        if not os.path.exists(INITIAL_CSV):
            print(
                f"Error: Initial CSV file not found at {INITIAL_CSV}. Cannot initialize database.")
            print("Please ensure initial_sujets.csv is in the correct directory.")
            sys.exit(1)

        df = pd.read_csv(INITIAL_CSV)

        df['user_notes'] = ''
        df['user_tags'] = ''
        df['status'] = 'needs_enrichment'
        df['view_count'] = 0  # <-- Ensure this column is added

        df = df.rename(columns={
            'Original Sujet': 'original_sujet',
            'Suggested Enrichment': 'ai_suggestion'
        })

        conn = get_db()
        # Use if_exists='replace' to start fresh
        df.to_sql('sujets', conn, if_exists='replace',
                  index=True, index_label='id')

        conn.commit()
        print("Database initialized successfully from CSV.")
    except Exception as e:
        print(
            f"An unexpected error occurred during database initialization: {e}")
        sys.exit(1)


# --- Google Sheets Client Helper Function ---
def get_gsheet_client():
    """Gets or creates a gspread client authenticated with the service account."""
    if 'gsheet_client' not in g:
        try:
            if not SERVICE_ACCOUNT_FILE or not os.path.exists(SERVICE_ACCOUNT_FILE):
                print(
                    f"Error: Google Service Account file path invalid or not found: {SERVICE_ACCOUNT_FILE}.")
                g.gsheet_client = None
                return None

            credentials = Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
            g.gsheet_client = gspread.authorize(credentials)
        except Exception as e:
            print(
                f"An unexpected error occurred during gspread client setup: {e}")
            g.gsheet_client = None
            return None

    return g.gsheet_client


# --- Google Sheets Logging Helper ---
# <-- Added view_count parameter
def log_sujet_to_sheet(sujet_id, original_sujet, ai_suggestion, user_notes, user_tags, status, view_count):
    """Appends a row to the Google Sheet log."""
    gsheet_client = get_gsheet_client()
    if gsheet_client is None:
        print("Google Sheets client not available. Skipping log to sheet.")
        return False

    try:
        spreadsheet = gsheet_client.open_by_key(GOOGLE_SHEET_ID)
        try:
            worksheet = spreadsheet.worksheet(ENRICHED_SHEET_NAME)
        except gspread.WorksheetNotFound:
            print(f"Worksheet '{ENRICHED_SHEET_NAME}' not found, creating...")
            try:
                worksheet = spreadsheet.add_worksheet(
                    title=ENRICHED_SHEET_NAME, rows="100", cols="20")
                # <-- Updated headers to include View Count
                headers = ["ID", "Original Sujet", "AI Suggestion",
                           "User Notes", "User Tags", "Status", "View Count", "Timestamp"]
                worksheet.append_row(headers)
                print("Created worksheet and added headers.")
            except GspreadAPIError as e:
                print(f"Error creating worksheet '{ENRICHED_SHEET_NAME}': {e}")
                print(
                    "Please ensure the service account has Editor access to the Google Sheet.")
                return False

        row_data = [
            sujet_id,
            original_sujet,
            ai_suggestion,
            user_notes,
            user_tags,
            status,
            view_count,  # <-- Include view count in row data
            pd.Timestamp.now().isoformat()
        ]

        worksheet.append_row(row_data)
        print(
            f"Logged sujet {sujet_id} status '{status}' (View Count: {view_count}) to Google Sheet '{ENRICHED_SHEET_NAME}'.")
        return True

    except GspreadAPIError as e:
        print(f"Google Sheets API Error logging sujet {sujet_id}: {e}")
        error_message = f"Google Sheets Error: {e.response.json().get('error', {}).get('message', str(e))}"
        print(f"Google Sheets log failed: {error_message}.")
        return False

    except Exception as e:
        print(
            f"An unexpected error occurred during Google Sheets log for sujet {sujet_id}: {e}")
        return False


# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main page."""
    return render_template('index.html')


@app.route('/get_sujet', methods=['GET'])
def get_sujet():
    """Returns the next sujet that needs enrichment and increments its view count."""
    db = get_db()
    sujet_row = db.execute(  # <-- Renamed variable for clarity
        'SELECT id, original_sujet, ai_suggestion, view_count FROM sujets WHERE status = "needs_enrichment" ORDER BY id LIMIT 1'  # <-- Fetch view_count
    ).fetchone()

    if sujet_row is None:
        return jsonify({'status': 'no_more_sujets'})
    else:
        sujet_dict = dict(sujet_row)  # <-- Use the fetched row

        # Increment view count in DB
        current_view_count = sujet_dict['view_count']
        new_view_count = current_view_count + 1
        try:
            db.execute(
                'UPDATE sujets SET view_count = ? WHERE id = ?',
                (new_view_count, sujet_dict['id'])
            )
            db.commit()  # <-- Commit the view count increment immediately
            # Update the dict to return the *new* count to frontend
            sujet_dict['view_count'] = new_view_count
            print(
                f"Incremented view count for sujet {sujet_dict['id']} to {sujet_dict['view_count']}.")
        except Exception as e:
            db.rollback()
            print(
                f"Error incrementing view count for sujet {sujet_dict['id']}: {e}")
            # Continue returning the sujet even if increment fails, frontend will show old count + warning

        return jsonify({'status': 'ok', 'sujet': sujet_dict})


@app.route('/save_sujet', methods=['POST'])
def save_sujet():
    """Saves the user's enrichment to SQLite and logs to Google Sheets if status changes."""
    data = request.get_json()

    sujet_id = data.get('id')
    user_notes = data.get('user_notes', '')
    user_tags = data.get('user_tags', '')

    if sujet_id is None:
        return jsonify({'status': 'error', 'message': 'Missing sujet ID'}), 400

    db = get_db()

    # --- Check current status and get data from SQLite ---
    sujet_data = db.execute(
        # <-- Fetch view_count
        'SELECT original_sujet, ai_suggestion, status, view_count FROM sujets WHERE id = ?', (
            sujet_id,)
    ).fetchone()

    if sujet_data is None:
        return jsonify({'status': 'error', 'message': f'Sujet with ID {sujet_id} not found in DB.'}), 404

    original_sujet = sujet_data['original_sujet']
    ai_suggestion = sujet_data['ai_suggestion']
    current_status = sujet_data['status']
    view_count = sujet_data['view_count']  # <-- Get view count

    # --- Only proceed with update/log if status is currently 'needs_enrichment' ---
    if current_status != 'needs_enrichment':
        print(
            f"Sujet {sujet_id} status is already '{current_status}'. Skipping save/log.")
        # Return success message, potentially indicating it was already done
        return jsonify({'status': 'success', 'message': f'Sujet was already {current_status}.'})

    # --- If status IS 'needs_enrichment', update DB and then log to sheet ---

    db.execute("BEGIN TRANSACTION")  # Start transaction for the status update

    try:
        # 1. Update status and data in SQLite
        db.execute(
            'UPDATE sujets SET user_notes = ?, user_tags = ?, status = "enriched" WHERE id = ?',
            (user_notes, user_tags, sujet_id)
        )
        # 2. Commit the SQLite transaction immediately after update
        db.commit()
        print(f"Committed sujet {sujet_id} status to 'enriched' in SQLite.")

        # 3. Log the status change to the Google Sheet *after* local commit
        # <-- Pass view_count to the log function
        log_to_gsheets_successful = log_sujet_to_sheet(
            sujet_id, original_sujet, ai_suggestion, user_notes, user_tags, "enriched", view_count
        )

        # Return success status based on Sheets log
        if log_to_gsheets_successful:
            return jsonify({'status': 'success', 'message': 'Sujet saved and logged to Google Sheets.'})
        else:
            # Even if Sheets failed, the local DB is updated, so it's still a local success
            return jsonify({'status': 'success', 'message': 'Sujet saved locally (Google Sheets log failed).'}), 200

    except Exception as e:  # Catch errors during the DB update/commit
        db.rollback()  # Ensure rollback if commit failed (less likely after execute but possible)
        print(
            f"An unexpected error occurred saving sujet {sujet_id} to DB: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/skip_sujet', methods=['POST'])
def skip_sujet():
    """Marks a sujet as skipped in SQLite and logs to Google Sheets if status changes."""
    data = request.get_json()
    sujet_id = data.get('id')
    if sujet_id is None:
        return jsonify({'status': 'error', 'message': 'Missing sujet ID'}), 400

    db = get_db()

    # --- Check current status and get data from SQLite ---
    sujet_data = db.execute(
        # <-- Fetch view_count
        'SELECT original_sujet, ai_suggestion, status, view_count FROM sujets WHERE id = ?', (
            sujet_id,)
    ).fetchone()

    if sujet_data is None:
        return jsonify({'status': 'error', 'message': f'Sujet with ID {sujet_id} not found in DB.'}), 404

    original_sujet = sujet_data['original_sujet']
    ai_suggestion = sujet_data['ai_suggestion']
    current_status = sujet_data['status']
    view_count = sujet_data['view_count']  # <-- Get view count

    # --- Only proceed with update/log if status is currently 'needs_enrichment' ---
    if current_status != 'needs_enrichment':
        print(
            f"Sujet {sujet_id} status is already '{current_status}'. Skipping log.")
        return jsonify({'status': 'success', 'message': f'Sujet was already {current_status}.'})

    # --- If status IS 'needs_enrichment', update DB and then log to sheet ---

    db.execute("BEGIN TRANSACTION")  # Start transaction

    try:
        # 1. Update status in SQLite
        db.execute(
            'UPDATE sujets SET status = "skipped" WHERE id = ?',
            (sujet_id,)
        )
        # 2. Commit the SQLite transaction immediately after update
        db.commit()
        print(f"Committed sujet {sujet_id} status to 'skipped' in SQLite.")

        # 3. Log the status change to the Google Sheet *after* local commit
        # <-- Pass view_count to the log function
        log_to_gsheets_successful = log_sujet_to_sheet(
            # No user notes/tags for skipped log
            sujet_id, original_sujet, ai_suggestion, "", "", "skipped", view_count
        )

        # Return success status based on Sheets log
        if log_to_gsheets_successful:
            return jsonify({'status': 'success', 'message': 'Sujet skipped and logged to Google Sheets.'})
        else:
            return jsonify({'status': 'success', 'message': 'Sujet skipped locally (Google Sheets log failed).'}), 200

    except Exception as e:  # Catch errors before the commit
        db.rollback()
        print(
            f"An unexpected error occurred skipping sujet {sujet_id} to DB: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# --- To run this app ---
# 1. Navigate to the 'weave' directory in your terminal (with venv activated).
# 2. Ensure you have created an 'instance' folder.
# 3. Ensure you have initial_sujets.csv, app.py, index.html, style.css, script.js, .env, .gitignore in place.
# 4. Ensure your .env file has GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_SHEET_ID pointing correctly.
# 5. Ensure service account has Editor access on the Google Sheet.
# 6. **Initialize the database:** If this is the first run or you deleted instance/sujets.db: flask init-db
# 7. Set the FLASK_APP environment variable: $env:FLASK_APP = "app.py" (Windows) or export FLASK_APP=app.py (mac/linux)
# 8. Run the Flask development server: flask run
