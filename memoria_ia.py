"""Memoria institucional del motor de IA (SQLite).

Guarda cada procesamiento, la evaluación que la IA hizo de cada expediente (parámetros
captados, notas, puntaje, puesto y sustentos) y las validaciones o correcciones de los
analistas. En procesamientos futuros se recuperan los casos similares como precedentes
para que la IA mantenga criterios coherentes en el tiempo.
"""
import datetime
import json
import re
import sqlite3
import unicodedata
from contextlib import closing

ESQUEMA = """
CREATE TABLE IF NOT EXISTS procesamientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    archivo TEXT,
    modelo TEXT,
    peso_legal REAL,
    peso_estrategico REAL,
    peso_tecnico REAL,
    documentos_contexto TEXT,
    total_expedientes INTEGER,
    tokens_entrada INTEGER,
    tokens_salida INTEGER,
    tokens_cache_leidos INTEGER,
    tokens_cache_escritos INTEGER
);

CREATE TABLE IF NOT EXISTS evaluaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    procesamiento_id INTEGER NOT NULL REFERENCES procesamientos(id),
    nro_exp TEXT NOT NULL,
    dependencia TEXT,
    asunto TEXT,
    parametros TEXT,
    nota_legal REAL,
    nota_estrategica REAL,
    nota_tecnica REAL,
    viable_legalmente INTEGER,
    requiere_subsanacion INTEGER,
    base_normativa TEXT,
    objetivo_pei TEXT,
    sustento_legal TEXT,
    sustento_estrategico TEXT,
    sustento_tecnico TEXT,
    alineamiento_ley TEXT,
    alineamiento_pei TEXT,
    puntaje REAL,
    estado TEXT,
    puesto INTEGER,
    sustento_puntaje TEXT,
    sustento_puesto TEXT,
    precedentes_usados TEXT
);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_nro_exp ON evaluaciones(nro_exp);

CREATE TABLE IF NOT EXISTS validaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluacion_id INTEGER NOT NULL REFERENCES evaluaciones(id),
    fecha TEXT NOT NULL,
    decision TEXT NOT NULL,
    puntaje_corregido REAL,
    estado_corregido TEXT,
    comentario TEXT
);
"""

# Columnas comunes para leer una evaluación junto con su procesamiento y su última validación.
SELECT_EVALUACION = """
SELECT e.*, p.fecha AS fecha_procesamiento, p.total_expedientes, p.modelo,
       p.peso_legal, p.peso_estrategico, p.peso_tecnico,
       v.decision, v.puntaje_corregido, v.estado_corregido, v.comentario, v.fecha AS fecha_validacion
FROM {origen}
JOIN procesamientos p ON p.id = e.procesamiento_id
LEFT JOIN validaciones v ON v.id = (SELECT MAX(id) FROM validaciones WHERE evaluacion_id = e.id)
"""

PALABRAS_VACIAS = {
    "para", "como", "pero", "este", "esta", "estos", "estas", "entre", "cuando", "sobre", "tambien",
    "hasta", "donde", "desde", "todo", "todos", "durante", "contra", "otros", "otras", "ante", "ellos",
    "esto", "antes", "algunos", "unos", "otro", "otra", "tanto", "mucho", "quienes", "nada", "cual",
    "solicita", "solicitud", "solicitan", "remite", "remiten", "expediente", "oficio", "senor", "senora",
    "universidad", "nacional", "mayor", "marcos", "unmsm", "atencion", "respecto", "mediante", "favor",
}


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


