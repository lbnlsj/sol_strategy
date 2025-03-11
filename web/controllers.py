# 示例：Web控制器

# 原代码：
@app.route('/tasks/create', methods=['POST'])
async def create_task_endpoint():
    data = await request.json()
    # 异步调用
    result = await task_service.create_task(data)
    return jsonify(result)

# 修改为：
@app.route('/tasks/create', methods=['POST'])
def create_task_endpoint():
    data = request.json
    # 同步调用
    result = task_service.create_task(data)
    return jsonify(result) 