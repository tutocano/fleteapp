import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export const TOKEN_KEY = 'fleteapp_token'
export const USUARIO_KEY = 'fleteapp_usuario'
export const EMPRESA_OVERRIDE_KEY = 'fleteapp_empresa_override'

export const api = axios.create({
  baseURL: API_URL,
})

// v4: adjunta el token JWT a cada request (si existe), y si el usuario actual
// es SUPER_ADMIN y eligio "ver datos de la empresa X" (selector en la
// cabecera), agrega ?empresa_id= automaticamente a menos que la llamada ya
// lo haya especificado explicitamente.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  const empresaOverride = localStorage.getItem(EMPRESA_OVERRIDE_KEY)
  if (empresaOverride) {
    config.params = { empresa_id: empresaOverride, ...config.params }
  }

  return config
})

// Si el token expiro o es invalido, el backend responde 401 -- se limpia la
// sesion y se manda a login. Se evita hacerlo para el propio POST /auth/login
// (ahi un 401 es "contrasena incorrecta", no "sesion expirada").
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const esLogin = error.config?.url?.includes('/auth/login')
    if (error.response?.status === 401 && !esLogin) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USUARIO_KEY)
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
