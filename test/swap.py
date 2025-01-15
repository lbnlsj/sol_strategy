import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to Python path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from utilities.storage import StorageManager
from utilities.settings import SettingsManager
from utilities.price_swap import PriceSwapManager


async def test_price_queries(swap_manager, test_token, sol_mint):
    """Test price query functionality"""
    print("\n=== 测试价格查询 ===")
    amounts = [100_000_000]  # 0.1 SOL
    prices = {}

    for amount in amounts:
        result = await swap_manager.get_current_price(
            input_mint=sol_mint,
            output_mint=test_token,
            amount=amount,
            slippage_bps=1
        )
        sol_amount = amount / 1_000_000_000
        prices[sol_amount] = result
        print(f"\n查询 {sol_amount} SOL 的价格信息:")
        print(f"价格: {result['price']}")
        print(f"输出代币数量: {int(result['outAmount']) / 1e5}")
        print(f"价格影响: {result['priceImpactPct']}%")

    # Test reverse query
    token_amount = 1_000_000
    result = await swap_manager.get_current_price(
        input_mint=test_token,
        output_mint=sol_mint,
        amount=token_amount
    )
    print(f"\n反向查询 {token_amount} tokens:")
    print(f"可得SOL: {int(result['outAmount']) / 1_000_000_000:.6f}")

    return prices


async def test_swaps(swap_manager, test_token, wallet_key, price_data):
    """Test swap execution functionality"""
    print("\n=== 测试交易功能 ===")

    # Get buy price info from the 0.1 SOL test
    buy_price_info = price_data[0.1]
    buy_price = buy_price_info['price']

    print(f"\n使用当前价格 {buy_price} 测试买入:")

    # Test standard buy
    # buy_result = await swap_manager.execute_swap(
    #     direction="buy",
    #     token_address=test_token,
    #     amount=Decimal("0.01"),  # 0.01 SOL
    #     wallet_key=wallet_key,
    #     use_jito=False,
    #     priority_fee=0.000001,
    #     price_limit=buy_price,
    #     slippage_bps=100  # 1% slippage
    # )
    # print("普通买入结果:", buy_result)
    #
    # # Test Jito buy
    # buy_result_jito = await swap_manager.execute_swap(
    #     direction="buy",
    #     token_address=test_token,
    #     amount=0.01,
    #     wallet_key=wallet_key,
    #     use_jito=True,
    #     priority_fee=0.01,
    #     tip_amount=0.0003,
    #     price_limit=buy_price,
    #     slippage_bps=100
    # )
    # print("Jito买入结果:", buy_result_jito)
    #
    # # Wait before testing sells
    # await asyncio.sleep(2)
    #
    # Test standard sell
    # sell_result = await swap_manager.execute_swap(
    #     direction="sell",
    #     token_address=test_token,
    #     amount=180283.3565643,
    #     wallet_key=wallet_key,
    #     use_jito=False,
    #     priority_fee=0.01,
    #     tip_amount=0.0003,
    #     price_limit=buy_price,
    #     slippage_bps=100
    # )
    # print("普通卖出结果:", sell_result)
    #
    # Test Jito sell
    sell_result_jito = await swap_manager.execute_swap(
        direction="sell",
        token_address=test_token,
        amount=100,
        wallet_key=wallet_key,
        use_jito=True,
        priority_fee=0.01,
        tip_amount=0.0003,
        price_limit=buy_price,
        slippage_bps=100
    )
    print("Jito卖出结果:", sell_result_jito)


async def main():
    storage = StorageManager(data_dir=str(project_root / "data"))
    settings = SettingsManager(storage)
    swap_manager = PriceSwapManager()

    # Test configuration  C65GE6jm7SMXVsxVPdH36CHSWoy37iCDnHYpwA8apump
    test_token = "9itDjTjWbfSRHeXzcHsUMHUTkfrSVfinWQvy6MVHpump"  # Bonk   DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
    sol_mint = "So11111111111111111111111111111111111111112"  # SOL
    # wallet_key = '[79,151,59,128,131,250,69,70,57,92,238,170,76,87,94,202,71,142,40,168,154,6,91,178,113,94,115,81,139,138,15,247,230,153,6,254,174,73,54,217,191,43,208,136,73,7,67,87,184,250,182,94,152,118,15,15,237,205,206,184,168,165,66,131]'
    wallet_key = 'ABHE6sNR19FyK8cSw3FJqjgTgy7LEvvx7YRBnTWmdX9omGD25RMiRH8hvrFzPzNRrdwBsdTsTPmXFLS5BDbLoXG'
    result = await swap_manager.get_token_balance(test_token, wallet_key)

    try:
        # First query prices
        price_data = await test_price_queries(swap_manager, test_token, sol_mint)

        # Then execute swap tests
        await test_swaps(swap_manager, test_token, wallet_key, price_data)

    except Exception as e:
        print(f"测试错误: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())