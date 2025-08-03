// 全局变量
let urlList = [];
let allProxies = [];
let selectedProxies = [];
let customNodes = [];
let customUrlList = []; // 自定义节点的URL列表
let chainedConfig = {}; // {node_id: dialer_proxy_name}
let config = {};
let gistList = [];
let currentGist = null;

// DOM元素获取函数 - 按需获取避免过度缓存
const getElement = (id) => document.getElementById(id);
const getElements = (selector) => document.querySelectorAll(selector);

// 只缓存高频使用的核心元素
const coreElements = {
    loadingOverlay: getElement('loadingOverlay'),
    toast: getElement('toast')
};

// 通用API调用函数，集成加载状态管理
async function apiCall(url, options = {}, loadingText = '处理中...') {
    try {
        showLoading(loadingText);
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        const data = await response.json();
        return data;
    } finally {
        hideLoading();
    }
}

// 带成功/错误提示的API调用
async function apiCallWithToast(url, options = {}, loadingText = '处理中...', successMessage = null) {
    try {
        const data = await apiCall(url, options, loadingText);
        if (data.success) {
            if (successMessage) {
                showToast(successMessage, 'success');
            }
        } else {
            showToast(data.error || '操作失败', 'error');
        }
        return data;
    } catch (error) {
        showToast('请求失败: ' + error.message, 'error');
        return { success: false, error: error.message };
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    loadGists();
    loadHistory();
    loadChainedProxyConfig();
    loadTokenStatus();
    setupEventListeners();
});

// 设置事件监听器
function setupEventListeners() {
    // URL 输入相关
    getElement('urlInput').addEventListener('paste', () => {
        setTimeout(() => extractUrls(), 100);
    });
    getElement('extractBtn').addEventListener('click', extractUrls);
    getElement('testAllBtn').addEventListener('click', testAllUrls);
    
    // 地区过滤器
    getElements('.region-btn').forEach(btn => {
        btn.addEventListener('click', () => toggleRegionFilter(btn));
    });
    
    // 获取节点
    getElement('fetchProxiesBtn').addEventListener('click', fetchProxies);
    
    // 节点选择控制
    getElement('selectAllBtn').addEventListener('click', () => selectAllProxies(true));
    getElement('deselectAllBtn').addEventListener('click', () => selectAllProxies(false));
    getElement('invertSelectionBtn').addEventListener('click', invertProxySelection);
    
    // 自定义节点
    getElement('extractCustomUrlsBtn').addEventListener('click', extractCustomUrls);
    getElement('fetchCustomNodesBtn').addEventListener('click', fetchCustomNodesFromUrl);
    getElement('parseCustomNodesBtn').addEventListener('click', parseCustomNodes);
    
    // 配置管理
    getElement('loadConfigBtn').addEventListener('click', loadChainedProxyConfig);
    getElement('saveConfigBtn').addEventListener('click', saveChainedProxyConfig);
    getElement('clearConfigBtn').addEventListener('click', clearChainedProxyConfig);
    
    // 生成配置
    getElement('generateConfigBtn').addEventListener('click', generateConfig);
    
    // 复制订阅链接
    getElement('copyBtn').addEventListener('click', copySubscriptionUrl);
    
    // Gist 管理
    getElement('manageGistsBtn').addEventListener('click', openGistModal);
    getElement('gistSelector').addEventListener('change', onGistSelect);
    // GitHub Token 相关事件
    getElement('configureTokenBtn').addEventListener('click', openTokenModal);
    getElement('viewTokenBtn').addEventListener('click', viewToken);
    getElement('editTokenBtn').addEventListener('click', editToken);
    getElement('saveTokenModalBtn').addEventListener('click', saveTokenFromModal);
    getElement('toggleTokenVisibility').addEventListener('click', toggleTokenVisibility);
    
    getElement('addExistingGistBtn').addEventListener('click', addExistingGist);
    
    // 重用 Gist 复选框变化时切换显示
    getElement('reuseGist').addEventListener('change', toggleGistOptions);
}

// 切换 Gist 选项显示
function toggleGistOptions() {
    const reuseGist = getElement('reuseGist').checked;
    const gistSelectorContainer = getElement('gistSelectorContainer');
    const newGistNameContainer = getElement('newGistNameContainer');
    const newGistNameInput = getElement('newGistNameInput');
    
    if (reuseGist) {
        // 显示 Gist 选择器，隐藏新名称输入框
        gistSelectorContainer.style.display = 'block';
        newGistNameContainer.style.display = 'none';
        newGistNameInput.value = ''; // 清空输入
    } else {
        // 隐藏 Gist 选择器，显示新名称输入框
        gistSelectorContainer.style.display = 'none';
        newGistNameContainer.style.display = 'block';
    }
}

