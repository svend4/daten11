// ===== State Management =====
const state = {
    currentFilePath: null,
    currentPage: 1,
    itemsPerPage: 12,
    totalResults: 0,
    currentView: 'grid',
    theme: localStorage.getItem('theme') || 'light',
    searchResults: null,
    facets: null
};

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadFacets();
    performSearch();
    setupEventListeners();
});

function setupEventListeners() {
    // Search input with debounce
    const searchInput = document.getElementById('searchInput');
    let searchTimeout;

    searchInput.addEventListener('input', (e) => {
        const clearBtn = document.querySelector('.clear-btn');
        if (e.target.value) {
            clearBtn.classList.remove('hidden');
        } else {
            clearBtn.classList.add('hidden');
        }

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            if (e.target.value.length >= 2 || e.target.value.length === 0) {
                performSearch();
            }
        }, 500);
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // Filter changes
    document.getElementById('categoryFilter').addEventListener('change', performSearch);
    document.getElementById('typeFilter').addEventListener('change', performSearch);
    document.getElementById('sortFilter')?.addEventListener('change', performSearch);
}

// ===== Theme Toggle =====
function initTheme() {
    if (state.theme === 'dark') {
        document.body.classList.add('dark-theme');
        document.querySelector('.sun-icon').classList.add('hidden');
        document.querySelector('.moon-icon').classList.remove('hidden');
    }
}

function toggleTheme() {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    document.body.classList.toggle('dark-theme');

    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    sunIcon.classList.toggle('hidden');
    moonIcon.classList.toggle('hidden');

    localStorage.setItem('theme', state.theme);
    showToast(`Тема изменена на ${state.theme === 'dark' ? 'тёмную' : 'светлую'}`, 'info');
}

// ===== Facets Loading =====
async function loadFacets() {
    try {
        const response = await fetch('/api/facets');
        const facets = await response.json();
        state.facets = facets;

        displayCategories(facets.categories);
        displayTags(facets.tags);
        displayFileTypes(facets.fileTypes);

        // Populate filter dropdowns
        populateFilterDropdown('categoryFilter', facets.categories);
        populateFilterDropdown('typeFilter', facets.fileTypes);

    } catch (error) {
        console.error('Error loading facets:', error);
        showToast('Ошибка загрузки фасетов', 'error');
    }
}

function displayCategories(categories) {
    const container = document.getElementById('categoriesFacet');
    container.innerHTML = '';

    const sortedCategories = Object.entries(categories)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    sortedCategories.forEach(([category, count]) => {
        const item = document.createElement('div');
        item.className = 'facet-item';
        item.onclick = () => filterByCategory(category);
        item.innerHTML = `
            <span class="facet-name">${category || 'Без категории'}</span>
            <span class="facet-count">${count}</span>
        `;
        container.appendChild(item);
    });
}

function displayTags(tags) {
    const container = document.getElementById('tagsFacet');
    container.innerHTML = '';

    const sortedTags = Object.entries(tags)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 20);

    sortedTags.forEach(([tag, count]) => {
        const item = document.createElement('span');
        item.className = 'tag-item';
        item.onclick = () => filterByTag(tag);
        item.textContent = tag;
        item.title = `${count} документов`;
        container.appendChild(item);
    });
}

function displayFileTypes(types) {
    const container = document.getElementById('typesFacet');
    container.innerHTML = '';

    const sortedTypes = Object.entries(types)
        .sort((a, b) => b[1] - a[1]);

    sortedTypes.forEach(([type, count]) => {
        const item = document.createElement('div');
        item.className = 'facet-item';
        item.onclick = () => filterByType(type);
        item.innerHTML = `
            <span class="facet-name">${getFileTypeIcon(type)} ${type || 'Без расширения'}</span>
            <span class="facet-count">${count}</span>
        `;
        container.appendChild(item);
    });
}

