import { useEffect, useState } from 'react'
import api from '../api/client.js'

/**
 * Componente generico de mantenimiento CRUD (tabla + formulario simple).
 *
 * props:
 *  - endpoint: string, ej "/clientes/"
 *  - title, subtitle: textos de cabecera
 *  - columns: [{ key, label, render? }]
 *  - fields: [{ key, label, type ("text"|"number"|"checkbox"|"select"), options?, required? }]
 *  - defaultValues: objeto con valores iniciales del formulario
 */
export default function CrudTable({ endpoint, title, subtitle, columns, fields, defaultValues = {} }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(defaultValues)
  const [showForm, setShowForm] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get(endpoint)
      setItems(res.data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint])

  const startCreate = () => {
    setForm(defaultValues)
    setEditingId(null)
    setShowForm(true)
  }

  const startEdit = (item) => {
    setForm(item)
    setEditingId(item.id)
    setShowForm(true)
  }

  const handleChange = (key, value, type) => {
    let v = value
    if (type === 'number') v = value === '' ? '' : Number(value)
    if (type === 'checkbox') v = value
    setForm((f) => ({ ...f, [key]: v }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...form }
      if (editingId) {
        await api.put(`${endpoint}${editingId}`, payload)
      } else {
        await api.post(endpoint, payload)
      }
      setShowForm(false)
      await load()
    } catch (e) {
      alert('Error guardando: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Confirma eliminar el registro ' + id + '?')) return
    try {
      await api.delete(`${endpoint}${id}`)
      await load()
    } catch (e) {
      alert('Error eliminando: ' + (e.response?.data?.detail || e.message))
    }
  }

  return (
    <div>
      <div className="page-title">{title}</div>
      <div className="page-subtitle">{subtitle}</div>

      <div className="card">
        <button className="btn" onClick={startCreate}>+ Nuevo</button>
      </div>

      {showForm && (
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              {fields.map((f) => (
                <label key={f.key}>
                  {f.label}
                  {f.type === 'select' ? (
                    <select
                      value={form[f.key] ?? ''}
                      required={f.required}
                      onChange={(e) => handleChange(f.key, e.target.value, f.type)}
                    >
                      <option value="">-- Seleccione --</option>
                      {(f.options || []).map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : f.type === 'checkbox' ? (
                    <input
                      type="checkbox"
                      checked={!!form[f.key]}
                      onChange={(e) => handleChange(f.key, e.target.checked, f.type)}
                    />
                  ) : (
                    <input
                      type={f.type || 'text'}
                      step={f.type === 'number' ? 'any' : undefined}
                      value={form[f.key] ?? ''}
                      required={f.required}
                      onChange={(e) => handleChange(f.key, e.target.value, f.type)}
                    />
                  )}
                </label>
              ))}
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
        {loading && <p>Cargando...</p>}
        {error && <p style={{ color: 'red' }}>Error: {error}</p>}
        {!loading && !error && (
          <table>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c.key}>{c.label}</th>
                ))}
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  {columns.map((c) => (
                    <td key={c.key}>{c.render ? c.render(item) : item[c.key]}</td>
                  ))}
                  <td>
                    <button className="btn secondary" onClick={() => startEdit(item)}>
                      Editar
                    </button>{' '}
                    <button className="btn secondary" onClick={() => handleDelete(item.id)}>
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={columns.length + 1}>Sin registros.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
