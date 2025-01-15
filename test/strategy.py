import requests
import os

from dotenv import load_dotenv

load_dotenv()

<<<<<<< HEAD
host = '49.51.162.135'
# host = '127.0.0.1'
BASE_URL = f'http://{host}:' + os.getenv('PORT')

data = {
    'ca': 'Eg4AUpzkaYodsCaWLfxHvfWoPcqdxSiXpNQmYFWpump',
=======
# host = '49.51.162.135'
host = '127.0.0.1'
BASE_URL = f'http://{host}:' + os.getenv('PORT')

data = {
    'ca': 'AXq7hB6Q2R1kLUKNhUiP7U2Wso27G3ocyhYg2vfmpump',
>>>>>>> 4fa1be4 (.)
    'type_id': 2
}
response = requests.post(BASE_URL + '/api/tasks', json=data)
print(response.text)