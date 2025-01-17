import requests
import os

from dotenv import load_dotenv

load_dotenv()

host = '49.51.162.135'
# host = '127.0.0.1'
BASE_URL = f'http://{host}:' + os.getenv('PORT')

data = {
    'ca': '3X7MidG2QYnfmQ6egHMDDFt9iGmryB8gCvuw3ad8pump',
    'type_id': 2
}

response = requests.post(BASE_URL + '/api/tasks', json=data)
print(response.text)
