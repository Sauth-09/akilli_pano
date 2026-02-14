import requests
try:
    r = requests.get('http://127.0.0.1:7000/api/get_slides')
    print(r.status_code)
    print(r.json())
except Exception as e:
    print(e)
