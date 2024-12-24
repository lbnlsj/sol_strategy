# task_executor.py
from threading import Thread, Event
import time
from typing import Dict, List
import json
from datetime import datetime


class TaskExecutor:
    def __init__(self, storage_manager):
        self.storage_manager = storage_manager
        self.active_tasks = {}  # task_id -> Thread
        self.stop_events = {}  # task_id -> Event

    def start_task(self, task: Dict, strategy: Dict):
        """启动新的任务线程"""
        if task['id'] in self.active_tasks:
            print(f"任务 {task['id']} 已在运行中")
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

        print(f"已启动任务 {task['id']}, 策略名称: {strategy['name']}")
        return True

    def stop_task(self, task_id: str):
        """停止运行中的任务"""
        if task_id not in self.active_tasks:
            print(f"任务 {task_id} 未在运行")
            return False

        self.stop_events[task_id].set()
        self.active_tasks[task_id].join(timeout=2.0)

        if self.active_tasks[task_id].is_alive():
            print(f"警告: 任务 {task_id} 未能正常停止")

        del self.active_tasks[task_id]
        del self.stop_events[task_id]

        print(f"已停止任务 {task_id}")
        return True

    def _run_task(self, task: Dict, strategy: Dict, stop_event: Event):
        """任务执行主循环"""
        try:
            print(f"\n开始执行任务 {task['id']}")
            print("任务参数:")
            print(f"- 合约地址: {task['contractAddress']}")
            print(f"- 策略名称: {strategy['name']}")
            print(f"- 类型ID: {task['typeId']}")

            # 打印策略参数
            print("\n策略配置:")
            print(f"- 速度模式: {strategy['speedMode']}")
            print(f"- 防夹模式: {strategy['antiSqueeze']}")
            print(f"- 买入金额范围: {strategy['minBuyAmount']} - {strategy['maxBuyAmount']} SOL")
            print(f"- 滑点: {strategy['slippage']}%")
            print(f"- 移动止损: {strategy['trailingStop']}%")

            # 模拟监控和交易循环
            while not stop_event.is_set():
                current_time = datetime.now().strftime("%H:%M:%S")

                # 模拟市场检查
                print(f"\n[{current_time}] 检查市场状况 {task['contractAddress']}")
                print("- 模拟价格监控...")
                time.sleep(2)  # 模拟监控延迟

                # 模拟交易决策
                print("- 分析交易机会...")
                time.sleep(1)  # 模拟分析延迟

                # 模拟钱包余额检查
                print("- 检查钱包余额...")
                for wallet in strategy['selectedWallets']:
                    print(f"  钱包地址 {wallet[:8]}...{wallet[-6:]}")
                time.sleep(1)  # 模拟钱包检查延迟

                # 等待下一次迭代
                time.sleep(5)  # 主循环延迟

        except Exception as e:
            print(f"任务 {task['id']} 执行错误: {str(e)}")
        finally:
            print(f"\n任务 {task['id']} 执行完成")

    def get_active_task_count(self) -> int:
        """返回当前活动任务数量"""
        return len(self.active_tasks)

    def get_active_task_ids(self) -> List[str]:
        """返回活动任务ID列表"""
        return list(self.active_tasks.keys())