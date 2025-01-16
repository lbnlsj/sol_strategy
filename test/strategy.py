import requests
import os

from dotenv import load_dotenv

load_dotenv()

# host = '154.12.92.165'
host = '127.0.0.1'
BASE_URL = f'http://{host}:' + os.getenv('PORT')

data = {
    'ca': 'CPA3hYPuTuDFTzcmtEyuLC81VHPbTsAaXoRDz3u63wKF',
    'type_id': 2
}

response = requests.post(BASE_URL + '/api/tasks', json=data)
print(response.text)
