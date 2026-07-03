import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'

/**
 * Editor de poligono de zona, implementado con Leaflet "vanilla" (sin la
 * libreria leaflet-draw). Se descarto leaflet-draw porque tiene bugs viejos y
 * no resueltos al combinarse con Leaflet 1.9.x/React 18 (deja de aceptar
 * vertices despues del 3ro, la edicion no funciona) -- ver issues abiertos en
 * su repo. Esta implementacion es mas simple y queda bajo nuestro control:
 *
 *  - Click en el mapa: agrega un vertice nuevo al final del poligono.
 *  - Arrastrar un vertice: lo reposiciona.
 *  - Click derecho sobre un vertice: lo elimina.
 *  - Botones "Deshacer ultimo punto" / "Borrar poligono" debajo del mapa.
 *
 * No hace falta "cerrar" el poligono ni doble-click: apenas hay 3 o mas
 * vertices ya se dibuja cerrado automaticamente. El resultado no tiene que
 * coincidir con ninguna division administrativa oficial.
 */

const verticeIcon = L.divIcon({
  className: 'zona-vertice-icon',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
})

function PoligonoEditorControl({ vertices, setVertices, color }) {
  const map = useMap()
  const fitInicialHechoRef = useRef(false)

  // Click en el mapa vacio agrega un vertice nuevo. Los clicks sobre un marker
  // no llegan aca (Leaflet no propaga el click del marker al mapa por defecto).
  useEffect(() => {
    const alClickMapa = (e) => {
      setVertices((v) => [...v, [Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6))]])
    }
    map.on('click', alClickMapa)
    return () => map.off('click', alClickMapa)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])

  // Redibuja el poligono (o la linea, si aun hay menos de 3 puntos) y los
  // markers arrastrables de cada vertice cada vez que cambia la lista.
  useEffect(() => {
    let capaPoligono = null
    if (vertices.length >= 3) {
      capaPoligono = L.polygon(vertices, { color, fillOpacity: 0.15 }).addTo(map)
    } else if (vertices.length === 2) {
      capaPoligono = L.polyline(vertices, { color }).addTo(map)
    }

    const markers = vertices.map((latlng, idx) =>
      L.marker(latlng, { icon: verticeIcon, draggable: true })
        .addTo(map)
        .on('dragend', (e) => {
          const { lat, lng } = e.target.getLatLng()
          setVertices((v) =>
            v.map((p, i) => (i === idx ? [Number(lat.toFixed(6)), Number(lng.toFixed(6))] : p))
          )
        })
        .on('contextmenu', (e) => {
          L.DomEvent.preventDefault(e.originalEvent)
          setVertices((v) => v.filter((_, i) => i !== idx))
        })
    )

    if (!fitInicialHechoRef.current && vertices.length >= 3) {
      map.fitBounds(capaPoligono.getBounds(), { maxZoom: 15, padding: [20, 20] })
      fitInicialHechoRef.current = true
    }

    return () => {
      markers.forEach((m) => map.removeLayer(m))
      if (capaPoligono) map.removeLayer(capaPoligono)
    }
  }, [vertices, map, color])

  return null
}

/**
 * Mapa listo para usar dentro de un formulario: incluye TileLayer + editor de
 * poligono + controles de deshacer/borrar. Maneja su propio estado de
 * vertices (inicializado desde poligonoInicial) y avisa cada cambio via
 * onChange(poligono | null) -- poligono es null mientras haya menos de 3
 * vertices.
 *
 * Importante: si el componente padre reutiliza esta instancia para editar
 * zonas distintas (o pasar de crear a editar), debe montarla con una `key`
 * distinta por zona (ej. key={editingId ?? 'new'}) para que el estado interno
 * se reinicie -- de lo contrario conserva los vertices de la edicion anterior.
 */
export function ZonaPoligonoEditor({ poligonoInicial, onChange, center = [4.65, -74.1] }) {
  const [vertices, setVertices] = useState(() =>
    poligonoInicial ? poligonoInicial.map((p) => [...p]) : []
  )

  useEffect(() => {
    onChange(vertices.length >= 3 ? vertices : null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vertices])

  return (
    <div>
      <div className="map-container" style={{ height: 420 }}>
        <MapContainer center={center} zoom={11} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
          <PoligonoEditorControl vertices={vertices} setVertices={setVertices} color="#2563eb" />
        </MapContainer>
      </div>
      <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          type="button"
          className="btn secondary"
          disabled={vertices.length === 0}
          onClick={() => setVertices((v) => v.slice(0, -1))}
        >
          Deshacer ultimo punto
        </button>
        <button
          type="button"
          className="btn secondary"
          disabled={vertices.length === 0}
          onClick={() => setVertices([])}
        >
          Borrar poligono
        </button>
        <span className="page-subtitle" style={{ margin: 0 }}>
          {vertices.length === 0
            ? 'Haz click en el mapa para colocar el primer vertice.'
            : `${vertices.length} vertice(s)${
                vertices.length < 3 ? ' -- faltan al menos ' + (3 - vertices.length) + ' para formar un poligono' : ''
              }. Arrastra un vertice para moverlo, click derecho para borrarlo.`}
        </span>
      </div>
    </div>
  )
}
