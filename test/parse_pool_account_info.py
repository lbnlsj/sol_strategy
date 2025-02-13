import base64
import struct
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from construct import Bytes, Int64ul, Padding
from construct import Struct as cStruct

client = Client("https://api.mainnet-beta.solana.com")

LIQUIDITY_STATE_LAYOUT_V4 = cStruct(
    "status" / Int64ul,
    "nonce" / Int64ul,
    "maxOrder" / Int64ul,
    "depth" / Int64ul,
    "baseDecimal" / Int64ul,
    "quoteDecimal" / Int64ul,
    "state" / Int64ul,
    "resetFlag" / Int64ul,
    "minSize" / Int64ul,
    "volMaxCutRatio" / Int64ul,
    "amountWaveRatio" / Int64ul,
    "baseLotSize" / Int64ul,
    "quoteLotSize" / Int64ul,
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
    "baseNeedTakePnl" / Int64ul,
    "quoteNeedTakePnl" / Int64ul,
    "quoteTotalPnl" / Int64ul,
    "baseTotalPnl" / Int64ul,
    "baseTarget" / Int64ul,
    "quoteTarget" / Int64ul,
    "startTime" / Int64ul,
    "baseVirtual" / Int64ul,
    "quoteVirtual" / Int64ul,
    "confidenceInterval" / Int64ul,
    Padding(32),
    "baseVault" / Bytes(32),
    "quoteVault" / Bytes(32),
    "baseMint" / Bytes(32),
    "quoteMint" / Bytes(32),
    "baseMint" / Bytes(32),
    "openOrders" / Bytes(32),
    "marketId" / Bytes(32),
    "marketProgramId" / Bytes(32),
    "targetOrders" / Bytes(32),
    "withdrawQueue" / Bytes(32),
    "lpVault" / Bytes(32),
    "owner" / Bytes(32)
)


def get_pool_info(pool_address):
    pool_pubkey = Pubkey.from_string(pool_address)
    pool_info = client.get_account_info(pool_pubkey)
    # pool_data = base64.b64decode(pool_info.value.data)
    parsed_data = LIQUIDITY_STATE_LAYOUT_V4.parse(pool_info.value.data)

    base_mint = Pubkey(parsed_data.baseMint)
    quote_mint = Pubkey(parsed_data.quoteMint)
    lp_mint = Pubkey(parsed_data.lpMint)
    owner = Pubkey(parsed_data.owner)

    print(f"Pool Address: {pool_pubkey}")
    print(f"Trading Pair: {base_mint} / {quote_mint}")
    print(f"LP Token Mint: {lp_mint}")
    print(f"Owner: {owner}")


# 示例用法
pool_address = "E8N4Ng5nG2y3wUYckjFHdeM4h454CHUtAz7f45EAS2B3"
get_pool_info(pool_address)
