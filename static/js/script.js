//script.js
// Variáveis para os gráficos 
let statusChart, httpChart;
let currentPage = 1;
const itemsPerPage = 10;
let sortedBy = 'url';
let sortDirection = 'asc';
let filteredData = [];
let allData = {
    totalLinks: 0,
    status200: 0,
    statusError: 0,
    lastCheck: '--:--:--',
    links: []
};

// ===== FUNÇÕES PRINCIPAIS =====

// Função para buscar dados da API
async function fetchData() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) {
            throw new Error('Erro ao buscar dados');
        }
        const data = await response.json();
        allData = data;
        updateUI(data);
        addLog('Dados atualizados com sucesso', 'success');
    } catch (error) {
        console.error('Erro ao buscar dados:', error);
        addLog('Erro ao atualizar dados: ' + error.message, 'error');
    }
}

// Função para inicializar os gráficos
function initCharts(data) {
    const statusCtx = document.getElementById('status-chart').getContext('2d');
    const httpCtx = document.getElementById('http-chart').getContext('2d');
    
    // Dados para o gráfico de status
    const statusData = {
        healthy: data.links.filter(link => link.status === 200 && link.layoutOk && link.padraoOk).length,
        warning: data.links.filter(link => link.status === 200 && (!link.layoutOk || !link.padraoOk)).length,
        error: data.links.filter(link => link.status !== 200).length
    };
    
    // Gráfico de pizza para status geral
    if (statusChart) statusChart.destroy();
    statusChart = new Chart(statusCtx, {
        type: 'pie',
        data: {
            labels: ['Saudável', 'Com Avisos', 'Com Erros'],
            datasets: [{
                data: [statusData.healthy, statusData.warning, statusData.error],
                backgroundColor: [varToRgba('--success'), varToRgba('--warning'), varToRgba('--danger')],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#e6e6e6' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    // Dados para o gráfico de barras (status HTTP)
    const statusCodes = {};
    data.links.forEach(link => {
        const status = link.status;
        statusCodes[status] = (statusCodes[status] || 0) + 1;
    });
    
    const httpLabels = Object.keys(statusCodes);
    const httpData = Object.values(statusCodes);
    
    // Gráfico de barras para status HTTP
    if (httpChart) httpChart.destroy();
    httpChart = new Chart(httpCtx, {
        type: 'bar',
        data: {
            labels: httpLabels,
            datasets: [{
                label: 'Quantidade de Links',
                data: httpData,
                backgroundColor: httpLabels.map(status => {
                    if (status === 200) return varToRgba('--success');
                    if (status === 'erro') return varToRgba('--danger');
                    return varToRgba('--warning');
                }),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#a0a0a0' },
                    grid: { color: '#2d2d42' }
                },
                x: {
                    ticks: { color: '#a0a0a0' },
                    grid: { display: false }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// Função auxiliar para converter variáveis CSS em RGBA
function varToRgba(variable, alpha = 1) {
    const hex = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
    let r = 0, g = 0, b = 0;
    
    if (hex.length === 4) {
        r = parseInt(hex[1] + hex[1], 16);
        g = parseInt(hex[2] + hex[2], 16);
        b = parseInt(hex[3] + hex[3], 16);
    } else if (hex.length === 7) {
        r = parseInt(hex[1] + hex[2], 16);
        g = parseInt(hex[3] + hex[4], 16);
        b = parseInt(hex[5] + hex[6], 16);
    }
    
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Atualizar a interface com os dados
// Atualizar a interface com os dados - CORRIGIDO
function updateUI(data) {
    document.getElementById('total-links').textContent = data.totalLinks;
    document.getElementById('status-200').textContent = data.status200;
    document.getElementById('status-error').textContent = data.statusError;
    document.getElementById('last-check').textContent = data.lastCheck;
    document.getElementById('update-time').textContent = new Date().toLocaleString();
    
    // Percentuais JÁ CALCULADOS no backend
    document.getElementById('status-200-percent').textContent = `${data.status200Percent}%`;
    document.getElementById('status-error-percent').textContent = `${data.statusErrorPercent}%`;    
    // Próxima verificação
    const nextCheck = new Date();
    nextCheck.setMinutes(nextCheck.getMinutes() + 5);
    document.getElementById('next-check').textContent = `Próxima: ${nextCheck.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
    
    // Gráficos
    initCharts(data);
    
    // Tabela
    filteredData = [...data.links];
    sortData();
    renderTable();
}

// Renderizar tabela com paginação
function renderTable() {
    const tableBody = document.getElementById('links-table-body');
    tableBody.innerHTML = '';
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredData.length);
    
    for (let i = startIndex; i < endIndex; i++) {
        const link = filteredData[i];
        const row = document.createElement('tr');
        
        const urlCell = document.createElement('td');
        const urlLink = document.createElement('a');
        urlLink.href = link.url;
        urlLink.target = '_blank';
        urlLink.rel = 'noopener noreferrer';
        urlLink.textContent = link.url.length > 50 ? link.url.substring(0, 50) + '...' : link.url;
        urlLink.title = link.url;
        urlLink.classList.add('url-link');
        urlCell.appendChild(urlLink);
        row.appendChild(urlCell);
        
        const statusCell = document.createElement('td');
        const statusBadge = document.createElement('span');
        statusBadge.classList.add('status-badge');
        
        if (link.status === 200) {
            statusBadge.classList.add('status-200');
            statusBadge.textContent = '200 OK';
        } else if (link.status === 'erro') {
            statusBadge.classList.add('status-error');
            statusBadge.textContent = 'Erro';
        } else {
            statusBadge.classList.add('status-other');
            statusBadge.textContent = link.status;
        }
        
        statusCell.appendChild(statusBadge);
        row.appendChild(statusCell);
        
        const layoutCell = document.createElement('td');
        layoutCell.classList.add(link.layoutOk ? 'boolean-true' : 'boolean-false');
        layoutCell.textContent = link.layoutOk ? 'Sim' : 'Não';
        row.appendChild(layoutCell);
        
        const padraoCell = document.createElement('td');
        padraoCell.classList.add(link.padraoOk ? 'boolean-true' : 'boolean-false');
        padraoCell.textContent = link.padraoOk ? 'Sim' : 'Não';
        row.appendChild(padraoCell);
        
        const timeCell = document.createElement('td');
        timeCell.textContent = link.timestamp;
        row.appendChild(timeCell);
        
        tableBody.appendChild(row);
    }
    
    updatePagination();
}

// Atualizar paginação
function updatePagination() {
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);
    const paginationContainer = document.getElementById('pagination');
    
    const prevButton = document.getElementById('prev-page');
    const nextButton = document.getElementById('next-page');
    paginationContainer.innerHTML = '';
    paginationContainer.appendChild(prevButton);
    
    for (let i = 1; i <= totalPages; i++) {
        const pageButton = document.createElement('button');
        pageButton.textContent = i;
        if (i === currentPage) pageButton.classList.add('active');
        pageButton.addEventListener('click', () => { currentPage = i; renderTable(); });
        paginationContainer.appendChild(pageButton);
    }
    
    paginationContainer.appendChild(nextButton);
    prevButton.disabled = currentPage === 1;
    nextButton.disabled = currentPage === totalPages || totalPages === 0;
}

// Ordenar dados
function sortData() {
    filteredData.sort((a, b) => {
        let valueA, valueB;
        switch (sortedBy) {
            case 'url': valueA = a.url.toLowerCase(); valueB = b.url.toLowerCase(); break;
            case 'status': valueA = a.status; valueB = b.status; break;
            case 'layout': valueA = a.layoutOk; valueB = b.layoutOk; break;
            case 'pattern': valueA = a.padraoOk; valueB = b.padraoOk; break;
            case 'timestamp': 
                valueA = new Date(a.timestamp.split(' ')[0].split('/').reverse().join('-') + 'T' + a.timestamp.split(' ')[1]);
                valueB = new Date(b.timestamp.split(' ')[0].split('/').reverse().join('-') + 'T' + b.timestamp.split(' ')[1]);
                break;
            default: valueA = a.url; valueB = b.url;
        }
        if (valueA < valueB) return sortDirection === 'asc' ? -1 : 1;
        if (valueA > valueB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

// Adicionar log
function addLog(message, type = 'info') {
    const logContainer = document.getElementById('log-container');
    if (!logContainer) return;
    
    const logEntry = document.createElement('div');
    logEntry.classList.add('log-entry', `log-${type}`);
    
    const timestamp = new Date().toLocaleTimeString();
    logEntry.textContent = `[${timestamp}] ${message}`;
    
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Exportar dados
async function exportData() {
    try {
        const response = await fetch('/api/export');
        if (!response.ok) throw new Error('Erro ao exportar dados');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `monitoramento_links_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        addLog('Dados exportados com sucesso', 'success');
    } catch (error) {
        console.error('Erro ao exportar dados:', error);
        addLog('Erro ao exportar dados: ' + error.message, 'error');
    }
}

// Buscar logs
async function fetchLogs() {
    try {
        const response = await fetch('/api/logs');
        if (!response.ok) throw new Error('Erro ao buscar logs');
        const data = await response.json();
        
        const logContainer = document.getElementById('log-container');
        if (!logContainer) return;
        
        logContainer.innerHTML = '';
        
        data.logs.forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.classList.add('log-entry', 'log-info');
            logEntry.textContent = log;
            logContainer.appendChild(logEntry);
        });
        logContainer.scrollTop = logContainer.scrollHeight;
    } catch (error) {
        console.error('Erro ao buscar logs:', error);
        addLog('Erro ao carregar logs: ' + error.message, 'error');
    }
}

// ===== FUNÇÕES PARA LOGS EM TEMPO REAL =====

// Conexão WebSocket
const socket = io();

// Configurar WebSocket para receber logs em tempo real
socket.on('log', function(data) {
    addRealtimeLog(data.message, data.level || 'info');
});

// Função para adicionar log em tempo real
function addRealtimeLog(message, level = 'info') {
    const logContainer = document.getElementById('realtime-log-container');
    if (!logContainer) return;
    
    const logEntry = document.createElement('div');
    logEntry.classList.add('realtime-log-entry', level);
    
    const timestamp = new Date().toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    logEntry.textContent = `[${timestamp}] ${message}`;
    
    // Manter TODOS os logs - não remover os antigos
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Função para carregar TODOS os logs existentes
async function loadAllRealtimeLogs() {
    try {
        const response = await fetch('/api/realtime-logs');
        if (!response.ok) throw new Error('Erro ao buscar logs em tempo real');
        const data = await response.json();
        
        const logContainer = document.getElementById('realtime-log-container');
        if (!logContainer) return;
        
        // Limpar apenas se necessário (não há logs)
        if (data.logs.length > 0) {
            logContainer.innerHTML = '';
        }
        
        // Adicionar TODOS os logs
        data.logs.forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.classList.add('realtime-log-entry', log.level || 'info');
            logEntry.textContent = `[${log.timestamp}] ${log.message}`;
            logContainer.appendChild(logEntry);
        });
        
        logContainer.scrollTop = logContainer.scrollHeight;
    } catch (error) {
        console.error('Erro ao carregar logs em tempo real:', error);
        addRealtimeLog('Erro ao carregar logs: ' + error.message, 'error');
    }
}

// No relógio, atualize para:
function updateClock() { 
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    }); 
}

// Configurar botão para mostrar/ocultar logs em tempo real
function setupRealtimeLogsToggle() {
    const toggleButton = document.getElementById('btn-toggle-realtime-logs');
    const logSection = document.getElementById('realtime-logs-section');
    
    if (!toggleButton || !logSection) return;
    
    toggleButton.addEventListener('click', function() {
        const isHidden = logSection.style.display === 'none';
        
        if (isHidden) {
            logSection.style.display = 'block';
            this.innerHTML = '<i class="fas fa-broadcast-tower"></i> Ocultar Logs em Tempo Real';
            // Carregar todos os logs quando mostrar a seção
            loadAllRealtimeLogs();
        } else {
            logSection.style.display = 'none';
            this.innerHTML = '<i class="fas fa-broadcast-tower"></i> Mostrar Logs em Tempo Real';
        }
    });
}

// Configurar botão para limpar logs em tempo real
function setupClearRealtimeLogs() {
    const clearButton = document.getElementById('btn-clear-realtime-logs');
    
    if (!clearButton) return;
    
    clearButton.addEventListener('click', function() {
        const logContainer = document.getElementById('realtime-log-container');
        if (logContainer) {
            logContainer.innerHTML = '';
            addRealtimeLog('Logs limpos', 'info');
        }
    });
}

// Configurar botão para recarregar TODOS os logs
function setupLoadAllLogs() {
    const loadButton = document.getElementById('btn-load-all-logs');
    
    if (!loadButton) return;
    
    loadButton.addEventListener('click', function() {
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Carregando...';
        loadAllRealtimeLogs().finally(() => {
            this.innerHTML = '<i class="fas fa-sync"></i> Recarregar Tudo';
        });
    });
}

// Inicializar funcionalidades de logs em tempo real
function initRealtimeLogs() {
    setupRealtimeLogsToggle();
    setupClearRealtimeLogs();
    setupLoadAllLogs();
    
    // Carregar TODOS os logs ao inicializar
    loadAllRealtimeLogs();
    
    // Adicionar mensagem inicial
    addRealtimeLog('Sistema de logs em tempo real iniciado - Mostrando TODOS os logs', 'info');
}

// ===== INICIALIZAÇÃO =====

document.addEventListener('DOMContentLoaded', function() {
    // Relógio
    function updateClock() { 
        document.getElementById('current-time').textContent = new Date().toLocaleTimeString(); 
    }
    setInterval(updateClock, 1000);
    updateClock();
    
    // Dados iniciais
    fetchData();
    addLog('Sistema de monitoramento inicializado', 'info');
    
    // Botões
    document.getElementById('btn-refresh').addEventListener('click', function() {
        const icon = this.querySelector('i');
        icon.classList.add('refresh-animation');
        this.classList.add('loading');
        addLog('Atualização manual solicitada', 'info');
        fetchData().finally(() => { 
            icon.classList.remove('refresh-animation'); 
            this.classList.remove('loading'); 
        });
    });    
    
    document.getElementById('btn-view-logs').addEventListener('click', function() {
        const logSection = document.getElementById('log-section');
        const isHidden = logSection.style.display === 'none';
        logSection.style.display = isHidden ? 'block' : 'none';
        if (isHidden) fetchLogs();
    });
    
    document.getElementById('btn-clear-logs').addEventListener('click', function() {
        document.getElementById('log-container').innerHTML = '';
        addLog('Logs limpos', 'info');
    });
    
    document.getElementById('btn-export').addEventListener('click', function() {
        addLog('Exportação de dados solicitada', 'info');
        exportData();
    });
    
    // Ordenação
    document.querySelectorAll('.monitor-table th').forEach(header => {
        header.addEventListener('click', () => {
            const newSort = header.getAttribute('data-sort');
            if (sortedBy === newSort) sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            else { sortedBy = newSort; sortDirection = 'asc'; }
            document.querySelectorAll('.monitor-table th i').forEach(icon => icon.className = 'fas fa-sort');
            const icon = header.querySelector('i');
            icon.className = `fas fa-sort-${sortDirection === 'asc' ? 'up' : 'down'}`;
            sortData();
            renderTable();
        });
    });
    
    // Filtro
    document.getElementById('search-input').addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        filteredData = searchTerm ? allData.links.filter(link => 
            link.url.toLowerCase().includes(searchTerm) || 
            link.status.toString().includes(searchTerm) ||
            link.timestamp.toLowerCase().includes(searchTerm)
        ) : [...allData.links];
        currentPage = 1;
        sortData();
        renderTable();
    });
    
    // Paginação
    document.getElementById('prev-page').addEventListener('click', function() { 
        if (currentPage > 1) { currentPage--; renderTable(); } 
    });
    
    document.getElementById('next-page').addEventListener('click', function() { 
        const totalPages = Math.ceil(filteredData.length / itemsPerPage); 
        if (currentPage < totalPages) { currentPage++; renderTable(); } 
    });
    
    // Inicializar logs em tempo real
    initRealtimeLogs();
    
    // Atualizar dados a cada 30s
    setInterval(fetchData, 30000);

    // Atualizar logs automaticamente a cada 5s se a seção estiver visível
    setInterval(() => {
        const logSection = document.getElementById('log-section');
        if (logSection && logSection.style.display !== 'none') fetchLogs();
    }, 5000);
});