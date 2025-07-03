import { CONFIG } from './config';

// Обработка установки расширения
chrome.runtime.onInstalled.addListener(() => {
  console.log(`${CONFIG.EXTENSION.NAME} extension installed`);
});

// Синхронизация токена Telegram между окнами/попапом
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Background received message:', message);
  if (message.type === CONFIG.MESSAGES.TELEGRAM_TOKEN && message.token) {
    chrome.storage.local.set({ [CONFIG.STORAGE.TOKEN]: message.token }, () => {
      console.log('Token saved in background:', message.token);
      sendResponse({ success: true });
      chrome.runtime.sendMessage({ type: CONFIG.MESSAGES.TOKEN_UPDATED });
      console.log('Sent token_updated message');
    });
    return true; // для асинхронного sendResponse
  }
});

// Здесь больше не нужно обрабатывать сообщения LOGIN или открывать Telegram Login
