# task_integration.py
from flask import request, jsonify
from .task_executor import TaskExecutor


def initialize_task_executor(app, storage_manager, task_manager, strategy_manager, log_manager):
    """初始化任务执行器并添加所需的路由处理器"""

    # 创建任务执行器实例
    executor = TaskExecutor(storage_manager)

    # 将执行器存储在应用程序上下文中
    app.task_executor = executor

    # 修改现有的任务创建端点
    @app.route('/api/tasks', methods=['POST'])
    def create_task():
        try:
            data = request.json
            strategy_id = data.get("strategyId")
            contract_address = data.get("contractAddress")
            type_id = data.get("typeId")

            # 查找策略
            strategy = next((s for s in strategy_manager.strategies if s["id"] == strategy_id), None)
            if not strategy:
                log_manager.add_log("ERROR", f"创建任务失败: 策略不存在 ID={strategy_id}")
                return jsonify({"error": "Strategy not found"}), 404

            # 创建任务
            task = task_manager.create_task(
                strategy_id=strategy_id,
                strategy_name=strategy["name"],
                contract_address=contract_address,
                type_id=type_id
            )

            # 启动任务执行
            executor.start_task(task, strategy)

            log_manager.add_log("INFO", f"创建并启动任务成功: {strategy['name']}")
            return jsonify(task)

        except Exception as e:
            log_manager.add_log("ERROR", f"创建任务失败: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # 修改现有的任务停止端点
    @app.route('/api/tasks/<task_id>/stop', methods=['POST'])
    def stop_task(task_id):
        try:
            # 停止任务执行
            executor.stop_task(task_id)

            # 更新存储中的任务状态
            if task_manager.stop_task(task_id):
                log_manager.add_log("INFO", f"停止任务成功: ID={task_id}")
                return jsonify({"success": True})

            log_manager.add_log("ERROR", f"停止任务失败: 任务不存在 ID={task_id}")
            return jsonify({"error": "Task not found"}), 404

        except Exception as e:
            log_manager.add_log("ERROR", f"停止任务失败: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # 添加新的任务执行状态端点
    @app.route('/api/tasks/status', methods=['GET'])
    def get_task_status():
        try:
            return jsonify({
                "active_tasks": executor.get_active_task_count(),
                "task_ids": executor.get_active_task_ids()
            })
        except Exception as e:
            log_manager.add_log("ERROR", f"获取任务状态失败: {str(e)}")
            return jsonify({"error": str(e)}), 500