import { CONFIG, getApiUrl } from './config';

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

// Обработчик для Telegram Login Widget
function onTelegramAuth(user: any) {
  console.log('Telegram auth callback received:', user);
  
  fetch(getApiUrl(CONFIG.API.ENDPOINTS.TELEGRAM_AUTH), {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(user)
  })
  .then(r => {
    console.log('Auth response status:', r.status);
    return r.json();
  })
  .then(data => {
    console.log('Auth response data:', data);
    if (data.token) {
      chrome.storage.local.set({ [CONFIG.STORAGE.TOKEN]: data.token }, () => {
        console.log('Token saved, reloading extension');
        chrome.runtime.reload();
      });
    } else {
      console.error('No token in response:', data);
      alert('Ошибка авторизации: ' + (data.detail || 'Неизвестная ошибка'));
    }
  })
  .catch(error => {
    console.error('Auth request failed:', error);
    alert('Ошибка авторизации: ' + error.message);
  });
}

// @ts-ignore
window.onTelegramAuth = onTelegramAuth; 