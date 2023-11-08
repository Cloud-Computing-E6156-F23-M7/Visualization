import json, os
from flask import Blueprint, Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import pandas as pd

class DbConfig(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site_mgmt.db'
    SQLALCHEMY_BINDS = {
        'malaria_db': 'sqlite:///malaria.db',
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

app = Flask(__name__)
app.config.from_object(DbConfig)
app.json.sort_keys = False
db = SQLAlchemy(app)
CORS(app)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    isDeleted = db.Column(db.Integer, default=False, nullable=False) # perform soft deletion only
    actions = db.relationship('Action', back_populates='admin') 

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    text = db.Column(db.Text, nullable=False)
    submission_date = db.Column(db.DateTime(timezone=True), default=func.now())
    actions = db.relationship('Action', back_populates='feedback')

class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id'), nullable=False)
    comment = db.Column(db.Text)
    action_date = db.Column(db.DateTime(timezone=True), default=func.now())

    admin = db.relationship('Admin', back_populates='actions')
    feedback = db.relationship('Feedback', back_populates='actions')

class Malaria(db.Model):
    __bind_key__ = 'malaria_db'
    index = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(100))
    year = db.Column(db.Integer)
    cases = db.Column(db.String(100))
    deaths = db.Column(db.String(100))
    cases_median = db.Column(db.Integer)
    cases_min = db.Column(db.Integer)
    cases_max = db.Column(db.Integer)
    deaths_median = db.Column(db.Integer)
    deaths_min = db.Column(db.Integer)
    deaths_max = db.Column(db.Integer)
    who_region = db.Column(db.String(100))

def import_csv():
    malaria_csv_path = os.path.join(
        os.getcwd(), 
        'estimated_numbers.csv'
        )
    df = pd.read_csv(malaria_csv_path)
    
    df_schema = {
        "index": db.Integer,
        "region": db.String(100),
        "year": db.Integer,
        "cases": db.String(100),
        "deaths": db.String(100),
        "cases_median": db.Integer,
        "cases_min": db.Integer,
        "cases_max": db.Integer,
        "deaths_median": db.Integer,
        "deaths_min": db.Integer,
        "deaths_max": db.Integer,
        "who_region": db.String(100),
    }

    df.to_sql(
        Malaria.__tablename__, 
        db.engines['malaria_db'], 
        if_exists='replace',
        index=True,
        dtype=df_schema
        )

# NOTE: This route is needed for the default EB health check route
@app.route('/')  
def home():
    return "ok"

@app.route('/api/malaria/filter_malaria', methods=['POST'])
def filter_malaria():
    page = request.json.get('page', 1) # default is 1 if none is provided

    pagination = Malaria.query.paginate(page=page, per_page=10, error_out=False)
    malaria_data = [{
        'region': malaria.region,
        'year': malaria.year,
        'cases_median': malaria.cases_median,
        'deaths_median': malaria.deaths_median,
        'who_region': malaria.who_region
    } for malaria in pagination.items]

    next_url = f'/api/malaria/filter_malaria?page={pagination.next_num}' if pagination.has_next else None
    prev_url = f'/api/malaria/filter_malaria?page={pagination.prev_num}' if pagination.has_prev else None
    current_url = f'/api/malaria/filter_malaria?page={page}'

    return jsonify({
        'malaria_data': malaria_data,
        'prev_url': prev_url,
        'next_url': next_url,
        'current_url': current_url,
        'total_pages': pagination.pages,
        'total_items': pagination.total
    })

@app.route('/api/malaria/view_malaria')
def view_malaria():
    #TODO: add pagination
    malaria_list = Malaria.query.all()

    malaria_data = [{
        'region': malaria.region,
        'year': malaria.year,
        'cases_median': malaria.cases_median,
        'deaths_median': malaria.deaths_median,
        'who_region': malaria.who_region
    } for malaria in malaria_list]

    return jsonify({'malaria_data': malaria_data})

@app.route('/api/admin/add_admin', methods=['POST'])
def add_admin():
    email = request.json.get('email')
    admin = Admin.query.filter_by(email=email).first()
    
    if not admin:
        new_admin = Admin(email=email)
        db.session.add(new_admin)
        db.session.commit()
        return "Successfully added an admin", 201
    else:
        if admin.isDeleted == True:
            admin.isDeleted = False
            db.session.commit()
            return "Successfully reactivated a deleted admin", 201
        else:
            return "admin already exists and is activated", 400

@app.route('/api/admin/view_admin')
def view_admin():
    admin_list = Admin.query.all()

    admins = [{
        'admin_id': admin.id,
        'email': admin.email,
        'isDeleted': admin.isDeleted
    } for admin in admin_list]

    return jsonify({'admins': admins})

@app.route('/api/admin/deactivate_admin', methods=['POST'])
def deactivate_admin():
    email = request.json.get('email')
    admin = Admin.query.filter_by(email=email).first()

    if admin:
        admin.isDeleted = True
        try:
            db.session.commit()
            return "Successfully deactivated an admin", 201
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error deactivating admin", 501
    else:
        return "Admin not found", 404

@app.route('/api/admin/handle_feedback', methods=['POST'])
def handle_feedback():
    action_data = request.get_json()
    new_action = Action(
        admin_id=action_data['admin_id'], 
        feedback_id=action_data['feedback_id'],
        comment=action_data['comment']
        )

    db.session.add(new_action)
    db.session.commit()

    return "Successfully logged a feedback action", 201

@app.route('/api/feedback/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback_data = request.get_json()
    new_feedback = Feedback(
        name=feedback_data['name'], 
        email=feedback_data['email'],
        text=feedback_data['text']
        )

    db.session.add(new_feedback)
    db.session.commit()

    return "Successfully submitted feedback", 201

@app.route('/api/admin/view_feedback')
def view_feedback():
    feedback_list = db.session.query(Feedback, Action, Admin) \
        .select_from(Feedback) \
        .join(Action, isouter=True) \
        .join(Admin, isouter=True) \
        .all()

    feedback_entries = [{
        'feedback_id': feedback.id,
        'submission_date': feedback.submission_date,
        'name': feedback.name,
        'email': feedback.email,
        'text': feedback.text,
        'admin': admin.email if admin is not None else None,
        'action_date': action.action_date if action is not None else None,
        'action_comment': action.comment if action is not None else None
    } for feedback, action, admin in feedback_list]
    
    return jsonify({'feedback': feedback_entries})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        import_csv()

    app.run(debug=True, port=8080)
