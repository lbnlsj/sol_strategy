// Global variables
let strategyTemplates = [];
let wallets = [];
let types = [];
let editingTemplateIndex = null;
let activeStrategyIndex = null;
let activeTemplates = new Set();







// 更新任务管理模态框显示函数
async function showManagementModal(templateIndex, event) {
    if (event) event.stopPropagation();

    const template = strategyTemplates[templateIndex];
    const modalContent = document.getElementById('managementModal');
    const tasksList = modalContent.querySelector('#tasksList');

    try {
        const response = await fetch(`/api/tasks?strategyId=${template.id}`);
        if (!response.ok) {
            throw new Error('获取任务列表失败');
        }
        const tasks = await response.json();

        tasksList.innerHTML = tasks.map(task => {
            const isRunning = task.status === 'running';
            const statusClass = isRunning ?
                'bg-green-100 text-green-800' :
                'bg-gray-100 text-gray-800';
            const statusText = isRunning ? '运行中' : '已停止';

            return `
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${task.id}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div class="flex items-center">
                            <span class="truncate max-w-md" title="${task.contractAddress || '-'}">
                                ${task.contractAddress || '-'}
                            </span>
                            ${task.taskType === 'auto' ? 
                                '<span class="ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">自动</span>' 
                                : ''}
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${task.startTime}</td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
                            ${statusText}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        ${isRunning ? 
                            `<button onclick="stopTask('${task.id}', ${templateIndex})" 
                                    class="text-red-600 hover:text-red-900 transition-colors duration-200">
                                停止
                            </button>` : 
                            '<span class="text-gray-400">已停止</span>'}
                    </td>
                </tr>
            `;
        }).join('');

        modalContent.classList.remove('hidden');
    } catch (error) {
        showToast(error.message);
        addLog('ERROR', `加载任务列表失败: ${error.message}`);
    }
}

// 更新停止任务函数
async function stopTask(taskId, templateIndex) {
    if (!confirm('确定要停止此任务吗？停止后将无法重新启动。')) return;

    try {
        const response = await fetch(`/api/tasks/${taskId}/stop`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('停止任务失败');
        }

        showToast('任务已停止');
        addLog('INFO', `停止任务: ${taskId}`);

        // 刷新任务列表显示
        await showManagementModal(templateIndex, null);

        // 刷新主界面的策略列表
        refreshTemplateList();
    } catch (error) {
        showToast('停止任务失败');
        addLog('ERROR', `停止任务失败: ${error.message}`);
    }
}

// 更新任务列表的辅助函数
function formatTaskStatus(status) {
    switch (status) {
        case 'running':
            return {
                text: '运行中',
                class: 'bg-green-100 text-green-800'
            };
        case 'stopped':
            return {
                text: '已停止',
                class: 'bg-gray-100 text-gray-800'
            };
        default:
            return {
                text: '未知状态',
                class: 'bg-yellow-100 text-yellow-800'
            };
    }
}

// 批量停止任务函数
async function stopSelectedTasks(templateIndex) {
    const selectedTasks = Array.from(document.querySelectorAll('.task-checkbox:checked'))
        .map(checkbox => checkbox.value);

    if (selectedTasks.length === 0) {
        showToast('请至少选择一个任务');
        return;
    }

    if (!confirm(`确定要停止选中的 ${selectedTasks.length} 个任务吗？`)) return;

    try {
        const response = await fetch('/api/tasks/batch/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                taskIds: selectedTasks
            })
        });

        if (!response.ok) {
            throw new Error('批量停止任务失败');
        }

        const result = await response.json();

        showToast(`已成功停止 ${result.success.length} 个任务`);
        if (result.failed.length > 0) {
            addLog('WARNING', `${result.failed.length} 个任务停止失败`);
        }

        // 刷新任务列表显示
        await showManagementModal(templateIndex, null);
    } catch (error) {
        showToast('批量停止任务失败');
        addLog('ERROR', `批量停止任务失败: ${error.message}`);
    }
}






// Function to validate percentage input
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

