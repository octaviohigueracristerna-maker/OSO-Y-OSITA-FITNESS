import io
import json
import math
from datetime import date
from xml.sax.saxutils import escape

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

# ---------------------------------------------------------
# Configuración de página (mobile-first)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Oso y Osita Fitness",
    page_icon="🐻",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {padding: 1.2rem 1rem 2rem 1rem;}
    .main-title {text-align:center; color:#FF4B4B; font-size:1.8rem;
                 font-weight:800; margin-bottom:0.2rem;}
    .sub-title {text-align:center; color:#888; font-size:0.95rem;
                margin-bottom:1rem;}
    .stButton>button, .stDownloadButton>button {
        width:100%; border-radius:10px; min-height:3em; font-weight:bold;}
    .badge {display:inline-block; padding:6px 12px; margin:4px 4px 4px 0;
            border-radius:20px; background:#FF4B4B22; border:1px solid #FF4B4B66;
            font-size:0.9rem;}
    .badge-off {opacity:0.35; filter:grayscale(1);}
    #MainMenu, footer {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 class='main-title'>🐻 Oso y Osita Fitness 🐾</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='sub-title'>Entrenamiento, nutrición y progreso en una sola app</p>",
    unsafe_allow_html=True,
)

st.session_state.setdefault("historial", [])

# ---------------------------------------------------------
# Datos
# ---------------------------------------------------------
ACTIVIDAD = {
    "Sedentario (poco o ningún ejercicio)": 1.2,
    "Ligeramente activo (1-3 días/semana)": 1.375,
    "Moderadamente activo (3-5 días/semana)": 1.55,
    "Muy activo (6-7 días/semana)": 1.725,
}
OBJ_MASA = "Aumento de masa muscular (hipertrofia)"
OBJ_DEF = "Definición muscular (pérdida de grasa)"

RUTINA_HIPERTROFIA = [
    {"dia": "Día 1: Pecho, hombro y tríceps", "ejercicios": [
        {"nombre": "Press de banca plano", "series_reps": "4 x 8-10",
         "tips": "Retracción escapular y pies firmes en el suelo."},
        {"nombre": "Press inclinado con mancuernas", "series_reps": "3 x 10",
         "tips": "Baja controlado hasta sentir estiramiento en el pecho."},
        {"nombre": "Press militar con mancuernas", "series_reps": "3 x 10",
         "tips": "Extiende sin bloquear por completo los codos."},
        {"nombre": "Fondos o extensión de tríceps", "series_reps": "3 x 12",
         "tips": "Codos cerrados y movimiento lento."},
    ]},
    {"dia": "Día 2: Espalda y bíceps", "ejercicios": [
        {"nombre": "Jalón al pecho", "series_reps": "4 x 10",
         "tips": "Lleva la barra al pecho apretando los dorsales."},
        {"nombre": "Remo con barra o mancuerna", "series_reps": "4 x 10",
         "tips": "Espalda neutra y codos hacia atrás."},
        {"nombre": "Curl de bíceps alterno", "series_reps": "3 x 12",
         "tips": "Sube controlado, sin impulso."},
    ]},
    {"dia": "Día 3: Pierna completa", "ejercicios": [
        {"nombre": "Sentadilla trasera libre", "series_reps": "4 x 8-10",
         "tips": "Espalda neutra y profundidad al menos hasta el paralelo."},
        {"nombre": "Peso muerto rumano", "series_reps": "3 x 10",
         "tips": "Cadera hacia atrás, barra pegada a las piernas."},
        {"nombre": "Prensa de pierna", "series_reps": "3 x 12",
         "tips": "No bloquees las rodillas al extender."},
        {"nombre": "Elevación de talones", "series_reps": "4 x 15",
         "tips": "Pausa de 1 segundo arriba."},
    ]},
]

RUTINA_DEFINICION = [
    {"dia": "Día 1: Torso completo + cardio", "ejercicios": [
        {"nombre": "Flexiones de pecho (push-ups)", "series_reps": "4 x 15",
         "tips": "Core firme y cuerpo alineado con la cadera."},
        {"nombre": "Remo horizontal con mancuernas", "series_reps": "4 x 12-15",
         "tips": "Codos hacia atrás sintiendo la espalda."},
        {"nombre": "Press de hombro con mancuernas", "series_reps": "3 x 15",
         "tips": "Movimiento controlado, sin arquear la espalda."},
        {"nombre": "Cardio moderado (caminata rápida o bici)", "series_reps": "20 min",
         "tips": "Ritmo en el que aún puedas hablar con frases cortas."},
    ]},
    {"dia": "Día 2: Pierna + core", "ejercicios": [
        {"nombre": "Zancadas alternadas (lunges)", "series_reps": "4 x 15 por pierna",
         "tips": "Espalda recta y rodilla trasera cerca del suelo."},
        {"nombre": "Sentadilla goblet", "series_reps": "4 x 15",
         "tips": "Pecho arriba y talones apoyados."},
        {"nombre": "Puente de glúteo", "series_reps": "3 x 15",
         "tips": "Aprieta glúteos arriba 1 segundo."},
        {"nombre": "Plancha abdominal", "series_reps": "4 x 45-60 seg",
         "tips": "Contrae glúteos y abdomen con fuerza."},
    ]},
    {"dia": "Día 3: Circuito full body", "ejercicios": [
        {"nombre": "Burpees", "series_reps": "4 x 10",
         "tips": "Ajusta el ritmo a tu nivel; sin saltar si lo necesitas."},
        {"nombre": "Peso muerto con mancuernas", "series_reps": "4 x 12",
         "tips": "Espalda neutra, cadera atrás."},
        {"nombre": "Mountain climbers", "series_reps": "4 x 30 seg",
         "tips": "Rodillas al pecho con ritmo constante."},
        {"nombre": "Cardio por intervalos", "series_reps": "15 min",
         "tips": "30 seg fuerte / 60 seg suave."},
    ]},
]

