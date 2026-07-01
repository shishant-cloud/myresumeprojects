

class Config:
    SECRET_KEY = "your_super_secret_key_here_for_sessions"

    SQLALCHEMY_DATABASE_URI = \
        "sqlite:///new_expense_tracker.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False