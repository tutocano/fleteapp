import { useEffect, useState } from 'react'
import api from '../api/client.js'
import { ZonaPoligonoEditor } from '../components/PoligonoDrawMap.jsx'

const FORM_VACIO = { nombre: '', descripcion: '', tarifa_zona: 0 }

export default function ZonasPage() {
  const [zonas, setZonas] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [poligono, setPoligono] = useState(null)

  const load = async () => {
    setLoading(true)
    const res = await api.get('/zonas-geograficas/')
    setZonas(res.data)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const startCreate = () => {
    setForm(FORM_VACIO)
    setPoligono(null)
    setEditingId(null)
    setShowForm(true)
  }

  const startEdit = (z) => {
    setForm({ nombre: z.nombre, descripcion: z.descripcion || '', tarifa_zona: z.tarifa_zona })
    setPoligono(z.poligono || null)
    setEditingId(z.id)
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      tarifa_zona: Number(form.tarifa_zona) || 0,
      poligono,
    }
    try {
      if (editingId) {
        await api.put(`/zonas-geograficas/${editingId}`, payload)
      } else {
        await api.post('/zonas-geograficas/', payload)
      }
      setShowForm(false)
      await load()
    } catch (err) {
      alert('Error guardando: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Eliminar zona ' + id + '?')) return
    try {
      await api.delete(`/zonas-geograficas/${id}`)
      await load()
    } catch (err) {
      alert('Error eliminando: ' + (err.response?.data?.detail || err.message))
    }
  }

  return (
    <div>
      <div className="page-title">Zonas Geograficas</div>
      <div className="page-subtitle">
        Zonas usadas para el metodo de tarifa "por zona de entrega". Dibuja el poligono de cada
        zona directamente sobre el mapa -- no tiene que coincidir con la division administrativa
        oficial de la ciudad, es la zona tal como tu la definas.
      </div>

      <div className="card">
        <button className="btn" onClick={startCreate}>
          + Nueva Zona
        </button>
      </div>

      {showForm && (
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <label>
                Nombre
                <input
                  required
                  value={form.nombre}
                  onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
                />
              </label>
              <label>
                Descripcion
                <input
                  value={form.descripcion}
                  onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))}
                />
              </label>
              <label>
                Tarifa base
                <input
                  type="number"
                  step="any"
                  value={form.tarifa_zona}
                  onChange={(e) => setForm((f) => ({ ...f, tarifa_zona: e.target.value }))}
                />
              </label>
            </div>

            <div style={{ margin: '12px 0 4px' }}>
              <strong>Poligono de la zona</strong>
              <div className="page-subtitle" style={{ margin: '4px 0' }}>
                Haz click en el mapa para ir agregando vertices (minimo 3). Arrastra un vertice
                para moverlo, click derecho para borrarlo. Se guarda un solo poligono por zona.
              </div>
              <ZonaPoligonoEditor
                key={editingId ?? 'nueva'}
                poligonoInicial={poligono}
                onChange={setPoligono}
              />
            </div>

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
                <th>Nombre</th>
                <th>Descripcion</th>
                <th>Tarifa base</th>
                <th>Poligono</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {zonas.map((z) => (
                <tr key={z.id}>
                  <td>{z.id}</td>
                  <td>{z.nombre}</td>
                  <td>{z.descripcion}</td>
                  <td>{z.tarifa_zona}</td>
                  <td>
                    {z.poligono && z.poligono.length > 2
                      ? `${z.poligono.length} vertices`
                      : 'Sin dibujar'}
                  </td>
                  <td>
                    <button className="btn secondary" onClick={() => startEdit(z)}>
                      Editar
                    </button>{' '}
                    <button className="btn secondary" onClick={() => handleDelete(z.id)}>
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
              {zonas.length === 0 && (
                <tr>
                  <td colSpan={6}>Sin registros.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
