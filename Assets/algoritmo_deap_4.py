import tkinter as tk
from tkinter import ttk, messagebox
import random
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys, os, subprocess, psutil
import json
from deap import base, creator, tools

# Cuadrícula de la ciudad
ancho_total = 30
alto_total = 20
tam_celda = 2

xs = np.arange(0, ancho_total + tam_celda, tam_celda)
ys = np.arange(0, alto_total + tam_celda, tam_celda)

G = nx.Graph()
for y in ys:
    for x in xs:
        G.add_node((x, y))
        if x + tam_celda <= ancho_total:
            G.add_edge((x, y), (x + tam_celda, y), weight=tam_celda)
        if y + tam_celda <= alto_total:
            G.add_edge((x, y), (x, y + tam_celda), weight=tam_celda)

# Puntos de entrega y recarga

punto_inicio = (0, 0)
puntos_entrega = random.sample(list(G.nodes()), 6)

num_recargas = int(len(puntos_entrega) * 1.5)
puntos_recarga = random.sample(
    [n for n in G.nodes() if n not in puntos_entrega and n != punto_inicio],
    num_recargas
)

puntos = [punto_inicio] + puntos_entrega

# Matriz de distancias entre puntos

n = len(puntos)
distancias = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        if i != j:
            distancias[i, j] = nx.shortest_path_length(G, puntos[i], puntos[j], weight="weight")

# Configuración de DEAP

if "FitnessMin" in creator.__dict__:
    del creator.FitnessMin
if "Individual" in creator.__dict__:
    del creator.Individual

creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

# Individuos con índices 0..(n-2)
toolbox.register("indices", random.sample, range(n - 1), n - 1)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.indices)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Apertura de la simulación externa

