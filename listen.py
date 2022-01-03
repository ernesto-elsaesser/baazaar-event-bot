import os
import time
import json

import requests
from web3 import Web3


bot_key = os.environ['BOT_API_KEY']
chat_id = os.environ['CHAT_ID']
moralis_token = os.environ['MORALIS_TOKEN']


moralis_url = f"wss://speedy-nodes-nyc.moralis.io/{moralis_token}/polygon/mainnet/ws"
provider = Web3.WebsocketProvider(moralis_url)
web3 = Web3(provider)

with open("abi_aavegotchi.json") as abi_file:
    aavegotchi_abi = json.load(abi_file)

aavegotchi_contract = web3.eth.contract(address='0x86935F11C86623deC8a25696E1C19a8659CbF95d', abi=aavegotchi_abi)

with open("abi_realm.json") as abi_file:
    realm_abi = json.load(abi_file)

realm_contract = web3.eth.contract(address='0x1D0360BaC7299C86Ec8E99d0c1C9A95FEfaF2a11', abi=realm_abi)

add_event = aavegotchi_contract.events.ERC721ListingAdd()
exec_event = aavegotchi_contract.events.ERC721ExecutedListing()

# see https://github.com/aavegotchi/aavegotchi-contracts/blob/master/contracts/Aavegotchi/facets/ERC721MarketplaceFacet.sol#L199
realm_filter = {'category': 4}

add_filter = add_event.createFilter(fromBlock='latest', argument_filters=realm_filter)
exec_filter = exec_event.createFilter(fromBlock='latest', argument_filters=realm_filter)

sizes = ['humble', 'reasonable', 'spacious vertical', 'spacious horizontal', 'partner']

# D1 inner wall
min_x = 3800
max_x = 5700
min_y = 2400
max_y = 4000


def handle(action, tokenId, price_in_wei):

    price = price_in_wei / 1e18

    # see https://github.com/aavegotchi/aavegotchi-realm-diamond/blob/master/contracts/facets/RealmFacet.sol#L55
    info = realm_contract.functions.getParcelInfo(tokenId).call()
    x_coord = info[3]
    y_coord = info[4]
    size_id = info[5]
    district = info[6]
    boosts = info[7]
    size = sizes[size_id]

    msg = f"{action} {size} D{district} {boosts} for {price:.0f} GHST\nhttps://gotchiverse.io/browse?tokenId={tokenId}"
    print(msg)

    if min_x < x_coord < max_x and min_y < y_coord < max_y:
        send_url = f"https://api.telegram.org/bot{bot_key}/sendMessage?chat_id={chat_id}&text={msg}"
        response = requests.get(send_url)
        if response.status_code != 200:
            print(response)


while True:

    for event in add_filter.get_new_entries():
        # in ERC721ListingAdd events, time field is used for price_in_wei 
        # see https://github.com/aavegotchi/aavegotchi-contracts/blob/master/contracts/Aavegotchi/facets/ERC721MarketplaceFacet.sol#L259
        handle('listed', event.args.erc721TokenId, event.args.time)

    for event in exec_filter.get_new_entries():
        handle('sold', event.args.erc721TokenId, event.args.priceInWei)

    time.sleep(60)
