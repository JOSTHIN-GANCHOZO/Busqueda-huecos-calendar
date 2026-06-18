import React from "react";
import BotonGoogle from "../components/botones/BotonGoogle";
import "./Login.css";

const Login = () => {
return (
        <div className="login-container"> 
            <div className="login-card"> 
                <div className="login-content"> <h1 className="login-title">Smart Scheduler IA</h1>
                    <p className="login-description">
                        Optimiza tus reuniones cruzando agendas con inteligencia artificial
                    </p>

                    <div className="login-button-container">
                        <BotonGoogle />
                    </div>
                </div>

                <div className="login-footer">
                    <div className="security-title">
                        Seguridad IA
                    </div>

                    <div className="security-features">
                        <div className="security-item">
                            <span>🛡️</span>
                            <span>Protegido</span>
                        </div>

                        <div className="security-item">
                            <span>📋</span>
                            <span>Sincronizado</span>
                        </div>

                        <div className="security-item">
                            <span>⚡</span>
                            <span>Eficiente</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Login;
