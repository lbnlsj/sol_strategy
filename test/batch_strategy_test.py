# import requests
import random
import os
from curl_cffi import requests

url = 'https://frontend-api-v2.pump.fun/coins?offset=0&limit=50&sort=created_timestamp&order=DESC&includeNsfw=false'
# url = 'https://gmgn.ai/defi/quotation/v1/rank/sol/swaps/1h?orderby=swaps&direction=desc&filters[]=renounced&filters[]=frozen'

session = requests.Session()
response = session.get(url, impersonate="safari15_5")
mints = [d['mint'] for d in response.json()]
print(f'一共检测到 {len(mints)} 个token地址')

target_mints = [random.choice(mints) for _ in range(1)]
print(target_mints)

host = '127.0.0.1'
BASE_URL = f'http://{host}:2000'

for ca in target_mints:
    data = {
        'ca': '6ttH9AbqPqxCPk5G7BN6JBrQbuyrGiorNkSupd4tpump',
        'type_id': 2
    }
    response = requests.post(BASE_URL + '/api/tasks', json=data)
    print(response.text)