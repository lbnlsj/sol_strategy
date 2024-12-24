from typing import Dict, List
from .storage import StorageManager


class StrategyManager:
    def __init__(self, storage: StorageManager):
        self.storage = storage
        self.strategies = self.load_strategies()
        self.active_templates = self.load_active_templates()

    def load_strategies(self) -> List[Dict]:
        """加载所有策略模板"""
        return self.storage.load_json('strategies.json', default=[])

    def load_active_templates(self) -> List[int]:
        """加载已激活的模板ID列表"""
        return self.storage.load_json('active_templates.json', default=[])

    def save_strategies(self) -> None:
        """保存策略信息"""
        self.storage.save_json('strategies.json', self.strategies)

    def save_active_templates(self) -> None:
        """保存激活的模板状态"""
        self.storage.save_json('active_templates.json', self.active_templates)

    def add_or_update_strategy(self, strategy: Dict) -> Dict:
        """添加或更新策略模板"""
        if 'id' in strategy:
            # 更新现有策略
            for i, existing in enumerate(self.strategies):
                if existing['id'] == strategy['id']:
                    self.strategies[i] = strategy
                    break
        else:
            # 添加新策略
            strategy['id'] = len(self.strategies) + 1
            self.strategies.append(strategy)

        self.save_strategies()
        return strategy

    def remove_strategy(self, strategy_id: int) -> bool:
        """删除策略模板"""
        initial_length = len(self.strategies)
        self.strategies = [s for s in self.strategies if s['id'] != strategy_id]

        # 如果删除模板，同时也从激活列表中移除
        if strategy_id in self.active_templates:
            self.deactivate_template(strategy_id)

        if len(self.strategies) < initial_length:
            self.save_strategies()
            return True
        return False

    def activate_template(self, template_id: int) -> bool:
        """激活策略模板"""
        if template_id not in self.active_templates:
            self.active_templates.append(template_id)
            self.save_active_templates()
            return True
        return False

    def deactivate_template(self, template_id: int) -> bool:
        """停用策略模板"""
        if template_id in self.active_templates:
            self.active_templates.remove(template_id)
            self.save_active_templates()
            return True
        return False

    def get_matching_templates(self, type_id: int) -> List[Dict]:
        """根据类型ID获取匹配的活跃模板"""
        return [
            strategy for strategy in self.strategies
            if strategy['id'] in self.active_templates
               and type_id in strategy['selectedTypes']
        ]

    def is_template_active(self, template_id: int) -> bool:
        """检查模板是否处于激活状态"""
        return template_id in self.active_templates

    def get_active_templates(self) -> List[Dict]:
        """获取所有激活状态的模板"""
        return [
            strategy for strategy in self.strategies
            if strategy['id'] in self.active_templates
        ]