import { createContext, useContext, useEffect, useState } from 'react'
import api, { TOKEN_KEY, USUARIO_KEY, EMPRESA_OVERRIDE_KEY } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [empresaSeleccionada, setEmpresaSeleccionadaState] = useState(
    localStorage.getItem(EMPRESA_OVERRIDE_KEY) || ''
  )
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setCargando(false)
      return
    }
    // Valida el token contra el backend (por si expiro o el usuario fue
    // desactivado desde que se guardo localmente).
    api
      .get('/auth/me')
      .then((res) => {
        setUsuario(res.data)
        localStorage.setItem(USUARIO_KEY, JSON.stringify(res.data))
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USUARIO_KEY)
        setUsuario(null)
      })
      .finally(() => setCargando(false))
  }, [])

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    localStorage.setItem(TOKEN_KEY, res.data.access_token)
    localStorage.setItem(USUARIO_KEY, JSON.stringify(res.data.usuario))
    setUsuario(res.data.usuario)
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USUARIO_KEY)
    localStorage.removeItem(EMPRESA_OVERRIDE_KEY)
    setUsuario(null)
    setEmpresaSeleccionadaState('')
  }

  const setEmpresaSeleccionada = (empresaId) => {
    if (empresaId) {
      localStorage.setItem(EMPRESA_OVERRIDE_KEY, empresaId)
    } else {
      localStorage.removeItem(EMPRESA_OVERRIDE_KEY)
    }
    setEmpresaSeleccionadaState(empresaId || '')
  }

  return (
    <AuthContext.Provider
      value={{ usuario, cargando, login, logout, empresaSeleccionada, setEmpresaSeleccionada }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
