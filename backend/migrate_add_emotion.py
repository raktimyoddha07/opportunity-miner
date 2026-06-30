"""
Migration script: adds the emotion column to pain_points table.
Run once from the project root:
    backend\.venv\Scripts\python backend\migrate_add_emotion.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='pain_points' AND column_name='emotion'"
    ))
    exists = result.fetchone()
    if exists:
        print("emotion column already exists in pain_points table — nothing to do.")
    else:
        conn.execute(text("ALTER TABLE pain_points ADD COLUMN emotion VARCHAR(100)"))
        conn.commit()
        print("emotion column added to pain_points table successfully.")
