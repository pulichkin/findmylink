import { t } from '../i18n';

interface Tab {
  id?: number;
  title?: string;
  url?: string;
}

export function initTabSearch(userId: string, translations: any): void {
  const container = document.createElement('div');
  container.className = 'tab-search mb-4';
  
  // Создаем заголовок
  const title = document.createElement('h2');
  title.className = 'text-lg font-semibold';
  title.textContent = t('tab_search.title');
  container.appendChild(title);

  // Создаем поле поиска
  const searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.className = 'w-full p-2 border rounded mt-2';
  searchInput.placeholder = t('tab_search.placeholder');
  container.appendChild(searchInput);

  // Создаем список результатов
  const resultsList = document.createElement('ul');
  resultsList.className = 'mt-2 max-h-48 overflow-y-auto';
  container.appendChild(resultsList);

  // Добавляем контейнер на страницу
  const searchContainer = document.getElementById('tab-search-container');
  if (searchContainer) {
    searchContainer.appendChild(container);
  }

  // Обработчик поиска
  searchInput.addEventListener('input', async () => {
    const query = searchInput.value.toLowerCase();
    
    // Получаем все вкладки
    const tabs = await chrome.tabs.query({});
    const filtered = tabs.filter(
      (tab) =>
        tab.title?.toLowerCase().includes(query) ||
        tab.url?.toLowerCase().includes(query)
    );

    // Очищаем список
    resultsList.innerHTML = '';

    if (query && filtered.length === 0) {
      const noResults = document.createElement('li');
      noResults.className = 'py-1';
      noResults.textContent = t('tab_search.no_results');
      resultsList.appendChild(noResults);
    } else {
      filtered.forEach((tab) => {
        const li = document.createElement('li');
        li.className = 'flex justify-between items-center py-1';

        const link = document.createElement('a');
        link.href = '#';
        link.className = 'text-blue-600 hover:underline truncate';
        link.textContent = tab.title || tab.url || '';
        link.onclick = () => {
          if (tab.id) {
            chrome.tabs.update(tab.id, { active: true });
            chrome.windows.update(tab.windowId, { focused: true });
          }
        };

        li.appendChild(link);
        resultsList.appendChild(li);
      });
    }
  });
} 