from flask import render_template, request, redirect, url_for, send_file, session
from src import app
from src import database
from src.utils.excel_generator import generate_excel

@app.route('/')
def index():
    """Dashboard showing all person cards."""
    people = database.get_all_people()
    return render_template('index.html', people=people)

@app.route('/settings')
def settings():
    """Settings page to manage people."""
    people = database.get_all_people()
    return render_template('settings.html', people=people)

@app.route('/add_person', methods=['POST'])
def add_person():
    """Route to add a new person."""
    name = request.form.get('name')
    if name:
        database.add_person(name.strip())
    return redirect(url_for('settings'))

@app.route('/edit_person/<int:person_id>', methods=['POST'])
def edit_person(person_id):
    """Route to edit a person's name."""
    new_name = request.form.get('new_name')
    if new_name:
        database.update_person(person_id, new_name.strip())
    return redirect(url_for('settings'))

@app.route('/delete_person/<int:person_id>', methods=['POST'])
def delete_person(person_id):
    """Route to delete a person."""
    database.delete_person(person_id)
    return redirect(url_for('settings'))

@app.route('/debug_tasks/<int:person_id>')
def debug_tasks(person_id):
    from src import database
    tasks = database.get_tasks_by_person(person_id)
    tasks.extend(database.get_tasks_waiting_on_person(person_id))
    import json
    return json.dumps([{k: v for k, v in t.items() if k in ['id', 'action_name', 'waiting_reason', 'collab_waiting_reason']} for t in tasks])

@app.route('/person/<int:person_id>')
def person_detail(person_id):
    """View tasks for a specific person."""
    person = database.get_person_by_id(person_id)
    if not person:
        return redirect(url_for('index'))
    
    sort_mode = request.args.get('sort')
    if sort_mode:
        session['sort_mode'] = sort_mode
    else:
        sort_mode = session.get('sort_mode', 'manual')
    
    tasks = database.get_tasks_by_person(person_id, sort_mode=sort_mode)
    tasks.extend(database.get_tasks_waiting_on_person(person_id))
    
    # Load history for each task
    for task in tasks:
        task['history'] = database.get_task_history(task['id'])
        
    all_people = database.get_all_people()
        
    return render_template('person_detail.html', person=person, tasks=tasks, current_sort=sort_mode, all_people=all_people)

@app.route('/add_task/<int:person_id>', methods=['POST'])
def add_task(person_id):
    """Route to add a new task for a person."""
    action_name = request.form.get('action_name')
    status = request.form.get('status')
    target_period_id_str = request.form.get('target_period_id')
    target_period_id = int(target_period_id_str) if target_period_id_str else 4
    
    # Checkbox logic
    is_exact_date_active_str = request.form.get('is_exact_date_active')
    is_exact_date_active = 1 if is_exact_date_active_str == 'on' else 0
    
    exact_date = request.form.get('exact_date') if is_exact_date_active else None
    
    waiting_on_person_id_strs = request.form.getlist('waiting_on_person_ids')
    waiting_on_persons_data = []
    for pid in waiting_on_person_id_strs:
        if pid:
            reason = request.form.get(f'waiting_reason_{pid}')
            if reason and not reason.strip():
                reason = None
            waiting_on_persons_data.append({'id': int(pid), 'reason': reason})
    
    sort_mode = request.form.get('sort_mode', 'manual')
    if action_name and status:
        database.add_task(
            person_id=person_id,
            action_name=action_name,
            status=status,
            target_period_id=target_period_id,
            is_exact_date_active=is_exact_date_active,
            exact_date=exact_date,
            waiting_on_persons_data=waiting_on_persons_data
        )
    return redirect(url_for('person_detail', person_id=person_id, sort=sort_mode))

