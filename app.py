from flask import Flask, jsonify, request, render_template
import json
from datetime import datetime
import os

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

# 修改 app.py 中的任务相关代码

from flask import Flask, jsonify, request
from datetime import datetime

# 添加新的模拟数据存储
mock_tasks = {}  # 存储运行中的任务
task_counter = 0  # 用于生成任务ID

# 在 app.py 中添加策略 ID 计数器
strategy_id_counter = 0  # 用于生成策略ID


# 修改策略保存/更新接口
@app.route('/api/strategies', methods=['POST'])
def add_strategy():
    global strategy_id_counter
    strategy_data = request.json

    # 如果传入了strategy_id，说明是更新操作
    strategy_id = strategy_data.get('id')

    if strategy_id is not None:
        # 更新现有策略
        existing_strategy = next(
            (s for s in mock_strategies if s["id"] == strategy_id),
            None
        )
        if existing_strategy:
            for i, strategy in enumerate(mock_strategies):
                if strategy["id"] == strategy_id:
                    # 保持原有ID
                    strategy_data["id"] = strategy_id
                    mock_strategies[i] = strategy_data
                    return jsonify(strategy_data)
            return jsonify({"error": "Strategy not found"}), 404
    else:
        # 添加新策略
        strategy_id_counter += 1
        strategy_data["id"] = strategy_id_counter
        mock_strategies.append(strategy_data)

    return jsonify(strategy_data)


