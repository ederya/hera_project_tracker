import sys
sys.path.append('src')
import database

conn = database.get_db_connection()

patterns = [
    'Task created with status%',
    'Task result marked as%',
    'Action Name changed%',
    'Status changed%',
    'Target Period updated%',
    'Date setting updated%',
    'Removed waiting person%',
    'Updated waiting reason%',
    'Added waiting person%',
]

total = 0
for p in patterns:
    cur = conn.execute('DELETE FROM task_history WHERE description LIKE ?', (p,))
    total += cur.rowcount

conn.commit()
conn.close()
print(f'Deleted {total} old log entries')
