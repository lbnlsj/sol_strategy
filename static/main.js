// 全局变量
let strategyTemplates = [];
let wallets = [];
let types = [];
let editingTemplateIndex = null;
let activeStrategyIndex = null;



// 在文件顶部添加任务状态跟踪变量
let runningTasks = new Map(); // 用于跟踪运行中的任务 {templateName: taskId}








// 修改保存策略模板函数
async function saveStrategyTemplate() {
    const selectedWallets = Array.from(document.querySelectorAll('.wallet-checkbox:checked'))
        .map(checkbox => checkbox.value);

    const selectedTypes = Array.from(document.querySelectorAll('.type-checkbox:checked'))
        .map(checkbox => parseInt(checkbox.value));

    if (selectedTypes.length === 0) {
        showToast('请至少选择一个类型');
        return;
    }

    const template = {
        name: document.getElementById('templateName').value.trim(),
        selectedWallets: selectedWallets,
        selectedTypes: selectedTypes,
        minBuyAmount: parseFloat(document.getElementById('templateMinBuyAmount').value),
        maxBuyAmount: parseFloat(document.getElementById('templateMaxBuyAmount').value),
        speedMode: document.getElementById('templateSpeedMode').value,
        antiSqueeze: document.getElementById('templateAntiSqueeze').value,
        buyPriority: parseFloat(document.getElementById('templateBuyPriority').value),
        sellPriority: parseFloat(document.getElementById('templateSellPriority').value),
        stopPriority: parseFloat(document.getElementById('templateStopPriority').value),
        slippage: parseFloat(document.getElementById('templateSlippage').value),
        trailingStop: parseFloat(document.getElementById('templateTrailingStop').value),
        sellPercent: parseFloat(document.getElementById('templateSellPercent').value),
        stopLevels: collectStopLevels(),
        jitoSettings: {
            enabled: document.getElementById('jitoEnabled').checked,
            fee: parseFloat(document.getElementById('jitoFee').value)
        },
        antiSandwichSettings: {
            enabled: document.getElementById('antiSandwichEnabled').checked,
            fee: parseFloat(document.getElementById('antiSandwichFee').value)
        }
    };

    if (!template.name) {
        showToast('请填写模板名称');
        return;
    }

    if (template.selectedWallets.length === 0) {
        showToast('请至少选择一个钱包');
        return;
    }

    try {
        // 如果是编辑模式，添加策略ID
        if (editingTemplateIndex !== null) {
            template.id = strategyTemplates[editingTemplateIndex].id;
        }

        const response = await fetch('/api/strategies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(template)
        });

        if (!response.ok) {
            throw new Error('保存策略失败');
        }

        const savedStrategy = await response.json();

        if (editingTemplateIndex !== null) {
            // 更新现有策略
            strategyTemplates[editingTemplateIndex] = savedStrategy;
            showToast('策略更新成功');
            addLog('INFO', `更新策略成功: ${template.name}`);
        } else {
            // 添加新策略
            strategyTemplates.push(savedStrategy);
            showToast('策略创建成功');
            addLog('INFO', `创建策略成功: ${template.name}`);
        }

        refreshTemplateList();
        closeStrategyModal();
    } catch (error) {
        showToast(error.message);
        addLog('ERROR', `保存策略失败: ${error.message}`);
    }
}

