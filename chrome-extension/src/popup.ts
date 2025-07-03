import { fetchUserProfile } from './api';
import { loadTranslations, t as translate } from './i18n';
import './styles.css';
import { CONFIG, getBotStartUrl } from './config';

// --- Helper Functions ---
function flattenTranslations(obj: any, prefix = '', res: Record<string, string> = {}) {
  for (const key in obj) {
    const value = obj[key];
    const newKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'string') {
      res[newKey] = value;
    } else if (typeof value === 'object' && value !== null) {
      flattenTranslations(value, newKey, res);
    }
  }
  return res;
}

const t = (key: string, params: Record<string, string> = {}) => translate(key, params);

const app = document.getElementById('app')!;
let currentLang = 'en';

// --- Search Logic Helpers ---

// Helper to flatten the bookmark tree
function flattenBookmarks(nodes: chrome.bookmarks.BookmarkTreeNode[]): chrome.bookmarks.BookmarkTreeNode[] {
  let result: chrome.bookmarks.BookmarkTreeNode[] = [];
  for (const node of nodes) {
    if (node.url) result.push(node);
    if (node.children) result = [...result, ...flattenBookmarks(node.children)];
  }
  return result;
}

// Sets up basic bookmark search functionality
function setupBookmarkSearch(container: HTMLElement) {
  const searchInput = container.querySelector('.search-input') as HTMLInputElement;
  const resultsList = container.querySelector('.results-list') as HTMLUListElement;

  if (!searchInput || !resultsList) {
    console.error('Search input or results list not found for bookmark search setup.');
    return;
  }

  let bookmarks: chrome.bookmarks.BookmarkTreeNode[] = [];

  chrome.bookmarks.getTree((bookmarkTree) => {
    bookmarks = flattenBookmarks(bookmarkTree);
  });

  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase().trim();
    resultsList.innerHTML = '';

    if (!query) {
      return;
    }

    const filtered = bookmarks.filter(
      (bookmark) =>
        bookmark.title.toLowerCase().includes(query) ||
        (bookmark.url && bookmark.url.toLowerCase().includes(query))
    );

    if (filtered.length === 0) {
      const noResults = document.createElement('li');
      noResults.className = 'py-1 px-2 text-gray-500';
      noResults.textContent = t('bookmark_search.no_results');
      resultsList.appendChild(noResults);
    } else {
      filtered.forEach((bookmark) => {
        const li = document.createElement('li');
        const link = document.createElement('a');
        link.href = bookmark.url || '#';
        link.textContent = bookmark.title;
        link.title = bookmark.url || '';
        link.onclick = (e) => {
          e.preventDefault();
          if (bookmark.url) {
            chrome.tabs.create({ url: bookmark.url });
          }
        };
        li.appendChild(link);
        resultsList.appendChild(li);
      });
    }
  });
}

// SVG-иконки (минимальный набор)
function iconSearch() {
  return `<svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`;
}
function iconBookmark() {
  return `<svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>`;
}
function iconGlobe() {
  return `<svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 0 20M12 2a15.3 15.3 0 0 0 0 20"/></svg>`;
}
function iconStar() {
  return `<svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="12 17.27 18.18 21 15.54 13.97 22 9.24 14.81 8.63 12 2 9.19 8.63 2 9.24 8.46 13.97 5.82 21 12 17.27"/></svg>`;
}
function iconExternalLink() {
  return `<svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`;
}
function iconFilter() {
  return `<svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="3 4 21 4 14 14 14 21 10 21 10 14 3 4"/></svg>`;
}
function iconClock() {
  return `<svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
}
function iconAlphabeticalOrder() {
  return `<svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 17h6M3 12h6M3 7h6M21 7l-3 3-3-3"/></svg>`;
}

