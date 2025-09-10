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
                    labels: {
                        color: '#e6e6e6'
                    }
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
                    ticks: {
                        color: '#a0a0a0'
                    },
                    grid: {
                        color: '#2d2d42'
                    }
                },
                x: {
                    ticks: {
                        color: '#a0a0a0'
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
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

// Função para atualizar a interface com os dados
function updateUI(data) {
    document.getElementById('total-links').textContent = data.totalLinks;
    document.getElementById('status-200').textContent = data.status200;
    document.getElementById('status-error').textContent = data.statusError;
    document.getElementById('last-check').textContent = data.lastCheck;
    document.getElementById('update-time').textContent = new Date().toLocaleString();
    
    // Calcular percentuais
    const successPercent = data.totalLinks > 0 ? Math.round((data.status200 / data.totalLinks) * 100) : 0;
    const errorPercent = data.totalLinks > 0 ? Math.round((data.statusError / data.totalLinks) * 100) : 0;
    
    document.getElementById('status-200-percent').textContent = `${successPercent}%`;
    document.getElementById('status-error-percent').textContent = `${errorPercent}%`;
    
    // Calcular próxima verificação
    const nextCheck = new Date();
    nextCheck.setMinutes(nextCheck.getMinutes() + 5);
    document.getElementById('next-check').textContent = `Próxima: ${nextCheck.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
    
    // Inicializar gráficos
    initCharts(data);
    
    // Atualizar tabela
    filteredData = [...data.links];
    sortData();
    renderTable();
}

// Função para renderizar a tabela com paginação
function renderTable() {
    const tableBody = document.getElementById('links-table-body');
    tableBody.innerHTML = '';
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredData.length);
    
    for (let i = startIndex; i < endIndex; i++) {
        const link = filteredData[i];
        const row = document.createElement('tr');
        
        // URL (agora clicável)
        const urlCell = document.createElement('td');
        const urlLink = document.createElement('a');
        urlLink.href = link.url;
        urlLink.target = '_blank'; // Abre em nova aba
        urlLink.rel = 'noopener noreferrer'; // Segurança
        urlLink.textContent = link.url.length > 50 ? link.url.substring(0, 50) + '...' : link.url;
        urlLink.title = link.url;
        urlLink.classList.add('url-link');
        urlCell.appendChild(urlLink);
        row.appendChild(urlCell);
        
        // Status
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
        
        // Layout OK
        const layoutCell = document.createElement('td');
        layoutCell.classList.add(link.layoutOk ? 'boolean-true' : 'boolean-false');
        layoutCell.textContent = link.layoutOk ? 'Sim' : 'Não';
        row.appendChild(layoutCell);
        
        // Padrão OK
        const padraoCell = document.createElement('td');
        padraoCell.classList.add(link.padraoOk ? 'boolean-true' : 'boolean-false');
        padraoCell.textContent = link.padraoOk ? 'Sim' : 'Não';
        row.appendChild(padraoCell);
        
        // Timestamp
        const timeCell = document.createElement('td');
        timeCell.textContent = link.timestamp;
        row.appendChild(timeCell);
        
        tableBody.appendChild(row);
    }
    
    updatePagination();
}

// Função para atualizar a paginação
function updatePagination() {
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);
    const paginationContainer = document.getElementById('pagination');
    
    // Limpar botões de página, exceto os de navegação
    const prevButton = document.getElementById('prev-page');
    const nextButton = document.getElementById('next-page');
    paginationContainer.innerHTML = '';
    paginationContainer.appendChild(prevButton);
    
    // Adicionar botões de página
    for (let i = 1; i <= totalPages; i++) {
        const pageButton = document.createElement('button');
        pageButton.textContent = i;
        if (i === currentPage) {
            pageButton.classList.add('active');
        }
        pageButton.addEventListener('click', () => {
            currentPage = i;
            renderTable();
        });
        paginationContainer.appendChild(pageButton);
    }
    
    paginationContainer.appendChild(nextButton);
    
    // Atualizar estado dos botões de navegação
    prevButton.disabled = currentPage === 1;
    nextButton.disabled = currentPage === totalPages || totalPages === 0;
}

// Função para ordenar os dados
function sortData() {
    filteredData.sort((a, b) => {
        let valueA, valueB;
        
        switch (sortedBy) {
            case 'url':
                valueA = a.url.toLowerCase();
                valueB = b.url.toLowerCase();
                break;
            case 'status':
                valueA = a.status;
                valueB = b.status;
                break;
            case 'layout':
                valueA = a.layoutOk;
                valueB = b.layoutOk;
                break;
            case 'pattern':
                valueA = a.padraoOk;
                valueB = b.padraoOk;
                break;
            case 'timestamp':
                valueA = new Date(a.timestamp.split(' ').reverse().join('-'));
                valueB = new Date(b.timestamp.split(' ').reverse().join('-'));
                break;
            default:
                valueA = a.url;
                valueB = b.url;
        }
        
        if (valueA < valueB) return sortDirection === 'asc' ? -1 : 1;
        if (valueA > valueB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

// Função para adicionar entradas de log
function addLog(message, type = 'info') {
    const logContainer = document.getElementById('log-container');
    const logEntry = document.createElement('div');
    logEntry.classList.add('log-entry', `log-${type}`);
    
    const timestamp = new Date().toLocaleTimeString();
    logEntry.textContent = `[${timestamp}] ${message}`;
    
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Função para exportar dados
async function exportData() {
    try {
        const response = await fetch('/api/export');
        if (!response.ok) {
            throw new Error('Erro ao exportar dados');
        }
        
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

// Função para buscar logs
async function fetchLogs() {
    try {
        const response = await fetch('/api/logs');
        if (!response.ok) {
            throw new Error('Erro ao buscar logs');
        }
        const data = await response.json();
        
        const logContainer = document.getElementById('log-container');
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

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    // Atualizar relógio
    function updateClock() {
        document.getElementById('current-time').textContent = new Date().toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();
    
    // Carregar dados iniciais
    fetchData();
    addLog('Sistema de monitoramento inicializado', 'info');
    
    // Configurar botões
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
        
        if (isHidden) {
            fetchLogs();
        }
    });
    
    document.getElementById('btn-clear-logs').addEventListener('click', function() {
        document.getElementById('log-container').innerHTML = '';
        addLog('Logs limpos', 'info');
    });
    
    document.getElementById('btn-export').addEventListener('click', function() {
        addLog('Exportação de dados solicitada', 'info');
        exportData();
    });
    
    // Configurar ordenação da tabela
    document.querySelectorAll('.monitor-table th').forEach(header => {
        header.addEventListener('click', () => {
            const newSort = header.getAttribute('data-sort');
            
            if (sortedBy === newSort) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortedBy = newSort;
                sortDirection = 'asc';
            }
            
            // Atualizar ícones de ordenação
            document.querySelectorAll('.monitor-table th i').forEach(icon => {
                icon.className = 'fas fa-sort';
            });
            
            const icon = header.querySelector('i');
            icon.className = `fas fa-sort-${sortDirection === 'asc' ? 'up' : 'down'}`;
            
            sortData();
            renderTable();
        });
    });
    
    // Configurar filtro de busca
    document.getElementById('search-input').addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        
        if (searchTerm) {
            filteredData = allData.links.filter(link => 
                link.url.toLowerCase().includes(searchTerm) || 
                link.status.toString().includes(searchTerm) ||
                link.timestamp.toLowerCase().includes(searchTerm)
            );
        } else {
            filteredData = [...allData.links];
        }
        
        currentPage = 1;
        sortData();
        renderTable();
    });
    
    // Configurar paginação
    document.getElementById('prev-page').addEventListener('click', function() {
        if (currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });
    
    document.getElementById('next-page').addEventListener('click', function() {
        const totalPages = Math.ceil(filteredData.length / itemsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            renderTable();
        }
    });
    
    // Atualizar dados a cada 30 segundos
    setInterval(fetchData, 30000);
});