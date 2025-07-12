#!/usr/bin/env python3
"""
Database Synchronization Script for Weave

This script synchronizes the development and production databases with the following priorities:
1. Production data takes precedence (sujets, tags, enrichment)
2. Development schema changes are applied to production
3. Creates backups before any changes

Usage:
    python sync_db.py --download  # Download production DB to local backup, then sync schema changes to it
    python sync_db.py --upload    # Upload the synced DB to production (use with caution)
"""

import os
import sys
import sqlite3
import shutil
import argparse
import subprocess
from datetime import datetime
import tempfile

# Configuration
DEV_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'sujets.db')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db_backups')
TEMP_DIR = tempfile.gettempdir()

# Render configuration - update these with your actual values
RENDER_SSH_KEY = r"C:\Users\danie\.ssh\id_ed25519_render"  # Path to your Render SSH key
RENDER_HOST = "srv-d1bu58re5dus73evpbb0@ssh.frankfurt.render.com"  # Your Render SSH host (without ssh:// prefix)
PROD_DB_PATH = "/var/data/sujets.db"  # Path on Render's persistent disk

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

def timestamp():
    """Generate a timestamp string for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def backup_database(db_path, prefix="dev"):
    """Create a backup of the specified database"""
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return None
    
    backup_path = os.path.join(BACKUP_DIR, f"{prefix}_backup_{timestamp()}.db")
    shutil.copy2(db_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def get_schema(db_path):
    """Extract schema from a SQLite database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table definitions
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = cursor.fetchall()
    
    # Get index definitions
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;")
    indexes = cursor.fetchall()
    
    # Get view definitions
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='view';")
    views = cursor.fetchall()
    
    conn.close()
    
    return {
        'tables': [t[0] for t in tables],
        'indexes': [i[0] for i in indexes],
        'views': [v[0] for v in views]
    }

def get_table_columns(db_path, table_name):
    """Get column information for a specific table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    conn.close()
    
    return columns

def download_prod_db():
    """Download the production database from Render"""
    temp_prod_db = os.path.join(TEMP_DIR, f"prod_db_{timestamp()}.db")
    
    try:
        # Use scp with explicit parameters to avoid SSH agent issues
        cmd = f'scp -i "{RENDER_SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {RENDER_HOST}:{PROD_DB_PATH} "{temp_prod_db}"'
        print(f"Executing: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        print("Download successful")
        return temp_prod_db
    except subprocess.CalledProcessError as e:
        print(f"Error downloading production database: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return None

def upload_to_prod(db_path):
    """Upload a database to production"""
    try:
        # Use scp with explicit parameters to avoid SSH agent issues
        cmd = f'scp -i "{RENDER_SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "{db_path}" {RENDER_HOST}:{PROD_DB_PATH}'
        print(f"Executing: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        print("Upload successful")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error uploading database: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def apply_schema_changes(prod_db_path, dev_db_path):
    """Apply schema changes from dev to prod while preserving prod data"""
    # Create a working copy of the production database
    working_db = os.path.join(TEMP_DIR, f"working_db_{timestamp()}.db")
    shutil.copy2(prod_db_path, working_db)
    
    # Connect to both databases
    dev_conn = sqlite3.connect(dev_db_path)
    dev_cursor = dev_conn.cursor()
    
    working_conn = sqlite3.connect(working_db)
    working_cursor = working_conn.cursor()
    
    try:
        # Get schema information from both databases
        dev_schema = get_schema(dev_db_path)
        prod_schema = get_schema(prod_db_path)
        
        # Get table names
        dev_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        dev_tables = [row[0] for row in dev_cursor.fetchall()]
        
        working_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        prod_tables = [row[0] for row in working_cursor.fetchall()]
        
        # Process each table in dev that exists in prod
        for table in dev_tables:
            if table in prod_tables:
                # Get column information
                dev_columns = get_table_columns(dev_db_path, table)
                prod_columns = get_table_columns(prod_db_path, table)
                
                dev_column_names = [col[1] for col in dev_columns]
                prod_column_names = [col[1] for col in prod_columns]
                
                # Find new columns in dev that don't exist in prod
                new_columns = [col for col in dev_columns if col[1] not in prod_column_names]
                
                # Add new columns to the working database
                for col in new_columns:
                    col_name = col[1]
                    col_type = col[2]
                    col_default = col[4] if col[4] is not None else "NULL"
                    col_not_null = "NOT NULL" if col[3] == 1 else ""
                    
                    alter_sql = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type} {col_not_null}"
                    if col_default != "NULL":
                        alter_sql += f" DEFAULT {col_default}"
                    
                    print(f"Adding column: {alter_sql}")
                    working_cursor.execute(alter_sql)
            else:
                # Table exists in dev but not in prod, create it
                for create_stmt in dev_schema['tables']:
                    if f"CREATE TABLE {table}" in create_stmt:
                        print(f"Creating new table: {table}")
                        working_cursor.execute(create_stmt)
                        break
        
        # Commit changes
        working_conn.commit()
        print("Schema changes applied successfully")
        return working_db
    
    except Exception as e:
        print(f"Error applying schema changes: {e}")
        return None
    
    finally:
        dev_conn.close()
        working_conn.close()

def main():
    parser = argparse.ArgumentParser(description="Weave Database Synchronization Tool")
    parser.add_argument("--download", action="store_true", help="Download production DB and apply schema changes")
    parser.add_argument("--upload", action="store_true", help="Upload synced DB to production")
    
    args = parser.parse_args()
    
    if not args.download and not args.upload:
        parser.print_help()
        return
    
    # Backup the development database first
    dev_backup = backup_database(DEV_DB_PATH, "dev")
    if not dev_backup:
        print("Failed to backup development database. Exiting.")
        return
    
    if args.download:
        # Download production database
        prod_db = download_prod_db()
        if not prod_db:
            print("Failed to download production database. Exiting.")
            return
        
        # Backup the downloaded production database
        prod_backup = backup_database(prod_db, "prod")
        
        # Apply schema changes from dev to prod
        synced_db = apply_schema_changes(prod_db, DEV_DB_PATH)
        if not synced_db:
            print("Failed to apply schema changes. Exiting.")
            return
        
        # Copy the synced database to the development location
        print(f"Copying synced database to development location: {DEV_DB_PATH}")
        shutil.copy2(synced_db, DEV_DB_PATH)
        print("Sync completed successfully. Development database now has production data with development schema.")
    
    if args.upload:
        # Confirm before uploading
        confirm = input("Are you sure you want to upload the database to production? This will overwrite the production database. (y/N): ")
        if confirm.lower() != 'y':
            print("Upload cancelled.")
            return
        
        # Upload the development database to production
        success = upload_to_prod(DEV_DB_PATH)
        if success:
            print("Database uploaded to production successfully.")
        else:
            print("Failed to upload database to production.")

if __name__ == "__main__":
    main()