// 修改删除模板函数
async function deleteTemplate(index, event) {
    event.stopPropagation();

    if (confirm('确定要删除这个策略模板吗？')) {
        const template = strategyTemplates[index];
        try {
            // 如果任务正在运行，先停止任务
            if (runningTasks.has(template.id)) {
                const taskId = runningTasks.get(template.id);
                await fetch(`/api/tasks/${taskId}/stop`, {
                    method: 'POST'
                });
                runningTasks.delete(template.id);
            }

            const response = await fetch(`/api/strategies/${template.id}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('删除策略失败');
            }

            strategyTemplates.splice(index, 1);
            refreshTemplateList();
            showToast('策略已删除');
            addLog('INFO', `删除策略: ${template.name}`);
        } catch (error) {
            showToast(error.message);
            addLog('ERROR', `删除策略失败: ${error.message}`);
        }
    }
}

// 修改任务启停函数
async function toggleTemplateStatus(templateId, index, event) {
    event.stopPropagation();

    try {
        if (runningTasks.has(templateId)) {
            // 停止任务
            const taskId = runningTasks.get(templateId);
            const response = await fetch(`/api/tasks/${taskId}/stop`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('停止任务失败');
            }

            runningTasks.delete(templateId);
            showToast('任务已停止');
            addLog('INFO', `停止任务: ${strategyTemplates[index].name}`);
        } else {
            // 启动新任务
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    strategyId: templateId
                })
            });

            if (!response.ok) {
                throw new Error('启动任务失败');
            }

            const task = await response.json();
            runningTasks.set(templateId, task.id);
            showToast('任务已启动');
            addLog('INFO', `启动任务: ${strategyTemplates[index].name}`);
        }

        refreshTemplateList();
    } catch (error) {
        showToast(error.message);
        addLog('ERROR', error.message);
    }
}

// 修改模板列表刷新函数
function refreshTemplateList() {
    const container = document.getElementById('strategyTemplateList');
    container.innerHTML = '';

    strategyTemplates.forEach((template, index) => {
        const selectedWalletNames = template.selectedWallets
            .map(addr => wallets.find(w => w.address === addr)?.name || '未知钱包')
            .join(', ');

        const selectedTypeInfo = template.selectedTypes
            .map(typeId => {
                const type = types.find(t => t.id === typeId);
                return type ? `[${type.id}] ${type.name}` : '未知类型';
            })
            .join(', ');

        const div = document.createElement('div');
        div.className = 'strategy-card relative border rounded-lg p-4 hover:bg-gray-50';

        // 检查任务是否正在运行
        const isRunning = runningTasks.has(template.id);

        const statusButton = `
            <button 
                onclick="toggleTemplateStatus(${template.id}, ${index}, event)" 
                class="${isRunning ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'} 
                    text-white px-3 py-1 rounded text-sm transition-colors duration-200">
                ${isRunning ? '停止' : '启动'}
            </button>
        `;

        div.innerHTML = `
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold text-gray-900">${template.name}</h3>
                <div class="flex space-x-2">
                    ${statusButton}
                    <button onclick="showEditStrategyModal(${index}, event)" 
                            class="text-blue-500 hover:text-blue-600">编辑</button>
                    <button onclick="deleteTemplate(${index}, event)" 
                            class="text-red-500 hover:text-red-600">删除</button>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 text-sm text-gray-600">
                <div class="col-span-2">选中钱包: ${selectedWalletNames}</div>
                <div class="col-span-2">选中类型: ${selectedTypeInfo}</div>
                <div>买入金额范围: ${template.minBuyAmount} - ${template.maxBuyAmount} SOL</div>
                <div>滑点: ${template.slippage}%</div>
                <div>极速模式: ${template.speedMode === 'fast' ? '开启' : '关闭'}</div>
                <div>防夹模式: ${template.antiSqueeze === 'on' ? '开启' : '关闭'}</div>
                <div>买入优先费: ${template.buyPriority}</div>
                <div>卖出优先费: ${template.sellPriority}</div>
                <div>止损优先费: ${template.stopPriority}</div>
                <div>移动止损: ${template.trailingStop}%</div>
                <div>卖出比例: ${template.sellPercent}%</div>
                <div>Jito费用: ${template.jitoSettings?.enabled ? template.jitoSettings.fee : '未启用'}</div>
                <div>防夹费用: ${template.antiSandwichSettings?.enabled ? template.antiSandwichSettings.fee : '未启用'}</div>
            </div>
        `;
        container.appendChild(div);
    });
}






// 在初始化函数中添加获取运行中任务的逻辑
async function initializeData() {
    try {
        const [walletsResponse, typesResponse, strategiesResponse, tasksResponse] = await Promise.all([
            fetch('/api/wallets'),
            fetch('/api/types'),
            fetch('/api/strategies'),
            fetch('/api/tasks')
        ]);

        wallets = await walletsResponse.json();
        types = await typesResponse.json();
        strategyTemplates = await strategiesResponse.json();

        // 初始化运行中的任务
        const tasks = await tasksResponse.json();
        runningTasks.clear();
        tasks.forEach(task => {
            if (task.templateName) {
                runningTasks.set(task.templateName, task.id);
            }
        });

        // 确保类型ID为数字
        types = types.map(type => ({
            ...type,
            id: parseInt(type.id)
        }));

        // 确保策略中的类型ID为数字
        strategyTemplates = strategyTemplates.map(strategy => ({
            ...strategy,
            selectedTypes: strategy.selectedTypes.map(id => parseInt(id))
        }));

        refreshWalletList();
        refreshTypeList();
        refreshTemplateList();
        refreshLogs();
        addLog('INFO', '系统初始化完成');
    } catch (error) {
        console.error('Error loading data:', error);
        addLog('ERROR', `初始化失败: ${error.message}`);
    }
}






// Add these variables at the top of main.js
let selectedStrategies = new Set();

// Add these functions to main.js
function toggleStrategySelection(index, event) {
    event.stopPropagation();
    if (selectedStrategies.has(index)) {
        selectedStrategies.delete(index);
    } else {
        selectedStrategies.add(index);
    }

    const manageBtn = document.getElementById('manageSelectedBtn');
    manageBtn.classList.toggle('hidden', selectedStrategies.size === 0);

    refreshTemplateList();
}

function manageSelectedStrategies() {
    document.getElementById('managementModal').classList.remove('hidden');
    refreshTasksList();
}

function closeManagementModal() {
    document.getElementById('managementModal').classList.add('hidden');
}

function refreshTasksList() {
    const tasksList = document.getElementById('tasksList');
    tasksList.innerHTML = '';

    runningTasks.forEach((task, taskId) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${task.id}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${task.contractAddress}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${task.startTime}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    运行中
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button onclick="stopTask('${taskId}')" 
                        class="text-red-600 hover:text-red-900">停止</button>
            </td>
        `;
        tasksList.appendChild(row);
    });
}

async function stopTask(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/stop`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('停止任务失败');
        }

        runningTasks.delete(taskId);
        refreshTasksList();
        showToast('任务已停止');
        addLog('INFO', `停止任务: ${taskId}`);
    } catch (error) {
        showToast('停止任务失败');
        addLog('ERROR', `停止任务失败: ${error.message}`);
    }
}


// Add these management functions
function showManagementModal(index, event) {
    if (event) {
        event.stopPropagation();
    }
    document.getElementById('managementModal').classList.remove('hidden');

    // 创建任务的处理函数
    const modalContainer = document.getElementById('managementModal');
    const tasksList = modalContainer.querySelector('#tasksList');

    // 清空当前任务列表
    tasksList.innerHTML = '';

    // 添加创建任务的表单行
    const newTaskRow = document.createElement('tr');
    newTaskRow.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap">新任务</td>
        <td class="px-6 py-4 whitespace-nowrap">
            <input type="text" 
                id="newTaskContract" 
                class="w-full px-3 py-1 border rounded" 
                placeholder="输入合约地址">
        </td>
        <td class="px-6 py-4 whitespace-nowrap">-</td>
        <td class="px-6 py-4 whitespace-nowrap">-</td>
        <td class="px-6 py-4 whitespace-nowrap text-right">
            <button onclick="createNewTask()"
                    class="text-green-600 hover:text-green-900">
                创建
            </button>
        </td>
    `;
    tasksList.appendChild(newTaskRow);

    // 添加现有任务列表
    refreshTasksList();
}

async function createNewTask() {
    const contractAddress = document.getElementById('newTaskContract').value;
    if (!contractAddress) {
        showToast('请输入合约地址');
        return;
    }

    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                contractAddress: contractAddress
            })
        });

        if (!response.ok) {
            throw new Error('创建任务失败');
        }

        const task = await response.json();
        runningTasks.set(task.id, task);

        // 清空输入框
        document.getElementById('newTaskContract').value = '';

        // 刷新任务列表
        refreshTasksList();

        showToast('任务创建成功');
        addLog('INFO', `创建任务成功: ${contractAddress}`);

    } catch (error) {
        showToast('创建任务失败');
        addLog('ERROR', `创建任务失败: ${error.message}`);
    }
}