// Новый современный поиск для подписчиков
function setupUnifiedSearch(container: HTMLElement, userId: string, options?: { onlyBookmarks?: boolean }) {
  // --- State ---
  let searchQuery = '';
  let filterType: 'all' | 'bookmarks' | 'tabs' = options?.onlyBookmarks ? 'bookmarks' : 'all';
  let sortBy: 'date' | 'name' | 'type' = 'date';
  let bookmarks: chrome.bookmarks.BookmarkTreeNode[] = [];
  let tabs: chrome.tabs.Tab[] = [];

  // --- UI ---
  container.innerHTML = '';
  const root = document.createElement('div');
  root.className = 'w-[370px] flex flex-col h-full bg-white rounded-lg shadow-none';

  // Header (поиск)
  const header = document.createElement('div');
  header.className = 'p-2 border-b';
  header.innerHTML = `
    <div class="w-full max-w-sm min-w-[200px]">
      <div class="relative flex items-center">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="absolute w-5 h-5 top-2.5 left-2.5 text-slate-600">
          <path fill-rule="evenodd" d="M10.5 3.75a6.75 6.75 0 1 0 0 13.5 6.75 6.75 0 0 0 0-13.5ZM2.25 10.5a8.25 8.25 0 1 1 14.59 5.28l4.69 4.69a.75.75 0 1 1-1.06 1.06l-4.69-4.69A8.25 8.25 0 0 1 2.25 10.5Z" clip-rule="evenodd"></path>
        </svg>
        <input class="w-full bg-transparent placeholder:text-slate-400 text-slate-700 text-sm border border-slate-200 rounded-md pl-10 pr-3 py-2 transition duration-300 ease focus:outline-none focus:border-slate-400 hover:border-slate-300 shadow-sm focus:shadow search-input" placeholder="${t('bookmark_search.placeholder')}">
      </div>
    </div>
  `;
  root.appendChild(header);

  // Controls (фильтры и сортировка)
  const controls = document.createElement('div');
  controls.className = 'p-2 border-b bg-gray-50';
  controls.innerHTML = `
    <div class="flex items-center justify-between">
      <div class="flex gap-2">
        ${options?.onlyBookmarks ?
          `<button class="filter-btn-bookmarks h-7 text-xs px-2 rounded flex items-center bg-blue-600 text-white">${iconBookmark()}<span class="ml-1">${t('bookmark_search.title')}</span></button>`
          :
          `<button class="filter-btn-all h-7 text-xs px-2 rounded flex items-center">${t('search.all')}</button>
           <button class="filter-btn-bookmarks h-7 text-xs px-2 rounded flex items-center">${iconBookmark()}<span class="ml-1">${t('bookmark_search.title')}</span></button>
           <button class="filter-btn-tabs h-7 text-xs px-2 rounded flex items-center">${iconGlobe()}<span class="ml-1">${t('tab_search.title')}</span></button>`
        }
      </div>
      <div class="relative">
        <button class="sort-btn h-7 px-2 rounded bg-white border flex items-center text-xs">${iconFilter()}<span class="ml-1">${t('search.sort')}</span></button>
        <div class="sort-menu absolute right-0 mt-1 bg-white border rounded shadow-lg z-10 hidden">
          <button class="sort-date flex items-center w-full px-3 py-1 text-left text-xs">${iconClock()}<span class="ml-2">${t('search.sort_recent')}</span></button>
          <button class="sort-name flex items-center w-full px-3 py-1 text-left text-xs">${iconAlphabeticalOrder()}<span class="ml-2">${t('search.sort_name')}</span></button>
          <button class="sort-type flex items-center w-full px-3 py-1 text-left text-xs">${iconFilter()}<span class="ml-2">${t('search.sort_type')}</span></button>
        </div>
      </div>
    </div>
  `;
  root.appendChild(controls);

  // Results + Footer в flex-колонке
  const resultsFooterWrap = document.createElement('div');
  resultsFooterWrap.className = 'flex flex-col flex-1 min-h-0';

  // Results
  const resultsDiv = document.createElement('div');
  resultsDiv.className = 'flex-1 max-h-[400px] overflow-y-auto p-2';
  resultsFooterWrap.appendChild(resultsDiv);

  root.appendChild(resultsFooterWrap);
  container.appendChild(root);

  // Footer (перемещаем после root, перед bottom-content)
  const footer = document.createElement('div');
  footer.className = 'p-2 border-t bg-gray-50 text-center text-xs text-gray-500 mb-0';
  resultsFooterWrap.appendChild(footer);

  // --- Data Fetching ---
  chrome.bookmarks.getTree((tree) => {
    bookmarks = flattenBookmarks(tree);
    renderResults();
  });
  if (!options?.onlyBookmarks) {
    chrome.tabs.query({}).then((t) => {
      tabs = t;
      renderResults();
    });
  }

  // --- Event Handlers ---
  const searchInput = header.querySelector('input') as HTMLInputElement;
  searchInput.addEventListener('input', (e) => {
    searchQuery = searchInput.value;
    renderResults();
  });

  if (!options?.onlyBookmarks) {
    controls.querySelector('.filter-btn-all')!.addEventListener('click', () => {
      filterType = 'all';
      renderResults();
      updateFilterButtons();
    });
    controls.querySelector('.filter-btn-bookmarks')!.addEventListener('click', () => {
      filterType = 'bookmarks';
      renderResults();
      updateFilterButtons();
    });
    controls.querySelector('.filter-btn-tabs')!.addEventListener('click', () => {
      filterType = 'tabs';
      renderResults();
      updateFilterButtons();
    });
  }

  // Сортировка (dropdown)
  const sortBtn = controls.querySelector('.sort-btn')! as HTMLButtonElement;
  const sortMenu = controls.querySelector('.sort-menu')! as HTMLDivElement;
  sortBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    sortMenu.classList.toggle('hidden');
  });
  document.addEventListener('click', () => sortMenu.classList.add('hidden'));
  sortMenu.querySelector('.sort-date')!.addEventListener('click', () => { sortBy = 'date'; renderResults(); });
  sortMenu.querySelector('.sort-name')!.addEventListener('click', () => { sortBy = 'name'; renderResults(); });
  sortMenu.querySelector('.sort-type')!.addEventListener('click', () => { sortBy = 'type'; renderResults(); });

  // После создания элементов, выставляем классы активных кнопок фильтра
  function updateFilterButtons() {
    if (!options?.onlyBookmarks) {
      controls.querySelector('.filter-btn-all')!.className = `filter-btn-all h-7 text-xs px-2 rounded flex items-center ${filterType === 'all' ? 'bg-blue-600 text-white' : 'bg-white border'}`;
      controls.querySelector('.filter-btn-bookmarks')!.className = `filter-btn-bookmarks h-7 text-xs px-2 rounded flex items-center ${filterType === 'bookmarks' ? 'bg-blue-600 text-white' : 'bg-white border'}`;
      controls.querySelector('.filter-btn-tabs')!.className = `filter-btn-tabs h-7 text-xs px-2 rounded flex items-center ${filterType === 'tabs' ? 'bg-blue-600 text-white' : 'bg-white border'}`;
    }
  }
  updateFilterButtons();

  // --- Render Results ---
  function renderResults() {
    let results: Array<any> = [];
    if (options?.onlyBookmarks) {
      results = bookmarks.map((b) => ({ ...b, type: 'bookmark', lastAccessed: b.dateAdded ? new Date(b.dateAdded) : undefined, parentId: b.parentId }));
    } else {
      if (filterType === 'all') {
        results = [
          ...bookmarks.map((b) => ({ ...b, type: 'bookmark', lastAccessed: b.dateAdded ? new Date(b.dateAdded) : undefined, parentId: b.parentId })),
          ...tabs.map((t) => ({ ...t, type: 'tab', lastAccessed: t.lastAccessed ? new Date(t.lastAccessed) : undefined, isActive: t.active }))
        ];
      } else if (filterType === 'bookmarks') {
        results = bookmarks.map((b) => ({ ...b, type: 'bookmark', lastAccessed: b.dateAdded ? new Date(b.dateAdded) : undefined, parentId: b.parentId }));
      } else {
        results = tabs.map((t) => ({ ...t, type: 'tab', lastAccessed: t.lastAccessed ? new Date(t.lastAccessed) : undefined, isActive: t.active }));
      }
    }
    // Фильтрация по поиску
    results = results.filter((result) => {
      const q = searchQuery.toLowerCase();
      return (
        result.title?.toLowerCase().includes(q) ||
        result.url?.toLowerCase().includes(q)
      );
    });
    // Сортировка
    results.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return (a.title || '').localeCompare(b.title || '');
        case 'type':
          return (a.type || '').localeCompare(b.type || '');
        case 'date':
        default:
          return ((b.lastAccessed?.getTime?.() || 0) - (a.lastAccessed?.getTime?.() || 0));
      }
    });

    // Для вкладок: кэшируем url всех закладок для быстрого поиска
    const bookmarkUrls = new Set(bookmarks.map(b => b.url));

    // Рендер
    resultsDiv.innerHTML = '';
    if (results.length === 0) {
      resultsDiv.innerHTML = `
        <div class="p-8 text-center text-gray-400">
          <div class="flex justify-center mb-2">${iconSearch()}</div>
          <p class="text-sm">${t('bookmark_search.no_results')}</p>
          <p class="text-xs mt-1">${t('search.try_changing_query')}</p>
        </div>
      `;
    } else {
      results.forEach((result) => {
        const card = document.createElement('div');
        card.className = 'mb-2 p-3 cursor-pointer hover:bg-gray-100 transition-colors border-0 shadow-none rounded-lg flex items-start gap-3';
        card.onclick = () => {
          if (result.type === 'bookmark' && result.url) {
            chrome.tabs.create({ url: result.url });
          } else if (result.type === 'tab' && result.id) {
            chrome.tabs.update(result.id, { active: true });
            chrome.windows.update(result.windowId, { focused: true });
          }
        };
        // Иконка
        const iconDiv = document.createElement('div');
        iconDiv.className = `flex-shrink-0 p-1.5 rounded ${result.type === 'bookmark' ? 'bg-blue-100 text-blue-600' : 'bg-green-100 text-green-600'}`;
        iconDiv.innerHTML = result.type === 'bookmark' ? iconBookmark() : iconGlobe();
        card.appendChild(iconDiv);
        // Контент
        const contentDiv = document.createElement('div');
        contentDiv.className = 'flex-1 min-w-0';
        // Заголовок и статус
        const titleRow = document.createElement('div');
        titleRow.className = 'flex items-center gap-2 mb-1';
        const title = document.createElement('h3');
        title.className = 'font-medium text-sm truncate flex-1';
        title.textContent = result.title || result.url || '';
        titleRow.appendChild(title);
        if (result.isActive) {
          const badge = document.createElement('span');
          badge.className = 'ml-2 px-2 py-0.5 rounded bg-green-200 text-green-800 text-xs';
          badge.textContent = 'Active';
          titleRow.appendChild(badge);
        }
        contentDiv.appendChild(titleRow);
        // URL
        const urlP = document.createElement('p');
        urlP.className = 'text-xs text-gray-400 truncate mb-1';
        urlP.textContent = result.url || '';
        contentDiv.appendChild(urlP);
        // Дата и кнопки
        const row = document.createElement('div');
        row.className = 'flex items-center justify-between mt-2';
        // --- Бейдж папки и дата ---
        const leftRow = document.createElement('div');
        leftRow.className = 'flex items-center gap-2';
        // Сначала бейдж папки
        if (result.type === 'bookmark' && result.parentId) {
          chrome.bookmarks.get(result.parentId.toString(), (parents) => {
            if (parents && parents[0] && parents[0].title && parents[0].title !== 'Bookmarks bar' && parents[0].title !== 'Закладки') {
              const folderBadge = document.createElement('span');
              folderBadge.className = 'px-2 py-0.5 rounded bg-gray-200 text-gray-700 text-xs';
              folderBadge.textContent = parents[0].title;
              leftRow.appendChild(folderBadge);
            }
            // Потом дата
            if (result.lastAccessed instanceof Date) {
              const dateBadge = document.createElement('span');
              dateBadge.className = 'ml-2 text-xs text-gray-400';
              const now = new Date();
              const diff = (now.getTime() - result.lastAccessed.getTime()) / (1000 * 60 * 60);
              if (diff < 1) dateBadge.textContent = 'Только что';
              else if (diff < 24) dateBadge.textContent = `${Math.floor(diff)}ч назад`;
              else dateBadge.textContent = `${Math.floor(diff / 24)}д назад`;
              leftRow.appendChild(dateBadge);
            }
          });
        } else if (result.type === 'bookmark' && result.lastAccessed instanceof Date) {
          // Если нет папки, просто дата
          const dateBadge = document.createElement('span');
          dateBadge.className = 'text-xs text-gray-400';
          const now = new Date();
          const diff = (now.getTime() - result.lastAccessed.getTime()) / (1000 * 60 * 60);
          if (diff < 1) dateBadge.textContent = 'Только что';
          else if (diff < 24) dateBadge.textContent = `${Math.floor(diff)}ч назад`;
          else dateBadge.textContent = `${Math.floor(diff / 24)}д назад`;
          leftRow.appendChild(dateBadge);
        }
        row.appendChild(leftRow);
        // Кнопки справа
        const btns = document.createElement('div');
        btns.className = 'flex gap-1';
        const favBtn = document.createElement('button');
        favBtn.className = 'h-6 w-6 p-0 opacity-60 hover:opacity-100';
        // --- Логика звезды ---
        if (result.type === 'bookmark') {
          // Закладка: синяя закрашенная звезда
          favBtn.innerHTML = `<svg class="h-4 w-4 text-blue-600" fill="currentColor" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="12 17.27 18.18 21 15.54 13.97 22 9.24 14.81 8.63 12 2 9.19 8.63 2 9.24 8.46 13.97 5.82 21 12 17.27"/></svg>`;
          favBtn.title = 'Удалить из закладок';
          favBtn.onclick = (e) => {
            e.stopPropagation();
            chrome.bookmarks.remove(result.id, () => {
              chrome.bookmarks.getTree((tree) => {
                bookmarks = flattenBookmarks(tree);
                chrome.tabs.query({}).then((t) => {
                  tabs = t;
                  renderResults();
                });
              });
            });
          };
        } else {
          // Вкладка: outline-звезда, если нет в закладках; зелёная закрашенная, если уже есть
          const isBookmarked = bookmarkUrls.has(result.url);
          if (isBookmarked) {
            favBtn.innerHTML = `<svg class="h-4 w-4 text-green-600" fill="currentColor" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="12 17.27 18.18 21 15.54 13.97 22 9.24 14.81 8.63 12 2 9.19 8.63 2 9.24 8.46 13.97 5.82 21 12 17.27"/></svg>`;
            favBtn.title = 'Удалить из закладок';
            favBtn.disabled = false;
            favBtn.onclick = (e) => {
              e.stopPropagation();
              // Находим все закладки с этим url и удаляем их
              const toDelete = bookmarks.filter(b => b.url === result.url);
              let deleted = 0;
              if (toDelete.length === 0) return;
              toDelete.forEach((b, idx) => {
                chrome.bookmarks.remove(b.id, () => {
                  deleted++;
                  if (deleted === toDelete.length) {
                    chrome.bookmarks.getTree((tree) => {
                      bookmarks = flattenBookmarks(tree);
                      chrome.tabs.query({}).then((t) => {
                        tabs = t;
                        renderResults();
                      });
                    });
                  }
                });
              });
            };
          } else {
            favBtn.innerHTML = `<svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="12 17.27 18.18 21 15.54 13.97 22 9.24 14.81 8.63 12 2 9.19 8.63 2 9.24 8.46 13.97 5.82 21 12 17.27"/></svg>`;
            favBtn.title = 'Добавить в закладки';
            favBtn.onclick = (e) => {
              e.stopPropagation();
              chrome.bookmarks.create({ title: result.title, url: result.url }, () => {
                chrome.bookmarks.getTree((tree) => {
                  bookmarks = flattenBookmarks(tree);
                  chrome.tabs.query({}).then((t) => {
                    tabs = t;
                    renderResults();
                  });
                });
              });
            };
          }
        }
        btns.appendChild(favBtn);
        const openBtn = document.createElement('button');
        openBtn.className = 'h-6 w-6 p-0 opacity-60 hover:opacity-100';
        openBtn.innerHTML = iconExternalLink();
        openBtn.title = 'Открыть в новой вкладке';
        openBtn.onclick = (e) => {
          e.stopPropagation();
          if (result.url) chrome.tabs.create({ url: result.url });
        };
        btns.appendChild(openBtn);
        row.appendChild(btns);
        contentDiv.appendChild(row);
        card.appendChild(contentDiv);
        resultsDiv.appendChild(card);
      });
    }
    // Футер
    footer.textContent = getPluralizedFooterText(results.length);
    if (!footer.parentElement) {
      // Вставляем футер после root, если его ещё нет
      root.parentElement?.insertBefore(footer, root.nextSibling);
    }
  }
}

