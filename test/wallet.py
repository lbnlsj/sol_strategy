from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.hash import Hash
from solana.rpc import types
from solders.message import MessageV0
from spl.token.constants import TOKEN_PROGRAM_ID
from solders.transaction import VersionedTransaction
from spl.token.instructions import (
    get_associated_token_address,
    create_associated_token_account,
    TransferCheckedParams,
    transfer_checked
)
from solders.compute_budget import set_compute_unit_price
from solders.system_program import TransferParams, transfer

# 连接到 Solana Devnet
client = Client("https://staked.helius-rpc.com?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd")

# 从私钥导入密钥对（假设私钥为 base58 编码的字符串）
# private_key = "your_private_key_here"
# sender_keypair = Keypair.from_base58_string(private_key)

secret_key_list = [79, 151, 59, 128, 131, 250, 69, 70, 57, 92, 238, 170, 76, 87, 94, 202, 71, 142, 40, 168, 154, 6, 91,
                   178, 113, 94, 115, 81, 139, 138, 15, 247, 230, 153, 6, 254, 174, 73, 54, 217, 191, 43, 208, 136, 73,
                   7, 67, 87, 184, 250, 182, 94, 152, 118, 15, 15, 237, 205, 206, 184, 168, 165, 66, 131]
secret_key_bytes = bytes(secret_key_list)

sender_keypair = Keypair.from_bytes(secret_key_bytes)

# 接收者的公钥
receiver_pubkey = Pubkey.from_string("C6dFNEq4hffou1NE4HXwDUBiRdpCgYT2C9efKDHRXktG")

# SPL 代币的铸币地址（MINT 地址）
mint_pubkey = Pubkey.from_string("7aJs6HyF4tgsCmMPX2YAh9YhBHzfr8AZSBnePZwbpump")

# 获取发送者的关联代币账户地址
sender_token_account = get_associated_token_address(sender_keypair.pubkey(), mint_pubkey)

# 获取接收者的关联代币账户地址
receiver_token_account = get_associated_token_address(receiver_pubkey, mint_pubkey)

ix = transfer(
    TransferParams(
        from_pubkey=sender_keypair.pubkey(), to_pubkey=receiver_pubkey, lamports=1_000_000
    )
)
blockhash =client.get_latest_blockhash().value.blockhash  # replace with a real blockhash using get_latest_blockhash
msg = MessageV0.try_compile(
    payer=sender_keypair.pubkey(),
    instructions=[ix],
    address_lookup_table_accounts=[],
    recent_blockhash=blockhash,
)
tx = VersionedTransaction(msg, [sender_keypair])

# 完成转账
# response = client.send_transaction(tx)

# 检查接收者的代币账户是否存在
response = client.get_account_info(receiver_token_account)
if response.value is None:
    # 如果不存在，创建接收者的关联代币账户的指令
    create_account_ix = create_associated_token_account(
        payer=sender_keypair.pubkey(),
        owner=receiver_pubkey,
        mint=mint_pubkey
    )

    # 获取最新的区块哈希
    blockhash = client.get_latest_blockhash().value.blockhash

    # 创建消息并编译
    create_account_msg = MessageV0.try_compile(
        payer=sender_keypair.pubkey(),
        instructions=[create_account_ix],
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )

    # 创建并发送创建账户的交易
    create_account_tx = VersionedTransaction(create_account_msg, [sender_keypair])
    client.send_transaction(create_account_tx)

# 转账金额（以代币的最小单位计，例如代币有 9 位小数，转账 1 个代币则为 1 * 10^9）
input_amount = 1  # 1 个代币

# 获取代币的小数位数
mint_info = client.get_token_supply(mint_pubkey)
decimals = mint_info.value.decimals

amount = input_amount * 10 ** decimals


# 创建转账指令
transfer_params = TransferCheckedParams(
    program_id=TOKEN_PROGRAM_ID,
    source=sender_token_account,
    mint=mint_pubkey,
    dest=receiver_token_account,
    owner=sender_keypair.pubkey(),
    amount=amount,
    decimals=decimals
)
transfer_ix = transfer_checked(transfer_params)

# 获取最新的区块哈希
blockhash = client.get_latest_blockhash().value.blockhash

set_compute_price_ix = set_compute_unit_price(333333)

# 创建消息并编译
msg = MessageV0.try_compile(
    payer=sender_keypair.pubkey(),
    instructions=[set_compute_price_ix, transfer_ix],
    address_lookup_table_accounts=[],
    recent_blockhash=blockhash,
)

# 创建并签名交易
tx = VersionedTransaction(msg, [sender_keypair])

opt = types.TxOpts(
    skip_preflight=True,
    skip_confirmation=True
)

# 发送交易
# response = client.send_transaction(tx, opt)
# print(f"Transaction signature: {response.value}")
print('测试完成')