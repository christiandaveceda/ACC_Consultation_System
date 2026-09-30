from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from ..auth.routes import role_required, log_activity
from ..extensions import db
from ..models import Consultation, ConsultationNote

medical_bp = Blueprint("medical", __name__, url_prefix="/medical")

@medical_bp.route("/dashboard")
@role_required("MEDICAL EXPERT")
def dashboard():
    mine = Consultation.query.filter_by(medical_expert_id=current_user.id)
    stats = {
        "pending": Consultation.query.filter_by(medical_expert_id=current_user.id, status="Pending").count(),
        "accepted": mine.filter_by(status="Accepted").count(),
        "in_progress": mine.filter_by(status="In Progress").count(),
        "completed": mine.filter_by(status="Completed").count(),
    }
    recent = Consultation.query.filter_by(medical_expert_id=current_user.id).order_by(Consultation.created_at.desc()).limit(8).all()
    incoming = Consultation.query.filter_by(status="Pending").filter((Consultation.medical_expert_id == current_user.id) | (Consultation.medical_expert_id.is_(None))).order_by(Consultation.created_at.desc()).limit(8).all()
    return render_template("medical/dashboard.html", stats=stats, recent=recent, incoming=incoming)

@medical_bp.route("/requests")
@role_required("MEDICAL EXPERT")
def requests_list():
    q = request.args.get("q", "").strip()
    query = Consultation.query.filter_by(status="Pending").filter((Consultation.medical_expert_id == current_user.id) | (Consultation.medical_expert_id.is_(None)))
    if q:
        query = query.filter(or_(Consultation.concern.ilike(f"%{q}%"), Consultation.consultation_type.ilike(f"%{q}%")))
    return render_template("medical/requests.html", consultations=query.order_by(Consultation.created_at.desc()).all(), q=q)

@medical_bp.route("/requests/<int:consultation_id>/accept", methods=["POST"])
@role_required("MEDICAL EXPERT")
def accept(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)
    if not consultation or consultation.status != "Pending" or (consultation.medical_expert_id not in (None, current_user.id)):
        flash("That consultation request is no longer available.", "warning")
        return redirect(url_for("medical.requests_list"))
    consultation.medical_expert_id = current_user.id
    consultation.status = "Accepted"
    log_activity("Consultation acceptance", f"Accepted consultation #{consultation.id}.", current_user.id)
    db.session.commit()
    flash("Consultation accepted.", "success")
    return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))

@medical_bp.route("/requests/<int:consultation_id>/reject", methods=["POST"])
@role_required("MEDICAL EXPERT")
def reject(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)
    if not consultation or consultation.status != "Pending" or (consultation.medical_expert_id not in (None, current_user.id)):
        flash("That consultation request is no longer available.", "warning")
        return redirect(url_for("medical.requests_list"))
    consultation.medical_expert_id = current_user.id
    consultation.status = "Rejected"
    log_activity("Consultation rejection", f"Rejected consultation #{consultation.id}.", current_user.id)
    db.session.commit()
    flash("Consultation rejected.", "info")
    return redirect(url_for("medical.requests_list"))

@medical_bp.route("/consultations")
@role_required("MEDICAL EXPERT")
def consultations():
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    query = Consultation.query.filter_by(medical_expert_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    if q:
        query = query.filter(or_(Consultation.concern.ilike(f"%{q}%"), Consultation.consultation_type.ilike(f"%{q}%")))
    return render_template("medical/consultations.html", consultations=query.order_by(Consultation.created_at.desc()).all(), status=status, q=q)

@medical_bp.route("/history")
@role_required("MEDICAL EXPERT")
def history():
    consultations = Consultation.query.filter_by(medical_expert_id=current_user.id, status="Completed").order_by(Consultation.updated_at.desc()).all()
    return render_template("medical/history.html", consultations=consultations)

@medical_bp.route("/consultations/<int:consultation_id>", methods=["GET", "POST"])
@role_required("MEDICAL EXPERT")
def consultation_detail(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)
    if not consultation or consultation.medical_expert_id != current_user.id:
        flash("Consultation not found or not assigned to you.", "danger")
        return redirect(url_for("medical.consultations"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "start" and consultation.status == "Accepted":
            consultation.status = "In Progress"
            log_activity("Consultation status", f"Started consultation #{consultation.id}.", current_user.id)
        elif action == "complete" and consultation.status in {"Accepted", "In Progress"}:
            notes = request.form.get("notes", "").strip()
            recommendations = request.form.get("recommendations", "").strip()
            if not notes:
                flash("Please enter consultation notes before completing.", "danger")
                return render_template("medical/consultation_detail.html", consultation=consultation)
            consultation.notes.append(ConsultationNote(medical_expert_id=current_user.id, notes=notes, recommendations=recommendations or None))
            consultation.status = "Completed"
            log_activity("Consultation completion", f"Completed consultation #{consultation.id}.", current_user.id)
        elif action == "note" and consultation.status in {"Accepted", "In Progress"}:
            notes = request.form.get("notes", "").strip()
            recommendations = request.form.get("recommendations", "").strip()
            if notes:
                consultation.notes.append(ConsultationNote(medical_expert_id=current_user.id, notes=notes, recommendations=recommendations or None))
                log_activity("Consultation note", f"Added notes to consultation #{consultation.id}.", current_user.id)
            else:
                flash("Notes cannot be empty.", "danger")
                return render_template("medical/consultation_detail.html", consultation=consultation)
        else:
            flash("That action is not valid for the current consultation status.", "warning")
            return render_template("medical/consultation_detail.html", consultation=consultation)
        db.session.commit()
        flash("Consultation updated successfully.", "success")
        return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))
    return render_template("medical/consultation_detail.html", consultation=consultation)

@medical_bp.route("/profile", methods=["GET", "POST"])
@role_required("MEDICAL EXPERT")
def profile():
    user = current_user
    p = user.medical_profile
    if request.method == "POST":
        user.email = request.form.get("email", "").strip().lower()
        for field in ["first_name", "middle_name", "last_name", "specialization", "contact_number", "professional_information"]:
            setattr(p, field, request.form.get(field, "").strip() or None)
        new_password = request.form.get("password", "")
        if new_password:
            if len(new_password) < 8:
                flash("New password must contain at least 8 characters.", "danger")
                return render_template("medical/profile.html", profile=p)
            user.set_password(new_password)
        log_activity("Profile update", f"Medical expert {user.username} updated their profile.", user.id)
        db.session.commit()
        flash("Profile updated.", "success")
    return render_template("medical/profile.html", profile=p)
