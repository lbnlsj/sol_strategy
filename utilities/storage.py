# utilities/storage.py
import json
import os
from typing import Dict, List, Any


class StorageManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _get_file_path(self, filename: str) -> str:
        """获取完整的文件路径"""
        return os.path.join(self.data_dir, filename)

    def save_json(self, filename: str, data: Any) -> None:
        """保存JSON数据到文件"""
        file_path = self._get_file_path(filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_json(self, filename: str, default: Any = None) -> Any:
        """从文件加载JSON数据"""
        file_path = self._get_file_path(filename)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {str(e)}")
        return default if default is not None else {}