function getFileTypeIcon(type) {
    const icons = {
        '.pdf': '📄',
        '.txt': '📝',
        '.md': '📋',
        '.docx': '📘',
        '.jpg': '🖼️',
        '.png': '🖼️',
        '.mp4': '🎬',
        '.mp3': '🎵'
    };
    return icons[type] || '📎';
}

function populateFilterDropdown(selectId, items) {
    const select = document.getElementById(selectId);
    const currentValue = select.value;

    // Clear except first option
    while (select.options.length > 1) {
        select.remove(1);
    }

    // Add options
    Object.keys(items).sort().forEach(item => {
        const option = document.createElement('option');
        option.value = item;
        option.textContent = item;
        select.appendChild(option);
    });

    // Restore selection if exists
    if (currentValue) {
        select.value = currentValue;
    }
}

// ===== Search =====
async function performSearch() {
    const query = document.getElementById('searchInput').value;
    const category = document.getElementById('categoryFilter').value;
    const type = document.getElementById('typeFilter').value;

    showLoading();

    try {
        let url = '/api/search?';
        if (query) url += `q=${encodeURIComponent(query)}&`;
        if (category) url += `category=${encodeURIComponent(category)}&`;
        if (type) url += `type=${encodeURIComponent(type)}&`;

        const response = await fetch(url);
        const results = await response.json();

        state.searchResults = results;
        state.totalResults = (results.files?.length || 0) + (results.folders?.length || 0);

        displayResults(results);
        updateResultsCount();

    } catch (error) {
        console.error('Error performing search:', error);
        showToast('Ошибка поиска', 'error');
        document.getElementById('results').innerHTML = `
            <div class="loading-state">
                <p>❌ Ошибка загрузки результатов</p>
            </div>
        `;
    }
}

