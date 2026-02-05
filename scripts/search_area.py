import requests
import json

query = """
[out:json];
area[name~"Roma"];
out body;
"""
url = "https://overpass-api.de/api/interpreter"
response = requests.post(url, data={'data': query})
print(json.dumps(response.json(), indent=2))