# 修改策略删除接口
@app.route('/api/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    global mock_strategies
    original_length = len(mock_strategies)
    mock_strategies = [s for s in mock_strategies if s["id"] != strategy_id]

    if len(mock_strategies) == original_length:
        return jsonify({"error": "Strategy not found"}), 404

    return jsonify({"success": True})


# 修改获取单个策略接口
@app.route('/api/strategies/<int:strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    strategy = next(
        (s for s in mock_strategies if s["id"] == strategy_id),
        None
    )
    if strategy:
        return jsonify(strategy)
    return jsonify({"error": "Strategy not found"}), 404


# 修改任务创建接口
@app.route('/api/tasks', methods=['POST'])
def create_task():
    global task_counter
    data = request.json
    strategy_id = data.get("strategyId")

    # 检查策略是否存在
    strategy = next((s for s in mock_strategies if s["id"] == strategy_id), None)
    if not strategy:
        return jsonify({"error": "Strategy not found"}), 404

    # 生成任务ID
    task_counter += 1
    task_id = str(task_counter)

    # 创建新任务
    task = {
        "id": task_id,
        "strategyId": strategy_id,
        "strategyName": strategy["name"],  # 保存策略名称用于显示
        "startTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "running"
    }

    mock_tasks[task_id] = task
    return jsonify(task)


# 任务管理相关接口
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    # 返回所有运行中的任务
    return jsonify([
        {
            "id": task_id,
            "templateName": task["templateName"],
            "startTime": task["startTime"],
            "status": task["status"]
        }
        for task_id, task in mock_tasks.items()
    ])


@app.route('/api/tasks/<task_id>/stop', methods=['POST'])
def stop_task(task_id):
    if task_id in mock_tasks:
        del mock_tasks[task_id]
        return jsonify({"success": True})
    return jsonify({"error": "Task not found"}), 404


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    task = mock_tasks.get(task_id)
    if task:
        return jsonify(task)
    return jsonify({"error": "Task not found"}), 404


# 模拟数据存储
mock_wallets = []
mock_strategies = []
mock_types = []
mock_logs = []
mock_settings = {
    "rpcUrl": "https://api.mainnet-beta.solana.com",
    "jitoRpcUrl": "https://jito-api.mainnet-beta.solana.com",
    "wsUrl": "wss://api.mainnet-beta.solana.com",
    "wsPort": 8900
}
active_strategy = None


# 模拟一些初始数据
def init_mock_data():
    global strategy_id_counter  # 确保可以更新全局计数器

    # 添加一些模拟钱包
    mock_wallets.extend([
        {
            "name": "测试钱包1",
            "address": "HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"
        },
        {
            "name": "测试钱包2",
            "address": "5BZWY6XWPxuWFxs2jagkmUkCoBWmJ6c4YEArr83hYBWk"
        }
    ])

    # 添加一些模拟类型
    mock_types.extend([
        {
            "id": 1,
            "name": "类型1"
        },
        {
            "id": 2,
            "name": "类型2"
        }
    ])

    # 添加一些模拟策略
    strategy_id_counter += 1  # 增加计数器
    mock_strategies.extend([
        {
            "id": strategy_id_counter,  # 使用计数器作为ID
            "name": "默认策略",
            "selectedWallets": ["HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"],
            "minBuyAmount": 0.3,
            "maxBuyAmount": 0.5,
            "speedMode": "normal",
            "antiSqueeze": "off",
            "buyPriority": 0.003,
            "sellPriority": 0.003,
            "stopPriority": 0.003,
            "slippage": 0.25,
            "trailingStop": 50,
            "sellPercent": 100,
            "stopLevels": [
                {"increase": 50, "sell": 50, "position": 50},
                {"increase": 100, "sell": 100, "position": 100}
            ],
            "selectedTypes": [1],  # 使用类型ID而不是字符串
            "jitoSettings": {
                "enabled": False,
                "fee": 0.0001
            },
            "antiSandwichSettings": {
                "enabled": False,
                "fee": 0.0001
            }
        }
    ])


# 初始化模拟数据
init_mock_data()


# 主页路由
@app.route('/')
def index():
    return render_template('index.html')


# API路由定义
@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    return jsonify(mock_wallets)


@app.route('/api/wallets', methods=['POST'])
def add_wallet():
    wallet_data = request.json

    # 模拟通过私钥生成地址
    import random
    mock_address = ''.join(random.choices('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz', k=44))

    new_wallet = {
        "name": wallet_data["name"],
        "address": mock_address
    }
    mock_wallets.append(new_wallet)
    return jsonify(new_wallet)


@app.route('/api/wallets/<address>', methods=['DELETE'])
def delete_wallet(address):
    global mock_wallets
    mock_wallets = [w for w in mock_wallets if w["address"] != address]
    return jsonify({"success": True})


@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    return jsonify(mock_strategies)


@app.route('/api/active-strategy', methods=['GET'])
def get_active_strategy():
    return jsonify({"activeStrategy": active_strategy})


@app.route('/api/active-strategy', methods=['POST'])
def set_active_strategy():
    global active_strategy
    data = request.json
    active_strategy = data.get("strategyName")
    return jsonify({"success": True})


@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(mock_settings)


@app.route('/api/settings', methods=['POST'])
def update_settings():
    global mock_settings
    settings_data = request.json
    mock_settings.update(settings_data)
    return jsonify(mock_settings)


# 类型管理API
@app.route('/api/types', methods=['GET'])
def get_types():
    return jsonify(mock_types)


@app.route('/api/types', methods=['POST'])
def add_type():
    type_data = request.json
    type_id = type_data.get("id")
    name = type_data.get("name")

    # 验证类型ID是否为整数
    try:
        type_id = int(type_id)
    except (ValueError, TypeError):
        return jsonify({"error": "类型ID必须为整数"}), 400

    # 检查ID是否已存在
    if any(t["id"] == type_id for t in mock_types):
        return jsonify({"error": "类型ID已存在"}), 400

    new_type = {
        "id": type_id,
        "name": name
    }
    mock_types.append(new_type)
    return jsonify(new_type)


@app.route('/api/types/<type_id>', methods=['DELETE'])
def delete_type(type_id):
    global mock_types
    mock_types = [t for t in mock_types if t["id"] != type_id]
    # 同时更新所有策略中的类型选择
    for strategy in mock_strategies:
        strategy["selectedTypes"] = [t for t in strategy["selectedTypes"] if t != type_id]
    return jsonify({"success": True})


# 日志API
@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(mock_logs)


@app.route('/api/logs', methods=['POST'])
def add_log():
    log_data = request.json
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "level": log_data.get("level", "INFO"),
        "message": log_data["message"]
    }
    mock_logs.append(log_entry)
    # 保持日志不超过1000条
    if len(mock_logs) > 1000:
        mock_logs.pop(0)
    return jsonify(log_entry)


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=2000, host='0.0.0.0')
