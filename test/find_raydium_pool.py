from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.rpc.types import MemcmpOpts
from construct import Bytes, Int64ul, Padding
from construct import Struct as cStruct

RAYDIUM_LIQUIDITY_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

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
    "lpMint" / Bytes(32),
)


def get_liquidity_pool(mint_str: str) -> dict:
    client = Client("https://mainnet.helius-rpc.com/?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd")

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

    for pool in pools:
        pool_data = LIQUIDITY_STATE_LAYOUT_V4.parse(pool.account.data)
        base_vault = Pubkey(pool_data.baseVault)
        quote_vault = Pubkey(pool_data.quoteVault)

        return {
            "pool_address": str(pool.pubkey),
            "sol_pool": str(base_vault),
            "token_pool": str(quote_vault)
        }

    return None


if __name__ == "__main__":
    mint_str = "7w3v2MBZGHRiAPMprhvm5UQFStyKGvVUKwDM9B7Apump"
    pool = get_liquidity_pool(mint_str)
    if pool:
        print(f"Pool Address: {pool['pool_address']}")
        print(f"SOL Pool: {pool['sol_pool']}")
        print(f"Token Pool: {pool['token_pool']}")
    else:
        print("No liquidity pool found for the given token mint")