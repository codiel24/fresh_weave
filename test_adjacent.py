#!/usr/bin/env python3
"""Test script to debug adjacent sujet functionality"""

import sqlite3
from flask import Flask

# Create a minimal Flask app to get the context
app = Flask(__name__)
app.config['DATABASE'] = 'instance/sujets.db'


def test_adjacent_logic():
    """Test the adjacent sujet logic directly on the database"""
    print('=== TESTING ADJACENT SUJET LOGIC ===')

    conn = sqlite3.connect('instance/sujets.db')
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    cursor = conn.cursor()

    test_id = 553
    print(f'Testing for sujet ID {test_id}')

    # Test what the current backend logic should find
    print('\n1. Testing current backend logic:')

    # Next: ID > 553
    cursor.execute(
        'SELECT id, original_sujet FROM sujets WHERE id > ? ORDER BY id ASC LIMIT 1', (test_id,))
    next_result = cursor.fetchone()
    if next_result:
        print(
            f'   Next sujet: ID {next_result["id"]} - {next_result["original_sujet"][:50]}...')
    else:
        print('   Next sujet: None found')

    # Prev: ID < 553
    cursor.execute(
        'SELECT id, original_sujet FROM sujets WHERE id < ? ORDER BY id DESC LIMIT 1', (test_id,))
    prev_result = cursor.fetchone()
    if prev_result:
        print(
            f'   Prev sujet: ID {prev_result["id"]} - {prev_result["original_sujet"][:50]}...')
    else:
        print('   Prev sujet: None found')

    # Test with filters (simulate what might be causing the issue)
    print('\n2. Testing with various filter scenarios:')

    # Scenario: Empty string filters (what Flask might pass)
    tags_filter = "user_tags LIKE ?"
    people_filter = "person LIKE ?"

    # Test with empty string patterns
    cursor.execute(f'''
        SELECT id, original_sujet FROM sujets 
        WHERE id > ? AND ({tags_filter} OR {people_filter})
        ORDER BY id ASC LIMIT 1
    ''', (test_id, '%' + '' + '%', '%' + '' + '%'))

    filtered_result = cursor.fetchone()
    if filtered_result:
        print(f'   With empty string filters: ID {filtered_result["id"]}')
    else:
        print('   With empty string filters: No results (THIS MIGHT BE THE BUG!)')

    # Test without any filters
    cursor.execute(
        'SELECT id, original_sujet FROM sujets WHERE id > ? ORDER BY id ASC LIMIT 1', (test_id,))
    no_filter_result = cursor.fetchone()
    if no_filter_result:
        print(f'   Without filters: ID {no_filter_result["id"]} (should work)')
    else:
        print('   Without filters: No results')

    conn.close()


if __name__ == '__main__':
    test_adjacent_logic()
