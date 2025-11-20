import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'https://denna-eisteddfodic-subpolygonally.ngrok-free.dev/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
  timeout: 10000,
});

export default api;