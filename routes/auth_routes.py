from flask import Blueprint
from services.auth_service import home, signup

auth_bp = Blueprint('auth', __name__)

auth_bp.route('/')(home)

auth_bp.route(
    '/signup',
    methods=['GET', 'POST']
)(signup)