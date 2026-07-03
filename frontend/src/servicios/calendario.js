// src/servicios/calendario.js
import api from './api';

export const calendarioService = {
    // 1. Carga los calendarios de Google usando el email
    obtenerCalendarios: async (email) => {
        try {
            const { data } = await api.get('/auth/lista-calendarios', {
                params: { email }
            });
            return data;
        } catch (error) {
            const mensaje = error.response?.data?.detail || "No se pudieron cargar tus calendarios de Google.";
            throw new Error(mensaje);
        }
    },

    // 2. Envía los parámetros elegidos para que la IA busque los huecos libres
    buscarHuecos: async (payload) => {
        try {
            const { data } = await api.post('/auth/buscar-huecos', payload);
            return data;
        } catch (error) {
            const mensaje = error.response?.data?.detail || "Error en el servidor al buscar huecos.";
            throw new Error(mensaje);
        }
    }
};