// 加载配置
async function loadConfig() {
    try {
        const data = await apiCall('/api/config');
        
        if (data.success) {
            config = data.config;
            getElement('reuseGist').checked = config.reuse_gist;
            
            if (config.has_gist_id && config.reuse_gist) {
                showToast('已启用 Gist 重用模式', 'success');
            }
            
            // 初始化界面显示状态
            toggleGistOptions();
        }
        
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}


// 添加已有 Gist
async function addExistingGist() {
    const name = getElement('addGistName').value.trim();
    const gistId = getElement('addGistId').value.trim();
    
    if (!name || !gistId) {
        showToast('请输入 Gist 名称和 ID', 'error');
        return;
    }
    
    try {
        showLoading('正在添加 Gist...');
        
        const response = await fetch('/api/gists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, gist_id: gistId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            getElement('addGistName').value = '';
            getElement('addGistId').value = '';
            await loadGists();
            updateGistList();
        } else {
            showToast(data.error, 'error');
        }
    } catch (error) {
        showToast('添加 Gist 失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 加载 Gist 列表
async function loadGists() {
    try {
        const response = await fetch('/api/gists');
        const data = await response.json();
        
        if (data.success) {
            gistList = data.gists;
            updateGistSelector();
            
            // 获取当前选中的 Gist
            const currentResponse = await fetch('/api/current-gist');
            const currentData = await currentResponse.json();
            
            if (currentData.success && currentData.current_name) {
                currentGist = currentData.current_name;
                getElement('gistSelector').value = currentGist;
            }
        }
    } catch (error) {
        console.error('加载 Gist 列表失败:', error);
    }
}

// 更新 Gist 选择器
function updateGistSelector() {
    getElement('gistSelector').innerHTML = gistList.map(gist =>
        `<option value="${gist.name}" ${gist.is_default ? 'data-default="true"' : ''}>
            ${gist.name}${gist.is_default ? ' (默认)' : ''}
        </option>`
    ).join('');
    
    // 如果有当前 Gist，选中它
    if (currentGist) {
        getElement('gistSelector').value = currentGist;
    }
}

// Gist 选择变化
function onGistSelect() {
    currentGist = getElement('gistSelector').value;
}

// 打开 Gist 管理对话框
function openGistModal() {
    getElement('gistManagementModal').style.display = 'flex';
    updateGistList();
}

// 关闭 Gist 管理对话框
function closeGistModal() {
    getElement('gistManagementModal').style.display = 'none';
}

// 更新 Gist 列表显示
function updateGistList() {
    if (gistList.length === 0) {
        getElement('gistList').innerHTML = '<div style="text-align: center; color: #999;">暂无 Gist 配置</div>';
        return;
    }
    
    getElement('gistList').innerHTML = gistList.map((gist, index) => `
        <div class="gist-item ${gist.is_default ? 'is-default' : ''}">
            <div class="gist-info">
                <div class="gist-name">
                    ${escapeHtml(gist.name)}
                    ${gist.is_default ? '<span class="default-badge">默认</span>' : ''}
                </div>
                <div class="gist-id">${gist.id}</div>
            </div>
            <div class="gist-actions">
                <button class="gist-action-btn" onclick="renameGistByIndex(${index})">
                    <i class="fas fa-edit"></i> 重命名
                </button>
                ${gistList.length > 1 ? `
                    <button class="gist-action-btn delete" onclick="deleteGistByIndex(${index})">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// 通过索引重命名 Gist
async function renameGistByIndex(index) {
    if (index < 0 || index >= gistList.length) {
        showToast('无效的 Gist 索引', 'error');
        return;
    }
    
    const gist = gistList[index];
    await renameGist(gist.name);
}

// 通过索引删除 Gist
async function deleteGistByIndex(index) {
    if (index < 0 || index >= gistList.length) {
        showToast('无效的 Gist 索引', 'error');
        return;
    }
    
    const gist = gistList[index];
    await deleteGist(gist.name);
}

// 重命名 Gist
async function renameGist(oldName) {
    const newName = prompt(`重命名 "${oldName}" 为:`, oldName);
    
    if (!newName || newName === oldName) {
        return;
    }
    
    try {
        const data = await apiCallWithToast(`/api/gists/${encodeURIComponent(oldName)}`, {
            method: 'PUT',
            body: JSON.stringify({ new_name: newName })
        }, '正在重命名...', null);
        
        if (data.success) {
            showToast(data.message, 'success');
            await loadGists();
            updateGistList();
        }
    } catch (error) {
        showToast('重命名失败: ' + error.message, 'error');
    }
}

// 删除 Gist
async function deleteGist(name) {
    if (!confirm(`确定要删除 Gist "${name}" 吗？`)) {
        return;
    }
    
    try {
        const data = await apiCallWithToast(`/api/gists/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        }, '正在删除...', null);
        
        if (data.success) {
            showToast(data.message, 'success');
            await loadGists();
            updateGistList();
        }
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// 加载历史 URL
async function loadHistory() {
    try {
        const response = await fetch('/api/urls');
        const data = await response.json();
        
        if (data.success && data.urls.length > 0) {
            displayHistory(data.urls);
        }
    } catch (error) {
        console.error('加载历史失败:', error);
    }
}

// 显示历史 URL
function displayHistory(urls) {
    getElement('historyList').innerHTML = urls.map(url => 
        `<div class="history-item" onclick="addUrlFromHistory('${url}')">${url}</div>`
    ).join('');
}

// 从历史添加 URL
function addUrlFromHistory(url) {
    const currentText = getElement('urlInput').value;
    getElement('urlInput').value = currentText ? `${currentText}\n${url}` : url;
    extractUrls();
}

// 提取 URL
async function extractUrls() {
    const text = getElement('urlInput').value;
    
    if (!text.trim()) {
        urlList = [];
        updateUrlList();
        return;
    }
    
    try {
        showLoading('正在提取 URL...');
        
        const response = await fetch('/api/extract-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        
        const data = await response.json();
        
        if (data.success) {
            urlList = data.urls.map(url => ({ url, selected: true, status: '' }));
            updateUrlList();
        } else {
            showToast('提取 URL 失败: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('提取 URL 失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 更新 URL 列表显示
function updateUrlList() {
    getElement('urlCount').textContent = urlList.length;
    
    if (urlList.length === 0) {
        getElement('urlList').innerHTML = '<div style="text-align: center; color: #999;">暂无 URL</div>';
        return;
    }
    
    getElement('urlList').innerHTML = urlList.map((item, index) => `
        <div class="url-item">
            <input type="checkbox" class="url-checkbox" 
                   ${item.selected ? 'checked' : ''} 
                   onchange="toggleUrl(${index})">
            <span class="url-text">${item.url}</span>
            ${item.status ? `<span class="url-status ${getStatusClass(item.status)}">${item.status}</span>` : ''}
        </div>
    `).join('');
}

// 切换 URL 选中状态
function toggleUrl(index) {
    urlList[index].selected = !urlList[index].selected;
}

// 获取状态样式类
function getStatusClass(status) {
    if (status === '可用') return 'status-available';
    if (status === '测试中...') return 'status-testing';
    return 'status-unavailable';
}

// 测试所有 URL
async function testAllUrls() {
    const selectedUrls = urlList.filter(item => item.selected).map(item => item.url);
    
    if (selectedUrls.length === 0) {
        showToast('请至少选择一个 URL', 'error');
        return;
    }
    
    // 设置所有选中的 URL 为测试中状态
    urlList.forEach(item => {
        if (item.selected) {
            item.status = '测试中...';
        }
    });
    updateUrlList();
    
    try {
        const response = await fetch('/api/test-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls: selectedUrls })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 更新测试结果
            data.results.forEach(result => {
                const item = urlList.find(item => item.url === result.url);
                if (item) {
                    item.status = result.status;
                }
            });
            updateUrlList();
        } else {
            showToast('测试失败: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('测试失败: ' + error.message, 'error');
    }
}

// 切换地区过滤器
function toggleRegionFilter(btn) {
    const region = btn.dataset.region;
    
    if (region === 'all') {
        // 如果点击全部，取消其他选择
        getElements('.region-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    } else {
        // 取消全部选择
        document.querySelector('[data-region="all"]').classList.remove('active');
        
        // 切换当前按钮
        btn.classList.toggle('active');
        
        // 如果没有任何选择，默认选择香港
        const hasActive = Array.from(getElements('.region-btn')).some(b => 
            b.classList.contains('active') && b.dataset.region !== 'all'
        );
        if (!hasActive) {
            document.querySelector('[data-region="hk"]').classList.add('active');
        }
    }
}

// 获取节点
async function fetchProxies() {
    const selectedUrls = urlList.filter(item => item.selected).map(item => item.url);
    
    if (selectedUrls.length === 0) {
        showToast('请至少选择一个订阅 URL', 'error');
        return;
    }
    
    // 获取过滤选项
    const activeRegions = Array.from(getElements('.region-btn'))
        .filter(btn => btn.classList.contains('active'))
        .map(btn => btn.dataset.region);
    
    const customKeywords = getElement('customKeywords').value
        .split(',')
        .map(k => k.trim())
        .filter(k => k);
    
    const filterOptions = {
        regions: activeRegions,
        keywords: customKeywords
    };
    
    try {
        showLoading('正在获取节点...');
        
        const response = await fetch('/api/fetch-proxies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                urls: selectedUrls,
                filter_options: filterOptions
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            allProxies = data.proxies;
            selectedProxies = [...allProxies]; // 默认全选
            displayProxies();
            showToast(`成功获取 ${allProxies.length} 个节点`, 'success');
            
            // 显示节点选择区域
            getElement('proxySelectionSection').style.display = 'block';
            getElement('proxySelectionSection').scrollIntoView({ behavior: 'smooth' });
            
            // 启用生成配置按钮
            updateGenerateButtonState();
        } else {
            showToast('获取节点失败: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('获取节点失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 提取自定义节点 URL
async function extractCustomUrls() {
    const text = getElement('customNodesUrlInput').value.trim();
    
    if (!text) {
        showToast('请输入订阅链接', 'error');
        return;
    }
    
    try {
        showLoading('正在提取 URL...');
        
        const response = await fetch('/api/extract-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        
        const data = await response.json();
        
        if (data.success && data.urls.length > 0) {
            customUrlList = data.urls.map(url => ({ url, selected: true }));
            updateCustomUrlList();
            showToast(`提取到 ${data.urls.length} 个订阅链接`, 'success');
        } else {
            showToast('未找到有效的 URL', 'error');
        }
    } catch (error) {
        showToast('提取 URL 失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 更新自定义 URL 列表显示
function updateCustomUrlList() {
    if (customUrlList.length === 0) {
        getElement('customUrlsList').style.display = 'none';
        return;
    }
    
    getElement('customUrlsList').style.display = 'block';
    getElement('customUrlsList').innerHTML = '<strong>已识别的订阅链接：</strong>' +
        customUrlList.map((item, index) => `
            <div class="custom-url-item">
                <input type="checkbox" ${item.selected ? 'checked' : ''}
                       onchange="toggleCustomUrl(${index})">
                <span class="url-text">${item.url}</span>
            </div>
        `).join('');
}

// 切换自定义 URL 选中状态
function toggleCustomUrl(index) {
    customUrlList[index].selected = !customUrlList[index].selected;
}

// 从 URL 获取自定义节点
async function fetchCustomNodesFromUrl() {
    const selectedUrls = customUrlList.filter(item => item.selected).map(item => item.url);
    
    if (selectedUrls.length === 0) {
        showToast('请至少选择一个订阅链接', 'error');
        return;
    }
    
    try {
        showLoading('正在获取节点...');
        
        // 使用已有的 fetch-proxies API，但不过滤
        const response = await fetch('/api/fetch-proxies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                urls: selectedUrls,
                filter_options: { regions: ['all'] }  // 获取所有节点
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.proxies.length > 0) {
            // 标记为自定义节点
            data.proxies.forEach(node => {
                node.is_custom = true;
                node._id = `custom_${node._id}`;  // 确保 ID 唯一
            });
            
            // 添加到自定义节点列表
            customNodes = customNodes.concat(data.proxies);
            
            // 自动标记为需要链式代理
            const defaultDialer = getElement('defaultDialerProxy').value || 'dialer-selector';
            data.proxies.forEach(node => {
                chainedConfig[node._id] = defaultDialer;
            });
            
            // 清空输入
            getElement('customNodesUrlInput').value = '';
            customUrlList = [];
            updateCustomUrlList();
            
            // 更新显示
            displayProxies();
            showToast(`成功添加 ${data.proxies.length} 个自定义节点`, 'success');
            
            // 显示节点选择区域
            getElement('proxySelectionSection').style.display = 'block';
            
            // 启用生成配置按钮
            updateGenerateButtonState();
        } else {
            showToast('获取节点失败: ' + (data.error || '未找到有效节点'), 'error');
        }
    } catch (error) {
        showToast('获取节点失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 解析自定义节点
async function parseCustomNodes() {
    const nodesText = getElement('customNodesText').value.trim();
    
    if (!nodesText) {
        showToast('请输入节点配置', 'error');
        return;
    }
    
    try {
        showLoading('正在解析节点...');
        
        const response = await fetch('/api/parse-clash-nodes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nodes_text: nodesText })
        });
        
        const data = await response.json();
        
        if (data.success && data.nodes.length > 0) {
            // 添加到自定义节点列表
            customNodes = customNodes.concat(data.nodes);
            
            // 自动标记为需要链式代理
            const defaultDialer = getElement('defaultDialerProxy').value || 'dialer-selector';
            data.nodes.forEach(node => {
                chainedConfig[node._id] = defaultDialer;
            });
            
            // 清空输入
            getElement('customNodesText').value = '';
            
            // 更新显示
            displayProxies();
            showToast(`成功添加 ${data.nodes.length} 个自定义节点`, 'success');
            
            // 显示节点选择区域
            getElement('proxySelectionSection').style.display = 'block';
            
            // 启用生成配置按钮
            updateGenerateButtonState();
        } else {
            showToast('解析节点失败: ' + (data.error || '未找到有效节点'), 'error');
        }
    } catch (error) {
        showToast('解析节点失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 显示代理节点
function displayProxies() {
    const allNodes = [...allProxies, ...customNodes];
    getElement('totalProxyCount').textContent = allNodes.length;
    updateSelectedCount();
    updateChainedCount();
    
    if (allNodes.length === 0) {
        getElement('proxyList').innerHTML = '<div style="text-align: center; color: #999;">没有找到符合条件的节点</div>';
        return;
    }
    
    getElement('proxyList').innerHTML = allNodes.map(proxy => {
        const isSelected = selectedProxies.some(p => p._id === proxy._id);
        const isChained = chainedConfig.hasOwnProperty(proxy._id);
        const dialerProxy = chainedConfig[proxy._id] || getElement('defaultDialerProxy').value || 'dialer-selector';
        
        return `
            <div class="proxy-item ${isSelected ? 'selected' : ''} ${isChained ? 'chained' : ''}" 
                 onclick="toggleProxy('${proxy._id}')">
                <input type="checkbox" class="proxy-checkbox" 
                       ${isSelected ? 'checked' : ''}>
                <div class="proxy-info">
                    <div class="proxy-name">
                        ${escapeHtml(proxy.name)}
                        ${proxy.is_custom ? '<span class="custom-node-badge">自定义</span>' : ''}
                        ${isChained ? `<span class="chain-indicator"><i class="fas fa-link"></i> 链式代理</span>` : ''}
                    </div>
                    <div class="proxy-details">
                        <span class="proxy-type">${proxy.type.toUpperCase()}</span>
                        <span class="proxy-server">${proxy.server}:${proxy.port}</span>
                    </div>
                </div>
                <div class="chain-controls" onclick="event.stopPropagation()">
                    <button class="chain-toggle ${isChained ? 'active' : ''}" 
                            onclick="toggleChainedProxy('${proxy._id}')">
                        <i class="fas fa-link"></i> 链式代理
                    </button>
                    ${isChained ? `
                        <input type="text" class="dialer-input" 
                               value="${dialerProxy}"
                               placeholder="dialer-selector"
                               onclick="event.stopPropagation()"
                               onchange="updateDialerProxy('${proxy._id}', this.value)">
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// 切换代理选择
function toggleProxy(proxyId) {
    const allNodes = [...allProxies, ...customNodes];
    const proxy = allNodes.find(p => p._id === proxyId);
    if (!proxy) return;
    
    const index = selectedProxies.findIndex(p => p._id === proxyId);
    if (index === -1) {
        selectedProxies.push(proxy);
    } else {
        selectedProxies.splice(index, 1);
    }
    
    displayProxies();
}

// 切换链式代理
function toggleChainedProxy(proxyId) {
    if (chainedConfig.hasOwnProperty(proxyId)) {
        delete chainedConfig[proxyId];
    } else {
        const defaultDialer = getElement('defaultDialerProxy').value || 'dialer-selector';
        chainedConfig[proxyId] = defaultDialer;
    }
    displayProxies();
}

// 更新 dialer-proxy
function updateDialerProxy(proxyId, value) {
    if (value.trim()) {
        chainedConfig[proxyId] = value.trim();
    } else {
        delete chainedConfig[proxyId];
    }
    updateChainedCount();
}

// 全选/取消全选
function selectAllProxies(select) {
    const allNodes = [...allProxies, ...customNodes];
    if (select) {
        selectedProxies = [...allNodes];
    } else {
        selectedProxies = [];
    }
    displayProxies();
}

// 反选
function invertProxySelection() {
    const allNodes = [...allProxies, ...customNodes];
    selectedProxies = allNodes.filter(proxy => 
        !selectedProxies.some(p => p._id === proxy._id)
    );
    displayProxies();
}

// 更新选中数量
function updateSelectedCount() {
    getElement('selectedProxyCount').textContent = selectedProxies.length;
}

// 更新链式代理数量
function updateChainedCount() {
    getElement('chainedProxyCount').textContent = Object.keys(chainedConfig).length;
}

// 更新生成按钮状态
function updateGenerateButtonState() {
    const hasNodes = selectedProxies.length > 0 || customNodes.length > 0;
    getElement('generateConfigBtn').disabled = !hasNodes;
}

// 加载链式代理配置
async function loadChainedProxyConfig() {
    try {
        showLoading('正在加载配置...');
        
        const response = await fetch('/api/chained-proxy-config');
        const data = await response.json();
        
        if (data.success && data.config) {
            const config = data.config;
            
            // 加载自定义节点
            if (config.custom_nodes && config.custom_nodes.length > 0) {
                customNodes = config.custom_nodes;
            }
            
            // 加载链式代理配置
            if (config.chained_nodes) {
                chainedConfig = config.chained_nodes;
            }
            
            // 加载所有从订阅获取的节点
            if (config.all_proxies && config.all_proxies.length > 0) {
                allProxies = config.all_proxies;
                
                // 恢复选中状态
                if (config.selected_proxy_ids && config.selected_proxy_ids.length > 0) {
                    selectedProxies = allProxies.filter(proxy =>
                        config.selected_proxy_ids.includes(proxy._id)
                    );
                } else {
                    // 如果没有保存选中状态，默认全选
                    selectedProxies = [...allProxies];
                }
            }
            
            // 加载订阅URL列表
            if (config.subscription_urls && config.subscription_urls.length > 0) {
                // 将URL添加到输入框
                getElement('urlInput').value = config.subscription_urls.join('\n');
                // 更新URL列表
                urlList = config.subscription_urls.map(url => ({ url, selected: true, status: '' }));
                updateUrlList();
            }
            
            // 更新显示
            displayProxies();
            showToast('配置加载成功', 'success');
            
            // 显示节点选择区域（如果有任何节点）
            if (customNodes.length > 0 || allProxies.length > 0) {
                getElement('proxySelectionSection').style.display = 'block';
                updateGenerateButtonState();
            }
        }
    } catch (error) {
        showToast('加载配置失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 保存链式代理配置
async function saveChainedProxyConfig() {
    try {
        showLoading('正在保存配置...');
        
        const config = {
            custom_nodes: customNodes,
            chained_nodes: chainedConfig,
            // 新增：保存所有从订阅获取的节点
            all_proxies: allProxies,
            // 新增：保存选中的节点ID列表
            selected_proxy_ids: selectedProxies.map(p => p._id),
            // 新增：保存当前使用的URL列表
            subscription_urls: urlList.filter(item => item.selected).map(item => item.url)
        };
        
        const response = await fetch('/api/chained-proxy-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('配置保存成功', 'success');
        } else {
            showToast('保存配置失败: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('保存配置失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 清除链式代理配置
async function clearChainedProxyConfig() {
    if (!confirm('确定要清除所有保存的配置吗？这将清除所有节点数据（包括订阅节点和自定义节点）。')) {
        return;
    }
    
    try {
        showLoading('正在清除配置...');
        
        // 清空本地所有数据
        customNodes = [];
        chainedConfig = {};
        allProxies = [];
        selectedProxies = [];
        urlList = [];
        
        // 清空输入框
        getElement('urlInput').value = '';
        
        // 清空服务器端存储
        const response = await fetch('/api/chained-proxy-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                config: {
                    custom_nodes: [],
                    chained_nodes: {},
                    all_proxies: [],
                    selected_proxy_ids: [],
                    subscription_urls: []
                }
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateUrlList();
            displayProxies();
            updateGenerateButtonState();
            showToast('所有配置已清除', 'success');
            
            // 隐藏节点选择区域
            getElement('proxySelectionSection').style.display = 'none';
        } else {
            throw new Error(data.error || '清除配置失败');
        }
    } catch (error) {
        console.error('清除配置失败:', error);
        showToast('清除配置失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 生成配置
async function generateConfig() {
    if (selectedProxies.length === 0 && customNodes.length === 0) {
        showToast('请至少选择一个节点或添加自定义节点', 'error');
        return;
    }
    
    // 从 localStorage 或环境变量获取 GitHub Token
    const githubToken = localStorage.getItem('github_token') || undefined;
    const reuseGist = getElement('reuseGist').checked;
    let gistName = null;
    
    if (reuseGist) {
        // 重用模式：使用选中的 Gist
        gistName = getElement('gistSelector').value;
    } else {
        // 新建模式：使用输入的名称或留空（后端会自动生成）
        gistName = getElement('newGistNameInput').value.trim() || null;
    }
    
    try {
        showLoading('正在生成配置...');
        
        // 过滤掉 selectedProxies 中的自定义节点，避免重复
        const selectedNonCustomProxies = selectedProxies.filter(proxy => !proxy.is_custom);
        
        const response = await fetch('/api/generate-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                selected_proxies: selectedNonCustomProxies,  // 只包含非自定义节点
                custom_nodes: customNodes,  // 所有自定义节点
                chained_config: chainedConfig,
                github_token: githubToken,
                reuse_gist: reuseGist,
                save_config: true,
                gist_name: gistName  // 指定使用的 Gist
            })
        });
        
        const data = await response.json();
        
        displayResult(data);
        
        if (data.success) {
            // 重新加载历史
            loadHistory();
        }
    } catch (error) {
        showToast('生成配置失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 显示处理结果
function displayResult(result) {
    getElement('resultSection').style.display = 'block';
    
    // 显示消息
    getElement('resultMessage').textContent = result.message || result.error;
    getElement('resultMessage').className = result.success ? 'result-success' : 'result-error';
    
    // 显示订阅链接
    if (result.success && result.subscription_url) {
        getElement('subscriptionUrl').style.display = 'block';
        getElement('subscriptionInput').value = result.subscription_url;
    } else {
        getElement('subscriptionUrl').style.display = 'none';
    }
    
    // 显示处理详情
    if (result.details) {
        getElement('processDetails').innerHTML = '<h3>处理详情：</h3>' + 
            `<div class="detail-item">
                <span>总节点数：${result.details.total_nodes}</span>
                <span>选择的节点：${result.details.selected_nodes}</span>
                <span>自定义节点：${result.details.custom_nodes}</span>
                <span>链式代理节点：${result.details.chained_nodes}</span>
            </div>`;
    } else {
        getElement('processDetails').innerHTML = '';
    }
    
    // 滚动到结果区域
    getElement('resultSection').scrollIntoView({ behavior: 'smooth' });
}

// 复制订阅链接
function copySubscriptionUrl() {
    const url = getElement('subscriptionInput').value;
    if (!url) return;
    
    navigator.clipboard.writeText(url).then(() => {
        showToast('订阅链接已复制到剪贴板', 'success');
    }).catch(() => {
        // 降级方案
        getElement('subscriptionInput').select();
        document.execCommand('copy');
        showToast('订阅链接已复制到剪贴板', 'success');
    });
}

// 显示加载动画
function showLoading(text = '加载中...') {
    coreElements.loadingOverlay.style.display = 'flex';
    coreElements.loadingOverlay.querySelector('.loading-text').textContent = text;
}

// 隐藏加载动画
function hideLoading() {
    coreElements.loadingOverlay.style.display = 'none';
}

// 显示 Toast 通知
function showToast(message, type = 'info') {
    coreElements.toast.textContent = message;
    coreElements.toast.className = `toast ${type}`;
    coreElements.toast.classList.add('show');
    
    setTimeout(() => {
        coreElements.toast.classList.remove('show');
    }, 3000);
}

// HTML 转义
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// GitHub Token 管理功能
// 加载 Token 状态
async function loadTokenStatus() {
    try {
        const response = await fetch('/api/github-token');
        const data = await response.json();
        
        if (data.success) {
            updateTokenDisplay(data);
        }
    } catch (error) {
        console.error('加载 Token 状态失败:', error);
    }
}

// 更新 Token 显示
function updateTokenDisplay(tokenData) {
    const statusText = getElement('tokenStatusText');
    const statusIcon = getElement('tokenStatusIcon');
    const viewBtn = getElement('viewTokenBtn');
    const editBtn = getElement('editTokenBtn');
    const configureBtn = getElement('configureTokenBtn');
    
    if (tokenData.has_token) {
        statusText.textContent = `已配置 (${tokenData.masked_token})`;
        statusIcon.innerHTML = '<i class="fas fa-check-circle" style="color: #27ae60;"></i>';
        viewBtn.style.display = 'inline-block';
        editBtn.style.display = 'inline-block';
        configureBtn.innerHTML = '<i class="fas fa-key"></i> 重新配置';
    } else {
        statusText.textContent = '未配置';
        statusIcon.innerHTML = '<i class="fas fa-times-circle" style="color: #e74c3c;"></i>';
        viewBtn.style.display = 'none';
        editBtn.style.display = 'none';
        configureBtn.innerHTML = '<i class="fas fa-key"></i> 配置 Token';
    }
}

// 打开 Token 配置对话框
function openTokenModal() {
    getElement('tokenConfigModal').style.display = 'flex';
    getElement('githubTokenInput').value = '';
    getElement('githubTokenInput').type = 'password';
    getElement('toggleTokenVisibility').innerHTML = '<i class="fas fa-eye"></i>';
}

// 关闭 Token 配置对话框
function closeTokenModal() {
    getElement('tokenConfigModal').style.display = 'none';
}

// 查看 Token
async function viewToken() {
    const response = await fetch('/api/github-token');
    const data = await response.json();
    
    if (data.success && data.has_token) {
        // 从本地存储或环境变量获取完整 token
        const savedToken = localStorage.getItem('github_token');
        if (savedToken) {
            alert(`GitHub Token: ${savedToken}`);
        } else {
            alert('Token 保存在 .env 文件中，无法直接查看完整内容');
        }
    }
}

// 编辑 Token
function editToken() {
    openTokenModal();
    // 尝试从本地存储加载 token
    const savedToken = localStorage.getItem('github_token');
    if (savedToken) {
        getElement('githubTokenInput').value = savedToken;
    }
}

// 切换 Token 可见性
function toggleTokenVisibility() {
    const input = getElement('githubTokenInput');
    const button = getElement('toggleTokenVisibility');
    
    if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        button.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

// 从模态框保存 Token
async function saveTokenFromModal() {
    const token = getElement('githubTokenInput').value.trim();
    const saveToEnv = getElement('saveTokenToEnvModal').checked;
    
    if (!token) {
        showToast('请输入 GitHub Token', 'error');
        return;
    }
    
    try {
        if (saveToEnv) {
            // 保存到 .env 文件
            const response = await apiCall('/api/save-github-token', {
                method: 'POST',
                body: JSON.stringify({ token })
            }, '保存 Token...');
            
            if (response.success) {
                showToast('Token 已保存到 .env 文件', 'success');
                localStorage.removeItem('github_token'); // 移除本地存储
            } else {
                showToast('保存失败: ' + response.error, 'error');
                return;
            }
        } else {
            // 保存到本地存储
            localStorage.setItem('github_token', token);
            showToast('Token 已保存到本地存储', 'success');
        }
        
        closeTokenModal();
        loadTokenStatus(); // 重新加载状态
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}


// 全局函数（供 HTML 内联事件使用）
window.addUrlFromHistory = addUrlFromHistory;
window.toggleUrl = toggleUrl;
window.toggleProxy = toggleProxy;
window.toggleChainedProxy = toggleChainedProxy;
window.updateDialerProxy = updateDialerProxy;
window.toggleCustomUrl = toggleCustomUrl;
window.clearChainedProxyConfig = clearChainedProxyConfig;
window.closeGistModal = closeGistModal;
window.closeTokenModal = closeTokenModal;
window.renameGist = renameGist;
window.deleteGist = deleteGist;
window.renameGistByIndex = renameGistByIndex;
window.deleteGistByIndex = deleteGistByIndex;