// Add these variables at the top of main.js


// 设置相关函数
function showSettingsModal() {
    loadSettings();
    document.getElementById('settingsModal').classList.remove('hidden');
}

function closeSettingsModal() {
    document.getElementById('settingsModal').classList.add('hidden');
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (!response.ok) {
            throw new Error('加载设置失败');
        }
        const settings = await response.json();

        document.getElementById('settingsRpcUrl').value = settings.rpcUrl || '';
        document.getElementById('settingsJitoRpcUrl').value = settings.jitoRpcUrl || '';
        document.getElementById('settingsWsUrl').value = settings.wsUrl || '';
        document.getElementById('settingsWsPort').value = settings.wsPort || '';
    } catch (error) {
        console.error('Error loading settings:', error);
        showToast('加载设置失败');
        addLog('ERROR', '加载设置失败');
    }
}

async function saveSettings() {
    const settings = {
        rpcUrl: document.getElementById('settingsRpcUrl').value.trim(),
        jitoRpcUrl: document.getElementById('settingsJitoRpcUrl').value.trim(),
        wsUrl: document.getElementById('settingsWsUrl').value.trim(),
        wsPort: parseInt(document.getElementById('settingsWsPort').value) || 8900
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });

        if (!response.ok) {
            throw new Error('保存设置失败');
        }

        closeSettingsModal();
        showToast('设置保存成功');
        addLog('INFO', '保存设置成功');
    } catch (error) {
        console.error('Error saving settings:', error);
        showToast('保存设置失败');
        addLog('ERROR', '保存设置失败');
    }
}

