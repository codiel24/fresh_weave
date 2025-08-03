#!/usr/bin/env python3
"""Test the exact Flask route that gets called during delete"""

import requests
import json


def test_flask_route():
    """Test the actual Flask route with the exact parameters from delete"""
    print('=== TESTING FLASK /adjacent_sujet ROUTE ===')

    base_url = 'http://localhost:5000'  # Assuming Flask is running

    # Test 1: Exact call from delete (ignoreFilters=true)
    print('Test 1: Delete scenario (no filter parameters)')

    url = f'{base_url}/adjacent_sujet?id=553&direction=next'
    print(f'Calling: {url}')

    try:
        response = requests.get(url)
        data = response.json()
        print(f'Response: {data}')

        if data.get('status') == 'ok':
            print(f'SUCCESS: Found sujet ID {data["sujet"]["id"]}')
        else:
            print(f'FAILED: {data.get("status")} - {data.get("message", "")}')
    except Exception as e:
        print(f'ERROR: {e}')

    print()

    # Test 2: Call with empty filter parameters (what might happen)
    print('Test 2: With empty filter parameters')

    url = f'{base_url}/adjacent_sujet?id=553&direction=next&tags=&people=&search='
    print(f'Calling: {url}')

    try:
        response = requests.get(url)
        data = response.json()
        print(f'Response: {data}')

        if data.get('status') == 'ok':
            print(f'SUCCESS: Found sujet ID {data["sujet"]["id"]}')
        else:
            print(f'FAILED: {data.get("status")} - {data.get("message", "")}')
    except Exception as e:
        print(f'ERROR: {e}')

    print()

    # Test 3: Previous direction
    print('Test 3: Previous direction')

    url = f'{base_url}/adjacent_sujet?id=553&direction=prev'
    print(f'Calling: {url}')

    try:
        response = requests.get(url)
        data = response.json()
        print(f'Response: {data}')

        if data.get('status') == 'ok':
            print(f'SUCCESS: Found sujet ID {data["sujet"]["id"]}')
        else:
            print(f'FAILED: {data.get("status")} - {data.get("message", "")}')
    except Exception as e:
        print(f'ERROR: {e}')


if __name__ == '__main__':
    test_flask_route()
