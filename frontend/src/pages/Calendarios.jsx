import React from "react";
import SeleccionCalendarios from "../components/Calendarios/ListaCalendarios"; // Ajusta la ruta según tus carpetas

const CalendariosPage = () => {
    return (
        <div className="page-wrapper">
            {/* Aquí puedes poner un Navbar o contenedor si tienen */}
            <SeleccionCalendarios />
        </div>
    );
};

export default CalendariosPage;