// Calculate total sell percentage from previous rows
function getPreviousTotalSellPercentage(currentRow) {
    let total = 0;
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));
    const currentIndex = allRows.indexOf(currentRow);

    for (let i = 1; i < currentIndex; i++) {
        const sellValue = parseFloat(allRows[i].querySelector('.stop-position').value) || 0;
        total += sellValue / 100;
    }

    return total;
}

// Update position based on sell percentage
function updatePosition(sellInput) {
    const currentRow = sellInput.closest('div').parentElement;
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));
    const currentIndex = allRows.indexOf(currentRow);

    if (currentIndex === 0) return;

    const positionInput = currentRow.querySelector('.stop-position');
    const sellPercentage = parseFloat(sellInput.value) || 0;
    const previousTotalSell = getPreviousTotalSellPercentage(currentRow);
    const remainingPosition = 1 - previousTotalSell;
    const positionPercentage = (sellPercentage / 100) * remainingPosition * 100;
    positionInput.value = positionPercentage.toFixed(4);
    updateSubsequentPositions(currentRow);
}

// Update sell percentage based on position
function updateSell(positionInput) {
    const currentRow = positionInput.closest('div').parentElement;
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));
    const currentIndex = allRows.indexOf(currentRow);

    if (currentIndex === 0) return;

    const sellInput = currentRow.querySelector('.stop-sell');
    const positionPercentage = parseFloat(positionInput.value) || 0;
    const previousTotalSell = getPreviousTotalSellPercentage(currentRow);
    const remainingPosition = 1 - previousTotalSell;
    const sellPercentage = (positionPercentage / 100) / remainingPosition * 100;
    sellInput.value = sellPercentage.toFixed(2);
    updateSubsequentPositions(currentRow);
}

// Update all subsequent positions after a change
function updateSubsequentPositions(currentRow) {
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));
    const currentIndex = allRows.indexOf(currentRow);

    if (currentIndex === 0) return;

    for (let i = currentIndex + 1; i < allRows.length; i++) {
        const row = allRows[i];
        const sellInput = row.querySelector('.stop-sell');
        updatePosition(sellInput);
    }
}

