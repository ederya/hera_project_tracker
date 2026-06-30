from flask import Flask
from src.database import init_db

app = Flask(__name__)
app.secret_key = 'hera_workflow_secret_key_2026'

# Initialize database
init_db()

# Import routes to register them
from src import routes
