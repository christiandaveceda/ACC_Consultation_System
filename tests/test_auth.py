from app.extensions import db
from app.models import User, StudentProfile

def test_login_and_user_loader(app,client):
    with app.app_context():
        u=User(username="student",email="student@test.local",role="STUDENT",status="Active")
        u.set_password("Password123!")
        u.student_profile=StudentProfile(student_id="S1",first_name="Test",last_name="Student",course="BSIT",year_level="1st Year")
        db.session.add(u);db.session.commit()
    r=client.post('/login',data={'identity':'student','password':'Password123!'},follow_redirects=True)
    assert r.status_code==200
    assert b"Student care space" in r.data

def test_invalid_login(client):
    r=client.post('/login',data={'identity':'nope','password':'bad'})
    assert r.status_code==200
    assert b"Invalid username/email" in r.data
