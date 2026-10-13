import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import random
import os
import shutil
import datetime
import json
import queue
import threading

from memoria_ia import MemoriaIA

try:
    import pandas as pd
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    pd = None

try:
    from motor_ia import MotorIA, MODELOS, ESTADOS, describir_error, cargar_contexto_normativo
except ImportError:
    MotorIA = None  # Falta: pip install anthropic pypdf
    MODELOS, ESTADOS = {}, {}


class SimuladorSIGAGerencial:
    def __init__(self, root):
        self.root = root
        self.root.title("SIGA - Motor de Priorización (OGPL - UNMSM)")

        self.root.minsize(1024, 720)
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-zoomed', True)

        self.root.configure(bg="#f8f9fa")

        self.auditoria_db = {}
        self.df_exportar = None

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.carpeta_contexto = os.path.join(self.base_dir, "contexto_normativo")
        self.memoria = MemoriaIA(os.path.join(self.base_dir, "memoria_ia.db"))
        self.api_key = None
        self.api_key_preguntada = False
        self.motor_var = tk.StringVar(value="ia" if MotorIA else "ahp")
        self.modelo_var = tk.StringVar(value=next(iter(MODELOS), ""))

        self.main_container = tk.Frame(self.root, bg="#f8f9fa")
        self.main_container.pack(fill="both", expand=True)

        self.mostrar_pantalla_bienvenida()

    # ==========================================
    # PANTALLA 1: BIENVENIDA
    # ==========================================
    def mostrar_pantalla_bienvenida(self):
        for widget in self.main_container.winfo_children(): widget.destroy()

        tk.Label(self.main_container, text="ESTRUCTURA JERÁRQUICA AHP (Oficina General de Planificación)",
                 font=("Arial", 20, "bold"), bg="#f8f9fa", fg="#1a252f").pack(pady=(15, 0))
        tk.Label(self.main_container,
                 text="* Tip: Si tu pantalla es pequeña, usa el ratón para arrastrar el diagrama y explorarlo sin perder nitidez.",
                 font=("Arial", 10, "italic"), bg="#f8f9fa", fg="#7f8c8d").pack(pady=(0, 10))

        frame_canvas = tk.Frame(self.main_container, bg="#f8f9fa")
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=5)

        scroll_x = ttk.Scrollbar(frame_canvas, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        scroll_y = ttk.Scrollbar(frame_canvas, orient="vertical")
        scroll_y.pack(side="right", fill="y")

        c = tk.Canvas(frame_canvas, bg="#ffffff", bd=1, relief="solid", highlightthickness=0,
                      xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        c.pack(side="left", fill="both", expand=True)

        scroll_x.config(command=c.xview)
        scroll_y.config(command=c.yview)

        c_meta, c_leg, c_est, c_tec = "#1c2833", "#c0392b", "#27ae60", "#d4ac0d"
        c_sub, c_line, c_line_main = "#eaeded", "#d5d8dc", "#7f8c8d"

        x_subs = [100, 250, 400, 525, 675, 825, 950, 1100, 1250]
        x_alts = [230, 530, 830, 1130]
        y_sub_bottom, y_alt_top = 320, 440

        for xs in x_subs:
            for xa in x_alts: c.create_line(xs, y_sub_bottom, xa, y_alt_top, fill=c_line, width=1)

        c.create_rectangle(475, 20, 875, 80, fill=c_meta, outline="#17202a", width=2)
        c.create_text(675, 50,
                      text="META PRINCIPAL:\nReducir tiempos de espera optimizando la capacidad de atención en SIGA",
                      fill="white", font=("Arial", 12, "bold"), justify="center")

        c.create_line(675, 80, 675, 110, width=2, fill=c_line_main)
        c.create_line(250, 110, 1100, 110, width=2, fill=c_line_main)
        c.create_line(250, 110, 250, 130, arrow=tk.LAST, width=2, fill=c_line_main)
        c.create_line(675, 110, 675, 130, arrow=tk.LAST, width=2, fill=c_line_main)
        c.create_line(1100, 110, 1100, 130, arrow=tk.LAST, width=2, fill=c_line_main)

        c.create_rectangle(110, 130, 390, 190, fill="white", outline=c_leg, width=2)
        c.create_text(250, 160, text="1. FILTRO LEGAL (Austeridad)\n[ Peso: 50% ]", font=("Arial", 11, "bold"),
                      fill=c_leg, justify="center")

        c.create_rectangle(535, 130, 815, 190, fill="white", outline=c_est, width=2)
        c.create_text(675, 160, text="2. FILTRO ESTRATÉGICO (Impacto)\n[ Peso: 30% ]", font=("Arial", 11, "bold"),
                      fill=c_est, justify="center")

        c.create_rectangle(960, 130, 1240, 190, fill="white", outline=c_tec, width=2)
        c.create_text(1100, 160, text="3. FILTRO TÉCNICO (Sustento)\n[ Peso: 20% ]", font=("Arial", 11, "bold"),
                      fill=c_tec, justify="center")

        c.create_line(250, 190, 250, 220, width=2, fill=c_line_main)
        c.create_line(100, 220, 400, 220, width=2, fill=c_line_main)
        for x in [100, 250, 400]: c.create_line(x, 220, x, 240, arrow=tk.LAST, width=2, fill=c_line_main)

        c.create_line(675, 190, 675, 220, width=2, fill=c_line_main)
        c.create_line(525, 220, 825, 220, width=2, fill=c_line_main)
        for x in [525, 675, 825]: c.create_line(x, 220, x, 240, arrow=tk.LAST, width=2, fill=c_line_main)

        c.create_line(1100, 190, 1100, 220, width=2, fill=c_line_main)
        c.create_line(950, 220, 1250, 220, width=2, fill=c_line_main)
        for x in [950, 1100, 1250]: c.create_line(x, 220, x, 240, arrow=tk.LAST, width=2, fill=c_line_main)

        def draw_sub(x, text):
            c.create_rectangle(x - 70, 240, x + 70, 320, fill=c_sub, outline="#a6acaf", width=1)
            c.create_text(x, 280, text=text, font=("Arial", 9, "bold"), fill="#2c3e50", justify="center")

        draw_sub(100, "1.1 Cumple\nLey Presupuesto")
        draw_sub(250, "1.2 Sin Gastos\nProhibidos")
        draw_sub(400, "1.3 Sin Cruce\nde Fondos")
        draw_sub(525, "2.1 Licenciamiento\ny Acreditación")
        draw_sub(675, "2.2 Inversiones\ncon alto avance")
        draw_sub(825, "2.3 Continuidad de\nServicios Básicos")
        draw_sub(950, "3.1 Certificación\nPresupuestaria (CCP)")
        draw_sub(1100, "3.2 Formatos y\nDatos Completos")
        draw_sub(1250, "3.3 Alerta de\nRiesgo Fiscal")

        def draw_alt(x, title, subtitle, color):
            c.create_rectangle(x - 130, 440, x + 130, 520, fill="white", outline=color, width=3)
            c.create_text(x, 465, text=title, font=("Arial", 11, "bold"), fill=color, justify="center")
            c.create_text(x, 495, text=subtitle, font=("Arial", 10), fill="#34495e", justify="center")

        draw_alt(x_alts[0], "RECHAZO AUTOMÁTICO", "Rebota por ser ilegal (ej. bonos)", "#c0392b")
        draw_alt(x_alts[1], "OBSERVADO Y DEVUELTO", "Retorna a facultad por falta de CCP", "#d4ac0d")
        draw_alt(x_alts[2], "ATENCIÓN REGULAR", "Trámite correcto (Cola normal)", "#7f8c8d")
        draw_alt(x_alts[3], "PRIORIDAD MÁXIMA", "Pasa al puesto N° 1 de inmediato", "#27ae60")

        c.update_idletasks()
        c.config(scrollregion=c.bbox("all"))

        def scroll_vertical(event):
            c.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def scroll_horizontal(event):
            c.xview_scroll(int(-1 * (event.delta / 120)), "units")

        def arrastrar_inicio(event):
            c.scan_mark(event.x, event.y)

        def arrastrar_movimiento(event):
            c.scan_dragto(event.x, event.y, gain=1)

        c.bind("<MouseWheel>", scroll_vertical)
        c.bind("<Shift-MouseWheel>", scroll_horizontal)
        c.bind("<ButtonPress-1>", arrastrar_inicio)
        c.bind("<B1-Motion>", arrastrar_movimiento)

        tk.Label(self.main_container, text="* El algoritmo cruza estos 9 subcriterios al instante.",
                 font=("Arial", 11, "italic"), bg="#f8f9fa", fg="#5c6a79").pack(pady=(5, 5))

        frame_botones = tk.Frame(self.main_container, bg="#f8f9fa")
        frame_botones.pack(pady=10)

        tk.Button(frame_botones, text="📘 VER GUÍA DE ESTADOS", bg="#34495e", fg="white", font=("Arial", 12, "bold"),
                  padx=20, pady=10, cursor="hand2", command=self.mostrar_diccionario_estados).grid(row=0, column=0,
                                                                                                   padx=10)
        tk.Button(frame_botones, text="⚙️ INICIAR MOTOR AHP ➔", bg="#004080", fg="white", font=("Arial", 12, "bold"),
                  padx=20, pady=10, cursor="hand2", command=self.mostrar_pantalla_simulador).grid(row=0, column=1,
                                                                                                  padx=10)

    # ==========================================
    # VENTANAS EMERGENTES (POP-UPS)
    # ==========================================
    def mostrar_diccionario_estados(self):
        win = tk.Toplevel(self.root)
        win.title("Guía Ejecutiva - Estados de Priorización SIGA")
        w, h = min(1000, self.root.winfo_width() - 50), min(750, self.root.winfo_height() - 50)
        win.geometry(f"{w}x{h}")
        win.configure(bg="#ffffff")
        win.grab_set();
        win.focus_force()

        c_win = tk.Canvas(win, bg="#ffffff", highlightthickness=0)
        scroll_win = ttk.Scrollbar(win, orient="vertical", command=c_win.yview)
        f_win = tk.Frame(c_win, bg="#ffffff")

        f_win.bind("<Configure>", lambda e: c_win.configure(scrollregion=c_win.bbox("all")))
        c_win.create_window((0, 0), window=f_win, anchor="nw", width=w - 30)
        c_win.configure(yscrollcommand=scroll_win.set)
        c_win.pack(side="left", fill="both", expand=True);
        scroll_win.pack(side="right", fill="y")

        tk.Label(f_win, text="ESTADOS DE PRIORIZACIÓN EN EL SIGA (MODELO AHP)", font=("Arial", 18, "bold"),
                 bg="#ffffff", fg="#1a252f").pack(pady=(25, 5))

        def crear_tarjeta(parent, titulo, color_bg, color_fg, significado, criterios, accion):
            f = tk.Frame(parent, bg=color_bg, bd=1, relief="solid")
            f.pack(fill="x", padx=20, pady=10)
            tk.Label(f, text=titulo, font=("Arial", 13, "bold"), bg=color_bg, fg=color_fg).pack(anchor="w", padx=15,
                                                                                                pady=(10, 5))
            body_f = tk.Frame(f, bg=color_bg);
            body_f.pack(fill="x", padx=15, pady=(0, 10));
            body_f.columnconfigure(1, weight=1)
            tk.Label(body_f, text="• Significado:", font=("Arial", 11, "bold"), bg=color_bg, fg="#2c3e50").grid(row=0,
                                                                                                                column=0,
                                                                                                                sticky="nw",
                                                                                                                pady=2)
            tk.Label(body_f, text=significado, font=("Arial", 11), bg=color_bg, fg="#2c3e50", justify="left",
                     wraplength=w - 250).grid(row=0, column=1, sticky="w", padx=10, pady=2)
            tk.Label(body_f, text="• ¿Por qué se asigna?:", font=("Arial", 11, "bold"), bg=color_bg, fg="#2c3e50").grid(
                row=1, column=0, sticky="nw", pady=2)
            tk.Label(body_f, text=criterios, font=("Arial", 11), bg=color_bg, fg="#2c3e50", justify="left",
                     wraplength=w - 250).grid(row=1, column=1, sticky="w", padx=10, pady=2)
            tk.Label(body_f, text="• Acción del Analista:", font=("Arial", 11, "bold"), bg=color_bg, fg="#2c3e50").grid(
                row=2, column=0, sticky="nw", pady=2)
            tk.Label(body_f, text=accion, font=("Arial", 11), bg=color_bg, fg="#2c3e50", justify="left",
                     wraplength=w - 250).grid(row=2, column=1, sticky="w", padx=10, pady=2)

        crear_tarjeta(f_win, "🟢 1. PRIORIDAD MÁXIMA (El Trámite Crítico)", "#d4edda", "#155724",
                      "Son expedientes vitales y urgentes. Pasan directamente al primer lugar de la fila.",
                      "Impactan en la operatividad de la UNMSM, aseguran el Licenciamiento (ej. membresías DOI) o garantizan obras de inversión.",
                      "Revisión y despacho prioritario. La facultad adjuntó todo de forma impecable.")
        crear_tarjeta(f_win, "⚪ 2. ATENCIÓN REGULAR (La Fila Común)", "#f8f9fa", "#333333",
                      "Trámites administrativos del día a día. Avanzan a su ritmo normal.",
                      "Requerimientos legales y bien sustentados, pero que no resuelven ninguna urgencia crítica.",
                      "Se atienden estrictamente después de haber liberado todos los expedientes de Prioridad Máxima (Verdes).")
        crear_tarjeta(f_win, "🟡 3. OBSERVADO (Devolución Automática a Origen)", "#fff3cd", "#856404",
                      "El expediente NUNCA ingresa a la bandeja de OGPL. Es devuelto automáticamente a la Facultad remitente.",
                      "La facultad omitió adjuntar la Certificación Presupuestaria (CCP) o formatos técnicos requeridos.",
                      "NIGUNA (Cero desgaste). El analista no lo ve. El sistema exige a la facultad que subsane el error antes de poder enviarlo nuevamente.")
        crear_tarjeta(f_win, "🔴 4. RECHAZO AUTOMÁTICO (Inviable por Ley)", "#f2dede", "#a94442",
                      "El trámite rebota en milisegundos ('Rebote en puerta'). Jamás llega a la bandeja de trabajo.",
                      "Solicitan conceptos expresamente prohibidos por la Ley de Presupuesto (Ej: bonos no autorizados o cruce indebido de fondos).",
                      "NIGUNA (Cero desgaste). El sistema cierra el trámite por inviabilidad legal.")

        tk.Button(f_win, text="Cerrar Ventana", font=("Arial", 12, "bold"), bg="#5c6a79", fg="white", padx=15, pady=5,
                  cursor="hand2", command=win.destroy).pack(pady=20)

    def mostrar_info_pesos(self):
        # Explicación amigable de los Pesos
        win = tk.Toplevel(self.root)
        win.title("¿Cómo decide el sistema la prioridad?")
        win.geometry("800x550")
        win.configure(bg="#ffffff", padx=30, pady=20)
        win.grab_set();
        win.focus_force()

        tk.Label(win, text="¿CÓMO DECIDE EL SISTEMA QUÉ ES MÁS IMPORTANTE?", font=("Arial", 16, "bold"), bg="#ffffff",
                 fg="#1a252f").pack(pady=(0, 10))
        tk.Label(win,
                 text="El sistema distribuye 100 puntos basándose en tres niveles de importancia. No todos los requisitos valen lo mismo:",
                 font=("Arial", 12, "italic"), bg="#ffffff", fg="#5c6a79", wraplength=700).pack(pady=(0, 20))

        f1 = tk.Frame(win, bg="#ffdddd", bd=1, relief="solid");
        f1.pack(fill="x", pady=8)
        tk.Label(f1, text="🔴 1. Cumplimiento de Ley y Austeridad (Vale 50%)", font=("Arial", 12, "bold"), bg="#ffdddd",
                 fg="#a94442", anchor="w").pack(fill="x", padx=15, pady=(10, 0))
        tk.Label(f1,
                 text="La regla de oro de la oficina. Si un trámite pide algo ilegal (como un bono no permitido), el sistema lo bloquea y lo rechaza al instante, sin importar quién lo pida o cuán urgente parezca. Por eso se lleva la mitad de los puntos.",
                 font=("Arial", 11), bg="#ffdddd", justify="left", wraplength=700).pack(anchor="w", padx=15, pady=10)

        f2 = tk.Frame(win, bg="#d4edda", bd=1, relief="solid");
        f2.pack(fill="x", pady=8)
        tk.Label(f2, text="🟢 2. Impacto Estratégico en San Marcos (Vale 30%)", font=("Arial", 12, "bold"), bg="#d4edda",
                 fg="#155724", anchor="w").pack(fill="x", padx=15, pady=(10, 0))
        tk.Label(f2,
                 text="El valor real para la universidad. Aquí el sistema se pregunta: ¿Este pago asegura el Licenciamiento (códigos DOI)? ¿Evita el corte de luz/agua? ¿Es una obra avanzada? Le damos prioridad alta a lo que hace avanzar a la universidad, no a los papeles de rutina.",
                 font=("Arial", 11), bg="#d4edda", justify="left", wraplength=700).pack(anchor="w", padx=15, pady=10)

        f3 = tk.Frame(win, bg="#fff3cd", bd=1, relief="solid");
        f3.pack(fill="x", pady=8)
        tk.Label(f3, text="🟡 3. Sustento Técnico y Formatos (Vale 20%)", font=("Arial", 12, "bold"), bg="#fff3cd",
                 fg="#856404", anchor="w").pack(fill="x", padx=15, pady=(10, 0))
        tk.Label(f3,
                 text="El orden administrativo. ¿La facultad adjuntó su Certificación Presupuestaria (CCP)? ¿Llenó bien los anexos? Es importante, pero es menos crítico que cumplir la ley o salvar el licenciamiento. Si se equivocan aquí, el sistema simplemente les devuelve el trámite para que lo corrijan.",
                 font=("Arial", 11), bg="#fff3cd", justify="left", wraplength=700).pack(anchor="w", padx=15, pady=10)

        tk.Button(win, text="¡Entendido!", font=("Arial", 12, "bold"), bg="#004080", fg="white", padx=20, pady=5,
                  cursor="hand2", command=win.destroy).pack(pady=20)

    def mostrar_info_kpis(self):
        # NUEVA VENTANA: EXPLICACIÓN DE LOS KPIs (El "Pitch" para el Jefe)
        win = tk.Toplevel(self.root)
        win.title("Impacto Operativo - Entendiendo el KPI")
        win.geometry("900x650")
        win.configure(bg="#ffffff", padx=30, pady=20)
        win.grab_set();
        win.focus_force()

        tk.Label(win, text="EL INDICADOR CLAVE DE RENDIMIENTO (KPI)", font=("Arial", 16, "bold"), bg="#ffffff",
                 fg="#1a252f").pack(pady=(0, 5))
        tk.Label(win,
                 text="Esta es la métrica que demuestra cuantitativamente el valor de tu proyecto ante la jefatura.",
                 font=("Arial", 12, "italic"), bg="#ffffff", fg="#5c6a79").pack(pady=(0, 15))

        # Tarjeta 1: Total Procesados
        f1 = tk.Frame(win, bg="#e8f4f8", bd=1, relief="solid");
        f1.pack(fill="x", pady=8)
        tk.Label(f1, text="📊 1. Total Procesados (Ej. 68)", font=("Arial", 12, "bold"), bg="#e8f4f8", fg="#004080",
                 anchor="w").pack(fill="x", padx=15, pady=(10, 0))
        tk.Label(f1,
                 text="Significa que el algoritmo AHP leyó con éxito todos los expedientes de la base de datos (correspondientes al mes) y los clasificó en menos de un segundo.",
                 font=("Arial", 11), bg="#e8f4f8", justify="left", wraplength=800).pack(anchor="w", padx=15, pady=10)

        # Tarjeta 2: Reprocesos Evitados
        f2 = tk.Frame(win, bg="#fff3cd", bd=1, relief="solid");
        f2.pack(fill="x", pady=8)
        tk.Label(f2, text="⏱️ 2. Reprocesos Evitados (Ej. 7.0 Horas)", font=("Arial", 12, "bold"), bg="#fff3cd",
                 fg="#856404", anchor="w").pack(fill="x", padx=15, pady=(10, 0))
        txt_ahorro = (
            "Este es el 'Ahorro de Tiempo' real. En la lógica interna le programamos al sistema penalidades de tiempo basadas en la vida real de un analista:\n\n"
            "• Expediente Ilegal (Rechazado): Se asume un ahorro de 1.5 horas (tiempo que el analista hubiera perdido leyendo el documento, buscando leyes y redactando el informe de rechazo).\n"
            "• Expediente Incompleto (Devuelto a origen): Se asume un ahorro de 1.0 hora (tiempo perdido en revisar, notar que falta el anexo y devolverlo)."
        )
        tk.Label(f2, text=txt_ahorro, font=("Arial", 11), bg="#fff3cd", justify="left", wraplength=800).pack(anchor="w",
                                                                                                             padx=15,
                                                                                                             pady=10)

        # Tarjeta 3: Qué significa para el Jefe
        f3 = tk.Frame(win, bg="#d4edda", bd=1, relief="solid");
        f3.pack(fill="x", pady=8)
        tk.Label(f3, text="🎯 ¿Qué quiere decir el número?", font=("Arial", 12, "bold"), bg="#d4edda",
                 fg="#155724", anchor="w").pack(fill="x", padx=15, pady=(10, 0))
        tk.Label(f3,
                 text="Significa que el sistema detectó expedientes incompletos y los bloqueó automáticamente. Al hacerlo, le acaba de ahorrar a la oficina casi una jornada laboral completa de tiempo desperdiciado en trámites que no iban a llegar a nada.",
                 font=("Arial", 11), bg="#d4edda", justify="left", wraplength=800).pack(anchor="w", padx=15, pady=10)

        # Tarjeta 4: El "Pitch"
        f4 = tk.Frame(win, bg="#2c3e50", bd=1, relief="solid");
        f4.pack(fill="x", pady=8)
        tk.Label(f4, text="🗣️ RESUMEN:", font=("Arial", 12, "bold"), bg="#2c3e50",
                 fg="#f1c40f", anchor="w").pack(fill="x", padx=15, pady=(10, 0))
        pitch = "\"Con un solo clic, el sistema procesó 68 expedientes y nos acaba de ahorrar 7 horas de trabajo. En lugar de que nuestros analistas pasen todo el día devolviendo trámites mal hechos por las facultades, el sistema ya lo hizo por ellos. Ahora los analistas pueden dedicar esas 7 horas exclusivamente a los expedientes VIP (verdes).\""
        tk.Label(f4, text=pitch, font=("Arial", 12, "italic"), bg="#2c3e50", fg="white", justify="left",
                 wraplength=800).pack(anchor="w", padx=15, pady=10)

        tk.Button(win, text="¡Comprendido!", font=("Arial", 12, "bold"), bg="#004080", fg="white", padx=20, pady=5,
                  cursor="hand2", command=win.destroy).pack(pady=15)

    # ==========================================
    # PANTALLA 2: EL SIMULADOR AHP (MENÚ AMIGABLE)
    # ==========================================
    def mostrar_pantalla_simulador(self):
        for widget in self.main_container.winfo_children(): widget.destroy()
        self.main_container.configure(bg="#f0f0f0")

        frame_jefatura = tk.LabelFrame(self.main_container, text=" 1. Nivel de Importancia de los Filtros (Pesos AHP) ",
                                       font=("Arial", 11, "bold"), bg="white")
        frame_jefatura.pack(fill="x", padx=15, pady=(15, 10))

        for i in range(10): frame_jefatura.columnconfigure(i, weight=1)

        btn_info = tk.Button(frame_jefatura, text="ℹ️ ¿Qué significa esto?", font=("Arial", 9, "bold"), bg="#17a2b8",
                             fg="white", cursor="hand2", command=self.mostrar_info_pesos)
        btn_info.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        tk.Label(frame_jefatura, text="🔴 Filtro Legal (Cumplimiento) %:", bg="white", font=("Arial", 10)).grid(row=0,
                                                                                                               column=1,
                                                                                                               padx=2,
                                                                                                               sticky="e")
        # El Spinbox arranca con "0": se vacía antes de insertar el peso inicial (si no, queda "500").
        self.peso_legal = tk.Spinbox(frame_jefatura, from_=0, to=100, width=4, font=("Arial", 10));
        self.peso_legal.delete(0, "end");
        self.peso_legal.insert(0, "50");
        self.peso_legal.grid(row=0, column=2, padx=2, sticky="w")

        tk.Label(frame_jefatura, text="🟢 Filtro Estratégico (Impacto) %:", bg="white", font=("Arial", 10)).grid(row=0,
                                                                                                                column=3,
                                                                                                                padx=2,
                                                                                                                sticky="e")
        self.peso_estrategico = tk.Spinbox(frame_jefatura, from_=0, to=100, width=4, font=("Arial", 10));
        self.peso_estrategico.delete(0, "end");
        self.peso_estrategico.insert(0, "30");
        self.peso_estrategico.grid(row=0, column=4, padx=2, sticky="w")

        tk.Label(frame_jefatura, text="🟡 Filtro Técnico (Sustento) %:", bg="white", font=("Arial", 10)).grid(row=0,
                                                                                                             column=5,
                                                                                                             padx=2,
                                                                                                             sticky="e")
        self.peso_tecnico = tk.Spinbox(frame_jefatura, from_=0, to=100, width=4, font=("Arial", 10));
        self.peso_tecnico.delete(0, "end");
        self.peso_tecnico.insert(0, "20");
        self.peso_tecnico.grid(row=0, column=6, padx=2, sticky="w")

        self.btn_simular = tk.Button(frame_jefatura, text="▶ Procesar Bandeja", bg="#004080", fg="white",
                                     font=("Arial", 10, "bold"), command=self.procesar_excel)
        self.btn_simular.grid(row=0, column=7, padx=10)
        self.btn_exportar = tk.Button(frame_jefatura, text="💾 Exportar Excel", bg="#28a745", fg="white",
                                      font=("Arial", 10, "bold"), state="disabled", command=self.exportar_excel)
        self.btn_exportar.grid(row=0, column=8, padx=10)
        self.btn_volver = tk.Button(frame_jefatura, text="⬅ Volver", font=("Arial", 9),
                                    command=self.mostrar_pantalla_bienvenida)
        self.btn_volver.grid(row=0, column=9, padx=10)

        # Fila del motor de IA
        fila_ia = tk.Frame(frame_jefatura, bg="white")
        fila_ia.grid(row=1, column=0, columnspan=10, sticky="ew", padx=10, pady=(0, 10))
        tk.Label(fila_ia, text="🤖 Motor:", bg="white", font=("Arial", 10, "bold")).pack(side="left")
        tk.Radiobutton(fila_ia, text="IA (Claude)", variable=self.motor_var, value="ia", bg="white",
                       font=("Arial", 10), state="normal" if MotorIA else "disabled").pack(side="left", padx=(5, 0))
        tk.Radiobutton(fila_ia, text="Reglas AHP (sin IA)", variable=self.motor_var, value="ahp", bg="white",
                       font=("Arial", 10)).pack(side="left", padx=(5, 15))
        tk.Label(fila_ia, text="Modelo:", bg="white", font=("Arial", 10)).pack(side="left")
        ttk.Combobox(fila_ia, textvariable=self.modelo_var, values=list(MODELOS), state="readonly",
                     width=32).pack(side="left", padx=(5, 15))
        tk.Button(fila_ia, text="📚 Contexto normativo", font=("Arial", 9, "bold"), bg="#6f42c1", fg="white",
                  cursor="hand2", command=self.mostrar_contexto_normativo).pack(side="left", padx=5)
        tk.Button(fila_ia, text="🧠 Memoria IA", font=("Arial", 9, "bold"), bg="#6f42c1", fg="white",
                  cursor="hand2", command=self.mostrar_memoria).pack(side="left", padx=5)
        self.barra_progreso = ttk.Progressbar(fila_ia, mode="determinate", maximum=1.0, length=180)
        self.barra_progreso.pack(side="left", padx=(15, 5))
        self.lbl_progreso = tk.Label(fila_ia, text="" if MotorIA else "Instale 'anthropic' para habilitar la IA.",
                                     bg="white", fg="#5c6a79", font=("Arial", 9, "italic"))
        self.lbl_progreso.pack(side="left", fill="x", expand=True, anchor="w")

        main_paned = tk.PanedWindow(self.main_container, orient=tk.HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # TABLA
        frame_bandeja = tk.LabelFrame(main_paned, text=" 2. Bandeja de Atención AHP (Doble clic para Auditar) ",
                                      font=("Arial", 11, "bold"))
        main_paned.add(frame_bandeja, minsize=500)

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        style.configure("Treeview", font=("Arial", 10), rowheight=25)

        columnas = ("Puesto", "N° Exp", "Dependencia", "Asunto", "Sustento Técnico", "Puntaje")
        self.tabla = ttk.Treeview(frame_bandeja, columns=columnas, show="headings")

        self.tabla.column("Puesto", width=55, anchor="center", stretch=False)
        self.tabla.column("N° Exp", width=60, anchor="center", stretch=False)
        self.tabla.column("Dependencia", width=150, anchor="w", stretch=True)
        self.tabla.column("Asunto", width=300, anchor="w", stretch=True)
        self.tabla.column("Sustento Técnico", width=110, anchor="center", stretch=False)
        self.tabla.column("Puntaje", width=70, anchor="center", stretch=False)

        for col in columnas: self.tabla.heading(col, text=col)

        self.tabla.tag_configure("rechazado", background="#ffcccc");
        self.tabla.tag_configure("top", background="#d4edda")
        self.tabla.tag_configure("normal", background="#ffffff");
        self.tabla.tag_configure("devuelto", background="#fff3cd")
        self.tabla.tag_configure("pendiente", background="#e2e3e5")

        self.tabla.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(frame_bandeja, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscroll=scroll.set);
        scroll.pack(side="right", fill="y")
        self.tabla.bind("<Double-1>", self.mostrar_auditoria)

        # DASHBOARD
        frame_dashboard = tk.LabelFrame(main_paned, text=" 3. Impacto Operativo ", font=("Arial", 11, "bold"),
                                        bg="white")
        main_paned.add(frame_dashboard, minsize=300)

        self.lbl_total = tk.Label(frame_dashboard, text="Total Procesados: 0", font=("Arial", 13, "bold"), bg="white")
        self.lbl_total.pack(pady=5)
        self.lbl_ahorro = tk.Label(frame_dashboard, text="Reprocesos Evitados: 0 hrs", font=("Arial", 13, "bold"),
                                   fg="#a94442", bg="white")
        self.lbl_ahorro.pack(pady=5)

        # NUEVO BOTÓN: Explicación de KPIs
        btn_kpi = tk.Button(frame_dashboard, text="💡 ¿Qué significan estos números?", font=("Arial", 9, "bold"),
                            bg="#17a2b8", fg="white", cursor="hand2", command=self.mostrar_info_kpis)
        btn_kpi.pack(pady=(0, 5))

        self.fig = Figure(figsize=(4, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_dashboard)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)

    # ==========================================
    # LÓGICA AHP
    # ==========================================
    def evaluar_subcriterios_ahp(self, asunto, w_leg, w_est, w_tec):
        asunto_lower = str(asunto).lower()
        if any(p in asunto_lower for p in ["bono ", "aumento", "aguinaldo"]):
            nota_legal, just_legal = 0, "Alerta: Concepto restringido por Ley de Presupuesto."
        else:
            nota_legal, just_legal = 100, "Cumple normativa."

        if any(p in asunto_lower for p in ["doi", "crossref", "licenciamiento", "agua", "luz"]):
            nota_est, just_est = 100, "Crítico: Servicios o Licenciamiento."
        elif any(p in asunto_lower for p in ["inversión", "obra", "cui", "2307554"]):
            nota_est, just_est = 90, "Alto: Continuidad Inversiones."
        elif any(p in asunto_lower for p in ["subvención", "transferencia"]):
            nota_est, just_est = 60, "Medio: Operatividad de Facultades."
        else:
            nota_est, just_est = 20, "Bajo: Trámite rutinario."

        if "subsanado" in asunto_lower:
            nota_tec, just_tec, txt_ccp = 100, "Subsanación confirmada.", "Subsanado (OK)"
        else:
            tiene_ccp = random.random() > 0.15
            nota_tec, just_tec, txt_ccp = (100, "Certificación vinculada.", "CCP Vinculado") if tiene_ccp else (0,
                                                                                                                "Falta Certificación (CCP).",
                                                                                                                "Falta Anexo/CCP")

        if nota_legal == 0:
            puntaje, estado, tag = 0, "RECHAZO AUTOMÁTICO", "rechazado"
        else:
            puntaje = (nota_legal * w_leg) + (nota_est * w_est) + (nota_tec * w_tec)
            if puntaje >= 80:
                estado, tag = "PRIORIDAD MÁXIMA", "top"
            elif nota_tec == 0:
                estado, tag = "OBSERVADO (Devuelto a Origen)", "devuelto"
            else:
                estado, tag = "ATENCIÓN REGULAR", "normal"

        datos_audit = {"legal": (nota_legal, just_legal), "estrategico": (nota_est, just_est),
                       "tecnico": (nota_tec, just_tec), "estado": estado}
        return round(puntaje, 1), estado, tag, txt_ccp, datos_audit

    def procesar_excel(self):
        if pd is None:
            messagebox.showerror("Error", "Falta librerías: pip install pandas matplotlib openpyxl");
            return
        try:
            w_leg, w_est, w_tec = float(self.peso_legal.get()) / 100, float(self.peso_estrategico.get()) / 100, float(
                self.peso_tecnico.get()) / 100
        except ValueError:
            return
        if abs(w_leg + w_est + w_tec - 1) > 0.001:
            messagebox.showwarning("Pesos AHP", "Los pesos de los tres filtros deben sumar 100%.")
            return

        file_path = 'MES DE FEBRERO.xlsx'
        if not os.path.exists(file_path):
            file_path = filedialog.askopenfilename(title="Seleccionar Excel", filetypes=[("Excel", "*.xlsx *.xls")])
            if not file_path: return

        expedientes_excel = self.leer_expedientes(file_path)
        if self.motor_var.get() == "ia":
            self.procesar_con_ia(file_path, expedientes_excel, (w_leg, w_est, w_tec))
            return

        for item in self.tabla.get_children(): self.tabla.delete(item)

        expedientes, self.auditoria_db, conteos = [], {}, {"top": 0, "normal": 0, "devuelto": 0, "rechazado": 0}

        for exp in expedientes_excel:
            nro_exp, dep, asunto = exp["nro_exp"], exp["dependencia"][:30] + "...", exp["asunto"]
            puntaje, estado, tag, txt_ccp, d_audit = self.evaluar_subcriterios_ahp(asunto, w_leg, w_est, w_tec)
            self.auditoria_db[exp["ref"]] = d_audit;
            conteos[tag] += 1
            expedientes.append(
                {"ref": exp["ref"], "N° Expediente": nro_exp, "Dependencia": dep, "Asunto": asunto,
                 "Sustento (CCP)": txt_ccp, "Puntaje": puntaje, "Estado": estado, "Tag": tag})

        exp_ordenados = sorted(expedientes, key=lambda x: x["Puntaje"], reverse=True)
        self.df_exportar = pd.DataFrame(exp_ordenados).drop(columns=['Tag', 'ref'])

        for puesto, exp in enumerate(exp_ordenados, start=1):
            self.tabla.insert("", "end", iid=exp["ref"], values=(puesto, exp["N° Expediente"], exp["Dependencia"],
                                                                 exp["Asunto"][:85] + "...",
                                                                 exp["Sustento (CCP)"], exp["Puntaje"]),
                              tags=(exp["Tag"],))
        self.actualizar_dashboard(conteos)
        self.btn_exportar.config(state="normal")
        messagebox.showinfo("Motor AHP", "Expedientes procesados. Trámites sin CCP han sido devueltos virtualmente.")

    def leer_expedientes(self, file_path):
        """Lee la bandeja del Excel. Cada expediente conserva todas sus columnas no vacías
        para que la IA pueda captar parámetros más allá del asunto."""
        df = pd.read_excel(file_path, sheet_name='CAT_1_Aprobación, Modifica', skiprows=3)
        expedientes = []
        for _, row in df.iterrows():
            nro_exp = str(row.get('NRO EXP', 'S/N')).split('.')[0]
            if nro_exp == 'nan' or nro_exp == 'S/N': continue
            campos = {str(col).strip(): str(val).strip() for col, val in row.items()
                      if pd.notna(val) and str(val).strip()}
            expedientes.append({"ref": f"E{len(expedientes) + 1:03d}", "nro_exp": nro_exp,
                                "dependencia": str(row.get('REMITENTE', '')),
                                "asunto": str(row.get('ASUNTO', '')).replace("\n", " "),
                                "campos": campos})
        return expedientes

    # ==========================================
    # MOTOR DE IA
    # ==========================================
    def obtener_api_key(self):
        if self.api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            return self.api_key
        if not self.api_key_preguntada:
            self.api_key_preguntada = True
            clave = simpledialog.askstring(
                "API key de Anthropic",
                "No se encontró la variable de entorno ANTHROPIC_API_KEY.\n"
                "Ingrese su API key (solo se usará durante esta sesión):",
                show="*", parent=self.root)
            if clave and clave.strip():
                self.api_key = clave.strip()
        return self.api_key

    def procesar_con_ia(self, file_path, expedientes, pesos):
        if MotorIA is None:
            messagebox.showerror("Motor IA", "Falta la librería de Anthropic: pip install anthropic pypdf")
            return
        if not expedientes:
            messagebox.showwarning("Motor IA", "El archivo no contiene expedientes para procesar.")
            return
        try:
            motor = MotorIA(MODELOS[self.modelo_var.get()], self.carpeta_contexto, self.memoria,
                            self.obtener_api_key())
        except Exception as e:
            messagebox.showerror("Motor IA", f"No se pudo iniciar el cliente de Anthropic:\n{e}")
            return
        if not motor.documentos:
            messagebox.showerror("Motor IA", "No hay documentos en la carpeta 'contexto_normativo'.\n"
                                             "Agregue la Ley de Presupuesto, el PEI y los criterios OGPL.")
            return
        if motor.avisos:
            messagebox.showwarning("Contexto normativo", "\n".join(motor.avisos))

        for boton in (self.btn_simular, self.btn_exportar, self.btn_volver): boton.config(state="disabled")
        self.barra_progreso["value"] = 0
        self.cola_ia = queue.Queue()
        threading.Thread(target=self.hilo_ia, args=(motor, file_path, expedientes, pesos), daemon=True).start()
        self.root.after(200, self.revisar_cola_ia)

    def hilo_ia(self, motor, file_path, expedientes, pesos):
        # Corre fuera del hilo de Tkinter; se comunica con la interfaz solo a través de la cola.
        try:
            resultado = motor.procesar(expedientes, pesos, os.path.basename(file_path),
                                       progreso=lambda texto, frac: self.cola_ia.put(("progreso", texto, frac)))
            self.cola_ia.put(("fin", resultado))
        except Exception as e:
            self.cola_ia.put(("error", describir_error(e)))

    def revisar_cola_ia(self):
        try:
            while True:
                mensaje = self.cola_ia.get_nowait()
                if mensaje[0] == "progreso":
                    self.lbl_progreso.config(text=mensaje[1])
                    self.barra_progreso["value"] = mensaje[2]
                    continue
                for boton in (self.btn_simular, self.btn_volver): boton.config(state="normal")
                if mensaje[0] == "fin":
                    self.mostrar_resultado_ia(mensaje[1])
                else:
                    self.lbl_progreso.config(text="El procesamiento con IA falló.")
                    messagebox.showerror("Motor IA", mensaje[1])
                return
        except queue.Empty:
            pass
        self.root.after(200, self.revisar_cola_ia)

    def mostrar_resultado_ia(self, resultado):
        for item in self.tabla.get_children(): self.tabla.delete(item)
        self.auditoria_db = {}
        conteos = {"top": 0, "normal": 0, "devuelto": 0, "rechazado": 0}
        filas_exportar = []

        for ev in resultado["evaluaciones"]:
            ev["total"], ev["pesos"] = resultado["total"], resultado["pesos"]
            self.auditoria_db[ev["ref"]] = ev
            if ev["tag"] in conteos: conteos[ev["tag"]] += 1
            if ev["tag"] == "pendiente":
                sustento_tec, puntaje = "—", "—"
            else:
                sustento_tec = "Requiere subsanar" if ev["requiere_subsanacion"] else f"Conforme ({ev['nota_tecnica']})"
                puntaje = ev["puntaje"]
            self.tabla.insert("", "end", iid=ev["ref"],
                              values=(ev["puesto"] or "—", ev["nro_exp"], ev["dependencia"][:30] + "...",
                                      ev["asunto"][:85] + "...", sustento_tec, puntaje),
                              tags=(ev["tag"],))
            parametros = ev.get("parametros", {})
            filas_exportar.append({
                "Puesto": ev["puesto"], "N° Expediente": ev["nro_exp"], "Dependencia": ev["dependencia"],
                "Asunto": ev["asunto"], "Estado": ev["estado"], "Puntaje": ev["puntaje"],
                "Nota Legal": ev.get("nota_legal"), "Nota Estratégica": ev.get("nota_estrategica"),
                "Nota Técnica": ev.get("nota_tecnica"), "Alineamiento Ley": ev.get("alineamiento_ley"),
                "Alineamiento PEI": ev.get("alineamiento_pei"), "Objetivo PEI": ev.get("objetivo_pei"),
                "Base Normativa": ev.get("base_normativa"),
                "Tipo de Trámite": parametros.get("tipo_tramite"), "Concepto de Gasto": parametros.get("concepto_gasto"),
                "Monto": parametros.get("monto"), "Fuente de Financiamiento": parametros.get("fuente_financiamiento"),
                "Meta / Inversión": parametros.get("meta_o_inversion"),
                "Documentos de Sustento": parametros.get("documentos_sustento"), "Urgencia": parametros.get("urgencia"),
                "Sustento Legal": ev.get("sustento_legal"), "Sustento Estratégico": ev.get("sustento_estrategico"),
                "Sustento Técnico": ev.get("sustento_tecnico"), "Sustento del Puntaje": ev.get("sustento_puntaje"),
                "Sustento del Puesto": ev.get("sustento_puesto") or ev.get("error"),
            })

        self.df_exportar = pd.DataFrame(filas_exportar)
        self.actualizar_dashboard(conteos)
        self.btn_exportar.config(state="normal")
        self.barra_progreso["value"] = 1.0
        uso = resultado["uso"]
        self.lbl_progreso.config(
            text=f"Listo. Tokens: {uso['entrada'] + uso['cache_leidos'] + uso['cache_escritos']:,} entrada "
                 f"({uso['cache_leidos']:,} desde caché) · {uso['salida']:,} salida")
        aviso = ""
        if resultado["pendientes"]:
            aviso = (f"\n\n⚠ {resultado['pendientes']} expediente(s) no pudieron evaluarse y quedaron al final como "
                     "PENDIENTE. Doble clic para ver el motivo.")
        messagebox.showinfo("Motor IA", "Expedientes jerarquizados por la IA y registrados en la memoria institucional."
                                        "\nDoble clic en un expediente para ver el sustento y validarlo." + aviso)

    def actualizar_dashboard(self, conteos):
        self.lbl_total.config(text=f"Total Procesados: {sum(conteos.values())}")
        self.lbl_ahorro.config(
            text=f"Reprocesos Evitados: {conteos['rechazado'] * 1.5 + conteos['devuelto'] * 1.0} Horas")
        self.ax.clear()

        labels = ['VIP (Prioridad)', 'Rutina (Normal)', 'Devueltos', 'Rechazados']
        sizes = [conteos['top'], conteos['normal'], conteos['devuelto'], conteos['rechazado']]
        colors = ['#d4edda', '#d9d9d9', '#fff3cd', '#c0392b']

        filtrado = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
        if filtrado:
            f_labels, f_sizes, f_colors = zip(*filtrado)
            self.ax.pie(f_sizes, labels=f_labels, colors=f_colors, autopct='%1.1f%%', startangle=140,
                        textprops={'fontsize': 9, 'weight': 'bold'})
            self.ax.set_title("Distribución de la Cola", fontsize=11, weight="bold")
        self.canvas.draw()

    def mostrar_auditoria(self, event):
        seleccion = self.tabla.selection()
        if not seleccion: return
        datos = self.auditoria_db.get(seleccion[0])
        if not datos: return
        if "tag" in datos:  # Evaluación hecha por el motor de IA
            self.mostrar_auditoria_ia(datos)
            return
        nro_exp = self.tabla.item(seleccion[0], "values")[1]

        top = tk.Toplevel(self.root);
        top.title(f"Auditoría EXP {nro_exp}");
        top.geometry("500x350");
        top.configure(padx=20, pady=20, bg="white")
        tk.Label(top, text=f"Auditoría AHP: EXP {nro_exp}", font=("Arial", 14, "bold"), bg="white").pack(pady=(0, 15))
        for key, titulo in [("legal", "🔴 Filtro Legal"), ("estrategico", "🟢 Filtro Estratégico"),
                            ("tecnico", "🟡 Filtro Técnico")]:
            f = tk.Frame(top, bg="white");
            f.pack(fill="x", pady=5)
            tk.Label(f, text=f"{titulo}: {datos[key][0]} pts", font=("Arial", 11, "bold"), bg="white").pack(anchor="w")
            tk.Label(f, text=f"↳ Razón: {datos[key][1]}", fg="gray", bg="white").pack(anchor="w")
        tk.Label(top, text=f"ESTADO: {datos['estado']}", font=("Arial", 12, "bold"), bg="#004080", fg="white",
                 pady=5).pack(fill="x", pady=20)

    def ventana_desplazable(self, titulo, ancho, alto):
        win = tk.Toplevel(self.root)
        win.title(titulo)
        win.geometry(f"{min(ancho, self.root.winfo_width() - 50)}x{min(alto, self.root.winfo_height() - 50)}")
        win.configure(bg="#ffffff")
        win.focus_force()

        c_win = tk.Canvas(win, bg="#ffffff", highlightthickness=0)
        scroll_win = ttk.Scrollbar(win, orient="vertical", command=c_win.yview)
        f_win = tk.Frame(c_win, bg="#ffffff", padx=20, pady=15)

        f_win.bind("<Configure>", lambda e: c_win.configure(scrollregion=c_win.bbox("all")))
        id_ventana = c_win.create_window((0, 0), window=f_win, anchor="nw")
        c_win.bind("<Configure>", lambda e: c_win.itemconfigure(id_ventana, width=e.width))
        c_win.configure(yscrollcommand=scroll_win.set)
        c_win.pack(side="left", fill="both", expand=True);
        scroll_win.pack(side="right", fill="y")
        win.bind("<MouseWheel>", lambda e: c_win.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        return win, f_win

    def mostrar_auditoria_ia(self, ev):
        win, f = self.ventana_desplazable(f"Auditoría IA - EXP {ev['nro_exp']}", 920, 780)
        ancho = 820
        colores = {"top": ("#d4edda", "#155724"), "normal": ("#f8f9fa", "#333333"),
                   "devuelto": ("#fff3cd", "#856404"), "rechazado": ("#f2dede", "#a94442"),
                   "pendiente": ("#e2e3e5", "#383d41")}
        bg_estado, fg_estado = colores[ev["tag"]]

        def seccion(titulo, texto, color="#2c3e50"):
            tk.Label(f, text=titulo, font=("Arial", 11, "bold"), bg="white", fg=color).pack(anchor="w", pady=(14, 2))
            tk.Label(f, text=texto, font=("Arial", 10), bg="white", justify="left", wraplength=ancho).pack(anchor="w")

        tk.Label(f, text=f"Auditoría IA: EXP {ev['nro_exp']}", font=("Arial", 16, "bold"), bg="white",
                 fg="#1a252f").pack(anchor="w")
        tk.Label(f, text=f"{ev['dependencia']}\n{ev['asunto']}", font=("Arial", 10), bg="white", fg="#5c6a79",
                 justify="left", wraplength=ancho).pack(anchor="w", pady=(2, 10))
        encabezado = (f"PUESTO {ev['puesto']} DE {ev['total']}   ·   {ev['estado']}   ·   {ev['puntaje']} PTS"
                      if ev["puesto"] else ev["estado"])
        tk.Label(f, text=encabezado, font=("Arial", 12, "bold"), bg=bg_estado, fg=fg_estado, pady=6).pack(fill="x")

        if ev["tag"] == "pendiente":
            seccion("Motivo", ev["error"], "#a94442")
            return

        seccion("📌 ¿Por qué ocupa este puesto?", ev["sustento_puesto"], "#004080")

        w_leg, w_est, w_tec = (round(w * 100) for w in ev["pesos"])
        formula = (f"{ev['nota_legal']} × {w_leg}% + {ev['nota_estrategica']} × {w_est}% + "
                   f"{ev['nota_tecnica']} × {w_tec}% = {ev['puntaje']} pts")
        if not ev["viable_legalmente"]:
            formula = "Inviable legalmente → 0 pts (rechazo automático)"
        seccion("🧮 Cálculo del puntaje", f"{formula}\n{ev['sustento_puntaje']}")

        tk.Label(f, text="🔎 Parámetros captados por la IA", font=("Arial", 11, "bold"), bg="white",
                 fg="#2c3e50").pack(anchor="w", pady=(14, 2))
        tabla_param = tk.Frame(f, bg="#f8f9fa", bd=1, relief="solid")
        tabla_param.pack(fill="x")
        tabla_param.columnconfigure(1, weight=1)
        etiquetas = {"tipo_tramite": "Tipo de trámite", "concepto_gasto": "Concepto de gasto", "monto": "Monto",
                     "fuente_financiamiento": "Fuente de financiamiento", "meta_o_inversion": "Meta / inversión",
                     "documentos_sustento": "Documentos de sustento", "urgencia": "Urgencia"}
        for fila, (clave, etiqueta) in enumerate(etiquetas.items()):
            tk.Label(tabla_param, text=f"{etiqueta}:", font=("Arial", 10, "bold"), bg="#f8f9fa").grid(
                row=fila, column=0, sticky="nw", padx=10, pady=2)
            tk.Label(tabla_param, text=ev["parametros"].get(clave, "—"), font=("Arial", 10), bg="#f8f9fa",
                     justify="left", wraplength=ancho - 220).grid(row=fila, column=1, sticky="w", padx=10, pady=2)

        seccion(f"🔴 Filtro Legal: {ev['nota_legal']}/100  ·  Viable: {'Sí' if ev['viable_legalmente'] else 'NO'}"
                f"  ·  Alineamiento con la Ley: {ev['alineamiento_ley']}",
                f"Base normativa: {ev['base_normativa']}\n{ev['sustento_legal']}", "#a94442")
        seccion(f"🟢 Filtro Estratégico: {ev['nota_estrategica']}/100  ·  Alineamiento con el PEI: "
                f"{ev['alineamiento_pei']}",
                f"Objetivo PEI: {ev['objetivo_pei']}\n{ev['sustento_estrategico']}", "#155724")
        seccion(f"🟡 Filtro Técnico: {ev['nota_tecnica']}/100  ·  Requiere subsanación: "
                f"{'Sí' if ev['requiere_subsanacion'] else 'No'}", ev["sustento_tecnico"], "#856404")

        precedentes = self.memoria.obtener_evaluaciones(ev["precedentes_considerados"])
        if precedentes:
            texto_prec = "\n".join(
                f"• P-{p['id']} · EXP {p['nro_exp']} ({p['fecha_procesamiento'][:10]}) · {p['puntaje']} pts · "
                f"{p['estado']} · {'Validación: ' + p['decision'] if p['decision'] else 'Sin validación'}"
                for p in precedentes)
        else:
            texto_prec = "La IA no se apoyó en precedentes de la memoria para este expediente."
        seccion("🧠 Precedentes de la memoria considerados", texto_prec, "#6f42c1")

        # Validación del analista: alimenta la memoria que usará la IA en los próximos procesamientos.
        f_val = tk.LabelFrame(f, text=" ✅ Validación del analista ", font=("Arial", 11, "bold"), bg="white",
                              padx=10, pady=10)
        f_val.pack(fill="x", pady=(18, 5))
        lbl_estado_val = tk.Label(f_val, bg="white", font=("Arial", 10, "italic"), fg="#5c6a79", justify="left",
                                  wraplength=ancho - 40)
        lbl_estado_val.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        def refrescar_estado_validacion():
            registro = self.memoria.obtener_evaluaciones([ev["evaluacion_id"]])
            if registro and registro[0]["decision"]:
                r = registro[0]
                detalle = f"Última validación ({r['fecha_validacion'][:16].replace('T', ' ')}): {r['decision']}"
                if r["puntaje_corregido"] is not None: detalle += f" · puntaje correcto {r['puntaje_corregido']}"
                if r["estado_corregido"]: detalle += f" · estado correcto {r['estado_corregido']}"
                if r["comentario"]: detalle += f"\nComentario: {r['comentario']}"
            else:
                detalle = "Aún no validado. Su validación se guarda en la memoria y orienta a la IA en el futuro."
            lbl_estado_val.config(text=detalle)

        tk.Label(f_val, text="Puntaje correcto:", bg="white").grid(row=1, column=0, sticky="w")
        entrada_puntaje = tk.Entry(f_val, width=8)
        entrada_puntaje.grid(row=1, column=1, sticky="w", padx=(5, 20))
        tk.Label(f_val, text="Estado correcto:", bg="white").grid(row=1, column=2, sticky="w")
        estado_var = tk.StringVar()
        ttk.Combobox(f_val, textvariable=estado_var, state="readonly", width=32,
                     values=[""] + [e for t, e in ESTADOS.items() if t != "pendiente"]).grid(row=1, column=3,
                                                                                          sticky="w", padx=5)
        tk.Label(f_val, text="Comentario / criterio:", bg="white").grid(row=2, column=0, sticky="nw", pady=(8, 0))
        texto_comentario = tk.Text(f_val, height=3, width=70, font=("Arial", 10))
        texto_comentario.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(8, 0))

        def guardar(decision):
            comentario = texto_comentario.get("1.0", "end").strip()
            puntaje_corregido = None
            if decision == "CORREGIDO":
                try:
                    if entrada_puntaje.get().strip():
                        puntaje_corregido = float(entrada_puntaje.get().replace(",", "."))
                        if not 0 <= puntaje_corregido <= 100: raise ValueError
                except ValueError:
                    messagebox.showwarning("Validación", "El puntaje correcto debe ser un número entre 0 y 100.",
                                           parent=win)
                    return
                if not comentario or (puntaje_corregido is None and not estado_var.get()):
                    messagebox.showwarning("Validación", "Para corregir indique el puntaje o estado correcto y "
                                                         "explique el criterio en el comentario.", parent=win)
                    return
            estado_corregido = (estado_var.get() or None) if decision == "CORREGIDO" else None
            self.memoria.guardar_validacion(ev["evaluacion_id"], decision, puntaje_corregido, estado_corregido,
                                            comentario)
            refrescar_estado_validacion()
            messagebox.showinfo("Validación", "Validación registrada. La IA la tomará en cuenta como precedente "
                                              "en los próximos procesamientos.", parent=win)

        f_botones = tk.Frame(f_val, bg="white")
        f_botones.grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))
        tk.Button(f_botones, text="✔ Confirmar decisión de la IA", bg="#28a745", fg="white",
                  font=("Arial", 10, "bold"), cursor="hand2",
                  command=lambda: guardar("CONFIRMADO")).pack(side="left", padx=(0, 10))
        tk.Button(f_botones, text="✎ Guardar corrección", bg="#d4ac0d", fg="white", font=("Arial", 10, "bold"),
                  cursor="hand2", command=lambda: guardar("CORREGIDO")).pack(side="left")
        refrescar_estado_validacion()

        tk.Button(f, text="Cerrar", font=("Arial", 11, "bold"), bg="#5c6a79", fg="white", padx=15,
                  cursor="hand2", command=win.destroy).pack(pady=15)

    def mostrar_contexto_normativo(self):
        if MotorIA is None:
            messagebox.showerror("Contexto normativo", "Falta la librería de Anthropic: pip install anthropic pypdf")
            return
        documentos, avisos = cargar_contexto_normativo(self.carpeta_contexto)
        win, f = self.ventana_desplazable("Contexto normativo de la IA", 780, 560)

        tk.Label(f, text="DOCUMENTOS QUE LA IA USA COMO REFERENCIA", font=("Arial", 15, "bold"), bg="white",
                 fg="#1a252f").pack(anchor="w")
        tk.Label(f, text=f"Carpeta: {self.carpeta_contexto}", font=("Arial", 9), bg="white", fg="#5c6a79").pack(
            anchor="w", pady=(0, 10))
        total = 0
        for doc in documentos:
            tokens = len(doc["texto"]) // 4  # Estimación aproximada (≈ 4 caracteres por token)
            total += tokens
            tk.Label(f, text=f"📄 {doc['nombre']}  —  ~{tokens:,} tokens", font=("Arial", 11), bg="white").pack(
                anchor="w", pady=2)
        if not documentos:
            tk.Label(f, text="No hay documentos cargados.", font=("Arial", 11, "bold"), bg="white",
                     fg="#a94442").pack(anchor="w")
        tk.Label(f, text=f"Total aproximado: ~{total:,} tokens por llamada (se reutiliza desde la caché entre lotes).",
                 font=("Arial", 10, "italic"), bg="white", fg="#5c6a79").pack(anchor="w", pady=(8, 0))

        nombres = " ".join(d["nombre"].lower() for d in documentos)
        avisos = [f"No se detectó {desc} (incluya '{clave}' en el nombre del archivo)."
                  for clave, desc in (("ley", "un archivo de la Ley de Presupuesto"),
                                      ("pei", "un archivo del Plan Estratégico (PEI)"))
                  if clave not in nombres] + avisos
        if avisos:
            tk.Label(f, text="⚠ Avisos", font=("Arial", 11, "bold"), bg="white", fg="#856404").pack(anchor="w",
                                                                                                   pady=(14, 2))
            tk.Label(f, text="\n".join(f"• {a}" for a in avisos), font=("Arial", 10), bg="white", justify="left",
                     wraplength=700).pack(anchor="w")

        def subir_archivos():
            rutas = filedialog.askopenfilenames(parent=win, title="Seleccionar documentos normativos",
                                                filetypes=[("Documentos (PDF, TXT, MD)", "*.pdf *.txt *.md")])
            if not rutas: return
            os.makedirs(self.carpeta_contexto, exist_ok=True)
            for ruta in rutas:
                nombre = os.path.basename(ruta)
                destino = os.path.join(self.carpeta_contexto, nombre)
                if os.path.normcase(os.path.abspath(ruta)) == os.path.normcase(os.path.abspath(destino)): continue
                if os.path.exists(destino) and not messagebox.askyesno(
                        "Contexto normativo", f"'{nombre}' ya existe en la carpeta. ¿Desea reemplazarlo?", parent=win):
                    continue
                try:
                    shutil.copy2(ruta, destino)
                except OSError as e:
                    messagebox.showerror("Contexto normativo", f"No se pudo copiar '{nombre}':\n{e}", parent=win)
            win.destroy()
            self.mostrar_contexto_normativo()  # Reabre la ventana con la lista actualizada

        f_botones = tk.Frame(f, bg="white")
        f_botones.pack(pady=20)
        tk.Button(f_botones, text="⬆ Subir archivos", font=("Arial", 10, "bold"), bg="#28a745", fg="white",
                  cursor="hand2", command=subir_archivos).pack(side="left", padx=5)
        if hasattr(os, "startfile"):
            tk.Button(f_botones, text="📂 Abrir carpeta", font=("Arial", 10, "bold"), bg="#6f42c1", fg="white",
                      cursor="hand2", command=lambda: os.startfile(self.carpeta_contexto)).pack(side="left", padx=5)
        tk.Button(f_botones, text="Cerrar", font=("Arial", 10, "bold"), bg="#5c6a79", fg="white", cursor="hand2",
                  command=win.destroy).pack(side="left", padx=5)

    def mostrar_memoria(self):
        est = self.memoria.estadisticas()
        win = tk.Toplevel(self.root)
        win.title("Memoria institucional de la IA")
        win.geometry(f"{min(1100, self.root.winfo_width() - 50)}x{min(620, self.root.winfo_height() - 50)}")
        win.configure(bg="#ffffff", padx=15, pady=15)

        tk.Label(win, text="MEMORIA INSTITUCIONAL DE LA IA", font=("Arial", 15, "bold"), bg="white",
                 fg="#1a252f").pack(anchor="w")
        tk.Label(win, text=f"{est['procesamientos']} procesamientos  ·  {est['evaluaciones']} evaluaciones  ·  "
                           f"{est['validaciones']} validadas por analistas ({est['correcciones']} corregidas)",
                 font=("Arial", 11), bg="white").pack(anchor="w")
        tk.Label(win, text="Doble clic en un registro para ver su sustento y validarlo. Las validaciones y "
                           "correcciones se usan como precedente en los siguientes procesamientos.",
                 font=("Arial", 9, "italic"), bg="white", fg="#5c6a79").pack(anchor="w", pady=(0, 8))

        marco = tk.Frame(win, bg="white")
        marco.pack(fill="both", expand=True)
        columnas = ("Fecha", "N° Exp", "Asunto", "Puntaje", "Estado", "Puesto", "Validación")
        tabla = ttk.Treeview(marco, columns=columnas, show="headings")
        for col, ancho, estirar in (("Fecha", 90, False), ("N° Exp", 70, False), ("Asunto", 380, True),
                                    ("Puntaje", 65, False), ("Estado", 200, False), ("Puesto", 60, False),
                                    ("Validación", 100, False)):
            tabla.column(col, width=ancho, stretch=estirar, anchor="w" if estirar else "center")
            tabla.heading(col, text=col)
        scroll = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
        tabla.configure(yscroll=scroll.set)
        tabla.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        registros = {}
        tag_por_estado = {estado: tag for tag, estado in ESTADOS.items()}
        for fila in self.memoria.historial():
            ev = dict(fila)
            ev.update(ref=str(fila["id"]), evaluacion_id=fila["id"], total=fila["total_expedientes"],
                      tag=tag_por_estado.get(fila["estado"], "normal"),
                      pesos=(fila["peso_legal"], fila["peso_estrategico"], fila["peso_tecnico"]),
                      parametros=json.loads(fila["parametros"] or "{}"),
                      precedentes_considerados=json.loads(fila["precedentes_usados"] or "[]"),
                      viable_legalmente=bool(fila["viable_legalmente"]),
                      requiere_subsanacion=bool(fila["requiere_subsanacion"]))
            for clave in ("nota_legal", "nota_estrategica", "nota_tecnica"): ev[clave] = int(ev[clave])
            registros[ev["ref"]] = ev
            tabla.insert("", "end", iid=ev["ref"], values=(fila["fecha_procesamiento"][:10], fila["nro_exp"],
                                                           (fila["asunto"] or "")[:90], fila["puntaje"], fila["estado"],
                                                           fila["puesto"], fila["decision"] or "—"))

        def abrir(event):
            seleccion = tabla.selection()
            if seleccion: self.mostrar_auditoria_ia(registros[seleccion[0]])

        tabla.bind("<Double-1>", abrir)
        tk.Button(win, text="Cerrar", font=("Arial", 10, "bold"), bg="#5c6a79", fg="white", cursor="hand2",
                  command=win.destroy).pack(pady=(10, 0))

    def exportar_excel(self):
        if self.df_exportar is not None:
            nombre = f"Plan_Trabajo_SIGA_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            self.df_exportar.to_excel(nombre, index=False)
            messagebox.showinfo("Exportado", f"El plan ha sido guardado como:\n{nombre}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SimuladorSIGAGerencial(root)
    root.mainloop()