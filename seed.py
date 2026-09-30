from datetime import date, time, timedelta
from app import create_app
from app.extensions import db
from app.models import User, StudentProfile, MedicalExpertProfile, Consultation, ConsultationNote, ActivityLog, SystemSetting

app = create_app()

def add_user(username,email,password,role,profile=None):
    user=User(username=username,email=email,role=role,status="Active")
    user.set_password(password)
    if role=="STUDENT":
        user.student_profile=StudentProfile(**profile)
    elif role=="MEDICAL EXPERT":
        user.medical_profile=MedicalExpertProfile(**profile)
    db.session.add(user)
    db.session.flush()
    return user

with app.app_context():
    db.drop_all()
    db.create_all()
    admin=add_user("admin","admin@acc.local","Admin123!","SUPER ADMIN")
    expert1=add_user("dr.alex","alex@acc.local","Expert123!","MEDICAL EXPERT",dict(first_name="Alex",middle_name="M",last_name="Reyes",specialization="General Medicine",contact_number="09170000001",professional_information="Fictional development account."))
    expert2=add_user("dr.jamie","jamie@acc.local","Expert123!","MEDICAL EXPERT",dict(first_name="Jamie",middle_name="L",last_name="Santos",specialization="Student Wellness",contact_number="09170000002",professional_information="Fictional development account."))
    students=[]
    data=[("student1","student1@acc.local","S1001","Ava","Dela Cruz","BS Information Technology","1st Year"),("student2","student2@acc.local","S1002","Ben","Garcia","BS Information Technology","2nd Year"),("student3","student3@acc.local","S1003","Cara","Mendoza","BS Information Technology","3rd Year"),("student4","student4@acc.local","S1004","Dan","Ramos","BS Information Technology","4th Year"),("student5","student5@acc.local","S1005","Ella","Torres","BS Information Technology","2nd Year")]
    for i,(u,e,sid,fn,ln,course,year) in enumerate(data,1):
        students.append(add_user(u,e,"Student123!","STUDENT",dict(student_id=sid,first_name=fn,middle_name=None,last_name=ln,course=course,year_level=year,contact_number=f"09170000{i:04d}",address="Fictional development address")))
    consultations=[Consultation(student_id=students[0].id,medical_expert_id=expert1.id,consultation_type="General Wellness",concern="I would like a routine wellness consultation.",preferred_date=date.today()+timedelta(days=2),preferred_time=time(9,0),status="Completed"),Consultation(student_id=students[1].id,medical_expert_id=expert2.id,consultation_type="Student Wellness",concern="I would like to discuss study-related wellbeing concerns.",preferred_date=date.today()+timedelta(days=3),preferred_time=time(10,30),status="In Progress"),Consultation(student_id=students[2].id,medical_expert_id=None,consultation_type="Nutrition",concern="I would like general guidance for healthy student meals.",preferred_date=date.today()+timedelta(days=4),preferred_time=time(13,0),status="Pending"),Consultation(student_id=students[3].id,medical_expert_id=expert1.id,consultation_type="Physical Health",concern="I would like to schedule a non-emergency health consultation.",preferred_date=date.today()+timedelta(days=5),preferred_time=time(14,0),status="Accepted"),Consultation(student_id=students[4].id,medical_expert_id=None,consultation_type="General Wellness",concern="I want to ask about maintaining healthy routines.",preferred_date=date.today()+timedelta(days=6),preferred_time=time(15,0),status="Pending")]
    db.session.add_all(consultations)
    db.session.flush()
    db.session.add(ConsultationNote(consultation_id=consultations[0].id,medical_expert_id=expert1.id,notes="Fictional sample consultation note.",recommendations="Continue healthy routines and seek appropriate professional care when needed."))
    db.session.add_all([SystemSetting(key="site_name",value="ACC Consultation System"),SystemSetting(key="allow_registration",value="1")])
    db.session.add(ActivityLog(user_id=admin.id,action="Seed",description="Development database seeded with fictional sample accounts."))
    db.session.commit()
    print("Database seeded successfully.")
    print("Admin: admin@acc.local / Admin123!")
    print("Experts: alex@acc.local or jamie@acc.local / Expert123!")
    print("Students: student1@acc.local ... student5@acc.local / Student123!")
