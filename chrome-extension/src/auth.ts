import { CONFIG, getApiUrl, getBotStartUrl } from './config';

export async function initAuth() {
  console.log('initAuth called');
  
  // Часть 1: Обработка нажатия на кнопку входа.
  // Этот код выполняется на странице auth.html перед перенаправлением в Telegram.
  const loginButton = document.getElementById('loginButton');
  console.log('Login button found:', !!loginButton);
  
  if (loginButton) {
    loginButton.addEventListener('click', function(e) {
      console.log('Login button clicked');
      e.preventDefault();
      const extensionId = chrome.runtime.id;
      console.log('Extension ID:', extensionId);
      // URL, на который Telegram перенаправит пользователя после авторизации
      const extUrl = `chrome-extension://${extensionId}/auth.html`;
      console.log('Extension URL:', extUrl);
      // URL нашего бэкенда, который инициирует процесс входа
      const callbackUrl = `${CONFIG.API.BASE_URL}/api/v1/telegram-callback?ext=${encodeURIComponent(extUrl)}`;
      console.log('Callback URL:', callbackUrl);
      const authUrl = `${CONFIG.API.BASE_URL}/api/v1/telegram-login?callback=${encodeURIComponent(callbackUrl)}`;
      console.log('Auth URL:', authUrl);
      window.location.href = authUrl;
    });
  }

  // Универсальный парсер параметров
  function getAllParams(): Record<string, string> {
    const params = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const all: Record<string, string> = {};
    for (const [k, v] of params.entries()) all[k] = v;
    for (const [k, v] of hashParams.entries()) all[k] = v;
    return all;
  }

  const allParams = getAllParams();
  console.log('All params:', allParams);

  if (allParams['hash']) {
    try {
      const response = await fetch(getApiUrl(CONFIG.API.ENDPOINTS.TELEGRAM_AUTH), {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(allParams)
      });
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Backend error response:', errorText);
        throw new Error(`Server returned ${response.status}: ${errorText}`);
      }
      const result = await response.json();
      if (result.token) {
        console.log('Received token from backend. Saving...');
        chrome.storage.local.set({ [CONFIG.STORAGE.TOKEN]: result.token }, () => {
          console.log('Token saved. Reloading extension to apply changes.');
          // Перезагружаем все расширение, чтобы главный popup обновился.
          chrome.runtime.reload();
        });
      } else {
        console.error('Backend did not return a token.', result.error || result);
      }
    } catch (error) {
      console.error('Error during Telegram auth verification:', error);
    }
  } else {
    console.log('No hash found in URL params, this is initial auth page load');
  }
}

export async function initiateTelegramAuth(): Promise<string> {
  const extUrl = chrome.runtime.getURL('');
  const callbackUrl = `${CONFIG.API.BASE_URL}/api/v1/telegram-callback?ext=${encodeURIComponent(extUrl)}`;
  const authUrl = `${CONFIG.API.BASE_URL}/api/v1/telegram-login?callback=${encodeURIComponent(callbackUrl)}`;
  
  return authUrl;
}

export async function handleTelegramAuth(authData: string): Promise<{ token: string; user_id: number } | null> {
  try {
    const response = await fetch(getApiUrl(CONFIG.API.ENDPOINTS.TELEGRAM_AUTH), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Добавляем auth_data как query параметр
    });

    if (!response.ok) {
      console.error('Telegram auth failed:', response.status);
      return null;
    }

    const data = await response.json();
    return {
      token: data.token,
      user_id: data.user_id
    };
  } catch (error) {
    console.error('Telegram auth error:', error);
    return null;
  }
} 