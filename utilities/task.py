from typing import Dict, List
from datetime import datetime
from .storage import StorageManager

class TaskManager:
    def __init__(self, storage: StorageManager):
        self.storage = storage
        self.tasks = self.load_tasks()
        self.task_counter = max([int(task['id']) for task in self.tasks.values()], default=0)

    def load_tasks(self) -> Dict:
        """加载所有任务"""
        return self.storage.load_json('tasks.json', default={})

    def save_tasks(self) -> None:
        """保存任务信息"""
        self.storage.save_json('tasks.json', self.tasks)

    def create_task(self, strategy_id: int, strategy_name: str, contract_address: str, type_id: int) -> Dict:
        """根据策略模板创建新任务"""
        self.task_counter += 1
        task_id = str(self.task_counter)

        task = {
            "id": task_id,
            "strategyId": strategy_id,
            "strategyName": strategy_name,
            "contractAddress": contract_address,
            "typeId": type_id,  # 添加类型ID字段
            "startTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "running"
        }

        self.tasks[task_id] = task
        self.save_tasks()
        return task

    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = 'stopped'
            self.save_tasks()
            return True
        return False

    def get_tasks(self) -> List[Dict]:
        """获取所有运行中的任务"""
        return [
            task for task in self.tasks.values() 
            # if task['status'] == 'running'
        ]

    def get_tasks_by_type(self, type_id: int) -> List[Dict]:
        """获取指定类型的所有运行中任务"""
        return [
            task for task in self.tasks.values()
            if task['status'] == 'running' and task.get('typeId') == type_id
        ]

    def get_tasks_by_contract(self, contract_address: str) -> List[Dict]:
        """获取指定合约地址的所有运行中任务"""
        return [
            task for task in self.tasks.values()
            if task['status'] == 'running' and task['contractAddress'] == contract_address
        ]