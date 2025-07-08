# gsheet_operations.py

import os
import gspread
import pandas as pd
import json
from google.oauth2.service_account import Credentials

# --- Google Sheets Integration ---

def get_gsheet_client():
    """Establishes a connection to the Google Sheet and returns the client and sheet."""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = None

        # Cloud-friendly: Load credentials from environment variable if it exists
        creds_json_str = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if creds_json_str:
            try:
                creds_info = json.loads(creds_json_str)
                creds = Credentials.from_service_account_info(creds_info, scopes=scope)
                print("--- INFO: Loaded Google credentials from environment variable. ---")
            except Exception as e:
                print(f"--- ERROR: Failed to load credentials from GOOGLE_CREDENTIALS_JSON: {e} ---")
                return None, None
        else:
            # Fallback for local development: Load credentials from file path
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_path:
                try:
                    creds = Credentials.from_service_account_file(creds_path, scopes=scope)
                    print("--- INFO: Loaded Google credentials from file path. ---")
                except Exception as e:
                    print(f"--- ERROR: Failed to load credentials from {creds_path}: {e} ---")
                    return None, None

        if not creds:
            print("--- WARNING: Google application credentials not found. Skipping GSheet logging. ---")
            return None, None
        client = gspread.authorize(creds)
        sheet_id = os.getenv('GOOGLE_SHEET_ID')
        if not sheet_id:
            print("--- WARNING: GOOGLE_SHEET_ID not set. Skipping GSheet logging. ---")
            return None, None
        
        sheet = client.open_by_key(sheet_id).sheet1
        return client, sheet
    except Exception as e:
        print(f"--- ERROR: Could not connect to Google Sheets: {e} ---")
        return None, None


def _log_sujet_to_sheet_impl(sheet, sujet_data):
    """(Private) Implementation for logging a sujet's data to the Google Sheet."""
    if not sheet:
        return False, "Google Sheet not available"
    try:
        headers = [
            'id', 'original_sujet', 'ai_suggestion', 'user_notes', 
            'user_tags', 'status', 'person', 'view_count', 'created_at', 'updated_at'
        ]
        data_to_log = {header: sujet_data.get(header, '') for header in headers}
        df = pd.DataFrame([data_to_log])
        values_to_append = df[headers].values.tolist()
        sheet.append_row(values_to_append[0], value_input_option='USER_ENTERED')
        print(f"--- INFO: Successfully logged sujet {sujet_data.get('id')} to Google Sheet. ---")
        return True, "Logged successfully"
    except Exception as e:
        print(f"--- ERROR: Failed to log to Google Sheets: {e} ---")
        return False, str(e)

def log_sujet_to_sheet(**sujet_data):
    """
    Public-facing function to log a sujet to Google Sheets.
    This is a wrapper that handles getting the sheet client and then calls the implementation.
    Accepts sujet data as keyword arguments.
    Returns a tuple (success, message).
    """
    _client, sheet = get_gsheet_client()
    if not sheet:
        print("--- WARNING (log_sujet_to_sheet): Could not get sheet client. Aborting log. ---")
        return False, "Could not get sheet client. Check credentials."

    return _log_sujet_to_sheet_impl(sheet, sujet_data)
