# app.py
from flask import Flask, request, jsonify, render_template
import base58
import base64
import json
from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed
from jupiter_python_sdk.jupiter import Jupiter
import asyncio
from functools import wraps

app = Flask(__name__)


def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()

    return wrapped


def create_jupiter_client(wallet_key=None):
    try:
        async_client = AsyncClient("https://staked.helius-rpc.com?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd")

        if wallet_key:
            if '[' in wallet_key:
                secret_key_bytes = bytes(eval(wallet_key))
                payer = Keypair.from_bytes(secret_key_bytes)
            else:
                payer = Keypair.from_base58_string(wallet_key)
        else:
            # 使用默认密钥用于价格查询
            secret_key_list = [79, 151, 59, 128, 131, 250, 69, 70, 57, 92, 238, 170, 76, 87, 94, 202, 71, 142, 40, 168,
                               154, 6, 91, 178, 113, 94, 115, 81, 139, 138, 15, 247, 230, 153, 6, 254, 174, 73, 54, 217,
                               191, 43, 208, 136, 73, 7, 67, 87, 184, 250, 182, 94, 152, 118, 15, 15, 237, 205, 206,
                               184,
                               168, 165, 66, 131]
            payer = Keypair.from_bytes(bytes(secret_key_list))

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
        return jupiter, async_client, payer
    except Exception as e:
        raise Exception(f"创建Jupiter客户端失败: {str(e)}")


async def get_quote(jupiter, token_address, amount, is_buy):
    try:
        input_mint = "So11111111111111111111111111111111111111112" if is_buy else token_address
        output_mint = token_address if is_buy else "So11111111111111111111111111111111111111112"

        quote_data = await jupiter.quote(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
            slippage_bps=1,
        )
        return quote_data
    except Exception as e:
        raise Exception(f"获取报价失败: {str(e)}")


async def execute_swap(jupiter, async_client, payer, token_address, amount, is_buy):
    try:
        input_mint = "So11111111111111111111111111111111111111112" if is_buy else token_address
        output_mint = token_address if is_buy else "So11111111111111111111111111111111111111112"

        transaction_data = await jupiter.swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
            slippage_bps=1,
        )

        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature = payer.sign_message(message.to_bytes_versioned(raw_transaction.message))
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
        opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
        result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        transaction_id = json.loads(result.to_json())['result']

        return {
            "success": True,
            "transaction_id": transaction_id,
            "explorer_url": f"https://solscan.io/tx/{transaction_id}"
        }
    except Exception as e:
        raise Exception(f"交易失败: {str(e)}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/quote', methods=['POST'])
@async_route
async def get_swap_quote():
    try:
        data = request.json
        token_address = data.get('token_address')
        amount = int(float(data.get('amount')) * 1_000_000)  # 转换为 lamports
        is_buy = data.get('is_buy')

        jupiter, async_client, _ = create_jupiter_client()  # 不需要钱包密钥进行价格查询
        quote_data = await get_quote(jupiter, token_address, amount, is_buy)

        return jsonify({
            "success": True,
            "quote": quote_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route('/api/swap', methods=['POST'])
@async_route
async def execute_swap_route():
    try:
        data = request.json
        wallet_key = data.get('wallet_key')
        if not wallet_key:
            return jsonify({
                "success": False,
                "error": "请提供钱包密钥"
            }), 400

        token_address = data.get('token_address')

        is_buy = data.get('is_buy')
        amount = int(float(data.get('amount')) * 1_000_000)  # 转换为 lamports
        if is_buy: amount *= 1_000  # 如果是sol

        jupiter, async_client, payer = create_jupiter_client(wallet_key)
        result = await execute_swap(
            jupiter, async_client, payer, token_address, amount, is_buy
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=2001)