def ruta_relativa(ruta):
    """Devuelve una ruta válida tanto en desarrollo como en el ejecutable."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, ruta)

# 5. Función evaluativa con distancia mínima y combustible consumido

def evaluar(individuo):
    ruta = [0] + [i + 1 for i in individuo] + [0]
    total_distancia = 0
    combustible = 100
    ruta_real = []

    for i in range(len(ruta) - 1):
        origen = puntos[ruta[i]]
        destino = puntos[ruta[i + 1]]
        camino = nx.shortest_path(G, origen, destino, weight="weight")

        if i == 0:
            ruta_real.extend(camino)
        else:
            ruta_real.extend(camino[1:])

        for j in range(len(camino) - 1):
            p1 = camino[j]
            p2 = camino[j + 1]

            distancia = G[p1][p2]["weight"]
            total_distancia += distancia

            combustible -= distancia

            if p2 in puntos_recarga:
                combustible = min(100, combustible + 10)

            if combustible <= 0:
                total_distancia += 100
                individuo.ruta_real = ruta_real
                return (total_distancia,)
    individuo.ruta_real = ruta_real
    return (total_distancia,)


toolbox.register("evaluate", evaluar)
toolbox.register("mate", tools.cxOrdered)
toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.4)
toolbox.register("select", tools.selTournament, tournsize=3)

# Ejecutar el algoritmo genético y guardarlo en JSON

def ejecutar_ag_deap(n_gen, tam_pobl, prob_cx, prob_mut):
    pop = toolbox.population(n=tam_pobl)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("min", np.min)
    stats.register("avg", np.mean)

    log_rutas = []

    for gen in range(n_gen):
        for ind in pop:
            ind.fitness.values = toolbox.evaluate(ind)

        mejor = tools.selBest(pop, 1)[0]

        rutas_gen = {
            "generacion": int(gen),
            "rutas": [],
            "mejor_individuo": None
        }

        for ind in pop:
            rutas_gen["rutas"].append({
                "individuo": [{"x": int(p[0]), "y": int(p[1])} for p in ind.ruta_real],
                "fitness": float(ind.fitness.values[0])
            })

        rutas_gen["mejor_individuo"] = {
            "individuo": [{"x": int(p[0]), "y": int(p[1])} for p in mejor.ruta_real],
            "fitness": float(mejor.fitness.values[0])
        }

        log_rutas.append(rutas_gen)

        elite = tools.selBest(pop, 1)
        elite = [toolbox.clone(ind) for ind in elite]

        offspring = toolbox.select(pop, len(pop) - len(elite))
        offspring = list(map(toolbox.clone, offspring))

        for c1, c2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < prob_cx:
                toolbox.mate(c1, c2)
                del c1.fitness.values
                del c2.fitness.values

        for mut in offspring:
            if random.random() < prob_mut:
                toolbox.mutate(mut)
                del mut.fitness.values

        pop[:] = elite + offspring

    def convertir_nativo(obj):
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (list, tuple)):
            return [convertir_nativo(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: convertir_nativo(v) for k, v in obj.items()}
        else:
            return obj

    puntos_data = {
        "puntos_entrega": [{"x": int(p[0]), "y": int(p[1])} for p in puntos_entrega],
        "puntos_recarga": [{"x": int(p[0]), "y": int(p[1])} for p in puntos_recarga]
    }

    with open("Puntos/rutas_generaciones.json", "w", encoding="utf-8") as f:
        json.dump(convertir_nativo(log_rutas), f, indent=2, ensure_ascii=False)

    with open("Puntos/puntos_fijos.json", "w", encoding="utf-8") as f:
        json.dump(puntos_data, f, indent=2, ensure_ascii=False)

    hof.update(pop)
    return hof[0], log_rutas

# Interfaz Gráfica

class InterfazAG(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Configuración del Algoritmo Genético")
        self.geometry("400x300")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.al_cerrar)

        ttk.Label(self, text="Tamaño de población:").pack(pady=5)
        self.pobl_entry = ttk.Entry(self)
        self.pobl_entry.pack()
        self.pobl_entry.insert(0, "10")

        ttk.Label(self, text="Número de generaciones:").pack(pady=5)
        self.gen_entry = ttk.Entry(self)
        self.gen_entry.pack()
        self.gen_entry.insert(0, "100")

        ttk.Label(self, text="Probabilidad de cruce (0-1):").pack(pady=5)
        self.cx_entry = ttk.Entry(self)
        self.cx_entry.pack()
        self.cx_entry.insert(0, "0.8")

        ttk.Label(self, text="Probabilidad de mutación (0-1):").pack(pady=5)
        self.mut_entry = ttk.Entry(self)
        self.mut_entry.pack()
        self.mut_entry.insert(0, "0.4")

        ttk.Button(self, text="Ejecutar algoritmo", command=self.ejecutar_algoritmo).pack(pady=15)

    def validar_entradas(self):
        try:
            n_gen = int(self.gen_entry.get())
            tam_pobl = int(self.pobl_entry.get())
            prob_cx = float(self.cx_entry.get())
            prob_mut = float(self.mut_entry.get())
            if n_gen <= 0 or tam_pobl <= 0:
                raise ValueError("La población y generaciones deben ser > 0.")
            if not (0 <= prob_cx <= 1 and 0 <= prob_mut <= 1):
                raise ValueError("Las probabilidades deben estar entre 0 y 1.")
            return n_gen, tam_pobl, prob_cx, prob_mut
        except ValueError as e:
            messagebox.showerror("Error de entrada", "No puede ingresar valores no numéricos o comas.\n" + str(e))
            return None

    def ejecutar_algoritmo(self):
        params = self.validar_entradas()
        if not params: return

        n_gen, tam_pobl, prob_cx, prob_mut = params
        mejor, log_rutas = ejecutar_ag_deap(n_gen, tam_pobl, prob_cx, prob_mut)

        ventana_resultados = VentanaResultados(mejor, log_rutas)
        ventana_resultados.mainloop()

    def al_cerrar(self):
        try:
            proceso_actual = psutil.Process(os.getpid())
            for subproc in proceso_actual.children(recursive=True):
                subproc.kill()

            proceso_actual.kill()
        except Exception as e:
            print("⚠️ Error al cerrar procesos:", e)
        finally:
            os._exit(0)

# Ventana de Gráficos

class VentanaResultados(tk.Toplevel):
    def __init__(self, mejor, log_rutas):
        super().__init__()
        self.title("Resultados del Algoritmo Genético")
        self.geometry("950x600")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Figuras
        fig1, ax1 = plt.subplots()
        fig2, ax2 = plt.subplots()
        fig3, ax3 = plt.subplots()

        # Ruta óptima
        pos = {node: node for node in G.nodes()}
        nx.draw(G, pos, node_size=10, edge_color="lightgray", ax=ax1)
        nx.draw_networkx_nodes(G, pos, nodelist=[punto_inicio], node_color="blue", node_size=120, ax=ax1)
        nx.draw_networkx_nodes(G, pos, nodelist=puntos_entrega, node_color="red", node_size=80, ax=ax1)
        nx.draw_networkx_nodes(G, pos, nodelist=puntos_recarga, node_color="orange", node_size=60, ax=ax1)
        ruta_real = mejor.ruta_real
        x, y = zip(*ruta_real)
        ax1.plot(x, y, "-o", color="green", linewidth=2)
        ax1.set_title("Ruta óptima del camión")
        ax1.axis("equal")

        # Fitness
        gens = [r["generacion"] for r in log_rutas]
        minimos = [r["mejor_individuo"]["fitness"] for r in log_rutas]
        promedios = [np.mean([p["fitness"] for p in r["rutas"]]) for r in log_rutas]
        ax2.plot(gens, minimos, label="Distancia mínima", color="green", linewidth=2)
        ax2.plot(gens, promedios, label="Distancia promedio", color="blue", linestyle="--")
        ax2.legend()
        ax2.set_xlabel("Generación")
        ax2.set_ylabel("Distancia")
        ax2.set_title("Evolución del Fitness")
        ax2.grid(True)

        # Combustible
        combustible = 100
        niveles = [combustible]
        distancias = [0]
        d_total = 0
        recargas = 0
        for i in range(len(ruta_real) - 1):
            p1, p2 = ruta_real[i], ruta_real[i + 1]
            d = G[p1][p2]["weight"]
            d_total += d
            combustible -= d
            if p2 in puntos_recarga:
                combustible = min(100, combustible + 10)
                recargas += 1
            combustible = max(0, combustible)
            niveles.append(combustible)
            distancias.append(d_total)
        ax3.plot(distancias, niveles, "-o", color="orange")
        ax3.set_xlabel("Distancia recorrida")
        ax3.set_ylabel("Nivel de combustible")
        ax3.set_title("Consumo de combustible a lo largo del recorrido")
        ax3.grid(True)

        # Canvases
        canvas1 = FigureCanvasTkAgg(fig1, master=notebook)
        canvas2 = FigureCanvasTkAgg(fig2, master=notebook)
        canvas3 = FigureCanvasTkAgg(fig3, master=notebook)
        canvas1.draw(); canvas2.draw(); canvas3.draw()

        notebook.add(canvas1.get_tk_widget(), text="Ruta óptima")
        notebook.add(canvas2.get_tk_widget(), text="Evolución del Fitness")
        notebook.add(canvas3.get_tk_widget(), text="Consumo de Combustible")

        # Consola de texto (solo lectura)
        frame_text = ttk.Frame(notebook)
        text_widget = tk.Text(frame_text, wrap="word", state="normal")
        text_widget.insert(tk.END, f"Distancia total: {d_total:.2f} unidades\n")
        text_widget.insert(tk.END, f"Combustible restante: {combustible:.2f}\n")
        text_widget.insert(tk.END, f"Recargas utilizadas: {recargas}\n")
        text_widget.insert(tk.END, f"Mejor fitness: {min(minimos):.2f}\n")
        text_widget.insert(tk.END, f"Generaciones: {len(gens)}\n")
        text_widget.insert(tk.END, f"Tamaño de población: {len(log_rutas[0]['rutas'])}\n")
        text_widget.config(state="disabled")  # inmodificable
        text_widget.pack(fill="both", expand=True)
        notebook.add(frame_text, text="Resultados generales")

        self.protocol("WM_DELETE_WINDOW", self.destroy)

        frame_boton = ttk.Frame(self)
        frame_boton.pack(pady=10)
        ttk.Button(
            frame_boton,
            text="Abrir simulación 3D",
            command=self.abrir_simulacion_externa
        ).pack()

    def abrir_simulacion_externa(self):
        exe_path = ruta_relativa("Algoritmo_genetico_simulador.exe")
        if os.path.exists(exe_path):
            try:
                subprocess.Popen([exe_path], shell=True)
            except Exception as e:
                messagebox.showerror("Error", "No se pudo abrir el ejecutable:\n" + str(e))
        else:
            messagebox.showwarning("Archivo no encontrado", f"No se encontró: {exe_path}")
        


if __name__ == "__main__":
    app = InterfazAG()
    app.mainloop()