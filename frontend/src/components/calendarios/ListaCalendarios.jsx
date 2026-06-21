import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import './ListaCalendarios.css'; // Archivo de estilos separado

const API_LISTA_CALENDARIOS = "http://localhost:8000/api/v1/auth/lista-calendarios";
const API_BUSCAR_HUECOS = "http://localhost:8000/api/v1/auth/buscar-huecos";

const SeleccionCalendarios = () => {
    const [searchParams] = useSearchParams();
    const userEmail = searchParams.get("email") || "";

    // Estados
    const [misCalendarios, setMisCalendarios] = useState([]);
    const [calendariosSeleccionados, setCalendariosSeleccionados] = useState([]);
    const [duracion, setDuracion] = useState(30);
    const [rangoDias, setRangoDias] = useState(30);
    const [loadingLogs, setLoadingLogs] = useState(true);
    const [loadingAlgoritmo, setLoadingAlgoritmo] = useState(false);
    const [resultado, setResultado] = useState(null);

    // Carga los calendarios de Google en tiempo real
    useEffect(() => {
        const cargarCalendariosReales = async () => {
            if (!userEmail) return;
            try {
                const { data } = await axios.get(`${API_LISTA_CALENDARIOS}?email=${userEmail}`);
                setMisCalendarios(data);
            } catch (error) {
                console.error("Error cargando calendarios:", error);
                alert(error.response?.data?.detail || "No se pudieron cargar tus calendarios de Google.");
            } finally {
                setLoadingLogs(false);
            }
        };

        cargarCalendariosReales();
    }, [userEmail]);

    const handleCheckboxChange = (id) => {
        if (calendariosSeleccionados.includes(id)) {
            setCalendariosSeleccionados(calendariosSeleccionados.filter(item => item !== id));
        } else {
            setCalendariosSeleccionados([...calendariosSeleccionados, id]);
        }
    };

    const handleBuscarHuecos = async (e) => {
        e.preventDefault();
        if (calendariosSeleccionados.length === 0) {
            alert("Por favor, selecciona al menos un calendario.");
            return;
        }

        setLoadingAlgoritmo(true);
        setResultado(null);

        const payload = {
            email: userEmail,
            calendarios_ids: calendariosSeleccionados,
            duracion: parseInt(duracion),
            rango_dias: parseInt(rangoDias)
        };

        try {
            const { data } = await axios.post(API_BUSCAR_HUECOS, payload);
            setResultado(data);
        } catch (error) {
            console.error("Error al buscar huecos:", error);
            alert(error.response?.data?.detail || "Error en el servidor.");
        } finally {
            setLoadingAlgoritmo(false);
        }
    };

    return (
        <div className="scheduler-page-container">
            <div className="scheduler-card">
                <h2 className="scheduler-title">Smart Scheduler IA</h2>
                <p className="scheduler-subtitle">Cruza tus agendas configurando los parámetros de tu reunión</p>
                
                <div className="scheduler-user-badge">
                    <span>Usuario activo:</span> <strong>{userEmail}</strong>
                </div>

                {loadingLogs ? (
                    <div className="scheduler-loader-container">
                        <div className="scheduler-spinner"></div>
                        <p>Sincronizando tus calendarios de Google...</p>
                    </div>
                ) : (
                    <form onSubmit={handleBuscarHuecos} className="scheduler-form">
                        
                        {/* SECCIÓN CALENDARIOS */}
                        <div className="scheduler-section">
                            <label className="scheduler-section-title">1. Selecciona tus calendarios:</label>
                            <div className="scheduler-checkbox-list">
                                {misCalendarios.length === 0 ? (
                                    <p className="scheduler-empty-msg">No se encontraron calendarios activos.</p>
                                ) : (
                                    misCalendarios.map((cal) => (
                                        <label key={cal.id} className={`scheduler-checkbox-item ${calendariosSeleccionados.includes(cal.id) ? 'checked' : ''}`}>
                                            <input
                                                type="checkbox"
                                                checked={calendariosSeleccionados.includes(cal.id)}
                                                onChange={() => handleCheckboxChange(cal.id)}
                                            />
                                            <span className="custom-checkbox"></span>
                                            <span className="calendar-name">{cal.nombre}</span>
                                        </label>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* SECCIÓN SELECTORES */}
                        <div className="scheduler-grid-fields">
                            <div className="scheduler-field-group">
                                <label>Duración del evento</label>
                                <select value={duracion} onChange={(e) => setDuracion(e.target.value)}>
                                    <option value="15">15 minutos</option>
                                    <option value="30">30 minutos</option>
                                    <option value="45">45 minutos</option>
                                    <option value="60">60 minutos</option>
                                </select>
                            </div>

                            <div className="scheduler-field-group">
                                <label>Rango de búsqueda</label>
                                <select value={rangoDias} onChange={(e) => setRangoDias(e.target.value)}>
                                    <option value="7">Próximos 7 días</option>
                                    <option value="15">Próximos 15 días</option>
                                    <option value="30">Próximos 30 días</option>
                                </select>
                            </div>
                        </div>

                        {/* BOTÓN CON ESTILO DEL DE GOOGLE */}
                        <button type="submit" className="scheduler-submit-btn" disabled={loadingAlgoritmo}>
                            {loadingAlgoritmo ? "Procesando Agendas..." : "Optimizar Reunión con IA"}
                        </button>
                    </form>
                )}

                {/* CUADRO DE RESULTADO DE LA IA */}
                {resultado && (
                    <div className="scheduler-result-card">
                        <div className="result-header">
                            <span className="result-icon">⚡</span>
                            <h4>Análisis de Disponibilidad Listo</h4>
                        </div>
                        <pre className="result-json">{JSON.stringify(resultado, null, 2)}</pre>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SeleccionCalendarios;