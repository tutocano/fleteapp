import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { useAuth } from './auth/AuthContext.jsx'
import LoginPage from './pages/LoginPage.jsx'
import EmpresaPage from './pages/EmpresaPage.jsx'
import UsuariosPage from './pages/UsuariosPage.jsx'
import CedisPage from './pages/CedisPage.jsx'
import ClientesPage from './pages/ClientesPage.jsx'
import TransportistasPage from './pages/TransportistasPage.jsx'
import CoberturaZonasPage from './pages/CoberturaZonasPage.jsx'
import TarifasPage from './pages/TarifasPage.jsx'
import ZonasPage from './pages/ZonasPage.jsx'
import ProductosPage from './pages/ProductosPage.jsx'
import TiposCamionPage from './pages/TiposCamionPage.jsx'
import FlotaPage from './pages/FlotaPage.jsx'
import RutasPage from './pages/RutasPage.jsx'
import ConciliacionPage from './pages/ConciliacionPage.jsx'
import MapaPage from './pages/MapaPage.jsx'
import MapaGeneralPage from './pages/MapaGeneralPage.jsx'
import EmpresaSelector from './components/EmpresaSelector.jsx'

// v4: navegacion filtrada por rol. SUPER_ADMIN siempre ve todo (igual que el
// backend, ver auth.require_role) sin importar si aparece o no en `roles`.
const NAV_GROUPS = [
  {
    label: 'Administracion',
    roles: ['SUPER_ADMIN'],
    items: [
      { to: '/empresas', label: 'Empresas' },
      { to: '/usuarios', label: 'Usuarios' },
    ],
  },
  {
    label: 'Maestros',
    roles: ['EMPRESA_ADMIN'],
    items: [
      { to: '/cedis', label: 'Centros Distribucion' },
      { to: '/clientes', label: 'Clientes' },
      { to: '/zonas', label: 'Zonas Geograficas' },
      { to: '/tipos-camion', label: 'Tipos de Camion' },
      { to: '/flota', label: 'Flota' },
      { to: '/transportistas', label: 'Transportistas' },
      { to: '/cobertura-zonas', label: 'Cobertura de Zonas' },
      { to: '/tarifas', label: 'Tarifas de Flete' },
      { to: '/productos', label: 'Productos' },
    ],
  },
  {
    label: 'Operacion',
    roles: ['EMPRESA_ADMIN', 'INTERFAZ'],
    items: [{ to: '/rutas', label: 'Rutas (Import)' }],
  },
  {
    label: 'Consulta',
    roles: ['EMPRESA_ADMIN', 'INTERFAZ', 'USUARIO_FINAL'],
    items: [
      { to: '/mapa', label: 'Mapa de Rutas' },
      { to: '/mapa-general', label: 'Mapa General' },
      { to: '/conciliacion', label: 'Conciliacion' },
    ],
  },
]

function puedeVer(usuario, roles) {
  return usuario.rol === 'SUPER_ADMIN' || roles.includes(usuario.rol)
}

function RequireRole({ usuario, roles, children }) {
  if (!puedeVer(usuario, roles)) {
    return (
      <div className="card">
        <p>No tienes permiso para ver esta pagina con tu rol actual ({usuario.rol}).</p>
      </div>
    )
  }
  return children
}

function rutaInicial(usuario) {
  if (usuario.rol === 'SUPER_ADMIN') return '/empresas'
  if (usuario.rol === 'EMPRESA_ADMIN') return '/cedis'
  if (usuario.rol === 'INTERFAZ') return '/rutas'
  return '/mapa'
}

function App() {
  const { usuario, cargando, logout } = useAuth()

  if (cargando) {
    return <p style={{ padding: 20 }}>Cargando...</p>
  }

  if (!usuario) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    )
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h1>Fleteapp</h1>
        {NAV_GROUPS.filter((g) => puedeVer(usuario, g.roles)).map((g) => (
          <div key={g.label}>
            <div className="sidebar-group">{g.label}</div>
            {g.items.map((item) => (
              <NavLink key={item.to} to={item.to}>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </aside>
      <main className="content">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 16,
          }}
        >
          {usuario.rol === 'SUPER_ADMIN' ? (
            <EmpresaSelector />
          ) : (
            <span style={{ color: '#6b7280' }}>Empresa asignada: {usuario.empresa_id}</span>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span>
              {usuario.nombre} <span style={{ color: '#6b7280' }}>({usuario.rol})</span>
            </span>
            <button className="btn secondary" onClick={logout}>
              Cerrar sesion
            </button>
          </div>
        </div>

        <Routes>
          <Route path="/login" element={<Navigate to={rutaInicial(usuario)} replace />} />
          <Route
            path="/empresas"
            element={
              <RequireRole usuario={usuario} roles={['SUPER_ADMIN']}>
                <EmpresaPage />
              </RequireRole>
            }
          />
          <Route
            path="/usuarios"
            element={
              <RequireRole usuario={usuario} roles={['SUPER_ADMIN']}>
                <UsuariosPage />
              </RequireRole>
            }
          />
          <Route
            path="/cedis"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <CedisPage />
              </RequireRole>
            }
          />
          <Route
            path="/clientes"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <ClientesPage />
              </RequireRole>
            }
          />
          <Route
            path="/zonas"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <ZonasPage />
              </RequireRole>
            }
          />
          <Route
            path="/tipos-camion"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <TiposCamionPage />
              </RequireRole>
            }
          />
          <Route
            path="/flota"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <FlotaPage />
              </RequireRole>
            }
          />
          <Route
            path="/transportistas"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <TransportistasPage />
              </RequireRole>
            }
          />
          <Route
            path="/cobertura-zonas"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <CoberturaZonasPage />
              </RequireRole>
            }
          />
          <Route
            path="/tarifas"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <TarifasPage />
              </RequireRole>
            }
          />
          <Route
            path="/productos"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN']}>
                <ProductosPage />
              </RequireRole>
            }
          />
          <Route
            path="/rutas"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN', 'INTERFAZ']}>
                <RutasPage />
              </RequireRole>
            }
          />
          <Route
            path="/mapa"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN', 'INTERFAZ', 'USUARIO_FINAL']}>
                <MapaPage />
              </RequireRole>
            }
          />
          <Route
            path="/mapa-general"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN', 'INTERFAZ', 'USUARIO_FINAL']}>
                <MapaGeneralPage />
              </RequireRole>
            }
          />
          <Route
            path="/conciliacion"
            element={
              <RequireRole usuario={usuario} roles={['EMPRESA_ADMIN', 'INTERFAZ', 'USUARIO_FINAL']}>
                <ConciliacionPage />
              </RequireRole>
            }
          />
          <Route path="/" element={<Navigate to={rutaInicial(usuario)} replace />} />
          <Route path="*" element={<Navigate to={rutaInicial(usuario)} replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
