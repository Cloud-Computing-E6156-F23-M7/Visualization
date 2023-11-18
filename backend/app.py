import json, os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import requests
import pandas as pd

### Set up the databases ###

class DbConfig(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///malaria.db'
    SQLALCHEMY_BINDS = {
        'malaria_db': SQLALCHEMY_DATABASE_URI  # default bind
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

app = Flask(__name__)
app.config.from_object(DbConfig)
app.json.sort_keys = False
db = SQLAlchemy(app)
CORS(app)

class Malaria(db.Model):
    __bind_key__ = 'malaria_db'
    id = db.Column(db.Integer, primary_key=True)
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
    iso = db.Column(db.String(3))   # assume uppercase
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
    cca3 = db.Column(db.String(3), db.ForeignKey('malaria.iso'))    # assume uppercase
    currencies = db.Column(db.JSON)
    capital = db.Column(db.JSON)
    capitalInfo = db.Column(db.JSON)
    latlng = db.Column(db.JSON)
    area = db.Column(db.Integer)
    population = db.Column(db.Integer)
    timezones = db.Column(db.JSON)
    flags = db.Column(db.JSON)

    malaria = db.relationship('Malaria', back_populates='country')

### Import data to the databases ###

def import_malaria_csv():
    malaria_csv_path = os.path.join(
        os.getcwd(), 
        'estimated_numbers.csv'
        )
    df = pd.read_csv(malaria_csv_path)
    
    for index, row in df.iterrows():
        malaria = Malaria(
            region=row.get('region'),
            year=row.get('year'),
            cases=row.get('cases'),
            deaths=row.get('deaths'),
            cases_median=row.get('cases_median'),
            cases_min=row.get('cases_min'),
            cases_max=row.get('cases_max'),
            deaths_median=row.get('deaths_median'),
            deaths_min=row.get('deaths_min'),
            deaths_max=row.get('deaths_max'),
            fips=row.get('fips'),
            iso=row.get('iso'),   # assume uppercase
            iso2=row.get('iso2'),
            land_area_kmsq_2012=row.get('land_area_kmsq_2012'),
            languages_en_2012=row.get('languages_en_2012'),
            who_region=row.get('who_region'),
            world_bank_income_group=row.get('world_bank_income_group')
        )
        db.session.add(malaria)

    try:
        db.session.commit()
    except (IntegrityError, SQLAlchemyError):
        db.session.rollback()
        return "Error importing malaria data to the database"

def import_country_data():
    if Country.query.first():
        return  "Country data already exists in the database"
    
    api_url = 'https://restcountries.com/v3.1/alpha?codes='
    fields = '&fields=name,cca2,cca3,currencies,capital,capitalInfo,latlng,area,population,timezones,flags'
    iso_list = db.session.query(Malaria.iso).distinct().all()
    iso_list_str = ','.join([iso[0] for iso in iso_list])

    try:
        response = requests.get(api_url + iso_list_str + fields)
        
        if response.status_code == 200:
            api_data = response.json()

            for country in api_data:
                new_country = Country(
                    name=country.get('name'),
                    cca2=country.get('cca2'),
                    cca3=country.get('cca3'),   # assume uppercase
                    currencies=country.get('currencies'),
                    capital=country.get('capital'),
                    capitalInfo=country.get('capitalInfo'),
                    latlng=country.get('latlng'),
                    area=country.get('area'),
                    population=country.get('population'),
                    timezones=country.get('timezones'),
                    flags=country.get('flags')
                )
                db.session.add(new_country)
                
            try:
                db.session.commit()
            except (IntegrityError, SQLAlchemyError):
                db.session.rollback()
                return "Error importing country data to the database"
        else:
            return jsonify({
                'error': f'Error fetching country data from API. Status code: {response.status_code}'
                })
    
    except requests.RequestException as e:
        return jsonify({'error': f'Error making API request: {str(e)}'})

# NOTE: This route is needed for the default EB health check route
@app.route('/')  
def home():
    return "Ok"

### Reset database ###

@app.route('/api/reset/malaria/', methods=['PUT'])
def reset_malaria_db():
    engine = db.get_engine(app, bind='malaria_db')
    if engine:
        metadata = db.MetaData()
        metadata.reflect(bind=engine)
        metadata.drop_all(bind=engine)
        metadata.create_all(bind=engine)
        import_malaria_csv()
        import_country_data()
        return "Successfully reset the malaria database"
    else:
        return "Error resetting the malaria database", 501

### Country and Malaria resources ###

@app.route('/api/country/')
def get_country():
    iso = request.args.get('iso')

    query = Country.query

    if iso:
        iso_list = iso.upper().split(',')
        query = query.filter(Country.cca3.in_(iso_list))

    countries = [{
        'id': country.id,
        'name': country.name,
        'iso2': country.cca2,
        'iso': country.cca3,
        'currencies': country.currencies,
        'capital': country.capital,
        'capitalInfo': country.capitalInfo,
        'latlng': country.latlng,
        'area': country.area,
        'population': country.population,
        'timezones': country.timezones,
        'flags': country.flags
    } for country in query]

    return jsonify(countries)

@app.route('/api/malaria/filter')
def filter_malaria():
    region = request.args.get('region')  # takes region from query parameters
    year = request.args.get('year')  # takes year from query parameters
    who_region = request.args.get('who_region')
    page = request.args.get('page', 1, type=int)  # takes page number from query parameters
    per_page = request.args.get('per_page', 10, type=int)
    iso = request.args.get('iso')

    query = db.session.query(Malaria, Country) \
        .select_from(Malaria) \
        .join(Country, isouter=True)
    url = url = f'/api/malaria/filter?'

    if region:
        region_list = region.lower().split(',')
        query = query.filter(func.lower(Malaria.region).in_(region_list))
        url += '&' if url[-1] != '?' else ''
        url += f'region={region}'
    if year:
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
        'id': malaria.id,
        'region': malaria.region,
        'iso': malaria.iso,
        'year': malaria.year,
        'cases_median': malaria.cases_median,
        'deaths_median': malaria.deaths_median,
        'land_area_kmsq_2012': malaria.land_area_kmsq_2012,
        'languages_en_2012': malaria.languages_en_2012,
        'who_region': malaria.who_region,
        'world_bank_income_group': malaria.world_bank_income_group,
        'name': country.name if country else None,
        'latlng': country.latlng if country else None,
        'currencies': country.currencies if country else None,
        'capital': country.capital if country else None,
        'capitalInfo': country.capitalInfo if country else None,
        'population': country.population if country else None,
        'flags': country.flags if country else None
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
        'id': malaria.id,
        'region': malaria.region,
        'iso': malaria.iso,
        'year': malaria.year,
        'cases_median': malaria.cases_median,
        'deaths_median': malaria.deaths_median,
        'land_area_kmsq_2012': malaria.land_area_kmsq_2012,
        'languages_en_2012': malaria.languages_en_2012,
        'who_region': malaria.who_region,
        'world_bank_income_group': malaria.world_bank_income_group,
        'name': country.name if country else None,
        'latlng': country.latlng if country else None,
        'currencies': country.currencies if country else None,
        'capital': country.capital if country else None,
        'capitalInfo': country.capitalInfo if country else None,
        'population': country.population if country else None,
        'flags': country.flags if country else None
    } for malaria, country in malaria_list]

    return jsonify(malaria_data)

