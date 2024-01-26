import json
import requests

from settings import (
    ACCOUNT_FILE,
)


def get_addresses():
    with open(ACCOUNT_FILE, 'r') as f:
        addresses = f.readlines()

    return addresses


if __name__ == '__main__':
    addresses = get_addresses()

    data = []
    chain = []

    for idx, addr in enumerate(addresses):
        if len(chain) < 20:
            chain.append(addr.strip())
        else:
            data.append(chain)
            chain = []

    if len(chain) > 0:
        data.append(chain)

    balances = []

    for k, items in enumerate(data):
        print(k)

        url_addr = ','.join(items)

        response = requests.get(f'https://api.routescan.io/v2/network/testnet/evm/80085/etherscan/api?module=account&action=balancemulti&address={url_addr}&tag=latest').text
        response = json.loads(response)

        if response['status']:
            for result in response['result']:
                if result['balance']:
                    balance = float(int(result['balance']) / 1000000000000000000)
                    balances.append({'addr': result['account'], 'balance': balance})

    file = open('balance.json', 'w')
    file.write(json.dumps(balances))
    file.close()