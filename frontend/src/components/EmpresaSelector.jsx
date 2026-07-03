import { useEffect, useState } from 'react'
import api from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'

/**
 * Solo para SUPER_ADMIN: elige "viendo datos de la empresa X" (o "todas") y
 * queda guardado en localStorage -- el interceptor de axios (api/client.js)
 * agrega automaticamente ?empresa_id= a cada request mientras haya una
 * seleccion activa. Ver auth.empresa_actual en el backend.
 */
export default function EmpresaSelector() {
  const { empresaSeleccionada, setEmpresaSeleccionada } = useAuth()
  const [empresas, setEmpresas] = useState([])

  useEffect(() => {
    api.get('/empresas/').then((res) => setEmpresas(res.data))
  }, [])

  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      Viendo datos de:
      <select
        value={empresaSeleccionada}
        onChange={(e) => setEmpresaSeleccionada(e.target.value)}
      >
        <option value="">Todas las empresas</option>
        {empresas.map((e) => (
          <option key={e.id} value={e.id}>
            {e.nombre}
          </option>
        ))}
      </select>
    </label>
  )
}