// 钱包管理功能
function showWalletModal() {
    document.getElementById('walletModal').classList.remove('hidden');
}

function closeWalletModal() {
    document.getElementById('walletModal').classList.add('hidden');
    document.getElementById('walletName').value = '';
    document.getElementById('walletPrivateKey').value = '';
}

async function addWallet() {
    const name = document.getElementById('walletName').value;
    let privateKey = document.getElementById('walletPrivateKey').value.trim();

    if (!name || !privateKey) {
        alert('请填写钱包名称和私钥');
        return;
    }

    try {
        const response = await fetch('/api/wallets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                privateKey: privateKey
            })
        });

        if (!response.ok) {
            throw new Error('添加钱包失败');
        }

        const wallet = await response.json();
        wallets.push(wallet);
        refreshWalletList();
        closeWalletModal();
        showToast('钱包添加成功');
        addLog('INFO', `添加钱包成功: ${name}`);
    } catch (error) {
        alert(error.message);
        addLog('ERROR', `添加钱包失败: ${error.message}`);
    }
}

async function deleteWallet(index, event) {
    event.stopPropagation();

    if (confirm('确定要删除这个钱包吗？')) {
        const wallet = wallets[index];
        try {
            const response = await fetch(`/api/wallets/${wallet.address}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('删除钱包失败');
            }

            wallets.splice(index, 1);
            refreshWalletList();
            refreshTemplateList();
            showToast('钱包已删除');
            addLog('INFO', `删除钱包成功: ${wallet.name}`);
        } catch (error) {
            alert(error.message);
            addLog('ERROR', `删除钱包失败: ${error.message}`);
        }
    }
}

function refreshWalletList() {
    const container = document.getElementById('walletList');
    container.innerHTML = '';

    wallets.forEach((wallet, index) => {
        const div = document.createElement('div');
        div.className = 'wallet-item';
        div.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="font-semibold">${wallet.name}</h3>
                    <p class="text-sm text-gray-500">${wallet.address.substring(0, 8)}...${wallet.address.substring(36)}</p>
                </div>
                <button onclick="deleteWallet(${index}, event)" 
                        class="text-red-500 hover:text-red-600 transition-colors duration-200">
                    删除
                </button>
            </div>
        `;
        container.appendChild(div);
    });

    updateWalletSelection();
}

// 类型管理功能
function showTypeModal() {
    document.getElementById('typeModal').classList.remove('hidden');
}

function closeTypeModal() {
    document.getElementById('typeModal').classList.add('hidden');
    document.getElementById('typeId').value = '';
    document.getElementById('typeName').value = '';
}

async function addType() {
    const typeId = document.getElementById('typeId').value;
    const name = document.getElementById('typeName').value;

    if (!typeId || !name) {
        alert('请填写类型ID和类型备注');
        return;
    }

    // 验证ID是否为整数
    if (!Number.isInteger(Number(typeId)) || Number(typeId) <= 0) {
        alert('类型ID必须为正整数');
        return;
    }

    try {
        const response = await fetch('/api/types', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: parseInt(typeId),
                name: name
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '添加类型失败');
        }

        const type = await response.json();
        types.push(type);
        refreshTypeList();
        closeTypeModal();
        showToast('类型添加成功');
        addLog('INFO', `添加类型成功: ID=${typeId}, 备注=${name}`);
    } catch (error) {
        alert(error.message);
        addLog('ERROR', `添加类型失败: ${error.message}`);
    }
}