// --- Render Functions for each state ---

/**
 * Рендерит UI для неавторизованного пользователя.
 */
function renderLoggedOutView() {
  app.innerHTML = `<div class="top-content flex-grow flex flex-col"></div><div class="bottom-content"></div>`;
  const searchContainer = app.querySelector('.top-content') as HTMLElement;
  setupUnifiedSearch(searchContainer, 'anonymous', { onlyBookmarks: true });
  const bottom = app.querySelector('.bottom-content') as HTMLElement;
  bottom.innerHTML = `
    <p class="text-sm text-gray-600 text-center mb-2 whitespace-pre-line">${t('login.description')}</p>
    <div id="login-button-container"></div>
  `;
  const loginButtonContainer = document.getElementById('login-button-container');
  if (loginButtonContainer) {
    const loginButton = document.createElement('button');
    loginButton.type = 'button';
    loginButton.className = 'telegram-login-button w-full py-2 px-4 bg-[#0088cc] text-white rounded-lg hover:bg-[#0077b3] transition-colors flex items-center justify-center gap-2';
    // Добавляем иконку Telegram
    const telegramIcon = document.createElement('img');
    telegramIcon.src = chrome.runtime.getURL('icons/telegram.svg');
    telegramIcon.alt = 'Telegram';
    telegramIcon.className = 'w-5 h-5';
    loginButton.appendChild(telegramIcon);
    const span = document.createElement('span');
    span.textContent = t('login.button');
    loginButton.appendChild(span);
    loginButton.onclick = () => {
      const authUrl = `${CONFIG.API.BASE_URL}${CONFIG.API.ENDPOINTS.EXTENSION_AUTH}`;
      window.open(authUrl, 'telegram_auth', 'width=500,height=600,scrollbars=no');
      // Слушаем postMessage с токеном
      function handler(event: MessageEvent) {
        if (event.data?.type === CONFIG.MESSAGES.TELEGRAM_TOKEN && event.data.token) {
          chrome.runtime.sendMessage({ type: CONFIG.MESSAGES.TELEGRAM_TOKEN, token: event.data.token });
          window.removeEventListener('message', handler);
        }
      }
      window.addEventListener('message', handler);
    };
    loginButtonContainer.appendChild(loginButton);
  }
}

