"""Carga del mini-reto G2 (Uber) - José Ignacio Paccagnella, 20240103.

Cassandra no tiene JOIN: los JOIN de consultas.sql se hacen aquí, una sola vez,
al cargar. Por cada tabla de modelo.cql se arma un CSV con las columnas ya
unidas, se copia al contenedor y se carga con COPY FROM.

Uso, desde la raíz del repo, con el nodo arriba:
    python entregas/G2/20240103-jose-ignacio-paccagnella/mini-reto/carga.py
"""
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

NODO = "cassandra1"
KS = "uber_20240103"
AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[3]
DATOS = REPO / "data" / "mini-reto" / "G2-uber"
DESTINO = "/tmp/carga_uber_20240103"


def leer(nombre):
    with open(DATOS / nombre, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ts(valor):
    # Las horas de los CSV están en UTC.
    return valor + "+0000"


def escribir(carpeta, nombre, columnas, filas):
    with open(carpeta / nombre, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        w.writerows(filas)
    print(f"{nombre}: {len(filas)} filas")


def docker(*args, entrada=None):
    subprocess.run(["docker", *args], check=True, input=entrada,
                   text=True, encoding="utf-8")


def main():
    pasajeros = leer("pasajeros.csv")
    conductores = {c["conductor_id"]: c for c in leer("conductores.csv")}
    nombre_pasajero = {p["pasajero_id"]: p["nombre"] for p in pasajeros}
    pago_de_viaje = {p["viaje_id"]: p for p in leer("pagos.csv")}
    viajes = leer("viajes.csv")

    tablas = {
        "pasajeros": (
            ["pasajero_id", "nombre", "ciudad", "calificacion"],
            [[p["pasajero_id"], p["nombre"], p["ciudad"], p["calificacion"]]
             for p in pasajeros],
        ),
        # viajes JOIN conductores JOIN pagos
        "viajes_por_pasajero": (
            ["pasajero_id", "inicio", "viaje_id", "conductor_id", "conductor",
             "distancia_km", "monto", "metodo"],
            [[v["pasajero_id"], ts(v["inicio"]), v["viaje_id"], v["conductor_id"],
              conductores[v["conductor_id"]]["nombre"], v["distancia_km"],
              pago_de_viaje[v["viaje_id"]]["monto"],
              pago_de_viaje[v["viaje_id"]]["metodo"]]
             for v in viajes],
        ),
        # viajes JOIN pasajeros
        "viajes_por_conductor_dia": (
            ["conductor_id", "dia", "inicio", "viaje_id", "pasajero",
             "distancia_km", "tarifa"],
            [[v["conductor_id"], v["inicio"][:10], ts(v["inicio"]), v["viaje_id"],
              nombre_pasajero[v["pasajero_id"]], v["distancia_km"], v["tarifa"]]
             for v in viajes],
        ),
        "viajes_por_ciudad_dia": (
            ["ciudad", "dia", "inicio", "viaje_id"],
            [[v["ciudad"], v["inicio"][:10], ts(v["inicio"]), v["viaje_id"]]
             for v in viajes],
        ),
    }

    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        for tabla, (columnas, filas) in tablas.items():
            escribir(carpeta, f"{tabla}.csv", columnas, filas)

        # El modelo, y los CSV dentro del contenedor.
        docker("exec", "-i", NODO, "cqlsh",
               entrada=(AQUI / "modelo.cql").read_text(encoding="utf-8"))
        docker("exec", NODO, "rm", "-rf", DESTINO)
        docker("cp", str(carpeta), f"{NODO}:{DESTINO}")

        for tabla, (columnas, _) in tablas.items():
            docker("exec", NODO, "cqlsh", "-e",
                   f"COPY {KS}.{tabla} ({', '.join(columnas)}) "
                   f"FROM '{DESTINO}/{tabla}.csv' WITH HEADER = true;")

        docker("exec", NODO, "rm", "-rf", DESTINO)


if __name__ == "__main__":
    sys.exit(main())
