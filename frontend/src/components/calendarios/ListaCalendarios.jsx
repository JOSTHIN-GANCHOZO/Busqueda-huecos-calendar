import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import { calendarioService } from "../../servicios/calendario";
import { eventosService } from "../../servicios/eventos";
import "./ListaCalendarios.css";

const ListaCalendarios = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const userEmail = searchParams.get("email") || "";

    const [misCalendarios, setMisCalendarios] = useState([]);
    const [calendariosSeleccionados, setCalendariosSeleccionados] = useState([]);
    const [duracion, setDuracion] = useState(30);
    const [rangoDias, setRangoDias] = useState(30);

    const [loadingCalendarios, setLoadingCalendarios] = useState(true);
    const [loadingAlgoritmo, setLoadingAlgoritmo] = useState(false);
    const [cargandoEventos, setCargandoEventos] = useState(false);

    const [fechaActual, setFechaActual] = useState(new Date());
    const [eventos, setEventos] = useState([]);
    const [huecosRecomendados, setHuecosRecomendados] = useState([]);

    // Modal
    const [modalAbierto, setModalAbierto] = useState(false);
    const [huecoSeleccionado, setHuecoSeleccionado] = useState(null);
    const [tituloReunionModal, setTituloReunionModal] = useState("");

    const eventosHuecos = huecosRecomendados.map((hueco, index) => ({
        id: `hueco-${index}`,
        title: hueco.title || "Hueco disponible",
        start: hueco.start,
        end: hueco.end,
        color: "#108981",
        textColor: "#fff",
        extendedProps: { hueco }
    }));

    const eventosConHuecos = [...eventos, ...eventosHuecos];

    // Cargar calendarios
    useEffect(() => {
        const cargarCalendarios = async () => {
            if (!userEmail) {
                setLoadingCalendarios(false);
                return;
            }
            try {
                const data = await calendarioService.obtenerCalendarios(userEmail);
                setMisCalendarios(data);
            } catch (error) {
                console.error(error);
                alert(error.message);
            } finally {
                setLoadingCalendarios(false);
            }
        };
        cargarCalendarios();
    }, [userEmail]);

    // Cargar eventos
    useEffect(() => {
        const cargarEventos = async () => {
            if (!userEmail || calendariosSeleccionados.length === 0) {
                setEventos([]);
                return;
            }
            setCargandoEventos(true);
            try {
                const inicio = new Date(fechaActual);
                inicio.setHours(0, 0, 0, 0);
                const fin = new Date(fechaActual);
                fin.setDate(fin.getDate() + 30);
                fin.setHours(23, 59, 59, 999);

                const respuesta = await eventosService.obtenerEventosCalendario({
                    email: userEmail,
                    calendarios_ids: calendariosSeleccionados,
                    fecha_inicio: inicio.toISOString(),
                    fecha_fin: fin.toISOString()
                });

                const eventosGoogle = respuesta.eventos.map(evento => ({
                    id: evento.id,
                    title: evento.title,
                    start: evento.start,
                    end: evento.end,
                    color: "#4F46E5",
                    borderColor: "#4F46E5",
                    textColor: "#ffffff",
                    extendedProps: { calendarId: evento.calendar_id }
                }));

                setEventos(eventosGoogle);
            } catch (error) {
                console.error(error);
                alert(error.message);
            } finally {
                setCargandoEventos(false);
            }
        };
        cargarEventos();
    }, [userEmail, calendariosSeleccionados, fechaActual]);

    const handleCheckboxChange = (id) => {
        if (calendariosSeleccionados.includes(id)) {
            setCalendariosSeleccionados(calendariosSeleccionados.filter(cal => cal !== id));
        } else {
            setCalendariosSeleccionados([...calendariosSeleccionados, id]);
        }
    };

    const handleBuscarHuecos = async (e) => {
        e.preventDefault();
        if (calendariosSeleccionados.length === 0) {
            alert("Seleccione al menos un calendario.");
            return;
        }
        setLoadingAlgoritmo(true);
        setHuecosRecomendados([]);
        try {
            const respuesta = await calendarioService.buscarHuecos({
                email: userEmail,
                calendarios_ids: calendariosSeleccionados,
                duracion: Number(duracion),
                rango_dias: Number(rangoDias),
                titulo: "Reunión"
            });
            if (respuesta.huecos_recomendados.length === 0) {
                alert("No se encontraron huecos disponibles.");
                return;
            }
            setHuecosRecomendados(respuesta.huecos_recomendados);
        } catch (error) {
            console.error(error);
            alert(error.message);
        } finally {
            setLoadingAlgoritmo(false);
        }
    };

    const handleHuecoClick = (hueco) => {
        setHuecoSeleccionado(hueco);
        setTituloReunionModal("Reunión");
        setModalAbierto(true);
    };

    const handleConfirmarReunion = () => {
        alert(`Reunión "${tituloReunionModal}" programada para el ${new Date(huecoSeleccionado.inicio).toLocaleString()}`);
        setModalAbierto(false);
    };

    const handleDateChange = (info) => {
        setFechaActual(info.start);
    };

    const handleLogout = () => {
        navigate('/');
    };

    if (!userEmail) {
        return (
            <div className="scheduler-page-container">
                <div className="scheduler-card">
                    <h2>Acceso denegado</h2>
                    <p>No existe una sesión activa.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="scheduler-page-container">
            {/* HEADER SUPERIOR */}
            <header className="app-header">
                <h1>Smart Scheduler IA</h1>
                <button className="logout-btn-header" onClick={handleLogout}>
                    Cerrar sesión
                </button>
            </header>

            {/* LAYOUT PRINCIPAL */}
            <div className="scheduler-layout">
                {/* PANEL IZQUIERDO */}
                <div className="scheduler-sidebar">
                    <div className="scheduler-card">
                        <p>{userEmail}</p>
                        {loadingCalendarios ? (
                            <p>Cargando calendarios...</p>
                        ) : (
                            <form onSubmit={handleBuscarHuecos}>
                                <div className="form-group">
                                    <label>Calendarios</label>
                                    <div className="calendar-list">
                                        {misCalendarios.map((cal) => (
                                            <label key={cal.id} className="calendar-item">
                                                <input
                                                    type="checkbox"
                                                    checked={calendariosSeleccionados.includes(cal.id)}
                                                    onChange={() => handleCheckboxChange(cal.id)}
                                                />
                                                <span>{cal.nombre}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label>Duración</label>
                                    <select
                                        value={duracion}
                                        onChange={(e) => setDuracion(e.target.value)}
                                    >
                                        <option value={15}>15 minutos</option>
                                        <option value={30}>30 minutos</option>
                                        <option value={45}>45 minutos</option>
                                        <option value={60}>1 hora</option>
                                    </select>
                                </div>

                                <div className="form-group">
                                    <label>Buscar dentro de</label>
                                    <select
                                        value={rangoDias}
                                        onChange={(e) => setRangoDias(e.target.value)}
                                    >
                                        <option value={7}>7 días</option>
                                        <option value={15}>15 días</option>
                                        <option value={30}>30 días</option>
                                    </select>
                                </div>

                                <button
                                    type="submit"
                                    className="buscar-btn"
                                    disabled={loadingAlgoritmo}
                                >
                                    {loadingAlgoritmo ? "Buscando..." : "Buscar Huecos"}
                                </button>
                            </form>
                        )}
                    </div>
                </div>

                {/* PANEL DERECHO */}
                <div className="scheduler-calendar">
                    <div className="scheduler-card">
                        {cargandoEventos && <p>Cargando eventos...</p>}
                        <FullCalendar
                            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                            initialView="timeGridWeek"
                            locale="es"
                            height="100%"
                            events={eventosConHuecos}
                            datesSet={handleDateChange}
                            eventClick={(info) => {
                                if (info.event.id.startsWith("hueco-")) {
                                    handleHuecoClick(info.event.extendedProps.hueco);
                                }
                            }}
                            headerToolbar={{
                                left: "prev,next today",
                                center: "title",
                                right: "dayGridMonth,timeGridWeek,timeGridDay"
                            }}
                            buttonText={{
                                today: 'Hoy',
                                month: 'Mes',
                                week: 'Semana',
                                day: 'Día'
                            }}
                            slotMinTime="07:00:00"
                            slotMaxTime="20:00:00"
                            allDaySlot={false}
                            nowIndicator={true}
                            expandRows={true}
                            eventDisplay="block"
                            editable={false}
                            selectable={false}
                        />
                        <div className="calendar-legend">
                            <div className="legend-item">
                                <span className="legend-color" style={{ background: "#4F46E5" }}></span>
                                Eventos ocupados
                            </div>
                            <div className="legend-item">
                                <span className="legend-color" style={{ background: "#108981" }}></span>
                                Huecos recomendados por IA
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* MODAL */}
            {modalAbierto && huecoSeleccionado && (
                <div className="modal-overlay" onClick={() => setModalAbierto(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <h3>Programar reunión</h3>

                        <div className="modal-field">
                            <label>Título</label>
                            <input
                                type="text"
                                value={tituloReunionModal}
                                onChange={(e) => setTituloReunionModal(e.target.value)}
                                placeholder="Título de la reunión"
                            />
                        </div>

                        <div className="modal-field">
                            <label>Inicio</label>
                            <input
                                type="text"
                                value={new Date(huecoSeleccionado.start).toLocaleTimeString()}
                                readOnly
                            />
                        </div>

                        <div className="modal-field">
                            <label>Fin</label>
                            <input
                                type="text"
                                value={new Date(huecoSeleccionado.end).toLocaleTimeString()}
                                readOnly
                            />
                        </div>

                        <div className="modal-buttons">
                            <button
                                className="modal-btn cancelar"
                                onClick={() => setModalAbierto(false)}
                            >
                                Cancelar
                            </button>
                            <button
                                className="modal-btn confirmar"
                                onClick={handleConfirmarReunion}
                            >
                                Confirmar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ListaCalendarios;