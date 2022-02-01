import os
import time
import datetime
import json

import requests
from web3 import Web3


moralis_token = os.environ['MORALIS_TOKEN']
moralis_url = f"wss://speedy-nodes-nyc.moralis.io/{moralis_token}/polygon/mainnet/ws"
provider = Web3.WebsocketProvider(moralis_url)
web3 = Web3(provider)

def load_contract(address, abi_url):
    response = requests.get(abi_url)
    abi = response.json()
    return web3.eth.contract(address=address, abi=abi)

aavegotchi_contract = load_contract('0x86935F11C86623deC8a25696E1C19a8659CbF95d',
    "https://raw.githubusercontent.com/aavegotchi/aavegotchi-contracts/master/diamondABI/diamond.json")

realm_contract = load_contract('0x1D0360BaC7299C86Ec8E99d0c1C9A95FEfaF2a11',
    "https://raw.githubusercontent.com/aavegotchi/aavegotchi-realm-diamond/master/diamondABI/diamond.json")

add_event = aavegotchi_contract.events.ERC721ListingAdd()
exec_event = aavegotchi_contract.events.ERC721ExecutedListing()

# see https://github.com/aavegotchi/aavegotchi-contracts/blob/master/contracts/Aavegotchi/facets/ERC721MarketplaceFacet.sol#L199
realm_filter = {'category': 4}

add_filter = add_event.createFilter(fromBlock='latest', argument_filters=realm_filter)
exec_filter = exec_event.createFilter(fromBlock='latest', argument_filters=realm_filter)

sizes = ['humble', 'reasonable', 'spacious vertical', 'spacious horizontal', 'partner']

# D1 inner wall
min_x = 3875
max_x = 5650
min_y = 2400
max_y = 3900


def handle(action, listingId, tokenId, price_in_wei):

    price = int(price_in_wei / 1e18)

    # see https://github.com/aavegotchi/aavegotchi-realm-diamond/blob/master/contracts/facets/RealmFacet.sol#L55
    info = realm_contract.functions.getParcelInfo(tokenId).call()
    x_coord = info[3]
    y_coord = info[4]
    size = sizes[info[5]]
    district = 'D' + str(info[6])
    boosts = info[7]

    if min_x < x_coord < max_x and min_y < y_coord < max_y:
        district += " !INNER WALL!"

    url = "https://aavegotchi.com/baazaar/erc721/" + listingId
    timestamp = datetime.datetime.now().isoformat()
    msg = f"{timestamp} D{district} {size} {boosts} {action} for {price} GHST - {url}"
    print(msg)


print('listening ...')

while True:

    for event in add_filter.get_new_entries():
        # in ERC721ListingAdd events, time field is used for price_in_wei 
        # see https://github.com/aavegotchi/aavegotchi-contracts/blob/master/contracts/Aavegotchi/facets/ERC721MarketplaceFacet.sol#L259
        handle('listed', event.args.listingId,
                event.args.erc721TokenId, event.args.time)

    for event in exec_filter.get_new_entries():
        handle('sold', event.args.listingId,
                event.args.erc721TokenId, event.args.priceInWei)

    time.sleep(60)
