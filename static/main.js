// 存储策略模板和钱包群组的数组
let strategyTemplates = [];
let walletGroups = [];
let editingTemplateIndex = null;

// 初始化示例数据
function initializeData() {
    // 添加示例钱包群组
    walletGroups.push({
        name: "默认群组",
        wallets: []
    });

    // 添加示例策略模板
    strategyTemplates.push({
        name: "默认策略",
        walletGroup: "默认群组",
        buyAmount: 0.5,
        buyPriority: 0.003,
        sellPriority: 0.003,
        stopPriority: 0.003,
        slippage: 0.25,
        trailingStop: 50,
        sellPercent: 100,
        stopLevels: [
            {increase: -30, sell: 100},
            {increase: 100, sell: 10},
            {increase: 200, sell: 20},
            {increase: 300, sell: 30},
            {increase: 500, sell: 50}
        ]
    });

    refreshWalletGroups();
    refreshTemplateList();
}

// 钱包群组管理功能
function showWalletGroupModal() {
    document.getElementById('walletGroupModal').classList.remove('hidden');
}

function closeWalletGroupModal() {
    document.getElementById('walletGroupModal').classList.add('hidden');
}

function createWalletGroup() {
    const name = document.getElementById('groupName').value;
    const walletKeys = document.getElementById('walletAddresses').value
        .split('\n')
        .filter(key => key.trim() !== '');

    if (!name) {
        alert('请输入群组名称');
        return;
    }

    walletGroups.push({
        name: name,
        wallets: walletKeys
    });

    refreshWalletGroups();
    closeWalletGroupModal();
}

function deleteWalletGroup(index) {
    if (confirm('确定要删除这个钱包群组吗？')) {
        walletGroups.splice(index, 1);
        refreshWalletGroups();
    }
}

