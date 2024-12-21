# main.py
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.instruction import Instruction
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solana.rpc.types import TokenAccountOpts, TxOpts
from spl.token.instructions import get_associated_token_address, create_associated_token_account
import struct
from solana.transaction import AccountMeta  # 添加 AccountMeta 导入
from dataclasses import dataclass
from typing import Optional

# Constants
GLOBAL = Pubkey.from_string("4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf")
FEE_RECIPIENT = Pubkey.from_string("CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
PUMP_FUN_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
RENT = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
EVENT_AUTHORITY = Pubkey.from_string("Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1")
ASSOC_TOKEN_ACC_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

# Configuration
RPC_URL = "https://staked.helius-rpc.com?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd"
PRIVATE_KEY = "your_base58_private_key_here"
UNIT_BUDGET = 100_000
UNIT_PRICE = 333_333

client = Client(RPC_URL)
secret_key_list = [79, 151, 59, 128, 131, 250, 69, 70, 57, 92, 238, 170, 76, 87, 94, 202, 71, 142, 40, 168, 154, 6, 91,
                   178, 113, 94, 115, 81, 139, 138, 15, 247, 230, 153, 6, 254, 174, 73, 54, 217, 191, 43, 208, 136, 73,
                   7, 67, 87, 184, 250, 182, 94, 152, 118, 15, 15, 237, 205, 206, 184, 168, 165, 66, 131]
secret_key_bytes = bytes(secret_key_list)

payer = Keypair.from_bytes(secret_key_bytes)


@dataclass
class CoinData:
    mint: Pubkey
    bonding_curve: Pubkey
    associated_bonding_curve: Pubkey
    virtual_token_reserves: int
    virtual_sol_reserves: int
    complete: bool


def get_coin_data(mint_str: str) -> Optional[CoinData]:
    try:
        mint = Pubkey.from_string(mint_str)

        # Derive bonding curve address
        bonding_curve, _ = Pubkey.find_program_address(
            ["bonding-curve".encode(), bytes(mint)],
            PUMP_FUN_PROGRAM
        )

        # Get associated token account
        associated_bonding_curve = get_associated_token_address(bonding_curve, mint)

        # Get account info
        account_info = client.get_account_info(bonding_curve)
        if not account_info.value:
            return None

        # Parse account data
        data = account_info.value.data
        virtual_token_reserves = int.from_bytes(data[8:16], 'little')
        virtual_sol_reserves = int.from_bytes(data[16:24], 'little')
        complete = bool(data[-1])

        return CoinData(
            mint=mint,
            bonding_curve=bonding_curve,
            associated_bonding_curve=associated_bonding_curve,
            virtual_token_reserves=virtual_token_reserves,
            virtual_sol_reserves=virtual_sol_reserves,
            complete=complete
        )
    except Exception as e:
        print(f"Error getting coin data: {e}")
        return None


def buy_token(mint_str: str, sol_amount: float = 0.01, slippage: int = 5) -> bool:
    try:
        print(f"Buying token {mint_str}")

        coin_data = get_coin_data(mint_str)
        if not coin_data:
            print("Invalid token or token has completed bonding")
            return False

        # 修改金额计算逻辑
        sol_lamports = int(sol_amount * 1e18)  # 转换为 lamports
        amount = sol_lamports  # 使用确切的 lamports 数量作为 amount
        slippage_adjusted = int(sol_lamports * (1 + slippage / 100))

        print(f"Amount (lamports): {amount}")
        print(f"Max sol cost (lamports): {slippage_adjusted}")
        print(f"Virtual sol reserves: {coin_data.virtual_sol_reserves}")
        print(f"Virtual token reserves: {coin_data.virtual_token_reserves}")

        user_ata = get_associated_token_address(payer.pubkey(), coin_data.mint)
        create_ata_ix = None

        try:
            client.get_token_accounts_by_owner(payer.pubkey(), TokenAccountOpts(coin_data.mint))
        except:
            create_ata_ix = create_associated_token_account(
                payer.pubkey(),
                payer.pubkey(),
                coin_data.mint
            )

        keys = [
            AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
            AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
            AccountMeta(pubkey=coin_data.mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=coin_data.bonding_curve, is_signer=False, is_writable=True),
            AccountMeta(pubkey=coin_data.associated_bonding_curve, is_signer=False, is_writable=True),
            AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=RENT, is_signer=False, is_writable=False),
            AccountMeta(pubkey=EVENT_AUTHORITY, is_signer=False, is_writable=False),
            AccountMeta(pubkey=PUMP_FUN_PROGRAM, is_signer=False, is_writable=False)
        ]

        # 构建交易数据
        data = bytearray(bytes.fromhex("66063d1201daebea"))  # buy instruction discriminator
        data.extend(struct.pack("<Q", int(coin_data.virtual_token_reserves / coin_data.virtual_sol_reserves * 10 ** 10 * amount / 10e18)))  # amount in lamports
        data.extend(struct.pack("<Q", int(amount * 1.1)))  # max_sol_cost in lamports

        swap_ix = Instruction(PUMP_FUN_PROGRAM, bytes(data), keys)

        instructions = [
            set_compute_unit_limit(UNIT_BUDGET),
            set_compute_unit_price(UNIT_PRICE)
        ]

        if create_ata_ix:
            instructions.append(create_ata_ix)
        instructions.append(swap_ix)

        blockhash = client.get_latest_blockhash().value.blockhash
        message = MessageV0.try_compile(
            payer.pubkey(),
            instructions,
            [],
            blockhash
        )

        tx = VersionedTransaction(message, [payer])
        sig = client.send_transaction(tx, opts=TxOpts(skip_preflight=True)).value

        print(f"Transaction sent: {sig}")
        return True

    except Exception as e:
        print(f"Error during buy: {e}")
        return False



