import json
import math
import os.path
from datetime import datetime

import requests
from elasticsearch import Elasticsearch, helpers
from flask import Flask, flash, render_template, request, jsonify
from flask_restful import Resource, Api

from common import cache

# from wtforms import validators

app = Flask(__name__)
cache.init_app(app=app, config={"CACHE_TYPE": "filesystem", 'CACHE_DIR': '/tmp', "CACHE_DEFAULT_TIMEOUT": 300000})

app.config["DEBUG"] = True
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 10
app.config['UPLOAD_EXTENSIONS'] = [".json"]
app.config['PORT'] = 8000
app.config['SAVE_FILES'] = False
app.config['CONN_ADAPTER'] = "http://"
app.config['HOST'] = '0.0.0.0'
app.config['API_BASE'] = f"/api/v1"
app.config['ES_URL'] = "http://127.0.0.1:9200"
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

api = Api(app)

cache.set('FILES_COUNTER', 0)
cache.set('ID_COUNTER', 0)
cache.set('MAX_FILES', 100)
cache.set('PROCESSED_FILES', set())
cache.set('DOCS_KEYS', set())
cache.set('ES_INDEX', "json-index")

# es = Elasticsearch("localhost:9200")

try:
    # app.es = Elasticsearch(app.config['ES_URL'])
    app.es = Elasticsearch([{'host': 'host.docker.internal', 'port': 9200}])
    app.es.indices.delete(index=cache.get('ES_INDEX'), ignore=[400, 404])
except Exception as error:
    print("Elasticsearch Client Error:", error)


# def index_file(doc, es_index, _id):
#     doc['timestamp'] = datetime.now()
#     res = app.es.index(index=es_index, id=_id, body=doc)
#     app.es.indices.refresh(index=es_index)
#     log_string = f"Content has been indexed successfully with index {es_index} and id {_id}"
#     flash(log_string)
#     app.logger.info(log_string)
#     return True

def es_connected():
    response = requests.get(app.es)
    if response.status_code == 200:
        return True
    return False


def index_documents(docs_list):
    """ in case we have more than one document per file
    :param docs_list: list of document strings
    """
    helpers.bulk(app.es, docs_list, index=cache.get('ES_INDEX'), doc_type="_doc")
    app.es.indices.refresh(index=cache.get('ES_INDEX'))
    log_string = f"Content has been indexed successfully with index {cache.get('ES_INDEX')} and id "
    log_string += f"{cache.get('ID_COUNTER') - len(docs_list)}-{cache.get('ID_COUNTER') - 1}" if len(
        docs_list) > 1 else \
        f"{cache.get('ID_COUNTER') - 1}"
    flash(log_string)
    app.logger.info(log_string)


def prepare_docs(doc_str):
    """ in case we have more than one document per file
    :param doc_str: contains all the documents as strings
    :return: list of document strings
    """
    doc_list = []
    for num, doc in enumerate(doc_str.splitlines()):
        # catch any JSON loads() errors
        try:
            # convert the string to a dict object
            dict_doc = json.loads(doc)
            # get the keys from the first layer
            if cache.get('ID_COUNTER') == 0:
                cache.set('DOCS_KEYS', {key for key in dict_doc})

            # add timestamp field to the Elasticsearch doc
            dict_doc["timestamp"] = datetime.now()

            # add a dict key called "_id" if you'd like to specify an ID for the doc
            dict_doc["_id"] = num + cache.get('ID_COUNTER')

            # append the dict object to the list []
            doc_list += [dict_doc]

        except json.decoder.JSONDecodeError as err:
            # print the errors
            error = f"ERROR for num: {num} -- JSONDecodeError: {err} for doc: {doc}"
            flash(error)

    cache.set('ID_COUNTER', cache.get('ID_COUNTER') + len(doc_list))
    return doc_list


def read_json_file(file_storage):
    """
    :param file_storage:
    :return: if successfully open and decode the file, read the file to a string
    """
    doc_str = ""
    try:
        file_storage.seek(0)
        doc_str = file_storage.read().decode('utf8')
    except json.JSONDecodeError:
        error_message = '%s is empty or not a valid JSON file' % file_storage.filename
        flash(error_message)
    except UnicodeDecodeError:
        flash("Error decoding the file to UTF-8")

    return doc_str


def validate_file(file_name):
    """
    :param file_name: name of the uploaded file
    :return: message and code to check file_name and limitations
    """
    if file_name != '':
        file_ext = os.path.splitext(file_name)[1]
        if file_name in cache.get('PROCESSED_FILES'):
            flash("File already exists")
            return "File already exists", 400
        elif not file_ext:
            flash("Files should have extensions")
            return "Files should have extensions", 400
        elif file_ext not in app.config['UPLOAD_EXTENSIONS']:
            flash("The only allowed file extension is .json")
            return "The only allowed file extension is .json", 400
        elif cache.get('FILES_COUNTER') >= cache.get('MAX_FILES'):
            flash("Maximum number of files  is reached!")
            return "Maximum number of files  is reached!", 400
        else:
            return " ", 200
    else:
        return "No file selected for uploading", 404


