"""Demostración: calcula rutas con las estrategias, simula un incidente, recalcula y guarda las figuras."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from navegacion.grafo import generar_ciudad
from navegacion.estrategias import BFS, Dijkstra, AEstrella
from navegacion.trafico import SensorTrafico
from navegacion.cache import CacheRutas
from navegacion.navegador import Navegador, SesionNavegacion
from navegacion.ruta import IteradorInstrucciones

R = pathlib.Path(__file__).resolve().parent / "resultados"
g = generar_ciudad(40, 40, seed=11)
o, d = 1 * 40 + 2, 37 * 40 + 36
sensor, cache = SensorTrafico(g), CacheRutas()
sensor.suscribir(cache)
nav = Navegador(g, AEstrella(), cache)

print("== 1. Comparación de estrategias ==")
res = {}
for e in (BFS(), Dijkstra(), AEstrella()):
    r = e.buscar(g, o, d); res[e.nombre] = r
    print(f"{e.nombre:24s} tiempo de viaje {r.costo_s/60:6.2f} min | nodos expandidos {r.nodos_expandidos:5d} | cálculo {r.tiempo_calculo_ms:6.2f} ms")

print("\n== 2. Sesión con incidente ==")
ses = SesionNavegacion(nav, o, d); sensor.suscribir(ses)
antes = list(ses.camino); ses.avanzar(len(antes) // 3)
a, b = ses.camino[ses.pos], ses.camino[ses.pos + 1]
print(f"Incidente en la vía {a}-{b} (congestión x10). Ruta restante antes: {ses.restante and len(ses.restante)} nodos")
sensor.reportar(a, b, 10.0)
print(f"Recálculos automáticos: {ses.reroutes} ({ses.ms_reroute[0]:.2f} ms). Nueva ruta restante: {len(ses.restante)} nodos")
print("\n== 3. Primeras instrucciones (Iterator) ==")
for i, ins in zip(range(5), IteradorInstrucciones(g, ses.restante)):
    print(f"{i+1}. {ins}")

fig, ax = plt.subplots(1, 2, figsize=(12, 5.6))
def base(axx, titulo):
    for u, lst in g.adyacencia.items():
        for e in lst:
            if e.origen < e.destino:
                (x1, y1), (x2, y2) = g.coords[e.origen], g.coords[e.destino]
                axx.plot([x1, x2], [y1, y2], color="#cfd4da" if e.velocidad_kmh < 50 else "#9aa5b1",
                         lw=0.6 if e.velocidad_kmh < 50 else 1.2, zorder=1)
    axx.set_title(titulo, fontsize=11); axx.set_aspect("equal"); axx.axis("off")
def trazar(axx, cam, color, lab, lw=2.4):
    axx.plot([g.coords[n][0] for n in cam], [g.coords[n][1] for n in cam], color=color, lw=lw, label=lab, zorder=3)
base(ax[0], "Estrategias sin tráfico: BFS vs. A*")
trazar(ax[0], res["BFS (menos giros)"].camino, "#d1495b", f"BFS: {res['BFS (menos giros)'].costo_s/60:.1f} min")
trazar(ax[0], res["A*"].camino, "#00798c", f"A*: {res['A*'].costo_s/60:.1f} min")
base(ax[1], "Incidente (×10) y recálculo automático")
trazar(ax[1], antes, "#edae49", "Ruta original", 3.2)
trazar(ax[1], ses.camino, "#00798c", "Ruta recalculada")
ax[1].plot(*g.coords[a], "X", color="#d1495b", ms=13, zorder=5, label="Incidente")
ax[1].plot(*g.coords[ses.camino[0]], "o", color="#30323d", ms=8, zorder=5)
for axx in ax:
    axx.plot(*g.coords[o], "s", color="#30323d", ms=8, zorder=5)
    axx.plot(*g.coords[d], "^", color="#30323d", ms=9, zorder=5)
    axx.legend(loc="lower right", fontsize=8, frameon=True)
plt.tight_layout(); plt.savefig(R / "fig_mapa_rutas.png", dpi=170); plt.close()

# gráficas de benchmark
data = json.loads((R / "resultados.json").read_text())
esc = data["escala"]; nombres = sorted({r["estrategia"] for r in esc}, key=lambda n: [r["estrategia"] for r in esc].index(n))
col = {"BFS (menos giros)": "#d1495b", "Dijkstra": "#30323d", "A*": "#00798c", "Dijkstra bidireccional": "#edae49"}
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for n in nombres:
    f = [r for r in esc if r["estrategia"] == n]
    ax[0].plot([r["nodos"] for r in f], [r["ms_media"] for r in f], "o-", color=col[n], label=n)
    ax[1].plot([r["nodos"] for r in f], [r["expandidos_media"] for r in f], "o-", color=col[n], label=n)
for axx, t in zip(ax, ("Tiempo de cálculo medio (ms)", "Nodos expandidos (media)")):
    axx.set_xscale("log"); axx.set_yscale("log"); axx.set_xlabel("Nodos del mapa"); axx.set_title(t, fontsize=11)
    axx.grid(alpha=.3, which="both")
ax[0].legend(fontsize=8)
plt.tight_layout(); plt.savefig(R / "fig_escalabilidad.png", dpi=170); plt.close()

c = data["cache"]
fig, ax = plt.subplots(figsize=(5.2, 3.8))
v = [c["sin_cache"]["solicitudes_por_s"], c["con_cache"]["solicitudes_por_s"]]
bars = ax.bar(["Sin caché", "Con caché\n(Observer)"], v, color=["#9aa5b1", "#00798c"])
for bb, x in zip(bars, v): ax.text(bb.get_x() + bb.get_width() / 2, x, f"{x:,.0f}", ha="center", va="bottom", fontsize=9)
ax.set_ylabel("Solicitudes por segundo"); ax.set_title(f"Caché de rutas: {c['mejora_x']}× más rendimiento", fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig(R / "fig_cache.png", dpi=170); plt.close()
print("\nFiguras guardadas en resultados/")
