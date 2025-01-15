from typing import Dict, List
from .storage import StorageManager


class StrategyManager:
    def __init__(self, storage: StorageManager):
        self.storage = storage
        self.strategies = self.load_strategies()

    def load_strategies(self) -> List[Dict]:
        """加载所有策略模板"""
        return self.storage.load_json('strategies.json', default=[])

    def save_strategies(self) -> None:
        """保存策略信息"""
        self.storage.save_json('strategies.json', self.strategies)

    def add_or_update_strategy(self, strategy: Dict) -> Dict:
        """添加或更新策略模板"""
        if 'id' in strategy:
            # 更新现有策略
            for i, existing in enumerate(self.strategies):
                if existing['id'] == strategy['id']:
                    # 保持现有的激活状态
                    if 'isActive' not in strategy and 'isActive' in existing:
                        strategy['isActive'] = existing['isActive']
                    self.strategies[i] = strategy
                    break
        else:
            # 添加新策略，默认为未激活状态
            strategy['id'] = len(self.strategies) + 1
            strategy['isActive'] = False
            self.strategies.append(strategy)

        self.save_strategies()
        return strategy

    def remove_strategy(self, strategy_id: int) -> bool:
        """删除策略模板"""
        initial_length = len(self.strategies)
        self.strategies = [s for s in self.strategies if s['id'] != strategy_id]

        if len(self.strategies) < initial_length:
            self.save_strategies()
            return True
        return False

    def activate_template(self, template_id: int) -> bool:
        """激活策略模板"""
        for strategy in self.strategies:
            if strategy['id'] == template_id:
                strategy['isActive'] = True
                self.save_strategies()
                return True
        return False

    def deactivate_template(self, template_id: int) -> bool:
        """停用策略模板"""
        for strategy in self.strategies:
            if strategy['id'] == template_id:
                strategy['isActive'] = False
                self.save_strategies()
                return True
        return False

    def get_matching_templates(self, type_id: int) -> List[Dict]:
        """根据类型ID获取匹配的活跃模板"""
        return [
            strategy for strategy in self.strategies
            if strategy.get('isActive', False) and type_id in strategy['selectedTypes']
        ]

    def is_template_active(self, template_id: int) -> bool:
        """检查模板是否处于激活状态"""
        for strategy in self.strategies:
            if strategy['id'] == template_id:
                return strategy.get('isActive', False)
        return False

    def get_active_templates(self) -> List[Dict]:
        """获取所有激活状态的模板"""
        return [
            strategy for strategy in self.strategies
            if strategy.get('isActive', False)
        ]