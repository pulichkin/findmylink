import { t } from '../i18n';
import { CONFIG, getApiUrl, getBotStartUrl } from '../config';

interface Subscription {
  user_id: number;
  end_date: string;
  active: boolean;
}

export async function initSubscriptionStatus(
  userId: string,
  translations: any
): Promise<boolean> {
  const container = document.createElement('div');
  container.className = 'subscription-status mb-4';

  // Создаем контейнер для статуса
  const statusContainer = document.createElement('div');
  statusContainer.className = 'subscription-status flex flex-col items-center gap-2 p-4 bg-gray-50 rounded-lg mb-4';

  // Добавляем текст статуса
  const statusText = document.createElement('div');
  statusText.className = 'text-sm text-gray-600 text-center';
  statusContainer.appendChild(statusText);

  // Добавляем описание подписки
  const descriptionText = document.createElement('p');
  descriptionText.className = 'text-sm text-gray-600 text-center whitespace-pre-line';
  descriptionText.textContent = t('subscription.description');
  statusContainer.appendChild(descriptionText);

  // Если пользователь анонимный, показываем кнопку подписки
  if (userId === 'anonymous') {
    statusText.textContent = t('subscription.inactive');

    const subscribeButton = document.createElement('button');
    subscribeButton.type = 'button';
    subscribeButton.className = 'telegram-login-button w-full py-2 px-4 bg-[#0088cc] text-white rounded-lg hover:bg-[#0077b3] transition-colors flex items-center justify-center gap-2';
    subscribeButton.textContent = t('subscription.subscribe_button');

    // Добавляем иконку Telegram
    const telegramIcon = document.createElement('img');
    telegramIcon.src = chrome.runtime.getURL('icons/telegram.svg');
    telegramIcon.alt = 'Telegram';
    telegramIcon.className = 'w-5 h-5';
    subscribeButton.prepend(telegramIcon);

    subscribeButton.onclick = () => {
      window.open(`${getBotStartUrl()}?start=subscribe`, '_blank');
    };
    statusContainer.appendChild(subscribeButton);

    container.appendChild(statusContainer);

    // Добавляем контейнер на страницу
    const statusWrapper = document.getElementById('subscription-status-container');
    if (statusWrapper) {
      statusWrapper.appendChild(container);
    }

    return false;
  }

  try {
    const response = await fetch(getApiUrl(`${CONFIG.API.ENDPOINTS.SUBSCRIPTION}/${userId}`));
    const subscription: Subscription = await response.json();

    if (subscription.active) {
      statusText.textContent = t('subscription.active', {
        end_date: new Date(subscription.end_date).toLocaleDateString()
      });
      statusText.className = 'text-green-600 font-medium';

      container.appendChild(statusContainer);

      // Добавляем контейнер на страницу
      const statusWrapper = document.getElementById('subscription-status-container');
      if (statusWrapper) {
        statusWrapper.appendChild(container);
      }

      return true;
    } else {
      statusText.textContent = t('subscription.inactive');

      const subscribeButton = document.createElement('button');
      subscribeButton.type = 'button';
      subscribeButton.className = 'telegram-login-button w-full py-2 px-4 bg-[#0088cc] text-white rounded-lg hover:bg-[#0077b3] transition-colors flex items-center justify-center gap-2';
      subscribeButton.textContent = t('subscription.subscribe_button');

      // Добавляем иконку Telegram
      const telegramIcon = document.createElement('img');
      telegramIcon.src = chrome.runtime.getURL('icons/telegram.svg');
      telegramIcon.alt = 'Telegram';
      telegramIcon.className = 'w-5 h-5';
      subscribeButton.prepend(telegramIcon);

      subscribeButton.onclick = () => {
        window.open(`${getBotStartUrl()}?start=subscribe`, '_blank');
      };
      statusContainer.appendChild(subscribeButton);

      // Кнопка обновления статуса
      const refreshButton = document.createElement('button');
      refreshButton.type = 'button';
      refreshButton.className = 'telegram-login-button w-full mt-2 bg-gray-400 hover:bg-gray-500';
      refreshButton.textContent = 'Обновить статус';
      refreshButton.onclick = () => {
        const statusWrapper = document.getElementById('subscription-status-container');
        if (statusWrapper) statusWrapper.innerHTML = '';
        initSubscriptionStatus(userId, translations);
      };
      statusContainer.appendChild(refreshButton);

      container.appendChild(statusContainer);

      // Добавляем контейнер на страницу
      const statusWrapper = document.getElementById('subscription-status-container');
      if (statusWrapper) {
        statusWrapper.appendChild(container);
      }

      return false;
    }
  } catch (error) {
    console.error('Error fetching subscription status:', error);
    statusText.textContent = t('subscription.inactive');

    const subscribeButton = document.createElement('button');
    subscribeButton.type = 'button';
    subscribeButton.className = 'telegram-login-button w-full py-2 px-4 bg-[#0088cc] text-white rounded-lg hover:bg-[#0077b3] transition-colors flex items-center justify-center gap-2';
    subscribeButton.textContent = t('subscription.subscribe_button');

    // Добавляем иконку Telegram
    const telegramIcon = document.createElement('img');
    telegramIcon.src = chrome.runtime.getURL('icons/telegram.svg');
    telegramIcon.alt = 'Telegram';
    telegramIcon.className = 'w-5 h-5';
    subscribeButton.prepend(telegramIcon);

    subscribeButton.onclick = () => {
      window.open(`${getBotStartUrl()}?start=subscribe`, '_blank');
    };
    statusContainer.appendChild(subscribeButton);

    // Кнопка обновления статуса
    const refreshButton = document.createElement('button');
    refreshButton.type = 'button';
    refreshButton.className = 'telegram-login-button w-full mt-2 bg-gray-400 hover:bg-gray-500';
    refreshButton.textContent = 'Обновить статус';
    refreshButton.onclick = () => {
      const statusWrapper = document.getElementById('subscription-status-container');
      if (statusWrapper) statusWrapper.innerHTML = '';
      initSubscriptionStatus(userId, translations);
    };
    statusContainer.appendChild(refreshButton);

    container.appendChild(statusContainer);

    // Добавляем контейнер на страницу
    const statusWrapper = document.getElementById('subscription-status-container');
    if (statusWrapper) {
      statusWrapper.appendChild(container);
    }

    return false;
  }
}
