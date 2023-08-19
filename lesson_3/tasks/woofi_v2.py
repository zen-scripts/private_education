import asyncio
from typing import Optional
from web3.types import TxParams
from py_eth_async.data.models import TxArgs, TokenAmount
from data.models import Contracts
from tasks.base import Base


def check_similarity(from_token: Contracts,
                     to_token: Contracts
                     ):
    """
    Checks if the same token contract are supposed to be swapped
    :param from_token:
    :param to_token:
    :return:
    """
    if from_token == to_token:
        raise ValueError(f"\nYou try to swap between the same CONTRACTs")


class WooFi(Base):

    async def _get_token_name(self, token):
        """
        Returns a single token symbol name
        :param token:
        :return:
        """
        if token.address == Contracts.ARBITRUM_ETH.address:
            return 'ETH'
        token_contract = await self.client.contracts.default_token(contract_address=token)
        return await token_contract.functions.symbol().call()

    async def get_token_symbols(self, from_token, to_token):
        """
        Returns a tuple of swap symbol names
        :param from_token:
        :param to_token:
        :return:
        """
        from_token_name = await self._get_token_name(from_token)
        to_token_name = await self._get_token_name(to_token)
        return from_token_name, to_token_name

    async def calculate_min_amount(self,
                                   from_token_name: str,
                                   to_token_name: str,
                                   amount: TokenAmount,
                                   slippage: Optional[float] = 1
                                   ):
        return await self.get_token_ratio(from_token=from_token_name,
                                          to_token=to_token_name) * float(amount.Ether) * \
            (1 - slippage / 100)

    async def get_actual_token_balance(self,
                                       from_token: Contracts,
                                       ) -> TokenAmount:
        if from_token.address == Contracts.ARBITRUM_ETH.address:
            return await self.client.wallet.balance()
        return await self.client.wallet.balance(token=from_token.address)

    async def get_swap_amount(self,
                              from_token: Contracts,
                              amount: TokenAmount | None,
                              from_token_name: str
                              ):
        #   Текущее значение баланса from_token
        from_token_balance = await self.get_actual_token_balance(from_token=from_token)
        if not amount:
            if from_token.address == Contracts.ARBITRUM_ETH.address:
                return TokenAmount(amount=float(from_token_balance.Ether) * 0.5)
            return from_token_balance
        amount = TokenAmount(amount=amount.Ether, decimals=await self.get_decimals(from_token.address))
        if amount.Wei > from_token_balance.Wei:
            raise Exception(f'Specified amount {amount.Ether} {from_token_name} '
                            f'is higher than actual {from_token_name} balance: {from_token_balance.Ether}')
        return amount

    async def swap(self,
                   from_token: Optional[Contracts] = Contracts.ARBITRUM_ETH,
                   to_token: Optional[Contracts] = Contracts.ARBITRUM_ETH,
                   amount: Optional[TokenAmount] = None,
                   slippage: float = 1
                   ):

        #   Проверяем не свапаем ли одинаковые токены
        check_similarity(from_token=from_token, to_token=to_token)

        #   Получаем тикеры токенов
        from_token_name, to_token_name = await self.get_token_symbols(from_token=from_token, to_token=to_token)

        #   Формируем amount для транзакции
        amount = await self.get_swap_amount(from_token=from_token,
                                            from_token_name=from_token_name,
                                            amount=amount)

        failed_text = f'Failed swap {amount.Ether} {from_token_name} to {to_token_name} via WooFi'

        #   Вычисляем миниальную сумму к получению
        min_to_amount = TokenAmount(await self.calculate_min_amount(from_token_name, to_token_name, amount),
                                    decimals=await self.get_decimals(to_token.address),
                                    wei=False)

        args = TxArgs(
            fromToken=from_token.address,
            toToken=to_token.address,
            fromAmount=amount.Wei,
            minToAmount=min_to_amount.Wei,
            to=self.client.account.address,
            rebateTo=self.client.account.address,
        )

        tx_params = TxParams(
            to=self.contract.address,
            data=self.contract.encodeABI('swap', args=args.tuple()),
            value=amount.Wei if from_token.address == Contracts.ARBITRUM_ETH.address else 0
        )

        if from_token.address != Contracts.ARBITRUM_ETH.address:
            await self.approve_interface(token_address=from_token.address, spender=self.contract.address, amount=amount)
            await asyncio.sleep(5)

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
        receipt = await tx.wait_for_receipt(client=self.client, timeout=200)
        if receipt:
            return (f'{amount.Ether} {from_token_name} was swapped to {min_to_amount.Ether} '
                    f'{to_token_name} via WooFi: {tx.hash.hex()}')
        return f'{failed_text}!'
