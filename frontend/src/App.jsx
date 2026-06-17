import { useState } from 'react'
import './estilos/index.css'

function App() {
  // Estados listos para usar en el formulario
  const [correo1, setCorreo1] = useState('')
  const [correo2, setCorreo2] = useState('')
  const [correo3, setCorreo3] = useState('')
  const [duracion, setDuracion] = useState(60)

  const handleBuscar = (e) => {
    e.preventDefault()
    // Aquí tu compañera meterá el Axios más adelante
    console.log("Datos listos para enviar:", { correo1, correo2, correo3, duracion })
  }

  return (
    <div className="container">
      <h1>Agendamiento Inteligente de Reuniones 🚀</h1>
      {/* Tu compañera expandirá el formulario aquí dentro */}
      <form onSubmit={handleBuscar}>
        <button type="submit">Buscar Horario</button>
      </form>
    </div>
  )
}

export default App