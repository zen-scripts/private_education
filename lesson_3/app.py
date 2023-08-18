import asyncio
from typing import Optional
from loguru import logger

from web3.types import TxParams
from py_eth_async.data.models import Networks, TokenAmount, Unit, Ether
from py_eth_async.client import Client
from pretty_utils.miscellaneous.files import read_json
from py_eth_async.transactions import Tx
from py_eth_async.contracts import Contracts as pyContracts
from tasks.woofi import WooFi
from data.models import Contracts
from data.config import ABIS_DIR
from private_data import private_key1, proxy

async def main():
    client = Client(private_key=private_key1, network=Networks.Arbitrum)
    woofi = await WooFi.init_async(client)
    # res = await woofi.swap_from_eth_to_token(amount=TokenAmount(amount=0.0005), to_token=Contracts.ARBITRUM_USDT)
    res = await woofi.swap_from_token_to_eth(amount=TokenAmount(amount=0.7), from_token=Contracts.ARBITRUM_USDT)
    # res = await woofi.get_decimals(contract_address=Contracts.ARBITRUM_WBTC)
    print(res)


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
