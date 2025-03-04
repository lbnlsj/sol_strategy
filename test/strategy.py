import requests
import os

from dotenv import load_dotenv

load_dotenv()

# host = '43.157.45.202'
host = '127.0.0.1'
BASE_URL = f'http://{host}:' + os.getenv('PORT')

data = {
    'ca': '5hLueUaJGdL1C6rt8YMwya43EwvxYbcz9AowAsUTpump',
    'type_id': 5
}

response = requests.post(BASE_URL + '/api/tasks', json=data)
print(response.text)
