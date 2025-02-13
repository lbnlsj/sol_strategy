import base64
import os
import time
import struct
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from construct import Bytes, Int32ul, Int8ul, Int64ul, Padding, BitsInteger, BitsSwapped, BitStruct, Const, Flag, \
    BytesInteger
from construct import Struct as cStruct
from solana.rpc.commitment import Processed, Confirmed
from solana.rpc.types import TokenAccountOpts, TxOpts, MemcmpOpts
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.keypair import Keypair
from solders.system_program import CreateAccountWithSeedParams, create_account_with_seed
from spl.token.client import Token
from spl.token.instructions import get_associated_token_address, create_associated_token_account, CloseAccountParams, \
    close_account, InitializeAccountParams, initialize_account
from solana.rpc.api import Client

# Constants
RPC = "https://mainnet.helius-rpc.com/?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd"
PRIV_KEY = "2851U2qCNhaWtJ7UcxLVb9GJj3hWXXbN87RvSmFCD4dzAeaRQm83QoYRigjwgQpnDK3ep2bTTzUYMpevxYrcyrjc"
UNIT_BUDGET = 100_000
UNIT_PRICE = 1_000_000

# Initialize client and keypair
client = Client(RPC)
payer_keypair = Keypair.from_base58_string(PRIV_KEY)

# Program IDs
RAYDIUM_AMM_V4 = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
RAYDIUM_CPMM = Pubkey.from_string("CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C")
RAYDIUM_CLMM = Pubkey.from_string("CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK")
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
RAYDIUM_LIQUIDITY_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

# Constants
ACCOUNT_LAYOUT_LEN = 165
SOL_DECIMAL = 1e9

# Layout definitions
LIQUIDITY_STATE_LAYOUT_V4 = cStruct(
    "status" / Int64ul,
    "nonce" / Int64ul,
    "orderNum" / Int64ul,
    "depth" / Int64ul,
    "coinDecimals" / Int64ul,
    "pcDecimals" / Int64ul,
    "state" / Int64ul,
    "resetFlag" / Int64ul,
    "minSize" / Int64ul,
    "volMaxCutRatio" / Int64ul,
    "amountWaveRatio" / Int64ul,
    "coinLotSize" / Int64ul,
    "pcLotSize" / Int64ul,
    "minPriceMultiplier" / Int64ul,
    "maxPriceMultiplier" / Int64ul,
    "systemDecimalsValue" / Int64ul,
    "minSeparateNumerator" / Int64ul,
    "minSeparateDenominator" / Int64ul,
    "tradeFeeNumerator" / Int64ul,
    "tradeFeeDenominator" / Int64ul,
    "pnlNumerator" / Int64ul,
    "pnlDenominator" / Int64ul,
    "swapFeeNumerator" / Int64ul,
    "swapFeeDenominator" / Int64ul,
    "needTakePnlCoin" / Int64ul,
    "needTakePnlPc" / Int64ul,
    "totalPnlPc" / Int64ul,
    "totalPnlCoin" / Int64ul,
    "poolOpenTime" / Int64ul,
    "punishPcAmount" / Int64ul,
    "punishCoinAmount" / Int64ul,
    "orderbookToInitTime" / Int64ul,
    "swapCoinInAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapPcOutAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapCoin2PcFee" / Int64ul,
    "swapPcInAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapCoinOutAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapPc2CoinFee" / Int64ul,
    "poolCoinTokenAccount" / Bytes(32),
    "poolPcTokenAccount" / Bytes(32),
    "coinMintAddress" / Bytes(32),
    "pcMintAddress" / Bytes(32),
    "lpMintAddress" / Bytes(32),
    "ammOpenOrders" / Bytes(32),
    "serumMarket" / Bytes(32),
    "serumProgramId" / Bytes(32),
    "ammTargetOrders" / Bytes(32),
    "poolWithdrawQueue" / Bytes(32),
    "poolTempLpTokenAccount" / Bytes(32),
    "ammOwner" / Bytes(32),
    "pnlOwner" / Bytes(32),
)

ACCOUNT_FLAGS_LAYOUT = BitsSwapped(
    BitStruct(
        "initialized" / Flag,
        "market" / Flag,
        "open_orders" / Flag,
        "request_queue" / Flag,
        "event_queue" / Flag,
        "bids" / Flag,
        "asks" / Flag,
        Const(0, BitsInteger(57)),
    )
)

