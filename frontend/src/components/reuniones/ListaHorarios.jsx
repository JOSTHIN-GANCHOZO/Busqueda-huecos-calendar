import React, { useState, useEffect } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import { calendarioService } from '../../servicios/eventos'; // Asegúrate de que la ruta sea correcta
import './ListaHorarios.css';

const CalendarioVisual = ({ email, calendariosIds, huecoRecomendado }) => {
  const [fechaActual, setFechaActual] = useState(new Date());
  const [eventos, setEventos] = useState([]);
  const [cargando, setCargando] = useState(false);

  // Función para obtener inicio y fin del mes
  const obtenerInicioFinMes = (fecha) => {
    const inicio = new Date(fecha.getFullYear(), fecha.getMonth(), 1);
    const fin = new Date(fecha.getFullYear(), fecha.getMonth() + 1, 0, 23, 59, 59);
    return { inicio, fin };
  };

  // Carga automática al cambiar mes o calendarios seleccionados
  useEffect(() => {
    if (!email || calendariosIds.length === 0) {
      setEventos([]);
      return;
    }

    const cargarEventos = async () => {
      setCargando(true);
      try {
        const { inicio, fin } = obtenerInicioFinMes(fechaActual);
        // Convierte a ISO para enviar al backend
        const data = await calendarioService.obtenerEventosCalendario({
          email,
          calendarios_ids: calendariosIds,
          fecha_inicio: inicio.toISOString(),
          fecha_fin: fin.toISOString()
        });
        // Transforma al formato que espera FullCalendar
        const eventosFullCalendar = data.eventos.map(ev => ({
          id: ev.id,
          title: ev.title,
          start: ev.start,
          end: ev.end,
          calendarId: ev.calendar_id,
          // Puedes añadir color según calendarId si lo deseas
        }));
        setEventos(eventosFullCalendar);
      } catch (error) {
        console.error('Error cargando eventos:', error);
        alert('No se pudieron cargar los eventos del calendario.');
      } finally {
        setCargando(false);
      }
    };

    cargarEventos();
  }, [fechaActual, calendariosIds, email]);

  // Si hay un hueco recomendado, lo agregamos como evento destacado
  const eventosConHueco = [...eventos];
  if (huecoRecomendado) {
    eventosConHueco.push({
      id: 'hueco-ia',
      title: '⭐ Hueco óptimo',
      start: huecoRecomendado.inicio,
      end: huecoRecomendado.fin,
      color: '#4CAF50', // Verde
      textColor: 'white',
      classNames: ['hueco-recomendado']
    });
  }

  return (
    <div className="calendario-visual-container">
      {cargando && <div className="calendario-loader">Cargando eventos...</div>}
      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        events={eventosConHueco}
        datesSet={(arg) => {
          // Al cambiar de mes, actualizamos la fecha
          setFechaActual(arg.start);
        }}
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,dayGridWeek'
        }}
        height="auto"
        eventColor="#3788d8"
        eventDisplay="block"
      />
    </div>
  );
};

export default CalendarioVisual;