import CrudTable from '../components/CrudTable.jsx'

export default function ProductosPage() {
  return (
    <CrudTable
      endpoint="/productos/"
      title="Productos"
      subtitle="Catalogo de productos con peso y volumen unitario"
      columns={[
        { key: 'id', label: 'ID' },
        { key: 'codigo', label: 'Codigo' },
        { key: 'nombre', label: 'Nombre' },
        { key: 'peso_unitario_kg', label: 'Peso Unit. (kg)' },
        { key: 'volumen_unitario_m3', label: 'Volumen Unit. (m3)' },
      ]}
      fields={[
        { key: 'nombre', label: 'Nombre', required: true },
        { key: 'codigo', label: 'Codigo' },
        { key: 'peso_unitario_kg', label: 'Peso Unit. (kg)', type: 'number', required: true },
        { key: 'volumen_unitario_m3', label: 'Volumen Unit. (m3)', type: 'number', required: true },
      ]}
    />
  )
}