function showLoading() {
    document.getElementById('results').innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Поиск документов...</p>
        </div>
    `;
}

function displayResults(results) {
    const container = document.getElementById('results');
    container.innerHTML = '';

    const allItems = [
        ...(results.folders || []).map(f => ({...f, type: 'folder'})),
        ...(results.files || []).map(f => ({...f, type: 'file'}))
    ];

    if (allItems.length === 0) {
        container.innerHTML = `
            <div class="loading-state">
                <p>🔍 Ничего не найдено</p>
                <p style="font-size: 0.875rem; margin-top: 0.5rem;">Попробуйте изменить поисковый запрос</p>
            </div>
        `;
        return;
    }

    // Pagination
    const startIdx = (state.currentPage - 1) * state.itemsPerPage;
    const endIdx = startIdx + state.itemsPerPage;
    const paginatedItems = allItems.slice(startIdx, endIdx);

    paginatedItems.forEach(item => {
        const card = createItemCard(item);
        container.appendChild(card);
    });

    updatePagination(allItems.length);
}

function createItemCard(item) {
    const card = document.createElement('div');
    card.className = 'file-card';

    if (item.type === 'folder') {
        card.innerHTML = `
            <div class="file-icon">📁</div>
            <div class="file-title">${item.name}</div>
            <div class="file-description">${item.description || 'Нет описания'}</div>
            ${item.tags ? `<div class="file-tags">${item.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}</div>` : ''}
            <div class="file-meta">
                <span>📂 Папка</span>
                ${item.statistics ? `<span>📄 ${item.statistics.totalFiles} файлов</span>` : ''}
            </div>
        `;
    } else {
        card.onclick = () => showFileDetails(item._path + '/' + item.filename);
        card.innerHTML = `
            <div class="file-icon">${getFileTypeIcon(item.fileType)}</div>
            <div class="file-title">${item.title || item.filename}</div>
            <div class="file-description">${item.description || 'Нет описания'}</div>
            ${item.tags ? `<div class="file-tags">${item.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}</div>` : ''}
            <div class="file-meta">
                <span>${item.fileType || 'unknown'}</span>
                ${item.category ? `<span>${item.category}</span>` : ''}
            </div>
        `;
    }

    return card;
}

function updateResultsCount() {
    document.getElementById('resultsCount').textContent =
        `Найдено: ${state.totalResults} ${getPlural(state.totalResults, 'документ', 'документа', 'документов')}`;
}

function getPlural(n, one, few, many) {
    n = Math.abs(n) % 100;
    const n1 = n % 10;
    if (n > 10 && n < 20) return many;
    if (n1 > 1 && n1 < 5) return few;
    if (n1 === 1) return one;
    return many;
}

// ===== Filters =====
function toggleFilters() {
    const content = document.querySelector('.filters-content');
    const btn = document.querySelector('.toggle-filters');
    content.classList.toggle('collapsed');
    btn.classList.toggle('active');
}

function filterByCategory(category) {
    document.getElementById('categoryFilter').value = category;
    performSearch();
    highlightFacet('categoriesFacet', category);
}

function filterByTag(tag) {
    document.getElementById('searchInput').value = tag;
    performSearch();
}

function filterByType(type) {
    document.getElementById('typeFilter').value = type;
    performSearch();
    highlightFacet('typesFacet', type);
}

function highlightFacet(facetId, value) {
    const facet = document.getElementById(facetId);
    facet.querySelectorAll('.facet-item').forEach(item => {
        item.classList.remove('active');
        if (item.querySelector('.facet-name').textContent.includes(value)) {
            item.classList.add('active');
        }
    });
}

function resetFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('categoryFilter').value = '';
    document.getElementById('typeFilter').value = '';
    document.querySelector('.clear-btn')?.classList.add('hidden');
    performSearch();
    showToast('Фильтры сброшены', 'info');
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    document.querySelector('.clear-btn').classList.add('hidden');
    performSearch();
}

// ===== View Toggle =====
function changeView(view) {
    state.currentView = view;
    const results = document.getElementById('results');
    const viewBtns = document.querySelectorAll('.view-btn');

    if (view === 'list') {
        results.classList.add('list-view');
    } else {
        results.classList.remove('list-view');
    }

    viewBtns.forEach(btn => {
        if (btn.dataset.view === view) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// ===== File Details Modal =====
async function showFileDetails(filePath) {
    state.currentFilePath = filePath;

    try {
        const response = await fetch(`/api/file/${encodeURIComponent(filePath)}`);
        const data = await response.json();

        document.getElementById('modalTitle').textContent = data.file;

        // Info tab
        const infoTab = document.getElementById('tab-info');
        infoTab.innerHTML = createInfoContent(data.metadata);

        // Summary tab
        const summaryTab = document.getElementById('tab-summary');
        summaryTab.innerHTML = data.summary ?
            `<div class="prose">${marked(data.summary)}</div>` :
            '<p class="loading-state">Краткое содержание отсутствует</p>';

        // TOC tab
        const tocTab = document.getElementById('tab-toc');
        tocTab.innerHTML = data.toc ?
            `<div class="prose">${marked(data.toc)}</div>` :
            '<p class="loading-state">Оглавление отсутствует</p>';

        showModal('fileModal');

    } catch (error) {
        console.error('Error loading file details:', error);
        showToast('Ошибка загрузки деталей файла', 'error');
    }
}

function createInfoContent(metadata) {
    if (!metadata) return '<p>Метаданные отсутствуют</p>';

    let html = '<div class="info-grid" style="display: grid; gap: 1rem;">';

    if (metadata.description) {
        html += `<div><strong>Описание:</strong><p>${metadata.description}</p></div>`;
    }

    if (metadata.author) {
        html += `<div><strong>Автор:</strong> ${metadata.author}</div>`;
    }

    if (metadata.category) {
        html += `<div><strong>Категория:</strong> ${metadata.category}</div>`;
    }

    if (metadata.language) {
        html += `<div><strong>Язык:</strong> ${metadata.language}</div>`;
    }

    if (metadata.tags && metadata.tags.length > 0) {
        html += `<div><strong>Теги:</strong><div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;">
            ${metadata.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
        </div></div>`;
    }

    if (metadata.keywords && metadata.keywords.length > 0) {
        html += `<div><strong>Ключевые слова:</strong><p>${metadata.keywords.join(', ')}</p></div>`;
    }

    if (metadata.created) {
        html += `<div><strong>Создан:</strong> ${new Date(metadata.created).toLocaleString('ru-RU')}</div>`;
    }

    if (metadata.updated) {
        html += `<div><strong>Обновлён:</strong> ${new Date(metadata.updated).toLocaleString('ru-RU')}</div>`;
    }

    if (metadata.size) {
        html += `<div><strong>Размер:</strong> ${formatFileSize(metadata.size)}</div>`;
    }

    html += '</div>';
    return html;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Simple markdown parser (basic)
function marked(text) {
    return text
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*)\*/gim, '<em>$1</em>')
        .replace(/\n$/gim, '<br />');
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.closest('.tab').classList.add('active');

    // Update tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const modal = document.getElementById('fileModal');
    modal.classList.remove('show');
    document.body.style.overflow = 'auto';
}

function closeModalOnBackdrop(event) {
    if (event.target.classList.contains('modal')) {
        closeModal();
    }
}

function downloadFile() {
    if (state.currentFilePath) {
        window.location.href = `/download/${encodeURIComponent(state.currentFilePath)}`;
        showToast('Загрузка файла началась', 'success');
    }
}

// ===== Stats Modal =====
async function showStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        const content = document.getElementById('statsContent');
        content.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${stats.total_files}</div>
                <div class="stat-label">Файлов</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.total_folders}</div>
                <div class="stat-label">Папок</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${formatFileSize(stats.total_size)}</div>
                <div class="stat-label">Общий размер</div>
            </div>
        `;

        showModal('statsModal');

    } catch (error) {
        console.error('Error loading stats:', error);
        showToast('Ошибка загрузки статистики', 'error');
    }
}