MARKET_STATE_LAYOUT_V3 = cStruct(
    Padding(5),
    "account_flags" / ACCOUNT_FLAGS_LAYOUT,
    "own_address" / Bytes(32),
    "vault_signer_nonce" / Int64ul,
    "base_mint" / Bytes(32),
    "quote_mint" / Bytes(32),
    "base_vault" / Bytes(32),
    "base_deposits_total" / Int64ul,
    "base_fees_accrued" / Int64ul,
    "quote_vault" / Bytes(32),
    "quote_deposits_total" / Int64ul,
    "quote_fees_accrued" / Int64ul,
    "quote_dust_threshold" / Int64ul,
    "request_queue" / Bytes(32),
    "event_queue" / Bytes(32),
    "bids" / Bytes(32),
    "asks" / Bytes(32),
    "base_lot_size" / Int64ul,
    "quote_lot_size" / Int64ul,
    "fee_rate_bps" / Int64ul,
    "referrer_rebate_accrued" / Int64ul,
    Padding(7),
)


@dataclass
class AmmV4PoolKeys:
    amm_id: Pubkey
    base_mint: Pubkey
    quote_mint: Pubkey
    base_decimals: int
    quote_decimals: int
    open_orders: Pubkey
    target_orders: Pubkey
    base_vault: Pubkey
    quote_vault: Pubkey
    market_id: Pubkey
    market_authority: Pubkey
    market_base_vault: Pubkey
    market_quote_vault: Pubkey
    bids: Pubkey
    asks: Pubkey
    event_queue: Pubkey
    ray_authority_v4: Pubkey
    open_book_program: Pubkey
    token_program_id: Pubkey


def get_liquidity_pool(client, mint_str: str) -> Optional[str]:
    raydium_program_id = Pubkey.from_string(RAYDIUM_LIQUIDITY_V4)
    sol_mint = Pubkey.from_string("So11111111111111111111111111111111111111112")
    token_mint = Pubkey.from_string(mint_str)

    pools = client.get_program_accounts(
        raydium_program_id,
        filters=[
            MemcmpOpts(offset=400, bytes=str(sol_mint)),
            MemcmpOpts(offset=432, bytes=str(token_mint))
        ]
    )
    if len(pools.value) == 0:
        return None
    else:
        return str(pools.value[0].pubkey)


def confirm_txn(txn_sig, max_retries: int = 20, retry_interval: int = 3):
    retries = 1
    while retries < max_retries:
        try:
            txn_res = client.get_transaction(txn_sig, encoding="json", commitment=Confirmed,
                                             max_supported_transaction_version=0)
            if txn_res.value.transaction.meta.err is None:
                print("Transaction confirmed... try count:", retries)
                return True
            print("Transaction not confirmed. Retrying...")
            if txn_res.value.transaction.meta.err:
                print("Transaction failed.")
                return False
        except Exception as e:
            print("Awaiting confirmation... try count:", retries)
            retries += 1
            time.sleep(retry_interval)
    print("Max retries reached. Transaction confirmation failed.")
    return None


def get_token_balance(mint_str: str) -> Optional[float]:
    try:
        mint = Pubkey.from_string(mint_str)
        response = client.get_token_accounts_by_owner_json_parsed(
            payer_keypair.pubkey(),
            TokenAccountOpts(mint=mint),
            commitment=Processed
        )
        if response.value:
            token_amount = response.value[0].account.data.parsed['info']['tokenAmount']['uiAmount']
            return float(token_amount)
        return None
    except Exception as e:
        print(f"Error fetching token balance: {e}")
        return None


def sol_for_tokens(sol_amount: float, base_vault_balance: float, quote_vault_balance: float,
                   swap_fee: float = 0.25) -> float:
    effective_sol_used = sol_amount - (sol_amount * (swap_fee / 100))
    constant_product = base_vault_balance * quote_vault_balance
    updated_base_vault_balance = constant_product / (quote_vault_balance + effective_sol_used)
    tokens_received = base_vault_balance - updated_base_vault_balance
    return round(tokens_received, 9)


def tokens_for_sol(token_amount: float, base_vault_balance: float, quote_vault_balance: float,
                   swap_fee: float = 0.25) -> float:
    effective_tokens_sold = token_amount * (1 - (swap_fee / 100))
    constant_product = base_vault_balance * quote_vault_balance
    updated_quote_vault_balance = constant_product / (base_vault_balance + effective_tokens_sold)
    sol_received = quote_vault_balance - updated_quote_vault_balance
    return round(sol_received, 9)