function refreshWalletGroups() {
    // 更新钱包群组显示列表
    const container = document.getElementById('walletGroupsDisplay');
    container.innerHTML = '';

    walletGroups.forEach((group, index) => {
        const div = document.createElement('div');
        div.className = 'border rounded-lg p-4';
        div.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <h3 class="font-semibold">${group.name}</h3>
                <button onclick="deleteWalletGroup(${index})" class="text-red-500 hover:text-red-600">删除</button>
            </div>
            <div class="text-sm text-gray-600">
                钱包数量: ${group.wallets.length}
            </div>
        `;
        container.appendChild(div);
    });

    // 更新策略模板中的钱包群组选择下拉框
    const select = document.getElementById('walletGroup');
    if (select) {
        select.innerHTML = walletGroups.map(group =>
            `<option value="${group.name}">${group.name}</option>`
        ).join('');
    }
}

// 策略模板管理功能
function showNewStrategyModal() {
    editingTemplateIndex = null;
    document.getElementById('modalTitle').textContent = '新建策略模板';
    clearModalInputs();
    document.getElementById('strategyModal').classList.remove('hidden');
}

function showEditStrategyModal(index) {
    editingTemplateIndex = index;
    const template = strategyTemplates[index];
    document.getElementById('modalTitle').textContent = '编辑策略模板';
    fillModalWithTemplate(template);
    document.getElementById('strategyModal').classList.remove('hidden');
}

function clearModalInputs() {
    document.getElementById('templateName').value = '';
    document.getElementById('templateBuyAmount').value = '0.5';
    document.getElementById('templateBuyPriority').value = '0.003';
    document.getElementById('templateSellPriority').value = '0.003';
    document.getElementById('templateStopPriority').value = '0.003';
    document.getElementById('templateSlippage').value = '0.25';
    document.getElementById('templateTrailingStop').value = '50';
    document.getElementById('templateSellPercent').value = '100';
    document.getElementById('stopLevelsList').innerHTML = '';

    // 设置默认钱包群组
    if (walletGroups.length > 0) {
        document.getElementById('walletGroup').value = walletGroups[0].name;
    }
}

function fillModalWithTemplate(template) {
    document.getElementById('templateName').value = template.name;
    document.getElementById('walletGroup').value = template.walletGroup;
    document.getElementById('templateBuyAmount').value = template.buyAmount;
    document.getElementById('templateBuyPriority').value = template.buyPriority;
    document.getElementById('templateSellPriority').value = template.sellPriority;
    document.getElementById('templateStopPriority').value = template.stopPriority;
    document.getElementById('templateSlippage').value = template.slippage;
    document.getElementById('templateTrailingStop').value = template.trailingStop;
    document.getElementById('templateSellPercent').value = template.sellPercent;

    // 重新生成止盈止损级别
    document.getElementById('stopLevelsList').innerHTML = '';
    template.stopLevels.forEach(level => {
        addStopLevelToUI(level.increase, level.sell);
    });
}

function closeStrategyModal() {
    document.getElementById('strategyModal').classList.add('hidden');
}

function addStopLevelToUI(increase = '', sell = '') {
    const container = document.createElement('div');
    container.className = 'flex gap-4 items-center';
    container.innerHTML = `
        <div class="flex-1">
            <input type="number" class="w-full px-3 py-2 border rounded-md stop-increase" value="${increase}" placeholder="涨幅" step="any">
        </div>
        <div class="flex-1">
            <input type="number" class="w-full px-3 py-2 border rounded-md stop-sell" value="${sell}" placeholder="卖出" step="any">
        </div>
        <button onclick="this.parentElement.remove()" class="text-red-500">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
        </button>
    `;
    document.getElementById('stopLevelsList').appendChild(container);
}

function addStopLevel() {
    addStopLevelToUI();
}

function collectStopLevels() {
    const levels = [];
    document.querySelectorAll('#stopLevelsList > div').forEach(div => {
        const increase = div.querySelector('.stop-increase').value;
        const sell = div.querySelector('.stop-sell').value;
        if (increase && sell) {
            levels.push({
                increase: parseFloat(increase),
                sell: parseFloat(sell)
            });
        }
    });
    return levels;
}

function saveStrategyTemplate() {
    const template = {
        name: document.getElementById('templateName').value,
        walletGroup: document.getElementById('walletGroup').value,
        buyAmount: parseFloat(document.getElementById('templateBuyAmount').value),
        buyPriority: parseFloat(document.getElementById('templateBuyPriority').value),
        sellPriority: parseFloat(document.getElementById('templateSellPriority').value),
        stopPriority: parseFloat(document.getElementById('templateStopPriority').value),
        slippage: parseFloat(document.getElementById('templateSlippage').value),
        trailingStop: parseFloat(document.getElementById('templateTrailingStop').value),
        sellPercent: parseFloat(document.getElementById('templateSellPercent').value),
        stopLevels: collectStopLevels()
    };

    // 验证必填字段
    if (!template.name || !template.walletGroup) {
        alert('请填写模板名称和选择钱包群组');
        return;
    }

    // 验证止盈止损级别
    if (template.stopLevels.length === 0) {
        alert('请至少添加一个止盈止损级别');
        return;
    }

    if (editingTemplateIndex !== null) {
        strategyTemplates[editingTemplateIndex] = template;
    } else {
        strategyTemplates.push(template);
    }

    refreshTemplateList();
    closeStrategyModal();
}

function deleteTemplate(index) {
    if (confirm('确定要删除这个策略模板吗？')) {
        strategyTemplates.splice(index, 1);
        refreshTemplateList();
    }
}

function duplicateTemplate(index) {
    const template = {...strategyTemplates[index]};
    template.name = `${template.name} (复制)`;
    strategyTemplates.push(template);
    refreshTemplateList();
}

function refreshTemplateList() {
    const container = document.getElementById('strategyTemplateList');
    container.innerHTML = '';
    const strategySelect = document.getElementById('strategySelection');
    strategySelect.innerHTML = '';

    strategyTemplates.forEach((template, index) => {
        // 添加到模板列表
        const div = document.createElement('div');
        div.className = 'border rounded-lg p-4';
        div.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <h3 class="font-semibold">${template.name}</h3>
                <div class="space-x-2">
                    <button onclick="showEditStrategyModal(${index})" class="text-blue-500 hover:text-blue-600">编辑</button>
                    <button onclick="duplicateTemplate(${index})" class="text-green-500 hover:text-green-600">复制</button>
                    <button onclick="deleteTemplate(${index})" class="text-red-500 hover:text-red-600">删除</button>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 text-sm text-gray-600">
                <div>钱包群组: ${template.walletGroup}</div>
                <div>买入金额: ${template.buyAmount} SOL</div>
                <div>滑点: ${template.slippage}%</div>
                <div>买入优先费: ${template.buyPriority}</div>
                <div>卖出优先费: ${template.sellPriority}</div>
                <div>止损优先费: ${template.stopPriority}</div>
                <div>移动止损: ${template.trailingStop}%</div>
                <div>卖出比例: ${template.sellPercent}%</div>
            </div>
        `;
        container.appendChild(div);

        // 添加到策略选择下拉框
        const option = document.createElement('option');
        option.value = index;
        option.textContent = template.name;
        strategySelect.appendChild(option);
    });
}

// 交易相关函数
function startTrading() {
    const selectedStrategyIndex = document.getElementById('strategySelection').value;
    if (selectedStrategyIndex === '') {
        alert('请选择一个策略模板');
        return;
    }

    const selectedStrategy = strategyTemplates[selectedStrategyIndex];
    const selectedGroup = walletGroups.find(group => group.name === selectedStrategy.walletGroup);

    if (!selectedGroup || selectedGroup.wallets.length === 0) {
        alert('所选策略的钱包群组中没有钱包');
        return;
    }

    alert(`开始交易
策略: ${selectedStrategy.name}
钱包群组: ${selectedStrategy.walletGroup}
钱包数量: ${selectedGroup.wallets.length}`);
}

function stopTrading() {
    alert('交易已停止');
}

// 页面加载完成后初始化数据
document.addEventListener('DOMContentLoaded', initializeData);