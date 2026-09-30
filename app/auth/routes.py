from functools import wraps
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from . import __name__
from ..extensions import db
from ..models import ActivityLog, MedicalExpertProfile, StudentProfile, User

auth_bp = Blueprint("auth", __name__)

def log_activity(action, description, user_id=None):
    db.session.add(ActivityLog(user_id=user_id, action=action, description=description))

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles or not current_user.is_active:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator

@auth_bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard_redirect"))
    return redirect(url_for("auth.login"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard_redirect"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(or_(User.username == identity, User.email == identity.lower())).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=False)
            log_activity("Login", f"User {user.username} logged in.", user.id)
            db.session.commit()
            flash("Welcome back! You are now signed in.", "success")
            return redirect(url_for("auth.dashboard_redirect"))
        flash("Invalid username/email, password, or inactive account.", "danger")
    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard_redirect"))
    if request.method == "POST":
        from ..models import SystemSetting
        registration = SystemSetting.query.filter_by(key="allow_registration").first()
        if registration and registration.value != "1":
            flash("Student registration is currently disabled by the administrator.", "warning")
            return redirect(url_for("auth.login"))
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        student_id = request.form.get("student_id", "").strip()
        first_name = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        course = request.form.get("course", "").strip()
        year_level = request.form.get("year_level", "").strip()
        if not all([username, email, password, confirm, student_id, first_name, last_name, course, year_level]):
            flash("Please complete all required fields.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash("Username or email is already registered.", "danger")
        elif StudentProfile.query.filter_by(student_id=student_id).first():
            flash("Student ID is already registered.", "danger")
        else:
            user = User(username=username, email=email, role="STUDENT", status="Active")
            user.set_password(password)
            user.student_profile = StudentProfile(student_id=student_id, first_name=first_name, middle_name=middle_name or None, last_name=last_name, course=course, year_level=year_level, contact_number=request.form.get("contact_number", "").strip() or None, address=request.form.get("address", "").strip() or None)
            db.session.add(user)
            db.session.flush()
            log_activity("Registration", f"Student account {username} was registered.", user.id)
            db.session.commit()
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html")

@auth_bp.route("/dashboard")
@login_required
def dashboard_redirect():
    if not current_user.is_active:
        logout_user()
        flash("Your account is inactive. Please contact the administrator.", "danger")
        return redirect(url_for("auth.login"))
    if current_user.role == "SUPER ADMIN":
        return redirect(url_for("admin.dashboard"))
    if current_user.role == "MEDICAL EXPERT":
        return redirect(url_for("medical.dashboard"))
    if current_user.role == "STUDENT":
        return redirect(url_for("student.dashboard"))
    logout_user()
    abort(403)

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    user_id = current_user.id
    username = current_user.username
    log_activity("Logout", f"User {username} logged out.", user_id)
    db.session.commit()
    logout_user()
    flash("You have been logged out safely.", "success")
    return redirect(url_for("auth.login"))

from ..extensions import login_manager
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