RUTINA_HIPERTROFIA_5 = [
    {"dia": "Día 1: Pecho y tríceps", "ejercicios": [
        {"nombre": "Press de banca plano", "series_reps": "4 x 8-10",
         "tips": "Retracción escapular y pies firmes en el suelo."},
        {"nombre": "Press inclinado con mancuernas", "series_reps": "4 x 10",
         "tips": "Baja controlado hasta sentir estiramiento en el pecho."},
        {"nombre": "Aperturas con mancuernas o cables", "series_reps": "3 x 12",
         "tips": "Codos ligeramente flexionados; no bajes más allá del estiramiento cómodo."},
        {"nombre": "Fondos en paralelas o press cerrado", "series_reps": "3 x 10",
         "tips": "Codos pegados al cuerpo; usa asistencia si hace falta."},
        {"nombre": "Extensión de tríceps en polea", "series_reps": "3 x 12",
         "tips": "Codos fijos a los costados y extensión completa."},
    ]},
    {"dia": "Día 2: Espalda y bíceps", "ejercicios": [
        {"nombre": "Dominadas asistidas o jalón al pecho", "series_reps": "4 x 8-10",
         "tips": "Inicia el movimiento con los dorsales, no con los brazos."},
        {"nombre": "Remo con barra", "series_reps": "4 x 10",
         "tips": "Espalda neutra, torso inclinado y codos hacia atrás."},
        {"nombre": "Remo en polea baja", "series_reps": "3 x 12",
         "tips": "Junta los omóplatos al final y regresa lento."},
        {"nombre": "Curl de bíceps con barra", "series_reps": "3 x 10",
         "tips": "Codos fijos y sin balanceo del torso."},
        {"nombre": "Curl martillo", "series_reps": "3 x 12",
         "tips": "Agarre neutro; trabaja también el antebrazo."},
    ]},
    {"dia": "Día 3: Cuádriceps y glúteos", "ejercicios": [
        {"nombre": "Sentadilla trasera libre", "series_reps": "4 x 8-10",
         "tips": "Espalda neutra y profundidad al menos hasta el paralelo."},
        {"nombre": "Prensa de pierna", "series_reps": "4 x 12",
         "tips": "No bloquees las rodillas al extender."},
        {"nombre": "Zancadas caminando", "series_reps": "3 x 12 por pierna",
         "tips": "Paso largo, torso erguido y rodilla alineada con el pie."},
        {"nombre": "Extensión de cuádriceps", "series_reps": "3 x 15",
         "tips": "Pausa de 1 segundo arriba."},
        {"nombre": "Hip thrust (empuje de cadera)", "series_reps": "4 x 10",
         "tips": "Mentón al pecho y aprieta los glúteos arriba."},
    ]},
    {"dia": "Día 4: Hombros, trapecio y brazos", "ejercicios": [
        {"nombre": "Press militar con barra", "series_reps": "4 x 8-10",
         "tips": "Core firme; no arquees la zona lumbar."},
        {"nombre": "Elevaciones laterales", "series_reps": "4 x 15",
         "tips": "Sube hasta la altura del hombro con control."},
        {"nombre": "Pájaros (deltoide posterior)", "series_reps": "3 x 15",
         "tips": "Torso inclinado y movimiento lento."},
        {"nombre": "Encogimientos de trapecio", "series_reps": "3 x 12",
         "tips": "Sube los hombros hacia las orejas sin rotarlos."},
        {"nombre": "Superserie: curl de bíceps + extensión de tríceps", "series_reps": "3 x 12",
         "tips": "Haz los dos ejercicios seguidos y descansa después."},
    ]},
    {"dia": "Día 5: Femorales, pantorrillas y core", "ejercicios": [
        {"nombre": "Peso muerto rumano", "series_reps": "4 x 8-10",
         "tips": "Cadera hacia atrás, barra pegada a las piernas."},
        {"nombre": "Curl femoral acostado", "series_reps": "4 x 12",
         "tips": "Baja lento (3 segundos) en cada repetición."},
        {"nombre": "Sentadilla búlgara", "series_reps": "3 x 10 por pierna",
         "tips": "Torso ligeramente inclinado; el peso va en la pierna delantera."},
        {"nombre": "Elevación de talones de pie", "series_reps": "4 x 15",
         "tips": "Recorrido completo y pausa arriba."},
        {"nombre": "Plancha abdominal", "series_reps": "3 x 45-60 seg",
         "tips": "Contrae glúteos y abdomen; cuerpo en línea recta."},
        {"nombre": "Elevación de piernas colgado o acostado", "series_reps": "3 x 12",
         "tips": "Sin balanceo; sube con el abdomen."},
    ]},
]

