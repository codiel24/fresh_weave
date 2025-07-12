# weave_batch.py (Incorporating batch processing)

from dotenv import load_dotenv
import os
import time
import pandas as pd
import openai
from google.oauth2.service_account import Credentials
import gspread
# Use an alias to distinguish from openai.APIError
from gspread.exceptions import APIError as GspreadAPIError

# --- Load Environment Variables ---
# This will load variables from the .env file into the script's environment
load_dotenv()

# --- Configuration ---
# Read from environment variables. os.getenv() returns None if the variable is not set.
# It's good practice to add checks to ensure these are loaded.
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
# The openai client will automatically use this if set
# Note: client reads from env var OPENAI_API_KEY
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# --- Batch Processing Configuration ---
BATCH_SIZE = 10  # How many items to process in each run
# File to store the index of the last item processed
LAST_INDEX_FILE = os.path.join(os.path.dirname(
    __file__), 'last_processed_index.txt')

# --- Validate Configuration ---
if not SERVICE_ACCOUNT_FILE:
    print("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
    print("Please check your .env file or ensure the variable is set before running.")
    exit()
if not GOOGLE_SHEET_ID:
    print("Error: GOOGLE_SHEET_ID environment variable not set.")
    print("Please check your .env file or ensure the variable is set before running.")
    exit()
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable not set.")
    print("OpenAI calls may fail if the key is not provided.")
    # Don't exit here, allow the script to proceed and let the OpenAI function handle the API error


# --- Google Sheets Setup ---
# Changed scope to include write permission if you ever want to write back to the sheet
# For now, it's still read-only for fetching data, but good to have write capability ready
# Use full sheets scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# --- Added debugging prints and detailed error handling here ---
print(f"Attempting to load credentials from: {SERVICE_ACCOUNT_FILE}")

try:
    # Use Credentials.from_service_account_file to get credentials
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    print("Credentials loaded successfully.")  # <-- Step 1 Success

    # Authorize gspread client
    gc = gspread.authorize(credentials)
    print("gspread client authorized.")  # <-- Step 2 Success

    # Open the spreadsheet by key
    spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
    # <-- Step 3 Success
    print(f"Spreadsheet '{GOOGLE_SHEET_ID}' opened successfully.")

    # Access the first worksheet
    worksheet = spreadsheet.sheet1
    print("First worksheet accessed.")  # <-- Step 4 Success

# --- Specific Error Handling ---
except FileNotFoundError:
    print(
        f"Error: Google Service Account file not found at {SERVICE_ACCOUNT_FILE}")
    print("Please check the GOOGLE_APPLICATION_CREDENTIALS path in your .env file.")
    exit()
except GspreadAPIError as e:  # Using the alias GspreadAPIError
    print(f"Error connecting to Google Sheets: {e}")
    print("Please check your GOOGLE_SHEET_ID, sheet sharing permissions, and service account file validity.")
    print("Make sure the Google Sheets API is enabled for your Google Cloud Project.")
    # Try to extract project ID from the error if possible
    project_id = "YOUR_PROJECT_ID_HERE"  # Default placeholder
    try:
        # Attempt to parse error details for project ID
        if hasattr(e, 'response') and e.response is not None:
            details = e.response.json().get('error', {}).get('details', [{}])
            if details and isinstance(details, list) and details[0].get('project_id'):
                project_id = details[0]['project_id']
    except:
        pass  # Ignore errors during project ID extraction
    print(
        f"Enable it by visiting: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project={project_id}")
    exit()
# --- More Detailed Generic Exception Handling ---
except Exception as e:
    print(f"An unexpected error occurred during Google Sheets setup:")
    print(f"Error Type: {type(e).__name__}")  # Print the class name
    print(f"Error Details: {e}")           # Print the error message
    exit()


# --- OpenAI Helper Function ---
def get_enrichment_suggestion(sujet_text):
    """Calls OpenAI API to get a suggested enrichment for a brief sujet."""
    # Note: The client automatically uses OPENAI_API_KEY env var if set
    # if not OPENAI_API_KEY is checked at the start of the script, but we add
    # a local check too for clarity/safety within the function.
    if not os.getenv('OPENAI_API_KEY'):  # Check env var directly within the function
        print(
            f"Warning: OpenAI API key not available for '{sujet_text}'. Skipping API call.")
        return "[OpenAI API key not set. Cannot generate suggestion.]"

    prompt = f"""
    You are helping someone organize very brief personal notes ("sujets").
    Your task is to understand the likely meaning or core theme of the brief note and suggest relevant tags or categories.
    Provide a slightly more descriptive phrase or sentence clarifying the note's meaning, followed by suggested tags.
    The tags should be comma-separated keywords relevant to the topic (e.g., Travel, AI, Personal, Funny, Science, Observation, Quote).

    Example:
    Input: "weird hat coffee shop"
    Suggestion: "Observation about someone wearing a very unusual hat in a coffee shop. Tags: Observation, People Watching, Funny, Everyday Life."

    Input: "AI ethical debate"
    Suggestion: "Reflecting on recent discussions or articles about the ethical challenges of AI. Tags: AI, Ethics, Technology, Society, News."

    Input: "Feeling overwhelmed"
    Suggestion: "Recalling a personal experience of feeling overwhelmed. Tags: Personal, Feeling, Emotion, Self-reflection, Vulnerable."

    Input: "Great book quote"
    Suggestion: "A memorable quote from a book recently read. Tags: Quote, Reading, Literature, Philosophy, Inspiration."

    Input: "Visited the new museum exhibit"
    Suggestion: "Visited a new museum exhibit about modern art. Tags: Art, Culture, Travel (if applicable), Activity."

    Now, provide a suggestion for the following note. Format: Clarification phrase. Tags: Tag1, Tag2, Tag3...
    Input: "{sujet_text}"

    Suggestion:
    """
    try:
        # client = openai.OpenAI(api_key=OPENAI_API_KEY) # Not needed if env var is set
        client = openai.OpenAI()  # Reads from env var OPENAI_API_KEY automatically
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for organizing personal notes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        suggestion = response.choices[0].message.content.strip()
        return suggestion
    except openai.AuthenticationError as e:
        print(
            f"Error calling OpenAI API for '{sujet_text}': Authentication failed. Check your API key.")
        # Return a specific error message for this entry
        return f"[Error generating suggestion: Authentication Failed ({e})]"
    except openai.APIError as e:
        print(f"Error calling OpenAI API for '{sujet_text}': API Error: {e}")
        # Return a specific error message for this entry
        return f"[Error generating suggestion: API Error ({e})]"
    except Exception as e:
        print(
            f"An unexpected error occurred calling OpenAI API for '{sujet_text}': {e}")
        # Return a specific error message for this entry
        return f"[Error generating suggestion: Unexpected Error ({e})]"


# --- Main Logic ---
print("Fetching data from Google Sheet...")
try:
    # Use get_all_values() to get all data
    all_sujets_data = worksheet.get_all_values()
    # Get first column, filter empty rows/cells.
    # Skip the header row if your sheet has one.
    # Assuming row 1 is header, start from index 1: all_sujets_data[1:]
    sujets_full = [row[0] for row in all_sujets_data if row and row[0].strip()]

except GspreadAPIError as e:  # Using the alias
    print(f"Error reading data from sheet: {e}")
    print("Make sure the Google Sheets API is enabled for your Google Cloud Project:")
    project_id = "YOUR_PROJECT_ID_HERE"  # Default placeholder
    try:
        # Attempt to parse error details for project ID
        if hasattr(e, 'response') and e.response is not None:
            details = e.response.json().get('error', {}).get('details', [{}])
            if details and isinstance(details, list) and details[0].get('project_id'):
                project_id = details[0]['project_id']
    except:
        pass  # Ignore errors during project ID extraction
    print(
        f"Enable it by visiting: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project={project_id}")
    exit()
except Exception as e:
    print(f"An unexpected error occurred during data fetching: {e}")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Details: {e}")
    exit()

print(f"Found {len(sujets_full)} total non-empty entries in the first column.")

# --- Batch Processing Logic ---
start_index = 0
if os.path.exists(LAST_INDEX_FILE):
    try:
        with open(LAST_INDEX_FILE, 'r') as f:
            content = f.read().strip()
            if content.isdigit():
                start_index = int(content)
                print(
                    f"Resuming processing from index {start_index} (read from {LAST_INDEX_FILE}).")
            else:
                print(
                    f"Warning: {LAST_INDEX_FILE} contains non-digit content: '{content}'. Starting from index 0.")
    except Exception as e:
        print(f"Error reading {LAST_INDEX_FILE}: {e}. Starting from index 0.")

# Determine the end index for the current batch
end_index = min(start_index + BATCH_SIZE, len(sujets_full))

# Select the current batch of sujets to process
sujets_to_process = sujets_full[start_index:end_index]

if not sujets_to_process:
    print("No new entries found in the current batch range.")
    print(
        f"Last processed index was {start_index}. Total entries available: {len(sujets_full)}.")
    if start_index >= len(sujets_full):
        print("All entries appear to have been processed.")
        # Optional: Handle resetting the index file or sending a notification
    exit()  # Exit if no items in this batch

print(
    f"Processing {len(sujets_to_process)} entries (Batch from index {start_index} to {end_index-1}).")
print("Generating enrichment suggestions with OpenAI...")

# --- Load existing results if the CSV file exists ---
output_csv_path = os.path.join(os.path.dirname(
    __file__), 'sujet_enrichments.csv')  # Using absolute path
existing_df = pd.DataFrame(columns=['Original Sujet', 'Suggested Enrichment'])
if os.path.exists(output_csv_path):
    try:
        existing_df = pd.read_csv(output_csv_path)
        print(
            f"Loaded {len(existing_df)} existing results from {output_csv_path}.")
    except Exception as e:
        print(
            f"Warning: Could not read existing CSV file {output_csv_path}: {e}")
        # Start fresh if read fails
        existing_df = pd.DataFrame(
            columns=['Original Sujet', 'Suggested Enrichment'])

# Prepare to collect results for the current batch
current_batch_results = []

# Process the selected batch
for i, sujet in enumerate(sujets_to_process):
    # Display index relative to the overall list and the current batch
    overall_index = start_index + i
    print(
        f"\nProcessing entry {overall_index + 1}/{len(sujets_full)} (Batch index {i+1}/{len(sujets_to_process)}): '{sujet}'")

    suggestion = get_enrichment_suggestion(sujet)
    current_batch_results.append(
        {'Original Sujet': sujet, 'Suggested Enrichment': suggestion}
    )

    # Add a small delay to avoid hitting API rate limits
    # Consider a slightly longer delay if processing many items quickly
    time.sleep(0.5)

# Convert current batch results to DataFrame
current_batch_df = pd.DataFrame(current_batch_results)

# --- Combine existing results with the current batch results ---
# Append new results. The combined DataFrame will contain all processed entries.
# This handles cases where the script might be rerun on an index already in the CSV
# (e.g., if a previous run failed mid-batch), though the index file usually prevents this.
# A more robust approach might involve checking if the sujet is already in existing_df
# before processing, but for simplicity, we just append. This assumes unique 'Original Sujet'
# or that you don't mind duplicates if you rerun on the same start_index.
combined_df = pd.concat([existing_df, current_batch_df], ignore_index=True)

# Optional: Remove potential duplicates if the same entry was processed multiple times
# combined_df = combined_df.drop_duplicates(subset=['Original Sujet']).reset_index(drop=True)


# Only show results if we processed at least one entry in this batch
if not current_batch_df.empty:
    print("\n--- Enrichment Suggestions (Batch) ---")
    # Display results for the current batch only for clarity
    with pd.option_context('display.max_colwidth', None):
        print(current_batch_df.to_string(index=False))

    # --- Save the combined results (all processed entries) to the CSV file ---
    # This overwrites the file each time, ensuring it contains all data processed SO FAR
    try:
        combined_df.to_csv(output_csv_path, index=False)
        print(
            f"\nSaved combined enrichments (total {len(combined_df)} entries) to {output_csv_path}")
    except Exception as e:
        print(f"Error saving results to {output_csv_path}: {e}")
else:
    print("\nNo entries processed in this run.")

# --- Save the index for the NEXT batch ---
# This index marks the start of the *next* batch
next_start_index = end_index
try:
    with open(LAST_INDEX_FILE, 'w') as f:
        f.write(str(next_start_index))
    print(f"Saved next start index ({next_start_index}) to {LAST_INDEX_FILE}.")
except Exception as e:
    print(f"Error writing {LAST_INDEX_FILE}: {e}.")

print("\nBatch processing finished.")
