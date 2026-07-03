import { useEffect, useState } from 'react'
import api from '../api/client.js'

/**
 * v3: matriz transportista x zona geografica para marcar que zonas atiende cada
 * transportista. Es puramente informativo (no bloquea el import de rutas) --
 * decision explicita del usuario. Cada click guarda de inmediato via PUT
 * (reemplaza el conjunto completo de zonas del transportista).
 */
export default function CoberturaZonasPage() {
  const [transportistas, setTransportistas] = useState([])
  const [zonas, setZonas] = useState([])
  const [cobertura, setCobertura] = useState({})
  const [loading, setLoading] = useState(true)
  const [savingKey, setSavingKey] = useState(null)

  const load = async () => {
    setLoading(true)
    const [tr, zo] = await Promise.all([
      api.get('/transportistas/'),
      api.get('/zonas-geograficas/'),
    ])
    setTransportistas(tr.data)
    setZonas(zo.data)
    const cob = {}
    tr.data.forEach((t) => {
      cob[t.id] = new Set((t.zonas_cobertura || []).map((c) => c.zona_geografica_id))
    })
    setCobertura(cob)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const toggle = async (transportistaId, zonaId) => {
    const actuales = new Set(cobertura[transportistaId] || [])
    if (actuales.has(zonaId)) {
      actuales.delete(zonaId)
    } else {
      actuales.add(zonaId)
    }

    setCobertura((c) => ({ ...c, [transportistaId]: actuales }))
    const key = `${transportistaId}-${zonaId}`
    setSavingKey(key)
    try {
      await api.put(`/transportistas/${transportistaId}/zonas-cobertura`, {
        zona_geografica_ids: Array.from(actuales),
      })
    } catch (err) {
      alert('Error guardando cobertura: ' + (err.response?.data?.detail || err.message))
      await load()
    } finally {
      setSavingKey(null)
    }
  }

  return (
    <div>
      <div className="page-title">Cobertura de Zonas por Transportista</div>
      <div className="page-subtitle">
        Marca que zonas geograficas atiende cada transportista. Es informativo: no bloquea la
        importacion de rutas, sirve como referencia al elegir que transportista asignar.
      </div>

      <div className="card">
        {loading ? (
          <p>Cargando...</p>
        ) : zonas.length === 0 ? (
          <p>No hay zonas geograficas creadas todavia. Ve a "Zonas Geograficas" para crear alguna.</p>
        ) : transportistas.length === 0 ? (
          <p>No hay transportistas creados todavia.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Transportista</th>
                {zonas.map((z) => (
                  <th key={z.id}>{z.nombre}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {transportistas.map((t) => (
                <tr key={t.id}>
                  <td>{t.nombre}</td>
                  {zonas.map((z) => {
                    const marcado = cobertura[t.id]?.has(z.id) || false
                    const key = `${t.id}-${z.id}`
                    return (
                      <td key={z.id} style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={marcado}
                          disabled={savingKey === key}
                          onChange={() => toggle(t.id, z.id)}
                        />
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
