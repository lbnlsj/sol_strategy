import struct
import base64
import httpx
from decimal import Decimal
from typing import Optional, Dict, Tuple, Union
import logging
import traceback
import random
import base58
from solana.rpc import types
import asyncio
from solders.keypair import Keypair
from solders import message
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.instruction import Instruction
from solders.transaction import Transaction
from solders.instruction import CompiledInstruction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.transaction_status import TransactionConfirmationStatus
from solders.signature import Signature
from solana.rpc.types import TxOpts
from pathlib import Path
from solana.rpc.commitment import Processed
from jupiter_python_sdk.jupiter import Jupiter
from solana.rpc.async_api import AsyncClient
from solders.message import Message, MessageV0
# from .jito_jsonrpc_sdk import JitoJsonRpcSDK
# from .storage import StorageManager
# from .settings import SettingsManager

import os
# 改为绝对导入
import sys
from pathlib import Path

current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from utilities.jito_jsonrpc_sdk import JitoJsonRpcSDK
from utilities.storage import StorageManager
from utilities.settings import SettingsManager


class PriceSwapManager:
    def __init__(self):
        trade = os.getenv("trade")
        self.trade = True if trade == "True" or trade == "true" else False
        current_dir = Path(__file__).parent
        project_root = current_dir.parent
        storage = StorageManager(data_dir=str(project_root / "data"))
        settings = SettingsManager(storage)
        self.settings_manager = settings
        self.logger = logging.getLogger(__name__)
        self.jito_client = None

    async def _init_jito_client(self):
        rpc_url = self.settings_manager.settings.get(
            "jitoRpcUrl",
            "https://jito-api.mainnet-beta.solana.com"
        )
        if not self.jito_client:
            self.jito_client = JitoJsonRpcSDK(rpc_url + "/api/v1")
        return self.jito_client

    async def check_transaction_status(self, client: AsyncClient, signature_str: str) -> bool:
        """Check the status of a transaction until it's finalized or timeout"""
        print("Checking transaction status...")
        max_attempts = 60  # 60 seconds
        attempt = 0

        signature = Signature.from_string(signature_str)

        while attempt < max_attempts:
            try:
                response = await client.get_signature_statuses([signature])

                if response.value[0] is not None:
                    status = response.value[0]
                    confirmation_status = status.confirmation_status
                    err = status.err

                    if err:
                        print(f"Transaction failed with error: {err}")
                        return False
                    elif confirmation_status == TransactionConfirmationStatus.Finalized:
                        print("Transaction is finalized.")
                        return True

                await asyncio.sleep(1)
                attempt += 1
            except Exception as e:
                print(f"Error checking transaction status: {e}")
                await asyncio.sleep(1)
                attempt += 1

        return False

    async def execute_swap(
            self,
            direction: str,
            token_address: str,
            amount: Union[int, Decimal],
            wallet_key: str,
            use_jito: bool = False,
            priority_fee: Optional[float] = None,
            tip_amount: Optional[float] = None,
            slippage_bps: int = 1,
            quote_response: Dict = {},
            price_limit: Optional[Decimal] = None,
            try_time=0
    ) -> Dict:
        entry_price = 0
        try:
            print(f'tip_amount: {tip_amount}')
            jupiter, async_client, payer = await self.create_jupiter_client(wallet_key, use_jito)

            is_buy = direction.lower() == 'buy'
            input_mint = "So11111111111111111111111111111111111111112" if is_buy else token_address
            output_mint = token_address if is_buy else "So11111111111111111111111111111111111111112"

            # Convert amount if necessary
            amount_lamports = int(amount * 1_000_000)
            if is_buy:
                amount_lamports = int(amount_lamports * 1_000)

            # Get Jupiter quote
            quote_response = await jupiter.quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount_lamports,
                # slippage_bps=slippage_bps
                slippage_bps=10000
            )

            if 'error' in quote_response:
                raise Exception(f'jupiter quote error:' + str(quote_response['error']))

            entry_price = (int(quote_response['inAmount']) / 10e9) / (int(quote_response['outAmount']) / 10e6)
            # Calculate compute unit price in micro-lamports
            compute_unit_price_micro_lamports = int(priority_fee / 14e-5) * 10_000

            # Get swap transaction
            transaction_parameters = {
                "quoteResponse": quote_response,
                "userPublicKey": str(jupiter.keypair.pubkey()),
                "computeUnitPriceMicroLamports": compute_unit_price_micro_lamports
            }

            swap_response = {'error': 'init'}
            while 'error' in swap_response:
                if swap_response['error'] != 'init':
                    print(f'error jupiter quote: {swap_response["error"]}')
                try:
                    swap_response = httpx.post(
                        url=jupiter.ENDPOINT_APIS_URL['SWAP'],
                        json=transaction_parameters
                    ).json()
                except Exception as e:
                    pass
                await asyncio.sleep(0.1)

            # Decode the transaction
            raw_tx = VersionedTransaction.from_bytes(base64.b64decode(swap_response['swapTransaction']))

            if use_jito:
                # Initialize Jito client
                jito_client = await self._init_jito_client()

                # Add Jito tip transaction if specified
                tip_amount = random.uniform(0.0001, 0.02) if not tip_amount else tip_amount
                tip_lamports = int(tip_amount * 1_000_000_000)  # Convert to lamports
                # tip_accounts = self.jito_client.get_tip_accounts()
                tip_accounts = ['DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL',
                                'ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt',
                                'Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY',
                                'DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh',
                                'HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe',
                                'ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49',
                                '3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT']
                tip_account = random.choice(tip_accounts)
                # tip_account = '96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5'
                tip_pubkey = Pubkey.from_string(tip_account)

                # Create tip instruction
                tip_ix = transfer(TransferParams(
                    from_pubkey=payer.pubkey(),
                    to_pubkey=tip_pubkey,
                    lamports=tip_lamports
                ))
                tip_tx = Transaction.new_with_payer([tip_ix], payer.pubkey())
                tip_tx.sign([payer], raw_tx.message.recent_blockhash)
                # Get the compiled instruction from the tip transaction

                # Create a new transaction that combines Jupiter swap with tip
                if isinstance(raw_tx.message, MessageV0):

                    account_keys = list(raw_tx.message.account_keys)
                    instructions = list(raw_tx.message.instructions)
                    # swap_instructions.append(tip_compiled)

                    combined_message = MessageV0(
                        raw_tx.message.header,
                        account_keys,
                        raw_tx.message.recent_blockhash,
                        instructions,
                        raw_tx.message.address_table_lookups
                    )

                else:
                    print('警告： 过时的 legacy 发现')
                    # For legacy transactions
                    swap_instructions = list(raw_tx.message.instructions)
                    swap_instructions.append(tip_ix)

                    # Create new Message with combined instructions
                    combined_message = Message(
                        raw_tx.message.header,
                        raw_tx.message.account_keys,
                        raw_tx.message.recent_blockhash,
                        swap_instructions
                    )

                # Sign the combined message
                signature = payer.sign_message(message.to_bytes_versioned(combined_message))
                signed_tx = VersionedTransaction.populate(combined_message, [signature])

                # Send transaction through Jito
                serialized_tx = base58.b58encode(bytes(signed_tx)).decode('ascii')
                serialized_tx_fee = base58.b58encode(bytes(tip_tx)).decode('ascii')

                if self.trade:
                    jito_response = jito_client.send_bundle([serialized_tx, serialized_tx_fee])
                else:
                    jito_response = {'success': True, 'data': {'result': {'value': []}}}
                print(jito_response)
                if jito_response.get('success'):
                    # result = []
                    # while result == []:
                    #     await asyncio.sleep(5)
                    #     result = jito_client.get_bundle_statuses(jito_response['data']['result'])
                    #     print(result)
                    #     value = result['data']['result']['value']
                    # if len(value) == 0:
                    #     transactions = [str(signature)]
                    # else:
                    #     transactions = value[0]['transactions']
                    transactions = [str(signature)]
                    for signature_str in transactions:
                        print('https://solscan.io/tx/' + signature_str)

                    return {
                        # "success": 'finalized',
                        "transaction_id": transactions[0],
                        "explorer_url": f"https://solscan.io/tx/{transactions[0]}",
                        "direction": direction,
                        "use_jito": use_jito,
                        "priority_fee": priority_fee,
                        "tip_amount": tip_amount,
                        "entry_price": entry_price,
                        "out_amount": int(quote_response['outAmount']) / 10e6 if direction == 'buy' else int(
                            quote_response['inAmount']) / 10e6
                    }
                else:
                    raise Exception(f"Jito transaction failed: {jito_response.get('error')}")

            else:
                # Regular transaction without Jito
                signature = payer.sign_message(message.to_bytes_versioned(raw_tx.message))
                signed_tx = VersionedTransaction.populate(raw_tx.message, [signature])

                opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
                result = await async_client.send_raw_transaction(txn=bytes(signed_tx), opts=opts)

                return {
                    "success": True,
                    "transaction_id": result.value,
                    "explorer_url": f"https://solscan.io/tx/{result.value}",
                    "direction": direction,
                    "use_jito": False,
                    "priority_fee": priority_fee,
                    "tip_amount": None,
                    "entry_price": entry_price,
                    "out_amount": int(quote_response['outAmount']) / 10e6 if direction == 'buy' else int(
                        quote_response['inAmount']) / 10e6
                }

        except Exception as e:

            traceback.print_stack()
            self.logger.error(f"Swap execution failed: {str(e)}")

            try_time += 1
            if try_time > 3:
                return {
                    "success": False,
                    "error": str(e),
                    "direction": direction,
                    "use_jito": use_jito,
                    "entry_price": entry_price
                }

            return await self.execute_swap(direction, token_address, amount, wallet_key, use_jito, priority_fee,
                                           tip_amount,
                                           slippage_bps, quote_response, price_limit, try_time)

    # Rest of the class implementation remains the same...

    def get_wallet_from_string(self, wallet_key):
        if len(wallet_key) != 44:
            if '[' in wallet_key:
                secret_key_bytes = bytes(eval(wallet_key))
                owner_pubkey = Keypair.from_bytes(secret_key_bytes)
            else:
                owner_pubkey = Keypair.from_base58_string(wallet_key)
        else:
            owner_pubkey = Pubkey.from_string(wallet_key)
        return owner_pubkey

    async def get_token_balance(self, token_address: str, wallet_address: str) -> Optional[float]:
        """
        查询指定钱包的代币余额

        Args:
            token_address (str): 代币合约地址
            wallet_address (str): 钱包地址

        Returns:
            Optional[float]: 代币余额，如果查询失败返回 None
        """
        try:
            # 创建RPC客户端连接
            _, client, _ = await self.create_jupiter_client()

            owner_pubkey = self.get_wallet_from_string(wallet_address)

            # 将地址字符串转换为Pubkey对象
            token_pubkey = Pubkey.from_string(token_address)

            # 找到代币账户地址
            # 通过 getTokenAccountsByOwner 查询指定代币的账户
            response = await client.get_token_accounts_by_owner(
                owner_pubkey.pubkey(),
                types.TokenAccountOpts(mint=token_pubkey)  # 使用 TokenAccountOpts 类
            )

            if not response.value:
                # 代币账户不存在，余额为0
                return 0

            # 获取账户数据
            token_account = response.value[0]
            balance_data = await client.get_token_account_balance(
                token_account.pubkey
            )

            if balance_data.value is None:
                return 0

            # 返回余额（考虑代币精度）
            amount = float(balance_data.value.amount)
            decimals = balance_data.value.decimals
            adjusted_amount = amount / (10 ** decimals)

            return adjusted_amount

        except Exception as e:
            self.logger.error(f"获取代币余额失败: {str(e)}")
            return None

    async def create_jupiter_client(self, wallet_key=None, use_jito=False) -> Tuple[Jupiter, AsyncClient, Keypair]:
        if use_jito:
            rpc_url = self.settings_manager.settings.get(
                "jitoRpcUrl",
                "https://jito-api.mainnet-beta.solana.com"
            )
        else:
            rpc_url = self.settings_manager.settings.get(
                "rpcUrl",
                "https://staked.helius-rpc.com?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd"
            )
        jupiter_rpc_url = self.settings_manager.settings.get(
            "JupiterRpcUrl",
            "https://jup.ag"
        )

        async_client = AsyncClient(rpc_url)

        if wallet_key:
            if '[' in wallet_key:
                secret_key_bytes = bytes(eval(wallet_key))
                payer = Keypair.from_bytes(secret_key_bytes)
            else:
                payer = Keypair.from_base58_string(wallet_key)
        else:
            secret_key_list = [79, 151, 59, 128, 131, 250, 69, 70, 57, 92, 238, 170, 76, 87, 94, 202,
                               71, 142, 40, 168, 154, 6, 91, 178, 113, 94, 115, 81, 139, 138, 15, 247,
                               230, 153, 6, 254, 174, 73, 54, 217, 191, 43, 208, 136, 73, 7, 67, 87,
                               184, 250, 182, 94, 152, 118, 15, 15, 237, 205, 206, 184, 168, 165, 66, 131]
            payer = Keypair.from_bytes(bytes(secret_key_list))

        jupiter = Jupiter(
            async_client=async_client,
            keypair=payer,
            quote_api_url=jupiter_rpc_url + "/quote?",
            swap_api_url=jupiter_rpc_url + "/swap",
            open_order_api_url=jupiter_rpc_url + "/createOrder",
            cancel_orders_api_url=jupiter_rpc_url + "/cancelOrders",
            query_open_orders_api_url=jupiter_rpc_url + "/openOrders?wallet=",
            query_order_history_api_url=jupiter_rpc_url + "/orderHistory",
            query_trade_history_api_url=jupiter_rpc_url + "/tradeHistory"
        )
        return jupiter, async_client, payer

    async def get_current_price(
            self,
            input_mint: str,
            output_mint: str,
            amount: int,
            slippage_bps: int = 100
    ) -> Optional[Dict]:
        """Gets current price by fetching the latest transaction for the token"""
        try:
            # print(f'input_mint {input_mint}\t {output_mint}')
            rpc_url = self.settings_manager.settings.get(
                "rpcUrl",
                "https://staked.helius-rpc.com?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd"
            )

            async_client = AsyncClient(rpc_url)

            # Get recent transactions for the token account
            signature_response = await async_client.get_signatures_for_address(
                Pubkey.from_string(output_mint),
                limit=200
            )

            if not signature_response.value:
                return {'error': 'No recent transactions found'}

            for sig_info in signature_response.value:
                try:
                    tx_response = await async_client.get_transaction(
                        Signature.from_string(str(sig_info.signature)),
                        # Signature.from_string('4D2tg1BRWmZ9o8MqGpXrXQuCZYAmcTeebaTifVHuFSEPDeqWf9L9uH74VJX9ASqRrDHXw77c9tB4tfhhwtwSwDfx'),
                        max_supported_transaction_version=0
                    )

                    if tx_response.value is None or tx_response.value.transaction.meta is None:
                        continue

                    meta = tx_response.value.transaction.meta
                    if meta.pre_token_balances is None or meta.post_token_balances is None:
                        continue

                    token_mint = output_mint if str(
                        output_mint) != 'So11111111111111111111111111111111111111112' else input_mint

                    target_log = ''
                    valid_inx = 0

                    token_real_change = 0

                    for pre_token_balance in meta.pre_token_balances:

                        for post_token_balance in meta.post_token_balances:
                            if pre_token_balance.account_index == post_token_balance.account_index and \
                                str(pre_token_balance.mint) == token_mint and \
                                    str(post_token_balance.mint) == token_mint:
                                token_pre_amount = int(pre_token_balance.ui_token_amount.amount)
                                token_post_amount = int(post_token_balance.ui_token_amount.amount)
                                token_real_change = abs(token_post_amount - token_pre_amount)
                                break
                        if token_real_change != 0: break

                    for log in meta.log_messages:
                        valid_log = log.replace(' ', '').split(':')[-1]
                        if len(valid_log) <= 32: continue
                        try:
                            b64_log = base64.b64decode(valid_log)
                        except Exception as e:
                            continue

                        # pump
                        for inx in range(len(b64_log) - 31):
                            token_bytes = struct.unpack('32s', b64_log[inx: inx+32])[0]
                            if str(Pubkey.from_bytes(token_bytes)) == token_mint:
                                target_log = valid_log
                                valid_inx = inx
                                break

                        if valid_inx != 0:
                            break

                        # ray v4
                        for inx in range(len(b64_log) - 7):
                            amount = struct.unpack('<Q', b64_log[inx: inx + 8])[0]

                            if abs(amount) == token_real_change:
                                target_log = valid_log
                                valid_inx = inx
                                break

                        if valid_inx != 0:
                            break

                    dex = ''
                    b64_log = base64.b64decode(target_log)
                    if valid_inx == 8:
                        dex = 'pump'
                        sol_change = struct.unpack('<Q', b64_log[40:48])[0]
                        token_change = struct.unpack('<Q', b64_log[48:56])[0]
                        price = abs(sol_change / 1e3) / abs(token_change)
                    else:
                        if valid_inx == 0:
                            price = 0
                        else:
                            dex = 'ray v4'
                            if valid_inx < 20:
                                sol_change = struct.unpack('<Q', b64_log[49:57])[0]
                            else:
                                sol_change = struct.unpack('<Q', b64_log[25:33])[0]
                                continue
                            token_change = token_real_change
                            price = abs(sol_change / 1e3) / abs(token_change)

                    if price == 0: continue
                    print(f"{price} {str(sig_info.signature)} sol:change{sol_change / 10e9} {token_change / 10e5} {dex}")
                    if price > 0.1:
                        print()

                    # await asyncio.sleep(0.5)
                    return {
                        'price': price,
                        'inAmount': sol_change,
                        'outAmount': token_change,
                        'priceImpactPct': 0.1,
                        'transaction': str(sig_info.signature)
                    }

                except Exception as e:
                    # traceback.print_stack()
                    print(f"Error processing transaction {sig_info.signature}: {str(e)}")
                    continue

            # Fallback to Jupiter quote if no valid swap transactions found
            await asyncio.sleep(2)
            return await self.get_current_price(input_mint, output_mint, amount, slippage_bps)

        except Exception as e:
            traceback.print_stack()
            return {'error': str(e)}


if __name__ == "__main__":
    import asyncio
    import os
    import sys
    from pathlib import Path
    import time

    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    sys.path.append(str(project_root))

    from utilities.storage import StorageManager
    from utilities.settings import SettingsManager


    async def monitor_price():
        storage = StorageManager(data_dir=str(project_root / "data"))
        settings = SettingsManager(storage)
        swap_manager = PriceSwapManager()

        test_token = "EUqFjf1TySMNd95d57zTFAPijGgKz34Rm35rUg2jpump"
        sol_mint = "So11111111111111111111111111111111111111112"
        amount = 100_000_000  # 0.1 SOL

        while True:
            try:
                result = await swap_manager.get_current_price(
                    input_mint=sol_mint,
                    output_mint=test_token,
                    amount=amount,
                    slippage_bps=1
                )

                # print(f'{result["price"]}\t{result["transaction"]}')


            except Exception as e:

                print(f"Error: {str(e)}")

            await asyncio.sleep(1)


    asyncio.run(monitor_price())
