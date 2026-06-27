import sqlite3
from datetime import date, timedelta
import calendar
import os

DB_PATH = 'hera_workflow.db'

def run_migration():
    if not os.path.exists(DB_PATH):
        print("DB not found")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all tasks that have a target_period_id of 1, 2, or 3
    tasks = cursor.execute('SELECT id, target_period_id FROM tasks WHERE target_period_id IN (1, 2, 3) AND is_exact_date_active = 0').fetchall()
    
    today = date.today()
    days_to_friday = 4 - today.weekday()
    if days_to_friday < 0:
        days_to_friday += 7
    end_of_this_week = today + timedelta(days=days_to_friday)
    # End of next week
    end_of_next_week = end_of_this_week + timedelta(days=7)
    # End of this month
    last_day_of_month = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    
    updated_count = 0
    for tid, tpid in tasks:
        if tpid == 1:
            d = end_of_this_week
        elif tpid == 2:
            d = end_of_next_week
        else:
            d = last_day_of_month
            
        cursor.execute('UPDATE tasks SET exact_date = ? WHERE id = ?', (d.strftime('%Y-%m-%d'), tid))
        updated_count += 1
        
    conn.commit()
    conn.close()
    print(f"Migration completed. {updated_count} tasks updated.")

if __name__ == '__main__':
    run_migration()
