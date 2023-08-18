import asyncio
from typing import Optional
from web3.types import TxParams
from py_eth_async.data.models import TxArgs, TokenAmount
from data.models import Contracts
from tasks.base import Base


class WooFi(Base):
    async def get_tx_params(self, amount: TokenAmount, from_token: Contracts, to_token: Contracts, slippage):
        to_token_price = 1 if to_token.name.upper() in ("USDT", "USDC") \
            else await self.get_token_price(token=to_token.name)
        from_token_price = 1 if from_token.name.upper() in ("USDT", "USDC") \
            else await self.get_token_price(token=from_token.name)
        min_to_amount = TokenAmount(
            amount=from_token_price * float(amount.Ether) / to_token_price * (1 - slippage / 100),
            decimals=await self.get_decimals(contract_address=to_token.address)
        )

        args = TxArgs(
            fromToken=from_token.address,
            to_token=to_token.address,
            fromAmount=amount.Wei,
            minToAmount=min_to_amount.Wei,
            to=self.client.account.address,
            rebateTo=self.client.account.address
        )

        if from_token.name == 'ETH':
            tx_params = TxParams(
                to=self.contract.address,
                data=self.contract.encodeABI('swap', args=args.tuple()),
                value=amount.Wei
            )
            return min_to_amount, tx_params, f'Failed swap ETH to {to_token.name} via WooFi'

        tx_params = TxParams(
            to=self.contract.address,
            data=self.contract.encodeABI('swap', args=args.tuple()),
        )
        return min_to_amount, tx_params, f'Failed swap {from_token.name} to {to_token.name} via WooFi'

    async def swap_from_eth_to_token(self, amount: TokenAmount, to_token: Contracts, slippage: float = 1):
        min_to_amount, tx_params, failed_text = await self.get_tx_params(
            amount=amount,
            from_token=Contracts.ARBITRUM_ETH,
            to_token=to_token,
            slippage=slippage
        )

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
        receipt = await tx.wait_for_receipt(client=self.client, timeout=200)
        if receipt:
            return f'{amount.Ether} ETH was swapped to {min_to_amount.Ether} {to_token.name} via WooFi: {tx.hash.hex()}'
        return f'{failed_text}!'

    async def swap_from_token_to_eth(self, from_token: Contracts, slippage: float = 1,
                                     amount: Optional[TokenAmount] = None):

        if not amount:
            amount = await self.client.wallet.balance(token=from_token.address)
            if amount.Wei <= 0:
                raise ValueError(
                    f'Баланс токена {from_token.name} не достаточен для свапа: {amount.Wei} {from_token.name}')

        #   Если свапать конкретное количество токена, вылетала ошибка , т.к. брало с дефолтными decimals 18
        amount = TokenAmount(amount=amount.Ether, decimals=await self.get_decimals(from_token.address))

        await self.approve_interface(token_address=from_token.address, spender=self.contract.address, amount=amount)
        await asyncio.sleep(5)

        min_to_amount, tx_params, failed_text = await self.get_tx_params(
            amount=amount,
            from_token=from_token,
            to_token=Contracts.ARBITRUM_ETH,
            slippage=slippage
        )

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
        receipt = await tx.wait_for_receipt(client=self.client, timeout=200)
        if receipt:
            return f'{amount.Ether} {from_token.name} was swapped to {min_to_amount.Ether} ETH via WooFi: {tx.hash.hex()}'
        return f'{failed_text}!'
