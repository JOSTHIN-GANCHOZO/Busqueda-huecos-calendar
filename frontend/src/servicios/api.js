// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1', // Tu URL base
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;