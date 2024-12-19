// 存储策略模板和钱包的数组
let strategyTemplates = [];
let wallets = [];
let editingTemplateIndex = null;

// 初始化示例数据
function initializeData() {
    // 添加示例钱包
    wallets.push({
        name: "示例钱包",
        address: "12345...abcde",
        privateKey: "example_private_key"
    });

    // 添加示例策略模板
    strategyTemplates.push({
        name: "默认策略",
        selectedWallets: ["12345...abcde"],
        minBuyAmount: 0.3,
        maxBuyAmount: 0.5,
        speedMode: "normal",
        antiSqueeze: "off",
        buyPriority: 0.003,
        sellPriority: 0.003,
        stopPriority: 0.003,
        slippage: 0.25,
        trailingStop: 50,
        sellPercent: 100,
        stopLevels: [
            {increase: -30, sell: 100, position: 100},
            {increase: 100, sell: 10, position: 9},
            {increase: 200, sell: 20, position: 16.2},
            {increase: 300, sell: 30, position: 21.87},
            {increase: 500, sell: 50, position: 32.81}
        ]
    });

    refreshWalletList();
    refreshTemplateList();
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

function addWallet() {
    const name = document.getElementById('walletName').value;
    const privateKey = document.getElementById('walletPrivateKey').value;

    if (!name || !privateKey) {
        alert('请填写钱包名称和私钥');
        return;
    }

    // 这里应该添加私钥验证逻辑
    const address = `${privateKey.substring(0, 5)}...${privateKey.substring(privateKey.length - 5)}`;

    wallets.push({
        name: name,
        address: address,
        privateKey: privateKey
    });

    refreshWalletList();
    closeWalletModal();
}

function deleteWallet(index) {
    if (confirm('确定要删除这个钱包吗？')) {
        const deletedWallet = wallets[index];
        wallets.splice(index, 1);

        // 从所有策略中移除被删除的钱包
        strategyTemplates.forEach(template => {
            template.selectedWallets = template.selectedWallets.filter(addr => addr !== deletedWallet.address);
        });

        refreshWalletList();
        refreshTemplateList();
    }
}

function refreshWalletList() {
    const container = document.getElementById('walletList');
    container.innerHTML = '';

    wallets.forEach((wallet, index) => {
        const div = document.createElement('div');
        div.className = 'border rounded-lg p-4';
        div.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="font-semibold">${wallet.name} <span class="text-gray-500">(${wallet.address})</span></h3>
                </div>
                <button onclick="deleteWallet(${index})" class="text-red-500 hover:text-red-600">删除</button>
            </div>
        `;
        container.appendChild(div);
    });

    // 更新策略模板中的钱包选择
    updateWalletSelection();
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

    // 清除所有钱包选择
    const checkboxes = document.querySelectorAll('.wallet-checkbox');
    checkboxes.forEach(checkbox => checkbox.checked = false);
}


// 获取当前行之前所有行的总卖出比例
function getPreviousTotalSellPercentage(currentRow) {
    let total = 0;
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));
    const currentIndex = allRows.indexOf(currentRow);

    for (let i = 0; i < currentIndex; i++) {
        const sellValue = parseFloat(allRows[i].querySelector('.stop-position').value) || 0;
        total += sellValue / 100; // 转换为小数
    }

    return total;
}

// 更新总仓位比例（当卖出比例改变时调用）
function updatePosition(sellInput) {
    const currentRow = sellInput.closest('div').parentElement;
    const positionInput = currentRow.querySelector('.stop-position');
    const sellPercentage = parseFloat(sellInput.value) || 0;
    const previousTotalSell = getPreviousTotalSellPercentage(currentRow);

    // 计算剩余仓位比例
    const remainingPosition = 1 - previousTotalSell;

    // 计算当前级别的总仓位比例
    const positionPercentage = (sellPercentage / 100) * remainingPosition * 100;

    // 更新总仓位比例输入框的值，保留2位小数
    // positionInput.value = positionPercentage.toFixed(2);
    positionInput.value = positionPercentage;

    // 更新后续行的总仓位比例
    updateSubsequentPositions(currentRow);
}

// 更新卖出比例（当总仓位比例改变时调用）
function updateSell(positionInput) {
    const currentRow = positionInput.closest('div').parentElement;
    const sellInput = currentRow.querySelector('.stop-sell');
    const positionPercentage = parseFloat(positionInput.value) || 0;
    const previousTotalSell = getPreviousTotalSellPercentage(currentRow);

    // 计算剩余仓位比例
    const remainingPosition = 1 - previousTotalSell;

    // 计算卖出比例
    const sellPercentage = (positionPercentage / 100) / remainingPosition * 100;

    // 更新卖出比例输入框的值，保留2位小数
    sellInput.value = sellPercentage.toFixed(2);

    // 更新后续行的总仓位比例
    updateSubsequentPositions(currentRow);
}

// 更新当前行之后的所有行的总仓位比例
function updateSubsequentPositions(currentRow) {
    const allRows = Array.from(document.querySelectorAll('#stopLevelsList > div'));
    const currentIndex = allRows.indexOf(currentRow);

    for (let i = currentIndex + 1; i < allRows.length; i++) {
        const row = allRows[i];
        const sellInput = row.querySelector('.stop-sell');
        updatePosition(sellInput);
    }
}
















// 将 addStopLevelToUI 改名为 addStopLevel
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

    // 为新添加的输入框设置初始值时触发更新
    if (sell || position) {
        const sellInput = container.querySelector('.stop-sell');
        updatePosition(sellInput);
    }
}

// 同时需要更新调用这个函数的地方
function showNewStrategyModal() {
    editingTemplateIndex = null;
    document.getElementById('modalTitle').textContent = '新建策略模板';
    clearModalInputs();
    updateWalletSelection();
    // 添加一个预设的空行
    addStopLevel();
    document.getElementById('strategyModal').classList.remove('hidden');
}

function showEditStrategyModal(index) {
    editingTemplateIndex = index;
    const template = strategyTemplates[index];
    document.getElementById('modalTitle').textContent = '编辑策略模板';
    fillModalWithTemplate(template);
    updateWalletSelection();
    // 如果没有止盈止损级别，添加一个空行
    if (!template.stopLevels || template.stopLevels.length === 0) {
        addStopLevel();
    }
    document.getElementById('strategyModal').classList.remove('hidden');
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

    // 重新生成止盈止损级别
    document.getElementById('stopLevelsList').innerHTML = '';
    template.stopLevels.forEach(level => {
        addStopLevel(level.increase, level.sell, level.position);
    });
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

function saveStrategyTemplate() {
    const selectedWallets = Array.from(document.querySelectorAll('.wallet-checkbox:checked'))
        .map(checkbox => checkbox.value);

    const template = {
        name: document.getElementById('templateName').value,
        selectedWallets: selectedWallets,
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
        stopLevels: collectStopLevels()
    };

// 验证必填字段
    if (!template.name) {
        alert('请填写模板名称');
        return;
    }

    // 验证是否选择了钱包
    if (template.selectedWallets.length === 0) {
        alert('请至少选择一个钱包');
        return;
    }

    // 验证买入金额范围
    if (template.minBuyAmount > template.maxBuyAmount) {
        alert('最小买入金额不能大于最大买入金额');
        return;
    }

    // 验证止盈止损级别
    if (template.stopLevels.length === 0) {
        alert('请至少添加一个止盈止损级别');
        return;
    }

    // 保存模板
    if (editingTemplateIndex !== null) {
        strategyTemplates[editingTemplateIndex] = template;
    } else {
        strategyTemplates.push(template);
    }

    refreshTemplateList();
    closeStrategyModal();
}

function duplicateTemplate(index) {
    const template = {...strategyTemplates[index]};
    template.name = `${template.name} (复制)`;
    strategyTemplates.push(template);
    refreshTemplateList();
}

function deleteTemplate(index) {
    if (confirm('确定要删除这个策略模板吗？')) {
        strategyTemplates.splice(index, 1);
        refreshTemplateList();
    }
}

function closeStrategyModal() {
    document.getElementById('strategyModal').classList.add('hidden');
}

function refreshTemplateList() {
    const container = document.getElementById('strategyTemplateList');
    container.innerHTML = '';
    const strategySelect = document.getElementById('strategySelection');
    strategySelect.innerHTML = '';

    strategyTemplates.forEach((template, index) => {
        const selectedWalletNames = template.selectedWallets
            .map(addr => wallets.find(w => w.address === addr)?.name || '未知钱包')
            .join(', ');

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
                <div class="col-span-2">选中钱包: ${selectedWalletNames}</div>
                <div>买入金额范围: ${template.minBuyAmount} - ${template.maxBuyAmount} SOL</div>
                <div>滑点: ${template.slippage}%</div>
                <div>极速模式: ${template.speedMode === 'fast' ? '开启' : '关闭'}</div>
                <div>防夹模式: ${template.antiSqueeze === 'on' ? '开启' : '关闭'}</div>
                <div>买入优先费: ${template.buyPriority}</div>
                <div>卖出优先费: ${template.sellPriority}</div>
                <div>止损优先费: ${template.stopPriority}</div>
                <div>移动止损: ${template.trailingStop}%</div>
                <div>卖出比例: ${template.sellPercent}%</div>
            </div>
        `;
        container.appendChild(div);

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
    const selectedWalletNames = selectedStrategy.selectedWallets
        .map(addr => wallets.find(w => w.address === addr)?.name || '未知钱包')
        .join(', ');

    if (selectedStrategy.selectedWallets.length === 0) {
        alert('所选策略没有选择钱包');
        return;
    }

    alert(`开始交易
策略: ${selectedStrategy.name}
选中钱包: ${selectedWalletNames}
钱包数量: ${selectedStrategy.selectedWallets.length}`);
}

function stopTrading() {
    alert('停止交易');
}

// 在页面加载完成后更新所有输入框的step属性
function updateAllInputStepAttributes() {
    const numericInputs = document.querySelectorAll('input[type="number"]');
    numericInputs.forEach(input => {
        if (input.id.includes('Priority')) {
            input.setAttribute('step', '0.001');
        } else if (input.id.includes('Slippage') ||
            input.id.includes('BuyAmount') ||
            input.id.includes('TrailingStop') ||
            input.id.includes('SellPercent')) {
            input.setAttribute('step', '0.1');
        }
    });
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    initializeData();
    updateAllInputStepAttributes();
});