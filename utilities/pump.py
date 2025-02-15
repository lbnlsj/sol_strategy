import struct
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from construct import Flag, Int64ul, Padding, Struct
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solana.rpc.commitment import Processed, Confirmed
from solana.rpc.api import Client
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.keypair import Keypair
from spl.token.instructions import get_associated_token_address, create_associated_token_account, CloseAccountParams, \
    close_account

RPC = "https://mainnet.helius-rpc.com/?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd"
UNIT_BUDGET = 100_000
UNIT_PRICE = 1_000_000
client = Client(RPC)

# PRIV_KEY = "2851U2qCNhaWtJ7UcxLVb9GJj3hWXXbN87RvSmFCD4dzAeaRQm83QoYRigjwgQpnDK3ep2bTTzUYMpevxYrcyrjc"
# payer_keypair = Keypair.from_base58_string(PRIV_KEY)

GLOBAL = Pubkey.from_string("4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf")
FEE_RECIPIENT = Pubkey.from_string("CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOC_TOKEN_ACC_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
EVENT_AUTHORITY = Pubkey.from_string("Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1")
PUMP_FUN_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")


@dataclass
class CoinData:
    mint: Pubkey
    bonding_curve: Pubkey
    associated_bonding_curve: Pubkey
    virtual_token_reserves: int
    virtual_sol_reserves: int
    token_total_supply: int
    complete: bool


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"


def confirm_txn(txn_sig, max_retries: int = 20, retry_interval: int = 3):
    retries = 1
    while retries < max_retries:
        try:
            txn_res = client.get_transaction(txn_sig, encoding="json", commitment=Confirmed,
                                             max_supported_transaction_version=0)
            txn_json = txn_res.value.transaction.meta.to_json()
            if "err" not in txn_json or txn_json["err"] is None:
                print("Transaction confirmed... try count:", retries)
                return True
            print("Transaction not confirmed. Retrying...")
            if txn_json["err"]:
                print("Transaction failed.")
                return False
        except Exception as e:
            print("Awaiting confirmation... try count:", retries)
            retries += 1
            time.sleep(retry_interval)
    print("Max retries reached. Transaction confirmation failed.")
    return None


def get_token_balance(pub_key: Pubkey, mint_str: str):
    try:
        mint = Pubkey.from_string(mint_str)
        response = client.get_token_accounts_by_owner_json_parsed(
            pub_key,
            TokenAccountOpts(mint=mint),
            commitment=Processed
        )
        accounts = response.value
        if accounts:
            token_amount = accounts[0].account.data.parsed['info']['tokenAmount']['uiAmount']
            return float(token_amount)
        return None
    except Exception as e:
        print(f"Error fetching token balance: {e}")
        return None


def sol_for_tokens(sol_spent, sol_reserves, token_reserves):
    new_sol_reserves = sol_reserves + sol_spent
    new_token_reserves = (sol_reserves * token_reserves) / new_sol_reserves
    token_received = token_reserves - new_token_reserves
    return round(token_received)


def tokens_for_sol(tokens_to_sell, sol_reserves, token_reserves):
    new_token_reserves = token_reserves + tokens_to_sell
    new_sol_reserves = (sol_reserves * token_reserves) / new_token_reserves
    sol_received = sol_reserves - new_sol_reserves
    return sol_received


def get_virtual_reserves(bonding_curve: Pubkey):
    bonding_curve_struct = Struct(
        Padding(8),
        "virtualTokenReserves" / Int64ul,
        "virtualSolReserves" / Int64ul,
        "realTokenReserves" / Int64ul,
        "realSolReserves" / Int64ul,
        "tokenTotalSupply" / Int64ul,
        "complete" / Flag
    )
    try:
        account_info = client.get_account_info(bonding_curve)
        data = account_info.value.data
        parsed_data = bonding_curve_struct.parse(data)
        return parsed_data
    except Exception:
        return None


def derive_bonding_curve_accounts(mint_str: str):
    try:
        mint = Pubkey.from_string(mint_str)
        bonding_curve, _ = Pubkey.find_program_address(
            ["bonding-curve".encode(), bytes(mint)],
            PUMP_FUN_PROGRAM
        )
        associated_bonding_curve = get_associated_token_address(bonding_curve, mint)
        return bonding_curve, associated_bonding_curve
    except Exception:
        return None, None


def get_complete(mint_str: str) -> bool:
    try_time = 3
    for t in range(try_time):
        try:
            coin_data = get_coin_data(mint_str)
            return coin_data.complete
        except Exception as e:
            print(f'获取发射状态异常：{e}')


def get_coin_data(mint_str: str) -> Optional[CoinData]:
    bonding_curve, associated_bonding_curve = derive_bonding_curve_accounts(mint_str)
    if bonding_curve is None or associated_bonding_curve is None:
        return None
    virtual_reserves = get_virtual_reserves(bonding_curve)
    if virtual_reserves is None:
        return None
    try:
        return CoinData(
            mint=Pubkey.from_string(mint_str),
            bonding_curve=bonding_curve,
            associated_bonding_curve=associated_bonding_curve,
            virtual_token_reserves=int(virtual_reserves.virtualTokenReserves),
            virtual_sol_reserves=int(virtual_reserves.virtualSolReserves),
            token_total_supply=int(virtual_reserves.tokenTotalSupply),
            complete=bool(virtual_reserves.complete),
        )
    except Exception as e:
        print(e)
        return None


def buy(mint_str: str, sol_in: float = 0.01, slippage: int = 5):
    try:
        instructions = buy_instruction(mint_str, sol_in, slippage)
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )
        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True)
        ).value
        print(f"https://solscan.io/tx/{txn_sig}")
        return txn_sig
    except Exception as e:
        print(f"Error occurred during transaction: {e}")
        return False


