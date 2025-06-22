# weave_webapp/app.py

from flask import Flask, render_template, request, jsonify, g, session
import os
from dotenv import load_dotenv
import pandas as pd

# --- Custom Modules ---
from gsheet_operations import log_sujet_to_sheet
import db_operations

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

    client, sheet = get_gsheet_client()
    if sheet:
        log_success, log_message = log_sujet_to_sheet(sheet, dict(sujet_data_for_log))
        if not log_success:
            return jsonify({'status': 'partial_success', 'message': f'DB updated but GSheet failed: {log_message}'}), 207

    return jsonify({'status': 'success', 'message': 'Sujet saved and logged successfully.'})

@app.route('/skip_sujet', methods=['POST'])
def skip_sujet():
    """Marks a sujet as 'skipped' in SQLite and logs to Google Sheets."""
    data = request.get_json()
    sujet_id = data.get('id')

    db_operations.update_sujet_status(sujet_id, 'skipped')
    sujet_data_for_log = db_operations.get_sujet_by_id(sujet_id)

    client, sheet = get_gsheet_client()
    if sheet:
        log_success, log_message = log_sujet_to_sheet(sheet, dict(sujet_data_for_log))
        if not log_success:
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

    client, sheet = get_gsheet_client()
    if sheet:
        log_success, log_message = log_sujet_to_sheet(sheet, sujet_data_for_log)
        if not log_success:
            return jsonify({'status': 'partial_success', 'message': f'GSheet log failed, DB record not deleted: {log_message}'}), 207

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

if __name__ == '__main__':
    app.run(debug=True)


from flask import Flask, render_template, request, jsonify, g, session
import os
from dotenv import load_dotenv
import pandas as pd 

# --- Custom Modules ---
from gsheet_operations import get_gsheet_client, log_sujet_to_sheet
import db_operations # For database interactions and CLI commands

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for session management

# --- Register CLI commands and Teardown from db_operations ---
db_operations.register_cli_commands(app)
db_operations.register_teardown(app)


