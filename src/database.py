import sqlite3
import os

DB_PATH = 'hera_workflow.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database by creating necessary tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create People table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create Tasks table
    # target_period_id mapping: 1: This Week, 2: Next Week, 3: This Month, 4: On Hold
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            action_name TEXT NOT NULL,
            status TEXT NOT NULL,
            target_period_id INTEGER NOT NULL,
            is_exact_date_active BOOLEAN NOT NULL DEFAULT 0,
            exact_date DATE,
            result TEXT NOT NULL DEFAULT 'Open',
            FOREIGN KEY (person_id) REFERENCES people (id)
        )
    ''')
    
    # Create task_history table (stores snapshots of tasks)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            action_name TEXT NOT NULL,
            status TEXT NOT NULL,
            target_period_id INTEGER NOT NULL,
            is_exact_date_active BOOLEAN NOT NULL DEFAULT 0,
            exact_date DATE,
            result TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
from datetime import date, timedelta, datetime
import calendar

def _get_dynamic_period(exact_date_str, base_period_id):
    """Calculates the dynamic period (1, 2, 3) based on exact date compared to today.
       If exact_date_str is None, returns base_period_id (e.g. 4 or 5).
    """
    if not exact_date_str:
        return base_period_id
        
    try:
        exact_date = datetime.strptime(exact_date_str, '%Y-%m-%d').date()
    except ValueError:
        return base_period_id
        
    today = date.today()
    days_to_friday = 4 - today.weekday()
    if days_to_friday < 0:
        days_to_friday += 7
    end_of_this_week = today + timedelta(days=days_to_friday)
    end_of_next_week = end_of_this_week + timedelta(days=7)
    
    if exact_date <= end_of_this_week:
        return 1
    elif exact_date <= end_of_next_week:
        return 2
    else:
        return 3

def _calculate_auto_exact_date(target_period_id):
    """Calculates an automatic exact date if the user didn't provide one but chose 1, 2, or 3."""
    today = date.today()
    days_to_friday = 4 - today.weekday()
    if days_to_friday < 0:
        days_to_friday += 7
        
    if target_period_id == 1:
        return (today + timedelta(days=days_to_friday)).strftime('%Y-%m-%d')
    elif target_period_id == 2:
        return (today + timedelta(days=days_to_friday) + timedelta(days=7)).strftime('%Y-%m-%d')
    elif target_period_id == 3:
        last_day = calendar.monthrange(today.year, today.month)[1]
        return date(today.year, today.month, last_day).strftime('%Y-%m-%d')
    return None

def get_all_people():
    """Returns a list of all people in the database."""
    conn = get_db_connection()
    people = conn.execute('SELECT * FROM people ORDER BY name').fetchall()
    conn.close()
    return people

def add_person(name):
    """Adds a new person to the database."""
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO people (name) VALUES (?)', (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Person already exists, do nothing
    finally:
        conn.close()

def get_person_by_id(person_id):
    """Retrieves a single person by their ID."""
    conn = get_db_connection()
    person = conn.execute('SELECT * FROM people WHERE id = ?', (person_id,)).fetchone()
    conn.close()
    return person

def get_tasks_by_person(person_id, sort_mode='manual'):
    """Retrieves all tasks for a specific person, ordered by the chosen sort mode."""
    conn = get_db_connection()
    
    if sort_mode == 'priority':
        order_clause = 'CASE WHEN exact_date IS NULL THEN 1 ELSE 0 END, exact_date ASC, target_period_id ASC, sort_order ASC, id DESC'
    else: # manual
        order_clause = 'sort_order ASC, id DESC'
        
    raw_tasks = conn.execute(f'''
        SELECT * FROM tasks 
        WHERE person_id = ? 
        ORDER BY {order_clause}
    ''', (person_id,)).fetchall()
    
    tasks = []
    for row in raw_tasks:
        task = dict(row)
        task['target_period_id'] = _get_dynamic_period(task['exact_date'], task['target_period_id'])
        if task['exact_date']:
            try:
                task['exact_date_formatted'] = datetime.strptime(task['exact_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            except ValueError:
                task['exact_date_formatted'] = task['exact_date']
        else:
            task['exact_date_formatted'] = None
        tasks.append(task)
        
    conn.close()
    return tasks

def get_all_tasks_with_people():
    """Retrieves all tasks joined with people names (useful for Excel export)."""
    conn = get_db_connection()
    raw_data = conn.execute('''
        SELECT t.*, p.name as person_name 
        FROM tasks t
        JOIN people p ON t.person_id = p.id
        ORDER BY p.name ASC, CASE WHEN t.exact_date IS NULL THEN 1 ELSE 0 END, t.exact_date ASC
    ''').fetchall()
    conn.close()
    
    data = []
    for row in raw_data:
        task = dict(row)
        task['target_period_id'] = _get_dynamic_period(task['exact_date'], task['target_period_id'])
        data.append(task)
        
    return data

def add_task(person_id, action_name, status, target_period_id, is_exact_date_active, exact_date):
    """Adds a new task for a specific person."""
    if not is_exact_date_active:
        exact_date = _calculate_auto_exact_date(target_period_id)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (person_id, action_name, status, target_period_id, is_exact_date_active, exact_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (person_id, action_name, status, target_period_id, is_exact_date_active, exact_date))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def update_task_result(task_id, result):
    """Updates the result status (Open/Closed) of a task."""
    conn = get_db_connection()
    old_task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if old_task:
        conn.execute('''
            INSERT INTO task_history 
            (task_id, action_name, status, target_period_id, is_exact_date_active, exact_date, result) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (old_task['id'], old_task['action_name'], old_task['status'], old_task['target_period_id'], 
              old_task['is_exact_date_active'], old_task['exact_date'], old_task['result']))
    conn.execute('UPDATE tasks SET result = ? WHERE id = ?', (result, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    """Deletes a task from the database."""
    conn = get_db_connection()
    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def update_task_order(task_orders):
    """Updates the manual sort order of tasks. task_orders is a list of dicts: [{'id': 1, 'order': 0}, ...]"""
    conn = get_db_connection()
    cursor = conn.cursor()
    for item in task_orders:
        cursor.execute('UPDATE tasks SET sort_order = ? WHERE id = ?', (item['order'], item['id']))
    conn.commit()
    conn.close()

def update_person(person_id, new_name):
    """Updates the name of a person."""
    conn = get_db_connection()
    try:
        conn.execute('UPDATE people SET name = ? WHERE id = ?', (new_name, person_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def delete_person(person_id):
    """Deletes a person and all their tasks."""
    conn = get_db_connection()
    conn.execute('DELETE FROM tasks WHERE person_id = ?', (person_id,))
    conn.execute('DELETE FROM people WHERE id = ?', (person_id,))
    conn.commit()
    conn.close()

def get_task_by_id(task_id):
    """Retrieves a single task by ID."""
    conn = get_db_connection()
    task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    conn.close()
    return task

def update_task_details(task_id, action_name, status, target_period_id, is_exact_date_active, exact_date):
    """Updates the details of a task and logs the change."""
    conn = get_db_connection()
    # First get current state to save in history
    old_task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if old_task:
        conn.execute('''
            INSERT INTO task_history 
            (task_id, action_name, status, target_period_id, is_exact_date_active, exact_date, result) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (old_task['id'], old_task['action_name'], old_task['status'], old_task['target_period_id'], 
              old_task['is_exact_date_active'], old_task['exact_date'], old_task['result']))
              
    if not is_exact_date_active:
        exact_date = _calculate_auto_exact_date(target_period_id)
        
    conn.execute('''
        UPDATE tasks 
        SET action_name = ?, status = ?, target_period_id = ?, is_exact_date_active = ?, exact_date = ?
        WHERE id = ?
    ''', (action_name, status, target_period_id, is_exact_date_active, exact_date, task_id))
    conn.commit()
    conn.close()

def log_task_change(task_id, description):
    """Deprecated: using task_history instead."""
    pass

def get_task_history(task_id):
    """Retrieves the history snapshots of a specific task."""
    conn = get_db_connection()
    raw_logs = conn.execute('SELECT * FROM task_history WHERE task_id = ? ORDER BY timestamp DESC', (task_id,)).fetchall()
    conn.close()
    
    logs = []
    for row in raw_logs:
        log = dict(row)
        if log['exact_date']:
            try:
                log['exact_date_formatted'] = datetime.strptime(log['exact_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            except ValueError:
                log['exact_date_formatted'] = log['exact_date']
        else:
            log['exact_date_formatted'] = None
        logs.append(log)
        
    return logs
