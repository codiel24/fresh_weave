# weave_webapp/app.py

from flask import Flask, render_template, request, jsonify, g, session
import os
from dotenv import load_dotenv
import pandas as pd

# --- Custom Modules ---
import db_operations
from gsheet_operations import log_sujet_to_sheet

# Load environment variables from the .env file
load_dotenv()

# --- App Initialization ---
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_default_secret_key_for_development')

# Register database functions and CLI commands from the db_operations module
db_operations.register_cli_commands(app)
db_operations.register_teardown(app)

# --- Validate essential Configuration (Runs on import) ---
if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    print("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and not os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')):
    print(f"Error: Google Service Account file not found at {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}.")
if not os.getenv('GOOGLE_SHEET_ID'):
    print("Error: GOOGLE_SHEET_ID environment variable not set.")

# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main page and initializes sort order."""
    if 'sort_order' not in session:
        session['sort_order'] = 'ASC'  # Default sort order
    return render_template('index.html')

@app.route('/toggle_sort', methods=['POST'])
def toggle_sort():
    """Toggles the sort order in the session."""
    if 'sort_order' in session and session['sort_order'] == 'DESC':
        session['sort_order'] = 'ASC'
    else:
        session['sort_order'] = 'DESC'
    return jsonify({'status': 'ok', 'sort_order': session['sort_order']})

@app.route('/get_sujet')
def get_sujet():
    """Returns the next sujet based on filters and increments its view count."""
    offset = request.args.get('offset', 0, type=int)
    tags_str = request.args.get('tags', '')
    people_str = request.args.get('people', '')
    sort_order = session.get('sort_order', 'ASC')

    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
    people = [person.strip() for person in people_str.split(',') if person.strip()] if people_str else []

    sujet = db_operations.get_next_sujet_by_filter(offset, tags, people, sort_order)

    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'no_more_sujets'})

@app.route('/get_sujets_count')
def get_sujets_count():
    """Returns the count of sujets matching the given filter criteria."""
    tags_str = request.args.get('tags', '')
    people_str = request.args.get('people', '')
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
    people = [person.strip() for person in people_str.split(',') if person.strip()] if people_str else []

    count = db_operations.get_sujets_count_by_filter(tags, people)
    return jsonify({'status': 'ok', 'count': count})

@app.route('/get_sujet_by_id/<int:sujet_id>')
def get_sujet_by_id_route(sujet_id):
    """Route to return a specific sujet by its ID."""
    sujet = db_operations.get_sujet_by_id(sujet_id)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'error', 'message': 'Sujet not found'}), 404

@app.route('/get_random_sujet')
def get_random_sujet():
    """Returns a random sujet that needs enrichment and increments its view count."""
    sujet = db_operations.get_random_sujet_from_db()
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'no_more_sujets'})

@app.route('/first')
def first():
    """Fetches the very first sujet by its ID."""
    sujet = db_operations.get_first_or_last_sujet_from_db(first=True)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'error', 'message': 'Sujet not found'}), 404

@app.route('/last')
def last():
    """Fetches the very last sujet by its ID."""
    sujet = db_operations.get_first_or_last_sujet_from_db(first=False)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'error', 'message': 'Sujet not found'}), 404

@app.route('/save_sujet', methods=['POST'])
def save_sujet():
    """Saves the user's enrichment to SQLite and logs to Google Sheets."""
    data = request.get_json()
    sujet_id = data.get('id')
    user_notes = data.get('user_notes')
    user_tags = data.get('user_tags')
    person = data.get('person')

    db_operations.update_sujet_status(sujet_id, 'enriched', user_notes, user_tags, person)
    sujet_data_for_log = db_operations.get_sujet_by_id(sujet_id)

    if sujet_data_for_log:
        log_success, log_message = log_sujet_to_sheet(**dict(sujet_data_for_log))
        if not log_success:
            # Log the error but still return a success to the frontend, as the primary action (DB save) worked.
            print(f"--- WARNING: GSheet log failed for sujet {sujet_id}: {log_message} ---")
            # We can still consider the main operation a success
            return jsonify({'status': 'partial_success', 'message': f'DB updated but GSheet failed: {log_message}'}), 207

    return jsonify({'status': 'success', 'message': 'Sujet saved and logged successfully.'})

