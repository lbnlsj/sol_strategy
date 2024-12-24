# utilities/wallet.py
from typing import Dict, List
from solders.keypair import Keypair
import base58
from .storage import StorageManager


class WalletManager:
    def __init__(self, storage: StorageManager):
        self.storage = storage
        self.wallets = self.load_wallets()

    def load_wallets(self) -> List[Dict]:
        """加载所有钱包信息"""
        return self.storage.load_json('wallets.json', default=[])

    def save_wallets(self) -> None:
        """保存钱包信息"""
        self.storage.save_json('wallets.json', self.wallets)

    def add_wallet(self, name: str, private_key: str) -> Dict:
        """添加新钱包"""
        try:
            # 处理不同格式的私钥
            if '[' in private_key:  # 数组格式
                secret_key_bytes = bytes(eval(private_key))
                keypair = Keypair.from_bytes(secret_key_bytes)
            else:  # Base58格式
                try:
                    keypair = Keypair.from_base58_string(private_key)
                except:
                    # 尝试将十六进制转换为base58
                    if private_key.startswith('0x'):
                        private_key = private_key[2:]
                    secret_key_bytes = bytes.fromhex(private_key)
                    keypair = Keypair.from_bytes(secret_key_bytes)

            wallet = {
                "name": name,
                "address": str(keypair.pubkey()),
                "private_key": base58.b58encode(bytes(keypair.secret())).decode('utf-8')
            }

            # 检查是否已存在
            if any(w['address'] == wallet['address'] for w in self.wallets):
                raise ValueError("钱包地址已存在")

            self.wallets.append(wallet)
            self.save_wallets()

            # 返回不包含私钥的钱包信息
            return {
                "name": wallet["name"],
                "address": wallet["address"]
            }

        except Exception as e:
            raise ValueError(f"无效的私钥格式: {str(e)}")

    def remove_wallet(self, address: str) -> bool:
        """删除钱包"""
        initial_length = len(self.wallets)
        self.wallets = [w for w in self.wallets if w['address'] != address]
        if len(self.wallets) < initial_length:
            self.save_wallets()
            return True
        return False

    def get_wallet(self, address: str) -> Dict:
        """获取钱包信息（包括私钥）"""
        wallet = next((w for w in self.wallets if w['address'] == address), None)
        if wallet:
            return wallet.copy()
        raise ValueError("钱包不存在")

    def get_public_wallet_info(self) -> List[Dict]:
        """获取所有钱包的公开信息（不包括私钥）"""
        return [{
            "name": w["name"],
            "address": w["address"]
        } for w in self.wallets]