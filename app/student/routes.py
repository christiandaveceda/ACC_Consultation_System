from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from ..auth.routes import role_required, log_activity
from ..extensions import db
from ..models import Consultation, MedicalExpertProfile, User

student_bp = Blueprint("student", __name__, url_prefix="/student")

@student_bp.route("/dashboard")
@role_required("STUDENT")
def dashboard():
    mine = Consultation.query.filter_by(student_id=current_user.id)
    stats = {
        "total": mine.count(),
        "pending": mine.filter_by(status="Pending").count(),
        "upcoming": mine.filter(Consultation.status.in_(["Accepted", "In Progress"])).count(),
        "completed": mine.filter_by(status="Completed").count(),
    }
    recent = mine.order_by(Consultation.created_at.desc()).limit(8).all()
    return render_template("student/dashboard.html", stats=stats, recent=recent)

@student_bp.route("/consultations/new", methods=["GET", "POST"])
@role_required("STUDENT")
def request_consultation():
    experts = MedicalExpertProfile.query.join(User).filter(User.status == "Active").order_by(MedicalExpertProfile.last_name).all()
    if request.method == "POST":
        try:
            preferred_date = datetime.strptime(request.form.get("preferred_date", ""), "%Y-%m-%d").date()
            preferred_time = datetime.strptime(request.form.get("preferred_time", ""), "%H:%M").time()
        except ValueError:
            flash("Please provide a valid preferred date and time.", "danger")
            return render_template("student/request.html", experts=experts)
        consultation_type = request.form.get("consultation_type", "").strip()
        concern = request.form.get("concern", "").strip()
        expert_id = request.form.get("medical_expert_id", "").strip()
        if not consultation_type or not concern:
            flash("Consultation type and concern are required.", "danger")
        elif len(concern) < 10:
            flash("Please provide a little more detail about your concern.", "danger")
        else:
            expert = db.session.get(User, int(expert_id)) if expert_id else None
            if expert and (expert.role != "MEDICAL EXPERT" or not expert.is_active):
                expert = None
            consultation = Consultation(student_id=current_user.id, medical_expert_id=expert.id if expert else None, consultation_type=consultation_type, concern=concern, preferred_date=preferred_date, preferred_time=preferred_time, status="Pending")
            db.session.add(consultation)
            db.session.flush()
            log_activity("Consultation request", f"Submitted consultation #{consultation.id}.", current_user.id)
            db.session.commit()
            flash("Consultation request submitted successfully.", "success")
            return redirect(url_for("student.consultations"))
    return render_template("student/request.html", experts=experts)

@student_bp.route("/consultations")
@role_required("STUDENT")
def consultations():
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    query = Consultation.query.filter_by(student_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    if q:
        query = query.filter(or_(Consultation.concern.ilike(f"%{q}%"), Consultation.consultation_type.ilike(f"%{q}%")))
    return render_template("student/consultations.html", consultations=query.order_by(Consultation.created_at.desc()).all(), status=status, q=q)

@student_bp.route("/history")
@role_required("STUDENT")
def history():
    consultations = Consultation.query.filter_by(student_id=current_user.id).filter(Consultation.status.in_(["Completed", "Rejected", "Cancelled"])).order_by(Consultation.updated_at.desc()).all()
    return render_template("student/history.html", consultations=consultations)

@student_bp.route("/consultations/<int:consultation_id>")
@role_required("STUDENT")
def consultation_detail(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)
    if not consultation or consultation.student_id != current_user.id:
        flash("Consultation not found.", "danger")
        return redirect(url_for("student.consultations"))
    return render_template("student/consultation_detail.html", consultation=consultation)

@student_bp.route("/consultations/<int:consultation_id>/cancel", methods=["POST"])
@role_required("STUDENT")
def cancel(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)
    if not consultation or consultation.student_id != current_user.id:
        flash("Consultation not found.", "danger")
    elif consultation.status != "Pending":
        flash("Only pending requests can be cancelled.", "warning")
    else:
        consultation.status = "Cancelled"
        log_activity("Consultation cancellation", f"Cancelled consultation #{consultation.id}.", current_user.id)
        db.session.commit()
        flash("Consultation request cancelled.", "success")
    return redirect(url_for("student.consultations"))

@student_bp.route("/profile", methods=["GET", "POST"])
@role_required("STUDENT")
def profile():
    user = current_user
    p = user.student_profile
    if request.method == "POST":
        user.email = request.form.get("email", "").strip().lower()
        for field in ["first_name", "middle_name", "last_name", "student_id", "course", "year_level", "contact_number", "address"]:
            setattr(p, field, request.form.get(field, "").strip() or None)
        new_password = request.form.get("password", "")
        if new_password:
            if len(new_password) < 8:
                flash("New password must contain at least 8 characters.", "danger")
                return render_template("student/profile.html", profile=p)
            user.set_password(new_password)
        log_activity("Profile update", f"Student {user.username} updated their profile.", user.id)
        db.session.commit()
        flash("Profile updated.", "success")
    return render_template("student/profile.html", profile=p)
