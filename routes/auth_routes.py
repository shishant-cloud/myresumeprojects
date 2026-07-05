from flask import Blueprint

from services.auth_service import (
    home,
    signup,
    login,
    logout
)

auth_bp = Blueprint(
    "auth",
    __name__
)

# Home
auth_bp.route("/")(home)

# Signup
auth_bp.route(
    "/signup",
    methods=["GET", "POST"]
)(signup)

# Login
auth_bp.route(
    "/login",
    methods=["GET", "POST"]
)(login)

# Logout
auth_bp.route("/logout")(logout)