def fetch_amm_v4_pool_keys(pair_address: str) -> Optional[AmmV4PoolKeys]:
    def bytes_of(value):
        if not (0 <= value < 2 ** 64):
            raise ValueError("Value must be in the range of a u64 (0 to 2^64 - 1).")
        return struct.pack('<Q', value)

    try:
        amm_id = Pubkey.from_string(pair_address)

        # 修改这里：使用 get_account_info 而不是 get_account_info_json_parsed
        amm_response = client.get_account_info(amm_id, commitment=Processed)
        if not amm_response.value:
            print("Account not found")
            return None

        # 获取原始数据
        amm_data_decoded = LIQUIDITY_STATE_LAYOUT_V4.parse(amm_response.value.data)

        # 同样修改市场数据的获取方式
        marketId = Pubkey.from_bytes(amm_data_decoded.serumMarket)
        market_response = client.get_account_info(marketId, commitment=Processed)
        if not market_response.value:
            print("Market account not found")
            return None

        market_decoded = MARKET_STATE_LAYOUT_V3.parse(market_response.value.data)

        vault_signer_nonce = market_decoded.vault_signer_nonce

        ray_authority_v4 = Pubkey.from_string("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1")
        open_book_program = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")

        # 其余代码保持不变
        pool_keys = AmmV4PoolKeys(
            amm_id=amm_id,
            base_mint=Pubkey.from_bytes(market_decoded.base_mint),
            quote_mint=Pubkey.from_bytes(market_decoded.quote_mint),
            base_decimals=amm_data_decoded.coinDecimals,
            quote_decimals=amm_data_decoded.pcDecimals,
            open_orders=Pubkey.from_bytes(amm_data_decoded.ammOpenOrders),
            target_orders=Pubkey.from_bytes(amm_data_decoded.ammTargetOrders),
            base_vault=Pubkey.from_bytes(amm_data_decoded.poolCoinTokenAccount),
            quote_vault=Pubkey.from_bytes(amm_data_decoded.poolPcTokenAccount),
            market_id=marketId,
            market_authority=Pubkey.create_program_address(
                seeds=[bytes(marketId), bytes_of(vault_signer_nonce)],
                program_id=open_book_program
            ),
            market_base_vault=Pubkey.from_bytes(market_decoded.base_vault),
            market_quote_vault=Pubkey.from_bytes(market_decoded.quote_vault),
            bids=Pubkey.from_bytes(market_decoded.bids),
            asks=Pubkey.from_bytes(market_decoded.asks),
            event_queue=Pubkey.from_bytes(market_decoded.event_queue),
            ray_authority_v4=ray_authority_v4,
            open_book_program=open_book_program,
            token_program_id=TOKEN_PROGRAM_ID
        )
        return pool_keys

    except Exception as e:
        print(f"Error fetching pool keys: {e}")
        return None


def get_pool_reserves(pool_keys: AmmV4PoolKeys) -> tuple:
    try:
        quote_vault = pool_keys.quote_vault
        quote_decimal = pool_keys.quote_decimals
        quote_mint = pool_keys.quote_mint

        base_vault = pool_keys.base_vault
        base_decimal = pool_keys.base_decimals
        base_mint = pool_keys.base_mint

        balances = client.get_multiple_accounts_json_parsed(
            [quote_vault, base_vault],
            Processed
        ).value

        quote_account = balances[0]
        base_account = balances[1]

        quote_balance = quote_account.data.parsed['info']['tokenAmount']['uiAmount']
        base_balance = base_account.data.parsed['info']['tokenAmount']['uiAmount']

        if base_mint == WSOL:
            base_reserve = quote_balance
            quote_reserve = base_balance
            token_decimal = quote_decimal
        else:
            base_reserve = base_balance
            quote_reserve = quote_balance
            token_decimal = base_decimal

        print(f"Base Reserve: {base_reserve} | Quote Reserve: {quote_reserve}")
        return base_reserve, quote_reserve, token_decimal

    except Exception as e:
        print(f"Error getting pool reserves: {e}")
        return None, None, None


def make_swap_instruction(
        amount_in: int,
        minimum_amount_out: int,
        token_account_in: Pubkey,
        token_account_out: Pubkey,
        accounts: AmmV4PoolKeys,
        owner: Pubkey
) -> Instruction:
    try:
        keys = [
            AccountMeta(pubkey=accounts.token_program_id, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.amm_id, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.ray_authority_v4, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.open_orders, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.target_orders, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.base_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.quote_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.open_book_program, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.market_id, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.bids, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.asks, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.event_queue, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.market_base_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.market_quote_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.market_authority, is_signer=False, is_writable=False),
            AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
            AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=True, is_writable=False)
        ]

        data = bytearray()
        discriminator = 9
        data.extend(struct.pack('<B', discriminator))
        data.extend(struct.pack('<Q', amount_in))
        data.extend(struct.pack('<Q', minimum_amount_out))

        return Instruction(RAYDIUM_AMM_V4, bytes(data), keys)

    except Exception as e:
        print(f"Error creating swap instruction: {e}")
        return None

