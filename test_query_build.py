#!/usr/bin/env python3
"""Test the build_sujet_query function"""

import sys
sys.path.append('.')


def test_query_building():
    """Test what queries get built with different filter inputs"""
    print('=== TESTING build_sujet_query FUNCTION ===')

    # Simulate the build_sujet_query function logic
    def simulate_build_query(filters=None):
        if filters is None:
            filters = {}

        base_query = "SELECT id, original_sujet, ai_suggestion, view_count, user_notes, user_tags, status, person, date_created FROM sujets"
        query_params = []
        where_clauses = []

        tags = filters.get('tags', [])
        print(f"  Tags input: {tags}")

        if tags:
            tag_clauses = []
            for tag in tags:
                if tag and tag.strip():
                    tag_clauses.append("user_tags LIKE ?")
                    query_params.append(f"%{tag.strip()}%")
            if tag_clauses:
                where_clauses.append(f"({ ' OR '.join(tag_clauses) })")

        people = filters.get('people', [])
        print(f"  People input: {people}")

        if people:
            people_clauses = []
            for person in people:
                if person and person.strip():
                    people_clauses.append("person LIKE ?")
                    query_params.append(f"%{person.strip()}%")
            if people_clauses:
                where_clauses.append(f"({ ' OR '.join(people_clauses) })")

        search_term = filters.get('search', '')
        print(f"  Search input: '{search_term}'")

        if search_term and search_term.strip():
            search_clauses = []
            search_value = f"%{search_term.strip()}%"
            search_clauses.append("original_sujet LIKE ?")
            search_clauses.append("user_notes LIKE ?")
            query_params.extend([search_value, search_value])
            where_clauses.append(f"({ ' OR '.join(search_clauses) })")

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        print(f"  Final query: {base_query}")
        print(f"  Final params: {query_params}")
        print()

        return base_query, query_params

    # Test 1: Empty lists (what frontend should send with ignoreFilters=true)
    print("Test 1: Empty lists")
    simulate_build_query({'tags': [], 'people': [], 'search': None})

    # Test 2: Lists with empty strings (what Flask might create)
    print("Test 2: Lists with empty strings")
    simulate_build_query({'tags': [''], 'people': [''], 'search': ''})

    # Test 3: None values
    print("Test 3: None/missing values")
    simulate_build_query({'tags': None, 'people': None, 'search': None})

    # Test 4: No filters dict
    print("Test 4: No filters dict")
    simulate_build_query({})


if __name__ == '__main__':
    test_query_building()
