import sqlite3
import os
import hashlib


def hash_password(password):
    """Securely hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    """Initialize SQLite database for user management."""
    db_path = 'users.db'

    # Connect to SQLite database (creates if not exists)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop existing table if it exists to recreate with correct schema
    cursor.execute('DROP TABLE IF EXISTS users')

    # Create users table with all required columns
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        user_type TEXT NOT NULL,
        farm_location TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

    print("Database initialized successfully.")


def add_user(first_name, last_name, email, password, user_type, farm_location=None):
    """Add a new user to the database."""
    db_path = 'users.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Hash the password before storing
    hashed_password = hash_password(password)

    try:
        cursor.execute('''
        INSERT INTO users 
        (first_name, last_name, email, password, user_type, farm_location) 
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (first_name, last_name, email, hashed_password, user_type, farm_location))

        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Email already exists
        return False
    finally:
        conn.close()


def verify_user(email, password):
    """Verify user credentials."""
    db_path = 'users.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Hash the input password
    hashed_password = hash_password(password)

    cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, hashed_password))
    user = cursor.fetchone()

    conn.close()

    return user is not None


# Initialize database when script is run
if __name__ == '__main__':
    init_db()