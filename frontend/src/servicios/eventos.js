import api from './api';

export const eventosService = {
    // 1. Obtiene la lista de calendarios del usuario
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

    // 2. Obtiene eventos ocupados en un rango de fechas para la vista de calendario
    obtenerEventosCalendario: async (payload) => {
        try {
            const { data } = await api.post('/auth/eventos-calendario', payload);
            return data;
        } catch (error) {
            const mensaje = error.response?.data?.detail || "No se pudieron cargar los eventos del calendario.";
            throw new Error(mensaje);
        }
    }
};