import asyncio
from web3 import Web3
from sdk.data.models import Networks
from sdk.client import Client
from loguru import logger
from private_data import private_key1, proxy
from data.config import FILES_DIR


async def check_balance(semaphore: asyncio.Semaphore):
    async with semaphore:
        client = Client(private_key=None, network=Networks.Ethereum, proxy=proxy)
        # print(await client.wallet.balance(token_address='0xaf88d065e77c8cc2239327c5edb3a432268e5831'))
        balance = None
        retries = 1

        while not balance and retries <= 5:
            try:
                logger.info(f"Проверяю {client.account.address}. Попытка {retries}.")
                balance = await client.wallet.balance()
                if balance.Wei:
                    logger.success(f"{client.account.address}: {round(balance.Ether, 6)} ETH")
                    await asyncio.sleep(0.2)
                    return client.account.key.hex()
                logger.warning(f"{client.account.address}: денег нет, но вы держитесь.")
                await asyncio.sleep(0.2)
                return None
            except Exception as e:
                logger.error(f"Ошибка при проверке баланса: {e}. Попытка: {retries}")
                if 'Too Many Requests' in str(e):
                    logger.critical(f"429, message='Too Many Requests': Прокси в бане {proxy}")
                    return None
                retries += 1



async def main():
    accounts_number = int(input("Введите количество адресов для брута: "))
    threads = int(input("Введите количество потоков: "))
    semaphore = asyncio.Semaphore(threads)
    tasks = []
    for i in range(accounts_number):
        tasks.append(asyncio.create_task(check_balance(semaphore)))
    await asyncio.wait(tasks)
    for task in tasks:
        bruted_count = 0
        if task.result() is not None:
            bruted_count += 1
            logger.success(task.result())
            with open(f'{FILES_DIR}/bruted_accs.txt', 'a') as bruted:
                bruted.writelines(task.result())
    logger.info('\n\n==========================================================')
    logger.info('СТАТИСТИКА о проделанной работе')
    logger.info(f"Проверенно адресов: {len(tasks)}")
    logger.info(f"Успешно сбручено: {bruted_count}")


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())




    '''
    token_address = Web3.to_checksum_address('0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')

    tasks = []
    for private_key in [private_key1, private_key2, private_key3]:
        client = Client(private_key=private_key, network=Networks.Arbitrum)
        tasks.append(asyncio.create_task(client.wallet.balance(token_address=token_address)))

    await asyncio.gather(*tasks)
    await asyncio.wait([*tasks])

    for task in tasks:
        print(task.result())
    '''
    '''
    asyncio.gather() принимает список асинхронных задач (coroutines) в качестве аргументов и запускает их одновременно.
    Она возвращает список результатов, соответствующих выполненным задачам в том же порядке, в котором задачи были переданы в функцию.
    Если во время выполнения задачи возникает исключение, asyncio.gather() прекращает выполнение остальных задач и сразу же выбрасывает исключение.

    asyncio.wait() принимает список асинхронных задач (coroutines) в качестве аргументов и запускает их одновременно.
    Она возвращает кортеж из двух множеств: множество выполненных задач и множество невыполненных задач.
    Если во время выполнения задачи возникает исключение, asyncio.wait() продолжает выполнение остальных задач и не выбрасывает исключение.
    '''
