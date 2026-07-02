import { useEffect, useState } from 'react'
import api from '../api/client.js'
import CrudTable from '../components/CrudTable.jsx'

export default function FlotaPage() {
  const [transportistas, setTransportistas] = useState([])
  const [tiposCamion, setTiposCamion] = useState([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    Promise.all([api.get('/transportistas/'), api.get('/tipos-camion/')]).then(([t, tc]) => {
      setTransportistas(t.data)
      setTiposCamion(tc.data)
      setReady(true)
    })
  }, [])

  if (!ready) return <p>Cargando catalogos...</p>

  return (
    <CrudTable
      endpoint="/flota/"
      title="Flota"
      subtitle="Vehiculos disponibles por transportista y tipo de camion"
      columns={[
        { key: 'id', label: 'ID' },
        { key: 'placa', label: 'Placa' },
        { key: 'transportista_id', label: 'Transportista ID' },
        { key: 'tipo_camion_id', label: 'Tipo Camion ID' },
        { key: 'descripcion', label: 'Descripcion' },
        { key: 'activo', label: 'Activo', render: (i) => (i.activo ? 'Si' : 'No') },
      ]}
      fields={[
        {
          key: 'transportista_id',
          label: 'Transportista',
          type: 'select',
          required: true,
          options: transportistas.map((t) => ({ value: t.id, label: t.nombre })),
        },
        {
          key: 'tipo_camion_id',
          label: 'Tipo de Camion',
          type: 'select',
          required: true,
          options: tiposCamion.map((t) => ({ value: t.id, label: t.nombre })),
        },
        { key: 'placa', label: 'Placa' },
        { key: 'descripcion', label: 'Descripcion' },
        { key: 'activo', label: 'Activo', type: 'checkbox' },
      ]}
      defaultValues={{ activo: true }}
    />
  )
}
