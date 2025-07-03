import { CONFIG } from '../config';

// Утилиты для работы с хранилищем Chrome
export class StorageManager {
  // Получить токен из хранилища
  static async getToken(): Promise<string | null> {
    return new Promise((resolve) => {
      chrome.storage.local.get([CONFIG.STORAGE.TOKEN], (result) => {
        resolve(result[CONFIG.STORAGE.TOKEN] || null);
      });
    });
  }

  // Сохранить токен в хранилище
  static async setToken(token: string): Promise<void> {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [CONFIG.STORAGE.TOKEN]: token }, resolve);
    });
  }

  // Удалить токен из хранилища
  static async removeToken(): Promise<void> {
    return new Promise((resolve) => {
      chrome.storage.local.remove([CONFIG.STORAGE.TOKEN], resolve);
    });
  }

  // Получить ID пользователя из хранилища
  static async getUserId(): Promise<string | null> {
    return new Promise((resolve) => {
      chrome.storage.local.get([CONFIG.STORAGE.USER_ID], (result) => {
        resolve(result[CONFIG.STORAGE.USER_ID] || null);
      });
    });
  }

  // Сохранить ID пользователя в хранилище
  static async setUserId(userId: string): Promise<void> {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [CONFIG.STORAGE.USER_ID]: userId }, resolve);
    });
  }

  // Получить язык из хранилища
  static async getLanguage(): Promise<string> {
    return new Promise((resolve) => {
      chrome.storage.local.get([CONFIG.STORAGE.LANGUAGE], (result) => {
        resolve(result[CONFIG.STORAGE.LANGUAGE] || 'en');
      });
    });
  }

  // Сохранить язык в хранилище
  static async setLanguage(language: string): Promise<void> {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [CONFIG.STORAGE.LANGUAGE]: language }, resolve);
    });
  }

  // Получить настройки из хранилища
  static async getSettings(): Promise<Record<string, any>> {
    return new Promise((resolve) => {
      chrome.storage.local.get([CONFIG.STORAGE.SETTINGS], (result) => {
        resolve(result[CONFIG.STORAGE.SETTINGS] || {});
      });
    });
  }

  // Сохранить настройки в хранилище
  static async setSettings(settings: Record<string, any>): Promise<void> {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [CONFIG.STORAGE.SETTINGS]: settings }, resolve);
    });
  }

  // Очистить все данные расширения
  static async clearAll(): Promise<void> {
    return new Promise((resolve) => {
      chrome.storage.local.clear(resolve);
    });
  }
} 