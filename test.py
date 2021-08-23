import requests
import json

BASE = "http://127.0.0.1:8000/api/v1"

headers = {'Content-type': 'multipart/form-data'}

response = requests.post(BASE + "/upload/", files={'file': open('./test_files/co_lines.json', 'rb')})
print(response.json())

query = {'query': {'multi_match': {'query': "the", 'fields': ['*']}},
         'from': 0 * 10, 'size': 10}
query = json.dumps(query)
response = requests.get(BASE + "/search/", data=query,
                        headers={'content-type': 'application/json'})
print(response.status_code)

query = {'query': {'multi_match': {'query': "the", 'fields': ['*']}}}
query = json.dumps(query)
response = requests.get(BASE + "/search/", data=query,
                        headers={'content-type': 'application/json'})
print(response.status_code)


query = {'query': {'multi_match': {'query': "thedfadsfadfa", 'fields': ['*']}},
         'from': 0 * 10, 'size': 10}
query = json.dumps(query)
response = requests.get(BASE + "/search/", data=query,
                        headers={'content-type': 'application/json'})
print(response.status_code)