def buy_instructions(client, mint_str: str, sol_in: float, slippage: int) -> list:
    pair_address = get_liquidity_pool(client, mint_str)
    print(f"Starting buy transaction for pair: {pair_address}")

    pool_keys = fetch_amm_v4_pool_keys(pair_address)
    if pool_keys is None:
        print("Failed to fetch pool keys")
        return False

    mint = pool_keys.base_mint if pool_keys.base_mint != WSOL else pool_keys.quote_mint

    # Check and create token account if needed
    token_account_check = client.get_token_accounts_by_owner(
        payer_keypair.pubkey(),
        TokenAccountOpts(mint),
        Processed
    )
    if token_account_check.value:
        token_account = token_account_check.value[0].pubkey
        token_account_instruction = None
        print("Token account exists")
    else:
        token_account = get_associated_token_address(payer_keypair.pubkey(), mint)
        token_account_instruction = create_associated_token_account(
            payer_keypair.pubkey(),
            payer_keypair.pubkey(),
            mint
        )
        print("Creating new token account")

    # Calculate amounts
    amount_in = int(sol_in * SOL_DECIMAL)
    base_reserve, quote_reserve, token_decimal = get_pool_reserves(pool_keys)
    amount_out = sol_for_tokens(sol_in, base_reserve, quote_reserve)

    slippage_adjustment = 1 - (slippage / 100)
    minimum_amount_out = int(amount_out * slippage_adjustment * (10 ** token_decimal))

    print(f"Amount In: {sol_in} SOL")
    print(f"Expected Out: {amount_out} tokens")
    print(f"Minimum Out: {minimum_amount_out}")

    # Create WSOL account
    seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
    wsol_token_account = Pubkey.create_with_seed(
        payer_keypair.pubkey(),
        seed,
        TOKEN_PROGRAM_ID
    )
    balance_needed = Token.get_min_balance_rent_for_exempt_for_account(client)

    create_wsol_account = create_account_with_seed(
        CreateAccountWithSeedParams(
            from_pubkey=payer_keypair.pubkey(),
            to_pubkey=wsol_token_account,
            base=payer_keypair.pubkey(),
            seed=seed,
            lamports=int(balance_needed + amount_in),
            space=ACCOUNT_LAYOUT_LEN,
            owner=TOKEN_PROGRAM_ID,
        )
    )

    init_wsol_account = initialize_account(
        InitializeAccountParams(
            program_id=TOKEN_PROGRAM_ID,
            account=wsol_token_account,
            mint=WSOL,
            owner=payer_keypair.pubkey(),
        )
    )

    # Create swap instruction
    swap_instruction = make_swap_instruction(
        amount_in=amount_in,
        minimum_amount_out=minimum_amount_out,
        token_account_in=wsol_token_account,
        token_account_out=token_account,
        accounts=pool_keys,
        owner=payer_keypair.pubkey(),
    )

    close_wsol_account = close_account(
        CloseAccountParams(
            program_id=TOKEN_PROGRAM_ID,
            account=wsol_token_account,
            dest=payer_keypair.pubkey(),
            owner=payer_keypair.pubkey(),
        )
    )

    # Compile all instructions
    instructions = [
        set_compute_unit_limit(UNIT_BUDGET),
        set_compute_unit_price(UNIT_PRICE),
        create_wsol_account,
        init_wsol_account,
    ]

    if token_account_instruction:
        instructions.append(token_account_instruction)

    instructions.append(swap_instruction)
    instructions.append(close_wsol_account)
    return instructions

def buy(client, mint_str: str, sol_in: float = 0.1, slippage: int = 1) -> list:

    try:
        instructions = buy_instructions(mint_str, sol_in, slippage)

        # Create and send transaction
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )

        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True),
        ).value

        print(f"Transaction sent: https://solscan.io/tx/{txn_sig}")

        # Wait for confirmation
        if confirm_txn(txn_sig):
            print("Buy transaction successful")
            return txn_sig
        else:
            print("Buy transaction failed")
            return False

    except Exception as e:
        print(f"Error executing buy: {e}")
        return False


