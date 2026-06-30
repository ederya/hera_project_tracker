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
            waiting_on_person_id INTEGER,
            FOREIGN KEY (person_id) REFERENCES people (id),
            FOREIGN KEY (waiting_on_person_id) REFERENCES people (id)
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
            waiting_on_person_id INTEGER,
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
        order_clause = "tasks.target_period_id ASC, CASE WHEN tasks.exact_date IS NULL OR tasks.exact_date = '' THEN 1 ELSE 0 END, tasks.exact_date ASC, tasks.sort_order ASC, tasks.id DESC"
    else: # manual
        order_clause = 'tasks.sort_order ASC, tasks.id DESC'
        
    raw_tasks = conn.execute(f'''
        SELECT tasks.*, p1.name as owner_name 
        FROM tasks 
        JOIN people p1 ON tasks.person_id = p1.id
        WHERE tasks.person_id = ?
        ORDER BY {order_clause}
    ''', (person_id,)).fetchall()
    
    task_ids = [str(r['id']) for r in raw_tasks]
    collaborators_by_task = {}
    if task_ids:
        placeholders = ','.join('?' * len(task_ids))
        collabs = conn.execute(f'''
            SELECT tc.task_id, tc.person_id, tc.is_completed, tc.waiting_reason, p.name 
            FROM task_collaborators tc
            JOIN people p ON tc.person_id = p.id
            WHERE tc.task_id IN ({placeholders})
        ''', task_ids).fetchall()
        for c in collabs:
            tid = c['task_id']
            if tid not in collaborators_by_task:
                collaborators_by_task[tid] = []
            collaborators_by_task[tid].append({'id': c['person_id'], 'name': c['name'], 'is_completed': c['is_completed'], 'waiting_reason': c['waiting_reason']})
    
    tasks = []
    for row in raw_tasks:
        task = dict(row)
        task['collaborators'] = collaborators_by_task.get(task['id'], [])
        # Only recalculate period dynamically when user set an explicit exact date
        if task['is_exact_date_active']:
            task['target_period_id'] = _get_dynamic_period(task['exact_date'], task['target_period_id'])
        if task['is_exact_date_active'] and task['exact_date']:
            try:
                task['exact_date_formatted'] = datetime.strptime(task['exact_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            except ValueError:
                task['exact_date_formatted'] = task['exact_date']
        else:
            task['exact_date_formatted'] = None
        tasks.append(task)
        
    if sort_mode == 'priority':
        tasks.sort(key=lambda x: (
            x['target_period_id'],
            1 if (not x['exact_date'] or x['exact_date'] == '') else 0,
            x['exact_date'] or '',
            x['sort_order'],
            -x['id']
        ))
        
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
    
    task_ids = [str(r['id']) for r in raw_data]
    collaborators_by_task = {}
    if task_ids:
        placeholders = ','.join('?' * len(task_ids))
        collabs = conn.execute(f'''
            SELECT tc.task_id, tc.person_id, tc.is_completed, tc.waiting_reason, p.name 
            FROM task_collaborators tc
            JOIN people p ON tc.person_id = p.id
            WHERE tc.task_id IN ({placeholders})
        ''', task_ids).fetchall()
        for c in collabs:
            tid = c['task_id']
            if tid not in collaborators_by_task:
                collaborators_by_task[tid] = []
            collaborators_by_task[tid].append({'id': c['person_id'], 'name': c['name'], 'is_completed': c['is_completed'], 'waiting_reason': c['waiting_reason']})
    
    conn.close()
    
    data = []
    for row in raw_data:
        task = dict(row)
        task['collaborators'] = collaborators_by_task.get(task['id'], [])
        if task['is_exact_date_active']:
            task['target_period_id'] = _get_dynamic_period(task['exact_date'], task['target_period_id'])
        data.append(task)
        
    data.sort(key=lambda x: (
        x['person_name'],
        x['target_period_id'],
        1 if (not x['exact_date'] or x['exact_date'] == '') else 0,
        x['exact_date'] or '',
        -x['id']
    ))
        
    return data

def add_task(person_id, action_name, status, target_period_id, is_exact_date_active, exact_date, waiting_on_persons_data=None):
    """Adds a new task for a specific person."""
    if not is_exact_date_active:
        exact_date = _calculate_auto_exact_date(target_period_id)
        
    if waiting_on_persons_data is None:
        waiting_on_persons_data = []
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (person_id, action_name, status, target_period_id, is_exact_date_active, exact_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (person_id, action_name, status, target_period_id, is_exact_date_active, exact_date))
    task_id = cursor.lastrowid
    
    for item in waiting_on_persons_data:
        cursor.execute('''
            INSERT INTO task_collaborators (task_id, person_id, is_completed, waiting_reason)
            VALUES (?, ?, 0, ?)
        ''', (task_id, item['id'], item.get('reason')))
        
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
            (task_id, action_name, status, target_period_id, is_exact_date_active, exact_date, result, waiting_on_person_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (old_task['id'], old_task['action_name'], old_task['status'], old_task['target_period_id'], 
              old_task['is_exact_date_active'], old_task['exact_date'], old_task['result'], old_task['waiting_on_person_id']))
    conn.execute('UPDATE tasks SET result = ? WHERE id = ?', (result, task_id))
    conn.commit()
    conn.close()

def update_waiting_status(task_id, person_id, is_completed):
    """Updates the waiting status (completed or not) for a specific awaited person."""
    conn = get_db_connection()
    conn.execute('UPDATE task_collaborators SET is_completed = ? WHERE task_id = ? AND person_id = ?', (is_completed, task_id, person_id))
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
    """Retrieves a single task by ID, including its collaborators."""
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if not row:
        conn.close()
        return None
        
    task = dict(row)
    collabs = conn.execute('''
        SELECT tc.person_id, p.name, tc.is_completed, tc.waiting_reason
        FROM task_collaborators tc
        JOIN people p ON tc.person_id = p.id
        WHERE tc.task_id = ?
    ''', (task_id,)).fetchall()
    
    task['collaborators'] = []
    for c in collabs:
        task['collaborators'].append({
            'id': c['person_id'], 
            'name': c['name'], 
            'is_completed': c['is_completed'], 
            'waiting_reason': c['waiting_reason']
        })
        
    conn.close()
    return task

def update_task_details(task_id, action_name, status, target_period_id, is_exact_date_active, exact_date, waiting_on_persons_data=None):
    """Updates the details of a task."""
    if waiting_on_persons_data is None:
        waiting_on_persons_data = []
        
    conn = get_db_connection()
        
    if not is_exact_date_active:
        exact_date = _calculate_auto_exact_date(target_period_id)
        
    conn.execute('''
        UPDATE tasks 
        SET action_name = ?, status = ?, target_period_id = ?, is_exact_date_active = ?, exact_date = ?
        WHERE id = ?
    ''', (action_name, status, target_period_id, is_exact_date_active, exact_date, task_id))
    
    # We clear and re-insert collaborators if the list changed.
    # Enforce rule: incomplete collaborators cannot be removed.
    existing_collabs = conn.execute('SELECT person_id, is_completed, waiting_reason FROM task_collaborators WHERE task_id = ?', (task_id,)).fetchall()
    existing_dict = {c['person_id']: c for c in existing_collabs}
    
    conn.execute('DELETE FROM task_collaborators WHERE task_id = ?', (task_id,))
    
    new_pid_set = {item['id'] for item in waiting_on_persons_data}
    
    # First, re-add any existing incomplete collabs that were missing from input
    for pid, c in existing_dict.items():
        if pid not in new_pid_set and not c['is_completed']:
            waiting_on_persons_data.append({'id': pid, 'reason': c['waiting_reason']})
    
    for item in waiting_on_persons_data:
        pid = item['id']
        reason = item.get('reason')
        # Keep old completed status if they were already here, else 0
        is_completed = existing_dict[pid]['is_completed'] if pid in existing_dict else 0
        conn.execute('''
            INSERT INTO task_collaborators (task_id, person_id, is_completed, waiting_reason)
            VALUES (?, ?, ?, ?)
        ''', (task_id, pid, is_completed, reason))
        
    conn.commit()
    conn.close()

def log_task_snapshot(task_dict, custom_action_name=None):
    """Saves the current task state as a history snapshot. If custom_action_name is provided, uses it instead of task name."""
    action_val = custom_action_name if custom_action_name else task_dict['action_name']
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO task_history 
        (task_id, action_name, status, target_period_id, is_exact_date_active, exact_date, result, waiting_on_person_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (task_dict['id'], action_val, task_dict['status'], task_dict['target_period_id'], 
          task_dict['is_exact_date_active'], task_dict['exact_date'], task_dict['result'], task_dict.get('waiting_on_person_id')))
    conn.commit()
    conn.close()

def log_task_change(task_id, description):
    """Legacy: logs a named event (e.g. 'kendi kismini kapatti') as a history entry."""
    conn = get_db_connection()
    old_task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if old_task:
        conn.execute('''
            INSERT INTO task_history 
            (task_id, action_name, status, target_period_id, is_exact_date_active, exact_date, result, waiting_on_person_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (old_task['id'], description, old_task['status'], old_task['target_period_id'], 
              old_task['is_exact_date_active'], old_task['exact_date'], old_task['result'], old_task['waiting_on_person_id']))
        conn.commit()
    conn.close()

def get_task_history(task_id):
    """Retrieves the history snapshots of a specific task."""
    conn = get_db_connection()
    raw_logs = conn.execute('''
        SELECT th.*, p2.name as waiting_on_person_name
        FROM task_history th
        LEFT JOIN people p2 ON th.waiting_on_person_id = p2.id
        WHERE th.task_id = ? 
        ORDER BY th.timestamp DESC
    ''', (task_id,)).fetchall()
    conn.close()
    
    logs = []
    for row in raw_logs:
        log = dict(row)
        # Only format exact_date if it was explicitly active at snapshot time
        if log['is_exact_date_active'] and log['exact_date']:
            try:
                log['exact_date_formatted'] = datetime.strptime(log['exact_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            except ValueError:
                log['exact_date_formatted'] = log['exact_date']
        else:
            log['exact_date_formatted'] = None
        # Convert UTC timestamp to Turkey time (UTC+3) and format as DD.MM.YYYY HH:MM
        try:
            ts = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
            ts = ts + timedelta(hours=3)
            log['timestamp'] = ts.strftime('%d.%m.%Y %H:%M')
        except (ValueError, TypeError):
            pass
        logs.append(log)
        
    return logs

def get_tasks_waiting_on_person(person_id):
    """Retrieves all open tasks where the given person is marked as the waiting_on_person."""
    conn = get_db_connection()
    raw_tasks = conn.execute('''
        SELECT tasks.*, p1.name as owner_name, tc.waiting_reason as collab_waiting_reason, tc.is_completed as waiting_is_completed
        FROM tasks 
        JOIN people p1 ON tasks.person_id = p1.id
        JOIN task_collaborators tc ON tasks.id = tc.task_id
        WHERE tc.person_id = ? AND tasks.result = 'Open' AND tc.is_completed = 0
        ORDER BY tasks.target_period_id ASC, tasks.id DESC
    ''', (person_id,)).fetchall()
    
    tasks = []
    for row in raw_tasks:
        task = dict(row)
        task['waiting_reason'] = row['collab_waiting_reason']
        if task['is_exact_date_active']:
            task['target_period_id'] = _get_dynamic_period(task['exact_date'], task['target_period_id'])
        if task['is_exact_date_active'] and task['exact_date']:
            try:
                task['exact_date_formatted'] = datetime.strptime(task['exact_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            except ValueError:
                task['exact_date_formatted'] = task['exact_date']
        else:
            task['exact_date_formatted'] = None
        tasks.append(task)
        
    conn.close()
    return tasks
