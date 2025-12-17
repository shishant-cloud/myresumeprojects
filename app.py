import bcrypt
import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from sqlalchemy import CheckConstraint, UniqueConstraint, func, cast, Date
import math # Needed for EMI calculation

# --- Configuration ---
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here_for_sessions'

# --- Database Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///new_expense_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Database Models (RESTORED/MODIFIED) ---

class FinancialPlan(db.Model):
    __tablename__ = 'financial_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    # New simplified fields for debt tracking
    loan_principal = db.Column(db.Numeric(12, 2), default=0.00)
    annual_interest_rate = db.Column(db.Numeric(5, 2), default=0.00) 
    loan_tenure_months = db.Column(db.Integer, default=0)
    monthly_net_income = db.Column(db.Numeric(12, 2), default=0.00) # Re-introducing salary for context
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expenses = db.relationship('Expense', backref='owner', lazy=True)
    categories = db.relationship('Category', backref='creator', lazy=True)
    bills = db.relationship('Bill', backref='owner', lazy=True) 
    financial_plan = db.relationship('FinancialPlan', backref='owner', uselist=False, lazy=True) # RESTORED

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    expenses = db.relationship('Expense', backref='category_ref', lazy=True)
    __table_args__ = (UniqueConstraint('name', 'user_id', name='_name_user_uc'),)

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (CheckConstraint(amount > 0, name='positive_amount'),)

class Bill(db.Model):
    __tablename__ = 'bills'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    is_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Initialization (Cleaned up) ---
