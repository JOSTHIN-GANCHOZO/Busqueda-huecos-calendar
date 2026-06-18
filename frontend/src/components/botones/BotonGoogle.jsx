import React, { useState } from "react";
import './botonGoogle.css'
import axios from "axios";

const API_URL = "http://localhost:8000/api/v1/auth/login";

const BotonGoogle = () => {
const [loading, setLoading] = useState(false);

const handleLogin = async () => {

        if (loading) return;

        setLoading(true);

        try {
            const { data } = await axios.get(API_URL);

            if (!data?.auth_url) {
                throw new Error("No se recibió la URL de autenticación.");
            }

            window.location.assign(data.auth_url);
        } catch (error) {
            console.error("Error al iniciar sesión con Google:", error);

            const mensaje =
                error.response?.data?.detail ||
                "No fue posible conectar con Google. Intenta nuevamente.";

            alert(mensaje);
        } finally {
         setLoading(false);
        }


    };

    return ( 
        <button
            type="button"
            onClick={handleLogin}
            disabled={loading}
            > <span>
            {loading ? "Conectando..." : "Continuar con Google"} </span> 
        </button>
    );
};

export default BotonGoogle;
