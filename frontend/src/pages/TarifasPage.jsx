import { useEffect, useState } from 'react'
import api from '../api/client.js'

export default function TarifasPage() {
  const [tarifas, setTarifas] = useState([])
  const [transportistas, setTransportistas] = useState([])
  const [metodos, setMetodos] = useState([])
  const [zonas, setZonas] = useState([])
  const [tiposCamion, setTiposCamion] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({
    transportista_id: '',
    metodo_tarifa_id: '',
    tipo_camion_id: '',
    nombre: '',
    valor_unitario: 0,
    unidad: '',
    activo: true,
  })
  const [zonasDetalle, setZonasDetalle] = useState({})

  const load = async () => {
    setLoading(true)
    const [t, tr, m, z, tc] = await Promise.all([
      api.get('/tarifas-transportista/'),
      api.get('/transportistas/'),
      api.get('/metodos-tarifa/'),
      api.get('/zonas-geograficas/'),
      api.get('/tipos-camion/'),
    ])
    setTarifas(t.data)
    setTransportistas(tr.data)
    setMetodos(m.data)
    setZonas(z.data)
    setTiposCamion(tc.data)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const metodoCodigo = (id) => metodos.find((m) => m.id === Number(id))?.codigo

  const isZona = metodoCodigo(form.metodo_tarifa_id) === 'POR_ZONA'

  const startCreate = () => {
    setForm({
      transportista_id: '',
      metodo_tarifa_id: '',
      tipo_camion_id: '',
      nombre: '',
      valor_unitario: 0,
      unidad: '',
      activo: true,
    })
    setZonasDetalle({})
    setEditingId(null)
    setShowForm(true)
  }

  const startEdit = (item) => {
    setForm({ ...item, tipo_camion_id: item.tipo_camion_id ?? '' })
    const zd = {}
    ;(item.zonas_detalle || []).forEach((z) => {
      zd[z.zona_geografica_id] = z.valor
    })
    setZonasDetalle(zd)
    setEditingId(item.id)
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      transportista_id: Number(form.transportista_id),
      metodo_tarifa_id: Number(form.metodo_tarifa_id),
      tipo_camion_id: form.tipo_camion_id === '' ? null : Number(form.tipo_camion_id),
      valor_unitario: Number(form.valor_unitario) || 0,
    }
    if (isZona) {
      payload.zonas_detalle = Object.entries(zonasDetalle)
        .filter(([, v]) => v !== '' && v !== undefined)
        .map(([zonaId, valor]) => ({ zona_geografica_id: Number(zonaId), valor: Number(valor) }))
    }
    try {
      if (editingId) {
        await api.put(`/tarifas-transportista/${editingId}`, payload)
      } else {
        await api.post('/tarifas-transportista/', payload)
      }
      setShowForm(false)
      await load()
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Eliminar tarifa ' + id + '?')) return
    await api.delete(`/tarifas-transportista/${id}`)
    await load()
  }

  const nombreTransportista = (id) => transportistas.find((t) => t.id === id)?.nombre || id
  const nombreMetodo = (id) => metodos.find((m) => m.id === id)?.nombre || id
  const nombreTipoCamion = (id) => (id ? tiposCamion.find((tc) => tc.id === id)?.nombre || id : 'Cualquier camion')

  // v3: matriz zona x tipo de camion para el metodo POR_ZONA. El modelo ya soporta
  // esta combinacion sin cambios de backend: tipo_camion_id vive en la tarifa
  // (TarifaTransportista) y zonas_detalle es propio de cada fila de tarifa, asi
  // que basta con crear una tarifa POR_ZONA por cada tipo de camion. Esta vista
  // solo agrupa lo ya creado para verlo de un vistazo y detectar huecos.
  const idMetodoZona = metodos.find((m) => m.codigo === 'POR_ZONA')?.id
  const tarifasPorZonaPorTransportista = {}
  tarifas
    .filter((t) => t.metodo_tarifa_id === idMetodoZona)
    .forEach((t) => {
      tarifasPorZonaPorTransportista[t.transportista_id] =
        tarifasPorZonaPorTransportista[t.transportista_id] || []
      tarifasPorZonaPorTransportista[t.transportista_id].push(t)
    })
  const columnasCamion = [{ id: '', nombre: 'Cualquier camion' }, ...tiposCamion]
  const valorCelda = (tarifasDelTransportista, camionId, zonaId) => {
    const tarifa = tarifasDelTransportista.find(
      (t) => (t.tipo_camion_id ?? '') === camionId
    )
    if (!tarifa) return null
    const zd = (tarifa.zonas_detalle || []).find((z) => z.zona_geografica_id === zonaId)
    return zd ? zd.valor : null
  }

  return (
    <div>
      <div className="page-title">Tarifas de Transportista</div>
      <div className="page-subtitle">
        Cada transportista puede ofrecer varios metodos de calculo de flete, cada uno con su propia tarifa.
        Para el metodo "Por zona", se define una tarifa especifica por cada zona geografica.
        Opcionalmente cada tarifa puede restringirse a un tipo de camion especifico (ej. "Por viaje" con NHR
        puede valer distinto que "Por viaje" con Sencillo) -- si se deja en "Cualquier camion", aplica sin
        importar el camion usado en la ruta.
      </div>

      <div className="card">
        <button className="btn" onClick={startCreate}>
          + Nueva Tarifa
        </button>
      </div>

      {showForm && (
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <label>
                Transportista
                <select
                  required
                  value={form.transportista_id}
                  onChange={(e) => setForm((f) => ({ ...f, transportista_id: e.target.value }))}
                >
                  <option value="">-- Seleccione --</option>
                  {transportistas.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Metodo de Tarifa
                <select
                  required
                  value={form.metodo_tarifa_id}
                  onChange={(e) => setForm((f) => ({ ...f, metodo_tarifa_id: e.target.value }))}
                >
                  <option value="">-- Seleccione --</option>
                  {metodos.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Tipo de camion (opcional)
                <select
                  value={form.tipo_camion_id}
                  onChange={(e) => setForm((f) => ({ ...f, tipo_camion_id: e.target.value }))}
                >
                  <option value="">-- Cualquier camion --</option>
                  {tiposCamion.map((tc) => (
                    <option key={tc.id} value={tc.id}>
                      {tc.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Nombre de la tarifa
                <input
                  required
                  value={form.nombre}
                  onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
                />
              </label>
              {!isZona && (
                <label>
                  Valor unitario
                  <input
                    type="number"
                    step="any"
                    value={form.valor_unitario}
                    onChange={(e) => setForm((f) => ({ ...f, valor_unitario: e.target.value }))}
                  />
                </label>
              )}
              <label>
                Unidad (ej: VIAJE, PARADA, KG, M3, MINUTO, HORA)
                <input
                  value={form.unidad || ''}
                  onChange={(e) => setForm((f) => ({ ...f, unidad: e.target.value }))}
                />
              </label>
              <label>
                Activo
                <input
                  type="checkbox"
                  checked={!!form.activo}
                  onChange={(e) => setForm((f) => ({ ...f, activo: e.target.checked }))}
                />
              </label>
            </div>

            {isZona && (
              <div className="card" style={{ background: '#f9fafb' }}>
                <strong>Tarifa por zona (se aplica la MAS COSTOSA entre los clientes de la ruta)</strong>
                <div className="form-grid">
                  {zonas.map((z) => (
                    <label key={z.id}>
                      {z.nombre}
                      <input
                        type="number"
                        step="any"
                        value={zonasDetalle[z.id] ?? ''}
                        onChange={(e) =>
                          setZonasDetalle((zd) => ({ ...zd, [z.id]: e.target.value }))
                        }
                      />
                    </label>
                  ))}
                </div>
              </div>
            )}

            <button className="btn" type="submit">
              {editingId ? 'Actualizar' : 'Crear'}
            </button>{' '}
            <button className="btn secondary" type="button" onClick={() => setShowForm(false)}>
              Cancelar
            </button>
          </form>
        </div>
      )}

      {!loading && zonas.length > 0 && Object.keys(tarifasPorZonaPorTransportista).length > 0 && (
        <div className="card">
          <strong>Matriz Zona x Tipo de Camion (metodo "Por zona")</strong>
          <div className="page-subtitle" style={{ margin: '4px 0 12px' }}>
            Resumen de las tarifas POR_ZONA ya creadas, por transportista. Cada celda es el valor
            de esa zona para ese tipo de camion (columna "Cualquier camion" = tarifa sin
            restriccion de camion). "-" significa que no existe una tarifa para esa combinacion.
          </div>
          {Object.entries(tarifasPorZonaPorTransportista).map(([transportistaId, tarifasDelTr]) => (
            <div key={transportistaId} style={{ marginBottom: 16 }}>
              <div style={{ fontWeight: 600, margin: '8px 0 4px' }}>
                {nombreTransportista(Number(transportistaId))}
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Zona</th>
                    {columnasCamion.map((c) => (
                      <th key={c.id || 'cualquiera'}>{c.nombre}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {zonas.map((z) => (
                    <tr key={z.id}>
                      <td>{z.nombre}</td>
                      {columnasCamion.map((c) => {
                        const valor = valorCelda(tarifasDelTr, c.id, z.id)
                        return (
                          <td key={c.id || 'cualquiera'} style={{ textAlign: 'center' }}>
                            {valor === null ? (
                              <span style={{ color: '#9ca3af' }}>-</span>
                            ) : (
                              valor.toLocaleString()
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        {loading ? (
          <p>Cargando...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Transportista</th>
                <th>Metodo</th>
                <th>Tipo de Camion</th>
                <th>Nombre</th>
                <th>Valor Unitario</th>
                <th>Unidad</th>
                <th>Detalle Zonas</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {tarifas.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td>{nombreTransportista(t.transportista_id)}</td>
                  <td>{nombreMetodo(t.metodo_tarifa_id)}</td>
                  <td>{nombreTipoCamion(t.tipo_camion_id)}</td>
                  <td>{t.nombre}</td>
                  <td>{t.valor_unitario}</td>
                  <td>{t.unidad}</td>
                  <td>
                    {(t.zonas_detalle || [])
                      .map((z) => `${zonas.find((zz) => zz.id === z.zona_geografica_id)?.nombre}: ${z.valor}`)
                      .join(' | ')}
                  </td>
                  <td>
                    <button className="btn secondary" onClick={() => startEdit(t)}>
                      Editar
                    </button>{' '}
                    <button className="btn secondary" onClick={() => handleDelete(t.id)}>
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
