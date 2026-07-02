import CrudTable from '../components/CrudTable.jsx'

export default function ZonasPage() {
  return (
    <CrudTable
      endpoint="/zonas-geograficas/"
      title="Zonas Geograficas"
      subtitle="Zonas usadas para el metodo de tarifa 'por zona de entrega'"
      columns={[
        { key: 'id', label: 'ID' },
        { key: 'nombre', label: 'Nombre' },
        { key: 'descripcion', label: 'Descripcion' },
        { key: 'tarifa_zona', label: 'Tarifa base' },
      ]}
      fields={[
        { key: 'nombre', label: 'Nombre', required: true },
        { key: 'descripcion', label: 'Descripcion' },
        { key: 'tarifa_zona', label: 'Tarifa base', type: 'number', required: true },
      ]}
      defaultValues={{ tarifa_zona: 0 }}
    />
  )
}
