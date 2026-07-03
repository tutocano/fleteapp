import { useState } from 'react'
import { useAuth } from '../auth/AuthContext.jsx'

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setCargando(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudo iniciar sesion')
    } finally {
      setCargando(false)
    }
  }

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f3f4f6',
      }}
    >
      <form onSubmit={handleSubmit} className="card" style={{ width: 340 }}>
        <h1 style={{ marginTop: 0 }}>Fleteapp</h1>
        <p className="page-subtitle" style={{ marginTop: -8 }}>
          Inicia sesion para continuar
        </p>
        <div className="form-grid">
          <label>
            Correo
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </label>
          <label>
            Contrasena
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
        </div>
        {error && (
          <p style={{ color: '#b91c1c', fontWeight: 600 }}>{error}</p>
        )}
        <button className="btn" type="submit" disabled={cargando} style={{ width: '100%' }}>
          {cargando ? 'Ingresando...' : 'Ingresar'}
        </button>
      </form>
    </div>
  )
}