/**
 * Рендерит UI для пользователя без активной подписки.
 */
function renderLoggedInNoSubscriptionView(userId: string) {
  app.innerHTML = `<div class="top-content flex-grow flex flex-col"></div><div class="bottom-content"></div>`;
  const searchContainer = app.querySelector('.top-content') as HTMLElement;
  setupUnifiedSearch(searchContainer, userId, { onlyBookmarks: true });
  const bottom = app.querySelector('.bottom-content') as HTMLElement;
  bottom.innerHTML = `
    <p class="text-sm text-gray-600 text-center mb-2 whitespace-pre-line">${t('subscription.description')}</p>
    <button id="subscribe-button" class="telegram-login-button">${t('subscription.subscribe_button')}</button>
    <button id="refresh-status-button" class="w-full mt-2 text-sm text-gray-500 hover:text-gray-700">${t('subscription.refresh_status')}</button>
  `;
  document.getElementById('subscribe-button')!.onclick = () => {
    window.open(`${getBotStartUrl()}?start=subscribe`, '_blank');
  };
  document.getElementById('refresh-status-button')!.onclick = () => {
    window.location.reload();
  };
}

/**
 * Рендерит UI для пользователя с активной подпиской.
 */
function renderLoggedInWithSubscriptionView(userId: string, subscription: any) {
  const endDate = new Date(subscription.end_date);
  const now = new Date();
  const twoWeeksFromNow = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);

  let statusColor = 'bg-red-500'; // неактивна
  if (subscription.active) {
    statusColor = endDate > twoWeeksFromNow ? 'bg-green-500' : 'bg-yellow-500';
  }

  const formattedDate = subscription.active ? endDate.toLocaleDateString() : '';

  app.innerHTML = `
    <div class="top-content flex-grow flex flex-col">
    </div>
    <div class="bottom-content">
      <div class="flex items-center justify-center text-sm text-gray-800">
        <div class="status-circle ${statusColor} mr-2"></div>
        <span>${t(subscription.active ? 'subscription.active' : 'subscription.inactive', { end_date: formattedDate })}</span>
      </div>
    </div>
  `;
  
  const searchContainer = app.querySelector('.top-content');
  if (searchContainer) {
    setupUnifiedSearch(searchContainer as HTMLElement, userId);
  }
}

