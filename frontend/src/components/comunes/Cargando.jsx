import React from "react";
import "./Cargando.css";

const RedirectLoading = () => {
    return (
        <div className="redirect-container">
            <div className="redirect-card">
                <div className="redirect-spinner"></div>
                <h2 className="redirect-title">Iniciando sesión de forma segura</h2>
                <p className="redirect-text">Validando tus credenciales con Google e IA...</p>
            </div>
        </div>
    );
};

export default RedirectLoading;