def sell_token(mint_str: str, percentage: int = 100, slippage: int = 5) -> bool:
    try:
        print(f"Selling {percentage}% of token {mint_str}")

        coin_data = get_coin_data(mint_str)
        if not coin_data:
            print("Invalid token or token has completed bonding")
            return False

        # Get token balance
        user_ata = get_associated_token_address(payer.pubkey(), coin_data.mint)
        token_account = client.get_token_accounts_by_owner(
            payer.pubkey(),
            TokenAccountOpts(coin_data.mint)
        ).value[0]

        data = token_account.account.data
        balance = int.from_bytes(data[64:72], 'little')
        amount = int(balance * percentage / 100)

        if amount == 0:
            print("No tokens to sell")
            return False

        # Calculate minimum SOL output
        virtual_sol = coin_data.virtual_sol_reserves / 1e9
        virtual_tokens = coin_data.virtual_token_reserves / 1e6
        expected_sol = (virtual_sol * amount) / (virtual_tokens + amount)
        min_sol = int(expected_sol * (1 - slippage / 100) * 1e9)

        # Create swap instruction
        keys = [
            AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
            AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
            AccountMeta(pubkey=coin_data.mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=coin_data.bonding_curve, is_signer=False, is_writable=True),
            AccountMeta(pubkey=coin_data.associated_bonding_curve, is_signer=False, is_writable=True),
            AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=ASSOC_TOKEN_ACC_PROG, is_signer=False, is_writable=False),  # Added
            AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=EVENT_AUTHORITY, is_signer=False, is_writable=False),
            AccountMeta(pubkey=PUMP_FUN_PROGRAM, is_signer=False, is_writable=False)
        ]

        data = bytearray(bytes.fromhex("33e685a4017f83ad"))
        data.extend(struct.pack("<Q", amount))
        data.extend(struct.pack("<Q", 1))

        swap_ix = Instruction(PUMP_FUN_PROGRAM, bytes(data), keys)

        # Build and send transaction
        blockhash = client.get_latest_blockhash().value.blockhash
        message = MessageV0.try_compile(
            payer.pubkey(),
            [
                set_compute_unit_limit(UNIT_BUDGET),
                set_compute_unit_price(UNIT_PRICE),
                swap_ix
            ],
            [],
            blockhash
        )

        tx = VersionedTransaction(message, [payer])
        sig = client.send_transaction(tx, opts=TxOpts(skip_preflight=True)).value

        print(f"Transaction sent: {sig}")
        return True

    except Exception as e:
        print(f"Error during sell: {e}")
        return False


# Example usage
if __name__ == "__main__":
    pass
    # Buy example
    # buy_token("HAReKWhADs64eS18eB75LiU8UhkBkLmsauS475kjpump", 0.001, 5)

    # Sell example
    # sell_token("HAReKWhADs64eS18eB75LiU8UhkBkLmsauS475kjpump", 10, 5)