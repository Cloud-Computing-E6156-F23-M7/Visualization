import json, os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import requests
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
    comment = db.Column(db.Text, nullable=False)
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
    fips = db.Column(db.String(2))
    iso = db.Column(db.String(3))
    iso2 = db.Column(db.String(2))
    land_area_kmsq_2012 = db.Column(db.Integer)
    languages_en_2012 = db.Column(db.String(100))
    who_region = db.Column(db.String(100))
    world_bank_income_group = db.Column(db.String(100))

    country = db.relationship('Country', back_populates='malaria')

class Country(db.Model):
    __bind_key__ = 'malaria_db'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.JSON)
    cca2 = db.Column(db.String(2))
    cca3 = db.Column(db.String(3), db.ForeignKey('malaria.iso'))
    currencies = db.Column(db.JSON)
    capital = db.Column(db.JSON)
    capitalInfo = db.Column(db.JSON)
    latlng = db.Column(db.JSON)
    area = db.Column(db.Integer)
    population = db.Column(db.Integer)
    timezones = db.Column(db.JSON)
    flags = db.Column(db.JSON)

    malaria = db.relationship('Malaria', back_populates='country')

def import_malaria_csv():
    malaria_csv_path = os.path.join(
        os.getcwd(), 
        'estimated_numbers.csv'
        )
    df = pd.read_csv(malaria_csv_path)
    
    df_schema = {
        'index': db.Integer,
        'region': db.String(100),
        'year': db.Integer,
        'cases': db.String(100),
        'deaths': db.String(100),
        'cases_median': db.Integer,
        'cases_min': db.Integer,
        'cases_max': db.Integer,
        'deaths_median': db.Integer,
        'deaths_min': db.Integer,
        'deaths_max': db.Integer,
        'fips': db.String(2),
        'iso': db.String(3),    # Assume uppercase
        'iso2': db.String(2),
        'land_area_kmsq_2012': db.Integer,
        'languages_en_2012': db.String(100),
        'who_region': db.String(100),
        'world_bank_income_group': db.String(100)
    }

    df.to_sql(
        Malaria.__tablename__, 
        db.engines['malaria_db'], 
        if_exists='replace',
        index=True,
        dtype=df_schema
        )

def import_country_data():
    if Country.query.first():
        return  # Do nothing
    
    api_url = 'https://restcountries.com/v3.1/alpha?codes='
    fields = '&fields=name,cca2,cca3,currencies,capital,capitalInfo,latlng,area,population,timezones,flags'
    iso_codes = Malaria.query.with_entities(Malaria.iso).distinct().all()
    iso_codes_str = ','.join([iso[0] for iso in iso_codes])

    try:
        response = requests.get(api_url + iso_codes_str + fields)
        
        if response.status_code == 200:
            api_data = response.json()

            for country in api_data:
                new_country = Country(
                    name=country['name'],
                    cca2=country['cca2'],
                    cca3=country['cca3'],   # Assume uppercase
                    currencies=country['currencies'],
                    capital=country['capital'],
                    capitalInfo=country['capitalInfo'],
                    latlng=country['latlng'],
                    area=country['area'],
                    population=country['population'],
                    timezones=country['timezones'],
                    flags=country['flags']
                )
                db.session.add(new_country)
                db.session.commit()
        else:
            return jsonify({
                'error': f'Error fetching country data from API. Status code: {response.status_code}'
                }), 501 

    except requests.RequestException as e:
        return jsonify({'error': f'Error making API request: {str(e)}'}), 501

# NOTE: This route is needed for the default EB health check route
@app.route('/')  
def home():
    return "Ok"

@app.route('/api/country/')
def get_all_country():
    country_list = Country.query.all()

    countries = [{
        'name': country.name,
        'cca2': country.cca2,
        'cca3': country.cca3,
        'currencies': country.currencies,
        'capital': country.capital,
        'capitalInfo': country.capitalInfo,
        'latlng': country.latlng,
        'area': country.area,
        'population': country.population,
        'timezones': country.timezones,
        'flags': country.flags
    } for country in country_list]

    return jsonify(countries)