// Add a new stop level row
function addStopLevel(increase = '', sell = '', position = '') {
    const container = document.createElement('div');
    container.className = 'flex gap-4 items-center';
    container.innerHTML = `
        <div class="flex-1">
            <input type="number" class="w-full px-3 py-2 border rounded-md stop-increase" 
                value="${increase}" placeholder="涨幅(%)" step="0.0001"
                min="-100" max="1000">
        </div>
        <div class="flex-1">
            <input type="number" class="w-full px-3 py-2 border rounded-md stop-sell" 
                value="${sell}" placeholder="卖出比例(%)" step="0.0001"
                min="0" max="100"
                onchange="validatePercentageInput(this); updatePosition(this)" 
                oninput="validatePercentageInput(this); updatePosition(this)">
        </div>
        <div class="flex-1">
            <input type="number" class="w-full px-3 py-2 border rounded-md stop-position" 
                value="${position}" placeholder="总仓位比例(%)" step="0.0001"
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

    // Get all rows after adding the new one
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));

    // Only update if this isn't the first row and we have values
    if (allRows.length > 1 && (sell || position)) {
        const sellInput = container.querySelector('.stop-sell');
        updatePosition(sellInput);
    }
}

// Collect all stop levels
function collectStopLevels() {
    const levels = [];
    document.querySelectorAll('#stopLevelsList > div').forEach(div => {
        const increase = div.querySelector('.stop-increase').value;
        const sell = div.querySelector('.stop-sell').value;
        const position = div.querySelector('.stop-position').value;
        if (increase && sell && position) {
            levels.push({
                increase: parseFloat(increase).toFixed(4),
                sell: parseFloat(sell).toFixed(4),
                position: parseFloat(position).toFixed(4)
            });
        }
    });
    return levels;
}

// Strategy template management
async function saveStrategyTemplate() {
    const selectedWallets = Array.from(document.querySelectorAll('.wallet-checkbox:checked'))
        .map(checkbox => checkbox.value);

    const selectedTypes = Array.from(document.querySelectorAll('.type-checkbox:checked'))
        .map(checkbox => parseInt(checkbox.value));

    if (selectedTypes.length === 0) {
        showToast('请至少选择一个类型');
        return;
    }

    // 收集并验证止盈止损设置
    const stopLevels = [];
    const stopRows = document.querySelectorAll('#stopLevelsList > div');
    let totalPosition = 0;

    for (const row of stopRows) {
        const increase = parseFloat(row.querySelector('.stop-increase').value);
        const sell = parseFloat(row.querySelector('.stop-sell').value);
        const position = parseFloat(row.querySelector('.stop-position').value);

        if (isNaN(increase) || isNaN(sell) || isNaN(position)) {
            showToast('请完整填写止盈止损设置');
            return;
        }

        // 验证数值范围
        if (increase < -100 || increase > 1000) {
            showToast('涨幅比例必须在-100%到1000%之间');
            return;
        }
        if (sell < 0 || sell > 100) {
            showToast('卖出比例必须在0%到100%之间');
            return;
        }
        if (position < 0 || position > 100) {
            showToast('仓位比例必须在0%到100%之间');
            return;
        }

        totalPosition += position;

        stopLevels.push({
            increase: increase.toFixed(4),
            sell: sell.toFixed(4),
            position: position.toFixed(4)
        });
    }

    // 验证总仓位不超过100%
    if (totalPosition > 100) {
        showToast('总仓位比例不能超过100%');
        return;
    }

    // 构建完整的策略模板数据
    const template = {
        name: document.getElementById('templateName').value.trim(),
        selectedWallets: selectedWallets,
        selectedTypes: selectedTypes,
        minBuyAmount: parseFloat(document.getElementById('templateMinBuyAmount').value).toFixed(4),
        maxBuyAmount: parseFloat(document.getElementById('templateMaxBuyAmount').value).toFixed(4),
        speedMode: document.getElementById('templateSpeedMode').value,
        antiSqueeze: document.getElementById('templateAntiSqueeze').value,
        buyPriority: parseFloat(document.getElementById('templateBuyPriority').value).toFixed(6),
        sellPriority: parseFloat(document.getElementById('templateSellPriority').value).toFixed(6),
        stopPriority: parseFloat(document.getElementById('templateStopPriority').value).toFixed(6),
        slippage: parseFloat(document.getElementById('templateSlippage').value).toFixed(4),
        trailingStop: parseFloat(document.getElementById('templateTrailingStop').value).toFixed(4),
        sellPercent: parseFloat(document.getElementById('templateSellPercent').value).toFixed(4),
        stopLevels: stopLevels,
        jitoSettings: {
            enabled: document.getElementById('jitoEnabled').checked,
            fee: parseFloat(document.getElementById('jitoFee').value).toFixed(6)
        },
        antiSandwichSettings: {
            enabled: document.getElementById('antiSandwichEnabled').checked,
            fee: parseFloat(document.getElementById('antiSandwichFee').value).toFixed(6)
        }
    };

    // 基本验证
    if (!template.name) {
        showToast('请填写模板名称');
        return;
    }

    if (template.selectedWallets.length === 0) {
        showToast('请至少选择一个钱包');
        return;
    }

    if (stopLevels.length === 0) {
        showToast('请至少添加一个止盈止损设置');
        return;
    }

    // 验证数值有效性
    if (parseFloat(template.minBuyAmount) >= parseFloat(template.maxBuyAmount)) {
        showToast('最小买入金额必须小于最大买入金额');
        return;
    }

    try {
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
            strategyTemplates[editingTemplateIndex] = savedStrategy;
            showToast('策略更新成功');
            addLog('INFO', `更新策略成功: ${template.name}`);
        } else {
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

async function toggleTemplateStatus(templateId, index, event) {
    event.stopPropagation();
    const template = strategyTemplates[index];
    const isActive = activeTemplates.has(templateId);

    try {
        if (isActive) {
            if (!confirm('确认要停用该策略模板吗？停用后将不再自动执行新任务。')) {
                return;
            }

            const response = await fetch(`/api/strategies/${templateId}/deactivate`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('停用策略模板失败');
            }

            activeTemplates.delete(templateId);
            showToast('策略模板已停用');
            addLog('INFO', `停用策略模板: ${template.name}`);
        } else {
            if (!confirm('确认要启用该策略模板吗？启用后将自动执行相关任务。')) {
                return;
            }

            const response = await fetch(`/api/strategies/${templateId}/activate`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('启用策略模板失败');
            }

            activeTemplates.add(templateId);
            showToast('策略模板已启用');
            addLog('INFO', `启用策略模板: ${template.name}`);
        }

        refreshTemplateList();
    } catch (error) {
        showToast(error.message);
        addLog('ERROR', error.message);
    }
}

async function deleteTemplate(index, event) {
    event.stopPropagation();

    if (!confirm('确定要删除这个策略模板吗？')) return;

    const template = strategyTemplates[index];
    try {
        const response = await fetch(`/api/strategies/${template.id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('删除策略失败');
        }

        strategyTemplates.splice(index, 1);
        activeTemplates.delete(template.id);
        refreshTemplateList();
        showToast('策略已删除');
        addLog('INFO', `删除策略: ${template.name}`);
    } catch (error) {
        showToast(error.message);
        addLog('ERROR', `删除策略失败: ${error.message}`);
    }
}

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

        const isActive = activeTemplates.has(template.id);
        const statusButton = `
            <button 
                onclick="toggleTemplateStatus(${template.id}, ${index}, event)" 
                class="${isActive ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'} 
                    text-white px-3 py-1 rounded text-sm transition-colors duration-200">
                ${isActive ? '停用' : '启用'}
            </button>
        `;

        div.innerHTML = `
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold text-gray-900">${template.name}</h3>
                <div class="flex space-x-2">
                    ${statusButton}
                    <button onclick="showEditStrategyModal(${index}, event)" 
                            class="text-blue-500 hover:text-blue-600">编辑</button>
                    <button onclick="showManagementModal(${index}, event)" 
                            class="text-purple-500 hover:text-purple-600">管理</button>
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
                <div class="col-span-2 mt-2">
                    <span class="font-medium">止盈止损设置:</span>
                    <div class="ml-4">
                        ${template.stopLevels?.map(level =>
            `<div>涨幅: ${level.increase}% | 卖出: ${level.sell}% | 仓位: ${level.position}%</div>`
        ).join('') || '未设置'}
                    </div>
                </div>
            </div>
        `;
        container.appendChild(div);
    });
}


