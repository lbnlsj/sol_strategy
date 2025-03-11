# task_executor.py
import traceback
from threading import Thread, Event
import time
from typing import Dict, List, Optional
from datetime import datetime
import base58
import random
import os
import json
from decimal import Decimal
from .price_swap import PriceSwapManager


class TaskExecutor:
    def __init__(self, storage_manager, log_manager=None):
        self.storage_manager = storage_manager
        self.log_manager = log_manager
        debug = os.getenv("DEBUG")
        trade = os.getenv("trade")
        self.debug = True if debug == "True" or debug == "true" else False
        self.trade = True if trade == "True" or trade == "true" else False
        self.active_tasks = {}  # task_id -> Thread
        self.stop_events = {}  # task_id -> Event
        self.max_retry = int(os.getenv('MAX_RETRY'))
        extra_info = os.getenv("EXTRA_INFO")
        self.extra_info = True if extra_info == "True" or extra_info == "true" else False
        if not self.debug:
            self.price_swap = PriceSwapManager()

    def check_token_balance(self, token_address: str, wallet_address: str):
        """检查钱包中的代币余额"""
        try:
            if self.debug:
                # 测试模式下直接返回记录的余额
                return None  # 让系统使用记录的余额
            else:
                balance = self.price_swap.get_token_balance_sync(token_address, wallet_address)
                return float(balance) if balance is not None else None
        except Exception as e:
            self.log("ERROR", f"查询代币余额失败: {str(e)}")
            return None

    def wait_for_transaction(self, tx_id: str, max_attempts: int = 60) -> bool:
        """等待交易确认"""
        if self.debug:
            # 测试模式下直接返回成功
            time.sleep(0.5)  # 模拟网络延迟
            self.log("DEBUG", f"测试模式交易确认: {tx_id}")
            return True

        attempt = 0
        while attempt < max_attempts:
            try:
                result = self.price_swap.check_transaction_status_sync(tx_id)
                if result.get('confirmed'):
                    return True
                elif result.get('error'):
                    return False
            except Exception as e:
                self.log("WARNING", f"检查交易状态失败: {str(e)}")

            time.sleep(1)
            attempt += 1

        return False

    def execute_sell_with_retry(self,
                               token_address: str,
                               amount: float,
                               wallet_key: str,
                               strategy: Dict,
                               current_price: float,
                               max_retries: int = 5,
                               wallet_state: Dict = {}, quota_data: Dict = {}) -> bool:
        """执行卖出操作，失败时重试"""
        if self.debug:
            wallet_state['token_balance'] -= amount
            time.sleep(self.get_debug_trade_time())
            self.log('INFO', f"当前余额：{wallet_state['token_balance']}")
            if wallet_state['token_balance'] < 0:
                self.log("ERROR", "余额错误")
            return False
        else:
            wallet_pubkey = str(self.price_swap.get_wallet_from_string(wallet_key).pubkey())
            # print(wallet_key)
            for attempt in range(max_retries):
                try:
                    exit_price, amount = self._execute_trade_real(
                        "SELL",
                        amount,
                        current_price,
                        token_address,
                        wallet_key,
                        strategy,
                        quota_data
                    )

                    if exit_price:
                        return True

                    self.log("WARNING", f"钱包 {wallet_pubkey} 卖出尝试 {attempt + 1} 失败，准备重试")
                    time.sleep(1)
                except Exception as e:
                    self.log("ERROR", f"钱包 {wallet_pubkey} 卖出操作失败: {str(e)}")
                    time.sleep(1)

            return False

    def _execute_wallet_trades(self,
                              wallet_key: str,
                              current_price: float,
                              task: Dict,
                              strategy: Dict,
                              wallet_state: Dict, quota_data: Dict):
        """执行单个钱包的交易操作"""
        wallet_pubkey = str(self.price_swap.get_wallet_from_string(wallet_key).pubkey())
        try:
            # 检查止盈止损条件
            for level in strategy.get('stopLevels', []):
                if level['increase'] in wallet_state['triggered_levels']:
                    continue

                price_target = wallet_state['entry_price'] * (1 + float(level['increase']) / 100)
                is_stop_loss = float(level['increase']) < 0
                condition_met = (current_price <= price_target) if is_stop_loss else (current_price >= price_target)

                if condition_met:
                    sell_amount = wallet_state['token_balance'] * float(level['sell']) / 100

                    loss_rate = (current_price - wallet_state['entry_price']) / wallet_state[
                        'entry_price'] * 100
                    self.log("INFO",
                             f"钱包(余额{wallet_state['token_balance']}，原始价格{wallet_state['entry_price']}) {wallet_pubkey} 触发固定止盈止损, 当前价格: {current_price} 将要卖出：{sell_amount} 盈亏率：{loss_rate}%\n档次：{level}")

                    if self.execute_sell_with_retry(
                            task['contractAddress'],
                            sell_amount,
                            wallet_key,
                            strategy,
                            current_price,
                            self.max_retry,
                            wallet_state,
                            quota_data
                    ):
                        wallet_state['token_balance'] -= sell_amount
                        self.log('INFO', f'检查 {wallet_pubkey} 钱包余额：{wallet_state["token_balance"]} token')
                        wallet_state['triggered_levels'].add(level['increase'])
                        return

            # 检查移动止损条件
            if (current_price <= wallet_state['trailing_stop_price'] and
                    not wallet_state['trailing_stop_triggered']):
                loss_rate = (wallet_state['trailing_stop_price'] - wallet_state['entry_price']) / wallet_state[
                    'entry_price'] * 100
                self.log("INFO",
                         f"钱包 {wallet_pubkey}(余额{wallet_state['token_balance']}) 触发移动止损, 当前价格: {current_price}, 目标价格 {wallet_state['trailing_stop_price']}  将要卖出：{wallet_state['token_balance'] * (strategy['sellPercent'] / 100)} 浮亏率：{loss_rate}% ")

                self.execute_sell_with_retry(
                    task['contractAddress'],
                    wallet_state['token_balance'],
                    wallet_key,
                    strategy,
                    current_price,
                    self.max_retry,
                    wallet_state,
                    quota_data
                )

                wallet_state['token_balance'] = 0
                self.log('INFO', f'检查 {wallet_pubkey} 钱包余额：{wallet_state["token_balance"]} token')
                wallet_state['trailing_stop_triggered'] = True
                return

            # 更新移动止损价格
            if current_price > wallet_state['highest_price']:
                wallet_state['highest_price'] = current_price
                trailing_stop_pct = float(strategy['trailingStop'])
                wallet_state['trailing_stop_price'] = current_price * (1 - trailing_stop_pct / 100)
                self.log("INFO",
                         f"钱包 {wallet_pubkey} ca：{task['contractAddress']} 更新移动止损价格（原始价格{wallet_state['entry_price']}，当前价格{current_price}）: {wallet_state['trailing_stop_price']}")

        except Exception as e:
            self.log("ERROR", f"钱包 {wallet_pubkey} 交易操作失败: {str(e)}")

    def get_token_balance(self, ca, wallet_key):
        if self.debug:
            token_amount = self.get_debug_balance()
        else:
            token_amount = self.price_swap.get_token_balance_sync(ca, wallet_key)
        return token_amount

    def _monitor_price_and_execute(self, task: Dict, strategy: Dict, stop_event: Event):
        """共享价格监控并执行多钱包交易"""
        try:
            # 初始化每个钱包的状态
            wallet_states = {}
            entry_price = 0
            ca = task['contractAddress']

            # 初始化钱包
            def initialize_wallet(wallet_key, quota_data):
                wallet_pubkey = str(self.price_swap.get_wallet_from_string(wallet_key).pubkey())
                try:
                    # 获取初始价格
                    nonlocal entry_price

                    # 执行买入
                    buy_amount_sol = round(random.uniform(
                        float(strategy['minBuyAmount']),
                        float(strategy['maxBuyAmount'])
                    ), 4)

                    entry_price, amount = self._execute_trade_real(
                        "BUY",
                        buy_amount_sol,
                        entry_price,
                        ca,
                        wallet_key,
                        strategy,
                        quota_data
                    )

                    token_amount = 0
                    for _ in range(20):
                        time.sleep(1)
                        try:
                            if self.trade:
                                token_amount = self.get_token_balance(task['contractAddress'], wallet_key)
                            else:
                                token_amount = amount * 10
                        except Exception as e:
                            print('查询价格失败：' + str(e))
                            pass
                        if token_amount is None: continue
                        if token_amount > 1: break

                    if token_amount != 0:
                        pass
                    else:
                        self.log('ERROR', f'长时间没有检测到买入的钱包的余额 wallet: {wallet_pubkey} ca:{task["contractAddress"]}')

                    self.log('INFO', f'钱包 {wallet_pubkey} entry_price 为：{entry_price}')
                    return {
                        'wallet_key': wallet_key,
                        'state': {
                            'token_balance': token_amount,
                            'entry_price': entry_price,
                            'highest_price': entry_price,
                            'trailing_stop_price': entry_price * (1 - float(strategy['trailingStop']) / 100),
                            'trailing_stop_triggered': False,
                            'triggered_levels': set(),
                            'levels': strategy['stopLevels'],
                            'amount': token_amount
                        }
                    }
                except Exception as e:
                    self.log("ERROR", f"钱包 {wallet_pubkey} 初始化失败: {str(e)}")
                    return None

            # 获取钱包私钥
            wallet_keys = [base58.b58decode(w['private_key']).decode()
                           for w in self.storage_manager.load_json('wallets.json', default=[])
                           if w['address'] in strategy['selectedWallets']]

            quote_data = {}

            # 使用线程池初始化钱包
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=10) as executor:
                wallet_init_results = list(executor.map(
                    lambda key: initialize_wallet(key, quote_data),
                    wallet_keys
                ))

            # 处理初始化结果
            for result in wallet_init_results:
                if result:
                    wallet_states[result['wallet_key']] = result['state']

            if not wallet_states:
                self.log("ERROR", "所有钱包初始化失败")
                traceback.print_exc()
                return

            entry_prices = [d['entry_price'] for d in wallet_states.values() if 'entry_price' in d]
            amounts = [d['amount'] for d in wallet_states.values() if 'amount' in d]
            if len(entry_prices) == 0:
                self.log('INFO', "没有有效钱包有有效余额")
            entry_price = entry_prices[0]
            if len(amounts) == 0:
                self.log('INFO', "没有有效买入余额")
            amount = amounts[0]
            last_price = 0

            self.log("INFO", f'task id: {task["id"]} 开始持久化监控token：{task["contractAddress"]} entry_price: {entry_price}\tamount:{amount}')

            # 开始价格监控循环
            while (not stop_event.is_set() and any(state['token_balance'] > 1 for state in wallet_states.values()) and
                   any(len(state['triggered_levels']) != len(state['levels']) for state in wallet_states.values())):

                try:
                    current_price, quote_data = self._get_current_price_real(task['contractAddress'], amount)
                except Exception as e:
                    print(e)
                    time.sleep(0.5)
                    continue

                if current_price is None:
                    print(f'查询 价格失败 task: {task} ')
                    continue

                # 使用线程池执行钱包交易
                active_wallets = [(wallet_key, state) for wallet_key, state in wallet_states.items() 
                                 if state['token_balance'] > 0]
                
                if active_wallets:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        executor.map(
                            lambda wallet_data: self._execute_wallet_trades(
                                wallet_data[0], current_price, task, strategy, wallet_data[1], quote_data
                            ),
                            active_wallets
                        )

                time.sleep(0.5)  # 主循环的延迟

            self.log("INFO", f'task id: {task["id"]} stop_event.is_set: {stop_event.is_set()}\t')
            return True

        except Exception as e:
            traceback.print_exc()
            self.log("ERROR", f"价格监控任务执行错误: {str(e)}")

    def _run_task(self, task: Dict, strategy: Dict, stop_event: Event):
        """执行任务主循环"""
        try:
            # 直接执行价格监控任务
            self._monitor_price_and_execute(task, strategy, stop_event)

        except Exception as e:
            traceback.print_stack()
            self.log("ERROR", f"任务执行错误: {str(e)}")
        finally:
            self.log('INFO', f"任务：{task['id']}执行完成")
            if task['id'] in self.stop_events:
                self.stop_events[task['id']].set()
            if task['id'] in self.active_tasks:
                del self.active_tasks[task['id']]
                del self.stop_events[task['id']]

        data = json.loads(open('data/tasks.json', 'r', encoding='utf-8').read())
        for key in data.keys():
            if data[key]['id'] == str(task['id']):
                data[key]['status'] = 'stopped'
                break
        open('data/tasks.json', 'w', encoding='utf-8').write(json.dumps(data))

    def log(self, level: str, message: str):
        """Helper method to handle logging"""
        if self.log_manager:
            self.log_manager.add_log(level, message)
        print(f"[{level}] {message}")

    def start_task(self, task: Dict, strategy: Dict):
        """启动新的任务线程"""
        if task['id'] in self.active_tasks:
            self.log("WARNING", f"任务 {task['id']} 已在运行中")
            return False

        stop_event = Event()
        self.stop_events[task['id']] = stop_event

        thread = Thread(
            target=self._run_task,
            args=(task, strategy, stop_event),
            daemon=True
        )
        self.active_tasks[task['id']] = thread
        thread.start()

        self.log("INFO", f"已启动任务 {task['id']}, 策略名称: {strategy['name']}")
        return True

    def stop_task(self, task_id: str):
        """停止任务"""
        if task_id not in self.active_tasks:
            self.log("WARNING", f"任务 {task_id} 未在运行")
            return False

        # Set the stop event
        self.stop_events[task_id].set()

        # Clean up regardless of join status
        del self.active_tasks[task_id]
        del self.stop_events[task_id]

        self.log("INFO", f"手动已停止任务 {task_id}")
        return True

    def _get_current_price_debug(self) -> float:
        """模拟获取当前价格"""
        return round(random.uniform(0.0001, 0.05), 6)

    def get_debug_current_price(self):
        """用于测试的价格生成"""
        return round(random.uniform(0.0001, 0.05), 6)

    def get_debug_balance(self):
        """用于测试的价格生成"""
        return random.randint(100, 1000)

    def get_debug_entry_price(self):
        return 0.035

    def get_debug_trade_time(self):
        return random.randint(1, 2)

    def get_debug_query_time(self):
        return random.randint(1, 4)

    def _get_current_price_real(self, token_address: str, amount: int = 10000):
        """获取真实当前价格"""
        if self.debug:
            entry_price = self.get_debug_current_price()
            self.log("DEBUG", f"使用测试价格: {entry_price}")
            time.sleep(self.get_debug_query_time())
            return entry_price, {}
        else:
            try:
                sol_mint = "So11111111111111111111111111111111111111112"
                quote_data = self.price_swap.get_current_price_sync(
                    input_mint=sol_mint,
                    output_mint=token_address,
                    amount=int(amount),
                    slippage_bps=100
                )
                if quote_data:
                    if 'error' in quote_data:
                        print(str(quote_data))
                        return None, quote_data
                    return float(quote_data['price']), quote_data
                self.log("ERROR", str(quote_data))
                return None, quote_data
            except Exception as e:
                print(f"获取价格失败: {str(e)}")
                time.sleep(0.02)
                return self._get_current_price_real(token_address, amount)

    def _execute_trade_debug(self, action: str, amount: float, price: float) -> bool:
        """模拟执行交易"""
        time.sleep(0.5)  # 模拟交易延迟
        return True

    def _execute_trade_real(self, action: str, amount: float, price: float, token_address: str, wallet_key: str,
                           strategy: Dict, quota_data):
        """执行真实交易"""
        self.log("INFO", f"开始交易 {token_address} {amount} 个")
        if self.debug:
            buy_result = {
                'success': True,
                'transaction_id': f"debug_tx_{int(time.time())}"
            }

            time.sleep(self.get_debug_trade_time())
            self.log("DEBUG", f"测试模式买入: {amount} SOL")
            return True, amount
        else:
            for _ in range(self.max_retry):
                try:
                    direction = "buy" if action == "BUY" else "sell"
                    use_jito = True if strategy.get('antiSqueeze') == "on" else False
                    priority_fee = float(strategy.get('buyPriority' if action == "BUY" else 'sellPriority', 0.000001))
                    tip_amount = float(strategy.get('jitoSettings', {}).get('fee', 0.0001)) if strategy.get(
                        'jitoSettings', {}).get('enabled') else random.uniform(0.0001, 0.001)
                    if strategy.get('speedMode') == 'fast':
                        tip_amount = float(strategy.get('antiSandwichSettings', {}).get('fee', 0.01)) if strategy.get(
                            'antiSandwichSettings', {}).get('enabled') else random.uniform(0.001, 0.01)
                    slippage_bps = int(
                        float(strategy.get('slippage', 0.25)) * 100)  # Convert percentage to basis points

                    while 1:
                        try:
                            result = self.price_swap.execute_swap_sync(
                                direction=direction,
                                token_address=token_address,
                                amount=Decimal(str(amount)),
                                wallet_key=wallet_key,
                                use_jito=use_jito,
                                priority_fee=priority_fee,
                                tip_amount=tip_amount,
                                slippage_bps=slippage_bps,
                                quote_response=quota_data
                            )
                            break
                        except Exception as e:
                            traceback.print_stack()
                            self.log('ERROR', '执行交易失败1：' + str(e))

                    if 'success' in result and not result['success']:
                        self.log('ERROR', str(result))
                        return result['entry_price'], amount
                    self.log("INFO", f"交易成功: {result['transaction_id']}")
                    return result['entry_price'], amount
                except Exception as e:
                    traceback.print_stack()
                    self.log("ERROR", f"执行交易失败: {str(e)}")
                    continue
            return 0, 0

    def get_active_task_count(self) -> int:
        """返回当前活动任务数量"""
        return len(self.active_tasks)

    def get_active_task_ids(self) -> List[str]:
        """返回活动任务ID列表"""
        return list(self.active_tasks.keys())

    def _get_current_price(self) -> float:
        """模拟获取当前价格"""
        return round(random.uniform(0.0001, 0.05), 6)

    def _execute_trade(self, action: str, amount: float, price: float) -> bool:
        """模拟执行交易"""
        time.sleep(0.5)  # 模拟交易延迟
        return True  # 模拟交易总是成功