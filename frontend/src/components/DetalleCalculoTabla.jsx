/**
 * Muestra de forma estructurada el detalle de calculo de flete de una ruta:
 * metodo de tarifa aplicado, valor unitario, cantidad/base de calculo y costo
 * total. Complementa (no reemplaza) el texto libre de `explicacion` que ya
 * devuelve el backend en `detalle_calculo.explicacion`.
 *
 * Espera un objeto `detalleCalculo` con la forma { metodo, explicacion, variables }
 * tal como lo devuelve `calcular_y_guardar` en el backend, y el costo total ya
 * calculado (costoTotal) para mostrarlo en la misma tabla.
 */

const ETIQUETAS_UNIDAD = {
  VIAJE: 'por viaje',
  PARADA: 'por parada',
  ZONA: '(tarifa de zona)',
  KG: '/kg',
  M3: '/m3',
  MINUTO: '/min',
  HORA: '/hora',
  KM: '/km',
}

function formatoMoneda(valor) {
  if (valor === null || valor === undefined) return '-'
  return `$${Number(valor).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`
}

function formatoCantidad(valor) {
  if (valor === null || valor === undefined) return '-'
  return Number(valor).toLocaleString('es-CO', { maximumFractionDigits: 2 })
}

function etiquetaBase(unidad) {
  switch (unidad) {
    case 'KM':
      return 'Distancia recorrida'
    case 'KG':
      return 'Peso total entregado'
    case 'M3':
      return 'Volumen total entregado'
    case 'MINUTO':
      return 'Tiempo de servicio'
    case 'HORA':
      return 'Tiempo de servicio'
    case 'PARADA':
      return 'Numero de paradas'
    case 'ZONA':
      return 'Zona aplicada'
    case 'VIAJE':
      return 'Viajes'
    default:
      return 'Base de calculo'
  }
}

function unidadCantidad(unidad) {
  switch (unidad) {
    case 'KM':
      return 'km'
    case 'KG':
      return 'kg'
    case 'M3':
      return 'm3'
    case 'MINUTO':
      return 'min'
    case 'HORA':
      return 'horas'
    case 'PARADA':
      return 'paradas'
    default:
      return ''
  }
}

export default function DetalleCalculoTabla({ detalleCalculo, costoTotal, tipoCamion }) {
  if (!detalleCalculo) return null
  const { metodo, explicacion, variables = {} } = detalleCalculo
  const unidad = variables.unidad
  const valorUnitario = variables.valor_unitario
  const baseCalculo = variables.base_calculo

  return (
    <div className="detalle-calculo">
      {explicacion && <p className="detalle-calculo-explicacion">{explicacion}</p>}
      <table className="detalle-calculo-tabla">
        <tbody>
          <tr>
            <td>Metodo de tarifa</td>
            <td>
              <span className="badge">{metodo}</span>
            </td>
          </tr>
          {tipoCamion && (
            <tr>
              <td>Tipo de camion usado</td>
              <td>
                {tipoCamion.nombre} ({tipoCamion.capacidad_peso_kg?.toLocaleString()} kg /{' '}
                {tipoCamion.capacidad_volumen_m3?.toLocaleString()} m3)
              </td>
            </tr>
          )}
          {valorUnitario !== undefined && (
            <tr>
              <td>Valor unitario</td>
              <td>
                {formatoMoneda(valorUnitario)}
                {unidad && ETIQUETAS_UNIDAD[unidad] ? ` ${ETIQUETAS_UNIDAD[unidad]}` : ''}
                {metodo === 'POR_ZONA' && variables.zona_aplicada ? ` (zona ${variables.zona_aplicada})` : ''}
              </td>
            </tr>
          )}
          {baseCalculo !== undefined && metodo !== 'POR_ZONA' && (
            <tr>
              <td>{etiquetaBase(unidad)}</td>
              <td>
                {formatoCantidad(baseCalculo)} {unidadCantidad(unidad)}
              </td>
            </tr>
          )}
          <tr>
            <td>
              <strong>Costo total</strong>
            </td>
            <td>
              <strong>{formatoMoneda(costoTotal)}</strong>
            </td>
          </tr>
        </tbody>
      </table>
      {metodo === 'POR_ZONA' && Array.isArray(variables.detalle_por_parada) && (
        <table className="detalle-calculo-tabla" style={{ marginTop: 8 }}>
          <thead>
            <tr>
              <th>Cliente</th>
              <th>Zona (poligono)</th>
              <th>Zona aplicada</th>
              <th>Respaldo manual</th>
              <th>Valor zona</th>
            </tr>
          </thead>
          <tbody>
            {variables.detalle_por_parada.map((d, idx) => (
              <tr key={idx}>
                <td>{d.cliente}</td>
                <td>{d.zona_por_poligono ?? '-'}</td>
                <td>{d.zona_aplicada ?? '-'}</td>
                <td>{d.uso_respaldo_manual ? 'Si' : 'No'}</td>
                <td>{formatoMoneda(d.valor_zona)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
