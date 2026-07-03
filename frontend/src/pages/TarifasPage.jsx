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
  // v3: ediciones pendientes de la matriz zona x tipo de camion, sin guardar todavia.
  // Clave: "transportistaId|camionKey|zonaId" (camionKey='' = cualquier camion) -> string.
  const [pendientes, setPendientes] = useState({})
  const [guardandoMatriz, setGuardandoMatriz] = useState(null)

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

  // v3: matriz editable zona x tipo de camion para el metodo POR_ZONA. El modelo ya
  // soporta esta combinacion sin cambios de backend: tipo_camion_id vive en la tarifa
  // (TarifaTransportista) y zonas_detalle es propio de cada fila de tarifa, asi que
  // basta con crear/actualizar una tarifa POR_ZONA por cada tipo de camion. Se muestra
  // un transportista por tabla, con TODOS los transportistas (no solo los que ya
  // tienen una tarifa por zona) para poder crear la primera desde aqui mismo.
  const idMetodoZona = metodos.find((m) => m.codigo === 'POR_ZONA')?.id
  const tarifasPorZonaPorTransportista = {}
  transportistas.forEach((t) => {
    tarifasPorZonaPorTransportista[t.id] = []
  })
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

  const pendienteKey = (transportistaId, camionKey, zonaId) =>
    `${transportistaId}|${camionKey}|${zonaId}`

  const valorInputMatriz = (transportistaId, camionKey, zonaId, tarifasDelTr) => {
    const key = pendienteKey(transportistaId, camionKey, zonaId)
    if (key in pendientes) return pendientes[key]
    const v = valorCelda(tarifasDelTr, camionKey === '' ? '' : Number(camionKey), zonaId)
    return v === null ? '' : String(v)
  }

  const cambiarCeldaMatriz = (transportistaId, camionKey, zonaId, valor) => {
    setPendientes((p) => ({ ...p, [pendienteKey(transportistaId, camionKey, zonaId)]: valor }))
  }

  const hayPendientesPara = (transportistaId) =>
    Object.keys(pendientes).some((k) => k.startsWith(`${transportistaId}|`))

  const guardarMatriz = async (transportistaId, tarifasDelTr) => {
    const prefijo = `${transportistaId}|`
    const grupos = {} // camionKey -> { zonaId: valorString }
    Object.entries(pendientes).forEach(([key, valor]) => {
      if (!key.startsWith(prefijo)) return
      const [, camionKey, zonaId] = key.split('|')
      grupos[camionKey] = grupos[camionKey] || {}
      grupos[camionKey][zonaId] = valor
    })
    if (Object.keys(grupos).length === 0) return

    setGuardandoMatriz(transportistaId)
    try {
      for (const [camionKey, edits] of Object.entries(grupos)) {
        const camionId = camionKey === '' ? null : Number(camionKey)
        const existente = tarifasDelTr.find((t) => (t.tipo_camion_id ?? '') === (camionKey === '' ? '' : Number(camionKey)))
        const zonasMap = {}
        ;(existente?.zonas_detalle || []).forEach((zd) => {
          zonasMap[zd.zona_geografica_id] = zd.valor
        })
        Object.entries(edits).forEach(([zonaId, valor]) => {
          if (valor === '') delete zonasMap[zonaId]
          else zonasMap[zonaId] = Number(valor)
        })
        const payload = {
          transportista_id: transportistaId,
          metodo_tarifa_id: idMetodoZona,
          tipo_camion_id: camionId,
          nombre:
            existente?.nombre ||
            `Por zona - ${nombreTransportista(transportistaId)}${
              camionId ? ' - ' + nombreTipoCamion(camionId) : ' (cualquier camion)'
            }`,
          valor_unitario: existente?.valor_unitario ?? 0,
          unidad: existente?.unidad || 'ZONA',
          activo: existente?.activo ?? true,
          zonas_detalle: Object.entries(zonasMap).map(([zonaId, valor]) => ({
            zona_geografica_id: Number(zonaId),
            valor,
          })),
        }
        if (existente) {
          await api.put(`/tarifas-transportista/${existente.id}`, payload)
        } else {
          await api.post('/tarifas-transportista/', payload)
        }
      }
      setPendientes((p) => {
        const nuevo = { ...p }
        Object.keys(nuevo).forEach((k) => {
          if (k.startsWith(prefijo)) delete nuevo[k]
        })
        return nuevo
      })
      await load()
    } catch (err) {
      alert('Error guardando la matriz: ' + (err.response?.data?.detail || err.message))
    } finally {
      setGuardandoMatriz(null)
    }
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

      {!loading && zonas.length > 0 && transportistas.length > 0 && (
        <div className="card">
          <strong>Matriz Zona x Tipo de Camion (metodo "Por zona")</strong>
          <div className="page-subtitle" style={{ margin: '4px 0 12px' }}>
            Edita directamente el valor de cada zona para cada tipo de camion (columna
            "Cualquier camion" = tarifa sin restriccion de camion). Deja una celda vacia para
            quitar ese valor. Los cambios de una fila de transportista se guardan juntos con el
            boton "Guardar cambios" de esa tabla -- si la combinacion zona/camion no tenia tarifa
            todavia, se crea una nueva automaticamente.
          </div>
          {Object.entries(tarifasPorZonaPorTransportista).map(([transportistaIdStr, tarifasDelTr]) => {
            const transportistaId = Number(transportistaIdStr)
            return (
              <div key={transportistaId} style={{ marginBottom: 16 }}>
                <div style={{ fontWeight: 600, margin: '8px 0 4px' }}>
                  {nombreTransportista(transportistaId)}
                </div>
                <table>
                  <thead>
                    <tr>
                      <th>Zona</th>
                      {columnasCamion.map((c) => (
                        <th key={c.id === '' ? 'cualquiera' : c.id}>{c.nombre}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {zonas.map((z) => (
                      <tr key={z.id}>
                        <td>{z.nombre}</td>
                        {columnasCamion.map((c) => (
                          <td key={c.id === '' ? 'cualquiera' : c.id} style={{ textAlign: 'center' }}>
                            <input
                              type="number"
                              step="any"
                              placeholder="-"
                              style={{ width: 90 }}
                              value={valorInputMatriz(transportistaId, c.id, z.id, tarifasDelTr)}
                              onChange={(e) => cambiarCeldaMatriz(transportistaId, c.id, z.id, e.target.value)}
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <button
                  type="button"
                  className="btn"
                  style={{ marginTop: 8 }}
                  disabled={!hayPendientesPara(transportistaId) || guardandoMatriz === transportistaId}
                  onClick={() => guardarMatriz(transportistaId, tarifasDelTr)}
                >
                  {guardandoMatriz === transportistaId ? 'Guardando...' : 'Guardar cambios'}
                </button>
              </div>
            )
          })}
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
