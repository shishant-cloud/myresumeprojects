from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request
)

from flask_login import (
    login_required,
    current_user
)

from extension import db

from models.models import (
    Expense,
    Category
)


def view_expenses():
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
