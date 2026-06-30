import sys
sys.path.append('src')
import database

conn = database.get_db_connection()

# Find duplicate history entries: same task_id, same timestamp, keep only one
rows = conn.execute('''
    SELECT id, task_id, timestamp, action_name
    FROM task_history
    ORDER BY task_id, timestamp, id
''').fetchall()

seen = {}
to_delete = []
for row in rows:
    key = (row['task_id'], row['timestamp'])
    if key in seen:
        to_delete.append(row['id'])
    else:
        seen[key] = row['id']

print(f'Duplicate entries to delete: {to_delete}')
if to_delete:
    placeholders = ','.join('?' * len(to_delete))
    conn.execute(f'DELETE FROM task_history WHERE id IN ({placeholders})', to_delete)
    conn.commit()
    print(f'Deleted {len(to_delete)} duplicates')
conn.close()
