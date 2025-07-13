# weave_webapp/app.py

from flask import Flask, render_template, request, jsonify, g, session
import os
from dotenv import load_dotenv
import pandas as pd
import json
from sqlite3 import Row

# --- Custom Modules ---
import db_operations
# Google Sheets logging removed

# Load environment variables from the .env file
load_dotenv()

# --- Custom JSON encoder to handle SQLite Row objects ---
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Row):
            return {k: ('' if v is None else v) for k, v in dict(obj).items()}
        return super().default(obj)

# --- App Initialization ---
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_default_secret_key_for_development')
app.json_encoder = CustomJSONEncoder  # Use custom JSON encoder

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
        session['sort_order'] = 'DESC'  # Default to DESC so newest sujets appear first
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
    sort_order = session.get('sort_order', 'DESC')

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
    # Get the current sort order from session
    sort_order = session.get('sort_order', 'DESC')
    
    # Get filter parameters
    tags_str = request.args.get('tags', '')
    people_str = request.args.get('people', '')
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
    people = [person.strip() for person in people_str.split(',') if person.strip()] if people_str else []
    
    sujet = db_operations.get_first_or_last_sujet_from_db(first=True, sort_order=sort_order, tags=tags, people=people)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'error', 'message': 'Sujet not found'}), 404

@app.route('/last')
def last():
    """Fetches the very last sujet by its ID."""
    # Get the current sort order from session
    sort_order = session.get('sort_order', 'DESC')
    
    # Get filter parameters
    tags_str = request.args.get('tags', '')
    people_str = request.args.get('people', '')
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
    people = [person.strip() for person in people_str.split(',') if person.strip()] if people_str else []
    
    sujet = db_operations.get_first_or_last_sujet_from_db(first=False, sort_order=sort_order, tags=tags, people=people)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'error', 'message': 'Sujet not found'}), 404

@app.route('/save_sujet', methods=['POST'])
def save_sujet():
    """Marks a sujet as 'enriched' in SQLite with user notes, tags, and person."""
    data = request.get_json()
    sujet_id = data.get('id')
    user_notes = data.get('user_notes', '')
    user_tags = data.get('user_tags', '')
    person = data.get('person', '')

    db_operations.update_sujet_status(sujet_id, 'enriched', user_notes, user_tags, person)
    
    # Google Sheets logging removed to fix 500 errors
    return jsonify({'status': 'success', 'message': 'Sujet saved successfully.'})

@app.route('/skip_sujet', methods=['POST'])
def skip_sujet():
    """Marks a sujet as 'skipped' in SQLite."""
    data = request.get_json()
    sujet_id = data.get('id')

    db_operations.update_sujet_status(sujet_id, 'skipped')
    
    # Google Sheets logging removed to fix 500 errors
    return jsonify({'status': 'success', 'message': 'Sujet skipped successfully.'})

@app.route('/delete_sujet/<int:sujet_id>', methods=['DELETE'])
def delete_sujet(sujet_id):
    """Deletes a sujet from SQLite."""
    sujet_to_log = db_operations.get_sujet_by_id(sujet_id)
    if not sujet_to_log:
        return jsonify({'status': 'error', 'message': 'Sujet not found'}), 404

    # Google Sheets logging removed to fix 500 errors
    
    # Delete from the database
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
    sort_order = session.get('sort_order', 'DESC')

    tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
    people = [p.strip() for p in people_str.split(',') if p.strip()] if people_str else []

    sujet = db_operations.get_adjacent_sujet(sujet_id, tags, people, sort_order, direction)
    if sujet:
        return jsonify({'status': 'ok', 'sujet': dict(sujet)})
    else:
        return jsonify({'status': 'no_more_sujets'})

@app.route('/update_title/<int:sujet_id>', methods=['POST'])
def update_title(sujet_id):
    """Updates the title of a sujet."""
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({'status': 'error', 'message': 'Missing title data'}), 400
    
    new_title = data['title'].strip()
    if not new_title:
        return jsonify({'status': 'error', 'message': 'Title cannot be empty'}), 400
    
    success = db_operations.update_sujet_title(sujet_id, new_title)
    
    if success:
        # Log to Google Sheets if enabled
        try:
            sujet = db_operations.get_sujet_by_id(sujet_id)
            if sujet:
                # Removed log_sujet_to_sheet call
                pass
        except Exception as e:
            print(f"Error logging title change to Google Sheets: {e}")
            # Continue even if logging fails
        
        return jsonify({
            'status': 'success',
            'message': 'Title updated successfully',
            'sujet_id': sujet_id,
            'new_title': new_title
        })
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update title'}), 500

@app.route('/add_sujet', methods=['POST'])
def add_sujet():
    """Creates a new sujet with the provided title."""
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({'status': 'error', 'message': 'Missing title data'}), 400
    
    title = data['title'].strip()
    if not title:
        return jsonify({'status': 'error', 'message': 'Title cannot be empty'}), 400
    
    # Add the new sujet to the database with empty AI suggestion and notes
    new_sujet = db_operations.add_new_sujet(title, "", "")
    
    if new_sujet:
        # Log to Google Sheets if enabled
        try:
            # Removed log_sujet_to_sheet call
            pass
        except Exception as e:
            print(f"Error logging new sujet to Google Sheets: {e}")
            # Continue even if logging fails
        
        # Convert SQLite Row to dict for JSON serialization
        sujet_dict = dict(new_sujet)
        
        return jsonify({
            'status': 'success',
            'message': 'Sujet created successfully',
            'sujet': sujet_dict
        })
    else:
        return jsonify({'status': 'error', 'message': 'Failed to create sujet'}), 500

if __name__ == '__main__':
    app.run(debug=True)
