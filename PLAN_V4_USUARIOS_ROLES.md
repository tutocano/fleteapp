# Plan v4 — Usuarios, roles y aislamiento de datos por empresa

Estado: **planificacion, nada implementado todavia**. Este documento es el spec de
referencia para cuando se decida empezar a construir v4, siguiendo el mismo metodo
usado en v2/v3 (tag de git de seguridad antes de empezar, todo probado localmente,
publicar solo al final).

## 1. Objetivo

Agregar autenticacion y 4 roles de usuario, y aislar los datos de cada empresa para
que fleteapp pueda operar como un sistema multi-cliente (una sola instancia, una sola
base de datos, todas las empresas conviven ahi).

## 2. Roles

| Rol | Que puede hacer | Empresa asignada |
|---|---|---|
| `SUPER_ADMIN` | Crear/editar empresas. Crear todos los usuarios de todas las empresas y asignarles rol + empresa. Ver y editar los datos de **cualquier** empresa (para corregir registros mal asignados). | Ninguna (no pertenece a una empresa especifica) |
| `EMPRESA_ADMIN` | CRUD de CEDIs, clientes, transportistas, zonas geograficas, tipos de camion, tarifas, cobertura de zonas por transportista, flota, productos — todo **dentro de su propia empresa** | Exactamente una |
| `INTERFAZ` | Importar rutas planificadas y ejecutadas (el uso diario) de su empresa | Exactamente una |
| `USUARIO_FINAL` | Solo lectura: Mapa de Rutas, Mapa General, Conciliacion, de su empresa | Exactamente una |

Reglas confirmadas contigo:
- Un usuario pertenece a **una sola empresa** (excepto `SUPER_ADMIN`, que no pertenece a
  ninguna en particular porque opera sobre todas).
- Solo `SUPER_ADMIN` puede crear usuarios y asignarles empresa + rol. Los demas roles no
  pueden crear ni editar otros usuarios.
- Solo `SUPER_ADMIN` puede ver/tocar datos de una empresa que no es la suya (o de
  cualquiera, ya que no tiene una asignada) — pensado explicitamente para corregir un
  registro que quedo mal asignado a la empresa equivocada.

Fuera de alcance para esta version (se puede agregar despues si hace falta): recuperar
contrasena por correo, 2FA, permisos mas finos dentro de un mismo rol (ej. un
`EMPRESA_ADMIN` de solo-lectura), auditoria de cambios.

## 3. Modelo de datos nuevo

```
Usuario
  id PK
  nombre
  email UNIQUE (es el login)
  password_hash
  rol            -- enum: SUPER_ADMIN | EMPRESA_ADMIN | INTERFAZ | USUARIO_FINAL
  empresa_id FK  -- NULL solo para SUPER_ADMIN; obligatorio para los demas 3 roles
  activo         -- boolean, para desactivar sin borrar
  creado_en
```

Un solo `rol` por usuario (no roles combinados). Si una persona real necesita dos roles
(ej. tambien importar rutas ademas de administrar), se le crean dos cuentas distintas
con el mismo correo+sufijo o correos distintos — mas simple que permisos compuestos, y
consistente con "un usuario pertenece a una sola empresa".

No se crea una tabla de "permisos" separada: con 4 roles fijos y pocos, un enum simple
alcanza; una tabla de permisos configurable seria sobre-ingenieria para este tamano.

## 4. Que tablas existentes necesitan `empresa_id`

Ya lo tienen (sin cambios):
`CentroDistribucion`, `Cliente`, `Transportista`.

Hay que agregarlo (son las que mencionaste que crea un usuario de empresa, mas
`TipoCliente` y `MetodoTarifa` que decidiste que tambien sean por empresa):
`ZonaGeografica`, `TipoCamion`, `Producto`, `TipoCliente`, `MetodoTarifa`.

Se agrega tambien, aunque sea "derivable" de otra tabla, **por consistencia** (para que
el filtro "trae solo lo de mi empresa" sea el mismo patron en todos lados, sin casos
especiales por tabla):
`Flota` (hoy se llega a la empresa via `transportista_id`), `TarifaTransportista` (hoy
via `transportista_id`), `Ruta` (hoy via `centro_distribucion_id`).

Se dejan **sin** `empresa_id` propio (son tablas de detalle/relacion, siempre se
consultan a traves de su padre, y se valida en el codigo que ambos lados de la relacion
sean de la misma empresa al crearlas):
`TarifaZonaDetalle`, `TransportistaZonaCobertura`, `ParadaRuta`, `PedidoClienteRuta`.

Ya no quedan catalogos globales compartidos entre empresas -- todo lo que crea o usa un
usuario de empresa vive dentro de su propia empresa.

### Implicacion de que `MetodoTarifa` sea por empresa

Hoy los 6 metodos (`POR_VIAJE`, `POR_PARADA`, `POR_ZONA`, `POR_PESO_VOLUMEN`,
`POR_TIEMPO_SERVICIO`, `POR_KILOMETRO`) se siembran una sola vez al arrancar el backend
(`main.py`, catalogo global). Si pasan a ser por empresa, esa siembra tiene que pasar a
ocurrir **automaticamente cada vez que `SUPER_ADMIN` crea una empresa nueva** (clonar los
6 metodos para esa empresa recien creada) -- si no, un `EMPRESA_ADMIN` nuevo veria el
desplegable de metodos de tarifa vacio y no podria crear ninguna tarifa. La logica de
calculo en `flete_calculo.py` sigue funcionando igual (identifica el metodo por su
`codigo`, ej. `"POR_ZONA"`, no por el `id`), asi que no cambia el motor de calculo, solo
de donde sale la lista de metodos disponibles por empresa.