@app.route('/api/malaria/filter')
def filter_malaria():
    region = request.args.get('region')  # takes region from query parameters
    year = request.args.get('year')  # takes year from query parameters
    who_region = request.args.get('who_region')
    page = request.args.get('page', 1, type=int)  # takes page number from query parameters
    per_page = request.args.get('per_page', 10, type=int)
    iso = request.args.get('iso')

    #query = Malaria.query

    query = db.session.query(Malaria, Country) \
        .select_from(Malaria) \
        .join(Country, isouter=True)
    url = url = f'/api/malaria/filter?'

    if region:
        #query = query.filter(Malaria.region.ilike(f'%{region}%'))
        region_list = region.lower().split(',')
        query = query.filter(func.lower(Malaria.region).in_(region_list))
        url += '&' if url[-1] != '?' else ''
        url += f'region={region}'
    if year:
        #query = query.filter(Malaria.year == year)
        year_list = year.split(',')
        query = query.filter(Malaria.year.in_(year_list))
        url += '&' if url[-1] != '?' else ''
        url += f'year={year}'
    if who_region:
        who_region_list = who_region.lower().split(',')
        query = query.filter(func.lower(Malaria.who_region).in_(who_region_list))
        url += '&' if url[-1] != '?' else ''
        url += f'who_region={who_region}'
    if iso:
        iso_list = iso.upper().split(',')
        query = query.filter(Malaria.iso.in_(iso_list))
        url += '&' if url[-1] != '?' else ''
        url += f'iso={iso}'

    # paginates the filtered query
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    malaria_data = [{
        'region': malaria.region,
        'year': malaria.year,
        'cases_median': malaria.cases_median,
        'deaths_median': malaria.deaths_median,
        'land_area_kmsq_2012': malaria.land_area_kmsq_2012,
        'languages_en_2012': malaria.languages_en_2012,
        'who_region': malaria.who_region,
        'world_bank_income_group': malaria.world_bank_income_group,
        'name': country.name,
        'latlng': country.latlng,
        'currencies': country.currencies,
        'capital': country.capital,
        'capitalInfo': country.capitalInfo,
        'population': country.population,
        'flags': country.flags
    } for malaria, country in pagination.items]

    url += '&' if url[-1] != '?' else ''
    next_url = url + f'page={pagination.next_num}&per_page={pagination.per_page}'
    prev_url = url + f'page={pagination.prev_num}&per_page={pagination.per_page}'

    return jsonify({
        'malaria_data': malaria_data,
        'previous_page': prev_url,
        'next_page': next_url,
        'total_pages': pagination.pages,
        'total_items': pagination.total
    })

@app.route('/api/malaria/')
def get_all_malaria():
    malaria_list = db.session.query(Malaria, Country) \
        .select_from(Malaria) \
        .join(Country, isouter=True) \
        .all()

    malaria_data = [{
        'region': malaria.region,
        'year': malaria.year,
        'cases_median': malaria.cases_median,
        'deaths_median': malaria.deaths_median,
        'land_area_kmsq_2012': malaria.land_area_kmsq_2012,
        'languages_en_2012': malaria.languages_en_2012,
        'who_region': malaria.who_region,
        'world_bank_income_group': malaria.world_bank_income_group,
        'name': country.name,
        'latlng': country.latlng,
        'currencies': country.currencies,
        'capital': country.capital,
        'capitalInfo': country.capitalInfo,
        'population': country.population,
        'flags': country.flags
    } for malaria, country in malaria_list]

    return jsonify(malaria_data)

@app.route('/api/admin/', methods=['GET'])
def get_all_admin():
    admin_list = Admin.query.all()

    admins = [{
        'admin_id': admin.id,
        'email': admin.email,
        'isDeleted': admin.isDeleted
    } for admin in admin_list]

    return jsonify(admins)