@app.route('/skip_sujet', methods=['POST'])
def skip_sujet():
    """Marks a sujet as 'skipped' in SQLite and logs to Google Sheets."""
    data = request.get_json()
    sujet_id = data.get('id')

    db_operations.update_sujet_status(sujet_id, 'skipped')
    sujet_data_for_log = db_operations.get_sujet_by_id(sujet_id)

    if sujet_data_for_log:
        log_success, log_message = log_sujet_to_sheet(**dict(sujet_data_for_log))
        if not log_success:
            print(f"--- WARNING: GSheet log failed for sujet {sujet_id}: {log_message} ---")
            return jsonify({'status': 'partial_success', 'message': f'DB updated but GSheet failed: {log_message}'}), 207

    return jsonify({'status': 'ok', 'message': 'Sujet skipped and logged successfully.'})

@app.route('/delete_sujet/<int:sujet_id>', methods=['DELETE'])
def delete_sujet(sujet_id):
    """Logs the sujet as 'deleted' in Google Sheets, then deletes it from SQLite."""
    sujet_to_log = db_operations.get_sujet_by_id(sujet_id)
    if not sujet_to_log:
        return jsonify({'status': 'error', 'message': 'Sujet not found'}), 404

    sujet_data_for_log = dict(sujet_to_log)
    sujet_data_for_log['status'] = 'deleted'

    # Log the deletion attempt to Google Sheets first
    log_success, log_message = log_sujet_to_sheet(**sujet_data_for_log)
    if not log_success:
        # If logging fails, we prevent deletion to avoid data inconsistency.
        print(f"--- WARNING: GSheet log failed for DELETION of sujet {sujet_id}: {log_message} ---")
        return jsonify({'status': 'error', 'message': f'GSheet log failed, DB record not deleted: {log_message}'}), 500

    # If logging is successful, then delete from the database
    db_operations.delete_sujet_from_db(sujet_id)
    return jsonify({'status': 'success', 'message': 'Sujet deleted successfully.'})

@app.route('/get_all_tags')
def get_all_tags():
    tags = db_operations.get_all_unique_tags()
    return jsonify(tags)

@app.route('/get_all_people')
def get_all_people():
    people = db_operations.get_all_unique_people()
    return jsonify(people)

@app.route('/get_first_sujet')
def get_first_sujet():
    """Returns the first sujet (by ID) and increments its view count."""
    sujet = db_operations.get_first_or_last_sujet_from_db(first=True)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'no_more_sujets'})

@app.route('/get_last_sujet')
def get_last_sujet():
    """Returns the last sujet (by ID) and increments its view count."""
    sujet = db_operations.get_first_or_last_sujet_from_db(first=False)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'no_more_sujets'})

@app.route('/adjacent_sujet')
def adjacent_sujet():
    """Returns the sujet immediately before or after the given ID respecting current sort order & filters.
    Query params:
        id:      current sujet ID (int)
        direction: 'next' or 'prev'
        tags:    optional comma-separated list
        people:  optional comma-separated list
    """
    sujet_id = request.args.get('id', type=int)
    if sujet_id is None:
        return jsonify({'status': 'error', 'message': 'Missing id param'}), 400

    direction = request.args.get('direction', 'next').lower()
    if direction not in ['next', 'prev']:
        return jsonify({'status': 'error', 'message': 'direction must be next or prev'}), 400

    tags_str = request.args.get('tags', '')
    people_str = request.args.get('people', '')
    sort_order = session.get('sort_order', 'ASC')

    tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
    people = [p.strip() for p in people_str.split(',') if p.strip()] if people_str else []

    sujet = db_operations.get_adjacent_sujet(sujet_id, tags, people, sort_order, direction)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'no_more_sujets'})

if __name__ == '__main__':
    app.run(debug=True)
