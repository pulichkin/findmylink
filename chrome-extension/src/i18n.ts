import enTranslations from '../locales/en.json';
import ruTranslations from '../locales/ru.json';

interface Translations {
  [key: string]: string | Translations;
}

let translations: Translations = {};

export async function loadTranslations(lang: string): Promise<Translations> {
  try {
    console.log('Loading translations for language:', lang);
    translations = lang.startsWith('ru') ? ruTranslations : enTranslations;
    console.log('Loaded translations:', translations);
    return translations;
  } catch (error) {
    console.error('Failed to load translations:', error);
    translations = enTranslations;
    console.log('Loaded fallback translations:', translations);
    return translations;
  }
}

export function t(key: string, params: Record<string, string> = {}): string {
  const keys = key.split('.');
  let value: any = translations;
  
  for (const k of keys) {
    value = value?.[k];
    if (value === undefined) {
      console.warn(`Translation key not found: ${key}`);
      return key;
    }
  }
  
  if (typeof value !== 'string') {
    console.warn(`Translation value is not a string for key: ${key}`);
    return key;
  }
  
  return value.replace(/\{(\w+)\}/g, (_, param) => params[param] || `{${param}}`);
} 