@app.route('/update_task_result/<int:task_id>', methods=['POST'])
def update_task_result(task_id):
    """Route to toggle task result between Open and Closed or mark waiting part as completed."""
    result = request.form.get('result')
    person_id_str = request.form.get('person_id')
    person_id = int(person_id_str) if person_id_str else 1
    sort_mode = request.form.get('sort_mode', 'manual')
    
    # Check if the person is a collaborator
    import sqlite3
    conn = database.get_db_connection()
    collab = conn.execute('SELECT * FROM task_collaborators WHERE task_id = ? AND person_id = ?', (task_id, person_id)).fetchone()
    conn.close()
    
    if collab:
        # Toggling waiting_is_completed status for the awaited person
        new_status = 1 if result == 'Closed' else 0
        database.update_waiting_status(task_id, person_id, new_status)
        
        person_record = database.get_person_by_id(person_id)
        person_name = person_record['name'] if person_record else "Bir kişi"
        status_text = "kendi kısmını kapattı!" if new_status else "kendi kısmını yeniden açtı!"
        
        database.log_task_change(task_id, f"{person_name} {status_text}")
    else:
        # Normal task closing
        if result == 'Closed':
            task = database.get_task_by_id(task_id)
            incomplete = [c['name'] for c in task.get('collaborators', []) if not c['is_completed']]
            if incomplete:
                return redirect(url_for('person_detail', person_id=person_id, sort=sort_mode))
        
        database.update_task_result(task_id, result)
        
    return redirect(url_for('person_detail', person_id=person_id, sort=sort_mode))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """Route to delete a task."""
    person_id = request.form.get('person_id')
    sort_mode = request.form.get('sort_mode', 'manual')
    database.delete_task(task_id)
    return redirect(url_for('person_detail', person_id=person_id, sort=sort_mode))

@app.route('/update_task_order', methods=['POST'])
def update_task_order():
    """Route to update manual sort order via AJAX."""
    data = request.get_json()
    if data and 'task_orders' in data:
        database.update_task_order(data['task_orders'])
        return {'status': 'success'}
    return {'status': 'error', 'message': 'Invalid data'}, 400



@app.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    """Route to edit task details."""
    task = database.get_task_by_id(task_id)
    if not task:
        return redirect(url_for('index'))
        
    action_name = request.form.get('action_name')
    status = request.form.get('status')
    target_period_id_str = request.form.get('target_period_id')
    target_period_id = int(target_period_id_str) if target_period_id_str else task['target_period_id']
    is_exact_date_active = 1 if request.form.get('is_exact_date_active') == 'on' else 0
    exact_date = request.form.get('exact_date') if is_exact_date_active else None
    
    waiting_on_person_id_strs = request.form.getlist('waiting_on_person_ids')
    waiting_on_persons_data = []
    for pid in waiting_on_person_id_strs:
        if pid:
            reason = request.form.get(f'waiting_reason_{pid}')
            if reason and not reason.strip():
                reason = None
            waiting_on_persons_data.append({'id': int(pid), 'reason': reason})
    
    sort_mode = request.form.get('sort_mode', 'manual')
    
    # Detect if anything actually changed (to avoid unnecessary snapshots)
    old_collabs = {c['id']: c for c in task.get('collaborators', [])}
    new_collabs = {d['id']: d for d in waiting_on_persons_data}
    
    # Only compare exact_date if exact date is active on both sides
    date_changed = task['is_exact_date_active'] != is_exact_date_active or (
        is_exact_date_active and (task['exact_date'] or '') != (exact_date or '')
    )
    
    collabs_changed = (
        set(old_collabs.keys()) != set(new_collabs.keys())
        or any((old_collabs[pid].get('waiting_reason') or '') != (new_collabs[pid]['reason'] or '')
               for pid in old_collabs if pid in new_collabs)
    )
    
    something_changed = (
        task['action_name'] != action_name
        or task['status'] != status
        or task['target_period_id'] != target_period_id
        or date_changed
        or collabs_changed
    )

    if something_changed:
        base_task_changed = (
            task['action_name'] != action_name
            or task['status'] != status
            or task['target_period_id'] != target_period_id
            or date_changed
        )
        custom_action = None
        if collabs_changed:
            if not base_task_changed:
                custom_action = "Kişiler / Mesajlar Güncellendi"
            else:
                custom_action = f"{task['action_name']} (Kişiler de Güncellendi)"
                
        # Save snapshot of the OLD state BEFORE updating
        database.log_task_snapshot(task, custom_action)
        database.update_task_details(
            task_id=task_id,
            action_name=action_name,
            status=status,
            target_period_id=target_period_id,
            is_exact_date_active=is_exact_date_active,
            exact_date=exact_date,
            waiting_on_persons_data=waiting_on_persons_data
        )
        
    return redirect(url_for('person_detail', person_id=task['person_id'], sort=sort_mode))

@app.route('/export_excel')
def export_excel():
    """Route to download the multi-sheet Excel file."""
    from datetime import datetime
    lang = request.args.get('lang', 'EN').upper()
    excel_file = generate_excel(lang)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f'Hera_Workflow_{timestamp}.xlsx'
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
