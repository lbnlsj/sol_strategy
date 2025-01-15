# utilities/log.py
from typing import Dict, List
from datetime import datetime
from .storage import StorageManager


class LogManager:
    def __init__(self, storage: StorageManager, max_logs: int = 1000):
        self.storage = storage
        self.max_logs = max_logs
        self.logs = self.load_logs()

    def load_logs(self) -> List[Dict]:
        """加载日志"""
        return self.storage.load_json('logs.json', default=[])

    def save_logs(self) -> None:
        """保存日志"""
        self.storage.save_json('logs.json', self.logs)

    def add_log(self, level: str, message: str) -> Dict:
        """添加新日志"""
        log = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level.upper(),
            "message": message
        }

        self.logs.append(log)

        # 保持日志数量在限制范围内
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

        self.save_logs()
        return log

    def clear_logs(self) -> None:
        """清除所有日志"""
        self.logs = []
        self.save_logs()

    def get_logs(self) -> List[Dict]:
        """获取所有日志"""
        return self.logs