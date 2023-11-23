import json, os, requests
from flask import Flask, request, jsonify
from flask_cors import CORS

### Set up the API URLs ###

malaria_base_url = 'http://127.0.0.1:7071/api'  # TODO: change to AWS API Gateway URL after deloyment
malaria_endpoints = {
    'reset': '/reset/malaria',      # PUT
    'filter': '/malaria/filter',    # support ?region=&year=&who_region=&iso=&page=&per_page= query parameters
    'all': '/malaria',
    'iso': '/malaria/iso',
}

country_base_url = 'http://127.0.0.1:7070/api'  # TODO: change to AWS API Gateway URL after deloyment
country_endpoints = {
    'reset': '/reset/country',      # PUT
    'get': '/country',              # support ?iso= query parameter
}

API_URLS = {
    'malaria': {endpoint: malaria_base_url + path for endpoint, path in malaria_endpoints.items()},
    'country': {endpoint: country_base_url + path for endpoint, path in country_endpoints.items()}
}

def make_api_request(url, method, **kwargs):
    try:
        response = requests.request(method, url, **kwargs)

        if response.status_code == 200:
            if response.headers['Content-Type'] == 'application/json':
                response_data = response.json()  # Parse JSON response
            else:
                response_data = response.text  # Get response as a string
            return jsonify(response_data)
        else:
            return jsonify({
                'error': f'Status: {response.status_code} {response.text}'
                })
    except requests.RequestException as e:
        return jsonify({'error': f'Error making API request: {str(e)}'})

### Set up the app ###

app = Flask(__name__)
app.json.sort_keys = False
CORS(app)

# NOTE: This route is needed for the default EB health check route
@app.route('/')  
def home():
    return "Ok"

### Reset databases ###

@app.route('/api/reset/malaria/', methods=['PUT'])
def reset_malaria_db():
    return make_api_request(API_URLS['malaria']['reset'], 'PUT')

@app.route('/api/reset/country/', methods=['PUT'])
def reset_country_db():
    return make_api_request(API_URLS['country']['reset'], 'PUT')

@app.route('/api/reset/', methods=['PUT'])
def reset_all_dbs():
    malaria_response = make_api_request(API_URLS['malaria']['reset'], 'PUT')
    country_response = make_api_request(API_URLS['country']['reset'], 'PUT')

    return jsonify({
        'malaria': malaria_response.json,
        'country': country_response.json
    })

### Country and Malaria resources ###

@app.route('/api/country/')
def get_country():
    iso = request.args.get('iso')
    params = {'iso': iso} if iso else {}
    return make_api_request(API_URLS['country']['get'], 'GET', params=params)

# TODO: from here down, change to use the new chilren APIs
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

    app.run(debug=True, port=8080)