def sell_instructions(client, mint_str: str, amount: int, slippage: int):
    pair_address = get_liquidity_pool(client, mint_str)
    print(f"Starting sell transaction for pair: {pair_address}")
    # if not (1 <= percentage <= 100):
    #     print("Percentage must be between 1 and 100")
    #     return False

    pool_keys = fetch_amm_v4_pool_keys(pair_address)
    if pool_keys is None:
        print("Failed to fetch pool keys")
        return False

    mint = pool_keys.base_mint if pool_keys.base_mint != WSOL else pool_keys.quote_mint
    token_balance = get_token_balance(str(mint))

    if token_balance == 0 or token_balance is None:
        print("No tokens to sell")
        return False

    # token_balance = token_balance * (percentage / 100)
    token_account = get_associated_token_address(payer_keypair.pubkey(), mint)

    base_reserve, quote_reserve, token_decimal = get_pool_reserves(pool_keys)
    # amount_in = int(token_balance * (10 ** token_decimal))
    amount_in = int(amount * 1_000_000)
    sol_out = tokens_for_sol(token_balance, base_reserve, quote_reserve)

    slippage_adjustment = 1 - (slippage / 100)
    minimum_amount_out = int(sol_out * slippage_adjustment * SOL_DECIMAL)

    # print(f"Selling {percentage}% of tokens")
    print(f"Amount In: {token_balance} tokens")
    print(f"Expected Out: {sol_out} SOL")
    print(f"Minimum Out: {minimum_amount_out}")

    # Create WSOL account
    seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
    wsol_token_account = Pubkey.create_with_seed(
        payer_keypair.pubkey(),
        seed,
        TOKEN_PROGRAM_ID
    )
    balance_needed = Token.get_min_balance_rent_for_exempt_for_account(client)

    create_wsol_account = create_account_with_seed(
        CreateAccountWithSeedParams(
            from_pubkey=payer_keypair.pubkey(),
            to_pubkey=wsol_token_account,
            base=payer_keypair.pubkey(),
            seed=seed,
            lamports=int(balance_needed),
            space=ACCOUNT_LAYOUT_LEN,
            owner=TOKEN_PROGRAM_ID,
        )
    )

    init_wsol_account = initialize_account(
        InitializeAccountParams(
            program_id=TOKEN_PROGRAM_ID,
            account=wsol_token_account,
            mint=WSOL,
            owner=payer_keypair.pubkey(),
        )
    )

    swap_instruction = make_swap_instruction(
        amount_in=amount_in,
        minimum_amount_out=minimum_amount_out,
        token_account_in=token_account,
        token_account_out=wsol_token_account,
        accounts=pool_keys,
        owner=payer_keypair.pubkey(),
    )

    close_wsol_account = close_account(
        CloseAccountParams(
            program_id=TOKEN_PROGRAM_ID,
            account=wsol_token_account,
            dest=payer_keypair.pubkey(),
            owner=payer_keypair.pubkey(),
        )
    )

    instructions = [
        set_compute_unit_limit(UNIT_BUDGET),
        set_compute_unit_price(UNIT_PRICE),
        create_wsol_account,
        init_wsol_account,
        swap_instruction,
        close_wsol_account,
    ]

    # if percentage == 100:
    #     close_token_account = close_account(
    #         CloseAccountParams(
    #             program_id=TOKEN_PROGRAM_ID,
    #             account=token_account,
    #             dest=payer_keypair.pubkey(),
    #             owner=payer_keypair.pubkey(),
    #         )
    #     )
    #     instructions.append(close_token_account)
    return instructions


def sell(client, mint_str: str, percentage: int = 100, slippage: int = 1):

    try:
        instructions = sell_instructions(mint_str, percentage, slippage)

        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )

        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True),
        ).value

        print(f"Transaction sent: https://solscan.io/tx/{txn_sig}")

        if confirm_txn(txn_sig):
            print("Sell transaction successful")
            return txn_sig
        else:
            print("Sell transaction failed")
            return False

    except Exception as e:
        print(f"Error executing sell: {e}")
        return False


if __name__ == "__main__":
    # Example usage:
    mint_str = "2sRQ1DQL6tdQN1LJHaVGSC7sbcZ6NdkzmHdWubtEpump"  # AMM v4 pool address

    # Buy example
    print("\nExecuting buy:")
    buy(client, mint_str, 0.1, 1)  # Buy 0.1 SOL worth with 1% slippage

    # Sell example
    print("\nExecuting sell:")
    sell(client, mint_str, 100, 1)  # Sell 100% with 1% slippage
