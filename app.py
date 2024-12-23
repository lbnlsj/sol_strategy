from flask import Flask, request, jsonify, render_template
import json
from solders.keypair import Keypair
from pathlib import Path
import os
from utilities.webhook_handler import WebhookExecutor

app = Flask(__name__)

# 创建数据存储目录
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

WALLETS_FILE = DATA_DIR / "wallets.json"
STRATEGIES_FILE = DATA_DIR / "strategies.json"
ACTIVE_STRATEGY_FILE = DATA_DIR / "active_strategy.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# 默认设置
DEFAULT_SETTINGS = {
    "rpcUrl": "https://api.mainnet-beta.solana.com",
    "jitoRpcUrl": "https://jito-api.mainnet-beta.solana.com",
    "wsUrl": "wss://api.mainnet-beta.solana.com",
    "wsPort": 8900
}

# 初始化WebhookExecutor
webhook_executor = WebhookExecutor(DATA_DIR)


def get_active_strategy():
    """获取当前激活的策略"""
    if ACTIVE_STRATEGY_FILE.exists():
        with open(ACTIVE_STRATEGY_FILE, 'r') as f:
            data = json.load(f)
            return data.get('activeStrategy')
    return None


def save_active_strategy(strategy_name):
    """保存当前激活的策略"""
    with open(ACTIVE_STRATEGY_FILE, 'w') as f:
        json.dump({'activeStrategy': strategy_name}, f)


def load_data(file_path):
    """加载JSON数据文件"""
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return []


def save_data(data, file_path):
    """保存数据到JSON文件"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


# 添加新的路由处理激活的策略
@app.route('/api/active-strategy', methods=['GET'])
def get_current_strategy():
    """获取当前激活的策略"""
    active_strategy = get_active_strategy()
    return jsonify({'activeStrategy': active_strategy})


@app.route('/api/active-strategy', methods=['POST'])
def set_current_strategy():
    """设置当前激活的策略"""
    data = request.json
    strategy_name = data.get('strategyName')
    if strategy_name:
        save_active_strategy(strategy_name)
        return jsonify({'status': 'success', 'activeStrategy': strategy_name})
    return jsonify({'error': 'No strategy name provided'}), 400


# 路由定义
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    """获取所有钱包"""
    wallets = load_data(WALLETS_FILE)
    return jsonify(wallets)


@app.route('/api/wallets', methods=['POST'])
def add_wallet():
    """添加新钱包"""
    data = request.json
    name = data.get('name')
    private_key = data.get('privateKey')

    try:
        # 检查私钥格式并转换为Keypair
        if isinstance(private_key, list):
            # 验证list格式私钥
            if len(private_key) != 64:
                raise ValueError("Invalid private key array length")
            try:
                keypair = Keypair.from_bytes(bytes(private_key))
            except Exception as e:
                raise ValueError(f"Invalid private key array format: {str(e)}")
        else:
            # 尝试解析为base58格式
            try:
                keypair = Keypair.from_base58_string(private_key)
            except Exception as e:
                raise ValueError(f"Invalid private key format: {str(e)}")

        # 生成公钥地址
        address = str(keypair.pubkey())

        wallets = load_data(WALLETS_FILE)

        # 检查是否已存在
        if any(w['address'] == address for w in wallets):
            return jsonify({"error": "Wallet already exists"}), 400

        wallet = {
            "name": name,
            "address": address,
            "privateKey": private_key
        }

        wallets.append(wallet)
        save_data(wallets, WALLETS_FILE)

        return jsonify(wallet)

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/wallets/<address>', methods=['DELETE'])
def delete_wallet(address):
    """删除钱包"""
    wallets = load_data(WALLETS_FILE)
    wallets = [w for w in wallets if w['address'] != address]
    save_data(wallets, WALLETS_FILE)
    return jsonify({"status": "success"})


@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """获取所有策略"""
    strategies = load_data(STRATEGIES_FILE)
    return jsonify(strategies)


@app.route('/api/strategies', methods=['POST'])
def save_strategy():
    """保存策略"""
    strategy = request.json
    strategies = load_data(STRATEGIES_FILE)

    # 检查是否是更新现有策略
    for i, existing in enumerate(strategies):
        if existing['name'] == strategy['name']:
            strategies[i] = strategy
            save_data(strategies, STRATEGIES_FILE)
            return jsonify(strategy)

    # 添加新策略
    strategies.append(strategy)
    save_data(strategies, STRATEGIES_FILE)
    return jsonify(strategy)


@app.route('/api/strategies/<name>', methods=['DELETE'])
def delete_strategy(name):
    """删除策略"""
    strategies = load_data(STRATEGIES_FILE)
    strategies = [s for s in strategies if s['name'] != name]
    save_data(strategies, STRATEGIES_FILE)
    return jsonify({"status": "success"})


# 修改webhook端点
@app.route('/api/create_task', methods=['POST'])
def handle_webhook():
    """处理webhook请求"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    ca_address = data.get('ca_address')
    if not ca_address:
        return jsonify({"error": "No CA address provided"}), 400

    # 验证CA地址格式
    if not ca_address.strip():
        return jsonify({"error": "Invalid CA address"}), 400

    try:
        # 执行交易策略
        result, status_code = webhook_executor.execute_trade(ca_address)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 修改状态检查端点
@app.route('/api/status/<task_id>', methods=['GET'])
def check_status(task_id):
    """检查特定任务的状态"""
    task_status = webhook_executor.get_task_status(task_id)
    if task_status:
        return jsonify(task_status)
    return jsonify({
        "error": "Task not found"
    }), 404


# 添加获取CA地址所有任务的端点
@app.route('/api/tasks/<ca_address>', methods=['GET'])
def get_ca_tasks(ca_address):
    """获取特定CA地址的所有任务"""
    # 遍历任务目录获取所有日志文件
    tasks = []
    for log_file in webhook_executor.logs_dir.glob("*.json"):
        with open(log_file, 'r') as f:
            task_data = json.load(f)
            if task_data.get('ca_address') == ca_address:
                tasks.append(task_data)

    return jsonify({
        "ca_address": ca_address,
        "tasks": sorted(tasks, key=lambda x: x.get('start_time', ''), reverse=True)
    })


if __name__ == '__main__':
    app.run(debug=True, port=7834, host='0.0.0.0')
