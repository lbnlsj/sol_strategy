import traceback
import json
from flask import request, jsonify
from .task_executor import TaskExecutor


def initialize_task_executor(app, storage_manager, task_manager, strategy_manager, log_manager):
    """初始化任务执行器并添加所需的路由处理器"""

    # 创建任务执行器实例，传入log_manager
    executor = TaskExecutor(storage_manager, log_manager=log_manager)

    # 将执行器存储在应用程序上下文中
    app.task_executor = executor

    @app.route('/api/tasks', methods=['POST'])
    def create_task():
        try:
            data = request.json
            contract_address = data.get("ca")
            type_id = int(data.get("type_id"))

            # tasks = json.loads(open('data/tasks.json', 'r', encoding='utf-8').read())
            # running_tasks = [tasks[k] for k in tasks.keys() if tasks[k]['status'] != 'stopped']
            # if len(running_tasks) > 0:
            #     return jsonify({"error": "Not support multiple tasks, please wait."}), 404

            # 查找策略
            strategy = next((s for s in strategy_manager.strategies if type_id in s["selectedTypes"] and s["isActive"]), None)

            if not strategy:
                log_manager.add_log("ERROR", f"创建任务失败: 没有找到符合条件的开启状态的策略模版，类型ID={type_id}")
                return jsonify({"error": "Strategy not found"}), 404
            else:
                strategy_id = strategy["id"]

            # 创建任务
            task = task_manager.create_task(
                strategy_id=strategy_id,
                strategy_name=strategy["name"],
                contract_address=contract_address,
                type_id=type_id
            )

            # 启动任务执行
            executor.start_task(task, strategy)

            return jsonify(task)

        except Exception as e:
            log_manager.add_log("ERROR", f"创建任务失败: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/tasks/<task_id>/stop', methods=['POST'])
    def stop_task(task_id):
        try:
            # 停止任务执行
            executor.stop_task(task_id)

            # 更新存储中的任务状态
            if task_manager.stop_task(task_id):
                return jsonify({"success": True})

            log_manager.add_log("ERROR", f"停止任务失败: 任务不存在 ID={task_id}")
            return jsonify({"error": "Task not found"}), 404

        except Exception as e:
            log_manager.add_log("ERROR", f"停止任务失败: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

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