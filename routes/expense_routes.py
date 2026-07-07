from flask import Blueprint

from services.expense_service import (
    view,
    delete_expense
)

expense_bp = Blueprint(
    "expense",
    __name__
)

expense_bp.route(
    "/view"
)(view)

expense_bp.route(
    "/delete_expense/<int:expense_id>",
    methods=["POST"]
)(delete_expense)