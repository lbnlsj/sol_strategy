# 示例：如果有任务路由文件使用了异步操作

# 原代码可能是这样的：
@app.route('/api/tasks/start', methods=['POST'])
async def start_task():
    data = await request.json()
    task_id = data.get('task_id')
    # 异步调用
    result = await task_executor.start_task(task_id)
    return jsonify({"success": result})

# 修改为：
@app.route('/api/tasks/start', methods=['POST'])
def start_task():
    data = request.json
    task_id = data.get('task_id')
    # 同步调用
    result = task_executor.start_task(task_id)
    return jsonify({"success": result}) 