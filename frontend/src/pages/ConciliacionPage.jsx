import { useEffect, useState } from 'react'
import api from '../api/client.js'

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

  useEffect(() => {
    Promise.all([api.get('/conciliacion/rutas'), api.get('/conciliacion/transportistas')]).then(
      ([r, t]) => {
        setPorRuta(r.data)
        setPorTransportista(t.data)
        setLoading(false)
      }
    )
  }, [])

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
            </tr>
          </thead>
          <tbody>
            {porRuta.map((r) => (
              <tr key={r.ruta_planificada_id}>
                <td>{r.codigo_ruta}</td>
                <td>{r.transportista_nombre}</td>
                <td>{r.metodo_tarifa}</td>
                <td>{r.costo_planificado?.toLocaleString() ?? '-'}</td>
                <td>{r.costo_real?.toLocaleString() ?? 'Sin ejecutar'}</td>
                <td>
                  <DiffCell value={r.diferencia_absoluta} pct={r.diferencia_porcentual} />
                </td>
              </tr>
            ))}
            {porRuta.length === 0 && (
              <tr>
                <td colSpan={6}>No hay rutas planificadas registradas.</td>
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
