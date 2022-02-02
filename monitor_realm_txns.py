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
within_inner_walls = lambda x, y: 3875 < x < 5650 and 2400 < y < 3900


def handle(action, event_args):

    listing_id = event_args.listingId
    token_id = event_args.erc721TokenId

    if action == 'listed':
        # in ERC721ListingAdd events, the price
        # is stored in the time field - see
        # https://github.com/aavegotchi/aavegotchi-contracts/blob/master/contracts/Aavegotchi/facets/ERC721MarketplaceFacet.sol#L259
        price_in_wei = event_args.time
    else:
        price_in_wei = event_args.priceInWei
    
    price = int(price_in_wei / 1e18)

    # see https://github.com/aavegotchi/aavegotchi-realm-diamond/blob/master/contracts/facets/RealmFacet.sol#L55
    info = realm_contract.functions.getParcelInfo(token_id).call()
    district = 'D' + str(info[6])
    if within_inner_walls(info[3], info[4]):
        district += " [INNER WALL]"
    size = sizes[info[5]]
    boosts = info[7]

    url = f"https://aavegotchi.com/baazaar/erc721/{listing_id}"
    timestamp = datetime.datetime.now().isoformat()
    msg = f"{timestamp} {district} {size} {boosts} {action} for {price} GHST - {url}"
    print(msg)


print('listening ...')

while True:

    for event in add_filter.get_new_entries():
        handle('listed', event.args)

    for event in exec_filter.get_new_entries():
        handle('sold', event.args)

    time.sleep(60)