async function deleteType(typeId, event) {
    event.stopPropagation();

    if (confirm('确定要删除这个类型吗？')) {
        try {
            const response = await fetch(`/api/types/${typeId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('删除类型失败');
            }

            types = types.filter(t => t.id !== typeId);

            strategyTemplates.forEach(strategy => {
                strategy.selectedTypes = strategy.selectedTypes.filter(id => id !== typeId);
            });

            refreshTypeList();
            refreshTemplateList();
            showToast('类型已删除');
            addLog('INFO', `删除类型成功: ID=${typeId}`);
        } catch (error) {
            alert(error.message);
            addLog('ERROR', `删除类型失败: ${error.message}`);
        }
    }
}

function refreshTypeList() {
    const container = document.getElementById('typeList');
    container.innerHTML = '';

    const sortedTypes = [...types].sort((a, b) => a.id - b.id);

    sortedTypes.forEach((type) => {
        const div = document.createElement('div');
        div.className = 'wallet-item';
        div.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <div class="flex items-center gap-2">
                        <span class="font-semibold text-blue-600">ID: ${type.id}</span>
                        <span class="text-gray-400">|</span>
                        <span class="text-gray-900">${type.name}</span>
                    </div>
                </div>
                <button onclick="deleteType(${type.id}, event)" 
                        class="text-red-500 hover:text-red-600 transition-colors duration-200">
                    删除
                </button>
            </div>
        `;
        container.appendChild(div);
    });

    updateTypeSelection();
}

function updateTypeSelection() {
    const container = document.getElementById('typeSelection');
    if (!container) return;

    const sortedTypes = [...types].sort((a, b) => a.id - b.id);

    container.innerHTML = sortedTypes.map(type => `
        <div class="flex items-center space-x-2 py-1">
            <input type="checkbox" 
                id="type-${type.id}" 
                value="${type.id}"
                class="type-checkbox"
                ${editingTemplateIndex !== null &&
    strategyTemplates[editingTemplateIndex].selectedTypes.includes(type.id) ? 'checked' : ''}>
            <label for="type-${type.id}" class="text-sm">
                <span class="font-medium text-blue-600">ID: ${type.id}</span>
                <span class="text-gray-400 mx-1">|</span>
                <span class="text-gray-900">${type.name}</span>
            </label>
        </div>
    `).join('');
}

function updateWalletSelection() {
    const container = document.getElementById('walletSelection');
    if (!container) return;

    container.innerHTML = wallets.map(wallet => `
        <div class="flex items-center space-x-2 py-1">
            <input type="checkbox" 
                id="wallet-${wallet.address}" 
                value="${wallet.address}"
                class="wallet-checkbox"
                ${editingTemplateIndex !== null &&
    strategyTemplates[editingTemplateIndex].selectedWallets.includes(wallet.address) ? 'checked' : ''}>
            <label for="wallet-${wallet.address}" class="text-sm">
                ${wallet.name} <span class="text-gray-500">(${wallet.address})</span>
            </label>
        </div>
    `).join('');
}

// 策略模板管理
function clearModalInputs() {
    document.getElementById('templateName').value = '';
    document.getElementById('templateMinBuyAmount').value = '0.3';
    document.getElementById('templateMaxBuyAmount').value = '0.5';
    document.getElementById('templateSpeedMode').value = 'normal';
    document.getElementById('templateAntiSqueeze').value = 'off';
    document.getElementById('templateBuyPriority').value = '0.003';
    document.getElementById('templateSellPriority').value = '0.003';
    document.getElementById('templateStopPriority').value = '0.003';
    document.getElementById('templateSlippage').value = '0.25';
    document.getElementById('templateTrailingStop').value = '50';
    document.getElementById('templateSellPercent').value = '100';
    document.getElementById('stopLevelsList').innerHTML = '';

    // 清除钱包和类型选择
    document.querySelectorAll('.wallet-checkbox').forEach(checkbox => checkbox.checked = false);
    document.querySelectorAll('.type-checkbox').forEach(checkbox => checkbox.checked = false);

    // 清除Jito设置
    document.getElementById('jitoEnabled').checked = false;
    document.getElementById('jitoFee').value = '0.0001';

    // 清除防夹设置
    document.getElementById('antiSandwichEnabled').checked = false;
    document.getElementById('antiSandwichFee').value = '0.0001';
}

function fillModalWithTemplate(template) {
    document.getElementById('templateName').value = template.name;
    document.getElementById('templateMinBuyAmount').value = template.minBuyAmount;
    document.getElementById('templateMaxBuyAmount').value = template.maxBuyAmount;
    document.getElementById('templateSpeedMode').value = template.speedMode;
    document.getElementById('templateAntiSqueeze').value = template.antiSqueeze;
    document.getElementById('templateBuyPriority').value = template.buyPriority;
    document.getElementById('templateSellPriority').value = template.sellPriority;
    document.getElementById('templateStopPriority').value = template.stopPriority;
    document.getElementById('templateSlippage').value = template.slippage;
    document.getElementById('templateTrailingStop').value = template.trailingStop;
    document.getElementById('templateSellPercent').value = template.sellPercent;

    document.getElementById('stopLevelsList').innerHTML = '';
    if (template.stopLevels) {
        template.stopLevels.forEach(level => {
            addStopLevel(level.increase, level.sell, level.position);
        });
    }

    // 填充Jito和防夹设置
    if (template.jitoSettings) {
        document.getElementById('jitoEnabled').checked = template.jitoSettings.enabled;
        document.getElementById('jitoFee').value = template.jitoSettings.fee;
    }
    if (template.antiSandwichSettings) {
        document.getElementById('antiSandwichEnabled').checked = template.antiSandwichSettings.enabled;
        document.getElementById('antiSandwichFee').value = template.antiSandwichSettings.fee;
    }
}


function showNewStrategyModal() {
    editingTemplateIndex = null;
    document.getElementById('modalTitle').textContent = '新建策略模板';
    clearModalInputs();
    updateWalletSelection();
    updateTypeSelection();
    addStopLevel();
    document.getElementById('strategyModal').classList.remove('hidden');
}

function showEditStrategyModal(index, event) {
    event.stopPropagation();
    editingTemplateIndex = index;
    const template = strategyTemplates[index];
    document.getElementById('modalTitle').textContent = '编辑策略模板';
    fillModalWithTemplate(template);
    updateWalletSelection();
    updateTypeSelection();

    if (!template.stopLevels || template.stopLevels.length === 0) {
        addStopLevel();
    }
    document.getElementById('strategyModal').classList.remove('hidden');
}

function closeStrategyModal() {
    document.getElementById('strategyModal').classList.add('hidden');
}

// 策略选择逻辑
async function selectStrategy(index) {
    try {
        const template = strategyTemplates[index];
        const response = await fetch('/api/active-strategy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                strategyName: template.name
            })
        });

        if (!response.ok) {
            throw new Error('设置活动策略失败');
        }

        activeStrategyIndex = index;
        refreshTemplateList();
        showToast(`已切换至策略: ${template.name}`);
        addLog('INFO', `切换策略: ${template.name}`);
    } catch (error) {
        console.error('Error selecting strategy:', error);
        showToast('切换策略失败');
        addLog('ERROR', `切换策略失败: ${error.message}`);
    }
}

