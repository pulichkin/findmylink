import { CONFIG, getApiUrl, getAuthHeaders } from './config';

interface UserProfile {
  user_id: number;
  subscription?: {
    end_date: string;
    active: boolean;
    trial_used?: boolean;
    auto_renewal?: boolean;
  };
}

interface PromoRequest {
  promo_code: string;
  user_id: number;
}

interface PromoResponse {
  message: string;
}

// Общие заголовки для всех API запросов
const getHeaders = (token?: string) => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
};

export async function fetchUserProfile(token: string): Promise<UserProfile | null> {
  console.log('Fetching user profile with token:', token);
  try {
    const res = await fetch(getApiUrl(CONFIG.API.ENDPOINTS.PROFILE), {
      headers: getAuthHeaders(token)
    });
    console.log('Profile API response status:', res.status);
    
    if (res.status === 401) {
      console.error('Unauthorized access - invalid token');
      return null;
    }
    
    if (res.status === 403) {
      console.error('Access denied - unauthorized client');
      return null;
    }
    
    if (res.status === 429) {
      console.error('Rate limit exceeded');
      return null;
    }
    
    if (!res.ok) {
      console.error('Profile API error:', await res.text());
      return null;
    }
    
    const data = await res.json();
    console.log('Profile API response data:', data);
    return data;
  } catch (error) {
    console.error('Profile API request failed:', error);
    return null;
  }
}

export async function applyPromoCode(token: string, promoCode: string): Promise<PromoResponse | null> {
  console.log('Applying promo code:', promoCode);
  try {
    const res = await fetch(getApiUrl(CONFIG.API.ENDPOINTS.APPLY_PROMO), {
      method: 'POST',
      headers: getAuthHeaders(token),
      body: JSON.stringify({
        promo_code: promoCode
      })
    });
    
    console.log('Promo API response status:', res.status);
    
    if (res.status === 401) {
      console.error('Unauthorized access - invalid token');
      return null;
    }
    
    if (res.status === 403) {
      console.error('Access denied - unauthorized client');
      return null;
    }
    
    if (res.status === 429) {
      console.error('Rate limit exceeded');
      return null;
    }
    
    if (!res.ok) {
      console.error('Promo API error:', await res.text());
      return null;
    }
    
    const data = await res.json();
    console.log('Promo API response data:', data);
    return data;
  } catch (error) {
    console.error('Promo API request failed:', error);
    return null;
  }
}

export async function getSubscription(token: string): Promise<any> {
  console.log('Fetching subscription');
  try {
    const res = await fetch(getApiUrl(CONFIG.API.ENDPOINTS.SUBSCRIPTION), {
      headers: getAuthHeaders(token)
    });
    
    console.log('Subscription API response status:', res.status);
    
    if (res.status === 401) {
      console.error('Unauthorized access - invalid token');
      return null;
    }
    
    if (res.status === 403) {
      console.error('Access denied - unauthorized client');
      return null;
    }
    
    if (res.status === 429) {
      console.error('Rate limit exceeded');
      return null;
    }
    
    if (!res.ok) {
      console.error('Subscription API error:', await res.text());
      return null;
    }
    
    const data = await res.json();
    console.log('Subscription API response data:', data);
    return data;
  } catch (error) {
    console.error('Subscription API request failed:', error);
    return null;
  }
}
 