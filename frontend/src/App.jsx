import { Routes, Route, NavLink } from 'react-router-dom'
import EmpresaPage from './pages/EmpresaPage.jsx'
import CedisPage from './pages/CedisPage.jsx'
import ClientesPage from './pages/ClientesPage.jsx'
import TransportistasPage from './pages/TransportistasPage.jsx'
import TarifasPage from './pages/TarifasPage.jsx'
import ZonasPage from './pages/ZonasPage.jsx'
import ProductosPage from './pages/ProductosPage.jsx'
import TiposCamionPage from './pages/TiposCamionPage.jsx'
import FlotaPage from './pages/FlotaPage.jsx'
import RutasPage from './pages/RutasPage.jsx'
import ConciliacionPage from './pages/ConciliacionPage.jsx'
import MapaPage from './pages/MapaPage.jsx'
import MapaGeneralPage from './pages/MapaGeneralPage.jsx'

function App() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h1>Fleteapp</h1>
        <div className="sidebar-group">Maestros</div>
        <NavLink to="/">Empresa</NavLink>
        <NavLink to="/cedis">Centros Distribucion</NavLink>
        <NavLink to="/clientes">Clientes</NavLink>
        <NavLink to="/zonas">Zonas Geograficas</NavLink>
        <NavLink to="/tipos-camion">Tipos de Camion</NavLink>
        <NavLink to="/flota">Flota</NavLink>
        <NavLink to="/transportistas">Transportistas</NavLink>
        <NavLink to="/tarifas">Tarifas de Flete</NavLink>
        <NavLink to="/productos">Productos</NavLink>
        <div className="sidebar-group">Operacion</div>
        <NavLink to="/rutas">Rutas (Import)</NavLink>
        <NavLink to="/mapa">Mapa de Rutas</NavLink>
        <NavLink to="/mapa-general">Mapa General</NavLink>
        <NavLink to="/conciliacion">Conciliacion</NavLink>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<EmpresaPage />} />
          <Route path="/cedis" element={<CedisPage />} />
          <Route path="/clientes" element={<ClientesPage />} />
          <Route path="/zonas" element={<ZonasPage />} />
          <Route path="/tipos-camion" element={<TiposCamionPage />} />
          <Route path="/flota" element={<FlotaPage />} />
          <Route path="/transportistas" element={<TransportistasPage />} />
          <Route path="/tarifas" element={<TarifasPage />} />
          <Route path="/productos" element={<ProductosPage />} />
          <Route path="/rutas" element={<RutasPage />} />
          <Route path="/mapa" element={<MapaPage />} />
          <Route path="/mapa-general" element={<MapaGeneralPage />} />
          <Route path="/conciliacion" element={<ConciliacionPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
