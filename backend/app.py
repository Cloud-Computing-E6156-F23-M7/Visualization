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
    params = {'iso': request.args.get('iso')}
    return make_api_request(API_URLS['country']['get'], 'GET', params=params)

# TODO: combine country data?
@app.route('/api/malaria/filter')
def filter_malaria():
    params = {
        'region': request.args.get('region'),
        'year': request.args.get('year'),
        'who_region': request.args.get('who_region'),
        'page': request.args.get('page', 1, type=int),
        'per_page': request.args.get('per_page', 10, type=int),
        'iso': request.args.get('iso')
    }

    malaria_data = make_api_request(
        API_URLS['malaria']['filter'], 'GET', params=params).json
    country_data = make_api_request(
        API_URLS['country']['get'], 'GET', params={'iso': params['iso']}).json

    for malaria in malaria_data['malaria_data']:
        matching_country = next((country for country in country_data if country['iso'] == malaria['iso']), None)
        if matching_country:
            malaria.update(matching_country)

    return jsonify(malaria_data)   

#TODO: from here down
@app.route('/api/malaria/')
def get_all_malaria():
    return make_api_request(API_URLS['malaria']['all'], 'GET')

@app.route('/api/malaria/iso/')
def get_all_malaria_iso():
    return make_api_request(API_URLS['malaria']['iso'], 'GET')

if __name__ == '__main__':
    app.run(debug=True, port=8080)