// 止盈止损相关函数
function addStopLevel(increase = '', sell = '', position = '') {
    const container = document.createElement('div');
    container.className = 'flex gap-4 items-center';
    container.innerHTML = `
        <div class="flex-1">
            <input type="number" class="w-full px-3 py-2 border rounded-md stop-increase" 
                value="${increase}" placeholder="涨幅(%)" step="0.1"
                min="-100" max="1000">
        </div>
        <div class="flex-1">
            <input type="number" class="w-full px-3 py-2 border rounded-md stop-sell" 
                value="${sell}" placeholder="卖出比例(%)" step="0.1"
                min="0" max="100"
                onchange="validatePercentageInput(this); updatePosition(this)" 
                oninput="validatePercentageInput(this); updatePosition(this)">
        </div>
        <div class="flex-1">
            <input type="number" class="w-full px-3 py-2 border rounded-md stop-position" 
                value="${position}" placeholder="总仓位比例(%)" step="0.1"
                min="0" max="100"
                onchange="validatePercentageInput(this); updateSell(this)" 
                oninput="validatePercentageInput(this); updateSell(this)">
        </div>
        <button onclick="this.parentElement.remove()" class="text-red-500">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
        </button>
    `;
    document.getElementById('stopLevelsList').appendChild(container);

    if (sell || position) {
        const sellInput = container.querySelector('.stop-sell');
        updatePosition(sellInput);
    }
}

