# db_operations.py
import sqlite3
import os
import pandas as pd
import click
import sys
from flask import g

# --- Constants ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# Allow deployment platforms to override DB location via env var (e.g., /var/data/sujets.db on Render)
DATABASE_PATH = os.getenv("DATABASE_PATH") or os.path.join(APP_ROOT, 'instance', 'sujets.db')
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
        'SELECT id, original_sujet, ai_suggestion, user_notes, user_tags, status, view_count, person FROM sujets WHERE id = ?',
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

    columns_to_select = "COUNT(*) as count" if filters.get('select_count') else "id, original_sujet, ai_suggestion, view_count, user_notes, user_tags, status, person"
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
        sort_order = filters.get('sort_order', 'ASC').upper()
        if sort_order not in ['ASC', 'DESC']:
            sort_order = 'ASC'

        if sort_by == 'random':
            base_query += " ORDER BY RANDOM()"
        elif sort_by == 'id':
            base_query += f" ORDER BY id {sort_order}"

    return base_query, query_params

# --- Data Access Functions for App ---

def get_next_sujet_by_filter(offset, tags, people, sort_order):
    """Fetches the next sujet based on filters and increments its view count."""
    db = get_db()
    filters = {
        'tags': tags,
        'people': people,
        'sort_by': 'id',
        'sort_order': sort_order
    }
    query, params = build_sujet_query(filters)
    
    query += " LIMIT 1 OFFSET ?"
    params.append(offset)
    
    sujet = db.execute(query, params).fetchone()
    
    if sujet:
        db.execute('UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet['id'],))
        db.commit()
        return get_sujet_by_id(sujet['id'])  # Re-fetch to get updated view count
    
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
    query = "SELECT id, original_sujet, ai_suggestion, view_count, user_notes, user_tags, status, person FROM sujets ORDER BY RANDOM() LIMIT 1"
    sujet = db.execute(query).fetchone()
    
    if sujet:
        db.execute('UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet['id'],))
        db.commit()
        return get_sujet_by_id(sujet['id'])  # Re-fetch to get updated view count
        
    return None

def get_first_or_last_sujet_from_db(first=True):
    """
    Fetches the first or last sujet by ID and increments its view count.
    :param first: Boolean, True to fetch the first sujet (min ID), False for the last (max ID).
    """
    db = get_db()
    order = "ASC" if first else "DESC"
    query = f"SELECT id, original_sujet, ai_suggestion, view_count, user_notes, user_tags, status, person FROM sujets ORDER BY id {order} LIMIT 1"
    
    sujet = db.execute(query).fetchone()
    
    if sujet:
        db.execute('UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (sujet['id'],))
        db.commit()
        # Re-fetch to get the updated view count
        return get_sujet_by_id(sujet['id'])
        
    return None

def update_sujet_status(sujet_id, status, user_notes=None, user_tags=None, person=None):
    """Updates the status and other fields of a sujet in the database."""
    db = get_db()
    if status == 'enriched':
        db.execute(
            'UPDATE sujets SET status = ?, user_notes = ?, user_tags = ?, person = ? WHERE id = ?',
            (status, user_notes, user_tags, person, sujet_id)
        )
    elif status == 'skipped':
        db.execute(
            'UPDATE sujets SET status = ? WHERE id = ?',
            (status, sujet_id)
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
        tags = [tag.strip() for tag in row['user_tags'].split(',') if tag.strip()]
        all_tags.update(tags)
    return sorted(list(all_tags))

def get_all_unique_people():
    """Fetches all unique, non-empty person values."""
    db = get_db()
    cursor = db.execute("SELECT DISTINCT person FROM sujets WHERE person != '' AND person IS NOT NULL")
    people = [row['person'] for row in cursor.fetchall()]
    return sorted(people)

def get_adjacent_sujet(current_id, tags, people, sort_order='ASC', direction='next'):
    """Return the sujet immediately before or after current_id given the active filters.

    Args:
        current_id (int): The reference sujet ID that is currently displayed.
        tags (list[str]): Tag filters (already lower-case).
        people (list[str]): People filters (already lower-case).
        sort_order (str): 'ASC' or 'DESC' indicating current sort order.
        direction   (str): 'next' or 'prev'.

    Returns:
        Row or None – sujet row that matches the request or None if at the edge.
    """
    db = get_db()

    # Decide comparison operator and ORDER BY direction so that we fetch one row.
    if direction == 'next':
        if sort_order.upper() == 'ASC':
            comp, order = '>', 'ASC'
        else:  # DESC visual order, so next visible item has lower ID
            comp, order = '<', 'DESC'
    elif direction == 'prev':
        if sort_order.upper() == 'ASC':
            comp, order = '<', 'DESC'
        else:
            comp, order = '>', 'ASC'
    else:
        raise ValueError("direction must be 'next' or 'prev'")

    filters = {
        'tags': tags,
        'people': people,
    }

    base_query, params = build_sujet_query(filters)
    # Remove trailing ORDER BY because we'll add our own customised ORDER BY
    if 'ORDER BY' in base_query:
        base_query = base_query.split('ORDER BY')[0].strip()

    # Append the id comparator, ensuring we include a WHERE clause if one doesn't already exist
    if ' WHERE ' in base_query.upper():
        base_query += f" AND id {comp} ?"
    else:
        base_query += f" WHERE id {comp} ?"
    params.append(current_id)
    base_query += f" ORDER BY id {order} LIMIT 1"

    row = db.execute(base_query, params).fetchone()
    if row:
        # Maintain view_count behaviour consistent with other fetch helpers
        db.execute('UPDATE sujets SET view_count = view_count + 1 WHERE id = ?', (row['id'],))
        db.commit()
        return get_sujet_by_id(row['id'])
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
            df_new_sujets = df_new_sujets.rename(columns={'Original sujet': 'original_sujet'})
            df_new_sujets['ai_suggestion'] = df_new_sujets.get('LLM interpretation', '')
        elif 'Original Sujet' in df_new_sujets.columns:
            df_new_sujets = df_new_sujets.rename(columns={'Original Sujet': 'original_sujet'})
            df_new_sujets['ai_suggestion'] = df_new_sujets.get('Suggested Enrichment', '')
        # ... (rest of logic is the same)
        added_count = 0
        skipped_count = 0
        for index, row in df_new_sujets.iterrows():
            original_sujet_text = row.get('original_sujet')
            if pd.isna(original_sujet_text): continue
            original_sujet_text = str(original_sujet_text).strip()
            if not original_sujet_text: continue
            
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM sujets WHERE original_sujet = ?", (original_sujet_text,))
            if cursor.fetchone():
                skipped_count += 1
            else:
                ai_suggestion_text = str(row.get('ai_suggestion', '')).strip()
                cursor.execute("""
                    INSERT INTO sujets (original_sujet, ai_suggestion, user_notes, user_tags, status, view_count, person)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (original_sujet_text, ai_suggestion_text, '', '', 'needs_enrichment', 0, ''))
                added_count += 1
        conn.commit()
        print(f"Added {added_count} new sujets, skipped {skipped_count} existing ones.")
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
        conn = get_db()
        df.index = df.index + 1
        df.to_sql('sujets', conn, if_exists='replace', index=True, index_label='id')
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