function closeManagementModal() {
    document.getElementById('managementModal').classList.add('hidden');
}

// Settings Management
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
        showToast('保存设置失败');
        addLog('ERROR', '保存设置失败');
    }
}

// Wallet Management
function showWalletModal() {
    document.getElementById('walletModal').classList.remove('hidden');
    document.getElementById('walletName').value = '';
    document.getElementById('walletPrivateKey').value = '';
}

function closeWalletModal() {
    document.getElementById('walletModal').classList.add('hidden');
}

async function addWallet() {
    const name = document.getElementById('walletName').value.trim();
    const privateKey = document.getElementById('walletPrivateKey').value.trim();

    if (!name || !privateKey) {
        showToast('请填写钱包名称和私钥');
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
        showToast(error.message);
        addLog('ERROR', `添加钱包失败: ${error.message}`);
    }
}

async function deleteWallet(address, event) {
    event.stopPropagation();

    if (!confirm('确定要删除这个钱包吗？')) return;

    try {
        const response = await fetch(`/api/wallets/${address}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('删除钱包失败');
        }

        wallets = wallets.filter(w => w.address !== address);
        refreshWalletList();
        refreshTemplateList();
        showToast('钱包已删除');
        addLog('INFO', `删除钱包成功: ${address}`);
    } catch (error) {
        showToast(error.message);
        addLog('ERROR', `删除钱包失败: ${error.message}`);
    }
}

function refreshWalletList() {
    const container = document.getElementById('walletList');
    if (!container) return;

    container.innerHTML = wallets.map((wallet, index) => `
        <div class="wallet-item">
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="font-semibold">${wallet.name}</h3>
                    <p class="text-sm text-gray-500">
                        ${wallet.address.substring(0, 8)}...${wallet.address.substring(36)}
                    </p>
                </div>
                <button onclick="deleteWallet('${wallet.address}', event)" 
                        class="text-red-500 hover:text-red-600 transition-colors duration-200">
                    删除
                </button>
            </div>
        </div>
    `).join('');

    updateWalletSelection();
}

// Type Management
function showTypeModal() {
    document.getElementById('typeModal').classList.remove('hidden');
    document.getElementById('typeId').value = '';
    document.getElementById('typeName').value = '';
}

function closeTypeModal() {
    document.getElementById('typeModal').classList.add('hidden');
}

async function addType() {
    const typeId = document.getElementById('typeId').value;
    const name = document.getElementById('typeName').value.trim();

    if (!typeId || !name) {
        showToast('请填写类型ID和类型备注');
        return;
    }

    if (!Number.isInteger(Number(typeId)) || Number(typeId) <= 0) {
        showToast('类型ID必须为正整数');
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
        updateTypeSelection();
        closeTypeModal();
        showToast('类型添加成功');
        addLog('INFO', `添加类型成功: ID=${typeId}, 备注=${name}`);
    } catch (error) {
        showToast(error.message);
        addLog('ERROR', `添加类型失败: ${error.message}`);
    }
}

async function deleteType(typeId, event) {
    event.stopPropagation();

    if (!confirm('确定要删除这个类型吗？')) return;

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
        showToast(error.message);
        addLog('ERROR', `删除类型失败: ${error.message}`);
    }
}

function refreshTypeList() {
    const container = document.getElementById('typeList');
    if (!container) return;

    const sortedTypes = [...types].sort((a, b) => a.id - b.id);

    container.innerHTML = sortedTypes.map(type => `
        <div class="wallet-item">
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
        </div>
    `).join('');

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
                ${wallet.name} 
                <span class="text-gray-500">(${wallet.address.substring(0, 8)}...${wallet.address.substring(36)})</span>
            </label>
        </div>
    `).join('');
}

function clearModalInputs() {
    document.getElementById('templateName').value = '';
    document.getElementById('templateMinBuyAmount').value = '0.3000';
    document.getElementById('templateMaxBuyAmount').value = '0.5000';
    document.getElementById('templateSpeedMode').value = 'normal';
    document.getElementById('templateAntiSqueeze').value = 'off';
    document.getElementById('templateBuyPriority').value = '0.003000';
    document.getElementById('templateSellPriority').value = '0.003000';
    document.getElementById('templateStopPriority').value = '0.003000';
    document.getElementById('templateSlippage').value = '0.2500';
    document.getElementById('templateTrailingStop').value = '50.0000';
    document.getElementById('templateSellPercent').value = '100.0000';
    document.getElementById('stopLevelsList').innerHTML = '';

    document.querySelectorAll('.wallet-checkbox').forEach(checkbox => checkbox.checked = false);
    document.querySelectorAll('.type-checkbox').forEach(checkbox => checkbox.checked = false);

    document.getElementById('jitoEnabled').checked = false;
    document.getElementById('jitoFee').value = '0.000100';
    document.getElementById('antiSandwichEnabled').checked = false;
    document.getElementById('antiSandwichFee').value = '0.000100';
}

function fillModalWithTemplate(template) {
    document.getElementById('templateName').value = template.name;
    document.getElementById('templateMinBuyAmount').value = parseFloat(template.minBuyAmount).toFixed(4);
    document.getElementById('templateMaxBuyAmount').value = parseFloat(template.maxBuyAmount).toFixed(4);
    document.getElementById('templateSpeedMode').value = template.speedMode;
    document.getElementById('templateAntiSqueeze').value = template.antiSqueeze;
    document.getElementById('templateBuyPriority').value = parseFloat(template.buyPriority).toFixed(6);
    document.getElementById('templateSellPriority').value = parseFloat(template.sellPriority).toFixed(6);
    document.getElementById('templateStopPriority').value = parseFloat(template.stopPriority).toFixed(6);
    document.getElementById('templateSlippage').value = parseFloat(template.slippage).toFixed(4);
    document.getElementById('templateTrailingStop').value = parseFloat(template.trailingStop).toFixed(4);
    document.getElementById('templateSellPercent').value = parseFloat(template.sellPercent).toFixed(4);

    document.getElementById('stopLevelsList').innerHTML = '';
    if (template.stopLevels && template.stopLevels.length > 0) {
        template.stopLevels.forEach(level => {
            addStopLevel(
                parseFloat(level.increase).toFixed(4),
                parseFloat(level.sell).toFixed(4),
                parseFloat(level.position).toFixed(4)
            );
        });
    } else {
        addStopLevel();
    }

    if (template.jitoSettings) {
        document.getElementById('jitoEnabled').checked = template.jitoSettings.enabled;
        document.getElementById('jitoFee').value = parseFloat(template.jitoSettings.fee).toFixed(6);
    }

    if (template.antiSandwichSettings) {
        document.getElementById('antiSandwichEnabled').checked = template.antiSandwichSettings.enabled;
        document.getElementById('antiSandwichFee').value = parseFloat(template.antiSandwichSettings.fee).toFixed(6);
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
    document.getElementById('modalTitle').textContent = '编辑策略模板';
    fillModalWithTemplate(strategyTemplates[index]);
    updateWalletSelection();
    updateTypeSelection();
    document.getElementById('strategyModal').classList.remove('hidden');
}

function closeStrategyModal() {
    document.getElementById('strategyModal').classList.add('hidden');
    editingTemplateIndex = null;
}

// Log Management
let logQueue = [];
let isLogging = false;
let lastLogTimestamp = null;

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
            await refreshLogs();
        }
    } catch (error) {
        console.error('Error adding log:', error);
    }

    setTimeout(() => processLogQueue(), 100);
}

