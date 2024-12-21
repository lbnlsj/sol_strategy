// 存储策略模板和钱包的数组
let strategyTemplates = [];
let wallets = [];
let editingTemplateIndex = null;
let activeStrategyIndex = null;

// 页面加载时初始化数据
async function initializeData() {
    try {
        // 加载钱包数据
        const walletsResponse = await fetch('/api/wallets');
        wallets = await walletsResponse.json();

        // 加载策略数据
        const strategiesResponse = await fetch('/api/strategies');
        strategyTemplates = await strategiesResponse.json();

        refreshWalletList();
        refreshTemplateList();
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// API测试相关函数
async function runApiTest() {
    const address = document.getElementById('apiTestAddress').value.trim();
    const resultDiv = document.getElementById('apiTestResult');

    if (!address) {
        resultDiv.textContent = '请输入Solana地址';
        resultDiv.className = 'text-red-500';
        return;
    }

    try {
        resultDiv.textContent = '测试中...';
        resultDiv.className = 'text-blue-500';

        // 模拟API调用延迟
        await new Promise(resolve => setTimeout(resolve, 1000));

        resultDiv.textContent = 'API测试成功';
        resultDiv.className = 'text-green-500';
    } catch (error) {
        resultDiv.textContent = '测试失败: ' + error.message;
        resultDiv.className = 'text-red-500';
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

    // 尝试解析为数组格式
    try {
        if (privateKey.startsWith('[') && privateKey.endsWith(']')) {
            privateKey = JSON.parse(privateKey);
            // 验证数组格式
            if (!Array.isArray(privateKey) || !privateKey.every(num => Number.isInteger(num) && num >= 0 && num <= 255)) {
                throw new Error('私钥数组格式无效');
            }
        }
    } catch (e) {
        // 如果不是有效的数组格式,就按base58字符串处理
        privateKey = privateKey.replace(/\s/g, ''); // 移除所有空白字符
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
            const error = await response.json();
            throw new Error(error.error || '添加钱包失败');
        }

        const wallet = await response.json();
        wallets.push(wallet);
        refreshWalletList();
        closeWalletModal();
        showToast('钱包添加成功');
    } catch (error) {
        alert(error.message);
    }
}

async function deleteWallet(index, event) {
    event.stopPropagation(); // 阻止事件冒泡

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

            // 从所有策略中移除被删除的钱包
            strategyTemplates.forEach(template => {
                template.selectedWallets = template.selectedWallets.filter(addr => addr !== wallet.address);
            });

            refreshWalletList();
            refreshTemplateList();
            showToast('钱包已删除');
        } catch (error) {
            alert(error.message);
        }
    }
}

// 策略相关函数
function selectStrategy(index) {
    activeStrategyIndex = index;
    refreshTemplateList();

    // 显示选中反馈
    const template = strategyTemplates[index];
    showToast(`已切换至策略: ${template.name}`);
}

function showToast(message) {
    // 创建toast元素
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-gray-800 text-white px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300 translate-y-0 opacity-100 z-50';
    toast.textContent = message;

    // 添加到页面
    document.body.appendChild(toast);

    // 2秒后淡出并移除
    setTimeout(() => {
        toast.classList.add('translate-y-2', 'opacity-0');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 2000);
}

function duplicateTemplate(index, event) {
    event.stopPropagation(); // 阻止事件冒泡

    const template = JSON.parse(JSON.stringify(strategyTemplates[index])); // 深拷贝
    template.name = `${template.name} (复制)`;
    strategyTemplates.push(template);
    refreshTemplateList();

    showToast(`已复制策略: ${template.name}`);
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
                <button onclick="deleteWallet(${index}, event)" class="text-red-500 hover:text-red-600">删除</button>
            </div>
        `;
        container.appendChild(div);
    });

    // 更新策略模板中的钱包选择
    updateWalletSelection();
}

function refreshTemplateList() {
    const container = document.getElementById('strategyTemplateList');
    container.innerHTML = '';

    strategyTemplates.forEach((template, index) => {
        const selectedWalletNames = template.selectedWallets
            .map(addr => wallets.find(w => w.address === addr)?.name || '未知钱包')
            .join(', ');

        const div = document.createElement('div');
        div.className = `strategy-card relative border rounded-lg p-4 cursor-pointer hover:bg-gray-50 ${index === activeStrategyIndex ? 'active' : ''}`;
        div.onclick = () => selectStrategy(index);

        // 添加选中标记
        const checkmark = `
            <div class="selected-check">
                <svg class="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
            </div>
        `;

        div.innerHTML = `
            ${checkmark}
            <div class="flex justify-between items-center mb-2">
                <h3 class="font-semibold">${template.name}</h3>
                <div class="space-x-2">
                    <button onclick="showEditStrategyModal(${index}, event)" class="text-blue-500 hover:text-blue-600">编辑</button>
<!--                    <button onclick="duplicateTemplate(${index}, event)" class="text-green-500 hover:text-green-600">复制</button>-->
                    <button onclick="deleteTemplate(${index}, event)" class="text-red-500 hover:text-red-600">删除</button>
                    <button class="text-red-500 hover:text-red-600">&nbsp&nbsp</button>
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
    });
}

// 策略模板编辑相关函数
function showNewStrategyModal() {
    editingTemplateIndex = null;
    document.getElementById('modalTitle').textContent = '新建策略模板';
    clearModalInputs();
    updateWalletSelection();
    addStopLevel();
    document.getElementById('strategyModal').classList.remove('hidden');
}

function showEditStrategyModal(index, event) {
    event.stopPropagation(); // 阻止事件冒泡

    editingTemplateIndex = index;
    const template = strategyTemplates[index];
    document.getElementById('modalTitle').textContent = '编辑策略模板';
    fillModalWithTemplate(template);
    updateWalletSelection();

    if (!template.stopLevels || template.stopLevels.length === 0) {
        addStopLevel();
    }
    document.getElementById('strategyModal').classList.remove('hidden');
}

function closeStrategyModal() {
    document.getElementById('strategyModal').classList.add('hidden');
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

    const checkboxes = document.querySelectorAll('.wallet-checkbox');
    checkboxes.forEach(checkbox => checkbox.checked = false);
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
}

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

    // 更新总仓位比例输入框的值
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

    // 更新卖出比例输入框的值
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

async function saveStrategyTemplate() {
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

    if (!template.name) {
        alert('请填写模板名称');
        return;
    }

    if (template.selectedWallets.length === 0) {
        alert('请至少选择一个钱包');
        return;
    }

    try {
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
        } else {
            strategyTemplates.push(savedStrategy);
            showToast('策略创建成功');
        }

        refreshTemplateList();
        closeStrategyModal();
    } catch (error) {
        alert(error.message);
    }
}

async function deleteTemplate(index, event) {
    event.stopPropagation(); // 阻止事件冒泡

    if (confirm('确定要删除这个策略模板吗？')) {
        const template = strategyTemplates[index];
        try {
            const response = await fetch(`/api/strategies/${template.name}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('删除策略失败');
            }

            strategyTemplates.splice(index, 1);
            if (activeStrategyIndex === index) {
                activeStrategyIndex = null;
            } else if (activeStrategyIndex > index) {
                activeStrategyIndex--;
            }
            refreshTemplateList();
            showToast('策略已删除');
        } catch (error) {
            alert(error.message);
        }
    }
}

// 更新所有输入框的step属性
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