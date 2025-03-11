# 示例：任务处理函数

# 原代码：
async def handle_task_creation(task_data):
    # 异步处理
    task = await create_task(task_data)
    await task_executor.start_task(task, task_data['strategy'])
    return {"success": True, "task_id": task['id']}

# 修改为：
def handle_task_creation(task_data):
    # 同步处理
    task = create_task(task_data)
    task_executor.start_task(task, task_data['strategy'])
    return {"success": True, "task_id": task['id']} 