def buy_instruction(mint_str: str, sol_in: float = 0.01, slippage: int = 5, payer_keypair: Keypair=None):
    print(f"Starting buy transaction for mint: {mint_str}")
    coin_data = get_coin_data(mint_str)
    if not coin_data:
        print("Failed to retrieve coin data.")
        return False
    if coin_data.complete:
        print("Warning: This token has bonded and is only tradable on Raydium.")
        return
    MINT = coin_data.mint
    BONDING_CURVE = coin_data.bonding_curve
    ASSOCIATED_BONDING_CURVE = coin_data.associated_bonding_curve
    USER = payer_keypair.pubkey()
    # USER = payer_keypair
    try:
        ASSOCIATED_USER = client.get_token_accounts_by_owner(USER, TokenAccountOpts(MINT)).value[0].pubkey
        token_account_instruction = None
    except:
        ASSOCIATED_USER = get_associated_token_address(USER, MINT)
        token_account_instruction = create_associated_token_account(USER, USER, MINT)
    sol_dec = 1e9
    token_dec = 1e6
    virtual_sol_reserves = coin_data.virtual_sol_reserves / sol_dec
    virtual_token_reserves = coin_data.virtual_token_reserves / token_dec
    amount = sol_for_tokens(sol_in, virtual_sol_reserves, virtual_token_reserves)
    amount = int(amount * token_dec)
    slippage_adjustment = 1 + (slippage / 100)
    max_sol_cost = int((sol_in * slippage_adjustment) * sol_dec)
    keys = [
        AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
        AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
        AccountMeta(pubkey=MINT, is_signer=False, is_writable=False),
        AccountMeta(pubkey=BONDING_CURVE, is_signer=False, is_writable=True),
        AccountMeta(pubkey=ASSOCIATED_BONDING_CURVE, is_signer=False, is_writable=True),
        AccountMeta(pubkey=ASSOCIATED_USER, is_signer=False, is_writable=True),
        AccountMeta(pubkey=USER, is_signer=True, is_writable=True),
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
        AccountMeta(pubkey=RENT, is_signer=False, is_writable=False),
        AccountMeta(pubkey=EVENT_AUTHORITY, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PUMP_FUN_PROGRAM, is_signer=False, is_writable=False)
    ]
    data = bytearray()
    data.extend(bytes.fromhex("66063d1201daebea"))
    data.extend(struct.pack('<Q', amount))
    data.extend(struct.pack('<Q', max_sol_cost))
    swap_instruction = Instruction(PUMP_FUN_PROGRAM, bytes(data), keys)
    instructions = [
        set_compute_unit_limit(UNIT_BUDGET),
        set_compute_unit_price(UNIT_PRICE),
    ]
    if token_account_instruction:
        instructions.append(token_account_instruction)
    instructions.append(swap_instruction)
    return instructions


