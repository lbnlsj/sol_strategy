import requests
import os

from dotenv import load_dotenv

load_dotenv()

# host = '49.51.162.135'
host = '127.0.0.1'
BASE_URL = f'http://{host}:' + os.getenv('PORT')

data = {
    'ca': '7c5PqTfAL3FqCqubbDkxwRb6XXmNVG7XnamRkqAyoHQS',
    'type_id': 2
}

response = requests.post(BASE_URL + '/api/tasks', json=data)
print(response.text)
