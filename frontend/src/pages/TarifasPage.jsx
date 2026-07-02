import { useEffect, useState } from 'react'
import api from '../api/client.js'

export default function TarifasPage() {
  const [tarifas, setTarifas] = useState([])
  const [transportistas, setTransportistas] = useState([])
  const [metodos, setMetodos] = useState([])
  const [zonas, setZonas] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({
    transportista_id: '',
    metodo_tarifa_id: '',
    nombre: '',
    valor_unitario: 0,
    unidad: '',
    activo: true,
  })
  const [zonasDetalle, setZonasDetalle] = useState({})

  const load = async () => {
    setLoading(true)
    const [t, tr, m, z] = await Promise.all([
      api.get('/tarifas-transportista/'),
      api.get('/transportistas/'),
      api.get('/metodos-tarifa/'),
      api.get('/zonas-geograficas/'),
    ])
    setTarifas(t.data)
    setTransportistas(tr.data)
    setMetodos(m.data)
    setZonas(z.data)
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
    setForm(item)
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

  return (
    <div>
      <div className="page-title">Tarifas de Transportista</div>
      <div className="page-subtitle">
        Cada transportista puede ofrecer varios metodos de calculo de flete, cada uno con su propia tarifa.
        Para el metodo "Por zona", se define una tarifa especifica por cada zona geografica.
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