Mismo razonamiento aplicaria si en el futuro quisieras que una empresa tenga, por
ejemplo, solo 4 de los 6 metodos habilitados -- quedaria facil de agregar despues
(desactivar filas en vez de borrarlas), pero no es parte de este alcance.

## 5. Autenticacion

- JWT (token en el header `Authorization: Bearer <token>`), sin sesiones de servidor.
  **Confirmado:** expira a las 12 horas; al vencerse, se vuelve a hacer login con
  correo+contrasena. Sin refresh token ni "cerrar sesion en todos los dispositivos" en
  esta version (mantenerlo simple, es lo que decidiste).
- Contrasenas con hash (bcrypt via `passlib`), nunca en texto plano.
- `POST /api/auth/login` recibe email+password, devuelve el token.
- Dependencia de FastAPI `get_current_user` en cada endpoint protegido: decodifica el
  token y carga el `Usuario`.
- Dependencia `require_role(*roles)`: rechaza con 403 si el rol del usuario actual no
  esta en la lista permitida para ese endpoint.

## 6. Aislamiento por empresa — el punto mas delicado

Regla de oro: **el `empresa_id` nunca se confia si viene del cliente** (body/query) para
roles distintos de `SUPER_ADMIN`. Siempre se toma del usuario autenticado.

Se centraliza en una sola dependencia (`empresa_actual`) para no repetir el filtro a
mano en cada uno de los ~30 endpoints:

- Si el rol es `SUPER_ADMIN`: puede ver todo (`empresa_id` opcional por query string
  `?empresa_id=` para navegar los datos de una empresa puntual, ej. para corregir un
  registro mal asignado).
- Para los otros 3 roles: la dependencia devuelve siempre `current_user.empresa_id`,
  sin excepcion, y cada query de listado/creacion la usa para filtrar/asignar.

Riesgo real: si a alguien se le olvida aplicar el filtro en un endpoint nuevo, esa
empresa ve datos de otra. Mitigacion: centralizar el filtro en la dependencia (un solo
lugar que revisar/probar) y agregar un test automatico que recorra los endpoints de
listado con 2 empresas de prueba y confirme que cada una solo ve lo suyo. Si mas
adelante se quiere una capa extra de seguridad, Postgres tiene Row-Level Security para
reforzarlo a nivel de base de datos (no necesario para el tamano actual, pero queda
como mejora futura documentada).

## 7. Migracion de datos existentes

Mismo patron ya usado con las columnas de distancia de referencia (v3): agregar las
columnas nuevas con `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` manualmente en
produccion **antes** de desplegar el codigo nuevo (porque `create_all()` no modifica
tablas que ya existen).

**Confirmado:** en vez de dejar todos los datos actuales en una sola empresa, se crea
una segunda empresa de prueba ("Empresa Demo 2" o el nombre que prefieras) y se reparte
parte de los datos sembrados (algunos CEDIs/clientes/transportistas/rutas) hacia ella,
para poder probar de verdad que el aislamiento funciona: que un usuario de la empresa 1
no vea nada de la empresa 2, y viceversa, y que `SUPER_ADMIN` si vea ambas. El script de
backfill (parecido a `backfill_distancia_referencia.py`) hace esta division en vez de
asignar todo en bloque a una sola empresa.

## 8. Cambios de frontend

- Pantalla de login.
- Interceptor de axios: agrega el token a cada request, y si una respuesta da 401
  redirige a login.
- Rutas protegidas por rol (ocultar/redirigir paginas que el rol actual no puede ver) y
  el menu lateral solo muestra las opciones permitidas para el rol de la sesion.
- Pantalla nueva "Usuarios" (solo visible para `SUPER_ADMIN`): crear/editar usuarios,
  asignar empresa + rol. La pantalla de "Empresa" pasa a ser tambien solo para
  `SUPER_ADMIN` (hoy cualquiera puede crear una empresa).
- Para `SUPER_ADMIN`: un selector de "viendo datos de la empresa X" en la cabecera,
  ya que el no tiene una empresa fija.

## 9. Fases de entrega

Vamos a hacerlo junto en una sola version (v4), pero conviene construirlo y probarlo en
este orden interno para poder verificar cada parte por separado antes de avanzar:

1. Modelo `Usuario` + login + JWT + roles, **sin** aislar datos todavia (protege el
   sistema actual detras de un login, pero todas las empresas siguen viendo todo — util
   para probar que el login/roles funcionan antes de meterle la complejidad del
   aislamiento).
2. Agregar `empresa_id` donde falta (seccion 4) + migrar datos existentes + filtrar cada
   endpoint por la empresa del usuario actual.
3. Frontend: login, guard de rutas por rol, pantalla de Usuarios, selector de empresa
   para `SUPER_ADMIN`.
4. Pruebas de aislamiento: crear una segunda empresa de prueba con su propio usuario y
   confirmar que ninguna ve datos de la otra, y que `SUPER_ADMIN` si ve ambas.

Igual que en v2/v3: tag de git de seguridad (`v3.x`) antes de empezar, todo se construye
y prueba local (docker compose / smoke tests), y solo se publica cuando quede validado.

## 10. Decisiones confirmadas (ya no son preguntas abiertas)

- Sesion simple: expira a las 12 horas, sin refresh token.
- Los datos de prueba existentes se reparten en 2 empresas (se crea una segunda
  empresa de prueba) para validar que el aislamiento funciona de verdad.

No quedan preguntas pendientes de tu lado — el plan esta listo para pasar a
construccion cuando digas.
