import CrudTable from '../components/CrudTable.jsx'

export default function EmpresaPage() {
  return (
    <CrudTable
      endpoint="/empresas/"
      title="Empresa"
      subtitle="Datos generales de la compania"
      columns={[
        { key: 'id', label: 'ID' },
        { key: 'nombre', label: 'Nombre' },
        { key: 'nit', label: 'NIT' },
        { key: 'direccion', label: 'Direccion' },
        { key: 'telefono', label: 'Telefono' },
        { key: 'email', label: 'Email' },
      ]}
      fields={[
        { key: 'nombre', label: 'Nombre', required: true },
        { key: 'nit', label: 'NIT' },
        { key: 'direccion', label: 'Direccion' },
        { key: 'telefono', label: 'Telefono' },
        { key: 'email', label: 'Email' },
      ]}
    />
  )
}
