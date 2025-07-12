import pytest
import sys
import os

# Add the project root to the Python path to allow for correct module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app # Import your Flask app instance

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # You can add test-specific configuration here if needed
    # For example, using a separate test database
    flask_app.config.update({
        "TESTING": True,
    })

    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_get_sujets_count_no_filters(client):
    """Test the /get_sujets_count endpoint with no filters."""
    # This is a placeholder test. We will add real assertions later.
    response = client.get('/get_sujets_count')
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'count' in data
    assert isinstance(data['count'], int)


def test_get_sujets_count_single_tag_filter(client):
    """Test the /get_sujets_count endpoint with a single tag filter."""
    # Replace 'AI' with a tag that is likely to exist in your test data for more meaningful testing
    # or consider setting up specific test data in the future.
    response = client.get('/get_sujets_count?tags=AI') 
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'count' in data
    assert isinstance(data['count'], int)
    # We can't assert a specific count without a controlled test database,
    # but we can assert that the count is not negative.
    assert data['count'] >= 0


def test_get_sujets_count_single_person_filter(client):
    """Test the /get_sujets_count endpoint with a single person filter."""
    # Replace 'S' with a person code that is likely to exist in your test data.
    response = client.get('/get_sujets_count?people=S') 
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'count' in data
    assert isinstance(data['count'], int)
    assert data['count'] >= 0


def test_get_sujet_single_tag_filter(client):
    """Test the /get_sujet endpoint with a single tag filter."""
    response = client.get('/get_sujet?tags=AI')
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert 'status' in data
    if data['status'] == 'ok':
        assert 'sujet' in data
        assert 'id' in data['sujet'] # Changed 'sujet_id' to 'id'
        assert 'original_sujet' in data['sujet'] # Changed 'original_prompt' to 'original_sujet'
        # Add other essential fields to check if a sujet is returned
    elif data['status'] == 'no_more_sujets':
        assert 'message' in data
    else:
        # If status is neither 'ok' nor 'no_more_sujets', it's an unexpected status
        assert False, f"Unexpected status: {data['status']}"


def test_get_sujet_single_person_filter(client):
    """Test the /get_sujet endpoint with a single person filter."""
    # Replace 'S' with a person code that is likely to exist in your test data.
    response = client.get('/get_sujet?people=S') 
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert 'status' in data
    if data['status'] == 'ok':
        assert 'sujet' in data
        assert 'id' in data['sujet']
        assert 'original_sujet' in data['sujet']
    elif data['status'] == 'no_more_sujets':
        assert 'message' in data
    else:
        assert False, f"Unexpected status: {data['status']}"


def test_get_sujets_count_multiple_tags_filter(client):
    """Test the /get_sujets_count endpoint with multiple tag filters (AND logic)."""
    # Replace with tags that are likely to co-exist in your test data for meaningful testing.
    response = client.get('/get_sujets_count?tags=AI,Productivity') 
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'count' in data
    assert isinstance(data['count'], int)
    assert data['count'] >= 0


def test_get_sujets_count_multiple_people_filter(client):
    """Test the /get_sujets_count endpoint with multiple people filters (OR logic)."""
    # Replace with person codes that are likely to exist in your test data.
    response = client.get('/get_sujets_count?people=S,Fam') 
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'count' in data
    assert isinstance(data['count'], int)
    assert data['count'] >= 0