def init_db():
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

            
# --- Routes ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('signup.html')

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or Email already exists!', 'warning')
            return render_template('signup.html')

        try:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login')) 

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')
            return render_template('signup.html')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id')
        password = request.form.get('password')

        user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    # 1. Fetch all categories available to the user (System default + User custom)
    all_categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id.is_(None))
    ).order_by(Category.name).all()
    
    # Set of category names to exclude from the dropdown
    categories_to_exclude = {'Savings & Debt'}
    
    # List to hold the final, filtered categories
    categories = []
    
    # Track names of categories already added to prevent duplicates
    added_names = set()

    for cat in all_categories:
        
        # Exclude the deprecated 'Savings & Debt' category
        if cat.name in categories_to_exclude:
            continue
            
        # Check for duplicate names (System category vs. Custom category)
        if cat.name in added_names:
            # If the name is already added, skip the current category. 
            continue
            
        # If it's a system category, or a unique custom category, add it
        categories.append(cat)
        added_names.add(cat.name)

    # Re-sort for display consistency after filtering
    categories.sort(key=lambda c: c.name)

    preselected_id = None
    if request.args.get('category_preload'):
        # Lookup the category by name provided in the preload argument
        cat = Category.query.filter_by(name=request.args.get('category_preload')).first()
        # Ensure preloaded category is not Savings & Debt and is a category we didn't filter out
        if cat and cat.name not in categories_to_exclude and cat.name in added_names: 
             preselected_id = cat.id

    if request.method == 'POST':
        try:
            amount = request.form.get('amount')
            date_str = request.form.get('date')
            category_id = request.form.get('category')
            description = request.form.get('description')

            if not all([amount, date_str, category_id]) or float(amount) <= 0:
                flash('Invalid data.', 'danger')
                return redirect(url_for('add'))
                
            selected_cat = Category.query.get(int(category_id))
            if selected_cat and selected_cat.name in categories_to_exclude:
                 flash(f'Cannot add expenses to the excluded "{selected_cat.name}" category.', 'danger')
                 return redirect(url_for('add'))


            expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            new_expense = Expense(user_id=current_user.id, amount=float(amount), date=expense_date, category_id=int(category_id), description=description)
            
            db.session.add(new_expense)
            db.session.commit()
            flash('Expense added successfully!', 'success')
            return redirect(url_for('dashboard')) 
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')

    return render_template('add.html', categories=categories, preselected_id=preselected_id, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/add_bill', methods=['POST'])
@login_required
def add_bill():
    try:
        amount = request.form.get('amount')
        due_date_str = request.form.get('due_date')
        category_id = request.form.get('category_id')
        description = request.form.get('description')

        if not all([amount, due_date_str, category_id]):
            flash('Missing required fields.', 'danger')
            return redirect(url_for('bill'))

        new_bill = Bill(
            user_id=current_user.id,
            amount=float(amount),
            due_date=datetime.strptime(due_date_str, '%Y-%m-%d').date(),
            category_id=int(category_id),
            description=description,
            is_paid=False
        )
        db.session.add(new_bill)
        db.session.commit()
        flash('Bill reminder set successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding bill: {e}', 'danger')

    return redirect(url_for('bill'))
    
# --- BILL MANAGEMENT ROUTES (UNCHANGED) ---

@app.route('/complete_bill/<int:bill_id>', methods=['POST'])
@login_required
def complete_bill(bill_id):
    """Marks a bill reminder as paid (completed)."""
    bill_to_complete = Bill.query.get_or_404(bill_id)
    if bill_to_complete.user_id != current_user.id:
        flash('You do not have permission to mark this bill.', 'danger')
        return redirect(url_for('bill'))
    try:
        bill_to_complete.is_paid = True
        cat_name = Category.query.get(bill_to_complete.category_id).name if bill_to_complete.category_id else 'Bill'
        flash(f'{cat_name} bill for ₹{float(bill_to_complete.amount)} marked as paid! Don\'t forget to add it as a new expense for accurate tracking.', 'success')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error marking bill as paid: {e}', 'danger')
    return redirect(url_for('bill'))

@app.route('/delete_bill/<int:bill_id>', methods=['POST'])
@login_required
def delete_bill(bill_id):
    """Deletes a bill reminder."""
    bill_to_delete = Bill.query.get_or_404(bill_id)
    if bill_to_delete.user_id != current_user.id:
        flash('You do not have permission to delete this bill.', 'danger')
        return redirect(url_for('bill'))
    try:
        db.session.delete(bill_to_delete)
        db.session.commit()
        flash('Bill reminder deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting bill reminder: {e}', 'danger')
    return redirect(url_for('bill'))

# --- DASHBOARD (UNCHANGED) ---
@app.route('/dashboard')
@login_required
def dashboard():
    """Renders the dashboard page containing charts and the detailed expense table."""
    expenses_data = db.session.query(Expense, Category.name.label('category_name'))\
        .join(Category, Expense.category_id == Category.id)\
        .filter(Expense.user_id == current_user.id).order_by(Expense.date.desc()).all()

    expenses_list = []
    total_expenses = 0.0
    
    total_savings_amount = 0.0
        
    for exp, cat_name in expenses_data:
        expenses_list.append({
            'id': exp.id,
            'date': exp.date.strftime('%Y-%m-%d'),
            'amount': float(exp.amount),
            'category': cat_name,
            'description': exp.description
        })
        total_expenses += float(exp.amount)
        
    return render_template('dashboard.html', 
                           expenses=expenses_list, 
                           total_expenses=total_expenses, 
                           username=current_user.username)


# --- ROUTE: View Expenses (Table Only) (UNCHANGED) ---
@app.route('/view')
@login_required
def view():
    """Renders the detailed expense table page (no charts)."""
    expenses_data = db.session.query(Expense, Category.name.label('category_name'))\
        .join(Category, Expense.category_id == Category.id)\
        .filter(Expense.user_id == current_user.id).order_by(Expense.date.desc()).all()

    expenses_list = []
    total_expenses = 0.0
    
    for exp, cat_name in expenses_data:
        expenses_list.append({
            'id': exp.id,
            'date': exp.date.strftime('%Y-%m-%d'),
            'amount': float(exp.amount),
            'category': cat_name,
            'description': exp.description
        })
        total_expenses += float(exp.amount)
        
    return render_template('view.html', expenses=expenses_list, total_expenses=total_expenses, username=current_user.username)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense_to_delete = Expense.query.get_or_404(expense_id)

    if expense_to_delete.user_id != current_user.id:
        flash('You do not have permission to delete this expense.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(expense_to_delete)
        db.session.commit()
        flash('Expense deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting expense: {e}', 'danger')

    return redirect(request.referrer or url_for('dashboard'))

# --- DISABLED ROUTE (UNCHANGED) ---
@app.route('/savings_details')
@login_required
def savings_details():
    """Renders the Savings page using the dedicated 'Savings' category."""
    flash("This feature has been temporarily disabled.", 'info')
    return redirect(url_for('dashboard'))


# --- NEW ROUTE: Loan Plan Input Form (Replaces /set_financial_plan) ---
@app.route('/set_loan_plan', methods=['GET', 'POST'])
@login_required
def set_loan_plan():
    plan = FinancialPlan.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        try:
            # Note: We rely on the template to enforce integer type for tenure, but convert safely
            principal = float(request.form.get('loan_principal', 0))
            rate = float(request.form.get('annual_interest_rate', 0))
            tenure = int(request.form.get('loan_tenure_months', 0))
            income = float(request.form.get('monthly_net_income', 0))
            
            if principal < 0 or rate < 0 or tenure <= 0 or income < 0:
                flash('Invalid input values. Principal, Rate, and Tenure must be positive.', 'danger')
                return redirect(url_for('set_loan_plan'))
            
            if plan:
                plan.loan_principal = principal
                plan.annual_interest_rate = rate
                plan.loan_tenure_months = tenure
                plan.monthly_net_income = income
                flash('Loan plan updated successfully!', 'success')
            else:
                plan = FinancialPlan(
                    user_id=current_user.id,
                    loan_principal=principal,
                    annual_interest_rate=rate,
                    loan_tenure_months=tenure,
                    monthly_net_income=income
                )
                db.session.add(plan)
                flash('Loan plan saved successfully! View your debt details.', 'success')
            
            db.session.commit()
            return redirect(url_for('debt_details'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error processing plan: {e}', 'danger')

    # GET request: Display the form, pre-filled if plan exists
    return render_template('loan_plan_form.html', plan=plan)


# --- MODIFIED ROUTE: Debt Details (Replaces /savings_debt_details) ---
@app.route('/debt_details')
@login_required
def debt_details():
    """Renders the Debt & EMI Tracker page, calculating EMI from saved plan."""
    
    plan = FinancialPlan.query.filter_by(user_id=current_user.id).first()
    
    # Redirect to plan setup if no plan exists
    if not plan or float(plan.loan_principal) <= 0:
        flash('Please set your loan details first to use the Debt Tracker.', 'info')
        return redirect(url_for('set_loan_plan'))
        
    P = float(plan.loan_principal)
    annualRate = float(plan.annual_interest_rate)
    N = int(plan.loan_tenure_months)
    
    # Calculate EMI (Ensure we handle zero rate/tenure gracefully)
    if P > 0 and annualRate > 0 and N > 0:
        R = annualRate / 12 / 100  # Monthly interest rate decimal
        # EMI Formula: P * R * (1 + R)^N / ((1 + R)^N - 1)
        # Handle division by zero edge case if math.pow(1 + R, N) - 1 is zero (e.g., if R is tiny and N is small)
        denominator = (math.pow(1 + R, N) - 1)
        if denominator == 0:
             EMI = P / N # Simple installment calculation if interest is effectively zero
        else:
             EMI = (P * R * math.pow(1 + R, N)) / denominator
             
        total_payment = EMI * N
        total_interest = total_payment - P
    else:
        EMI = 0.0
        total_payment = P # If no interest/tenure, total payment is principal
        total_interest = 0.0

    # 1. Fetch debt payment history (from 'Savings & Debt' category)
    debt_cat = Category.query.filter_by(name='Savings & Debt').first()
    
    total_debt_payments_made = 0.0
    debt_transactions = []
    
    if debt_cat:
        all_transactions = Expense.query.filter(
            Expense.user_id == current_user.id, 
            Expense.category_id == debt_cat.id
        ).order_by(Expense.date.desc()).all()
        
        for exp in all_transactions:
            item = {
                'id': exp.id,
                'date': exp.date.strftime('%Y-%m-%d'),
                'amount': float(exp.amount),
                'description': exp.description,
                'category_id': exp.category_id
            }
            debt_transactions.append(item)
            total_debt_payments_made += item['amount']
            
    # Calculate Remaining Principal (Simplified: Principal - Total Payments)
    remaining_principal = P - total_debt_payments_made
    if remaining_principal < 0:
        remaining_principal = 0.0 # Avoid negative remaining principal

    # Data to pass to the template
    context = {
        'plan': plan,
        'calculated_emi': EMI,
        'total_interest': total_interest,
        'total_payment': total_payment,
        'remaining_principal': remaining_principal,
        'total_debt_payments_made': total_debt_payments_made,
        'debt_transactions': debt_transactions,
        'username': current_user.username
    }
    
    return render_template('debt.html', **context)


# --- ALL OTHER CATEGORY ROUTES (UNCHANGED) ---

@app.route('/shopping_details')
@login_required
def shopping():
    shopping_categories = Category.query.filter(
        (Category.name == 'Shopping') & 
        ((Category.user_id == current_user.id) | (Category.user_id.is_(None)))
    ).all()
    
    cat_ids = [c.id for c in shopping_categories]
    expenses_list = []
    total_shopping = 0.0
    highest_shopping = 0.0

    if cat_ids:
        data = Expense.query.filter(Expense.user_id == current_user.id, Expense.category_id.in_(cat_ids)).order_by(Expense.date.desc()).all()
        for e in data:
            expenses_list.append({'date': e.date, 'amount': float(e.amount), 'description': e.description})
        
        total_shopping = sum(e['amount'] for e in expenses_list)
        if expenses_list: highest_shopping = max(e['amount'] for e in expenses_list)

    return render_template('shopping.html', shopping_expenses=expenses_list, 
                           total_shopping_spending=total_shopping, highest_shopping_expense=highest_shopping)

@app.route('/food_spending')
@login_required
def food():
    food_categories = Category.query.filter(
        (Category.name == 'Food') & 
        ((Category.user_id == current_user.id) | (Category.user_id.is_(None)))
    ).all()
    
    cat_ids = [c.id for c in food_categories]
    expenses_list = []
    total_food = 0.0
    highest_food = 0.0

    if cat_ids:
        data = Expense.query.filter(Expense.user_id == current_user.id, Expense.category_id.in_(cat_ids)).order_by(Expense.date.desc()).all()
        for e in data:
            expenses_list.append({'date': e.date, 'amount': float(e.amount), 'description': e.description})
            
        total_food = sum(e['amount'] for e in expenses_list)
        if expenses_list: highest_food = max(e['amount'] for e in expenses_list)

    return render_template('food.html', food_expenses=expenses_list, 
                           total_food_spending=total_food, highest_food_expense=highest_food)

@app.route('/healthcare_details')
@login_required
def healthcare():
    healthcare_categories = Category.query.filter(
        (Category.name == 'Healthcare') & 
        ((Category.user_id == current_user.id) | (Category.user_id.is_(None)))
    ).all()
    
    cat_ids = [c.id for c in healthcare_categories]
    expenses_list = []
    total_healthcare = 0.0
    highest_healthcare = 0.0

    if cat_ids:
        data = Expense.query.filter(Expense.user_id == current_user.id, Expense.category_id.in_(cat_ids)).order_by(Expense.date.desc()).all()
        for e in data:
            expenses_list.append({'date': e.date, 'amount': float(e.amount), 'description': e.description})
        
        total_healthcare = sum(e['amount'] for e in expenses_list)
        if expenses_list: highest_healthcare = max(e['amount'] for e in expenses_list)

    return render_template('healthcare.html', healthcare_expenses=expenses_list, 
                           total_healthcare_spending=total_healthcare, highest_healthcare_expense=highest_healthcare)


@app.route('/bill_details')
@login_required
def bill():
    BILL_CATEGORY_MAP = {
        'House Rent & Mortgage': ['Rent/Mortgage'],
        'Electricity Bill':      ['Electricity'], 
        'Water & Gas Bill':      ['Water/Gas'],
        'Internet & Phone':      ['Internet/Phone'] 
    }

    all_names = [n for sub in BILL_CATEGORY_MAP.values() for n in sub]
    bill_cats = Category.query.filter(Category.name.in_(all_names)).all()
    
    cat_name_to_id = {c.name: c.id for c in bill_cats}
    cat_id_to_name = {c.id: c.name for c in bill_cats}
    bill_cat_ids = list(cat_id_to_name.keys())

    category_breakdown = {k: {'total': 0.0, 'expenses': [], 'reminders': [], 'target_id': ''} for k in BILL_CATEGORY_MAP.keys()}

    for section_name, db_names in BILL_CATEGORY_MAP.items():
        primary_name = db_names[0]
        if primary_name in cat_name_to_id:
            category_breakdown[section_name]['target_id'] = cat_name_to_id[primary_name]

    expenses_list = []
    if bill_cat_ids:
        paid_data = Expense.query.filter(Expense.user_id == current_user.id, Expense.category_id.in_(bill_cat_ids)).order_by(Expense.date.desc()).all()
        for exp in paid_data:
            cat_name = cat_id_to_name.get(exp.category_id)
            item = {'date': exp.date, 'amount': float(exp.amount), 'description': exp.description}
            
            for disp, db_names in BILL_CATEGORY_MAP.items():
                if cat_name in db_names:
                    category_breakdown[disp]['expenses'].append(item)
                    category_breakdown[disp]['total'] += float(exp.amount)
                    expenses_list.append(item)
                    break
    
    total_bill = sum(e['amount'] for e in expenses_list)
    highest_bill = max([e['amount'] for e in expenses_list]) if expenses_list else 0

    unpaid = Bill.query.filter_by(user_id=current_user.id, is_paid=False).all()
    today = datetime.now().date()
    
    for b in unpaid:
        days_left = (b.due_date - today).days
        c_name = cat_id_to_name.get(b.category_id, 'Bill')
        for disp, db_names in BILL_CATEGORY_MAP.items():
            if c_name in db_names:
                category_breakdown[disp]['reminders'].append({
                    'id': b.id,
                    'amount': float(b.amount), 
                    'due_date': b.due_date, 
                    'days_left': days_left, 
                    'description': b.description
                })

        if 0 <= days_left <= 5:
            flash(f'Reminder: {c_name} of ₹{b.amount} is due in {days_left} days!', 'warning')
        elif days_left < 0:
            flash(f'Overdue: {c_name} of ₹{b.amount} was due on {b.due_date}!', 'danger')

    return render_template('bill.html', total_bill_spending=total_bill, highest_bill_expense=highest_bill,
                           bill_expenses=expenses_list, category_breakdown=category_breakdown)


# --- Plotly Data API Endpoint (UNCHANGED) ---

@app.route('/api/expense_data', methods=['GET'])
@login_required
def api_expense_data():
    """
    Returns expense data structured for Plotly visualization, including 
    Category and Amount for all expenses, and Monthly Totals.
    """
    
    # 1. Individual Expenses (for scatter/line plot of all spending over time)
    expenses_data = db.session.query(
        Expense.date, 
        Expense.amount, 
        Category.name.label('category_name')
    ).join(Category, Expense.category_id == Category.id)\
    .filter(Expense.user_id == current_user.id)\
    .order_by(Expense.date.asc()).all()
    
    # Format data: Plotly likes separate arrays for X, Y, and a category
    all_dates = [exp.date.strftime('%Y-%m-%d') for exp in expenses_data]
    all_amounts = [float(exp.amount) for exp in expenses_data]
    all_categories = [exp.category_name for exp in expenses_data]
    
    # 2. Monthly Totals (for bar chart visualization)
    month_totals_query = db.session.query(
        func.strftime('%Y-%m', Expense.date), 
        func.sum(Expense.amount)
    ).filter(Expense.user_id == current_user.id)\
    .group_by(func.strftime('%Y-%m', Expense.date))\
    .order_by(func.strftime('%Y-%m', Expense.date).asc()).all()
    
    monthly_x = [m for m, t in month_totals_query]
    monthly_y = [float(t) for m, t in month_totals_query]

    # 3. Category Breakdown (for pie chart visualization)
    category_totals_query = db.session.query(
        Category.name, 
        func.sum(Expense.amount)
    ).join(Expense).filter(Expense.user_id == current_user.id)\
    .group_by(Category.name).all()
    
    category_labels = [n for n, t in category_totals_query]
    category_values = [float(t) for n, t in category_totals_query]

    return jsonify({
        'all_expenses': {
            'dates': all_dates,
            'amounts': all_amounts,
            'categories': all_categories
        },
        'monthly_totals': {
            'months': monthly_x,
            'totals': monthly_y
        },
        'category_totals': {
            'labels': category_labels,
            'values': category_values
        }
    })

if __name__ == '__main__':
    init_db()
    app.run(port=5001, debug=True)