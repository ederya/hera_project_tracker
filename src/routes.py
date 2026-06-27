from flask import render_template, request, redirect, url_for, send_file
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

@app.route('/person/<int:person_id>')
def person_detail(person_id):
    """View tasks for a specific person."""
    person = database.get_person_by_id(person_id)
    if not person:
        return redirect(url_for('index'))
    
    sort_mode = request.args.get('sort', 'manual')
    
    raw_tasks = database.get_tasks_by_person(person_id, sort_mode=sort_mode)
    tasks = []
    for row in raw_tasks:
        task_dict = dict(row)
        task_dict['history'] = database.get_task_history(task_dict['id'])
        tasks.append(task_dict)
        
    return render_template('person_detail.html', person=person, tasks=tasks, current_sort=sort_mode)

@app.route('/add_task/<int:person_id>', methods=['POST'])
def add_task(person_id):
    """Route to add a new task for a person."""
    action_name = request.form.get('action_name')
    status = request.form.get('status')
    target_period_id_str = request.form.get('target_period_id')
    target_period_id = int(target_period_id_str) if target_period_id_str else 1
    
    # Checkbox logic
    is_exact_date_active_str = request.form.get('is_exact_date_active')
    is_exact_date_active = 1 if is_exact_date_active_str == 'on' else 0
    
    exact_date = request.form.get('exact_date') if is_exact_date_active else None
    
    sort_mode = request.form.get('sort_mode', 'manual')
    if action_name and status:
        task_id = database.add_task(
            person_id=person_id,
            action_name=action_name,
            status=status,
            target_period_id=target_period_id,
            is_exact_date_active=is_exact_date_active,
            exact_date=exact_date
        )
        database.log_task_change(task_id, f"Task created with status: '{status}'")
    return redirect(url_for('person_detail', person_id=person_id, sort=sort_mode))

@app.route('/update_task_result/<int:task_id>', methods=['POST'])
def update_task_result(task_id):
    """Route to toggle task result between Open and Closed."""
    result = request.form.get('result')
    person_id = request.form.get('person_id')
    sort_mode = request.form.get('sort_mode', 'manual')
    database.update_task_result(task_id, result)
    database.log_task_change(task_id, f"Task result marked as: '{result}'")
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
    
    sort_mode = request.form.get('sort_mode', 'manual')
    
    # Check what changed to log it
    changes = []
    if task['action_name'] != action_name:
        changes.append(f"Action Name changed to '{action_name}'")
    if task['status'] != status:
        changes.append(f"Status changed to '{status}'")
    if task['target_period_id'] != target_period_id:
        changes.append(f"Target Period changed to ID {target_period_id}")
    if task['is_exact_date_active'] != is_exact_date_active or task['exact_date'] != exact_date:
        changes.append(f"Date setting updated")
        
    if changes:
        database.update_task_details(task_id, action_name, status, target_period_id, is_exact_date_active, exact_date)
        for change in changes:
            database.log_task_change(task_id, change)
            
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
