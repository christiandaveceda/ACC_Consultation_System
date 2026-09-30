from app.extensions import db
from app.models import User, StudentProfile

def seed_student(app):
    with app.app_context():
        u=User(username="student",email="student@test.local",role="STUDENT",status="Active");u.set_password("Password123!");u.student_profile=StudentProfile(student_id="S1",first_name="Test",last_name="Student",course="BSIT",year_level="1st Year");db.session.add(u);db.session.commit()

def test_student_cannot_access_admin(app,client):
    seed_student(app)
    client.post('/login',data={'identity':'student','password':'Password123!'})
    r=client.get('/admin/dashboard')
    assert r.status_code==403
