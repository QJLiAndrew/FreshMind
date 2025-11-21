import axios from 'axios';
import Config from './constants/Config';


const api = axios.create({
  baseURL: Config.API_URL,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
  timeout: 10000,
});

export default api;