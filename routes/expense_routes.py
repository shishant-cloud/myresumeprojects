from flask import Blueprint

from services.expense_service import (
    delete_expense,
    view_expenses
)

expense_bp = Blueprint(
    "expense",
    __name__
)

expense_bp.route(
    "/view"
)(view_expenses)


expense_bp.route(
    "/delete_expense/<int:expense_id>",
    methods=["POST"]
)(delete_expense)