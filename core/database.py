"""
Database Module — SQLite Backend
=================================
Manages the SQLite database for the expert system.

Tables:
- users: username, password, role (admin/user)
- penyakit: id_penyakit, nama_penyakit
- gejala: id_gejala, nama_gejala
- rules_cf: id_rule, id_penyakit, id_gejala, bobot_cf
- rules_fc: id_rule, kondisi_if, id_penyakit

On first run, data is imported from CSV files into SQLite.
After that, all CRUD operations work on SQLite only — CSV files are never modified.
"""

import sqlite3
import pandas as pd
import os
import hashlib

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DATA_DIR, 'pakar.db')


def _hash_password(password):
    """Hash password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_connection():
    """Get a SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    Initialize the database: create tables and import CSV data if needed.
    This is idempotent — safe to call multiple times.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
            nama_lengkap TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS penyakit (
            id_penyakit TEXT PRIMARY KEY,
            nama_penyakit TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS gejala (
            id_gejala TEXT PRIMARY KEY,
            nama_gejala TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rules_cf (
            id_rule TEXT PRIMARY KEY,
            id_penyakit TEXT NOT NULL,
            id_gejala TEXT NOT NULL,
            bobot_cf REAL NOT NULL,
            FOREIGN KEY (id_penyakit) REFERENCES penyakit(id_penyakit),
            FOREIGN KEY (id_gejala) REFERENCES gejala(id_gejala)
        );

        CREATE TABLE IF NOT EXISTS rules_fc (
            id_rule TEXT PRIMARY KEY,
            kondisi_if TEXT NOT NULL,
            id_penyakit TEXT NOT NULL,
            FOREIGN KEY (id_penyakit) REFERENCES penyakit(id_penyakit)
        );
    """)

    # Check if data already exists (skip import if so)
    cursor.execute("SELECT COUNT(*) FROM penyakit")
    penyakit_count = cursor.fetchone()[0]

    if penyakit_count == 0:
        _import_csv_data(conn)

    # Create default accounts if no users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        cursor.execute(
            "INSERT INTO users (username, password, role, nama_lengkap) VALUES (?, ?, ?, ?)",
            ("admin", _hash_password("admin123"), "admin", "Administrator")
        )
        cursor.execute(
            "INSERT INTO users (username, password, role, nama_lengkap) VALUES (?, ?, ?, ?)",
            ("user", _hash_password("user123"), "user", "User Default")
        )

    conn.commit()
    conn.close()


def _import_csv_data(conn):
    """Import data from CSV files into SQLite tables (one-time operation)."""
    cursor = conn.cursor()

    # Import penyakit.csv
    csv_path = os.path.join(DATA_DIR, 'penyakit.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT OR IGNORE INTO penyakit (id_penyakit, nama_penyakit) VALUES (?, ?)",
                (row['id_penyakit'], row['nama_penyakit'])
            )

    # Import gejala.csv
    csv_path = os.path.join(DATA_DIR, 'gejala.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT OR IGNORE INTO gejala (id_gejala, nama_gejala) VALUES (?, ?)",
                (row['id_gejala'], row['nama_gejala'])
            )

    # Import rules_cf.csv
    csv_path = os.path.join(DATA_DIR, 'rules_cf.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT OR IGNORE INTO rules_cf (id_rule, id_penyakit, id_gejala, bobot_cf) VALUES (?, ?, ?, ?)",
                (row['id_rule'], row['id_penyakit'], row['id_gejala'], row['bobot_cf'])
            )

    # Import rules_forward.csv
    csv_path = os.path.join(DATA_DIR, 'rules_forward.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT OR IGNORE INTO rules_fc (id_rule, kondisi_if, id_penyakit) VALUES (?, ?, ?)",
                (row['id_rule'], row['kondisi_if'], row['id_penyakit'])
            )

    conn.commit()


# =============================================
# AUTH functions
# =============================================

def authenticate(username, password):
    """
    Authenticate a user.
    Returns dict with user info if successful, None otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, role, nama_lengkap FROM users WHERE username = ? AND password = ?",
        (username, _hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()

    if user:
        return {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'nama_lengkap': user['nama_lengkap'],
        }
    return None


def get_all_users():
    """Get all users as a list of dicts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, nama_lengkap FROM users ORDER BY id")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def add_user(username, password, role, nama_lengkap=""):
    """Add a new user. Returns True if success, False if username exists."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role, nama_lengkap) VALUES (?, ?, ?, ?)",
            (username, _hash_password(password), role, nama_lengkap)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def update_user(user_id, username=None, password=None, role=None, nama_lengkap=None):
    """Update user fields. Only non-None fields are updated."""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if username is not None:
        updates.append("username = ?")
        params.append(username)
    if password is not None:
        updates.append("password = ?")
        params.append(_hash_password(password))
    if role is not None:
        updates.append("role = ?")
        params.append(role)
    if nama_lengkap is not None:
        updates.append("nama_lengkap = ?")
        params.append(nama_lengkap)

    if updates:
        params.append(user_id)
        try:
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    conn.close()
    return True


def delete_user(user_id):
    """Delete a user by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# =============================================
# PENYAKIT CRUD
# =============================================

def get_all_penyakit():
    """Get all penyakit as DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM penyakit ORDER BY id_penyakit", conn)
    conn.close()
    return df


def add_penyakit(id_penyakit, nama_penyakit):
    """Add a new penyakit. Returns True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO penyakit (id_penyakit, nama_penyakit) VALUES (?, ?)",
            (id_penyakit, nama_penyakit)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def update_penyakit(id_penyakit, nama_penyakit):
    """Update a penyakit name."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE penyakit SET nama_penyakit = ? WHERE id_penyakit = ?",
        (nama_penyakit, id_penyakit)
    )
    conn.commit()
    conn.close()


def delete_penyakit(id_penyakit):
    """Delete a penyakit and cascade-delete related rules."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rules_cf WHERE id_penyakit = ?", (id_penyakit,))
    cursor.execute("DELETE FROM rules_fc WHERE id_penyakit = ?", (id_penyakit,))
    cursor.execute("DELETE FROM penyakit WHERE id_penyakit = ?", (id_penyakit,))
    conn.commit()
    conn.close()


def get_next_penyakit_id():
    """Generate next penyakit ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_penyakit FROM penyakit ORDER BY id_penyakit DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        num = int(row['id_penyakit'].replace('P', ''))
        return f"P{num + 1:03d}"
    return "P001"


# =============================================
# GEJALA CRUD
# =============================================

def get_all_gejala():
    """Get all gejala as DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM gejala ORDER BY id_gejala", conn)
    conn.close()
    return df


def add_gejala(id_gejala, nama_gejala):
    """Add a new gejala. Returns True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO gejala (id_gejala, nama_gejala) VALUES (?, ?)",
            (id_gejala, nama_gejala)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def update_gejala(id_gejala, nama_gejala):
    """Update a gejala name."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE gejala SET nama_gejala = ? WHERE id_gejala = ?",
        (nama_gejala, id_gejala)
    )
    conn.commit()
    conn.close()


def delete_gejala(id_gejala):
    """Delete a gejala and cascade-delete related CF rules."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rules_cf WHERE id_gejala = ?", (id_gejala,))
    cursor.execute("DELETE FROM gejala WHERE id_gejala = ?", (id_gejala,))
    conn.commit()
    conn.close()


def get_next_gejala_id():
    """Generate next gejala ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_gejala FROM gejala ORDER BY id_gejala DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        num = int(row['id_gejala'].replace('G', ''))
        return f"G{num + 1:03d}"
    return "G001"


# =============================================
# RULES CF CRUD
# =============================================

def get_all_rules_cf():
    """Get all CF rules as DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM rules_cf ORDER BY id_rule", conn)
    conn.close()
    return df


def add_rule_cf(id_rule, id_penyakit, id_gejala, bobot_cf):
    """Add a new CF rule. Returns True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO rules_cf (id_rule, id_penyakit, id_gejala, bobot_cf) VALUES (?, ?, ?, ?)",
            (id_rule, id_penyakit, id_gejala, bobot_cf)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def update_rule_cf(id_rule, id_penyakit, id_gejala, bobot_cf):
    """Update a CF rule."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE rules_cf SET id_penyakit = ?, id_gejala = ?, bobot_cf = ? WHERE id_rule = ?",
        (id_penyakit, id_gejala, bobot_cf, id_rule)
    )
    conn.commit()
    conn.close()


