import pytest
from app import create_app
from config import TestingConfig
from app.extensions import db
from app.models import User

@pytest.fixture()
def app():
    app=create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

def make_user(role="STUDENT"):
    u=User(username=role.lower().replace(' ','_'),email=f"{role.lower().replace(' ','_')}@test.local",role=role,status="Active")
    u.set_password("Password123!")
    return u
