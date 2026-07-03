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

// Columnas que espera el CSV (ver backend/app/services/csv_import.py). Una fila
// = un pedido dentro de una parada dentro de una ruta; filas con el mismo
// codigo_ruta se agrupan en la misma ruta, y con la misma secuencia en la misma
// parada. Los CSV de ejecutada NO llevan columna de "ruta planificada": se
// busca automaticamente una ruta planificada con el mismo codigo_ruta.
const COLUMNAS_CSV_OBLIGATORIAS = [
  'codigo_ruta', 'centro_distribucion_codigo', 'transportista_nombre', 'tarifa_nombre',
  'tipo_camion_nombre', 'secuencia', 'cliente_codigo', 'producto_codigo', 'cantidad',
]
const COLUMNAS_CSV_OPCIONALES = [
  'fecha', 'flota_placa', 'tiempo_servicio_min', 'distancia_km_tramo',
  'tiempo_transito_min_tramo', 'hora_llegada_estimada', 'hora_llegada_real', 'peso_kg', 'volumen_m3',
]

export default function RutasPage() {
  const [rutas, setRutas] = useState([])
  const [loading, setLoading] = useState(true)
  const [modoImport, setModoImport] = useState('json') // 'json' | 'csv'
  const [jsonText, setJsonText] = useState(JSON.stringify(EJEMPLO_PLANIFICADA, null, 2))
  const [tipoImport, setTipoImport] = useState('planificada')
  const [mensaje, setMensaje] = useState(null)
  const [rutaExpandidaId, setRutaExpandidaId] = useState(null)
  const [rutaExpandidaDetalle, setRutaExpandidaDetalle] = useState(null)
  const [archivoCsv, setArchivoCsv] = useState(null)
  const [resultadoCsv, setResultadoCsv] = useState(null)
  const [subiendoCsv, setSubiendoCsv] = useState(false)

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

  const handleSubirCsv = async () => {
    if (!archivoCsv) {
      setMensaje({ tipo: 'error', texto: 'Selecciona primero un archivo CSV' })
      return
    }
    setMensaje(null)
    setResultadoCsv(null)
    setSubiendoCsv(true)
    try {
      const formData = new FormData()
      formData.append('archivo', archivoCsv)
      const res = await api.post(`/rutas/importar-csv/${tipoImport}`, formData)
      setResultadoCsv(res.data)
      await load()
    } catch (e) {
      setMensaje({ tipo: 'error', texto: 'Error: ' + (e.response?.data?.detail || e.message) })
    } finally {
      setSubiendoCsv(false)
    }
  }

  return (
    <div>
      <div className="page-title">Rutas Planificadas y Ejecutadas</div>
      <div className="page-subtitle">
        Importa rutas (planificadas o ejecutadas) via JSON (una ruta a la vez, por ID) o via CSV
        (varias rutas de un dia completo a la vez, identificando cliente/producto/etc. por su codigo
        o nombre). El sistema calcula automaticamente el costo de flete segun el metodo de tarifa
        configurado para el transportista asignado.
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

        <div style={{ margin: '10px 0' }}>
          <button
            className={modoImport === 'json' ? 'btn' : 'btn secondary'}
            onClick={() => setModoImport('json')}
          >
            JSON (una ruta)
          </button>{' '}
          <button
            className={modoImport === 'csv' ? 'btn' : 'btn secondary'}
            onClick={() => setModoImport('csv')}
          >
            CSV (varias rutas de un dia)
          </button>
        </div>

        {modoImport === 'json' && (
          <>
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
          </>
        )}

        {modoImport === 'csv' && (
          <>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => {
                setArchivoCsv(e.target.files?.[0] || null)
                setResultadoCsv(null)
              }}
            />{' '}
            <button className="btn" onClick={handleSubirCsv} disabled={subiendoCsv}>
              {subiendoCsv ? 'Subiendo...' : 'Subir CSV'}
            </button>

            <p style={{ fontSize: 12, color: '#6b7280', marginTop: 10 }}>
              Una fila = un pedido dentro de una parada dentro de una ruta. Varias filas con el
              mismo <code>codigo_ruta</code> forman la misma ruta; varias filas con la misma{' '}
              <code>secuencia</code> forman la misma parada (con varios productos). Puedes cargar
              todas las rutas de un dia completo en un solo archivo.
            </p>
            <details style={{ fontSize: 12, color: '#6b7280' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Ver columnas del CSV</summary>
              <p style={{ marginBottom: 4 }}>
                <strong>Obligatorias:</strong> {COLUMNAS_CSV_OBLIGATORIAS.join(', ')}
              </p>
              <p>
                <strong>Opcionales</strong> (se pueden dejar vacias): {COLUMNAS_CSV_OPCIONALES.join(', ')}
              </p>
              <p>
                Los datos se identifican por codigo (Centro de Distribucion, Cliente, Producto) o por
                nombre (Transportista, Tipo de Camion, Tarifa de Transportista) -- los mismos que ves en
                sus respectivas pantallas, no por ID interno.
              </p>
              <p>
                Para CSV de <strong>ejecutada</strong>: no se indica ningun ID de ruta planificada; el
                <code>codigo_ruta</code> debe coincidir con el de una ruta planificada ya importada (misma
                convencion que ya usa el resto del sistema).
              </p>
              <p>Descarga ejemplos reales listos para subir en <code>backend/ejemplos_csv/</code>.</p>
            </details>

            {resultadoCsv && (
              <div style={{ marginTop: 12 }}>
                <p style={{ fontWeight: 600 }}>
                  {resultadoCsv.total_ok} ruta(s) importada(s), {resultadoCsv.total_error} con error.
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Codigo ruta</th>
                      <th>Estado</th>
                      <th>Detalle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultadoCsv.rutas_importadas.map((r, idx) => (
                      <tr key={idx}>
                        <td>{r.codigo_ruta}</td>
                        <td style={{ color: r.ok ? '#166534' : '#b91c1c', fontWeight: 600 }}>
                          {r.ok ? 'OK' : 'Error'}
                        </td>
                        <td>
                          {r.ok
                            ? `Ruta ID ${r.ruta_id}, costo $${r.costo_flete_calculado?.toLocaleString()}`
                            : r.error}
                        </td>
                      </tr>
                    ))}
                    {resultadoCsv.errores_filas.map((e, idx) => (
                      <tr key={`err-${idx}`}>
                        <td>{e.codigo_ruta || '-'}</td>
                        <td style={{ color: '#b91c1c', fontWeight: 600 }}>Error de fila</td>
                        <td>
                          {e.fila ? `Fila ${e.fila}: ` : ''}
                          {e.error}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {mensaje && (
          <p style={{ color: mensaje.tipo === 'error' ? '#b91c1c' : '#166534', fontWeight: 600 }}>
            {mensaje.texto}
          </p>
        )}
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
                            paradas={rutaExpandidaDetalle.paradas}
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
