import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './estilos/index.css'
import Login from './pages/Login.jsx'
import RedirectLoading from './pages/RedirectLoading.jsx' // ← 1. Importamos la nueva página de carga
import Calendarios from './pages/Calendarios.jsx' // ← 2. Importamos la página de calendarios final

function App() {
  return (
    <BrowserRouter>
      <div className="container">
        <Routes>
          {/* 1. Si entran a la raíz de la página, los manda directo al login */}
          <Route path="/" element={<Navigate to="/login" />} />
          
          {/* 2. Cuando la URL sea /login, muestra la página de Login */}
          <Route path="/login" element={<Login />} />
          
          {/* 3. ¡EL INTERMEDIARIO! Cuando Google regrese a /calendarios, ahora verá la animación de carga por 2 segundos */}
          <Route path="/calendarios" element={<RedirectLoading />} />
          
          {/* 4. La pantalla final con el formulario a la que saltará automáticamente después de la carga */}
          <Route path="/configurar-calendarios" element={<Calendarios />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App