RUTINA_DEFINICION_5 = [
    {"dia": "Día 1: Pecho, tríceps y cardio", "ejercicios": [
        {"nombre": "Flexiones de pecho (push-ups)", "series_reps": "4 x 15",
         "tips": "Core firme y cuerpo alineado con la cadera."},
        {"nombre": "Press con mancuernas en banco plano", "series_reps": "4 x 12-15",
         "tips": "Control en la bajada; descansa 45-60 seg."},
        {"nombre": "Aperturas con mancuernas", "series_reps": "3 x 15",
         "tips": "Codos ligeramente flexionados."},
        {"nombre": "Fondos en banco (tríceps)", "series_reps": "3 x 15",
         "tips": "Espalda cerca del banco y codos hacia atrás."},
        {"nombre": "Caminata inclinada o bici", "series_reps": "20 min",
         "tips": "Ritmo en el que aún puedas hablar con frases cortas."},
    ]},
    {"dia": "Día 2: Espalda, bíceps y HIIT", "ejercicios": [
        {"nombre": "Jalón al pecho", "series_reps": "4 x 12-15",
         "tips": "Aprieta los dorsales abajo."},
        {"nombre": "Remo con mancuerna a una mano", "series_reps": "4 x 12",
         "tips": "Espalda paralela al suelo y codo pegado al cuerpo."},
        {"nombre": "Remo en polea baja", "series_reps": "3 x 15",
         "tips": "Junta los omóplatos al final del recorrido."},
        {"nombre": "Curl de bíceps alterno", "series_reps": "3 x 15",
         "tips": "Sin impulso; baja controlado."},
        {"nombre": "HIIT (30 seg fuerte / 30 seg suave)", "series_reps": "10 min",
         "tips": "Elige bici, cuerda o trote; el esfuerzo fuerte debe ser exigente."},
    ]},
    {"dia": "Día 3: Pierna completa", "ejercicios": [
        {"nombre": "Sentadilla goblet", "series_reps": "4 x 15",
         "tips": "Pecho arriba y talones apoyados."},
        {"nombre": "Zancadas alternadas (lunges)", "series_reps": "4 x 15 por pierna",
         "tips": "Espalda recta y rodilla trasera cerca del suelo."},
        {"nombre": "Peso muerto rumano con mancuernas", "series_reps": "4 x 12",
         "tips": "Espalda neutra, cadera atrás."},
        {"nombre": "Puente de glúteo", "series_reps": "3 x 15",
         "tips": "Aprieta glúteos arriba 1 segundo."},
        {"nombre": "Elevación de talones", "series_reps": "4 x 20",
         "tips": "Recorrido completo, sin rebotar."},
    ]},
    {"dia": "Día 4: Hombros, core y cardio", "ejercicios": [
        {"nombre": "Press de hombro con mancuernas", "series_reps": "4 x 12-15",
         "tips": "Movimiento controlado, sin arquear la espalda."},
        {"nombre": "Elevaciones laterales", "series_reps": "4 x 15",
         "tips": "Sube hasta la altura del hombro."},
        {"nombre": "Pájaros (deltoide posterior)", "series_reps": "3 x 15",
         "tips": "Torso inclinado y movimiento lento."},
        {"nombre": "Plancha abdominal", "series_reps": "4 x 45-60 seg",
         "tips": "Contrae glúteos y abdomen con fuerza."},
        {"nombre": "Crunch bicicleta", "series_reps": "3 x 20",
         "tips": "Gira el torso, no solo los codos."},
        {"nombre": "Cardio en bici o elíptica", "series_reps": "20 min",
         "tips": "Ritmo moderado y constante."},
    ]},
    {"dia": "Día 5: Circuito full body", "ejercicios": [
        {"nombre": "Burpees", "series_reps": "4 x 10",
         "tips": "Ajusta el ritmo a tu nivel; sin saltar si lo necesitas."},
        {"nombre": "Sentadilla con salto o sentadilla libre", "series_reps": "4 x 15",
         "tips": "Aterriza suave con las rodillas flexionadas."},
        {"nombre": "Remo con mancuernas", "series_reps": "4 x 12",
         "tips": "Espalda neutra y codos hacia atrás."},
        {"nombre": "Flexiones de pecho (push-ups)", "series_reps": "3 x 15",
         "tips": "Hazlas con rodillas apoyadas si pierdes la técnica."},
        {"nombre": "Mountain climbers", "series_reps": "4 x 30 seg",
         "tips": "Rodillas al pecho con ritmo constante."},
        {"nombre": "Cardio por intervalos", "series_reps": "15 min",
         "tips": "30 seg fuerte / 60 seg suave."},
    ]},
]

