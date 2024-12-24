from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.instruction import Instruction
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solana.rpc.types import TokenAccountOpts, TxOpts
from solana.rpc.commitment import Processed
from spl.token.instructions import get_associated_token_address, create_associated_token_account
from solana.transaction import AccountMeta
import base64
import os
from typing import Optional, List

# Constants
WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
RAY_V4 = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
RAY_AUTHORITY_V4 = Pubkey.from_string("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1")
OPEN_BOOK_PROGRAM = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
RENT = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
SOL_DECIMAL = 1e9

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


def buy_token(mint_str: str, sol_amount: float = 0.01) -> bool:
    try:
        print(f"Starting buy for {mint_str}")
        mint = Pubkey.from_string(mint_str)
        amount_in = int(sol_amount * SOL_DECIMAL)

        # Get token account
        token_account = get_associated_token_address(payer.pubkey(), mint)
        token_account_instr = None

        try:
            client.get_token_accounts_by_owner(payer.pubkey(), TokenAccountOpts(mint))
        except:
            token_account_instr = create_associated_token_account(
                payer.pubkey(),
                payer.pubkey(),
                mint
            )

        # Create WSOL account
        seed = base64.urlsafe_b64encode(os.urandom(24)).decode('utf-8')
        wsol_account = Pubkey.create_with_seed(payer.pubkey(), seed, TOKEN_PROGRAM)

        # Create instructions list
        instructions: List[Instruction] = [
            set_compute_unit_limit(UNIT_BUDGET),
            set_compute_unit_price(UNIT_PRICE)
        ]

        if token_account_instr:
            instructions.append(token_account_instr)

        # Create swap instruction
        swap_keys = [
            AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=RAY_V4, is_signer=False, is_writable=True),
            AccountMeta(pubkey=RAY_AUTHORITY_V4, is_signer=False, is_writable=False),
            AccountMeta(pubkey=wsol_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=token_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False)
        ]

        swap_data = bytearray([9])  # Swap instruction
        swap_data.extend(amount_in.to_bytes(8, 'little'))
        swap_ix = Instruction(RAY_V4, bytes(swap_data), swap_keys)

        instructions.append(swap_ix)

        # Build and send transaction
        message = MessageV0.try_compile(
            payer.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash
        )

        tx = VersionedTransaction(message, [payer])
        sig = client.send_transaction(tx, opts=TxOpts(skip_preflight=True)).value
        print(f"Transaction sent: {sig}")
        return True

    except Exception as e:
        print(f"Error during buy: {e}")
        return False


def sell_token(mint_str: str, percentage: int = 100) -> bool:
    try:
        print(f"Selling {percentage}% of token {mint_str}")
        if not (1 <= percentage <= 100):
            print("Invalid percentage")
            return False

        mint = Pubkey.from_string(mint_str)
        token_account = get_associated_token_address(payer.pubkey(), mint)

        # Get token balance
        try:
            token_data = client.get_token_accounts_by_owner(
                payer.pubkey(),
                TokenAccountOpts(mint)
            ).value[0].account.data

            balance = int.from_bytes(token_data[64:72], 'little')
            amount = int(balance * percentage / 100)

            if amount == 0:
                print("No tokens to sell")
                return False

        except Exception as e:
            print(f"Error getting token balance: {e}")
            return False

        # Create WSOL account
        seed = base64.urlsafe_b64encode(os.urandom(24)).decode('utf-8')
        wsol_account = Pubkey.create_with_seed(payer.pubkey(), seed, TOKEN_PROGRAM)

        # Create swap instruction
        swap_keys = [
            AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=RAY_V4, is_signer=False, is_writable=True),
            AccountMeta(pubkey=RAY_AUTHORITY_V4, is_signer=False, is_writable=False),
            AccountMeta(pubkey=token_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=wsol_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False)
        ]

        swap_data = bytearray([9])  # Swap instruction
        swap_data.extend(amount.to_bytes(8, 'little'))
        swap_ix = Instruction(RAY_V4, bytes(swap_data), swap_keys)

        instructions = [
            set_compute_unit_limit(UNIT_BUDGET),
            set_compute_unit_price(UNIT_PRICE),
            swap_ix
        ]

        # Build and send transaction
        message = MessageV0.try_compile(
            payer.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash
        )

        tx = VersionedTransaction(message, [payer])
        sig = client.send_transaction(tx, opts=TxOpts(skip_preflight=True)).value
        print(f"Transaction sent: {sig}")
        return True

    except Exception as e:
        print(f"Error during sell: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    token_address = "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R"  # Example token

    # Buy example
    buy_token(token_address, 0.01)

    # Sell example
    # sell_token(token_address, 100)