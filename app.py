# app.py
from flask import Flask, jsonify, request, render_template
from utilities import (
    StorageManager,
    WalletManager,
    SettingsManager,
    StrategyManager,
    TaskManager,
    LogManager
)
import os
import decimal
from datetime import datetime
from utilities.task_integration import initialize_task_executor

app = Flask(__name__)

# Initialize all managers
storage = StorageManager(data_dir="data")
wallet_manager = WalletManager(storage)
settings_manager = SettingsManager(storage)
strategy_manager = StrategyManager(storage)
task_manager = TaskManager(storage)
log_manager = LogManager(storage)
# 初始化任务执行器
initialize_task_executor(app, storage, task_manager, strategy_manager, log_manager)


# Main route for web interface
@app.route('/')
def index():
    return render_template('index.html')


# Wallet Management API
@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    try:
        return jsonify(wallet_manager.get_public_wallet_info())
    except Exception as e:
        log_manager.add_log("ERROR", f"获取钱包列表失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/wallets', methods=['POST'])
def add_wallet():
    try:
        wallet_data = request.json
        new_wallet = wallet_manager.add_wallet(
            name=wallet_data["name"],
            private_key=wallet_data["privateKey"]
        )
        log_manager.add_log("INFO", f"添加钱包成功: {wallet_data['name']}")
        return jsonify(new_wallet)
    except ValueError as e:
        log_manager.add_log("ERROR", f"添加钱包失败: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        log_manager.add_log("ERROR", f"添加钱包失败: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/wallets/<address>', methods=['DELETE'])
def delete_wallet(address):
    try:
        if wallet_manager.remove_wallet(address):
            log_manager.add_log("INFO", f"删除钱包成功: {address}")
            return jsonify({"success": True})
        log_manager.add_log("ERROR", f"删除钱包失败: 钱包不存在 {address}")
        return jsonify({"error": "Wallet not found"}), 404
    except Exception as e:
        log_manager.add_log("ERROR", f"删除钱包失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Settings Management API
@app.route('/api/settings', methods=['GET'])
def get_settings():
    try:
        return jsonify(settings_manager.settings)
    except Exception as e:
        log_manager.add_log("ERROR", f"获取设置失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/settings', methods=['POST'])
def update_settings():
    try:
        settings_data = request.json
        updated_settings = settings_manager.update_settings(settings_data)
        log_manager.add_log("INFO", "更新设置成功")
        return jsonify(updated_settings)
    except Exception as e:
        log_manager.add_log("ERROR", f"更新设置失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Strategy Management API
@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    try:
        strategies = strategy_manager.strategies
        # Add active status to each strategy
        active_templates = strategy_manager.active_templates
        for strategy in strategies:
            strategy['isActive'] = strategy['id'] in active_templates
        return jsonify(strategies)
    except Exception as e:
        log_manager.add_log("ERROR", f"获取策略列表失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies', methods=['POST'])
def add_strategy():
    try:
        strategy_data = request.json

        # Convert numeric fields to proper precision
        numeric_fields = {
            'minBuyAmount': 4, 'maxBuyAmount': 4,
            'buyPriority': 6, 'sellPriority': 6, 'stopPriority': 6,
            'slippage': 4, 'trailingStop': 4, 'sellPercent': 4
        }

        for field, precision in numeric_fields.items():
            if field in strategy_data:
                strategy_data[field] = round(float(strategy_data[field]), precision)

        # Process stop levels
        if 'stopLevels' in strategy_data:
            for level in strategy_data['stopLevels']:
                level['increase'] = round(float(level['increase']), 4)
                level['sell'] = round(float(level['sell']), 4)
                level['position'] = round(float(level['position']), 4)

        # Process fee settings
        for setting in ['jitoSettings', 'antiSandwichSettings']:
            if setting in strategy_data and 'fee' in strategy_data[setting]:
                strategy_data[setting]['fee'] = round(float(strategy_data[setting]['fee']), 6)

        strategy = strategy_manager.add_or_update_strategy(strategy_data)
        action = "更新" if 'id' in strategy_data else "创建"
        log_manager.add_log("INFO", f"{action}策略成功: {strategy['name']}")
        return jsonify(strategy)
    except Exception as e:
        log_manager.add_log("ERROR", f"保存策略失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    try:
        if strategy_manager.remove_strategy(strategy_id):
            log_manager.add_log("INFO", f"删除策略成功: ID={strategy_id}")
            return jsonify({"success": True})
        return jsonify({"error": "Strategy not found"}), 404
    except Exception as e:
        log_manager.add_log("ERROR", f"删除策略失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/<int:strategy_id>/activate', methods=['POST'])
def activate_strategy(strategy_id):
    try:
        if strategy_manager.activate_template(strategy_id):
            log_manager.add_log("INFO", f"激活策略模板: ID={strategy_id}")
            return jsonify({"success": True})
        return jsonify({"error": "Strategy already active"}), 400
    except Exception as e:
        log_manager.add_log("ERROR", f"激活策略模板失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/<int:strategy_id>/deactivate', methods=['POST'])
def deactivate_strategy(strategy_id):
    try:
        if strategy_manager.deactivate_template(strategy_id):
            log_manager.add_log("INFO", f"停用策略模板: ID={strategy_id}")
            return jsonify({"success": True})
        return jsonify({"error": "Strategy not active"}), 400
    except Exception as e:
        log_manager.add_log("ERROR", f"停用策略模板失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/status', methods=['GET'])
def get_strategy_status():
    try:
        return jsonify({
            "activeTemplates": strategy_manager.active_templates
        })
    except Exception as e:
        log_manager.add_log("ERROR", f"获取策略状态失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Task Management API
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    try:
        strategy_id = request.args.get('strategyId')
        if strategy_id:
            tasks = [task for task in task_manager.get_tasks()
                     if task['strategyId'] == int(strategy_id)]
        else:
            tasks = task_manager.get_tasks()
        return jsonify(tasks)
    except Exception as e:
        log_manager.add_log("ERROR", f"获取任务列表失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# @app.route('/api/tasks', methods=['POST'])
# def create_task():
#     try:
#         data = request.json
#         strategy_id = data.get("strategyId")
#         contract_address = data.get("contractAddress")
#         type_id = data.get("typeId")
#
#         # Check if strategy exists
#         strategy = next((s for s in strategy_manager.strategies if s["id"] == strategy_id), None)
#         if not strategy:
#             log_manager.add_log("ERROR", f"创建任务失败: 策略不存在 ID={strategy_id}")
#             return jsonify({"error": "Strategy not found"}), 404
#
#         task = task_manager.create_task(
#             strategy_id=strategy_id,
#             strategy_name=strategy["name"],
#             contract_address=contract_address,
#             type_id=type_id
#         )
#
#         log_manager.add_log("INFO", f"创建任务成功: {strategy['name']}")
#         return jsonify(task)
#     except Exception as e:
#         log_manager.add_log("ERROR", f"创建任务失败: {str(e)}")
#         return jsonify({"error": str(e)}), 500


# @app.route('/api/tasks/<task_id>/stop', methods=['POST'])
# def stop_task(task_id):
#     try:
#         if task_manager.stop_task(task_id):
#             log_manager.add_log("INFO", f"停止任务成功: ID={task_id}")
#             return jsonify({"success": True})
#         log_manager.add_log("ERROR", f"停止任务失败: 任务不存在 ID={task_id}")
#         return jsonify({"error": "Task not found"}), 404
#     except Exception as e:
#         log_manager.add_log("ERROR", f"停止任务失败: {str(e)}")
#         return jsonify({"error": str(e)}), 500


# Type Management API
@app.route('/api/types', methods=['GET'])
def get_types():
    try:
        types = storage.load_json('types.json', default=[])
        sorted_types = sorted(types, key=lambda x: x['id'])
        return jsonify(sorted_types)
    except Exception as e:
        log_manager.add_log("ERROR", f"获取类型列表失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/types', methods=['POST'])
def add_type():
    try:
        type_data = request.json

        if 'id' not in type_data or 'name' not in type_data:
            return jsonify({"error": "Missing required fields: id and name"}), 400

        if not isinstance(type_data['id'], int) or type_data['id'] <= 0:
            return jsonify({"error": "Type ID must be a positive integer"}), 400

        existing_types = storage.load_json('types.json', default=[])
        if any(t['id'] == type_data['id'] for t in existing_types):
            return jsonify({"error": "Type ID already exists"}), 400

        new_type = {
            "id": type_data['id'],
            "name": type_data['name']
        }
        existing_types.append(new_type)
        storage.save_json('types.json', existing_types)

        log_manager.add_log("INFO", f"添加类型成功: ID={new_type['id']}, 名称={new_type['name']}")
        return jsonify(new_type)
    except Exception as e:
        log_manager.add_log("ERROR", f"添加类型失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/types/<int:type_id>', methods=['DELETE'])
def delete_type(type_id):
    try:
        types = storage.load_json('types.json', default=[])
        initial_count = len(types)
        types = [t for t in types if t['id'] != type_id]

        if len(types) == initial_count:
            return jsonify({"error": "Type not found"}), 404

        storage.save_json('types.json', types)
        log_manager.add_log("INFO", f"删除类型成功: ID={type_id}")
        return jsonify({"success": True})
    except Exception as e:
        log_manager.add_log("ERROR", f"删除类型失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Log Management API
@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        logs = log_manager.get_logs()
        return jsonify(logs[-1000:] if len(logs) > 1000 else logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs', methods=['POST'])
def add_log():
    try:
        log_data = request.json
        log = log_manager.add_log(
            level=log_data.get("level", "INFO"),
            message=log_data["message"]
        )
        return jsonify(log)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs', methods=['DELETE'])
def clear_logs():
    try:
        log_manager.clear_logs()
        log_manager.add_log("INFO", "清除所有日志")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auto-tasks', methods=['POST'])
def create_auto_task():
    try:
        data = request.json
        contract_address = data.get('ca')
        type_id = data.get('type_id')

        if not contract_address or not type_id:
            return jsonify({
                "success": False,
                "message": "Missing required parameters",
                "details": {
                    "contract_address": "Missing" if not contract_address else "Present",
                    "type_id": "Missing" if not type_id else "Present"
                }
            }), 400

        # Check for existing tasks for this contract address
        # existing_tasks = task_manager.get_tasks_by_contract(contract_address)
        # if existing_tasks:
        #     return jsonify({
        #         "success": False,
        #         "message": "Task already exists for this contract",
        #         "details": {
        #             "existing_tasks": [
        #                 {
        #                     "task_id": task["id"],
        #                     "strategy_name": task["strategyName"],
        #                     "start_time": task["startTime"]
        #                 } for task in existing_tasks
        #             ]
        #         }
        #     }), 409

        # Find active strategies that match the type_id
        matching_templates = strategy_manager.get_matching_templates(type_id)

        if not matching_templates:
            return jsonify({
                "success": False,
                "message": "No active strategies found for this type",
                "details": {
                    "type_id": type_id,
                    "active_strategies_count": len(strategy_manager.get_active_templates()),
                    "total_strategies_count": len(strategy_manager.strategies)
                }
            }), 404

        # Create tasks for matching templates
        created_tasks = []
        for template in matching_templates:
            task = task_manager.create_task(
                strategy_id=template['id'],
                strategy_name=template['name'],
                contract_address=contract_address,
                type_id=type_id
            )
            created_tasks.append({
                "task_id": task["id"],
                "strategy_name": task["strategyName"],
                "contract_address": task["contractAddress"],
                "start_time": task["startTime"],
                "status": task["status"]
            })

            log_manager.add_log(
                "INFO",
                f"自动创建任务成功: 策略={template['name']}, 合约={contract_address}, 类型={type_id}"
            )

        return jsonify({
            "success": True,
            "message": f"Successfully created {len(created_tasks)} tasks",
            "details": {
                "contract_address": contract_address,
                "type_id": type_id,
                "created_tasks": created_tasks,
                "matching_strategies": [
                    {
                        "id": template["id"],
                        "name": template["name"]
                    } for template in matching_templates
                ]
            }
        })

    except Exception as e:
        log_manager.add_log("ERROR", f"自动创建任务失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to create auto tasks",
            "details": {
                "error": str(e)
            }
        }), 500


# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# Health Check Endpoint
@app.route('/health')
def health_check():
    try:
        # Check all critical components
        storage.load_json('settings.json')
        strategy_manager.load_strategies()
        task_manager.load_tasks()
        wallet_manager.load_wallets()

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500


# Strategy Statistics API
@app.route('/api/strategies/stats', methods=['GET'])
def get_strategy_stats():
    try:
        stats = {
            'total': len(strategy_manager.strategies),
            'active': len(strategy_manager.active_templates),
            'types': {},
            'wallets': {}
        }

        # Count strategies by type
        for strategy in strategy_manager.strategies:
            for type_id in strategy.get('selectedTypes', []):
                stats['types'][type_id] = stats['types'].get(type_id, 0) + 1

        # Count strategies by wallet
        for strategy in strategy_manager.strategies:
            for wallet in strategy.get('selectedWallets', []):
                stats['wallets'][wallet] = stats['wallets'].get(wallet, 0) + 1

        return jsonify(stats)
    except Exception as e:
        log_manager.add_log("ERROR", f"获取策略统计失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Task Statistics API
@app.route('/api/tasks/stats', methods=['GET'])
def get_task_stats():
    try:
        all_tasks = task_manager.get_tasks()
        stats = {
            'total': len(all_tasks),
            'running': len([t for t in all_tasks if t['status'] == 'running']),
            'stopped': len([t for t in all_tasks if t['status'] == 'stopped']),
            'by_strategy': {},
            'by_type': {}
        }

        # Count tasks by strategy
        for task in all_tasks:
            strategy_id = task.get('strategyId')
            if strategy_id:
                stats['by_strategy'][strategy_id] = stats['by_strategy'].get(strategy_id, 0) + 1

        # Count tasks by type
        for task in all_tasks:
            type_id = task.get('typeId')
            if type_id:
                stats['by_type'][type_id] = stats['by_type'].get(type_id, 0) + 1

        return jsonify(stats)
    except Exception as e:
        log_manager.add_log("ERROR", f"获取任务统计失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Batch Operations API
@app.route('/api/tasks/batch/stop', methods=['POST'])
def stop_tasks_batch():
    try:
        data = request.json
        task_ids = data.get('taskIds', [])

        if not task_ids:
            return jsonify({"error": "No task IDs provided"}), 400

        results = {
            'success': [],
            'failed': []
        }

        for task_id in task_ids:
            try:
                if task_manager.stop_task(task_id):
                    results['success'].append(task_id)
                    log_manager.add_log("INFO", f"批量停止任务成功: ID={task_id}")
                else:
                    results['failed'].append({"id": task_id, "reason": "Task not found"})
            except Exception as e:
                results['failed'].append({"id": task_id, "reason": str(e)})

        return jsonify(results)
    except Exception as e:
        log_manager.add_log("ERROR", f"批量停止任务失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/batch/activate', methods=['POST'])
def activate_strategies_batch():
    try:
        data = request.json
        strategy_ids = data.get('strategyIds', [])

        if not strategy_ids:
            return jsonify({"error": "No strategy IDs provided"}), 400

        results = {
            'success': [],
            'failed': []
        }

        for strategy_id in strategy_ids:
            try:
                if strategy_manager.activate_template(strategy_id):
                    results['success'].append(strategy_id)
                    log_manager.add_log("INFO", f"批量激活策略成功: ID={strategy_id}")
                else:
                    results['failed'].append({"id": strategy_id, "reason": "Already active"})
            except Exception as e:
                results['failed'].append({"id": strategy_id, "reason": str(e)})

        return jsonify(results)
    except Exception as e:
        log_manager.add_log("ERROR", f"批量激活策略失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/batch/deactivate', methods=['POST'])
def deactivate_strategies_batch():
    try:
        data = request.json
        strategy_ids = data.get('strategyIds', [])

        if not strategy_ids:
            return jsonify({"error": "No strategy IDs provided"}), 400

        results = {
            'success': [],
            'failed': []
        }

        for strategy_id in strategy_ids:
            try:
                if strategy_manager.deactivate_template(strategy_id):
                    results['success'].append(strategy_id)
                    log_manager.add_log("INFO", f"批量停用策略成功: ID={strategy_id}")
                else:
                    results['failed'].append({"id": strategy_id, "reason": "Not active"})
            except Exception as e:
                results['failed'].append({"id": strategy_id, "reason": str(e)})

        return jsonify(results)
    except Exception as e:
        log_manager.add_log("ERROR", f"批量停用策略失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')

    app.run(debug=True, port=2000, host='0.0.0.0')
