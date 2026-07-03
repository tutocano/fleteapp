import { useEffect, useState } from 'react'
import api from '../api/client.js'

const ROLES = ['SUPER_ADMIN', 'EMPRESA_ADMIN', 'INTERFAZ', 'USUARIO_FINAL']
const VACIO = { nombre: '', email: '', rol: 'EMPRESA_ADMIN', empresa_id: '', activo: true, password: '' }

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([])
  const [empresas, setEmpresas] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(VACIO)
  const [showForm, setShowForm] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [u, e] = await Promise.all([api.get('/usuarios/'), api.get('/empresas/')])
      setUsuarios(u.data)
      setEmpresas(e.data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const nombreEmpresa = (empresaId) => empresas.find((e) => e.id === empresaId)?.nombre || '-'

  const startCreate = () => {
    setForm(VACIO)
    setEditingId(null)
    setShowForm(true)
  }

  const startEdit = (u) => {
    setForm({ ...u, empresa_id: u.empresa_id ?? '', password: '' })
    setEditingId(u.id)
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const requiereEmpresa = form.rol !== 'SUPER_ADMIN'
      const payload = {
        nombre: form.nombre,
        rol: form.rol,
        empresa_id: requiereEmpresa ? Number(form.empresa_id) : null,
        activo: form.activo,
      }
      if (editingId) {
        if (form.password) payload.password = form.password
        await api.put(`/usuarios/${editingId}`, payload)
      } else {
        await api.post('/usuarios/', { ...payload, email: form.email, password: form.password })
      }
      setShowForm(false)
      await load()
    } catch (err) {
      alert('Error guardando: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Confirma eliminar el usuario ' + id + '?')) return
    try {
      await api.delete(`/usuarios/${id}`)
      await load()
    } catch (err) {
      alert('Error eliminando: ' + (err.response?.data?.detail || err.message))
    }
  }

  return (
    <div>
      <div className="page-title">Usuarios</div>
      <div className="page-subtitle">
        Solo SUPER_ADMIN puede crear usuarios y asignarles rol + empresa. Un usuario
        pertenece a una sola empresa (SUPER_ADMIN no pertenece a ninguna en particular).
      </div>

      <div className="card">
        <button className="btn" onClick={startCreate}>
          + Nuevo usuario
        </button>
      </div>

      {showForm && (
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <label>
                Nombre
                <input
                  value={form.nombre}
                  required
                  onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
                />
              </label>
              <label>
                Correo
                <input
                  type="email"
                  value={form.email}
                  required
                  disabled={!!editingId}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                />
              </label>
              <label>
                Rol
                <select
                  value={form.rol}
                  onChange={(e) => setForm((f) => ({ ...f, rol: e.target.value }))}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </label>
              {form.rol !== 'SUPER_ADMIN' && (
                <label>
                  Empresa
                  <select
                    value={form.empresa_id}
                    required
                    onChange={(e) => setForm((f) => ({ ...f, empresa_id: e.target.value }))}
                  >
                    <option value="">-- Seleccione --</option>
                    {empresas.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.nombre}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label>
                {editingId ? 'Nueva contrasena (dejar vacio para no cambiar)' : 'Contrasena'}
                <input
                  type="password"
                  value={form.password}
                  required={!editingId}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
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
                <th>ID</th>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Empresa</th>
                <th>Activo</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.nombre}</td>
                  <td>{u.email}</td>
                  <td>{u.rol}</td>
                  <td>{u.empresa_id ? nombreEmpresa(u.empresa_id) : '-'}</td>
                  <td>{u.activo ? 'Si' : 'No'}</td>
                  <td>
                    <button className="btn secondary" onClick={() => startEdit(u)}>
                      Editar
                    </button>{' '}
                    <button className="btn secondary" onClick={() => handleDelete(u.id)}>
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
              {usuarios.length === 0 && (
                <tr>
                  <td colSpan={7}>Sin usuarios.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