function closeStatsModal() {
    const modal = document.getElementById('statsModal');
    modal.classList.remove('show');
    document.body.style.overflow = 'auto';
}

// ===== Pagination =====
function updatePagination(totalItems) {
    const totalPages = Math.ceil(totalItems / state.itemsPerPage);
    const pagination = document.getElementById('pagination');

    if (totalPages <= 1) {
        pagination.classList.add('hidden');
        return;
    }

    pagination.classList.remove('hidden');

    const pageNumbers = document.getElementById('pageNumbers');
    pageNumbers.innerHTML = '';

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= state.currentPage - 2 && i <= state.currentPage + 2)) {
            const pageBtn = document.createElement('button');
            pageBtn.className = 'page-number';
            pageBtn.textContent = i;
            if (i === state.currentPage) pageBtn.classList.add('active');
            pageBtn.onclick = () => goToPage(i);
            pageNumbers.appendChild(pageBtn);
        } else if (pageNumbers.lastChild?.textContent !== '...') {
            const dots = document.createElement('span');
            dots.textContent = '...';
            dots.style.padding = '0 0.5rem';
            pageNumbers.appendChild(dots);
        }
    }
}

function goToPage(page) {
    state.currentPage = page;
    displayResults(state.searchResults);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function prevPage() {
    if (state.currentPage > 1) {
        goToPage(state.currentPage - 1);
    }
}

function nextPage() {
    const totalPages = Math.ceil(state.totalResults / state.itemsPerPage);
    if (state.currentPage < totalPages) {
        goToPage(state.currentPage + 1);
    }
}

// ===== Toast Notifications =====
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div style="flex: 1;">${message}</div>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; cursor: pointer; color: var(--text-tertiary);">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z"/>
            </svg>
        </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===== Keyboard Shortcuts =====
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('searchInput').focus();
    }

    // Escape to close modal
    if (e.key === 'Escape') {
        closeModal();
        closeStatsModal();
    }
});
