from flask import Flask, app
from models.models import User, Category, Expense, Bill, FinancialPlan

from extension import db
from models.models import Category
from extension import db, login_manager


def init_db(app):
    with app.app_context():
        # IMPORTANT: When the schema changes, you must delete the old .db file first.
        db.create_all() 
        
        # Define the desired categories
        default_categories = [
            'Food',
            'Shopping',
            'Rent/Mortgage',
            'Healthcare',
            'Transportation',
            'Electricity',
            'Water/Gas',
            'Internet/Phone',
            'Savings & Debt',
            'Savings', 
        ]
        
        # Ensure all required categories exist
        for name in default_categories:
            if not Category.query.filter_by(name=name, user_id=None).first():
                db.session.add(Category(name=name, user_id=None))
                db.session.commit()
                
        # Remove any unwanted legacy categories if needed
        misc_cat = Category.query.filter_by(name='Miscellaneous', user_id=None).first()
        if misc_cat:
            db.session.delete(misc_cat)
            db.session.commit()
            
        print("Default categories ensured.")