# Grupos musculares trabajados en cada día (clave = título del día)
GRUPOS_DIA = {
    "Día 1: Pecho, hombro y tríceps": ["Pecho", "Hombros", "Tríceps"],
    "Día 2: Espalda y bíceps": ["Espalda", "Bíceps"],
    "Día 3: Pierna completa": ["Cuádriceps", "Femorales", "Glúteos", "Pantorrillas"],
    "Día 1: Torso completo + cardio": ["Pecho", "Espalda", "Hombros"],
    "Día 2: Pierna + core": ["Cuádriceps", "Glúteos", "Core"],
    "Día 3: Circuito full body": ["Cuerpo completo"],
    "Día 1: Pecho y tríceps": ["Pecho", "Tríceps"],
    "Día 3: Cuádriceps y glúteos": ["Cuádriceps", "Glúteos"],
    "Día 4: Hombros, trapecio y brazos": ["Hombros", "Trapecio", "Bíceps", "Tríceps"],
    "Día 5: Femorales, pantorrillas y core": ["Femorales", "Glúteos", "Pantorrillas", "Core"],
    "Día 1: Pecho, tríceps y cardio": ["Pecho", "Tríceps"],
    "Día 2: Espalda, bíceps y HIIT": ["Espalda", "Bíceps"],
    "Día 4: Hombros, core y cardio": ["Hombros", "Core"],
    "Día 5: Circuito full body": ["Pecho", "Espalda", "Cuádriceps", "Core"],
}
GRUPOS_REQUERIDOS = {"Pecho", "Espalda", "Hombros", "Bíceps", "Tríceps",
                     "Cuádriceps", "Femorales", "Glúteos", "Pantorrillas", "Core"}


def elegir_rutina(objetivo, dias):
    if dias == 5:
        return RUTINA_HIPERTROFIA_5 if objetivo == OBJ_MASA else RUTINA_DEFINICION_5
    return RUTINA_HIPERTROFIA if objetivo == OBJ_MASA else RUTINA_DEFINICION


def agenda_semana(dias):
    if dias == 5:
        return "Sugerencia: entrena de lunes a viernes; sábado actividad ligera (caminata) y domingo descanso."
    return "Sugerencia: entrena lunes, miércoles y viernes; deja los otros días para descansar o caminar."


# Reparto del día: (comida, % de calorías)
COMIDAS = [("Desayuno", 0.25), ("Comida", 0.35), ("Snack", 0.15), ("Cena", 0.25)]
IDEAS = {
    OBJ_MASA: {
        "Desayuno": "Huevos al gusto con frijoles y tortillas de maíz, plátano y avena.",
        "Comida": "Pollo o carne asada, arroz, frijoles y ensalada; agua de limón sin azúcar.",
        "Snack": "Yogur griego con fruta y nueces, o sándwich de atún.",
        "Cena": "Pescado o pollo con papa o camote y verduras salteadas.",
    },
    OBJ_DEF: {
        "Desayuno": "Omelette de claras con espinaca, nopales y 1-2 tortillas de maíz.",
        "Comida": "Pescado a la plancha o pechuga, ensalada grande y media taza de arroz o frijol.",
        "Snack": "Fruta con yogur griego natural, o pepino con limón y un huevo cocido.",
        "Cena": "Caldo de pollo con verduras, o tostadas de ceviche de pescado con aguacate.",
    },
}

LOGROS = {
    "primer_peso": ("🥇", "Primer registro de peso"),
    "tres_dias": ("📅", "3 registros de peso"),
    "rutina": ("🔥", "Rutina completada al 100%"),
    "agua": ("💧", "Meta de agua del día"),
}


# ---------------------------------------------------------
# Cálculos
# ---------------------------------------------------------
def categoria_imc(imc):
    if imc < 18.5:
        return "Bajo peso", "off"
    if imc < 25:
        return "Peso saludable", "normal"
    if imc < 30:
        return "Sobrepeso", "inverse"
    return "Obesidad", "inverse"


def calcular(d):
    peso, estatura, edad = d["peso"], d["estatura"], d["edad"]
    imc = peso / ((estatura / 100) ** 2)
    cat, color = categoria_imc(imc)

    # Mifflin-St Jeor
    tmb = 10 * peso + 6.25 * estatura - 5 * edad + (5 if d["sexo"] == "Masculino" else -161)
    tdee = tmb * ACTIVIDAD[d["actividad"]]

    if d["objetivo"] == OBJ_MASA:
        calorias, prot, grasa = tdee + 350, peso * 2.0, peso * 1.0
        foco = "Sobrecarga progresiva: 3-4 series de 8-12 reps. Descanso: 90 seg."
    else:
        calorias, prot, grasa = tdee - 450, peso * 2.2, peso * 0.8
        foco = "Intensidad alta con descansos cortos (45-60 seg): 3-4 series de 12-15 reps."

    # Piso de seguridad calórico
    minimo = 1500 if d["sexo"] == "Masculino" else 1200
    ajustado = calorias < minimo
    calorias = max(calorias, minimo)

    carbos = max(0.0, (calorias - (prot * 4 + grasa * 9)) / 4)
    return {
        **d, "imc": imc, "cat_imc": cat, "color_imc": color, "tdee": tdee,
        "calorias": calorias, "prot": prot, "carbos": carbos, "grasa": grasa,
        "agua": peso * 35 / 1000, "foco": foco, "ajustado": ajustado,
        "rutina": elegir_rutina(d["objetivo"], d.get("dias", 3)),
    }