function validatePercentageInput(input) {
    let value = parseFloat(input.value);
    if (isNaN(value)) {
        value = 0;
    } else if (value < 0) {
        value = 0;
    } else if (value > 100) {
        value = 100;
    }
    input.value = value;
    return value;
}

function getPreviousTotalSellPercentage(currentRow) {
    let total = 0;
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));
    const currentIndex = allRows.indexOf(currentRow);

    for (let i = 0; i < currentIndex; i++) {
        const sellValue = parseFloat(allRows[i].querySelector('.stop-position').value) || 0;
        total += sellValue / 100;
    }

    return total;
}

function updatePosition(sellInput) {
    const currentRow = sellInput.closest('div').parentElement;
    const positionInput = currentRow.querySelector('.stop-position');
    const sellPercentage = parseFloat(sellInput.value) || 0;
    const previousTotalSell = getPreviousTotalSellPercentage(currentRow);
    const remainingPosition = 1 - previousTotalSell;
    const positionPercentage = (sellPercentage / 100) * remainingPosition * 100;
    positionInput.value = positionPercentage.toFixed(4);
    updateSubsequentPositions(currentRow);
}

function updateSell(positionInput) {
    const currentRow = positionInput.closest('div').parentElement;
    const sellInput = currentRow.querySelector('.stop-sell');
    const positionPercentage = parseFloat(positionInput.value) || 0;
    const previousTotalSell = getPreviousTotalSellPercentage(currentRow);
    const remainingPosition = 1 - previousTotalSell;
    const sellPercentage = (positionPercentage / 100) / remainingPosition * 100;
    sellInput.value = sellPercentage.toFixed(2);
    updateSubsequentPositions(currentRow);
}

