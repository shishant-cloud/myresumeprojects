from app import app

# --- Database Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///new_expense_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