def plan_comidas(r):
    """Reparte calorías y macros del día entre las comidas."""
    filas = []
    for nombre, pct in COMIDAS:
        filas.append({
            "comida": nombre,
            "kcal": int(r["calorias"] * pct),
            "prot": int(r["prot"] * pct),
            "carbos": int(r["carbos"] * pct),
            "grasa": int(r["grasa"] * pct),
            "ideas": IDEAS[r["objetivo"]][nombre],
        })
    return filas


def vasos_meta(r):
    return max(1, math.ceil(r["agua"] * 1000 / 250))


def un_rm(peso, reps):
    """Fórmula de Epley."""
    return float(peso) if reps <= 1 else peso * (1 + reps / 30)


# ---------------------------------------------------------
# Historial de peso (guardar / cargar)
# ---------------------------------------------------------
def registrar_peso(nombre, peso):
    hoy = date.today().isoformat()
    h = [x for x in st.session_state["historial"]
         if not (x["nombre"] == nombre and x["fecha"] == hoy)]
    h.append({"nombre": nombre, "fecha": hoy, "peso": round(float(peso), 1)})
    st.session_state["historial"] = sorted(h, key=lambda x: (x["fecha"], x["nombre"]))


def importar_historial(contenido):
    """Valida un JSON exportado y lo mezcla con el historial actual. Devuelve cuántos registros entraron."""
    data = json.loads(contenido)
    items = data.get("historial", []) if isinstance(data, dict) else []
    validos = {}
    for x in items:
        try:
            nombre = str(x["nombre"])[:30]
            fecha = date.fromisoformat(str(x["fecha"])).isoformat()
            peso = float(x["peso"])
        except (KeyError, TypeError, ValueError):
            continue
        if 20 <= peso <= 400:
            validos[(nombre, fecha)] = {"nombre": nombre, "fecha": fecha, "peso": round(peso, 1)}
    actuales = {(x["nombre"], x["fecha"]): x for x in st.session_state["historial"]}
    actuales.update(validos)
    st.session_state["historial"] = sorted(actuales.values(), key=lambda x: (x["fecha"], x["nombre"]))
    return len(validos)


def logros_de(nombre, r):
    n_reg = sum(1 for x in st.session_state["historial"] if x["nombre"] == nombre)
    vasos = st.session_state.get(f"vasos_{nombre}", 0)
    return {
        "primer_peso": n_reg >= 1,
        "tres_dias": n_reg >= 3,
        "rutina": bool(st.session_state.get(f"celebrado_{nombre}", False)),
        "agua": vasos >= vasos_meta(r),
    }


