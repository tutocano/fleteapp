import { useEffect, useState } from 'react'
import api from '../api/client.js'
import DetalleCalculoTabla from '../components/DetalleCalculoTabla.jsx'

function DiffCell({ value, pct }) {
  if (value === null || value === undefined) return <span className="diff-zero">-</span>
  const cls = value > 0 ? 'diff-positive' : value < 0 ? 'diff-negative' : 'diff-zero'
  return (
    <span className={cls}>
      {value > 0 ? '+' : ''}
      {value.toLocaleString()} {pct !== null && pct !== undefined ? `(${pct > 0 ? '+' : ''}${pct}%)` : ''}
    </span>
  )
}

export default function ConciliacionPage() {
  const [porRuta, setPorRuta] = useState([])
  const [porTransportista, setPorTransportista] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandidoId, setExpandidoId] = useState(null)
  const [detalles, setDetalles] = useState({}) // { rutaId: { plan, ejec } }

  useEffect(() => {
    Promise.all([api.get('/conciliacion/rutas'), api.get('/conciliacion/transportistas')]).then(
      ([r, t]) => {
        setPorRuta(r.data)
        setPorTransportista(t.data)
        setLoading(false)
      }
    )
  }, [])

  const toggleDetalle = async (fila) => {
    const key = fila.ruta_planificada_id
    if (expandidoId === key) {
      setExpandidoId(null)
      return
    }
    setExpandidoId(key)
    if (!detalles[key]) {
      const planReq = api.get(`/rutas/${fila.ruta_planificada_id}`)
      const ejecReq = fila.ruta_ejecutada_id ? api.get(`/rutas/${fila.ruta_ejecutada_id}`) : Promise.resolve(null)
      const [planRes, ejecRes] = await Promise.all([planReq, ejecReq])
      setDetalles((prev) => ({
        ...prev,
        [key]: { plan: planRes.data, ejec: ejecRes ? ejecRes.data : null },
      }))
    }
  }

  if (loading) return <p>Cargando conciliacion...</p>

  return (
    <div>
      <div className="page-title">Conciliacion de Costos de Flete</div>
      <div className="page-subtitle">
        Comparacion entre el costo de flete estimado (planificado) y el costo real (ejecutado),
        por ruta y agregado por transportista.
      </div>

      <div className="card">
        <strong>Conciliacion por Ruta</strong>
        <table style={{ marginTop: 10 }}>
          <thead>
            <tr>
              <th>Codigo Ruta</th>
              <th>Transportista</th>
              <th>Metodo Tarifa</th>
              <th>Costo Planificado</th>
              <th>Costo Real</th>
              <th>Diferencia</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            {porRuta.map((r) => (
              <>
                <tr key={r.ruta_planificada_id}>
                  <td>{r.codigo_ruta}</td>
                  <td>{r.transportista_nombre}</td>
                  <td>{r.metodo_tarifa}</td>
                  <td>{r.costo_planificado?.toLocaleString() ?? '-'}</td>
                  <td>{r.costo_real?.toLocaleString() ?? 'Sin ejecutar'}</td>
                  <td>
                    <DiffCell value={r.diferencia_absoluta} pct={r.diferencia_porcentual} />
                  </td>
                  <td>
                    <button className="btn secondary" onClick={() => toggleDetalle(r)}>
                      {expandidoId === r.ruta_planificada_id ? 'Ocultar' : 'Ver calculo'}
                    </button>
                  </td>
                </tr>
                {expandidoId === r.ruta_planificada_id && (
                  <tr>
                    <td colSpan={7}>
                      {detalles[r.ruta_planificada_id] ? (
                        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                          <div style={{ flex: 1, minWidth: 320 }}>
                            <strong>Planificado</strong>
                            <DetalleCalculoTabla
                              detalleCalculo={detalles[r.ruta_planificada_id].plan?.detalle_calculo}
                              costoTotal={detalles[r.ruta_planificada_id].plan?.costo_flete_calculado}
                              tipoCamion={detalles[r.ruta_planificada_id].plan?.tipo_camion}
                              paradas={detalles[r.ruta_planificada_id].plan?.paradas}
                            />
                          </div>
                          <div style={{ flex: 1, minWidth: 320 }}>
                            <strong>Ejecutado</strong>
                            {detalles[r.ruta_planificada_id].ejec ? (
                              <DetalleCalculoTabla
                                detalleCalculo={detalles[r.ruta_planificada_id].ejec?.detalle_calculo}
                                costoTotal={detalles[r.ruta_planificada_id].ejec?.costo_flete_calculado}
                                tipoCamion={detalles[r.ruta_planificada_id].ejec?.tipo_camion}
                                paradas={detalles[r.ruta_planificada_id].ejec?.paradas}
                              />
                            ) : (
                              <p>Sin ruta ejecutada asociada aun.</p>
                            )}
                          </div>
                        </div>
                      ) : (
                        <p>Cargando detalle...</p>
                      )}
                    </td>
                  </tr>
                )}
              </>
            ))}
            {porRuta.length === 0 && (
              <tr>
                <td colSpan={7}>No hay rutas planificadas registradas.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <strong>Conciliacion Agregada por Transportista</strong>
        <table style={{ marginTop: 10 }}>
          <thead>
            <tr>
              <th>Transportista</th>
              <th># Rutas Conciliadas</th>
              <th>Total Planificado</th>
              <th>Total Real</th>
              <th>Diferencia</th>
            </tr>
          </thead>
          <tbody>
            {porTransportista.map((t) => (
              <tr key={t.transportista_id}>
                <td>{t.transportista_nombre}</td>
                <td>{t.num_rutas}</td>
                <td>{t.total_planificado.toLocaleString()}</td>
                <td>{t.total_real.toLocaleString()}</td>
                <td>
                  <DiffCell value={t.diferencia_absoluta} pct={t.diferencia_porcentual} />
                </td>
              </tr>
            ))}
            {porTransportista.length === 0 && (
              <tr>
                <td colSpan={5}>No hay conciliaciones disponibles (se requieren rutas ejecutadas).</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