async function refreshLogs() {
    try {
        const response = await fetch('/api/logs');
        const logs = await response.json();

        const logOutput = document.getElementById('logOutput');
        logOutput.innerHTML = logs.map(log => `
            <div class="log-entry py-1 ${log.timestamp !== lastLogTimestamp ? 'border-t border-gray-200' : ''}">
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

// Toast Messages
function showToast(message, duration = 2000) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-gray-800 text-white px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300 translate-y-0 opacity-100 z-50';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('translate-y-2', 'opacity-0');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, duration);
}

// Initialization
async function initializeData() {
    try {
        const [walletsResponse, typesResponse, strategiesResponse, statusResponse] =
            await Promise.all([
                fetch('/api/wallets'),
                fetch('/api/types'),
                fetch('/api/strategies'),
                fetch('/api/strategies/status')
            ]);

        wallets = await walletsResponse.json();
        types = await typesResponse.json();
        strategyTemplates = await strategiesResponse.json();
        const status = await statusResponse.json();
        activeTemplates = new Set(status.activeTemplates);

        // Ensure type IDs are numbers
        types = types.map(type => ({
            ...type,
            id: parseInt(type.id)
        }));

        // Ensure strategy type IDs are numbers
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

// Batch Operation Functions
async function batchActivateStrategies(strategyIds) {
    try {
        const response = await fetch('/api/strategies/batch/activate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({strategyIds})
        });

        if (!response.ok) {
            throw new Error('批量激活策略失败');
        }

        const result = await response.json();
        return result;
    } catch (error) {
        throw error;
    }
}

async function batchDeactivateStrategies(strategyIds) {
    try {
        const response = await fetch('/api/strategies/batch/deactivate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({strategyIds})
        });

        if (!response.ok) {
            throw new Error('批量停用策略失败');
        }

        const result = await response.json();
        return result;
    } catch (error) {
        throw error;
    }
}

async function batchStopTasks(taskIds) {
    try {
        const response = await fetch('/api/tasks/batch/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({taskIds})
        });

        if (!response.ok) {
            throw new Error('批量停止任务失败');
        }

        const result = await response.json();
        return result;
    } catch (error) {
        throw error;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeData();

    // Add auto-refresh for logs
    setInterval(refreshLogs, 5000);
});