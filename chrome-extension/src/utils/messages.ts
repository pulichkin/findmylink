import { CONFIG } from '../config';

// Утилиты для работы с сообщениями между компонентами расширения
export class MessageManager {
  // Отправить сообщение в background script
  static async sendToBackground(message: any): Promise<any> {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(message, resolve);
    });
  }

  // Отправить токен Telegram
  static async sendTelegramToken(token: string): Promise<void> {
    await this.sendToBackground({
      type: CONFIG.MESSAGES.TELEGRAM_TOKEN,
      token
    });
  }

  // Уведомить об обновлении токена
  static async notifyTokenUpdated(): Promise<void> {
    await this.sendToBackground({
      type: CONFIG.MESSAGES.TOKEN_UPDATED
    });
  }

  // Слушать сообщения
  static addMessageListener(callback: (message: any, sender: any, sendResponse: any) => void): void {
    chrome.runtime.onMessage.addListener(callback);
  }

  // Удалить слушатель сообщений
  static removeMessageListener(callback: (message: any, sender: any, sendResponse: any) => void): void {
    chrome.runtime.onMessage.removeListener(callback);
  }
}

// Утилиты для работы с postMessage
export class PostMessageManager {
  // Отправить сообщение в окно
  static sendToWindow(window: Window, message: any): void {
    window.postMessage(message, '*');
  }

  // Отправить токен в окно
  static sendTokenToWindow(window: Window, token: string): void {
    this.sendToWindow(window, {
      type: CONFIG.MESSAGES.TELEGRAM_TOKEN,
      token
    });
  }

  // Слушать postMessage
  static addPostMessageListener(callback: (event: MessageEvent) => void): void {
    window.addEventListener('message', callback);
  }

  // Удалить слушатель postMessage
  static removePostMessageListener(callback: (event: MessageEvent) => void): void {
    window.removeEventListener('message', callback);
  }
} 