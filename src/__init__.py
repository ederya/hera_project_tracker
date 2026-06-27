from flask import Flask
from src.database import init_db

app = Flask(__name__)

# Initialize database
init_db()

# Import routes to register them
from src import routes
