// Константы расширения FindMyLink
export const STORAGE_KEYS = {
  TOKEN: 'findmylink_token',
  USER_ID: 'findmylink_user_id',
  TOKEN_EXPIRY: 'findmylink_token_expiry',
  LANGUAGE: 'findmylink_language',
  SETTINGS: 'findmylink_settings',
} as const;

export const MESSAGE_TYPES = {
  TELEGRAM_TOKEN: 'telegram_token',
  TOKEN_UPDATED: 'token_updated',
  LOGIN: 'LOGIN',
  LOGOUT: 'LOGOUT',
} as const;

export const API_ENDPOINTS = {
  PROFILE: '/api/v1/profile',
  SUBSCRIPTION: '/api/v1/subscription',
  APPLY_PROMO: '/api/v1/apply_promo',
  TELEGRAM_AUTH: '/api/v1/auth/telegram',
  TELEGRAM_LOGIN: '/api/v1/telegram-login',
  TELEGRAM_CALLBACK: '/api/v1/telegram-callback',
  EXTENSION_AUTH: '/extension-auth',
} as const;

export const UI_CONSTANTS = {
  POPUP_WIDTH: 400,
  POPUP_HEIGHT: 600,
  MAX_SEARCH_RESULTS: 50,
  DEBOUNCE_DELAY: 300,
  SUCCESS_DURATION: 3000,
  ERROR_DURATION: 5000,
} as const;

export const SEARCH_CONSTANTS = {
  MIN_QUERY_LENGTH: 2,
  MAX_QUERY_LENGTH: 100,
  HIGHLIGHT_CLASS: 'findmylink-highlight',
} as const;

export const BOT_CONSTANTS = {
  NAME: 'FindMyLink Bot',
  USERNAME: '@findmlbot',
  DESCRIPTION: 'Бот для управления закладками и поиска по вкладкам',
  TELEGRAM_WIDGET_NAME: 'findmlbot',
} as const;

export const EXTENSION_CONSTANTS = {
  NAME: 'FindMyLink',
  VERSION: '1.0.0',
  DESCRIPTION: 'Расширение для поиска по закладкам и вкладкам',
} as const;

export const API_HEADERS = {
  CONTENT_TYPE: 'Content-Type',
} as const;

// Типы для констант
export type StorageKeys = typeof STORAGE_KEYS;
export type MessageTypes = typeof MESSAGE_TYPES;
export type ApiEndpoints = typeof API_ENDPOINTS;
export type UiConstants = typeof UI_CONSTANTS;
export type SearchConstants = typeof SEARCH_CONSTANTS;
export type BotConstants = typeof BOT_CONSTANTS;
export type ExtensionConstants = typeof EXTENSION_CONSTANTS;
