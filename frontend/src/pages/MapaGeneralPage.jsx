import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polygon, useMap } from 'react-leaflet'
import L from 'leaflet'
import api from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'

// Ver MapaPage.jsx: MapContainer solo aplica `center` en el montaje inicial,
// asi que si los datos cambian (ej. SUPER_ADMIN cambia de empresa) el mapa no
// se recentra solo. Este componente lo reencuadra cada vez que cambian los puntos.
function AutoEncuadre({ puntos }) {
  const map = useMap()
  useEffect(() => {
    if (!puntos || puntos.length === 0) return
    if (puntos.length === 1) {
      map.setView(puntos[0], 13)
    } else {
      map.fitBounds(puntos, { padding: [40, 40] })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, JSON.stringify(puntos)])
  return null
}

// Mismo cuidado que en MapaPage.jsx: nunca usar icon={undefined} en un Marker
// de react-leaflet (crashea al remover el marker). Se definen iconos explicitos.
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const cediIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [30, 46],
  iconAnchor: [15, 46],
  className: 'cedi-marker-icon',
})

const clienteIcon = new L.Icon.Default()

// Paleta para diferenciar visualmente cada zona geografica en el mapa (capa de fondo).
const ZONA_COLORS = ['#f59e0b', '#3b82f6', '#10b981', '#ef4444', '#8b5cf6', '#14b8a6']

export default function MapaGeneralPage() {
  const { empresaSeleccionada } = useAuth()
  const [clientes, setClientes] = useState([])
  const [cedis, setCedis] = useState([])
  const [zonas, setZonas] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.get('/clientes/'),
      api.get('/centros-distribucion/'),
      api.get('/zonas-geograficas/'),
    ]).then(([cli, cedi, zon]) => {
      setClientes(cli.data)
      setCedis(cedi.data)
      setZonas(zon.data)
      setLoading(false)
    })
    // Si un SUPER_ADMIN cambia la empresa seleccionada en la cabecera, hay que
    // volver a cargar -- si no, se queda viendo los datos de la empresa anterior.
  }, [empresaSeleccionada])

  const center = cedis.length > 0 ? [cedis[0].latitud, cedis[0].longitud] : [4.65, -74.1]

  return (
    <div>
      <div className="page-title">Mapa General de Clientes y Centros de Distribucion</div>
      <div className="page-subtitle">
        Todos los clientes y CEDIs de la empresa en un solo mapa, con las zonas geograficas
        (poligonos aproximados) como capa de fondo para dar contexto visual.
      </div>

      {!loading && (
        <div className="legend">
          <div className="legend-item">
            <span className="legend-swatch-box" style={{ background: '#c0392b' }}></span> CEDI (marcador rojo)
          </div>
          <div className="legend-item">
            <span className="legend-swatch-box" style={{ background: '#2a81cb' }}></span> Cliente (marcador azul)
          </div>
          {zonas.map((z, idx) => (
            <div className="legend-item" key={z.id}>
              <span
                className="legend-swatch-box"
                style={{ background: ZONA_COLORS[idx % ZONA_COLORS.length] }}
              ></span>{' '}
              {z.nombre}
            </div>
          ))}
        </div>
      )}

      <div className="map-container">
        {loading ? (
          <p>Cargando mapa...</p>
        ) : (
          <MapContainer center={center} zoom={11} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={19}
            />
            <AutoEncuadre
              puntos={[
                ...cedis.map((c) => [c.latitud, c.longitud]),
                ...clientes.map((c) => [c.latitud, c.longitud]),
              ]}
            />

            {zonas.map((z, idx) =>
              z.poligono && z.poligono.length > 2 ? (
                <Polygon
                  key={`zona-${z.id}`}
                  positions={z.poligono}
                  pathOptions={{
                    color: ZONA_COLORS[idx % ZONA_COLORS.length],
                    fillColor: ZONA_COLORS[idx % ZONA_COLORS.length],
                    fillOpacity: 0.15,
                    weight: 1.5,
                  }}
                >
                  <Popup>
                    <strong>{z.nombre}</strong>
                    <br />
                    {z.descripcion}
                    <br />
                    Tarifa base: ${z.tarifa_zona?.toLocaleString()}
                  </Popup>
                </Polygon>
              ) : null
            )}

            {cedis.map((c) => (
              <Marker key={`cedi-${c.id}`} position={[c.latitud, c.longitud]} icon={cediIcon}>
                <Popup>
                  <strong>CEDI: {c.nombre}</strong>
                  <br />
                  Codigo: {c.codigo}
                  <br />
                  {c.direccion}
                </Popup>
              </Marker>
            ))}

            {clientes.map((cl) => (
              <Marker key={`cliente-${cl.id}`} position={[cl.latitud, cl.longitud]} icon={clienteIcon}>
                <Popup>
                  <strong>{cl.nombre}</strong>
                  <br />
                  Canal: {cl.canal || '-'}
                  <br />
                  Codigo: {cl.codigo}
                  <br />
                  {cl.direccion}
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}
      </div>
    </div>
  )
}