# ---------------------------------------------------------
# PDF
# ---------------------------------------------------------
def generar_pdf(resultados):
    """Genera el PDF. Sin emojis: la fuente Helvetica los dibuja como cuadros negros."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36,
                            leftMargin=36, topMargin=36, bottomMargin=36,
                            title="Plan Oso y Osita Fitness")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Heading1"], fontSize=20,
                           textColor=colors.HexColor("#FF4B4B"), alignment=1, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14,
                        textColor=colors.HexColor("#2C3E50"), spaceBefore=10, spaceAfter=6)
    normal = ParagraphStyle("N", parent=styles["Normal"], fontSize=10, leading=14)
    small = ParagraphStyle("S", parent=normal, fontSize=8, textColor=colors.grey)
    mini = ParagraphStyle("M", parent=normal, fontSize=9, leading=12)
    bold = ParagraphStyle("B", parent=normal, fontName="Helvetica-Bold")
    dia_style = ParagraphStyle("D", parent=normal, fontName="Helvetica-Bold", fontSize=11,
                               textColor=colors.HexColor("#FF4B4B"), spaceBefore=8, spaceAfter=3)

    def P(txt, st_=normal):
        return Paragraph(escape(str(txt)), st_)

    def estilo_tabla(cabecera=True):
        base = [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]
        if cabecera:
            base.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9ECEF")))
        return TableStyle(base)

    story = []
    for i, r in enumerate(resultados):
        if i:
            story.append(PageBreak())
        story.append(Paragraph("Oso y Osita Fitness - Plan de entrenamiento", title))
        story.append(P(f"{r['nombre']} - plan de {r['dias']} días por semana - generado el {date.today():%d/%m/%Y}", small))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Diagnóstico y nutrición", h2))
        datos = [
            [P("Objetivo:", bold), P(r["objetivo"]), P("I.M.C.:", bold), P(f"{r['imc']:.1f} ({r['cat_imc']})")],
            [P("Meta calórica:", bold), P(f"{int(r['calorias'])} kcal"), P("Agua diaria:", bold), P(f"{r['agua']:.1f} L")],
            [P("Proteínas:", bold), P(f"{int(r['prot'])} g"), P("Carbohidratos:", bold), P(f"{int(r['carbos'])} g")],
            [P("Grasas:", bold), P(f"{int(r['grasa'])} g"), P("Estrategia:", bold), P(r["foco"])],
        ]
        t = Table(datos, colWidths=[85, 165, 85, 185])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

        story.append(Paragraph("Plan de comidas del día", h2))
        filas = [[P("Comida", bold), P("kcal", bold), P("P / C / G (g)", bold), P("Ideas", bold)]]
        for c in plan_comidas(r):
            filas.append([P(c["comida"], bold), P(c["kcal"]),
                          P(f"{c['prot']} / {c['carbos']} / {c['grasa']}"), P(c["ideas"], mini)])
        tc = Table(filas, colWidths=[65, 50, 90, 315], repeatRows=1)
        tc.setStyle(estilo_tabla())
        story.append(tc)
        story.append(Spacer(1, 10))

        story.append(Paragraph("Rutina de entrenamiento", h2))
        for dia in r["rutina"]:
            story.append(P(dia["dia"], dia_style))
            filas = [[P("Ejercicio", bold), P("Series x reps", bold), P("Técnica / recomendación", bold)]]
            for ej in dia["ejercicios"]:
                filas.append([P(ej["nombre"], bold), P(ej["series_reps"]), P(ej["tips"])])
            te = Table(filas, colWidths=[160, 90, 270], repeatRows=1)
            te.setStyle(estilo_tabla())
            story.append(te)
        story.append(Spacer(1, 12))
        story.append(P("Estimaciones generales; no sustituyen la valoración de un médico o "
                       "nutriólogo. Consulta a un profesional antes de iniciar un plan nuevo.", small))
    doc.build(story)
    return buffer.getvalue()


# ---------------------------------------------------------
# Componentes de UI
# ---------------------------------------------------------
def formulario(prefijo, nombre, sexo_def, peso_def, est_def):
    c1, c2 = st.columns(2)
    with c1:
        edad = st.number_input("Edad (años)", 12, 90, 25, 1, key=f"{prefijo}_edad")
        peso = st.number_input("Peso (kg)", 30.0, 250.0, peso_def, 0.5, key=f"{prefijo}_peso")
    with c2:
        estatura = st.number_input("Estatura (cm)", 120.0, 230.0, est_def, 1.0, key=f"{prefijo}_est")
        sexo = st.selectbox("Sexo biológico", ["Masculino", "Femenino"],
                            index=0 if sexo_def == "Masculino" else 1, key=f"{prefijo}_sexo")
    actividad = st.selectbox("🔥 Nivel de actividad física", list(ACTIVIDAD), key=f"{prefijo}_act")
    objetivo = st.radio("🎯 Objetivo principal", [OBJ_MASA, OBJ_DEF], key=f"{prefijo}_obj")
    dias = st.radio("📅 Días de entrenamiento por semana", [3, 5], horizontal=True,
                    format_func=lambda x: f"{x} días", key=f"{prefijo}_dias")
    return {"nombre": nombre, "edad": edad, "peso": peso, "estatura": estatura,
            "sexo": sexo, "actividad": actividad, "objetivo": objetivo, "dias": dias}


def mostrar_resultado(r):
    st.markdown(f"#### {r['nombre']}")
    m1, m2, m3 = st.columns(3)
    m1.metric("I.M.C.", f"{r['imc']:.1f}", delta=r["cat_imc"], delta_color=r["color_imc"])
    m2.metric("Mantenimiento", f"{int(r['tdee'])} kcal")
    m3.metric("Meta diaria", f"{int(r['calorias'])} kcal")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Proteína", f"{int(r['prot'])} g")
    c2.metric("Carbos", f"{int(r['carbos'])} g")
    c3.metric("Grasas", f"{int(r['grasa'])} g")
    c4.metric("Agua", f"{r['agua']:.1f} L")
    st.info(f"💡 **Estrategia:** {r['foco']}")
    if r["ajustado"]:
        st.warning("Las calorías se ajustaron a un mínimo de seguridad. "
                   "Consulta a un profesional si buscas bajar de peso más rápido.")


def limpiar_checklist():
    """Reinicia el checklist cambiando de 'generación' (las claves nuevas empiezan sin marcar)."""
    st.session_state["chk_gen"] = st.session_state.get("chk_gen", 0) + 1
    for k in list(st.session_state.keys()):
        if k.startswith("celebrado_"):
            st.session_state[k] = False


def sumar_vaso(nombre):
    st.session_state[f"vasos_{nombre}"] = st.session_state.get(f"vasos_{nombre}", 0) + 1


def quitar_vaso(nombre):
    st.session_state[f"vasos_{nombre}"] = max(0, st.session_state.get(f"vasos_{nombre}", 0) - 1)


def fijar_timer(s):
    st.session_state["segundos_timer"] = s


TIMER_HTML = """
<div style="text-align:center;font-family:sans-serif;padding:20px;background:#f1f3f5;border-radius:12px;">
  <h1 id="d" style="font-size:3.5rem;color:#FF4B4B;margin:0;">__S__</h1>
  <p style="color:#666;font-size:.9rem;">Segundos de descanso restantes</p>
  <button onclick="start()" style="background:#28a745;color:#fff;border:none;padding:12px 24px;font-size:1.1rem;font-weight:bold;border-radius:8px;margin-right:8px;">▶️ Iniciar</button>
  <button onclick="reset()" style="background:#dc3545;color:#fff;border:none;padding:12px 24px;font-size:1.1rem;font-weight:bold;border-radius:8px;">🔄 Reiniciar</button>