function updateSubsequentPositions(currentRow) {
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));
    const currentIndex = allRows.indexOf(currentRow);

    for (let i = currentIndex + 1; i < allRows.length; i++) {
        const row = allRows[i];
        const sellInput = row.querySelector('.stop-sell');
        updatePosition(sellInput);
    }
}

function collectStopLevels() {
    const levels = [];
    document.querySelectorAll('#stopLevelsList > div').forEach(div => {
        const increase = div.querySelector('.stop-increase').value;
        const sell = div.querySelector('.stop-sell').value;
        const position = div.querySelector('.stop-position').value;
        if (increase && sell && position) {
            levels.push({
                increase: parseFloat(increase),
                sell: parseFloat(sell),
                position: parseFloat(position)
            });
        }
    });
    return levels;
}

// 日志管理
let logQueue = [];
let isLogging = false;

async function addLog(level, message) {
    logQueue.push({level, message});
    if (!isLogging) {
        await processLogQueue();
    }
}

async function processLogQueue() {
    if (logQueue.length === 0) {
        isLogging = false;
        return;
    }

    isLogging = true;
    const {level, message} = logQueue.shift();

    try {
        const response = await fetch('/api/logs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                level: level,
                message: message
            })
        });

        if (response.ok) {
            refreshLogs();
        }
    } catch (error) {
        console.error('Error adding log:', error);
    }

    setTimeout(() => processLogQueue(), 100);
}

let lastLogTimestamp = null;

async function refreshLogs() {
    try {
        const response = await fetch('/api/logs');
        const logs = await response.json();

        const logOutput = document.getElementById('logOutput');
        logOutput.innerHTML = logs.map(log => `
            <div class="log-entry py-1 ${log.timestamp !== lastLogTimestamp ? 'border-tborder-gray-200' : ''}">
                <span class="text-gray-500">${log.timestamp}</span>
                <span class="px-2 rounded ${getLogLevelClass(log.level)}">${log.level}</span>
                <span class="text-gray-900">${log.message}</span>
            </div>
        `).join('');

        if (logs.length > 0) {
            lastLogTimestamp = logs[logs.length - 1].timestamp;
        }

        logOutput.scrollTop = logOutput.scrollHeight;
    } catch (error) {
        console.error('Error refreshing logs:', error);
    }
}

function getLogLevelClass(level) {
    switch (level.toUpperCase()) {
        case 'INFO':
            return 'bg-blue-100 text-blue-800';
        case 'WARNING':
            return 'bg-yellow-100 text-yellow-800';
        case 'ERROR':
            return 'bg-red-100 text-red-800';
        default:
            return 'bg-gray-100 text-gray-800';
    }
}

async function clearLogs() {
    if (confirm('确定要清除所有日志吗？')) {
        try {
            logQueue = [];
            isLogging = false;
            document.getElementById('logOutput').innerHTML = '';
            addLog('INFO', '日志已清除');
        } catch (error) {
            console.error('Error clearing logs:', error);
            showToast('清除日志失败');
        }
    }
}

// Toast消息
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-gray-800 text-white px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300 translate-y-0 opacity-100 z-50';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('translate-y-2', 'opacity-0');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 2000);
}


// 页面加载初始化
document.addEventListener('DOMContentLoaded', () => {
    initializeData();
});