@app.route('/api/malaria/iso/')
def get_all_malaria_iso():
    iso_list = db.session.query(Malaria.iso).distinct().order_by(Malaria.iso).all()

    iso_list = [iso[0] for iso in iso_list]

    return jsonify(iso_list)

### Routes for E6156 requirements (NOT to be consumed) ###

@app.route('/api/malaria/<int:id>/', methods=['DELETE'])
def delete_malaria(id):
    malaria = Malaria.query.get(id)

    if malaria:
        db.session.delete(malaria)
        try:
            db.session.commit()
            return "Successfully deleted malaria data"
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error deleting malaria data", 501
    else:
        return "Malaria data not found", 404

@app.route('/api/country/<int:id>/', methods=['DELETE'])
def delete_country(id):
    country = Country.query.get(id)

    if country:
        db.session.delete(country)
        try:
            db.session.commit()
            return "Successfully deleted country data"
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error deleting country data", 501
    else:
        return "Country not found", 404

@app.route('/api/malaria/<int:id>/', methods=['PUT'])
def update_malaria(id):
    malaria = Malaria.query.get(id)

    if malaria:
        new_malaria = request.get_json()
        malaria.region = new_malaria.get('region', malaria.region)
        malaria.year = new_malaria.get('year', malaria.year)
        malaria.cases = new_malaria.get('cases', malaria.cases)
        malaria.deaths = new_malaria.get('deaths', malaria.deaths)
        malaria.cases_median = new_malaria.get('cases_median', malaria.cases_median)
        malaria.cases_min = new_malaria.get('cases_min', malaria.cases_min)
        malaria.cases_max = new_malaria.get('cases_max', malaria.cases_max)
        malaria.deaths_median = new_malaria.get('deaths_median', malaria.deaths_median)
        malaria.deaths_min = new_malaria.get('deaths_min', malaria.deaths_min)
        malaria.deaths_max = new_malaria.get('deaths_max', malaria.deaths_max)
        malaria.fips = new_malaria.get('fips', malaria.fips)
        malaria.iso = new_malaria.get('iso', malaria.iso)
        malaria.iso2 = new_malaria.get('iso2', malaria.iso2)
        malaria.land_area_kmsq_2012 = new_malaria.get('land_area_kmsq_2012', malaria.land_area_kmsq_2012)
        malaria.languages_en_2012 = new_malaria.get('languages_en_2012', malaria.languages_en_2012)
        malaria.who_region = new_malaria.get('who_region', malaria.who_region)
        malaria.world_bank_income_group = new_malaria.get('world_bank_income_group', malaria.world_bank_income_group)

        try:
            db.session.commit()
            return "Successfully updated malaria data"
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error updating malaria data", 501
    else:
        return "Malaria data not found", 404

