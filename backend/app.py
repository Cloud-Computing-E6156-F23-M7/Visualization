import json, os, requests, asyncio, aiohttp
from flask import Flask, request, jsonify
from flask_cors import CORS

### Set up the API URLs ###

malaria_base_url = 'http://127.0.0.1:7071/api'  # TODO: change to AWS API Gateway URL after deloyment
malaria_endpoints = {
    'reset': '/reset/malaria',      # PUT
    'filter': '/malaria/filter',    # support ?region=&year=&who_region=&iso=&page=&per_page= query parameters
    'all': '/malaria',
    'iso': '/malaria/iso',
    'iso/<iso>': '/malaria/iso/<iso>',
    '<id>': '/malaria/<id>'
}

country_base_url = 'http://127.0.0.1:7070/api'  # TODO: change to AWS API Gateway URL after deloyment
country_endpoints = {
    'reset': '/reset/country',      # PUT
    'get': '/country',              # support ?iso= query parameter
    'iso/<iso>': '/country/iso/<iso>',
    '<id>': '/country/<id>'
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

async def async_make_api_request(url, method, params=None, session=None):
    if session is None:
        async with aiohttp.ClientSession() as session:
            return await async_make_api_request(url, method, params=params, session=session)

    methods = {
        'GET': session.get,
        'POST': session.post,
        'PUT': session.put,
        'DELETE': session.delete
    }

    if method in methods:
        async with methods[method](url, params=params) as response:
            return await response.json()
    else:
        raise ValueError(f'Invalid method: {method}')

async def fetch_data(urls, method, params=None):    # Assume all URLs use the same method
    async with aiohttp.ClientSession() as session:
        tasks = [
            async_make_api_request(url, method, params=params, session=session) for url in urls
        ]
        responses = []
        for future in asyncio.as_completed(tasks):
            response = await future
            responses.append(response)
        return responses

def run_in_new_loop(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)

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
        matching_country = next((
            country for country in country_data if country['iso'] == malaria['iso']), None)
        if matching_country:
            malaria.update(matching_country)

    return jsonify(malaria_data)   

# For visual initialization, not meant to be called frequently
@app.route('/api/malaria/') 
def get_all_malaria():
    malaria_data = make_api_request(API_URLS['malaria']['all'], 'GET').json
    country_data = make_api_request(API_URLS['country']['get'], 'GET').json

    for malaria in malaria_data:
        matching_country = next((
            country for country in country_data if country['iso'] == malaria['iso']), None)
        if matching_country:
            malaria.update(matching_country)

    return jsonify(malaria_data) 

@app.route('/api/malaria/iso/')
def get_all_malaria_iso():
    return make_api_request(API_URLS['malaria']['iso'], 'GET')

@app.route('/api/malaria_country/iso/<string:iso>')
def get_malaria_by_iso(iso):
    malaria_url = API_URLS['malaria']['iso/<iso>'].replace('<iso>', iso)
    country_url = API_URLS['country']['iso/<iso>'].replace('<iso>', iso)

    coroutine = fetch_data([malaria_url, country_url], 'GET')
    responses = run_in_new_loop(coroutine)

    return jsonify(responses)

@app.route('/api/malaria_country/async/<int:id>')
def get_malaria_async_by_id(id):
    malaria_url = API_URLS['malaria']['<id>'].replace('<id>', str(id))
    country_url = API_URLS['country']['<id>'].replace('<id>', str(id))

    coroutine = fetch_data([malaria_url, country_url], 'GET')
    responses = run_in_new_loop(coroutine)

    return jsonify(responses)

@app.route('/api/malaria_country/sync/<int:id>')
def get_malaria_sync_by_id(id):
    malaria_url = API_URLS['malaria']['<id>'].replace('<id>', str(id))
    country_url = API_URLS['country']['<id>'].replace('<id>', str(id))

    malaria_response = make_api_request(malaria_url, 'GET').json
    country_response = make_api_request(country_url, 'GET').json

    return jsonify([malaria_response, country_response])

if __name__ == '__main__':
    app.run(debug=True, port=8080)
