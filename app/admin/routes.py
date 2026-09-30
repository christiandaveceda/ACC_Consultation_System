from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.orm import aliased
from flask_login import current_user
from ..auth.routes import role_required, log_activity
from ..extensions import db
from ..models import ActivityLog, Consultation, MedicalExpertProfile, StudentProfile, SystemSetting, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
@role_required("SUPER ADMIN")
def dashboard():
    stats = {
        "users": User.query.count(),
        "students": User.query.filter_by(role="STUDENT").count(),
        "experts": User.query.filter_by(role="MEDICAL EXPERT").count(),
        "consultations": Consultation.query.count(),
        "pending": Consultation.query.filter_by(status="Pending").count(),
        "completed": Consultation.query.filter_by(status="Completed").count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(6).all()
    recent_consultations = Consultation.query.order_by(Consultation.created_at.desc()).limit(6).all()
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(8).all()
    return render_template("admin/dashboard.html", stats=stats, recent_users=recent_users, recent_consultations=recent_consultations, recent_logs=recent_logs)

@admin_bp.route("/users")
@role_required("SUPER ADMIN")
def users():
    q = request.args.get("q", "").strip()
    role = request.args.get("role", "")
    status = request.args.get("status", "")
    query = User.query
    if q:
        query = query.filter(or_(User.username.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    if role:
        query = query.filter_by(role=role)
    if status:
        query = query.filter_by(status=status)
    return render_template("admin/users.html", users=query.order_by(User.created_at.desc()).all(), q=q, role=role, status=status)

@admin_bp.route("/users/new", methods=["GET", "POST"])
@role_required("SUPER ADMIN")
def create_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "")
        password = request.form.get("password", "")
        if role not in {"SUPER ADMIN", "MEDICAL EXPERT", "STUDENT"}:
            flash("Invalid role selected.", "danger")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif User.query.filter(or_(User.username == username, User.email == email)).first():
            flash("Username or email already exists.", "danger")
        else:
            user = User(username=username, email=email, role=role, status="Active")
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            if role == "STUDENT":
                user.student_profile = StudentProfile(student_id=request.form.get("student_id", "").strip(), first_name=request.form.get("first_name", "").strip(), middle_name=request.form.get("middle_name", "").strip() or None, last_name=request.form.get("last_name", "").strip(), course=request.form.get("course", "").strip(), year_level=request.form.get("year_level", "").strip(), contact_number=request.form.get("contact_number", "").strip() or None, address=request.form.get("address", "").strip() or None)
            elif role == "MEDICAL EXPERT":
                user.medical_profile = MedicalExpertProfile(first_name=request.form.get("first_name", "").strip(), middle_name=request.form.get("middle_name", "").strip() or None, last_name=request.form.get("last_name", "").strip(), specialization=request.form.get("specialization", "").strip(), contact_number=request.form.get("contact_number", "").strip() or None, professional_information=request.form.get("professional_information", "").strip() or None)
            log_activity("User creation", f"Created {role} account {username}.", current_user.id)
            db.session.commit()
            flash("User account created successfully.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=None)

@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required("SUPER ADMIN")
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return render_template("errors/404.html"), 404
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        duplicate = User.query.filter(User.email == email, User.id != user.id).first()
        if duplicate:
            flash("That email is already used by another account.", "danger")
        else:
            old_role = user.role
            user.email = email
            user.role = request.form.get("role", user.role)
            user.status = request.form.get("status", user.status)
            if old_role == "STUDENT" and user.role != "STUDENT" and user.student_profile:
                db.session.delete(user.student_profile)
                user.student_profile = None
            if old_role == "MEDICAL EXPERT" and user.role != "MEDICAL EXPERT" and user.medical_profile:
                db.session.delete(user.medical_profile)
                user.medical_profile = None
            password = request.form.get("password", "")
            if password:
                if len(password) < 8:
                    flash("Password must contain at least 8 characters.", "danger")
                    return render_template("admin/user_form.html", user=user)
                user.set_password(password)
            if user.role == "STUDENT":
                if not user.student_profile:
                    user.student_profile = StudentProfile(student_id=request.form.get("student_id", "").strip(), first_name=request.form.get("first_name", "").strip(), last_name=request.form.get("last_name", "").strip(), course=request.form.get("course", "").strip(), year_level=request.form.get("year_level", "").strip())
                p = user.student_profile
                for field in ["student_id", "first_name", "middle_name", "last_name", "course", "year_level", "contact_number", "address"]:
                    setattr(p, field, request.form.get(field, "").strip() or None)
            elif user.role == "MEDICAL EXPERT":
                if not user.medical_profile:
                    user.medical_profile = MedicalExpertProfile(first_name=request.form.get("first_name", "").strip(), last_name=request.form.get("last_name", "").strip(), specialization=request.form.get("specialization", "").strip())
                p = user.medical_profile
                for field in ["first_name", "middle_name", "last_name", "specialization", "contact_number", "professional_information"]:
                    setattr(p, field, request.form.get(field, "").strip() or None)
            log_activity("User update", f"Updated user {user.username}; role changed from {old_role} to {user.role}.", current_user.id)
            db.session.commit()
            flash("User updated successfully.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=user)

@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@role_required("SUPER ADMIN")
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return render_template("errors/404.html"), 404
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
    else:
        user.status = "Inactive" if user.status == "Active" else "Active"
        log_activity("Account status", f"Set {user.username} to {user.status}.", current_user.id)
        db.session.commit()
        flash(f"Account is now {user.status.lower()}.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required("SUPER ADMIN")
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return render_template("errors/404.html"), 404
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
    elif user.role == "SUPER ADMIN" and User.query.filter_by(role="SUPER ADMIN", status="Active").count() <= 1:
        flash("The system must retain at least one active Super Admin.", "warning")
    else:
        username = user.username
        db.session.delete(user)
        log_activity("User deletion", f"Deleted user {username}.", current_user.id)
        db.session.commit()
        flash("User deleted successfully.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/students")
@role_required("SUPER ADMIN")
def students():
    q = request.args.get("q", "").strip()
    query = StudentProfile.query.join(User)
    if q:
        query = query.filter(or_(StudentProfile.first_name.ilike(f"%{q}%"), StudentProfile.last_name.ilike(f"%{q}%"), StudentProfile.student_id.ilike(f"%{q}%"), User.username.ilike(f"%{q}%")))
    return render_template("admin/students.html", students=query.order_by(StudentProfile.last_name).all(), q=q)

@admin_bp.route("/medical-experts")
@role_required("SUPER ADMIN")
def experts():
    q = request.args.get("q", "").strip()
    query = MedicalExpertProfile.query.join(User)
    if q:
        query = query.filter(or_(MedicalExpertProfile.first_name.ilike(f"%{q}%"), MedicalExpertProfile.last_name.ilike(f"%{q}%"), MedicalExpertProfile.specialization.ilike(f"%{q}%"), User.username.ilike(f"%{q}%")))
    return render_template("admin/experts.html", experts=query.order_by(MedicalExpertProfile.last_name).all(), q=q)

@admin_bp.route("/consultations")
@role_required("SUPER ADMIN")
def consultations():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    consultation_type = request.args.get("consultation_type", "")
    date_filter = request.args.get("date", "").strip()
    student = aliased(User)
    expert = aliased(User)
    query = Consultation.query.join(student, Consultation.student_id == student.id).outerjoin(expert, Consultation.medical_expert_id == expert.id)
    if q:
        term = f"%{q}%"
        query = query.filter(or_(Consultation.concern.ilike(term), Consultation.consultation_type.ilike(term), student.username.ilike(term), student.email.ilike(term), expert.username.ilike(term), expert.email.ilike(term)))
    if status:
        query = query.filter(Consultation.status == status)
    if consultation_type:
        query = query.filter(Consultation.consultation_type.ilike(f"%{consultation_type}%"))
    if date_filter:
        try:
            query = query.filter(Consultation.preferred_date == datetime.strptime(date_filter, "%Y-%m-%d").date())
        except ValueError:
            flash("Invalid date filter.", "warning")
    return render_template("admin/consultations.html", consultations=query.order_by(Consultation.created_at.desc()).all(), q=q, status=status, consultation_type=consultation_type, date_filter=date_filter)

@admin_bp.route("/activity-logs")
@role_required("SUPER ADMIN")
def activity_logs():
    q = request.args.get("q", "").strip()
    query = ActivityLog.query
    if q:
        query = query.filter(or_(ActivityLog.action.ilike(f"%{q}%"), ActivityLog.description.ilike(f"%{q}%")))
    logs = query.order_by(ActivityLog.timestamp.desc()).limit(300).all()
    return render_template("admin/activity_logs.html", logs=logs, q=q)

@admin_bp.route("/settings", methods=["GET", "POST"])
@role_required("SUPER ADMIN")
def settings():
    if request.method == "POST":
        for key in ["site_name", "allow_registration"]:
            value = request.form.get(key, "")
            setting = SystemSetting.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                db.session.add(SystemSetting(key=key, value=value))
        log_activity("Settings update", "Updated system settings.", current_user.id)
        db.session.commit()
        flash("System settings saved.", "success")
        return redirect(url_for("admin.settings"))
    settings = {s.key: s.value for s in SystemSetting.query.all()}
    return render_template("admin/settings.html", settings=settings)
