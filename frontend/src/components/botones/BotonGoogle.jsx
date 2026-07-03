import React, { useState } from "react";
import './BotonGoogle.css';
import GoogleIcon from '../../assets/google.png';
import { authService } from '../../servicios/auth.js'; 

const BotonGoogle = () => {
    const [loading, setLoading] = useState(false);

    const handleLogin = async () => {
        if (loading) return;
        setLoading(true);

        try {
            // Llamamos al servicio que ya tienes en tu carpeta
            const authUrl = await authService.getGoogleAuthUrl();
            window.location.assign(authUrl);
        } catch (error) {
            console.error("Error al iniciar sesión con Google:", error);
            alert(error.message); // El servicio ya te da el mensaje limpio aquí
        } finally {
            setLoading(false);
        }
    };

    return ( 
        <button
            type="button"
            onClick={handleLogin}
            disabled={loading}
            className="google-button" 
        >
            <div className="google-button-content">
                <span className="google-icon">
                    <img src={GoogleIcon} alt="Google Icon" />
                </span>
                <span className="google-button-text">
                  {loading ? "Conectando..." : "Continuar con Google"}
                </span>
            </div>
        </button>
    );
};

export default BotonGoogle;