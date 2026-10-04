# Bitácora del taller de Cassandra

- **Nombre:** José Ignacio Paccagnella
- **Carné:** 20240103
- **Grupo:** G2
- **Tu nodo en el clúster del grupo:** cassandra1 (semilla), 100.126.2.38

---

## 1. Evidencias

### E1. Tres nodos en tu clúster y tu datacenter

![E1](capturas/E1-cluster.png)

### E2. Las copias de la partición de Quetzaltenango

![E2](capturas/E2-copias.png)

### E3. Upsert, TTL e IF NOT EXISTS

![E3](capturas/E3-cql.png)

### E4. Un nodo caído: QUORUM frente a ALL

![E4](capturas/E4-un-nodo-caido.png)

### E5. Dos nodos caídos: ONE frente a QUORUM

![E5](capturas/E5-dos-nodos-caidos.png)

### E6a. El hint guardado para el nodo caído

![E6a](capturas/E6a-hint.png)

### E6b. La entrega del hint

![E6b](capturas/E6b-handoff.png)

### Tabla del Paso 8

| Nodos caídos | `ONE` | `QUORUM` | `ALL` |
|---|---|---|---|
| 0 | | | |
| 1 | | | |
| 2 | | | |

---

## 2. Preguntas

**1. ¿Qué línea de la traza muestra que la consulta por ciudad leyó una sola partición, y cuál que la de producto recorrió toda la tabla? ¿Por qué Cassandra rechaza la segunda sin ALLOW FILTERING?**

**2. ¿Qué lecturas se comportaron como CP y cuáles como AP? ¿Qué nivel usarías para el saldo de una cuenta y cuál para un contador de reproducciones, y por qué?**

**3. ¿Cómo se enteró el nodo apagado de tu venta? ¿Qué pasaría si el nodo estuviera apagado más tiempo que max_hint_window?**

---

## 3. Mini-reto

### Tablas

| Tabla | Consulta que responde | Partition key | Clustering key |
|---|---|---|---|
| `pasajeros` | C1 | `pasajero_id` | (ninguna) |
| `viajes_por_pasajero` | C2 | `pasajero_id` | `inicio DESC`, `viaje_id` |
| `viajes_por_conductor_dia` | C3 | `(conductor_id, dia)` | `inicio ASC`, `viaje_id` |
| `viajes_por_ciudad_dia` | C4 | `(ciudad, dia)` | `inicio ASC`, `viaje_id` |

### Justificación

**Por qué esas llaves:**

- **C1:** el perfil se pide siempre por `pasajero_id`, así que esa es la partition key y cada pasajero es una partición de una fila. No hace falta clustering key.
- **C2:** la consulta filtra por pasajero, así que `pasajero_id` es la partition key y todos sus viajes viven juntos. `inicio DESC` como clustering key deja los viajes ya ordenados del más reciente al más viejo, y `LIMIT 10` toma los primeros sin ordenar nada al leer. `viaje_id` va al final para que dos viajes con el mismo `inicio` no se pisen (upsert).
- **C3:** se pide un conductor **en un día**, así que la partición es `(conductor_id, dia)`: una lectura cae en una sola partición y las particiones no crecen sin límite con los meses. `inicio ASC` devuelve los viajes en orden cronológico, como el `ORDER BY v.inicio` del SQL.
- **C4:** se cuentan viajes de **una ciudad en un día**, así que la partición es `(ciudad, dia)`. Si fuera solo `ciudad`, San José acumularía todos sus viajes en una partición gigante. `inicio` como clustering key permite el rango `inicio >= 17:00 AND inicio < 20:00` dentro de la partición, sin `ALLOW FILTERING`.

**Qué datos quedaron duplicados entre tablas:**

- Cada viaje está guardado **tres veces**: en `viajes_por_pasajero`, en `viajes_por_conductor_dia` y en `viajes_por_ciudad_dia`. `inicio`, `viaje_id` y `distancia_km` se repiten.
- El **nombre del conductor** se copió en cada viaje de `viajes_por_pasajero` (en SQL salía del JOIN con `conductores`).
- El **nombre del pasajero** se copió en cada viaje de `viajes_por_conductor_dia`, y también está en `pasajeros` (JOIN con `pasajeros`).
- El **monto y el método de pago** se copiaron en `viajes_por_pasajero` (JOIN con `pagos`).

**Qué hace la aplicación si cambia un dato duplicado:**

Cassandra no actualiza las copias sola: la aplicación tiene que escribir en **todas** las tablas donde está el dato. Por ejemplo, si un pasajero cambia su nombre, hay que actualizar `pasajeros` y además cada fila de ese pasajero en `viajes_por_conductor_dia`. Para encontrar esas filas, la aplicación primero lee los viajes del pasajero en `viajes_por_pasajero`, que trae `conductor_id`, `inicio` y `viaje_id` (de `inicio` sale el `dia`), y con eso arma la llave completa de cada fila a actualizar. Por eso `viajes_por_pasajero` guarda también el `conductor_id`, aunque C2 no lo muestre. Lo mismo si un conductor cambia de nombre o si se corrige un pago. Conviene agrupar esas escrituras en un `BATCH` lógico (`BEGIN BATCH ... APPLY BATCH`) para que, si una falla, se reintenten todas y las tablas no queden distintas. Para el historial de viajes, otra opción es no actualizar nada y aceptar que un viaje muestre el nombre que la persona tenía cuando lo hizo.

---

## 4. Problemas encontrados (opcional)

