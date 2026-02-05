import requests
import json

query = """
[out:json];
(
  area[name="Roma"][admin_level="8"];
  area[name="Roma"][admin_level="6"];
  area[name="Città metropolitana di Roma Capitale"];
);
out body;
"""
url = "https://overpass-api.de/api/interpreter"
response = requests.post(url, data={'data': query})
data = response.json()
for element in data.get('elements', []):
    print(f"Name: {element.get('tags', {}).get('name')}, Level: {element.get('tags', {}).get('admin_level')}, ID: {element.get('id')}")
