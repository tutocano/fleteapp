import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, Polygon } from 'react-leaflet'
import L from 'leaflet'
import api from '../api/client.js'

// Fix de iconos default de Leaflet con bundlers tipo Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const cediIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [30, 46],
  iconAnchor: [15, 46],
  className: 'cedi-marker-icon',
})

// Icono explicito para clientes: NUNCA pasar `icon={undefined}` a un Marker de
// react-leaflet, porque JSX igual incluye la clave "icon" con valor undefined
// en el objeto de opciones, pisando el icono por defecto de Leaflet. Eso deja
// el marker sin `_icon` inicializado y provoca un crash ("Cannot read
// properties of undefined (reading '_leaflet_events')") cuando React luego
// intenta remover ese marker (por ejemplo al cambiar de ruta seleccionada).
const clienteIcon = new L.Icon.Default()

// Paleta simple para diferenciar poligonos de zona de fondo (capa contextual, opcional).
const ZONA_COLORS = ['#f59e0b', '#3b82f6', '#10b981', '#ef4444', '#8b5cf6', '#14b8a6']

export default function MapaPage() {
  const [rutasPlan, setRutasPlan] = useState([])
  const [rutaSeleccionada, setRutaSeleccionada] = useState(null)
  const [datosPlan, setDatosPlan] = useState(null)
  const [datosEjec, setDatosEjec] = useState(null)
  const [rutaEjecId, setRutaEjecId] = useState(null)
  const [zonas, setZonas] = useState([])

  useEffect(() => {
    api.get('/rutas/?es_planificada=true').then((res) => setRutasPlan(res.data))
    api.get('/zonas-geograficas/').then((res) => setZonas(res.data))
  }, [])

  const cargarRuta = async (rutaPlanId) => {
    setRutaSeleccionada(rutaPlanId)
    const mapaPlan = await api.get(`/rutas/${rutaPlanId}/mapa`)
    setDatosPlan(mapaPlan.data)

    const todas = await api.get('/rutas/?es_planificada=false')
    const ejecutada = todas.data.find((r) => r.ruta_planificada_id === rutaPlanId)
    if (ejecutada) {
      setRutaEjecId(ejecutada.id)
      const mapaEjec = await api.get(`/rutas/${ejecutada.id}/mapa`)
      setDatosEjec(mapaEjec.data)
    } else {
      setRutaEjecId(null)
      setDatosEjec(null)
    }
  }

  const center = datosPlan?.puntos?.[0]
    ? [datosPlan.puntos[0].lat, datosPlan.puntos[0].lon]
    : [4.65, -74.1]

  const polylinePlan = (datosPlan?.puntos || []).map((p) => [p.lat, p.lon])
  const polylineEjec = (datosEjec?.puntos || []).map((p) => [p.lat, p.lon])

  return (
    <div>
      <div className="page-title">Mapa de Rutas</div>
      <div className="page-subtitle">
        Visualiza la ruta planificada (azul) y su correspondiente ruta ejecutada (verde) superpuestas,
        con los puntos de CEDI y clientes.
      </div>

      <div className="card">
        <label>
          Seleccionar ruta planificada:{' '}
          <select
            value={rutaSeleccionada || ''}
            onChange={(e) => cargarRuta(Number(e.target.value))}
          >
            <option value="">-- Seleccione una ruta --</option>
            {rutasPlan.map((r) => (
              <option key={r.id} value={r.id}>
                {r.codigo_ruta} (ID {r.id})
              </option>
            ))}
          </select>
        </label>
      </div>

      {datosPlan && (
        <div className="legend">
          <div className="legend-item">
            <span className="legend-swatch" style={{ background: '#2563eb' }}></span> Ruta Planificada
          </div>
          {datosEjec && (
            <div className="legend-item">
              <span className="legend-swatch" style={{ background: '#16a34a' }}></span> Ruta Ejecutada
              (ID {rutaEjecId})
            </div>
          )}
          {!datosEjec && <div className="legend-item">Sin ruta ejecutada asociada aun.</div>}
        </div>
      )}

      <div className="map-container">
        <MapContainer center={center} zoom={11} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
          {zonas.map((z, idx) =>
            z.poligono && z.poligono.length > 2 ? (
              <Polygon
                key={`zona-${z.id}`}
                positions={z.poligono}
                pathOptions={{
                  color: ZONA_COLORS[idx % ZONA_COLORS.length],
                  fillColor: ZONA_COLORS[idx % ZONA_COLORS.length],
                  fillOpacity: 0.08,
                  weight: 1,
                }}
              >
                <Popup>{z.nombre}</Popup>
              </Polygon>
            ) : null
          )}
          {datosPlan &&
            datosPlan.puntos.map((p, idx) => (
              <Marker
                key={`plan-${idx}`}
                position={[p.lat, p.lon]}
                icon={p.tipo === 'CEDI' ? cediIcon : clienteIcon}
              >
                <Popup>
                  <strong>{p.tipo === 'CEDI' ? 'CEDI (origen)' : `Parada ${p.secuencia}`}</strong>
                  <br />
                  {p.nombre}
                  {p.tipo === 'CLIENTE' && (
                    <>
                      <br />
                      Distancia tramo: {p.distancia_km_tramo} km
                      <br />
                      Tiempo transito: {p.tiempo_transito_min_tramo} min
                      <br />
                      Tiempo servicio: {p.tiempo_servicio_min} min
                    </>
                  )}
                </Popup>
              </Marker>
            ))}
          {polylinePlan.length > 1 && (
            <Polyline positions={polylinePlan} pathOptions={{ color: '#2563eb', weight: 4 }} />
          )}
          {polylineEjec.length > 1 && (
            <Polyline
              positions={polylineEjec}
              pathOptions={{ color: '#16a34a', weight: 4, dashArray: '8 6' }}
            />
          )}
        </MapContainer>
      </div>
    </div>
  )
}
