import { useEffect, useState } from 'react'
import api from '../api/client.js'
import DetalleCalculoTabla from '../components/DetalleCalculoTabla.jsx'

const EJEMPLO_PLANIFICADA = {
  codigo_ruta: 'RUTA-DEMO-001',
  centro_distribucion_id: 1,
  transportista_id: 2,
  tarifa_transportista_id: 3,
  tipo_camion_id: 3,
  fecha: '2026-07-01T07:00:00',
  paradas: [
    {
      cliente_id: 1,
      secuencia: 1,
      tiempo_servicio_min: 20,
      pedidos: [{ producto_id: 1, cantidad: 50 }],
    },
    {
      cliente_id: 2,
      secuencia: 2,
      tiempo_servicio_min: 25,
      pedidos: [{ producto_id: 1, cantidad: 30 }],
    },
  ],
}

const EJEMPLO_EJECUTADA = {
  codigo_ruta: 'RUTA-DEMO-001',
  centro_distribucion_id: 1,
  transportista_id: 2,
  tarifa_transportista_id: 3,
  tipo_camion_id: 3,
  fecha: '2026-07-01T07:00:00',
  ruta_planificada_id: null, // se debe reemplazar por el ID real de la ruta planificada creada
  paradas: [
    {
      cliente_id: 1,
      secuencia: 1,
      tiempo_servicio_min: 28,
      pedidos: [{ producto_id: 1, cantidad: 55 }],
    },
    {
      cliente_id: 2,
      secuencia: 2,
      tiempo_servicio_min: 25,
      pedidos: [{ producto_id: 1, cantidad: 30 }],
    },
  ],
}

export default function RutasPage() {
  const [rutas, setRutas] = useState([])
  const [loading, setLoading] = useState(true)
  const [jsonText, setJsonText] = useState(JSON.stringify(EJEMPLO_PLANIFICADA, null, 2))
  const [tipoImport, setTipoImport] = useState('planificada')
  const [mensaje, setMensaje] = useState(null)
  const [rutaExpandidaId, setRutaExpandidaId] = useState(null)
  const [rutaExpandidaDetalle, setRutaExpandidaDetalle] = useState(null)

  const load = async () => {
    setLoading(true)
    const res = await api.get('/rutas/')
    setRutas(res.data)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const toggleDetalle = async (rutaId) => {
    if (rutaExpandidaId === rutaId) {
      setRutaExpandidaId(null)
      setRutaExpandidaDetalle(null)
      return
    }
    setRutaExpandidaId(rutaId)
    const res = await api.get(`/rutas/${rutaId}`)
    setRutaExpandidaDetalle(res.data)
  }

  const cargarEjemplo = () => {
    setJsonText(
      JSON.stringify(tipoImport === 'planificada' ? EJEMPLO_PLANIFICADA : EJEMPLO_EJECUTADA, null, 2)
    )
  }

  const handleImport = async () => {
    setMensaje(null)
    let payload
    try {
      payload = JSON.parse(jsonText)
    } catch (e) {
      setMensaje({ tipo: 'error', texto: 'JSON invalido: ' + e.message })
      return
    }
    try {
      const res = await api.post(`/rutas/importar/${tipoImport}`, payload)
      setMensaje({
        tipo: 'ok',
        texto: `Ruta importada con ID ${res.data.id}. Costo calculado: $${res.data.costo_flete_calculado?.toLocaleString()} (${res.data.detalle_calculo?.explicacion || ''})`,
      })
      await load()
    } catch (e) {
      setMensaje({ tipo: 'error', texto: 'Error: ' + (e.response?.data?.detail || e.message) })
    }
  }

  return (
    <div>
      <div className="page-title">Rutas Planificadas y Ejecutadas</div>
      <div className="page-subtitle">
        Importa rutas (planificadas o ejecutadas) via JSON. El sistema calcula automaticamente
        el costo de flete segun el metodo de tarifa configurado para el transportista asignado.
      </div>

      <div className="card">
        <div className="form-grid" style={{ maxWidth: 400 }}>
          <label>
            Tipo de importacion
            <select value={tipoImport} onChange={(e) => setTipoImport(e.target.value)}>
              <option value="planificada">Ruta Planificada</option>
              <option value="ejecutada">Ruta Ejecutada</option>
            </select>
          </label>
        </div>
        <button className="btn secondary" onClick={cargarEjemplo}>
          Cargar JSON de ejemplo
        </button>{' '}
        <button className="btn" onClick={handleImport}>
          Importar JSON
        </button>
        <div style={{ marginTop: 12 }}>
          <textarea
            style={{ width: '100%', height: 320, fontFamily: 'monospace', fontSize: 12 }}
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
          />
        </div>
        {mensaje && (
          <p style={{ color: mensaje.tipo === 'error' ? '#b91c1c' : '#166534', fontWeight: 600 }}>
            {mensaje.texto}
          </p>
        )}
        <p style={{ fontSize: 12, color: '#6b7280' }}>
          Nota: para importar una ruta EJECUTADA debes referenciar el <code>ruta_planificada_id</code>{' '}
          de una ruta planificada existente (ver tabla abajo para obtener el ID).
        </p>
        <p style={{ fontSize: 12, color: '#6b7280' }}>
          Nota: si el transportista tiene tarifas distintas segun el tipo de camion, revisa la pantalla
          "Tarifas de Flete" (columna "Tipo de Camion") para usar el <code>tarifa_transportista_id</code>{' '}
          correcto para el <code>tipo_camion_id</code> de esta ruta. Si usas una tarifa restringida a un
          camion distinto al de la ruta, la importacion sera rechazada con un error explicativo.
        </p>
      </div>

      <div className="card">
        <strong>Rutas registradas</strong>
        {loading ? (
          <p>Cargando...</p>
        ) : (
          <table style={{ marginTop: 10 }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Codigo</th>
                <th>Tipo</th>
                <th>Ruta Planificada Ref.</th>
                <th>Transportista ID</th>
                <th>Fecha</th>
                <th>Estado</th>
                <th>Costo Calculado</th>
                <th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {rutas.map((r) => (
                <>
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>{r.codigo_ruta}</td>
                    <td>
                      <span className={`badge ${r.es_planificada ? 'plan' : 'ejec'}`}>
                        {r.es_planificada ? 'Planificada' : 'Ejecutada'}
                      </span>
                    </td>
                    <td>{r.ruta_planificada_id ?? '-'}</td>
                    <td>{r.transportista_id}</td>
                    <td>{r.fecha}</td>
                    <td>{r.estado}</td>
                    <td>{r.costo_flete_calculado?.toLocaleString()}</td>
                    <td>
                      <button className="btn secondary" onClick={() => toggleDetalle(r.id)}>
                        {rutaExpandidaId === r.id ? 'Ocultar' : 'Ver calculo'}
                      </button>
                    </td>
                  </tr>
                  {rutaExpandidaId === r.id && (
                    <tr>
                      <td colSpan={9}>
                        {rutaExpandidaDetalle ? (
                          <DetalleCalculoTabla
                            detalleCalculo={rutaExpandidaDetalle.detalle_calculo}
                            costoTotal={rutaExpandidaDetalle.costo_flete_calculado}
                            tipoCamion={rutaExpandidaDetalle.tipo_camion}
                          />
                        ) : (
                          <p>Cargando detalle...</p>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