@app.route('/api/country/<int:id>/', methods=['PUT'])
def update_country(id):
    country = Country.query.get(id)

    if country:
        new_country = request.get_json()
        country.name = new_country.get('name', country.name)
        country.cca2 = new_country.get('iso2', country.cca2)
        country.cca3 = new_country.get('iso3', country.cca3)
        country.currencies = new_country.get('currencies', country.currencies)
        country.capital = new_country.get('capital', country.capital)
        country.capitalInfo = new_country.get('capitalInfo', country.capitalInfo)
        country.latlng = new_country.get('latlng', country.latlng)
        country.area = new_country.get('area', country.area)
        country.population = new_country.get('population', country.population)
        country.timezones = new_country.get('timezones', country.timezones)
        country.flags = new_country.get('flags', country.flags)

        try:
            db.session.commit()
            return "Successfully updated country data"
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error updating country data", 501
    else:
        return "Country not found", 404

@app.route('/api/malaria/', methods=['POST'])
def add_malaria():
    new_malaria_data = request.get_json()

    new_malaria = Malaria(
        region=new_malaria_data.get('region'),
        year=new_malaria_data.get('year'),
        cases=new_malaria_data.get('cases'),
        deaths=new_malaria_data.get('deaths'),
        cases_median=new_malaria_data.get('cases_median'),
        cases_min=new_malaria_data.get('cases_min'),
        cases_max=new_malaria_data.get('cases_max'),
        deaths_min=new_malaria_data.get('deaths_min'),
        deaths_max=new_malaria_data.get('deaths_max'),
        fips=new_malaria_data.get('fips'),
        iso=new_malaria_data.get('iso'),
        iso2=new_malaria_data.get('iso2'),
        land_area_kmsq_2012=new_malaria_data.get('land_area_kmsq_2012'),
        languages_en_2012=new_malaria_data.get('languages_en_2012'),
        who_region=new_malaria_data.get('who_region'),
        world_bank_income_group=new_malaria_data.get('world_bank_income_group')
    )

    db.session.add(new_malaria)
    try:
        db.session.commit()
        return "Successfully added malaria data"
    except (IntegrityError, SQLAlchemyError):
        db.session.rollback()
        return "Error adding malaria data", 501

@app.route('/api/country/', methods=['POST'])
def add_country():
    new_country_data = request.get_json()

    new_country = Country(
        name=new_country_data.get('name'),
        cca2=new_country_data.get('iso2'),
        cca3=new_country_data.get('iso'),
        currencies=new_country_data.get('currencies'),
        capital=new_country_data.get('capital'),
        capitalInfo=new_country_data.get('capitalInfo'),
        latlng=new_country_data.get('latlng'),
        area=new_country_data.get('area'),
        population=new_country_data.get('population'),
        timezones=new_country_data.get('timezones'),
        flags=new_country_data.get('flags')
    )

    db.session.add(new_country)
    try:
        db.session.commit()
        return "Successfully added country data"
    except (IntegrityError, SQLAlchemyError):
        db.session.rollback()
        return "Error adding country data", 501

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        import_malaria_csv()
        import_country_data()

    app.run(debug=True, port=8080)
