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
        selectedWallets: ["12345...abcde"], // 存储钱包地址
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

// 策略模板管理功能
function showNewStrategyModal() {
    editingTemplateIndex = null;
    document.getElementById('modalTitle').textContent = '新建策略模板';
    clearModalInputs();
    updateWalletSelection();
    document.getElementById('strategyModal').classList.remove('hidden');
}

function showEditStrategyModal(index) {
    editingTemplateIndex = index;
    const template = strategyTemplates[index];
    document.getElementById('modalTitle').textContent = '编辑策略模板';
    fillModalWithTemplate(template);
    updateWalletSelection();
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

    // 清除所有钱包选择
    const checkboxes = document.querySelectorAll('.wallet-checkbox');
    checkboxes.forEach(checkbox => checkbox.checked = false);
}

function fillModalWithTemplate(template) {
    document.getElementById('templateName').value = template.name;
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

function saveStrategyTemplate() {
    // 获取选中的钱包
    const selectedWallets = Array.from(document.querySelectorAll('.wallet-checkbox:checked'))
        .map(checkbox => checkbox.value);

    const template = {
        name: document.getElementById('templateName').value,
        selectedWallets: selectedWallets,
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
    if (!template.name) {
        alert('请填写模板名称');
        return;
    }

    // 验证是否选择了钱包
    if (template.selectedWallets.length === 0) {
        alert('请至少选择一个钱包');
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

function refreshTemplateList() {
    const container = document.getElementById('strategyTemplateList');
    container.innerHTML = '';
    const strategySelect = document.getElementById('strategySelection');
    strategySelect.innerHTML = '';

    strategyTemplates.forEach((template, index) => {
        // 获取选中钱包的名称列表
        const selectedWalletNames = template.selectedWallets
            .map(addr => wallets.find(w => w.address === addr)?.name || '未知钱包')
            .join(', ');

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
                <div class="col-span-2">选中钱包: ${selectedWalletNames}</div>
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

// 其他辅助函数保持不变
function closeStrategyModal() {
    document.getElementById('strategyModal').classList.add('hidden');
}

function addStopLevel() {
    addStopLevelToUI();
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

// 页面加载完成后初始化数据
document.addEventListener('DOMContentLoaded', initializeData);