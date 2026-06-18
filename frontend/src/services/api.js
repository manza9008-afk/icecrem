import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL + '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Helper functions
export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(amount || 0);
};

export const formatNumber = (num, decimals = 2) => {
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num || 0);
};

export const formatDate = (dateStr, format = 'DD-MM-YYYY') => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  
  if (format === 'DD-MM-YYYY') return `${day}-${month}-${year}`;
  if (format === 'YYYY-MM-DD') return `${year}-${month}-${day}`;
  return dateStr;
};

export const getTodayDate = () => {
  const now = new Date();
  return now.toISOString().split('T')[0];
};

export const getFinancialYear = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  
  if (month >= 4) {
    return `${year}-${(year + 1).toString().slice(2)}`;
  }
  return `${year - 1}-${year.toString().slice(2)}`;
};

export const getItemSizeLabel = (item) => {
  if (!item) return '';
  return item.print_name || item.alternate_unit || item.unit || '';
};
