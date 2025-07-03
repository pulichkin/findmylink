import {
  STORAGE_KEYS,
  MESSAGE_TYPES,
  API_ENDPOINTS,
  UI_CONSTANTS,
  SEARCH_CONSTANTS,
  BOT_CONSTANTS,
  EXTENSION_CONSTANTS,
  API_HEADERS
} from './constants';

// Конфигурация расширения FindMyLink
export const CONFIG = {
  // Название и информация о боте
  BOT: BOT_CONSTANTS,

  // API настройки
  API: {
    BASE_URL: 'https://findmylink.ru',
    ENDPOINTS: API_ENDPOINTS,
    HEADERS: API_HEADERS,
  },

  // Настройки расширения
  EXTENSION: EXTENSION_CONSTANTS,

  // Настройки авторизации
  AUTH: {
    TOKEN_KEY: STORAGE_KEYS.TOKEN,
    USER_ID_KEY: STORAGE_KEYS.USER_ID,
    EXPIRY_KEY: STORAGE_KEYS.TOKEN_EXPIRY,
  },

  // Настройки UI
  UI: UI_CONSTANTS,

  // Настройки поиска
  SEARCH: SEARCH_CONSTANTS,

  // Настройки уведомлений
  NOTIFICATIONS: {
    SUCCESS_DURATION: UI_CONSTANTS.SUCCESS_DURATION,
    ERROR_DURATION: UI_CONSTANTS.ERROR_DURATION,
  },

  // Настройки сообщений
  MESSAGES: MESSAGE_TYPES,

  // Настройки хранилища
  STORAGE: STORAGE_KEYS,
} as const;

// Типы для конфигурации
export type Config = typeof CONFIG;
export type BotConfig = Config['BOT'];
export type ApiConfig = Config['API'];
export type ExtensionConfig = Config['EXTENSION'];
export type AuthConfig = Config['AUTH'];
export type UiConfig = Config['UI'];
export type SearchConfig = Config['SEARCH'];
export type NotificationsConfig = Config['NOTIFICATIONS'];
export type MessagesConfig = Config['MESSAGES'];
export type StorageConfig = Config['STORAGE'];

// Вспомогательные функции для работы с конфигом
export const getApiUrl = (endpoint: string): string => {
  return `${CONFIG.API.BASE_URL}${endpoint}`;
};

export const getAuthHeaders = (token?: string): Record<string, string> => {
  const headers: Record<string, string> = {
    [CONFIG.API.HEADERS.CONTENT_TYPE]: CONFIG.API.HEADERS.CONTENT_TYPE,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
};

export const getBotUrl = (): string => {
  return `https://t.me/${CONFIG.BOT.USERNAME.replace('@', '')}`;
};

export const getBotStartUrl = (): string => {
  return `${getBotUrl()}?start=extension`;
};