def delete_rule_cf(id_rule):
    """Delete a CF rule."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rules_cf WHERE id_rule = ?", (id_rule,))
    conn.commit()
    conn.close()


def get_next_rule_cf_id():
    """Generate next CF rule ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_rule FROM rules_cf ORDER BY id_rule DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        num = int(row['id_rule'].replace('R', ''))
        return f"R{num + 1:03d}"
    return "R001"


def check_duplicate_rule_cf(id_penyakit, id_gejala, exclude_rule_id=None):
    """Check if a CF rule with same penyakit+gejala already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    if exclude_rule_id:
        cursor.execute(
            "SELECT COUNT(*) FROM rules_cf WHERE id_penyakit = ? AND id_gejala = ? AND id_rule != ?",
            (id_penyakit, id_gejala, exclude_rule_id)
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM rules_cf WHERE id_penyakit = ? AND id_gejala = ?",
            (id_penyakit, id_gejala)
        )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


# =============================================
# RULES FC CRUD
# =============================================

def get_all_rules_fc():
    """Get all FC rules as DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM rules_fc ORDER BY id_rule", conn)
    conn.close()
    return df


def add_rule_fc(id_rule, kondisi_if, id_penyakit):
    """Add a new FC rule. Returns True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO rules_fc (id_rule, kondisi_if, id_penyakit) VALUES (?, ?, ?)",
            (id_rule, kondisi_if, id_penyakit)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def update_rule_fc(id_rule, kondisi_if, id_penyakit):
    """Update an FC rule."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE rules_fc SET kondisi_if = ?, id_penyakit = ? WHERE id_rule = ?",
        (kondisi_if, id_penyakit, id_rule)
    )
    conn.commit()
    conn.close()


def delete_rule_fc(id_rule):
    """Delete an FC rule."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rules_fc WHERE id_rule = ?", (id_rule,))
    conn.commit()
    conn.close()


def get_next_rule_fc_id():
    """Generate next FC rule ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_rule FROM rules_fc ORDER BY id_rule DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        num = int(row['id_rule'].replace('R', ''))
        return f"R{num + 1:02d}"
    return "R01"


# =============================================
# STATS
# =============================================

def get_related_rules_count(id_penyakit=None, id_gejala=None):
    """Get count of related rules for cascade delete warnings."""
    conn = get_connection()
    cursor = conn.cursor()
    result = {'cf': 0, 'fc': 0}

    if id_penyakit:
        cursor.execute("SELECT COUNT(*) FROM rules_cf WHERE id_penyakit = ?", (id_penyakit,))
        result['cf'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rules_fc WHERE id_penyakit = ?", (id_penyakit,))
        result['fc'] = cursor.fetchone()[0]

    if id_gejala:
        cursor.execute("SELECT COUNT(*) FROM rules_cf WHERE id_gejala = ?", (id_gejala,))
        result['cf'] = cursor.fetchone()[0]

    conn.close()
    return result