</div>
<script>
const TOTAL = __S__;
let id = null, ctx = null;
function beep() {
  try {
    ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.connect(g); g.connect(ctx.destination);
    o.frequency.value = 880; g.gain.value = 0.3;
    o.start(); o.stop(ctx.currentTime + 0.6);
  } catch (e) {}
  try { if (navigator.vibrate) navigator.vibrate([300, 150, 300]); } catch (e) {}
}
function start() {
  clearInterval(id);
  try { ctx = ctx || new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {}
  const d = document.getElementById('d');
  const fin = Date.now() + TOTAL * 1000;
  d.textContent = TOTAL;
  id = setInterval(() => {
    const left = Math.ceil((fin - Date.now()) / 1000);
    if (left <= 0) { clearInterval(id); d.textContent = '🔔 ¡TIEMPO!'; beep(); }
    else d.textContent = left;
  }, 250);
}
function reset() { clearInterval(id); document.getElementById('d').textContent = TOTAL; }
</script>
"""


def mostrar_timer(segundos):
    html = TIMER_HTML.replace("__S__", str(segundos))
    if hasattr(st, "iframe"):  # Streamlit nuevo (components.v1.html está obsoleto)
        st.iframe(html, height=240)
    else:  # Streamlit antiguo
        import streamlit.components.v1 as components
        components.html(html, height=240)


# ---------------------------------------------------------
# Pestañas
# ---------------------------------------------------------
tab_perfil, tab_rutina, tab_comidas, tab_progreso, tab_tools = st.tabs(
    ["📋 Perfil", "🏋️ Rutina", "🍽️ Comidas", "📈 Progreso", "🧰 Herramientas"]
)

# ---- Perfil ----
with tab_perfil:
    modo = st.radio(
        "Perfil activo:",
        ["🐻 Modo Oso", "🐻‍❄️ Modo Osita", "👩‍❤️‍👨 Entrenamiento en pareja"],
        horizontal=True,
    )

    if modo == "🐻 Modo Oso":
        datos = [formulario("oso", "Oso", "Masculino", 75.0, 175.0)]
    elif modo == "🐻‍❄️ Modo Osita":
        datos = [formulario("osita", "Osita", "Femenino", 60.0, 162.0)]
    else:
        t_oso, t_osita = st.tabs(["🐻 Oso", "🐻‍❄️ Osita"])
        with t_oso:
            d_oso = formulario("oso", "Oso", "Masculino", 75.0, 175.0)
        with t_osita:
            d_osita = formulario("osita", "Osita", "Femenino", 60.0, 162.0)
        datos = [d_oso, d_osita]

    if st.button("🚀 Calcular plan", use_container_width=True):
        limpiar_checklist()
        st.session_state["resultados"] = [calcular(d) for d in datos]
        st.success("✅ Plan calculado. Revisa Rutina, Comidas y Progreso.")

    if st.session_state.get("resultados"):
        st.divider()
        st.subheader("📊 Resultados")
        for r in st.session_state["resultados"]:
            mostrar_resultado(r)

resultados = st.session_state.get("resultados")
AVISO = "👉 Primero ingresa tus datos en **'📋 Perfil'** y presiona 'Calcular plan'."

# ---- Rutina (con checklist) ----
with tab_rutina:
    st.subheader("🏋️ Plan de entrenamiento")
    if not resultados:
        st.warning(AVISO)
    else:
        for r in resultados:
            nombre = r["nombre"]
            st.markdown(f"### {nombre} · plan de {r['dias']} días")
            st.caption(agenda_semana(r["dias"]))
            barra = st.empty()
            hechos = total = 0
            for di, dia in enumerate(r["rutina"]):
                with st.expander(f"📌 {dia['dia']}", expanded=len(resultados) == 1):
                    grupos = GRUPOS_DIA.get(dia["dia"])
                    if grupos:
                        st.caption("🎯 Grupos musculares: " + ", ".join(grupos))
                    for ei, ej in enumerate(dia["ejercicios"]):
                        marcado = st.checkbox(f"**{ej['nombre']}** · {ej['series_reps']}",
                                              key=f"chk_{nombre}_{st.session_state.get('chk_gen', 0)}_{di}_{ei}")
                        st.caption(f"💡 {ej['tips']}")
                        total += 1
                        hechos += int(marcado)
            frac = hechos / total if total else 0.0
            barra.progress(frac, text=f"Progreso de {nombre}: {hechos}/{total} ejercicios")
            if total and hechos == total:
                if not st.session_state.get(f"celebrado_{nombre}"):
                    st.session_state[f"celebrado_{nombre}"] = True
                    st.balloons()
                st.success(f"🏆 ¡{nombre} completó toda la rutina!")
            else:
                st.session_state[f"celebrado_{nombre}"] = False
        st.button("↺ Reiniciar checklist", on_click=limpiar_checklist, key="reset_chk")
        try:
            st.download_button(
                "📄 Descargar plan en PDF",
                data=generar_pdf(resultados),
                file_name="Plan_Oso_y_Osita_Fitness.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:  # el PDF nunca debe tumbar la app
            st.error(f"No se pudo generar el PDF: {e}")

# ---- Comidas ----
with tab_comidas:
    st.subheader("🍽️ Plan de comidas del día")
    if not resultados:
        st.warning(AVISO)
    else:
        for r in resultados:
            st.markdown(f"### {r['nombre']} · {int(r['calorias'])} kcal")
            for c in plan_comidas(r):
                with st.expander(f"{c['comida']} · {c['kcal']} kcal", expanded=False):
                    a, b, d = st.columns(3)
                    a.metric("Proteína", f"{c['prot']} g")
                    b.metric("Carbos", f"{c['carbos']} g")
                    d.metric("Grasas", f"{c['grasa']} g")
                    st.write(f"🥗 {c['ideas']}")
        st.caption("Ideas de referencia con comida local. Ajusta porciones para acercarte a los gramos indicados.")

# ---- Progreso ----
with tab_progreso:
    st.subheader("📈 Mi progreso")
    if not resultados:
        st.warning(AVISO)
    else:
        for r in resultados:
            nombre = r["nombre"]
            st.markdown(f"### {nombre}")
            peso_hoy = st.number_input(f"Peso de hoy de {nombre} (kg)", 30.0, 250.0,
                                       float(r["peso"]), 0.1, key=f"peso_hoy_{nombre}")
            if st.button(f"⚖️ Registrar peso de {nombre}", key=f"reg_{nombre}"):
                registrar_peso(nombre, peso_hoy)
                st.success("Peso registrado.")

            propios = [x for x in st.session_state["historial"] if x["nombre"] == nombre]
            if len(propios) >= 2:
                cambio = propios[-1]["peso"] - propios[0]["peso"]
                st.metric("Cambio desde el primer registro", f"{propios[-1]['peso']:.1f} kg",
                          delta=f"{cambio:+.1f} kg", delta_color="off")
            elif propios:
                st.caption("Registra otro día para ver tu tendencia.")

            # Agua
            meta = vasos_meta(r)
            vasos = st.session_state.get(f"vasos_{nombre}", 0)
            st.progress(min(vasos / meta, 1.0), text=f"💧 Agua: {vasos}/{meta} vasos (250 ml)")
            w1, w2 = st.columns(2)
            w1.button("➕ Vaso", key=f"mas_{nombre}", on_click=sumar_vaso, args=(nombre,))
            w2.button("➖ Quitar", key=f"menos_{nombre}", on_click=quitar_vaso, args=(nombre,))

            # Logros
            ganados = logros_de(nombre, r)
            html = "".join(
                f"<span class='badge{'' if ganados[k] else ' badge-off'}'>{ico} {txt}</span>"
                for k, (ico, txt) in LOGROS.items()
            )
            st.markdown(html, unsafe_allow_html=True)
            st.divider()

        if st.session_state["historial"]:
            df = pd.DataFrame(st.session_state["historial"])
            df["fecha"] = pd.to_datetime(df["fecha"])
            tabla = df.pivot_table(index="fecha", columns="nombre", values="peso", aggfunc="last")
            st.line_chart(tabla)

        st.markdown("#### 💾 Guardar / cargar historial")
        st.caption("La app no guarda datos al cerrarse. Descarga tu historial y cárgalo la próxima vez.")
        st.download_button(
            "⬇️ Descargar historial",
            data=json.dumps({"historial": st.session_state["historial"]}, ensure_ascii=False, indent=2),
            file_name="historial_oso_osita.json",
            mime="application/json",
            use_container_width=True,
        )
        subido = st.file_uploader("⬆️ Cargar historial", type=["json"], key="subir_hist")
        if subido is not None:
            marca = f"{subido.name}-{subido.size}"
            if st.session_state.get("_ultimo_import") != marca:
                try:
                    n = importar_historial(subido.getvalue().decode("utf-8"))
                    st.session_state["_ultimo_import"] = marca
                    st.success(f"Se cargaron {n} registros.")
                    st.rerun()
                except Exception:
                    st.error("El archivo no es un historial válido.")

# ---- Herramientas ----
with tab_tools:
    st.subheader("⏱️ Temporizador de descanso")
    st.session_state.setdefault("segundos_timer", 60)
    cols = st.columns(4)
    for col, s in zip(cols, (30, 60, 90, 120)):
        col.button(f"{s}s", key=f"btn_{s}", on_click=fijar_timer, args=(s,))
    segundos = int(st.number_input("O ingresa los segundos:", 5, 300, step=5, key="segundos_timer"))
    mostrar_timer(segundos)

    st.divider()
    st.subheader("🧮 Calculadora de 1RM")
    st.caption("Estima tu repetición máxima con la fórmula de Epley (usa series de 1 a 12 reps).")
    k1, k2 = st.columns(2)
    peso_lev = k1.number_input("Peso levantado (kg)", 1.0, 500.0, 60.0, 2.5, key="rm_peso")
    reps_lev = k2.number_input("Repeticiones", 1, 12, 8, 1, key="rm_reps")
    rm = un_rm(peso_lev, int(reps_lev))
    st.metric("1RM estimado", f"{rm:.1f} kg")
    st.table([
        {"% del 1RM": f"{p}%", "Peso (kg)": round(rm * p / 100 / 2.5) * 2.5, "Reps aprox.": rp}
        for p, rp in [(95, 2), (90, 4), (85, 6), (80, 8), (75, 10), (70, 12), (60, 15)]
    ])
