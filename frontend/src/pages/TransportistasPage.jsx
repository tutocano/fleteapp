import CrudTable from '../components/CrudTable.jsx'

export default function TransportistasPage() {
  return (
    <CrudTable
      endpoint="/transportistas/"
      title="Transportistas"
      subtitle="Empresas de transporte externas que prestan el servicio de flete"
      columns={[
        { key: 'id', label: 'ID' },
        { key: 'nombre', label: 'Nombre' },
        { key: 'nit', label: 'NIT' },
        { key: 'contacto', label: 'Contacto' },
        { key: 'telefono', label: 'Telefono' },
      ]}
      fields={[
        { key: 'nombre', label: 'Nombre', required: true },
        { key: 'nit', label: 'NIT' },
        { key: 'contacto', label: 'Contacto' },
        { key: 'telefono', label: 'Telefono' },
      ]}
    />
  )
}
