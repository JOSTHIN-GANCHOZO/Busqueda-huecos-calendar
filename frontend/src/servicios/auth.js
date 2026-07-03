// src/services/authService.js
import api from './api.js';

export const authService = {
  // Función para obtener la URL de Google
  getGoogleAuthUrl: async () => {
    try {
      const { data } = await api.get('/auth/login');
      
      if (!data?.auth_url) {
        throw new Error("No se recibió la URL de autenticación.");
      }
      
      return data.auth_url;
    } catch (error) {
      // Formateamos el error aquí para que el componente no tenga que lidiar con axios
      const mensajeError = error.response?.data?.detail || "No fue posible conectar con Google. Intenta nuevamente.";
      throw new Error(mensajeError);
    }
  },
};