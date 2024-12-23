from threading import Thread, Lock
import json
from pathlib import Path
from solders.keypair import Keypair
from .pump_demo import buy_token, sell_token, get_coin_data
import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TradeTask:
    def __init__(self, task_id: str, ca_address: str, strategy: dict):
        self.task_id = task_id
        self.ca_address = ca_address
        self.strategy = strategy
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.logs: List[dict] = []
        self.thread: Optional[Thread] = None
        self.error = None

    def add_log(self, message: str, level: str = "info"):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        self.logs.append(log_entry)

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "ca_address": self.ca_address,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "logs": self.logs[-10:],  # Only return the last 10 logs
            "error": str(self.error) if self.error else None
        }


class WebhookExecutor:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.tasks: Dict[str, TradeTask] = {}
        self.tasks_lock = Lock()
        self.logs_dir = data_dir / "task_logs"
        self.logs_dir.mkdir(exist_ok=True)

    def load_strategy(self):
        """加载当前激活的策略"""
        active_strategy_file = self.data_dir / "active_strategy.json"
        strategies_file = self.data_dir / "strategies.json"
        wallets_file = self.data_dir / "wallets.json"

        if not active_strategy_file.exists():
            return None

        with open(active_strategy_file, 'r') as f:
            active_data = json.load(f)
            active_name = active_data.get('activeStrategy')

        if not active_name:
            return None

        with open(strategies_file, 'r') as f:
            strategies = json.load(f)

        strategy = next((s for s in strategies if s['name'] == active_name), None)

        if not strategy:
            return None

        with open(wallets_file, 'r') as f:
            wallets = json.load(f)

        strategy['wallets'] = [w for w in wallets if w['address'] in strategy['selectedWallets']]
        return strategy

    def _save_task_logs(self, task: TradeTask):
        """保存任务日志到文件"""
        log_file = self.logs_dir / f"{task.task_id}.json"
        with open(log_file, 'w') as f:
            json.dump(task.to_dict(), f, indent=2)

    def execute_trade(self, ca_address: str) -> tuple:
        """执行交易策略并返回任务ID"""
        strategy = self.load_strategy()
        if not strategy:
            return {"error": "No active strategy found"}, 400

        # 创建新的任务
        task_id = str(uuid.uuid4())
        task = TradeTask(task_id, ca_address, strategy)

        def trade_worker(task: TradeTask):
            try:
                task.status = TaskStatus.RUNNING
                task.start_time = datetime.now()
                task.add_log(f"Starting trade for {ca_address}")

                # 获取代币数据
                coin_data = get_coin_data(ca_address)
                if not coin_data:
                    raise Exception("Failed to get coin data")

                task.add_log("Successfully retrieved coin data")

                # 为每个选中的钱包执行交易
                for wallet in task.strategy['wallets']:
                    try:
                        # 创建Keypair对象
                        if isinstance(wallet['privateKey'], list):
                            keypair = Keypair.from_bytes(bytes(wallet['privateKey']))
                        else:
                            keypair = Keypair.from_base58_string(wallet['privateKey'])

                        task.add_log(f"Processing wallet: {wallet['name']}")

                        # 执行买入
                        amount = (task.strategy['minBuyAmount'] + task.strategy['maxBuyAmount']) / 2
                        success = buy_token(ca_address, amount, task.strategy['slippage'])

                        if success:
                            task.add_log(f"Successfully bought tokens with wallet {wallet['name']}")
                            # 设置跟踪止损
                            self.monitor_position(ca_address, keypair, task.strategy, task)
                        else:
                            task.add_log(f"Failed to buy tokens with wallet {wallet['name']}", "error")

                    except Exception as e:
                        task.add_log(f"Error trading with wallet {wallet['name']}: {str(e)}", "error")

                task.status = TaskStatus.COMPLETED

            except Exception as e:
                task.error = e
                task.status = TaskStatus.FAILED
                task.add_log(f"Task failed: {str(e)}", "error")

            finally:
                task.end_time = datetime.now()
                self._save_task_logs(task)

        # 启动交易线程
        task.thread = Thread(target=trade_worker, args=(task,))
        task.thread.start()

        # 保存任务信息
        with self.tasks_lock:
            self.tasks[task_id] = task

        return {
            "status": "success",
            "message": "Trade started",
            "task_id": task_id
        }, 200

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if task:
                return task.to_dict()

            # 如果内存中没有，尝试从日志文件加载
            log_file = self.logs_dir / f"{task_id}.json"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    return json.load(f)

            return None

    def monitor_position(self, ca: str, keypair: Keypair, strategy: dict, task: TradeTask):
        """监控持仓并执行止盈止损"""

        async def monitor_worker():
            try:
                initial_data = get_coin_data(ca)
                if not initial_data:
                    task.add_log("Failed to get initial coin data for monitoring", "error")
                    return

                highest_price = initial_data.virtual_sol_reserves / initial_data.virtual_token_reserves
                current_price = highest_price

                task.add_log(f"Started position monitoring at price {highest_price}")

                while task.status == TaskStatus.RUNNING:
                    await asyncio.sleep(1)

                    coin_data = get_coin_data(ca)
                    if not coin_data:
                        continue

                    new_price = coin_data.virtual_sol_reserves / coin_data.virtual_token_reserves

                    # 更新最高价
                    if new_price > highest_price:
                        highest_price = new_price
                        task.add_log(f"New highest price: {highest_price}")

                    # 计算跌幅
                    price_drop = (highest_price - new_price) / highest_price * 100

                    # 检查是否触发移动止损
                    if price_drop >= strategy['trailingStop']:
                        task.add_log(f"Trailing stop triggered at {price_drop}% drop")
                        sell_token(ca, strategy['sellPercent'], strategy['slippage'])
                        break

                    # 检查止盈止损点位
                    price_change = (new_price - current_price) / current_price * 100
                    for level in strategy.get('stopLevels', []):
                        if price_change >= level['increase']:
                            sell_amount = level['sell']
                            if sell_amount > 0:
                                task.add_log(f"Stop level triggered at {price_change}% increase")
                                sell_token(ca, sell_amount, strategy['slippage'])

            except Exception as e:
                task.add_log(f"Error in monitor_position: {str(e)}", "error")

        # 启动异步监控
        asyncio.run(monitor_worker())