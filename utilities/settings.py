# utilities/settings.py
from typing import Dict
from .storage import StorageManager


class SettingsManager:
    def __init__(self, storage: StorageManager):
        self.storage = storage
        self.settings = self.load_settings()

    def load_settings(self) -> Dict:
        """加载设置"""
        return self.storage.load_json('settings.json', default={
            "rpcUrl": "https://staked.helius-rpc.com?api-key=bc8bd2ae-8330-4a02-9c98-2970d98545cd",
            "jitoRpcUrl": "https://jito-api.mainnet-beta.solana.com",
            "wsUrl": "wss://api.mainnet-beta.solana.com",
            "wsPort": 8900
        })

    def save_settings(self) -> None:
        """保存设置"""
        self.storage.save_json('settings.json', self.settings)

    def update_settings(self, new_settings: Dict) -> Dict:
        """更新设置"""
        self.settings.update(new_settings)
        self.save_settings()
        return self.settings