import { t } from '../i18n';
import { CONFIG } from '../config';

export function initTelegramLoginButton(container: HTMLElement) {
  container.innerHTML = '';
  const loginButton = document.createElement('button');
  loginButton.type = 'button';
  loginButton.className = 'telegram-login-button w-full py-2 px-4 bg-[#0088cc] text-white rounded-lg hover:bg-[#0077b3] transition-colors flex items-center justify-center gap-2';
  loginButton.textContent = t('login.button', {});
  loginButton.onclick = () => {
    // Открываем внешнюю страницу авторизации
    const authUrl = `${CONFIG.API.BASE_URL}${CONFIG.API.ENDPOINTS.EXTENSION_AUTH}`;
    const win = window.open(authUrl, 'telegram_auth', 'width=500,height=600');
    // Слушаем postMessage с токеном
    function handler(event: MessageEvent) {
      if (event.data?.type === CONFIG.MESSAGES.TELEGRAM_TOKEN && event.data.token) {
        chrome.runtime.sendMessage({ type: CONFIG.MESSAGES.TELEGRAM_TOKEN, token: event.data.token });
        window.removeEventListener('message', handler);
        if (win) win.close();
      }
    }
    window.addEventListener('message', handler);
  };
  container.appendChild(loginButton);
}