@app.route('/api/admin/<int:admin_id>/', methods=['GET'])
def get_admin(admin_id):
    admin = Admin.query.filter_by(id=admin_id).first()

    if not admin:
        return "Admin not found", 404
    if admin.isDeleted == True:
        return "Admin not activated", 400

    admin_dic = {
        'admin_id': admin.id,
        'email': admin.email,
        'isDeleted': admin.isDeleted
    }
    
    return jsonify(admin_dic)

@app.route('/api/admin/', methods=['POST'])
def add_admin():
    email = request.json.get('email')
    
    if email is None:
        return "Email cannot be null", 400
    
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
            return "Successfully reactivated a deleted admin"
        else:
            return "admin already exists and is activated", 400

@app.route('/api/admin/<int:admin_id>/', methods=['DELETE'])
def delete_admin(admin_id):
    admin = Admin.query.filter_by(id=admin_id).first()

    if admin:
        admin.isDeleted = True
        try:
            db.session.commit()
            return "Successfully deactivated an admin"
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error deactivating an admin", 501
    else:
        return "Admin not found", 404

@app.route('/api/admin/<int:admin_id>/', methods=['PUT'])
def update_admin(admin_id):
    admin = Admin.query.filter_by(id=admin_id).first()
    new_email = request.json.get('email')

    if admin:
        if not new_email:
            if admin.isDeleted == True:
                admin.isDeleted = False
                db.session.commit()
                return "Successfully reactivated a deleted admin"
            else:
                return "Email cannot be null", 400
        if Admin.query.filter_by(email=new_email).first():
            return "Email already exists", 400
        admin.email = new_email
        if admin.isDeleted == True:
            admin.isDeleted = False
            db.session.commit()
            return "Successfully activated an admin and updated the email"
        else:
            db.session.commit()
            return "Successfully updated an admin email"
    else:
        return "Admin not found", 404

@app.route('/api/admin/<int:admin_id>/handle_feedback/<int:feedback_id>/', methods=['POST'])
def handle_feedback(admin_id, feedback_id):
    comment = request.json.get('comment')
    
    if not comment:
        return "Comment cannot be null", 400

    admin = Admin.query.filter_by(id=admin_id).first()

    if not (admin and Feedback.query.filter_by(id=feedback_id).first()):
        return "admin_id or feedback_id not found", 404

    if admin.isDeleted == True:
        return "admin is deactivated", 400

    new_action = Action(
        admin_id=admin_id,
        feedback_id=feedback_id,
        comment=comment
        )

    db.session.add(new_action)
    db.session.commit()

    return "Successfully logged a feedback action", 201

@app.route('/api/feedback/submit_feedback/', methods=['POST'])
def submit_feedback():
    feedback_data = request.get_json()

    feedback_text = feedback_data.get('text')

    if feedback_text is None:
        return "Text cannot be null", 400

    new_feedback = Feedback(
        name=feedback_data.get('name'), 
        email=feedback_data.get('email'),
        text=feedback_text
        )

    db.session.add(new_feedback)
    db.session.commit()

    return "Successfully submitted feedback", 201

@app.route('/api/admin/get_feedback/')
def get_all_feedback():
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
        'actioned_by': admin.email if admin else None,
        'action_date': action.action_date if action else None,
        'action_comment': action.comment if action else None
    } for feedback, action, admin in feedback_list]
    
    return jsonify(feedback_entries)

@app.route('/api/admin/get_action/')
def get_all_action():
    action_list = db.session.query(Action, Feedback, Admin) \
        .select_from(Action) \
        .join(Feedback, isouter=True) \
        .join(Admin, isouter=True) \
        .all()

    actions = [{
        'action_id': action.id,
        'admin': admin.email if admin else None,
        'action_date': action.action_date,
        'action_comment': action.comment,
        'feedback_id': feedback.id if feedback else None,
        'feedback_submission_date': feedback.submission_date if feedback else None,
        'feedback_name': feedback.name if feedback else None,
        'feedback_email': feedback.email if feedback else None,
        'feedback_text': feedback.text if feedback else None
    } for action, feedback, admin in action_list]
    
    return jsonify(actions)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        import_malaria_csv()
        import_country_data()

    app.run(debug=True, port=8080)