function getPluralizedFooterText(count: number): string {
  if (currentLang === 'ru') {
    const n = Math.abs(count) % 100;
    const n1 = n % 10;
    if (n > 10 && n < 20) {
      return `${count} ${t('search.results_plural_5')} ${t('search.found_plural')}`;
    }
    if (n1 > 1 && n1 < 5) {
      return `${count} ${t('search.results_plural_2_4')} ${t('search.found_plural')}`;
    }
    if (n1 === 1) {
      return `${count} ${t('search.result_singular')} ${t('search.found_singular')}`;
    }
    return `${count} ${t('search.results_plural_5')} ${t('search.found_plural')}`;
  } else { // en
    return `${count} ${count === 1 ? t('search.result_singular') : t('search.result_plural')} ${t('search.found')}`;
  }
}

// --- Main Initialization Logic ---

async function main() {
  console.log('DOM loaded, initializing extension');
  
  // Используем getAcceptLanguages, чтобы определить предпочитаемый язык контента пользователя
  chrome.i18n.getAcceptLanguages(async (languages) => {
    const lang = languages[0] || 'en'; // Берем самый предпочитаемый язык
    currentLang = lang.startsWith('ru') ? 'ru' : 'en';
    await loadTranslations(lang);

    // Остальная логика инициализации запускается после загрузки переводов
    chrome.storage.local.get([CONFIG.STORAGE.TOKEN], async (result) => {
      console.log('Retrieved token from storage:', result);
      const token = result[CONFIG.STORAGE.TOKEN] || null;

      if (!token) {
        console.log('No token found, rendering logged out view');
        renderLoggedOutView();
        return;
      }

      console.log('Token found, fetching user profile...');
      const user = await fetchUserProfile(token);

      if (!user) {
        console.log('Invalid token, rendering logged out view');
        chrome.storage.local.remove([CONFIG.STORAGE.TOKEN]);
        renderLoggedOutView();
        return;
      }

      console.log('User profile:', user);
      if (user.subscription && user.subscription.active) {
        console.log('Rendering view for user with active subscription');
        renderLoggedInWithSubscriptionView(user.user_id.toString(), user.subscription);
      } else {
        console.log('Rendering view for user with no subscription');
        renderLoggedInNoSubscriptionView(user.user_id.toString());
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', main);

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === CONFIG.MESSAGES.TOKEN_UPDATED) {
    console.log('Token updated, reloading popup...');
    window.location.reload();
  }
}); 