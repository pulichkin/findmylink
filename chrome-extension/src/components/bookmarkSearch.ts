import { t } from '../i18n';

interface BookmarkTreeNode {
  id: string;
  title: string;
  url?: string;
  children?: BookmarkTreeNode[];
}

export function initBookmarkSearch(
  hasSubscription: boolean,
  userId: string,
  translations: any
): void {
  const container = document.createElement('div');
  container.className = 'bookmark-search mb-4';
  
  // Создаем заголовок
  const title = document.createElement('h2');
  title.className = 'text-lg font-semibold';
  title.textContent = t('bookmark_search.title');
  container.appendChild(title);

  // Создаем поле поиска
  const searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.className = 'w-full p-2 border rounded mt-2';
  searchInput.placeholder = t('bookmark_search.placeholder');
  container.appendChild(searchInput);

  // Создаем список результатов
  const resultsList = document.createElement('ul');
  resultsList.className = 'mt-2 max-h-48 overflow-y-auto';
  container.appendChild(resultsList);

  // Добавляем контейнер на страницу
  const searchContainer = document.getElementById('bookmark-search-container');
  if (searchContainer) {
    searchContainer.appendChild(container);
  }

  let bookmarks: BookmarkTreeNode[] = [];

  // Загружаем закладки
  chrome.bookmarks.getTree((bookmarkTree) => {
    bookmarks = flattenBookmarks(bookmarkTree);
  });

  // Обработчик поиска
  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase();
    const filtered = bookmarks.filter(
      (bookmark) =>
        bookmark.title.toLowerCase().includes(query) ||
        (bookmark.url && bookmark.url.toLowerCase().includes(query))
    );

    // Очищаем список
    resultsList.innerHTML = '';

    if (query && filtered.length === 0) {
      const noResults = document.createElement('li');
      noResults.className = 'py-1';
      noResults.textContent = t('bookmark_search.no_results');
      resultsList.appendChild(noResults);
    } else {
      filtered.forEach((bookmark) => {
        const li = document.createElement('li');
        li.className = 'flex justify-between items-center py-1';

        const link = document.createElement('a');
        link.href = '#';
        link.className = 'text-blue-600 hover:underline truncate';
        link.textContent = bookmark.title;
        link.onclick = () => {
          if (bookmark.url) {
            chrome.tabs.create({ url: bookmark.url });
          }
        };

        li.appendChild(link);

        if (hasSubscription) {
          const deleteButton = document.createElement('button');
          deleteButton.className = 'text-red-600 hover:text-red-800 ml-2';
          deleteButton.textContent = '✕';
          deleteButton.title = t('bookmark_search.delete_tooltip');
          deleteButton.onclick = async () => {
            try {
              await chrome.bookmarks.remove(bookmark.id);
              bookmarks = bookmarks.filter((b) => b.id !== bookmark.id);
              searchInput.dispatchEvent(new Event('input'));
            } catch (error) {
              console.error('Error deleting bookmark:', error);
            }
          };
          li.appendChild(deleteButton);
        }

        resultsList.appendChild(li);
      });
    }
  });
}

function flattenBookmarks(nodes: BookmarkTreeNode[]): BookmarkTreeNode[] {
  let result: BookmarkTreeNode[] = [];
  for (const node of nodes) {
    if (node.url) result.push(node);
    if (node.children) result = [...result, ...flattenBookmarks(node.children)];
  }
  return result;
} 