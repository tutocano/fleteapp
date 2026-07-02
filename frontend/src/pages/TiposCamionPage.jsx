import CrudTable from '../components/CrudTable.jsx'

export default function TiposCamionPage() {
  return (
    <CrudTable
      endpoint="/tipos-camion/"
      title="Tipos de Camion"
      subtitle="Catalogo de vehiculos con su capacidad de peso y volumen"
      columns={[
        { key: 'id', label: 'ID' },
        { key: 'nombre', label: 'Nombre' },
        { key: 'capacidad_peso_kg', label: 'Capacidad Peso (kg)' },
        { key: 'capacidad_volumen_m3', label: 'Capacidad Volumen (m3)' },
      ]}
      fields={[
        { key: 'nombre', label: 'Nombre', required: true },
        { key: 'capacidad_peso_kg', label: 'Capacidad Peso (kg)', type: 'number', required: true },
        { key: 'capacidad_volumen_m3', label: 'Capacidad Volumen (m3)', type: 'number', required: true },
      ]}
    />
  )
}
