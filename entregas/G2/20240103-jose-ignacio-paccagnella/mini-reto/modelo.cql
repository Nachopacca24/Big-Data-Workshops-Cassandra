-- Mini-reto G2 (Uber) - José Ignacio Paccagnella, 20240103
-- Una tabla por consulta. Los JOIN de SQL se resuelven al cargar: cada tabla
-- ya trae copiados los datos que su consulta necesita de las otras tablas.

CREATE KEYSPACE IF NOT EXISTS uber_20240103
  WITH replication = {'class': 'NetworkTopologyStrategy', 'dc-g2': 3};

-- C1. Perfil de un pasajero: se busca por pasajero_id.
CREATE TABLE IF NOT EXISTS uber_20240103.pasajeros (
  pasajero_id  text,
  nombre       text,
  ciudad       text,
  calificacion decimal,
  PRIMARY KEY ((pasajero_id))
);

-- C2. Los 10 viajes más recientes de un pasajero, con su conductor y su pago.
-- Partición: el pasajero. Orden: inicio descendente, para que LIMIT 10 sean los últimos.
CREATE TABLE IF NOT EXISTS uber_20240103.viajes_por_pasajero (
  pasajero_id  text,
  inicio       timestamp,
  viaje_id     int,
  conductor_id text,
  conductor    text,
  distancia_km decimal,
  monto        decimal,
  metodo       text,
  PRIMARY KEY ((pasajero_id), inicio, viaje_id)
) WITH CLUSTERING ORDER BY (inicio DESC, viaje_id ASC);

-- C3. Los viajes de un conductor en un día, con el nombre del pasajero.
-- Partición: conductor + día, para que cada partición sea un día de trabajo.
CREATE TABLE IF NOT EXISTS uber_20240103.viajes_por_conductor_dia (
  conductor_id text,
  dia          date,
  inicio       timestamp,
  viaje_id     int,
  pasajero     text,
  distancia_km decimal,
  tarifa       decimal,
  PRIMARY KEY ((conductor_id, dia), inicio, viaje_id)
) WITH CLUSTERING ORDER BY (inicio ASC, viaje_id ASC);

-- C4. Cuántos viajes empezaron en una ciudad en una franja horaria de un día.
-- Partición: ciudad + día. Orden: inicio, para filtrar el rango de horas.
CREATE TABLE IF NOT EXISTS uber_20240103.viajes_por_ciudad_dia (
  ciudad   text,
  dia      date,
  inicio   timestamp,
  viaje_id int,
  PRIMARY KEY ((ciudad, dia), inicio, viaje_id)
) WITH CLUSTERING ORDER BY (inicio ASC, viaje_id ASC);
