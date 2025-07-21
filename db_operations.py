# db_operations.py
import sqlite3
import os
import pandas as pd
import click
import sys
from flask import g
from datetime import datetime

# --- Constants ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# Allow deployment platforms to override DB location via env var (e.g., /var/data/sujets.db on Render)
DATABASE_PATH = os.getenv("DATABASE_PATH") or os.path.join(
    APP_ROOT, 'instance', 'sujets.db')
INITIAL_CSV_PATH = os.path.join(APP_ROOT, 'initial_sujets.csv')

# --- Database Helper Functions ---


def get_db():
    """Connects to the specific database or returns the existing connection."""
    print(f"[DEBUG] Connecting to database at: {DATABASE_PATH}")
    if 'db' not in g:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        g.db = sqlite3.connect(
            DATABASE_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_connection(exception):
    """Closes the database connection at the end of the application context."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_sujet_by_id(sujet_id):
    """Fetches a single sujet by its ID from the database."""
    db = get_db()
    sujet_data = db.execute(
        'SELECT id, original_sujet, ai_suggestion, user_notes, user_tags, status, view_count, person, date_created FROM sujets WHERE id = ?',
        (sujet_id,)
    ).fetchone()
    return sujet_data


def build_sujet_query(filters=None):
    """Dynamically builds an SQL query to fetch sujets based on filter criteria."""
    if filters is None:
        filters = {}

    base_query = "SELECT {columns} FROM sujets"
    query_params = []
    where_clauses = []

    columns_to_select = "COUNT(*) as count" if filters.get(
        'select_count') else "id, original_sujet, ai_suggestion, view_count, user_notes, user_tags, status, person, date_created"
    base_query = base_query.format(columns=columns_to_select)

    tags = filters.get('tags', [])
    if tags:
        tag_clauses = []
        for tag in tags:
            if tag and tag.strip():
                tag_clauses.append("user_tags LIKE ?")
                query_params.append(f"%{tag.strip()}%")
        if tag_clauses:
            where_clauses.append(f"({ ' OR '.join(tag_clauses) })")

    people = filters.get('people', [])
    if people:
        people_clauses = []
        for person in people:
            if person and person.strip():
                people_clauses.append("person LIKE ?")
                query_params.append(f"%{person.strip()}%")
        if people_clauses:
            where_clauses.append(f"({ ' OR '.join(people_clauses) })")

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    if not filters.get('select_count'):
        sort_by = filters.get('sort_by', 'id')

        if sort_by == 'random':
            base_query += " ORDER BY RANDOM()"
        elif sort_by == 'id':
            # Simple chronological ordering by creation date, then ID
            base_query += " ORDER BY date_created ASC, id ASC"

    return base_query, query_params

# --- Data Access Functions for App ---


def get_next_sujet_by_filter(offset, tags, people):
    """Fetches the next sujet based on filters and increments its view count."""
    db = get_db()
    filters = {
        'tags': tags,
        'people': people,
        'sort_by': 'id'
    }
    query, params = build_sujet_query(filters)

    query += " LIMIT 1 OFFSET ?"
    params.append(offset)

    sujet = db.execute(query, params).fetchone()

    if sujet:
        db.execute(
            'UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet['id'],))
        db.commit()
        # Re-fetch to get updated view count
        return get_sujet_by_id(sujet['id'])

    return None


def get_sujets_count_by_filter(tags, people):
    """Returns the count of sujets matching the given filter criteria."""
    db = get_db()
    filters = {
        'tags': tags,
        'people': people,
        'select_count': True
    }
    query, params = build_sujet_query(filters)

    count_result = db.execute(query, params).fetchone()
    return count_result['count'] if count_result else 0


def get_random_sujet_from_db():
    """Fetches a random sujet and increments its view count."""
    db = get_db()
    # Query for any random sujet, not just those needing enrichment
    query = "SELECT id, original_sujet, ai_suggestion, view_count, user_notes, user_tags, status, person, date_created FROM sujets ORDER BY RANDOM() LIMIT 1"
    sujet = db.execute(query).fetchone()

    if sujet:
        db.execute(
            'UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet['id'],))
        db.commit()
        # Re-fetch to get updated view count
        return get_sujet_by_id(sujet['id'])

    return None


def get_first_or_last_sujet_from_db(first=True, tags=None, people=None):
    """Fetches the first or last sujet from the database.

    Args:
        first: True for chronologically first (lowest ID), False for last (highest ID)
        tags: Tag filters
        people: People filters
    """
    db = get_db()

    # Build query with filters
    filters = {'tags': tags or [], 'people': people or []}
    base_query, params = build_sujet_query(filters)

    # Remove existing ORDER BY clause if present
    if 'ORDER BY' in base_query:
        base_query = base_query.split('ORDER BY')[0].strip()

    # Determine ORDER BY direction based on chronological position
    if first:
        # First = chronologically first = lowest ID
        order = "ASC"
    else:
        # Last = chronologically last = highest ID
        order = "DESC"

    # Add ORDER BY clause
    base_query += f" ORDER BY id {order} LIMIT 1"

    print(
        f"[FIRST/LAST DEBUG] Getting {'first' if first else 'last'} sujet, query: {base_query}")

    # Execute query and update view count
    sujet = db.execute(base_query, params).fetchone()

    if sujet:
        db.execute(
            'UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet['id'],))
        db.commit()
        # Re-fetch to get the updated view count
        return get_sujet_by_id(sujet['id'])

    return None


def update_sujet_status(sujet_id, status):
    """Updates the status of a sujet (e.g., 'skipped')."""
    db = get_db()
    db.execute(
        'UPDATE sujets SET status = ? WHERE id = ?',
        (status, sujet_id)
    )
    db.commit()


def update_sujet_details(sujet_id, user_notes, user_tags, person):
    """Updates the user-provided details of a sujet without changing its status."""
    db = get_db()
    db.execute(
        'UPDATE sujets SET user_notes = ?, user_tags = ?, person = ? WHERE id = ?',
        (user_notes, user_tags, person, sujet_id)
    )
    db.commit()


def delete_sujet_from_db(sujet_id):
    """Deletes a sujet from the database by its ID."""
    db = get_db()
    db.execute('DELETE FROM sujets WHERE id = ?', (sujet_id,))
    db.commit()


def get_all_unique_tags():
    """Fetches all unique, non-empty tags from the user_tags column."""
    db = get_db()
    cursor = db.execute("SELECT user_tags FROM sujets WHERE user_tags != ''")
    all_tags = set()
    for row in cursor.fetchall():
        tags = [tag.strip()
                for tag in row['user_tags'].split(',') if tag.strip()]
        all_tags.update(tags)
    return sorted(list(all_tags))


def get_all_unique_people():
    """Fetches all unique, non-empty person values."""
    db = get_db()
    cursor = db.execute(
        "SELECT DISTINCT person FROM sujets WHERE person != '' AND person IS NOT NULL")
    people = [row['person'] for row in cursor.fetchall()]
    return sorted(people)


def get_adjacent_sujet(sujet_id, tags, people, direction):
    """
    Fetches the sujet immediately before or after the given ID in chronological order.

    Args:
        sujet_id: The current sujet ID
        tags: List of tag filters
        people: List of people filters  
        direction: 'next' or 'prev'

    Returns:
        The adjacent sujet or None if not found
    """
    print(
        f"[ADJACENT DEBUG] Called with sujet_id={sujet_id}, direction={direction}, tags={tags}, people={people}")

    db = get_db()

    # Get the current sujet's ID for comparison (ID is more reliable than dates)
    current_sujet = get_sujet_by_id(sujet_id)
    if not current_sujet:
        print(f"[ADJACENT DEBUG] Current sujet {sujet_id} not found!")
        return None

    # Build base query with filters
    filters = {
        'tags': tags,
        'people': people
    }
    base_query, params = build_sujet_query(filters)
    print(f"[ADJACENT DEBUG] Base query before modification: {base_query}")
    print(f"[ADJACENT DEBUG] Base params: {params}")

    # Remove existing ORDER BY clause if present
    if 'ORDER BY' in base_query:
        base_query = base_query.split('ORDER BY')[0].strip()

    # Simple chronological navigation by ID
    # 'next' = higher ID (forward in time)
    # 'prev' = lower ID (backward in time)
    if direction == 'next':
        id_compare = "id > ?"
        order_by = "id ASC"
    else:  # prev
        id_compare = "id < ?"
        order_by = "id DESC"

    # Add WHERE clause for adjacent comparison
    if 'WHERE' in base_query:
        base_query += f" AND {id_compare}"
    else:
        base_query += f" WHERE {id_compare}"

    # Add parameter for ID comparison
    params.append(sujet_id)

    # Add ORDER BY and LIMIT
    base_query += f" ORDER BY {order_by} LIMIT 1"

    print(f"[ADJACENT DEBUG] Final query: {base_query}")
    print(f"[ADJACENT DEBUG] Final params: {params}")

    # Execute query
    sujet = db.execute(base_query, params).fetchone()

    if sujet:
        print(
            f"[ADJACENT DEBUG] Found adjacent sujet: {sujet['id']} - {sujet['original_sujet']}")
        # Increment view count
        db.execute(
            'UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet['id'],))
        db.commit()
        # Re-fetch to get updated view count
        return get_sujet_by_id(sujet['id'])
    else:
        print(f"[ADJACENT DEBUG] No adjacent sujet found")
        return None

    return None


def update_sujet_title(sujet_id, new_title):
    """
    Updates the title part of the original_sujet field for a sujet.
    Preserves the ID prefix format (ID: xxx - ).

    Args:
        sujet_id (int): The ID of the sujet to update
        new_title (str): The new title text

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = get_db()

        # Get the current original_sujet value
        current_sujet = db.execute(
            'SELECT original_sujet FROM sujets WHERE id = ?',
            (sujet_id,)
        ).fetchone()

        if not current_sujet:
            return False

        # Extract the ID prefix if it exists
        current_text = current_sujet['original_sujet']
        match = current_text.split(' - ', 1)

        if len(match) > 1 and match[0].startswith('ID:'):
            # Preserve the ID prefix format
            id_prefix = match[0] + ' - '
            updated_text = id_prefix + new_title
        else:
            # If no ID prefix format exists, create one
            updated_text = f"ID: {sujet_id} - {new_title}"

        # Update the database
        db.execute(
            'UPDATE sujets SET original_sujet = ? WHERE id = ?',
            (updated_text, sujet_id)
        )
        db.commit()

        return True
    except Exception as e:
        print(f"Error updating sujet title: {e}")
        return False


def add_new_sujet(title, ai_suggestion="", user_notes=""):
    """
    Adds a new sujet to the database with the given title and optional AI suggestion.
    Automatically assigns the next available ID.

    Args:
        title (str): The title for the new sujet
        ai_suggestion (str, optional): AI suggestion for the sujet
        user_notes (str, optional): User notes for the sujet

    Returns:
        dict: The newly created sujet data or None if failed
    """
    try:
        db = get_db()

        # Get the highest ID currently in the database
        max_id_row = db.execute(
            'SELECT MAX(id) as max_id FROM sujets').fetchone()
        next_id = 1
        if max_id_row and max_id_row['max_id']:
            next_id = max_id_row['max_id'] + 1

        # Format the original_sujet with ID prefix
        original_sujet = f"ID: {next_id} - {title}"

        # Format the current date as YYYY-MM-DD
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Insert the new sujet
        db.execute(
            '''INSERT INTO sujets 
               (id, original_sujet, ai_suggestion, user_notes, user_tags, status, view_count, person, date_created) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (next_id, original_sujet, ai_suggestion,
             user_notes, "", "new", 1, "", current_date)
        )
        db.commit()

        # Return the newly created sujet
        return get_sujet_by_id(next_id)
    except Exception as e:
        print(f"Error adding new sujet: {e}")
        return None

# --- CLI Commands ---


@click.command('add-sujets')
@click.argument('csv_filepath', type=click.Path(exists=True))
def add_sujets_command(csv_filepath):
    """Adds new sujets from a CSV file to the database if they don't already exist."""
    conn = get_db()
    # ... (rest of the function is the same)
    try:
        df_new_sujets = pd.read_csv(csv_filepath)
        if 'Original sujet' in df_new_sujets.columns:
            df_new_sujets = df_new_sujets.rename(
                columns={'Original sujet': 'original_sujet'})
            df_new_sujets['ai_suggestion'] = df_new_sujets.get(
                'LLM interpretation', '')
        elif 'Original Sujet' in df_new_sujets.columns:
            df_new_sujets = df_new_sujets.rename(
                columns={'Original Sujet': 'original_sujet'})
            df_new_sujets['ai_suggestion'] = df_new_sujets.get(
                'Suggested Enrichment', '')
        # ... (rest of logic is the same)
        added_count = 0
        skipped_count = 0
        for index, row in df_new_sujets.iterrows():
            original_sujet_text = row.get('original_sujet')
            if pd.isna(original_sujet_text):
                continue
            original_sujet_text = str(original_sujet_text).strip()
            if not original_sujet_text:
                continue

            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM sujets WHERE original_sujet = ?", (original_sujet_text,))
            if cursor.fetchone():
                skipped_count += 1
            else:
                ai_suggestion_text = str(row.get('ai_suggestion', '')).strip()
                cursor.execute("""
                    INSERT INTO sujets (original_sujet, ai_suggestion, user_notes, user_tags, status, view_count, person, date_created)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (original_sujet_text, ai_suggestion_text, '', '', 'needs_enrichment', 0, '', datetime.now().strftime('%d.%m.%y')))
                added_count += 1
        conn.commit()
        print(
            f"Added {added_count} new sujets, skipped {skipped_count} existing ones.")
    except Exception as e:
        print(f"An error occurred: {e}")


@click.command('init-db')
def init_db_command():
    """Initialize the database from the initial CSV file."""
    try:
        if not os.path.exists(INITIAL_CSV_PATH):
            print(f"Error: Initial CSV file not found at {INITIAL_CSV_PATH}.")
            sys.exit(1)
        df = pd.read_csv(INITIAL_CSV_PATH)
        # ... (column renaming logic is the same)
        if 'Original sujet' in df.columns:
            df = df.rename(columns={'Original sujet': 'original_sujet'})
            df['ai_suggestion'] = df.get('LLM interpretation', '')
        elif 'Original Sujet' in df.columns:
            df = df.rename(columns={'Original Sujet': 'original_sujet'})
            df['ai_suggestion'] = df.get('Suggested Enrichment', '')
        # ...
        df['user_notes'] = ''
        df['user_tags'] = ''
        df['status'] = 'needs_enrichment'
        df['view_count'] = 0
        df['person'] = ''
        # Add date_created field as NULL for existing entries
        df['date_created'] = None
        conn = get_db()
        df.index = df.index + 1
        df.to_sql('sujets', conn, if_exists='replace',
                  index=True, index_label='id')
        conn.commit()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"An error occurred during DB initialization: {e}")
        sys.exit(1)

# --- Registration Functions ---


def register_cli_commands(app):
    """Registers CLI commands with the Flask app."""
    app.cli.add_command(add_sujets_command)
    app.cli.add_command(init_db_command)


def register_teardown(app):
    """Registers the teardown function for database connections."""
    app.teardown_appcontext(close_connection)
