from datetime import datetime
import asyncio
from solana.rpc.websocket_api import connect
from solders.pubkey import Pubkey
from solders.rpc.config import RpcTransactionLogsConfig
from solders.rpc.config import RpcTransactionLogsFilter, RpcTransactionLogsFilterMentions
from solana.rpc.commitment import Commitment
import json
import base64
import struct

LAMPORTS_PER_SOL = 1_000_000_000


class SolanaLogsMonitor:
    def __init__(self):
        """
        Initialize the Solana logs monitor with Helius endpoint
        """
        self.endpoint = "wss://mainnet.helius-rpc.com/?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd"
        self.subscription_id = None
        self.websocket = None
        self.switch = True
        self.block_info = {}
        # Token program ID
        self.TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        # Associated Token program ID
        self.ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        if not self.is_pump_token_creation(['Program returned success',
                                            'Program log: Instruction: Create',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Invoking Token Program',
                                            'Program log: Instruction: InitializeMint2',
                                            'Program Token Program consumed 2780 of 228444 compute units',
                                            'Program returned success',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Invoking Associated Token Account Program',
                                            'Program log: Create',
                                            'Invoking Token Program',
                                            'Program log: Instruction: GetAccountDataSize',
                                            'Program Token Program consumed 1595 of 207548 compute units',
                                            'Program return: TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA pQAAAAAAAAA=',
                                            'Program returned success',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Program log: Initialize the associated token account',
                                            'Invoking Token Program',
                                            'Program log: Instruction: InitializeImmutableOwner',
                                            'Program log: Please upgrade to SPL Token 2022 for immutable owner support',
                                            'Program Token Program consumed 1405 of 200935 compute units',
                                            'Program returned success',
                                            'Invoking Token Program',
                                            'Program log: Instruction: InitializeAccount3',
                                            'Program Token Program consumed 4214 of 197051 compute units',
                                            'Program returned success',
                                            'Program Associated Token Account Program consumed 20490 of 213023 compute units',
                                            'Program returned success',
                                            'Invoking Metaplex Token Metadata',
                                            'Program log: IX: Create Metadata Accounts v3',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Program log: Allocate space for the account',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Program log: Assign the account to the owning program',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Program Metaplex Token Metadata consumed 35222 of 177584 compute units',
                                            'Program returned success',
                                            'Invoking Token Program',
                                            'Program log: Instruction: MintTo',
                                            'Program Token Program consumed 4492 of 139847 compute units',
                                            'Program returned success',
                                            'Invoking Token Program',
                                            'Program log: Instruction: SetAuthority',
                                            'Program Token Program consumed 2911 of 133208 compute units',
                                            'Program returned success',
                                            'Invoking Pump.fun',
                                            'Program Pump.fun consumed 2003 of 126148 compute units',
                                            'Program returned success',
                                            'Program data: G3KpTd7rY3YLAAAAUm9hY2ggVG9rZW4FAAAAUk9BQ0hDAAAAaHR0cHM6Ly9pcGZzLmlvL2lwZnMvUW1SNUtYcU50ZkxwQWlqYW8zSjZueDJqcDltUW1uTHJhM3h3MllCRmRaYlVlUH521hPlKRNWIj9ImsPRSDEHgOc9DK4XBKN/GRDXKcOfYHI9n3/oAfrOR9ELHkoAtT8EKF36zirAHY345n5dx4Qt6/vJ3sxlPPv+XGgLUXHQfVXJ55NsBL9lVa0A+GxTAg==',
                                            'Program Pump.fun consumed 117556 of 239850 compute units',
                                            'Program returned success',
                                            'Program log: Create',
                                            'Invoking Token Program',
                                            'Program log: Instruction: GetAccountDataSize',
                                            'Program Token Program consumed 1569 of 110931 compute units',
                                            'Program return: TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA pQAAAAAAAAA=',
                                            'Program returned success',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Program log: Initialize the associated token account',
                                            'Invoking Token Program',
                                            'Program log: Instruction: InitializeImmutableOwner',
                                            'Program log: Please upgrade to SPL Token 2022 for immutable owner support',
                                            'Program Token Program consumed 1405 of 104344 compute units',
                                            'Program returned success',
                                            'Invoking Token Program',
                                            'Program log: Instruction: InitializeAccount3',
                                            'Program Token Program consumed 4188 of 100464 compute units',
                                            'Program returned success',
                                            'Program Associated Token Account Program consumed 26301 of 122294 compute units',
                                            'Program returned success',
                                            'Program log: Instruction: Buy',
                                            'Invoking Token Program',
                                            'Program log: Instruction: Transfer',
                                            'Program Token Program consumed 4645 of 77272 compute units',
                                            'Program returned success',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Invoking System Program',
                                            'Program returned success',
                                            'Invoking Pump.fun',
                                            'Program Pump.fun consumed 2003 of 65184 compute units',
                                            'Program returned success',
                                            'Program data: vdt/007mYe5+dtYT5SkTViI/SJrD0UgxB4DnPQyuFwSjfxkQ1ynDn4BfrqgAAAAAP6LDhR9UAAABLev7yd7MZTz7/lxoC1Fx0H1VyeeTbAS/ZVWtAPhsUwKs3F1nAAAAAIAL0qQHAAAAwW0UwsN7AwCAX66oAAAAAMHVAXYyfQIA',
                                            'Program Pump.fun consumed 34537 of 95993 compute units',
                                            'Program returned success',
                                            'Program returned success']):
            print(' 函数有问题 ')
            exit()
        else:
            print()

    def parse_token_info(self, logs):
        """
        Parse token information from logs
        """
        token_info = {
            'name': None,
            'symbol': None,
            'mint_address': None
        }

        for i, log in enumerate(logs):
            # Look for program data that contains token information
            if log.startswith('Program data:'):
                try:
                    # Get the base64 data
                    data = log.split('Program data: ')[1]
                    # Decode base64 data
                    decoded = base64.b64decode(data)
                    # Extract readable strings
                    readable = ''.join(chr(c) if 32 <= c <= 126 else ' ' for c in decoded)
                    # Split by spaces and look for token info
                    parts = readable.split()
                    for j, part in enumerate(parts):
                        if j + 1 < len(parts):
                            if len(part) >= 3:  # Token name or symbol
                                if token_info['name'] is None:
                                    token_info['name'] = part
                                elif token_info['symbol'] is None:
                                    token_info['symbol'] = part
                except:
                    continue

            # Look for mint address in create instruction
            elif "Create" in log and i > 0:
                prev_log = logs[i - 1]
                if "Invoking Token Program" in prev_log:
                    words = log.split()
                    for word in words:
                        if len(word) >= 32:  # Likely a Solana address
                            token_info['mint_address'] = word
                            break

        return token_info

    @staticmethod
    def parse_create_event_log(base64_log: str):
        """
        Parse a base64 encoded create event log for Solana.

        Args:
            base64_log (str): Base64 encoded log data

        Returns:
            str: The mint address as a string
        """
        # 1. 解码base64数据
        buffer = base64.b64decode(base64_log)


        # 2. 创建一个offset变量来追踪位置
        offset = [8]  # 跳过discriminator

        # 3. 解析字符串的辅助函数
        def parse_string() -> str:
            # 读取字符串长度
            length = int.from_bytes(buffer[offset[0]:offset[0] + 4], 'little')
            offset[0] += 4

            # 读取字符串内容
            string_data = buffer[offset[0]:offset[0] + length].decode('utf-8')
            offset[0] += length

            return string_data

        # 4. 解析PublicKey的辅助函数
        def parse_public_key() -> Pubkey:
            key_bytes = buffer[offset[0]:offset[0] + 32]
            offset[0] += 32
            return Pubkey(key_bytes)

        # 5. 解析数据
        try:
            name = parse_string()
            symbol = parse_string()
            uri = parse_string()
            mint = parse_public_key()
            bonding_curve = parse_public_key()
            user = parse_public_key()
        except ValueError:
            return None
        result = {
            "name": name,
            "symbol": symbol,
            "mint": str(mint),
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        print(result)
        # 打印日志
        return result

    def is_pump_token_creation(self, logs):
        """
        分析日志判断是否为pump token的创建
        基于实际日志模式识别
        """
        lgs = [d for d in logs if len(d) > 200 and 'Program data:' in d]
        if not lgs:
            return False

        token_info = self.parse_create_event_log(lgs[0].split('Program data:')[1])

        return token_info

    async def handle_log_message(self, msg):
        """
        Handle the received log message
        """
        try:
            if hasattr(msg, 'result'):
                result = msg.result
                # if hasattr(result, 'context'):
                #     slot = result.context.slot
                #     print(f"Block: https://solscan.io/block/{slot}")
                #     print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                if hasattr(result, 'value'):
                    value = result.value
                    # 检查是否有signature和logs
                    if hasattr(value, 'signature') and hasattr(value, 'logs'):
                        tx_signature = value.signature
                        logs = value.logs

                        # 检查是否为pump token创建
                        if self.is_pump_token_creation(logs):
                            print(f"Transaction: https://solscan.io/tx/{tx_signature}")

            return True

        except Exception as e:
            print(f"Error processing message: {e}")
            print(f"Message: {msg}")

    async def start_monitoring(self, program_id: str = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"):
        """
        Start monitoring logs for token program
        """
        try:
            async with connect(self.endpoint) as websocket:
                self.websocket = websocket

                # 创建Token程序的过滤器
                filter_ = RpcTransactionLogsFilterMentions(
                    Pubkey.from_string(program_id)
                )

                # 订阅日志
                await websocket.logs_subscribe(
                    filter_=filter_,
                    commitment=Commitment("processed")
                )

                # 获取订阅ID
                first_resp = await websocket.recv()
                self.subscription_id = first_resp[0].result

                print(f"Started monitoring token program: {program_id}")
                print(f"Subscription ID: {self.subscription_id}")
                print("Waiting for pump token creation events...")

                # 持续监控日志
                async for msg in websocket:
                    await self.handle_log_message(msg[0])

        except Exception as e:
            print(f"Error in monitoring: {e}")
            await self.stop_monitoring()
            raise

    async def stop_monitoring(self):
        """
        Stop monitoring logs and clean up
        """
        if self.websocket and self.subscription_id:
            try:
                await self.websocket.logs_unsubscribe(self.subscription_id)
                print(f"Stopped monitoring logs for subscription: {self.subscription_id}")
            except Exception as e:
                print(f"Error stopping monitor: {e}")
                raise
            finally:
                self.subscription_id = None
                self.websocket = None


async def main():
    monitor = SolanaLogsMonitor()

    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        await monitor.stop_monitoring()
    except Exception as e:
        print(f"Error in main: {e}")
        await monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
