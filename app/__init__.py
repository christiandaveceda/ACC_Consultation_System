from pathlib import Path
from flask import Flask, render_template
from config import Config
from .extensions import db, login_manager, csrf

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .medical.routes import medical_bp
    from .student.routes import student_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(medical_bp)
    app.register_blueprint(student_bp)

    from . import models
    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_globals():
        from .models import SystemSetting
        settings = {s.key: s.value for s in SystemSetting.query.all()}
        return {"system_settings": settings}

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