# --- Validate essential Configuration (Runs on import) ---
if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    print("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
    print("Please check your .env file and ensure it points to your service account key.")
if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and not os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')):
    print(
        f"Error: Google Service Account file not found at {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}.")
    print("Please double-check the GOOGLE_APPLICATION_CREDENTIALS path in your .env file.")
if not os.getenv('GOOGLE_SHEET_ID'):
    print("Error: GOOGLE_SHEET_ID environment variable not set.")
    print("Please check your .env file.")


# --- No direct Database Helper Functions here anymore ---
# They are now in db_operations.py

# --- No SQL Query Builder Helper here anymore ---
# It is now in db_operations.py

# --- No Database Initialization Commands here anymore ---
# They are now in db_operations.py and registered via db_operations.register_cli_commands(app)





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
    # Toggle between ASC and DESC
    if session.get('sort_order') == 'ASC':
        session['sort_order'] = 'DESC'
    else:
        session['sort_order'] = 'ASC'
    
    session.modified = True # Explicitly mark session as modified
    
    print(f"--- DEBUG: Sort order toggled to {session['sort_order']} ---")
    return jsonify({'status': 'ok', 'new_sort_order': session['sort_order']})


@app.route('/get_sujet', methods=['GET'])
def get_sujet():
    """Returns the next sujet based on filters and increments its view count."""
    db = db_operations.get_db()

    # Extract filter parameters from request arguments
    # For now, we'll keep it simple and primarily use the session sort_order
    # and the request offset. Advanced filters will be added later.
    tags_str = request.args.get('tags', '')
    tags_filter = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    people_str = request.args.get('people', '')
    people_filter = [person.strip() for person in people_str.split(',') if person.strip()]
    sort_by_filter = request.args.get('sort_by', 'id') # Default to id
    # Use session sort_order as default, but allow request to override
    sort_order_filter = request.args.get('sort_order', session.get('sort_order', 'ASC'))
    if sort_order_filter.upper() not in ['ASC', 'DESC']:
        sort_order_filter = session.get('sort_order', 'ASC') # Fallback to session or default ASC
    
    offset = request.args.get('offset', 0, type=int)

    filters_dict = {
        'tags': tags_filter,
        'people': people_filter,
        'sort_by': sort_by_filter,
        'sort_order': sort_order_filter,
        'select_count': False
    }

    query, query_params = db_operations.build_sujet_query(filters_dict)

    # Append pagination for fetching a single sujet
    query += " LIMIT 1 OFFSET ?"
    query_params.append(offset)
    
    print(f"--- DEBUG (get_sujet): Executing query: {query} with params: {query_params} ---")
    sujet_row = db.execute(query, query_params).fetchone()

    if sujet_row is None:
        return jsonify({'status': 'no_more_sujets'})
    else:
        # Increment view_count for the fetched sujet
        sujet_id = sujet_row['id']
        db.execute('UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet_id,))
        db.commit()

        # Fetch the sujet again to get the updated view_count
        # This is slightly inefficient but ensures data consistency for the response.
        # Alternatively, we could add view_count + 1 to the sujet_row dict before returning.
        # For now, re-fetching is simpler and less prone to off-by-one errors if logic changes.
        updated_sujet_row = db_operations.get_sujet_by_id(sujet_id) # Use existing helper
        if updated_sujet_row is None:
            # Should not happen if we just fetched and updated it
            return jsonify({'status': 'error', 'message': 'Failed to retrieve sujet after view count update.'}), 500
        
        sujet_dict = dict(updated_sujet_row)
        return jsonify({'status': 'ok', 'sujet': sujet_dict})


@app.route('/get_sujets_count', methods=['GET'])
def get_sujets_count():
    """Returns the count of sujets matching the given filter criteria."""
    db = db_operations.get_db()

    tags_str = request.args.get('tags', '')
    tags_filter = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    people_str = request.args.get('people', '')
    people_filter = [person.strip() for person in people_str.split(',') if person.strip()]
    # sort_by and sort_order are not relevant for count, but build_sujet_query can handle them

    filters_dict = {
        'tags': tags_filter,
        'people': people_filter,
        'select_count': True
    }

    query, query_params = db_operations.build_sujet_query(filters_dict)
    
    print(f"--- DEBUG (get_sujets_count): Executing query: {query} with params: {query_params} ---")
    count_row = db.execute(query, query_params).fetchone()

    # For a COUNT(*) query, the result is in the first column (index 0).
    # Accessing by index is more robust than by name.
    if count_row is not None:
        return jsonify({'status': 'ok', 'count': count_row[0]})
    else:
        # This case is unexpected for a COUNT query but handled for safety.
        print(f"--- ERROR (get_sujets_count): Failed to retrieve count. Query returned None. Query: {query}, Params: {query_params} ---")
        return jsonify({'status': 'error', 'message': 'Failed to retrieve sujet count.'}), 500


# <-- New route for fetching by ID
@app.route('/get_sujet_by_id/<int:sujet_id>', methods=['GET'])
def get_sujet_by_id_route(sujet_id):
    """Route to return a specific sujet by its ID."""
    sujet_data = db_operations.get_sujet_by_id(sujet_id) # Call the helper
    if sujet_data is None:
        return jsonify({'status': 'error', 'message': f'Sujet with ID {sujet_id} not found.'}), 404
    else:
        sujet_dict = dict(sujet_data)
        print(f"Fetched sujet by ID via route: {sujet_id}.")
        return jsonify({'status': 'ok', 'sujet': sujet_dict})


@app.route('/get_random_sujet', methods=['GET'])
def get_random_sujet():
    """Returns a random sujet that needs enrichment and increments its view count."""
    db = db_operations.get_db()
    
    # Query for one random sujet that needs enrichment
    query = 'SELECT id, original_sujet, ai_suggestion, view_count, user_notes, user_tags, status, person FROM sujets ORDER BY RANDOM() LIMIT 1'
    
    print(f"--- DEBUG (get_random_sujet): Fetching random sujet ---") # DEBUG
    sujet_row = db.execute(query).fetchone()

    if sujet_row is None:
        return jsonify({'status': 'no_more_sujets'})
    else:
        sujet_id = sujet_row['id']
        
        # Increment view_count in the database
        db.execute('UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet_id,))
        db.commit()
        
        # Fetch the now-updated sujet data to return it with the new view_count
        updated_sujet_row = db.execute(
            'SELECT id, original_sujet, ai_suggestion, view_count, user_notes, user_tags, status, person FROM sujets WHERE id = ?', (sujet_id,)
        ).fetchone()
        sujet_dict = dict(updated_sujet_row)

        return jsonify({'status': 'ok', 'sujet': sujet_dict})


@app.route('/save_sujet', methods=['POST'])
def save_sujet():
    """Saves the user's enrichment to SQLite and logs to Google Sheets."""
    data = request.get_json()
    sujet_id = data.get('id')
    user_notes = data.get('user_notes', '')
    user_tags = data.get('user_tags', '')
    person = data.get('person', '') # Get person from request, default to empty string
    # new_status_from_request = data.get('status') # This will be 'enriched'

    if sujet_id is None:
        return jsonify({'status': 'error', 'message': 'Sujet ID is required.'}), 400

    db = db_operations.get_db()
    # Get current details for logging and for view_count base
    current_sujet_details = db_operations.get_sujet_by_id(sujet_id)
    if not current_sujet_details:
        return jsonify({'status': 'error', 'message': f'Sujet with ID {sujet_id} not found.'}), 404

    initial_view_count = current_sujet_details['view_count'] # VC before this save action
    # current_status_in_db = current_sujet_details['status'] # No longer strictly needed for update logic itself

    print(f"--- DEBUG (save_sujet): Sujet ID {sujet_id}, Current DB Status: {current_sujet_details['status']}, Initial DB View Count for this save: {initial_view_count} ---")

    # No longer conditionally updating based on 'needs_enrichment'. Always update.
    # The status being set here will always be 'enriched' because this is the save_sujet route.
    new_status_for_db = "enriched"

    print(f"--- DEBUG (save_sujet): About to UPDATE DB for Sujet ID {sujet_id} with New Status: {new_status_for_db}, Notes: '{user_notes}', Tags: '{user_tags}' ---Pre-VC for this save: {initial_view_count}---")
    db.execute(
        'UPDATE sujets SET user_notes = ?, user_tags = ?, status = ?, person = ?, view_count = view_count + 1 WHERE id = ?',
        (user_notes, user_tags, new_status_for_db, person, sujet_id)
    )
    db.commit()
    print(f"--- DEBUG (save_sujet): DB UPDATE and COMMIT successful for Sujet ID {sujet_id}. ---")

    # Fetch the fully updated sujet data from DB for logging
    updated_db_sujet = db_operations.get_sujet_by_id(sujet_id)
    if not updated_db_sujet:
        # This should not happen if the above commit was successful
        return jsonify({'status': 'error', 'message': f'Failed to re-fetch sujet {sujet_id} after update.'}), 500

    print(f"--- DEBUG (save_sujet): Sujet ID {sujet_id}, View count after DB update: {updated_db_sujet['view_count']} ---")

    # Log to Google Sheets
    # The status passed to log_sujet_to_sheet will be the new_status_for_db ('enriched')
    print(f"--- DEBUG (save_sujet): Logging to sheet with Sujet ID: {updated_db_sujet['id']}, OS: ..., AS: ..., Notes: '{updated_db_sujet['user_notes']}', Tags: '{updated_db_sujet['user_tags']}', Status: '{updated_db_sujet['status']}', VC: {updated_db_sujet['view_count']} ---")
    log_success = log_sujet_to_sheet(
        sujet_id=updated_db_sujet['id'],
        original_sujet=updated_db_sujet['original_sujet'],
        ai_suggestion=updated_db_sujet['ai_suggestion'],
        user_notes=updated_db_sujet['user_notes'],
        user_tags=updated_db_sujet['user_tags'],
        status=updated_db_sujet['status'], # This will be 'enriched'
        view_count=updated_db_sujet['view_count'],
        person=updated_db_sujet['person']
    )

    if not log_success:
        print(f"--- WARNING (save_sujet): Sujet {sujet_id} was saved in DB, but GSheet logging FAILED. ---")
        return jsonify({'status': 'partial_success', 'message': 'Sujet saved to database, but failed to log to Google Sheet.'}), 207 # Multi-Status

    return jsonify({'status': 'success', 'message': 'Sujet updated and logged to Google Sheets.'})

@app.route('/skip_sujet', methods=['POST'])
def skip_sujet():
    """Marks a sujet as 'skipped' in SQLite and logs to Google Sheets."""
    data = request.get_json()
    sujet_id = data.get('id')

    if sujet_id is None:
        return jsonify({'status': 'error', 'message': 'Sujet ID is required.'}), 400

    db = db_operations.get_db()
    current_sujet_details = db_operations.get_sujet_by_id(sujet_id)
    if not current_sujet_details:
        return jsonify({'status': 'error', 'message': f'Sujet with ID {sujet_id} not found.'}), 404

    initial_view_count = current_sujet_details['view_count'] # VC before this skip action
    # current_status_in_db = current_sujet_details['status'] # No longer strictly needed for update logic

    print(f"--- DEBUG (skip_sujet): Sujet ID {sujet_id}, Current DB Status: {current_sujet_details['status']}, Initial DB View Count for this skip: {initial_view_count} ---")

    # Always update status to 'skipped'.
    db_status_to_set = "skipped"

    print(f"--- DEBUG (skip_sujet): About to UPDATE DB for Sujet ID {sujet_id} with New Status: {db_status_to_set} ---Pre-VC for this skip: {initial_view_count}---")
    db.execute(
        'UPDATE sujets SET status = ?, view_count = view_count + 1 WHERE id = ?',
        (db_status_to_set, sujet_id)
    )
    db.commit()
    print(f"--- DEBUG (skip_sujet): DB UPDATE and COMMIT successful for Sujet ID {sujet_id}. ---")

    updated_db_sujet = db_operations.get_sujet_by_id(sujet_id)
    if not updated_db_sujet:
        return jsonify({'status': 'error', 'message': f'Failed to re-fetch sujet {sujet_id} after update.'}), 500

    print(f"--- DEBUG (skip_sujet): Sujet ID {sujet_id}, View count after DB update: {updated_db_sujet['view_count']} ---")

    # Log to Google Sheets
    # The status passed to log_sujet_to_sheet will be the db_status_to_set ('skipped')
    print(f"--- DEBUG (skip_sujet): Logging to sheet with Sujet ID: {updated_db_sujet['id']}, OS: ..., AS: ..., Notes: '{updated_db_sujet['user_notes']}', Tags: '{updated_db_sujet['user_tags']}', Status: '{updated_db_sujet['status']}', VC: {updated_db_sujet['view_count']} ---")
    log_success = log_sujet_to_sheet(
        sujet_id=updated_db_sujet['id'],
        original_sujet=updated_db_sujet['original_sujet'],
        ai_suggestion=updated_db_sujet['ai_suggestion'],
        user_notes=updated_db_sujet['user_notes'], # Existing notes
        user_tags=updated_db_sujet['user_tags'],   # Existing tags
        status=updated_db_sujet['status'],         # This will be 'skipped'
        view_count=updated_db_sujet['view_count'],
        person=updated_db_sujet['person']
    )

    if not log_success:
        print(f"--- WARNING (skip_sujet): Sujet {sujet_id} was skipped in DB, but GSheet logging FAILED. ---")
        return jsonify({'status': 'partial_success', 'message': 'Sujet skipped in database, but failed to log to Google Sheet.'}), 207 # Multi-Status

    return jsonify({'status': 'ok', 'message': 'Sujet skipped and logged.'})


# ---------- NEW ROUTE FOR DELETING A SUJET ----------
@app.route('/delete_sujet/<int:sujet_id>', methods=['DELETE'])
def delete_sujet(sujet_id):
    """Logs the sujet as 'deleted' in Google Sheets, then deletes it from SQLite."""
    db = db_operations.get_db()
    try:
        # Step 1: Fetch all sujet details before deleting it from the local DB
        sujet_to_delete = db_operations.get_sujet_by_id(sujet_id)
        if not sujet_to_delete:
            return jsonify({'status': 'error', 'message': 'Sujet not found'}), 404

        # Step 2: Log the 'deleted' status to Google Sheets
        print(f"--- DEBUG: Logging deletion for sujet ID: {sujet_id} to Google Sheets ---")
        log_success = log_sujet_to_sheet(
            sujet_id=sujet_to_delete['id'],
            original_sujet=sujet_to_delete['original_sujet'],
            ai_suggestion=sujet_to_delete['ai_suggestion'],
            user_notes=sujet_to_delete['user_notes'],
            user_tags=sujet_to_delete['user_tags'],
            status='deleted',  # Explicitly set status to 'deleted'
            view_count=sujet_to_delete['view_count'],
            person=sujet_to_delete['person']
        )

        # Step 3: Delete the sujet from the local SQLite database
        db_operations.delete_sujet_from_db(sujet_id)
        print(f"--- DEBUG: Deleted sujet with ID: {sujet_id} from local DB ---")

        if not log_success:
            print(f"--- WARNING (delete_sujet): Sujet {sujet_id} was deleted from DB, but GSheet logging FAILED. ---")
            return jsonify({'status': 'partial_success', 'message': 'Sujet deleted from database, but failed to log to Google Sheet.'}), 207 # Multi-Status

        return jsonify({'status': 'success', 'message': 'Sujet logged as deleted and removed from local DB.'})

    except Exception as e:
        print(f"--- ERROR (delete_sujet): Failed to delete sujet {sujet_id}. Error: {e} ---")
        # Ensure a JSON response is sent on any unexpected exception
        return jsonify({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}), 500

# --- Route to get all unique tags ---
@app.route('/get_all_tags', methods=['GET'])
def get_all_tags():
    db = db_operations.get_db()
    try:
        cursor = db.execute('SELECT user_tags FROM sujets')
        rows = cursor.fetchall()
        all_tags = set()
        for row in rows:
            if row['user_tags']:
                tags_in_row = [tag.strip() for tag in row['user_tags'].split(',') if tag.strip()]
                all_tags.update(tags_in_row)
        sorted_tags = sorted(list(all_tags))
        # print(f"--- DEBUG (get_all_tags): Returning tags: {sorted_tags} ---") # Optional debug
        return jsonify({'status': 'ok', 'tags': sorted_tags})
    except sqlite3.Error as e:
        print(f"Database error in /get_all_tags: {e}")
        return jsonify({'status': 'error', 'message': f'Database error: {e}'}), 500


# --- Route to get all unique people ---
@app.route('/get_all_people', methods=['GET'])
def get_all_people():
    db = db_operations.get_db()
    try:
        cursor = db.execute('SELECT DISTINCT person FROM sujets WHERE person IS NOT NULL AND person != ""')
        rows = cursor.fetchall()
        all_people = sorted([row['person'] for row in rows])
        # print(f"--- DEBUG (get_all_people): Returning people: {all_people} ---") # Optional debug
        return jsonify({'status': 'ok', 'people': all_people})
    except sqlite3.Error as e:
        print(f"Database error in /get_all_people: {e}")
        return jsonify({'status': 'error', 'message': f'Database error: {e}'}), 500


# --- To run this app ---
# 1. Navigate to the 'weave' directory in your terminal (with venv activated).
# 2. Ensure you have created an 'instance' folder.
# 3. Ensure you have initial_sujets.csv, app.py, index.html, style.css, script.js, .env, .gitignore in place.
# 4. Ensure your .env file has GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_SHEET_ID pointing correctly.
# 5. Ensure service account has Editor access on the Google Sheet.
# 6. **Prepare initial_sujets.csv:** Run weave_limited.py (after configuring batch size and index file) to generate/update initial_sujets.csv with the current batch.
# 7. **Initialize the database:** If this is the first run or you deleted instance/sujets.db: flask init-db
# 8. Set the FLASK_APP environment variable: $env:FLASK_APP = "app.py" (Windows) or export FLASK_APP=app.py (mac/linux)
# 9. Run the Flask development server: flask run
