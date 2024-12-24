import base58
import base64
import json
import asyncio

from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed

from jupiter_python_sdk.jupiter import Jupiter, Jupiter_DCA

secret_key_list = [79, 151, 59, 128, 131, 250, 69, 70, 57, 92, 238, 170, 76, 87, 94, 202, 71, 142, 40, 168, 154, 6, 91,
                   178, 113, 94, 115, 81, 139, 138, 15, 247, 230, 153, 6, 254, 174, 73, 54, 217, 191, 43, 208, 136, 73,
                   7, 67, 87, 184, 250, 182, 94, 152, 118, 15, 15, 237, 205, 206, 184, 168, 165, 66, 131]
secret_key_bytes = bytes(secret_key_list)

payer = Keypair.from_bytes(secret_key_bytes)

# private_key = Keypair.from_bytes(base58.b58decode(os.getenv("PRIVATE-KEY"))) # Replace PRIVATE-KEY with your private key as string
async_client = AsyncClient(
    "https://staked.helius-rpc.com?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd")  # Replace SOLANA-RPC-ENDPOINT-URL with your Solana RPC Endpoint URL
jupiter = Jupiter(
    async_client=async_client,
    keypair=payer,
    quote_api_url="https://quote-api.jup.ag/v6/quote?",
    swap_api_url="https://quote-api.jup.ag/v6/swap",
    open_order_api_url="https://jup.ag/api/limit/v1/createOrder",
    cancel_orders_api_url="https://jup.ag/api/limit/v1/cancelOrders",
    query_open_orders_api_url="https://jup.ag/api/limit/v1/openOrders?wallet=",
    query_order_history_api_url="https://jup.ag/api/limit/v1/orderHistory",
    query_trade_history_api_url="https://jup.ag/api/limit/v1/tradeHistory"
)


async def get_jup_price():
    """
    EXECUTE A SWAP
    """
    quote_data = await jupiter.quote(
        input_mint="JV6Qzhsq7yRWGzScF2zA4Ltv9mSBjGsvtjWpm9Ppump",  # "JV6Qzhsq7yRWGzScF2zA4Ltv9mSBjGsvtjWpm9Ppump"
        output_mint="So11111111111111111111111111111111111111112",  # "So11111111111111111111111111111111111111112"
        amount=10_000_000,
        slippage_bps=1,
    )
    # example: {'inputMint': 'JV6Qzhsq7yRWGzScF2zA4Ltv9mSBjGsvtjWpm9Ppump', 'inAmount': '10000000', 'outputMint': 'So11111111111111111111111111111111111111112', 'outAmount': '286', 'otherAmountThreshold': '286', 'swapMode': 'ExactIn', 'slippageBps': 1, 'platformFee': None, 'priceImpactPct': '0.0219983962480627979400916166', 'routePlan': [{'swapInfo': {'ammKey': '9VQame1cc6zkWEKEQMstvuTc66Qs22nWeLPP7HTcPavz', 'label': 'Pump.fun', 'inputMint': 'JV6Qzhsq7yRWGzScF2zA4Ltv9mSBjGsvtjWpm9Ppump', 'outputMint': 'So11111111111111111111111111111111111111112', 'inAmount': '10000000', 'outAmount': '286', 'feeAmount': '100000', 'feeMint': 'JV6Qzhsq7yRWGzScF2zA4Ltv9mSBjGsvtjWpm9Ppump'}, 'percent': 100}], 'scoreReport': None, 'contextSlot': 309452136, 'timeTaken': 0.055498503}
    print(quote_data)

    transaction_data = await jupiter.swap(
        input_mint="JV6Qzhsq7yRWGzScF2zA4Ltv9mSBjGsvtjWpm9Ppump",  # "JV6Qzhsq7yRWGzScF2zA4Ltv9mSBjGsvtjWpm9Ppump"
        output_mint="So11111111111111111111111111111111111111112",  # "So11111111111111111111111111111111111111112"
        amount=10_000_000,
        slippage_bps=1,
    )

    raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
    signature = payer.sign_message(message.to_bytes_versioned(raw_transaction.message))
    signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
    opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
    result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
    transaction_id = json.loads(result.to_json())['result']
    print(f"Transaction sent: https://solscan.io/tx/{transaction_id}")
    return


# Run the async function
if __name__ == "__main__":
    asyncio.run(get_jup_price())
