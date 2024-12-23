import json
import time
import uuid
from pathlib import Path
from datetime import datetime
import random


class WebhookExecutor:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.logs_dir = self.data_dir / "task_logs"
        self.logs_dir.mkdir(exist_ok=True)

    def _load_active_strategy(self):
        """加载当前激活的策略配置"""
        active_strategy_file = self.data_dir / "active_strategy.json"
        if not active_strategy_file.exists():
            return None

        with open(active_strategy_file, 'r') as f:
            data = json.load(f)
            strategy_name = data.get('activeStrategy')

        if not strategy_name:
            return None

        strategies_file = self.data_dir / "strategies.json"
        if not strategies_file.exists():
            return None

        with open(strategies_file, 'r') as f:
            strategies = json.load(f)
            for strategy in strategies:
                if strategy['name'] == strategy_name:
                    return strategy

        return None

    def _load_wallets(self, wallet_addresses):
        """加载指定地址的钱包信息"""
        wallets_file = self.data_dir / "wallets.json"
        if not wallets_file.exists():
            return []

        with open(wallets_file, 'r') as f:
            all_wallets = json.load(f)
            return [w for w in all_wallets if w['address'] in wallet_addresses]

    def _generate_mock_transaction(self, wallet_address):
        """生成模拟交易数据"""
        tx_hash = ''.join(random.choices('0123456789abcdef', k=64))
        amount = random.uniform(0.1, 2.0)
        price = random.uniform(0.1, 10.0)

        return {
            "tx_hash": tx_hash,
            "wallet": wallet_address,
            "amount": round(amount, 4),
            "price": round(price, 4),
            "timestamp": datetime.now().isoformat()
        }

    def execute_trade(self, ca_address):
        """执行交易策略"""
        # 获取当前激活的策略
        strategy = self._load_active_strategy()
        if not strategy:
            return {"error": "No active strategy found"}, 400

        # 获取策略中配置的钱包
        wallets = self._load_wallets(strategy['selectedWallets'])
        if not wallets:
            return {"error": "No valid wallets found in strategy"}, 400

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 创建任务日志
        task_log = {
            "task_id": task_id,
            "ca_address": ca_address,
            "strategy_name": strategy['name'],
            "start_time": datetime.now().isoformat(),
            "status": "pending",
            "transactions": [],
            "wallets": [w['address'] for w in wallets],
            "config": {
                "min_amount": strategy['minBuyAmount'],
                "max_amount": strategy['maxBuyAmount'],
                "slippage": strategy['slippage'],
                "speed_mode": strategy['speedMode'],
                "anti_squeeze": strategy['antiSqueeze']
            }
        }

        # 模拟交易执行
        for wallet in wallets:
            # 模拟延迟
            time.sleep(random.uniform(0.1, 0.5))

            # 生成模拟交易数据
            tx = self._generate_mock_transaction(wallet['address'])
            task_log['transactions'].append(tx)

        # 更新任务状态
        task_log['status'] = random.choice(['completed', 'failed'])
        task_log['end_time'] = datetime.now().isoformat()

        if task_log['status'] == 'failed':
            task_log['error'] = "Mock transaction failed"

        # 保存任务日志
        log_file = self.logs_dir / f"{task_id}.json"
        with open(log_file, 'w') as f:
            json.dump(task_log, f, indent=2)

        return {
            "task_id": task_id,
            "status": task_log['status'],
            "message": "Task created successfully"
        }, 200

    def get_task_status(self, task_id):
        """获取任务状态"""
        log_file = self.logs_dir / f"{task_id}.json"
        if not log_file.exists():
            return None

        with open(log_file, 'r') as f:
            return json.load(f)