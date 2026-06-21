import React, { useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import Loading from '../components/comunes/Cargando.jsx'; // Aseguren aquí la ruta real a tu componente de carga

const RedirectLoading = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    
    // Captura el email que manda el backend en la URL
    const userEmail = searchParams.get("email") || "";

    useEffect(() => {
        // Muestra el componente de carga por 2 segundos exactos y luego redirige
        const timer = setTimeout(() => {
            navigate(`/configurar-calendarios?email=${userEmail}`);
        }, 2000); 

        return () => clearTimeout(timer);
    }, [userEmail, navigate]);

    // Renderiza tu componente de carga que acabamos de diseñar
    return <Loading />;
};

export default RedirectLoading;