def save_file(file_storage, file_name):
    """ save the uploaded files
    :param file_storage:
    :param file_name:
    """
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.mkdir(app.config['UPLOAD_FOLDER'])
    file_storage.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
    log_string = f"file {file_name} uploaded and saved"
    app.logger.info(log_string)


def read_file(file_storage):
    """
    :param file_storage: for future support of other file types
    :return: return file content or None if something
    """
    try:
        document = read_json_file(file_storage)
        return document
    except IOError:
        error_message = 'No file found with name: %s' % file_storage.filename
        flash(error_message)
    return None


@app.errorhandler(413)
def too_large(e):
    return f"File size exceeds the limit {math.floor(app.config['MAX_CONTENT_LENGTH'] / 1000000)} MB", 413


# parser = reqparse.RequestParser()
# parser.add_argument('file_name')

class UploadFile(Resource):
    def post(self):
        if 'file' not in request.files:
            resp = jsonify({'message': 'No file part in the request'})
            resp.status_code = 400
            return resp
        fs = request.files['file']
        file_name = fs.filename
        message, code = validate_file(file_name)
        # file not valid
        if code != 200:
            resp = jsonify({'message': message})
            resp.status_code = code
            return resp
        else:
            # file is valid
            if app.config['SAVE_FILES']:
                save_file(fs, file_name)
            docs_str = read_file(fs)
            if docs_str:
                docs_list = prepare_docs(docs_str)
                if docs_list:
                    if not es_connected():
                        return [], 500
                    # ready to index
                    index_documents(docs_list)
                    # add the file_name to the set of processed files to prevent duplicate
                    cur_set = cache.get('PROCESSED_FILES')
                    cur_set.add(fs.filename)
                    cache.set('PROCESSED_FILES', cur_set)
                    # Also, increment the counter to check for number of file limit
                    cache.set('FILES_COUNTER', cache.get('FILES_COUNTER') + 1)
                    resp = jsonify({'message': "File is indexed"})
                    resp.status_code = 201
                    return resp

            resp = jsonify({'message': message})
            resp.status_code = 400
            return resp


api.add_resource(UploadFile, f"{app.config['API_BASE']}/upload/")


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' in request.files:
            fs = request.files['file']
            f_name = fs.filename
            message, code = validate_file(f_name)
            if code == 200:
                # since we use post here, it is convenient to save files and read from it in the API
                save_file(fs, f_name)
                server_address = f"{app.config['CONN_ADAPTER']}{app.config['HOST']}:{app.config['PORT']}"

                # we can use upload API to upload files from web application
                response = requests.post(f"{server_address}{app.config['API_BASE']}/upload/",
                                         files={'file': open(os.path.join(app.config['UPLOAD_FOLDER'], f_name), 'rb')})
                # We don't need the file after indexing
                if not app.config['SAVE_FILES']:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f_name))

                if response.status_code == 201:
                    flash(f"Please proceed to search")
                else:
                    flash(f"Response code is {response.status_code}")

    return render_template("index.html")


# Search API definition
class Search(Resource):
    def get(self):
        if not request.data:
            return [], 400
        if not es_connected():
            return [], 500
        response = app.es.search(
            index=cache.get('ES_INDEX'), doc_type="_doc",
            body=request.data
        )
        return response


api.add_resource(Search, f"{app.config['API_BASE']}/search/")


@app.route('/search', methods=['GET', 'POST'])
def search_index():
    results_dict = {}
    if request.method == 'POST':
        keywords = request.form['search_words']
        if keywords != "":
            query = {'query': {'multi_match': {'query': keywords, 'fields': ['*']}},
                     'from': 0 * 10, 'size': 10}
            query = json.dumps(query)
            server_address = f"{app.config['CONN_ADAPTER']}{app.config['HOST']}:{app.config['PORT']}"

            # we can use search API for the search part of web application
            response = requests.get(f"{server_address}{app.config['API_BASE']}/search/", data=query,
                                    headers={'content-type': 'application/json'})

            if response.status_code == 200:
                # we can use response.text or response.json() to get the data from response
                response = response.json()

                # create a list of json dictionaries from response
                results_dict = [hit['_source'] for hit in response['hits']['hits']]

    return render_template('search.html', search_fields=cache.get('DOCS_KEYS'), page=results_dict)


if __name__ == "__main__":
    app.run(host=app.config['HOST'], port=app.config['PORT'])