def sell_instruction(mint_str: str, amount: int = 100, slippage: int = 5, payer_keypair: Pubkey=None):
    print(f"Starting sell transaction for mint: {mint_str}")
    # if not (1 <= percentage <= 100):
    #     print("Percentage must be between 1 and 100.")
    #     return False
    coin_data = get_coin_data(mint_str)
    if not coin_data:
        print("Failed to retrieve coin data.")
        return False
    if coin_data.complete:
        print("Warning: This token has bonded and is only tradable on Raydium.")
        return
    MINT = coin_data.mint
    BONDING_CURVE = coin_data.bonding_curve
    ASSOCIATED_BONDING_CURVE = coin_data.associated_bonding_curve
    # USER = payer_keypair.pubkey()
    USER = payer_keypair
    ASSOCIATED_USER = get_associated_token_address(USER, MINT)
    print("Retrieving token balance...")
    token_balance = get_token_balance(payer_keypair.pubkey(), mint_str)
    # if token_balance == 0 or token_balance is None:
    #     print("Token balance is zero. Nothing to sell.")
    #     return False
    # print(f"Token Balance: {token_balance}")
    sol_dec = 1e9
    token_dec = 1e6
    # amount = int(token_balance * token_dec)
    amount = int(amount * 1_000_000)
    virtual_sol_reserves = coin_data.virtual_sol_reserves / sol_dec
    virtual_token_reserves = coin_data.virtual_token_reserves / token_dec
    sol_out = tokens_for_sol(token_balance, virtual_sol_reserves, virtual_token_reserves)
    slippage_adjustment = 1 - (slippage / 100)
    min_sol_output = int((sol_out * slippage_adjustment) * sol_dec)
    print(f"Amount: {amount}, Minimum Sol Out: {min_sol_output}")
    keys = [
        AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
        AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
        AccountMeta(pubkey=MINT, is_signer=False, is_writable=False),
        AccountMeta(pubkey=BONDING_CURVE, is_signer=False, is_writable=True),
        AccountMeta(pubkey=ASSOCIATED_BONDING_CURVE, is_signer=False, is_writable=True),
        AccountMeta(pubkey=ASSOCIATED_USER, is_signer=False, is_writable=True),
        AccountMeta(pubkey=USER, is_signer=True, is_writable=True),
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        AccountMeta(pubkey=ASSOC_TOKEN_ACC_PROG, is_signer=False, is_writable=False),
        AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
        AccountMeta(pubkey=EVENT_AUTHORITY, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PUMP_FUN_PROGRAM, is_signer=False, is_writable=False)
    ]
    data = bytearray()
    data.extend(bytes.fromhex("33e685a4017f83ad"))
    data.extend(struct.pack('<Q', amount))
    data.extend(struct.pack('<Q', min_sol_output))
    swap_instruction = Instruction(PUMP_FUN_PROGRAM, bytes(data), keys)
    instructions = [
        set_compute_unit_limit(UNIT_BUDGET),
        set_compute_unit_price(UNIT_PRICE),
        swap_instruction,
    ]
    # if percentage == 100:
    #     print("Preparing to close token account after swap...")
    #     close_account_instruction = close_account(CloseAccountParams(TOKEN_PROGRAM, ASSOCIATED_USER, USER, USER))
    #     instructions.append(close_account_instruction)
    print("Compiling transaction message...")
    return instructions


def sell(mint_str: str, percentage: int = 100, slippage: int = 5):
    try:
        instructions = sell_instruction(mint_str, percentage, slippage)
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )
        print("Sending transaction...")
        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=False)
        ).value
        print(f"https://solscan.io/tx/{txn_sig}")
        return txn_sig
    except Exception as e:
        print(f"Error occurred during transaction: {e}")
        return False


def trade_pump(mint_address: str, direction: str, amount: float, slippage: float = 1):
    try:
        try:
            trade_direction = TradeDirection(direction.lower())
        except ValueError:
            print("Error: Direction must be either 'buy' or 'sell'")
            return False
        if trade_direction == TradeDirection.BUY:
            return buy(mint_address, amount, slippage)
        else:
            return sell(mint_address, amount, slippage)
    except Exception as e:
        print(f"Unexpected error during trade: {e}")
        return False


if __name__ == "__main__":
    mint_str = "Hh6G53nFBGNGyjHwkDkHrtShcxxw9Yy9WvS23Zgjpump"
    # print(get_complete(mint_str))
    # trade_pump(mint_str, "buy", 0.01, 100)  # Buy 0.1 SOL worth with 1% slippage
    trade_pump(mint_str, "sell", 100, 100)  # Sell 100% with 1% slippage
