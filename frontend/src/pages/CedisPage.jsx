import CrudTable from '../components/CrudTable.jsx'

export default function CedisPage() {
  return (
    <CrudTable
      endpoint="/centros-distribucion/"
      title="Centros de Distribucion (CEDIs)"
      subtitle="Bodegas desde donde parten las rutas, con geoposicion"
      columns={[
        { key: 'id', label: 'ID' },
        { key: 'codigo', label: 'Codigo' },
        { key: 'nombre', label: 'Nombre' },
        { key: 'latitud', label: 'Latitud' },
        { key: 'longitud', label: 'Longitud' },
        { key: 'direccion', label: 'Direccion' },
      ]}
      fields={[
        { key: 'nombre', label: 'Nombre', required: true },
        { key: 'codigo', label: 'Codigo' },
        { key: 'latitud', label: 'Latitud', type: 'number', required: true },
        { key: 'longitud', label: 'Longitud', type: 'number', required: true },
        { key: 'direccion', label: 'Direccion' },
      ]}
    />
  )
}
