import { useEffect, useState } from 'react'
import api from '../api/client.js'
import CrudTable from '../components/CrudTable.jsx'

export default function ClientesPage() {
  const [tiposCliente, setTiposCliente] = useState([])
  const [zonas, setZonas] = useState([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    Promise.all([api.get('/tipos-cliente/'), api.get('/zonas-geograficas/')]).then(
      ([tc, z]) => {
        setTiposCliente(tc.data)
        setZonas(z.data)
        setReady(true)
      }
    )
  }, [])

  if (!ready) return <p>Cargando catalogos...</p>

  return (
    <CrudTable
      endpoint="/clientes/"
      title="Clientes"
      subtitle="Puntos de entrega con geoposicion y canal"
      columns={[
        { key: 'id', label: 'ID' },
        { key: 'codigo', label: 'Codigo' },
        { key: 'nombre', label: 'Nombre' },
        { key: 'canal', label: 'Canal' },
        { key: 'latitud', label: 'Latitud' },
        { key: 'longitud', label: 'Longitud' },
      ]}
      fields={[
        {
          key: 'tipo_cliente_id',
          label: 'Tipo Cliente',
          type: 'select',
          options: tiposCliente.map((t) => ({ value: t.id, label: t.nombre })),
        },
        {
          key: 'zona_geografica_id',
          label: 'Zona Geografica',
          type: 'select',
          options: zonas.map((z) => ({ value: z.id, label: z.nombre })),
        },
        { key: 'nombre', label: 'Nombre', required: true },
        { key: 'codigo', label: 'Codigo' },
        { key: 'latitud', label: 'Latitud', type: 'number', required: true },
        { key: 'longitud', label: 'Longitud', type: 'number', required: true },
        { key: 'direccion', label: 'Direccion' },
        { key: 'canal', label: 'Canal (texto libre)' },
      ]}
    />
  )
}
