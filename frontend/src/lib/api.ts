export const getApiBaseUrl = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  if (typeof window === 'undefined') {
    return baseUrl.replace('localhost', 'backend');
  }
  return baseUrl;
};

export const API_BASE_URL = getApiBaseUrl();

class ApiClient {
  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    // In a real app, this should be more robust
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }
    
    return headers;
  }

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }

    async post<T>(endpoint: string, data: any): Promise<T> {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      });
  
      return this.handleResponse<T>(response);
    }
  
    async put<T>(endpoint: string, data: any): Promise<T> {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      });
  
      return this.handleResponse<T>(response);
    }

  // Handle x-www-form-urlencoded (for OAuth2 login)
  async postForm<T>(endpoint: string, data: Record<string, string>): Promise<T> {
    const formHeaders: Record<string, string> = {};
    
    // In a real app, this should be more robust
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        formHeaders['Authorization'] = `Bearer ${token}`;
      }
    }
    formHeaders['Content-Type'] = 'application/x-www-form-urlencoded';
    
    const formData = new URLSearchParams();
    for (const [key, value] of Object.entries(data)) {
      formData.append(key, value);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: formHeaders,
      body: formData.toString(),
    });

    return this.handleResponse<T>(response);
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      // Token expiration / 401 handling could go here
      if (response.status === 401 && typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        // Optional: redirect to login or attempt refresh
      }
      
      const error = data && data.detail ? data.detail : response.statusText;
      throw new Error(typeof error === 'string' ? error : JSON.stringify(error));
    }

    return data as T;
  }
}

export const api = new ApiClient();