class MemoriaIA:
    def __init__(self, ruta_db):
        self.ruta_db = ruta_db
        with closing(self._conectar()) as con, con:
            con.executescript(ESQUEMA)
            try:
                con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS evaluaciones_fts "
                            "USING fts5(texto, tokenize='unicode61 remove_diacritics 2')")
                self.fts = True
            except sqlite3.OperationalError:
                # SQLite sin FTS5: solo se recuperan precedentes del mismo expediente.
                self.fts = False

    def _conectar(self):
        # Una conexión por operación: el motor consulta la memoria desde varios hilos.
        con = sqlite3.connect(self.ruta_db)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    # ------------------------------------------
    # ESCRITURA
    # ------------------------------------------
    def guardar_procesamiento(self, meta, evaluaciones):
        """Registra un procesamiento completo. Devuelve (procesamiento_id, {ref: evaluacion_id})."""
        ids = {}
        with closing(self._conectar()) as con, con:
            cur = con.execute(
                "INSERT INTO procesamientos (fecha, archivo, modelo, peso_legal, peso_estrategico, peso_tecnico, "
                "documentos_contexto, total_expedientes, tokens_entrada, tokens_salida, tokens_cache_leidos, "
                "tokens_cache_escritos) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (datetime.datetime.now().isoformat(timespec="seconds"), meta["archivo"], meta["modelo"],
                 meta["pesos"][0], meta["pesos"][1], meta["pesos"][2],
                 json.dumps(meta["documentos"], ensure_ascii=False), len(evaluaciones),
                 meta["uso"]["entrada"], meta["uso"]["salida"], meta["uso"]["cache_leidos"],
                 meta["uso"]["cache_escritos"]))
            proc_id = cur.lastrowid
            for ev in evaluaciones:
                cur = con.execute(
                    "INSERT INTO evaluaciones (procesamiento_id, nro_exp, dependencia, asunto, parametros, "
                    "nota_legal, nota_estrategica, nota_tecnica, viable_legalmente, requiere_subsanacion, "
                    "base_normativa, objetivo_pei, sustento_legal, sustento_estrategico, sustento_tecnico, "
                    "alineamiento_ley, alineamiento_pei, puntaje, estado, puesto, sustento_puntaje, "
                    "sustento_puesto, precedentes_usados) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (proc_id, ev["nro_exp"], ev["dependencia"], ev["asunto"],
                     json.dumps(ev["parametros"], ensure_ascii=False),
                     ev["nota_legal"], ev["nota_estrategica"], ev["nota_tecnica"],
                     int(ev["viable_legalmente"]), int(ev["requiere_subsanacion"]),
                     ev["base_normativa"], ev["objetivo_pei"],
                     ev["sustento_legal"], ev["sustento_estrategico"], ev["sustento_tecnico"],
                     ev["alineamiento_ley"], ev["alineamiento_pei"],
                     ev["puntaje"], ev["estado"], ev["puesto"], ev["sustento_puntaje"], ev["sustento_puesto"],
                     json.dumps(ev["precedentes_considerados"])))
                ids[ev["ref"]] = cur.lastrowid
                if self.fts:
                    texto = " ".join([ev["asunto"], ev["dependencia"], ev["objetivo_pei"],
                                      *[str(v) for v in ev["parametros"].values()]])
                    con.execute("INSERT INTO evaluaciones_fts (rowid, texto) VALUES (?, ?)",
                                (cur.lastrowid, texto))
        return proc_id, ids

    def guardar_validacion(self, evaluacion_id, decision, puntaje_corregido=None, estado_corregido=None,
                           comentario=""):
        with closing(self._conectar()) as con, con:
            con.execute(
                "INSERT INTO validaciones (evaluacion_id, fecha, decision, puntaje_corregido, estado_corregido, "
                "comentario) VALUES (?, ?, ?, ?, ?, ?)",
                (evaluacion_id, datetime.datetime.now().isoformat(timespec="seconds"), decision,
                 puntaje_corregido, estado_corregido, comentario))

    # ------------------------------------------
    # LECTURA
    # ------------------------------------------
    def _consulta_fts(self, texto):
        palabras = []
        for p in re.findall(r"[a-z0-9]{4,}", _normalizar(texto)):
            if p not in PALABRAS_VACIAS and p not in palabras:
                palabras.append(p)
        return " OR ".join(f'"{p}"' for p in palabras[:15])

    def buscar_precedentes(self, expedientes, por_expediente=3, maximo=25):
        """Precedentes para un lote: evaluaciones previas del mismo N° de expediente
        (reingresos tras subsanación) y casos con asunto similar (búsqueda de texto completo)."""
        encontrados = {}
        sql_mismo = SELECT_EVALUACION.format(origen="evaluaciones e") + " WHERE e.nro_exp = ? ORDER BY e.id DESC LIMIT 2"
        sql_similar = (SELECT_EVALUACION.format(
            origen="evaluaciones_fts JOIN evaluaciones e ON e.id = evaluaciones_fts.rowid")
                       + " WHERE evaluaciones_fts MATCH ? ORDER BY bm25(evaluaciones_fts) LIMIT ?")
        with closing(self._conectar()) as con:
            for exp in expedientes:
                filas = con.execute(sql_mismo, (exp["nro_exp"],)).fetchall()
                consulta = self._consulta_fts(exp["asunto"])
                if self.fts and consulta:
                    filas += con.execute(sql_similar, (consulta, por_expediente)).fetchall()
                for f in filas:
                    encontrados.setdefault(f["id"], dict(f))
        # Las correcciones humanas primero: son el criterio institucional de referencia.
        precedentes = sorted(encontrados.values(), key=lambda p: (p["decision"] is None, -p["id"]))
        return precedentes[:maximo]

    def obtener_evaluaciones(self, ids):
        if not ids:
            return []
        marcas = ",".join("?" * len(ids))
        with closing(self._conectar()) as con:
            filas = con.execute(SELECT_EVALUACION.format(origen="evaluaciones e")
                                + f" WHERE e.id IN ({marcas}) ORDER BY e.id", list(ids)).fetchall()
        return [dict(f) for f in filas]

    def historial(self, limite=200):
        with closing(self._conectar()) as con:
            filas = con.execute(SELECT_EVALUACION.format(origen="evaluaciones e")
                                + " ORDER BY e.id DESC LIMIT ?", (limite,)).fetchall()
        return [dict(f) for f in filas]

    def estadisticas(self):
        with closing(self._conectar()) as con:
            return {
                "procesamientos": con.execute("SELECT COUNT(*) FROM procesamientos").fetchone()[0],
                "evaluaciones": con.execute("SELECT COUNT(*) FROM evaluaciones").fetchone()[0],
                "validaciones": con.execute("SELECT COUNT(DISTINCT evaluacion_id) FROM validaciones").fetchone()[0],
                "correcciones": con.execute(
                    "SELECT COUNT(DISTINCT evaluacion_id) FROM validaciones WHERE decision = 'CORREGIDO'").fetchone()[0],
            }
