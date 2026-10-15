import base64
import io
import json
import math
from datetime import date, datetime
from functools import lru_cache
from urllib.parse import quote_plus
from xml.sax.saxutils import escape

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

# ---------------------------------------------------------
# Fondo de gimnasio: oso en press de banca y osa en sentadilla
# ---------------------------------------------------------
_PEL, _OUT, _HOC, _NAR = "#9C6B3E", "#4A2E17", "#E8C9A0", "#2B1B12"
_PLACA, _PLACA2, _ROJO, _ROSA = "#5A6B7C", "#3B4756", "#FF4B4B", "#FF5C8A"


def _miembro(pts, ancho, color=_PEL):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    return (f'<path d="{d}" fill="none" stroke="{_OUT}" stroke-width="{ancho + 8}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{ancho}" stroke-linecap="round" stroke-linejoin="round"/>')


def _cabeza_oso(cx, cy, r, frente=True, osa=False, banda=False):
    """Cabeza de oso. frente=True: mira al espectador; False: de perfil mirando a la derecha."""
    o = []
    for dx, dy in ((-0.72, -0.78), (0.72, -0.78)) if frente else ((-0.55, -0.85), (0.25, -0.95)):
        ex, ey = cx + dx * r, cy + dy * r
        o.append(f'<circle cx="{ex:.0f}" cy="{ey:.0f}" r="{r * .38:.0f}" fill="{_PEL}" stroke="{_OUT}" stroke-width="5"/>'
                 f'<circle cx="{ex:.0f}" cy="{ey:.0f}" r="{r * .19:.0f}" fill="#E7A6A0"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{_PEL}" stroke="{_OUT}" stroke-width="6"/>')
    if banda:
        o.append(f'<path d="M{cx - r * .95:.0f},{cy - r * .38:.0f} Q{cx},{cy - r * .82:.0f} {cx + r * .95:.0f},{cy - r * .38:.0f}" '
                 f'fill="none" stroke="{_ROJO}" stroke-width="{r * .2:.0f}" stroke-linecap="round"/>')
    if frente:
        ex1, ex2, ey = cx - r * .36, cx + r * .36, cy - r * .08
        sx, sy = cx, cy + r * .34
    else:
        ex1, ex2, ey = cx + r * .18, cx + r * .5, cy - r * .12
        sx, sy = cx + r * .52, cy + r * .28
    for ex in (ex1, ex2):
        o.append(f'<circle cx="{ex:.0f}" cy="{ey:.0f}" r="{r * .11:.0f}" fill="{_NAR}"/>'
                 f'<circle cx="{ex + r * .03:.0f}" cy="{ey - r * .04:.0f}" r="{r * .035:.0f}" fill="#fff"/>')
        if osa:
            o.append(f'<path d="M{ex - r * .12:.0f},{ey - r * .12:.0f} l{-r * .1:.0f},{-r * .1:.0f} '
                     f'M{ex:.0f},{ey - r * .16:.0f} l0,{-r * .14:.0f} M{ex + r * .12:.0f},{ey - r * .12:.0f} l{r * .1:.0f},{-r * .1:.0f}" '
                     f'stroke="{_NAR}" stroke-width="4" stroke-linecap="round" fill="none"/>')
    o.append(f'<ellipse cx="{sx:.0f}" cy="{sy:.0f}" rx="{r * .42:.0f}" ry="{r * .32:.0f}" fill="{_HOC}" stroke="{_OUT}" stroke-width="4"/>'
             f'<ellipse cx="{sx + (0 if frente else r * .18):.0f}" cy="{sy - r * .1:.0f}" rx="{r * .15:.0f}" ry="{r * .1:.0f}" fill="{_NAR}"/>'
             f'<path d="M{sx - r * .14 + (0 if frente else r * .1):.0f},{sy + r * .1:.0f} q{r * .14:.0f},{r * .14:.0f} {r * .28:.0f},0" '
             f'stroke="{_NAR}" stroke-width="4" fill="none" stroke-linecap="round"/>')
    if osa:   # moño rosa
        bx, by = cx + (r * .55 if frente else -r * .1), cy - r * 1.02
        o.append(f'<path d="M{bx:.0f},{by:.0f} l{-r * .42:.0f},{-r * .26:.0f} l0,{r * .52:.0f} z '
                 f'M{bx:.0f},{by:.0f} l{r * .42:.0f},{-r * .26:.0f} l0,{r * .52:.0f} z" fill="{_ROSA}" stroke="{_OUT}" stroke-width="4" stroke-linejoin="round"/>'
                 f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="{r * .13:.0f}" fill="#FF8FB0" stroke="{_OUT}" stroke-width="3"/>')
    return "".join(o)


def _placa(cx, cy, r, ancho_eje=1):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{_PLACA2}" stroke="{_OUT}" stroke-width="6"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * .72:.0f}" fill="none" stroke="{_ROJO}" stroke-width="6"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * .26:.0f}" fill="#AEB8C2" stroke="{_OUT}" stroke-width="4"/>')


def _escena_press():
    """Oso acostado en banco empujando la barra (coordenadas propias, ~560 x 410)."""
    o = []
    o.append(f'<circle cx="300" cy="400" r="210" fill="url(#brillo)"/>')
    # banco
    o.append(f'<rect x="120" y="508" width="450" height="46" rx="18" fill="{_PLACA2}" stroke="{_OUT}" stroke-width="6"/>'
             f'<rect x="170" y="552" width="22" height="58" fill="{_PLACA2}"/><rect x="500" y="552" width="22" height="58" fill="{_PLACA2}"/>'
             f'<rect x="150" y="604" width="70" height="12" rx="6" fill="{_PLACA2}"/><rect x="470" y="604" width="70" height="12" rx="6" fill="{_PLACA2}"/>')
    # piernas (flexionadas, pies en el piso)
    o.append(_miembro([(450, 505), (545, 470), (565, 598)], 40))
    o.append(f'<ellipse cx="582" cy="606" rx="36" ry="15" fill="#2B3440" stroke="{_OUT}" stroke-width="5"/>')
    # torso y playera
    o.append(f'<ellipse cx="325" cy="498" rx="150" ry="48" fill="{_PEL}" stroke="{_OUT}" stroke-width="6"/>')
    o.append(f'<ellipse cx="330" cy="500" rx="105" ry="40" fill="{_ROJO}" opacity=".9"/>')
    # brazos hacia arriba (sosteniendo la barra) y placa
    o.append(_miembro([(255, 470), (255, 318)], 36))
    o.append(f'<path d="M150,300 L360,300" stroke="#AEB8C2" stroke-width="12" stroke-linecap="round"/>')
    o.append(_placa(255, 300, 62))
    o.append(f'<circle cx="255" cy="318" r="22" fill="{_PEL}" stroke="{_OUT}" stroke-width="5"/>')
    o.append(f'<rect x="232" y="338" width="46" height="16" rx="6" fill="{_ROJO}"/>')   # muñequera
    # cabeza
    o.append(_cabeza_oso(150, 478, 58, frente=True, banda=True))
    return "".join(o)


def _escena_sentadilla():
    """Osa en sentadilla con barra en la espalda (coordenadas propias, ~300 x 400)."""
    o = []
    o.append(f'<circle cx="950" cy="440" r="210" fill="url(#brillo)"/>')
    # pierna lejana
    o.append(_miembro([(890, 482), (1000, 478), (940, 590)], 44, "#8A5C33"))
    o.append(f'<ellipse cx="946" cy="600" rx="40" ry="15" fill="#E04A7A" stroke="{_OUT}" stroke-width="5"/>')
    # pierna cercana
    o.append(_miembro([(905, 478), (1022, 468), (958, 584)], 48))
    o.append(f'<ellipse cx="962" cy="598" rx="44" ry="16" fill="{_ROSA}" stroke="{_OUT}" stroke-width="5"/>')
    # short y top rosa, torso
    o.append(_miembro([(905, 480), (960, 345)], 92))
    o.append(f'<path d="M920,452 L955,370" stroke="{_ROSA}" stroke-width="92" stroke-linecap="round" fill="none"/>')
    o.append(f'<path d="M900,492 L960,478" stroke="{_ROSA}" stroke-width="66" stroke-linecap="round" fill="none"/>')
    # barra, placa y brazo
    o.append(f'<path d="M850,345 L1070,345" stroke="#AEB8C2" stroke-width="12" stroke-linecap="round"/>')
    o.append(_placa(955, 345, 62))
    o.append(_miembro([(968, 372), (930, 418), (944, 350)], 30))
    # cabeza (de perfil)
    o.append(_cabeza_oso(990, 282, 52, frente=False, osa=True))
    return "".join(o)


def _utileria(ancho, alto, suelo, disco_y, rack_y, kb_x, letrero_y):
    """Detalles de gimnasio: letrero, discos en la pared, mancuernas, kettlebells, rayos y piso."""
    o = [f'<text x="{ancho / 2:.0f}" y="{letrero_y}" text-anchor="middle" font-family="Impact, Arial Black, sans-serif" '
         f'font-size="{min(ancho * .15, 130):.0f}" fill="none" stroke="{_ROJO}" stroke-width="5" letter-spacing="8">GYM</text>']
    for x in (ancho * .13, ancho * .87):                        # rayos
        y = letrero_y - 96
        o.append(f'<path d="M{x + 10:.0f},{y} l-14,38 l12,0 l-12,38 l30,-48 l-12,0 l12,-28 z" fill="#F7B500" stroke="{_OUT}" stroke-width="3" stroke-linejoin="round"/>')
    for k in range(3):                                          # discos en la pared (izquierda)
        cy = disco_y + k * 62
        o.append(f'<circle cx="{58 + k * 6}" cy="{cy:.0f}" r="{42 - k * 6}" fill="{_PLACA2}" stroke="{_OUT}" stroke-width="5"/>'
                 f'<circle cx="{58 + k * 6}" cy="{cy:.0f}" r="{(42 - k * 6) * .25:.0f}" fill="#AEB8C2"/>')
    for k in range(5):                                          # rack de mancuernas (derecha)
        y = rack_y + k * 26
        c = _PLACA if k % 2 else _PLACA2
        o.append(f'<rect x="{ancho - 190}" y="{y:.0f}" width="150" height="8" rx="4" fill="#AEB8C2"/>'
                 f'<rect x="{ancho - 200}" y="{y - 10:.0f}" width="20" height="28" rx="5" fill="{c}" stroke="{_OUT}" stroke-width="3"/>'
                 f'<rect x="{ancho - 60}" y="{y - 10:.0f}" width="20" height="28" rx="5" fill="{c}" stroke="{_OUT}" stroke-width="3"/>')
    for x in kb_x:                                              # kettlebells
        o.append(f'<path d="M{x - 14:.0f},{suelo - 52:.0f} q14,-30 28,0" fill="none" stroke="{_OUT}" stroke-width="9" stroke-linecap="round"/>'
                 f'<circle cx="{x:.0f}" cy="{suelo - 28:.0f}" r="26" fill="{_PLACA2}" stroke="{_OUT}" stroke-width="5"/>')
    o.append(f'<rect x="0" y="{suelo}" width="{ancho}" height="{alto - suelo}" fill="{_PLACA2}" opacity=".55"/>'
             f'<path d="M0,{suelo} L{ancho},{suelo}" stroke="{_ROJO}" stroke-width="6"/>')
    return "".join(o)


def fondo_gym_svg(vertical):
    defs = ('<defs><radialGradient id="brillo"><stop offset="0" stop-color="#FFB454" stop-opacity=".55"/>'
            '<stop offset="1" stop-color="#FFB454" stop-opacity="0"/></radialGradient></defs>')
    if vertical:      # 600 x 1100: oso arriba, osa abajo
        w, h, suelo = 600, 1100, 1010
        cuerpo = (_utileria(w, h, suelo, 190, 175, (70, 125), 120) +
                  f'<rect x="0" y="560" width="{w}" height="14" fill="{_PLACA2}" opacity=".55"/>'
                  f'<path d="M0,560 L{w},560" stroke="{_ROJO}" stroke-width="5"/>'
                  '<g transform="translate(-32,-29) scale(.95)">' + _escena_press() + '</g>'
                  '<g transform="translate(-810,306) scale(1.15)">' + _escena_sentadilla() + '</g>')
    else:             # 1200 x 700: oso a la izquierda, osa a la derecha
        w, h, suelo = 1200, 700, 618
        cuerpo = (_utileria(w, h, suelo, 168, 150, (690, 750), 150) + _escena_press() + _escena_sentadilla())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice">'
            f'{defs}<g opacity=".36">{cuerpo}</g></svg>')


@lru_cache(maxsize=1)
def css_fondo():
    """CSS con el fondo de gimnasio (una versión para vertical y otra para horizontal)."""
    def uri(vertical):
        return "data:image/svg+xml;base64," + base64.b64encode(fondo_gym_svg(vertical).encode()).decode()
    return ('<style>'
            '.stApp{background-size:cover;background-position:center;background-attachment:fixed;background-repeat:no-repeat;}'
            f'@media (orientation: portrait){{.stApp{{background-image:url("{uri(True)}");}}}}'
            f'@media (orientation: landscape){{.stApp{{background-image:url("{uri(False)}");}}}}'
            '[data-testid="stAppViewContainer"],[data-testid="stMain"],.main{background:transparent !important;}'
            '</style>')


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
    """ + css_fondo(),
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


# ---------------------------------------------------------
# Rutinas 2 a 5: ejercicios distintos con el mismo enfoque muscular
# ---------------------------------------------------------
# (nombre, tipo, técnica). Tipos: C compuesto, A aislamiento, P pantorrilla, T isométrico (tiempo),
# L abdomen por repeticiones; "=texto" usa ese texto como series y repeticiones.
BIBLIOTECA = {
    "pecho": [
        ("Press de banca plano con barra", "C", "Retracción escapular y pies firmes en el suelo."),
        ("Press con mancuernas en banco plano", "C", "Baja hasta sentir estiramiento y empuja sin chocar las mancuernas."),
        ("Press inclinado con barra", "C", "Banco a 30-45°; baja a la parte alta del pecho."),
        ("Press inclinado con mancuernas", "C", "Codos a unos 45° del torso y control en la bajada."),
        ("Press declinado con mancuernas", "C", "Hombros hacia atrás y abajo durante todo el movimiento."),
        ("Aperturas con mancuernas", "A", "Codos ligeramente flexionados; abre sin forzar el hombro."),
        ("Aperturas en polea (cruces)", "A", "Junta las manos frente al pecho y aprieta 1 segundo."),
        ("Flexiones de pecho (push-ups)", "C", "Core firme y cuerpo alineado con la cadera."),
        ("Press en máquina de pecho", "C", "Espalda pegada al respaldo y empuje controlado."),
        ("Fondos en paralelas para pecho", "C", "Inclina el torso al frente; usa asistencia si hace falta."),
    ],
    "espalda": [
        ("Jalón al pecho", "C", "Lleva la barra al pecho apretando los dorsales."),
        ("Jalón agarre cerrado", "C", "Codos hacia las costillas y pecho arriba."),
        ("Dominadas asistidas", "C", "Inicia el movimiento con los dorsales, no con los brazos."),
        ("Remo con barra", "C", "Espalda neutra, torso inclinado y codos hacia atrás."),
        ("Remo con mancuerna a una mano", "C", "Apoya una mano y lleva el codo hacia la cadera."),
        ("Remo en polea baja", "C", "Junta los omóplatos al final y regresa lento."),
        ("Remo en máquina", "C", "Pecho pegado al soporte; no encojas los hombros."),
        ("Remo T con barra", "C", "Espalda recta y movimiento sin impulso."),
        ("Peso muerto convencional", "C", "Espalda neutra, empuja el piso y bloquea con la cadera."),
        ("Face pull en polea", "A", "Lleva la cuerda a la cara abriendo los codos."),
    ],
    "hombros": [
        ("Press militar con barra", "C", "Core firme; no arquees la zona lumbar."),
        ("Press de hombro con mancuernas", "C", "Movimiento controlado, sin bloquear los codos."),
        ("Press Arnold", "C", "Gira las palmas mientras subes, de forma fluida."),
        ("Elevaciones laterales", "A", "Sube hasta la altura del hombro con control."),
        ("Elevaciones laterales en polea", "A", "Mantén tensión constante y sin balanceo."),
        ("Pájaros (deltoide posterior)", "A", "Torso inclinado y movimiento lento."),
        ("Elevaciones frontales", "A", "Sube al frente hasta el hombro sin balancearte."),
    ],
    "trapecio": [
        ("Encogimientos de trapecio con mancuernas", "A", "Sube los hombros hacia las orejas sin rotarlos."),
        ("Encogimientos con barra", "A", "Pausa de 1 segundo arriba y baja lento."),
        ("Face pull en polea", "A", "Abre los codos y junta los omóplatos."),
        ("Encogimientos en máquina Smith", "A", "Recorrido corto y controlado."),
        ("Encogimientos con agarre por detrás", "A", "Pecho arriba y hombros hacia atrás."),
    ],
    "biceps": [
        ("Curl de bíceps con barra", "A", "Codos fijos y sin balanceo del torso."),
        ("Curl alterno con mancuernas", "A", "Sube controlado, sin impulso."),
        ("Curl martillo", "A", "Agarre neutro; trabaja también el antebrazo."),
        ("Curl concentrado", "A", "Codo apoyado en el muslo y contracción arriba."),
        ("Curl predicador", "A", "Baja casi hasta extender sin soltar la tensión."),
        ("Curl en polea baja", "A", "Tensión constante durante todo el recorrido."),
        ("Curl inclinado con mancuernas", "A", "Estira el bíceps abajo y sube lento."),
    ],
    "triceps": [
        ("Extensión de tríceps en polea", "A", "Codos fijos a los costados y extensión completa."),
        ("Press francés con barra Z", "A", "Codos apuntando al techo; baja hacia la frente."),
        ("Extensión de tríceps sobre la cabeza", "A", "Codo junto a la cabeza y extensión completa."),
        ("Fondos en banco (tríceps)", "A", "Espalda cerca del banco y codos hacia atrás."),
        ("Press de banca agarre cerrado", "C", "Codos pegados al cuerpo y trayectoria recta."),
        ("Extensión de tríceps con cuerda", "A", "Abre la cuerda al final del movimiento."),
    ],
    "cuadriceps": [
        ("Sentadilla trasera libre", "C", "Espalda neutra y profundidad al menos hasta el paralelo."),
        ("Sentadilla frontal", "C", "Codos arriba y torso erguido."),
        ("Sentadilla goblet", "C", "Pecho arriba y talones apoyados."),
        ("Sentadilla hack en máquina", "C", "Pies a la altura de la cadera; baja con control."),
        ("Prensa de pierna", "C", "No bloquees las rodillas al extender."),
        ("Zancadas caminando", "C", "Paso largo, torso erguido y rodilla alineada con el pie."),
        ("Zancadas reversas", "C", "Da el paso atrás y baja la rodilla cerca del piso."),
        ("Sentadilla búlgara", "C", "Torso ligeramente inclinado; el peso va en la pierna delantera."),
        ("Step-ups al cajón", "C", "Empuja con el talón de la pierna que sube."),
        ("Extensión de cuádriceps", "A", "Pausa de 1 segundo arriba."),
    ],
    "femorales": [
        ("Peso muerto rumano", "C", "Cadera hacia atrás, barra pegada a las piernas."),
        ("Curl femoral acostado", "A", "Baja lento (3 segundos) en cada repetición."),
        ("Curl femoral sentado", "A", "Espalda pegada al respaldo y recorrido completo."),
        ("Peso muerto con piernas rígidas", "C", "Rodillas casi estiradas y espalda neutra."),
        ("Buenos días con barra ligera", "C", "Bisagra de cadera sin redondear la espalda."),
        ("Peso muerto a una pierna", "C", "Mantén la cadera nivelada y la mirada al frente."),
    ],
    "gluteos": [
        ("Hip thrust (empuje de cadera)", "C", "Mentón al pecho y aprieta los glúteos arriba."),
        ("Puente de glúteo", "A", "Aprieta glúteos arriba 1 segundo."),
        ("Puente de glúteo a una pierna", "A", "Cadera nivelada y empuje con el talón."),
        ("Patada de glúteo en polea", "A", "Empuja el talón hacia atrás sin arquear la espalda."),
        ("Patada de glúteo a cuatro apoyos", "A", "Espalda neutra; sube el talón hacia el techo."),
        ("Sentadilla sumo con mancuerna", "C", "Puntas hacia afuera y rodillas siguiendo los pies."),
        ("Zancada lateral", "C", "Lleva la cadera atrás al bajar."),
        ("Peso muerto sumo", "C", "Pecho arriba y empuja el piso con las piernas."),
    ],
    "pantorrillas": [
        ("Elevación de talones de pie", "P", "Recorrido completo y pausa arriba."),
        ("Elevación de talones en prensa", "P", "Baja hasta estirar y sube sin rebotar."),
        ("Elevación de talones sentado", "P", "Movimiento lento y controlado."),
        ("Elevación de talones a una pierna", "P", "Apóyate ligeramente para mantener el equilibrio."),
    ],
    "core": [
        ("Plancha abdominal", "T", "Contrae glúteos y abdomen; cuerpo en línea recta."),
        ("Elevación de piernas acostado", "L", "Sube con el abdomen y baja sin tocar el piso."),
        ("Crunch abdominal", "L", "Sube el pecho sin jalar el cuello."),
        ("Crunch bicicleta", "L", "Gira el torso, no solo los codos."),
        ("Mountain climbers", "=4 x 30 seg", "Rodillas al pecho con ritmo constante."),
        ("Russian twist", "L", "Gira desde el torso con la espalda recta."),
        ("Rodillas al pecho colgado", "L", "Sin balanceo; sube con el abdomen."),
        ("Crunch en polea", "L", "Redondea la espalda llevando los codos a las rodillas."),
        ("Plancha lateral", "T", "Cadera arriba y cuerpo alineado."),
    ],
    "cardio": [
        ("Caminata inclinada", "=20 min", "Ritmo en el que aún puedas hablar con frases cortas."),
        ("Bicicleta estática", "=20 min", "Cadencia constante y espalda recta."),
        ("Trote suave", "=15 min", "Respiración controlada y pasos cortos."),
        ("Elíptica", "=20 min", "Postura erguida y ritmo moderado."),
        ("Saltos de cuerda por intervalos", "=10 min", "30 seg saltando / 30 seg descansando."),
        ("HIIT en bici (30 seg fuerte / 30 seg suave)", "=10 min", "El esfuerzo fuerte debe ser exigente."),
        ("Subir escaleras", "=15 min", "Apoya todo el pie y mantén el ritmo."),
        ("Caminata rápida", "=25 min", "Brazos activos y paso largo."),
    ],
    "cuerpo": [
        ("Burpees", "=4 x 10", "Ajusta el ritmo a tu nivel; sin saltar si lo necesitas."),
        ("Sentadilla con salto", "=4 x 15", "Aterriza suave con las rodillas flexionadas."),
        ("Thrusters con mancuernas", "=4 x 12", "Sentadilla profunda y empuje sobre la cabeza al subir."),
        ("Swing con kettlebell", "=4 x 15", "Cadera potente; los brazos solo guían."),
        ("Mountain climbers", "=4 x 30 seg", "Rodillas al pecho con ritmo constante."),
        ("Flexiones de pecho (push-ups)", "=3 x 15", "Hazlas con rodillas apoyadas si pierdes la técnica."),
        ("Remo con mancuernas", "=4 x 12", "Espalda neutra y codos hacia atrás."),
        ("Peso muerto con mancuernas", "=4 x 12", "Espalda neutra, cadera atrás."),
        ("Zancadas alternadas (lunges)", "=4 x 12 por pierna", "Espalda recta y rodilla trasera cerca del suelo."),
        ("Plancha abdominal", "=4 x 45 seg", "Contrae glúteos y abdomen con fuerza."),
    ],
}

REPS_TIPO = {
    OBJ_MASA: {"C": "4 x 8-10", "A": "3 x 12", "P": "4 x 15", "T": "3 x 45-60 seg", "L": "3 x 15"},
    OBJ_DEF: {"C": "4 x 12-15", "A": "3 x 15", "P": "4 x 20", "T": "4 x 45-60 seg", "L": "3 x 20"},
}

# Por día: (grupo, ejercicios para Oso/masculino, ejercicios para Osita/femenino)
_PLANTILLAS = {
    (OBJ_MASA, 3): [
        ("Día 1: Pecho, hombro y tríceps", [("pecho", 2, 2), ("hombros", 1, 2), ("triceps", 1, 1)]),
        ("Día 2: Espalda y bíceps", [("espalda", 3, 3), ("biceps", 1, 1), ("core", 0, 1)]),
        ("Día 3: Pierna completa", [("cuadriceps", 2, 2), ("femorales", 1, 1), ("gluteos", 1, 2), ("pantorrillas", 1, 1)]),
    ],
    (OBJ_DEF, 3): [
        ("Día 1: Torso completo + cardio", [("pecho", 1, 1), ("espalda", 1, 1), ("hombros", 1, 1), ("triceps", 1, 0), ("cardio", 1, 1)]),
        ("Día 2: Pierna + core", [("cuadriceps", 2, 2), ("gluteos", 1, 2), ("femorales", 1, 1), ("core", 1, 1)]),
        ("Día 3: Circuito full body", [("cuerpo", 4, 4), ("cardio", 1, 1)]),
    ],
    (OBJ_MASA, 5): [
        ("Día 1: Pecho y tríceps", [("pecho", 3, 3), ("triceps", 2, 1), ("core", 0, 1)]),
        ("Día 2: Espalda y bíceps", [("espalda", 3, 3), ("biceps", 2, 1)]),
        ("Día 3: Cuádriceps y glúteos", [("cuadriceps", 3, 3), ("gluteos", 2, 3)]),
        ("Día 4: Hombros, trapecio y brazos", [("hombros", 3, 3), ("trapecio", 1, 1), ("biceps", 1, 1), ("triceps", 1, 1)]),
        ("Día 5: Femorales, pantorrillas y core", [("femorales", 2, 2), ("cuadriceps", 1, 0), ("gluteos", 0, 1), ("pantorrillas", 1, 1), ("core", 2, 2)]),
    ],
    (OBJ_DEF, 5): [
        ("Día 1: Pecho, tríceps y cardio", [("pecho", 3, 2), ("triceps", 1, 1), ("core", 0, 1), ("cardio", 1, 1)]),
        ("Día 2: Espalda, bíceps y HIIT", [("espalda", 3, 3), ("biceps", 1, 1), ("cardio", 1, 1)]),
        ("Día 3: Pierna completa", [("cuadriceps", 2, 2), ("femorales", 1, 1), ("gluteos", 1, 2), ("pantorrillas", 1, 1)]),
        ("Día 4: Hombros, core y cardio", [("hombros", 3, 3), ("core", 2, 2), ("cardio", 1, 1)]),
        ("Día 5: Circuito full body", [("cuerpo", 5, 5), ("cardio", 1, 1)]),
    ],
}


def _elegir(lista, n, desplazamiento, usados):
    """Toma n ejercicios de la lista a partir de un desplazamiento, sin repetir dentro del día."""
    res, i = [], 0
    while len(res) < n and i < len(lista) * 2:
        e = lista[(desplazamiento + i) % len(lista)]
        i += 1
        if e[0] not in usados:
            usados.add(e[0])
            res.append(e)
    return res


def generar_rutina(objetivo, dias, variante, sexo="Masculino"):
    """Rutina 2 a 5: mismo enfoque por día que la Rutina 1, con ejercicios distintos.
    Cambia según objetivo, días por semana (3 o 5) y perfil (Oso / Osita)."""
    fem = sexo == "Femenino"
    reps = REPS_TIPO[objetivo]
    salida = []
    for titulo, grupos in _PLANTILLAS[(objetivo, 5 if dias == 5 else 3)]:
        usados, ejercicios = set(), []
        for grupo, n_oso, n_osita in grupos:
            n = n_osita if fem else n_oso
            if not n:
                continue
            desplaz = (variante - 1) * n + (1 if fem else 0)
            for nombre, tipo, tips in _elegir(BIBLIOTECA[grupo], n, desplaz, usados):
                ejercicios.append({"nombre": nombre, "series_reps": tipo[1:] if tipo.startswith("=") else reps[tipo],
                                   "tips": tips})
        salida.append({"dia": titulo, "ejercicios": ejercicios})
    return salida


def elegir_rutina(objetivo, dias, variante=1, sexo="Masculino"):
    if variante and variante > 1:
        return generar_rutina(objetivo, dias, variante, sexo)
    if dias == 5:
        return RUTINA_HIPERTROFIA_5 if objetivo == OBJ_MASA else RUTINA_DEFINICION_5
    return RUTINA_HIPERTROFIA if objetivo == OBJ_MASA else RUTINA_DEFINICION


# Más ideas de comidas: objetivo -> tipo de menú -> comida -> ideas
ESTILOS_MENU = ["Clásico mexicano", "Económico", "Rápido (poco tiempo)", "Vegetariano", "Para llevar (trabajo o escuela)"]
IDEAS_MENU = {
    OBJ_MASA: {
        "Clásico mexicano": {
            "Desayuno": ["Huevos a la mexicana con frijoles y tortillas de maíz", "Avena con plátano, nueces y leche", "Chilaquiles con pollo y queso fresco"],
            "Comida": ["Pollo o carne asada con arroz, frijoles y ensalada", "Pescado empanizado al horno con arroz y verduras", "Pasta con carne molida, queso y ensalada"],
            "Snack": ["Yogur griego con fruta y nueces", "Sándwich de atún con aguacate", "Licuado de plátano, avena y leche"],
            "Cena": ["Pescado o pollo con papa o camote y verduras", "Quesadillas de pollo con frijoles y salsa", "Tacos de carne con nopales y aguacate"],
        },
        "Económico": {
            "Desayuno": ["Huevos revueltos con frijoles y tortillas", "Avena cocida con leche y plátano", "Molletes con frijoles y queso"],
            "Comida": ["Arroz con huevo y frijoles de la olla", "Lentejas con arroz y plátano macho", "Pollo guisado con papa y zanahoria"],
            "Snack": ["Plátano con crema de cacahuate", "Pan integral con atún", "Palomitas con cacahuates y un vaso de leche"],
            "Cena": ["Tostadas de frijol con huevo y aguacate", "Sopa de pasta con pollo y verduras", "Quesadillas con frijoles y salsa"],
        },
        "Rápido (poco tiempo)": {
            "Desayuno": ["Licuado de leche, plátano, avena y crema de cacahuate", "Sándwich de huevo y jamón de pavo", "Yogur con granola y fruta"],
            "Comida": ["Burrito de pollo, arroz y frijoles", "Atún con arroz instantáneo y aguacate", "Pasta con pollo desmenuzado y queso"],
            "Snack": ["Barra de cereal con un puñado de nueces", "Queso con galletas integrales", "Batido de proteína con plátano"],
            "Cena": ["Wrap de pollo con verduras y queso", "Omelette de queso y jamón con tortillas", "Sopa instantánea con huevo y tostadas"],
        },
        "Vegetariano": {
            "Desayuno": ["Huevos con espinaca, frijoles y tortillas", "Avena con leche, plátano y semillas", "Hot cakes de avena con yogur y fruta"],
            "Comida": ["Lentejas o garbanzos con arroz y ensalada", "Tacos de frijol, queso y aguacate", "Pasta con queso, verduras y frijoles"],
            "Snack": ["Yogur griego con nueces y miel", "Hummus con pan pita", "Licuado de plátano, avena y cacahuate"],
            "Cena": ["Tortilla de huevo con papa y verduras", "Enchiladas de queso con frijoles", "Quesadillas de champiñón y queso"],
        },
        "Para llevar (trabajo o escuela)": {
            "Desayuno": ["Sándwich de huevo y queso en pan integral", "Frasco de avena con fruta y nueces", "Burrito de huevo y frijoles"],
            "Comida": ["Contenedor con pollo, arroz y verduras", "Ensalada de atún con pasta y aguacate", "Tortas de milanesa de pollo con frijoles"],
            "Snack": ["Bolsita de nueces y fruta seca", "Queso panela con tortillitas", "Yogur bebible y un plátano"],
            "Cena": ["Tacos de pollo o res listos del refri", "Arroz con pollo y verduras al vapor", "Sándwich de pavo con queso y aguacate"],
        },
    },
    OBJ_DEF: {
        "Clásico mexicano": {
            "Desayuno": ["Omelette de claras con espinaca, nopales y tortilla de maíz", "Huevos al gusto con frijoles de la olla y fruta", "Avena con canela, manzana y yogur natural"],
            "Comida": ["Pescado a la plancha con ensalada y media taza de arroz", "Pechuga con verduras al vapor y frijoles", "Caldo de pollo con verduras y tortilla"],
            "Snack": ["Fruta con yogur griego natural", "Pepino con limón y huevo cocido", "Jícama con chile y limón"],
            "Cena": ["Tostadas de ceviche de pescado con aguacate", "Sopa de verduras con pollo desmenuzado", "Ensalada de atún con garbanzos y limón"],
        },
        "Económico": {
            "Desayuno": ["Huevo cocido con frijoles y tortilla de maíz", "Avena con agua o leche descremada y canela", "Nopales con huevo y salsa"],
            "Comida": ["Frijoles con nopales y arroz (porción pequeña)", "Pollo hervido con calabacitas y chayote", "Sopa de lentejas con verduras"],
            "Snack": ["Manzana o naranja de temporada", "Zanahoria y pepino con limón", "Palomitas naturales sin mantequilla"],
            "Cena": ["Tostadas de frijol con lechuga y salsa", "Caldo de verduras con huevo", "Ensalada de atún con jitomate y cebolla"],
        },
        "Rápido (poco tiempo)": {
            "Desayuno": ["Yogur natural con fruta y avena", "Huevos revueltos con espinaca en 5 minutos", "Licuado de fruta con proteína y agua"],
            "Comida": ["Ensalada con atún o pollo de lata y aguacate", "Wrap de pechuga con lechuga y jitomate", "Pollo a la plancha con verduras congeladas"],
            "Snack": ["Gelatina sin azúcar con fruta", "Queso panela con pepino", "Proteína en polvo con agua"],
            "Cena": ["Omelette de claras con champiñones", "Sopa de verduras con huevo", "Tacos de lechuga con pollo o atún"],
        },
        "Vegetariano": {
            "Desayuno": ["Tofu o huevo revuelto con espinaca", "Yogur natural con chía y fruta", "Avena con canela y manzana"],
            "Comida": ["Ensalada de garbanzos con verduras y limón", "Lentejas con verduras y media taza de arroz", "Tacos de nopal con frijoles y queso panela"],
            "Snack": ["Hummus con zanahoria y pepino", "Yogur griego natural con fresas", "Garbanzos asados"],
            "Cena": ["Sopa de verduras con queso panela", "Omelette de claras con champiñón y espinaca", "Calabacitas rellenas de frijol y queso"],
        },
        "Para llevar (trabajo o escuela)": {
            "Desayuno": ["Frasco de avena con fruta y semillas", "Huevos cocidos y fruta", "Sándwich de claras con pavo en pan integral"],
            "Comida": ["Contenedor de pollo, verduras y arroz integral", "Ensalada grande de atún con garbanzos", "Bowl de frijoles, pollo, lechuga y pico de gallo"],
            "Snack": ["Fruta picada con limón", "Palitos de zanahoria con hummus", "Yogur natural y un puñado de nueces"],
            "Cena": ["Ensalada de pollo con aguacate", "Sopa de verduras en termo", "Rollitos de pavo con queso panela y lechuga"],
        },
    },
}



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
        story.append(P(f"{r['nombre']} - plan de {r['dias']} días por semana - Rutina {r.get('variante', 1)} - generado el {date.today():%d/%m/%Y}", small))
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
# Ilustraciones animadas de los ejercicios (SVG, sin internet)
# ---------------------------------------------------------
_LT, _LM, _LS, _UA, _FA = 50, 38, 38, 26, 24   # torso, muslo, espinilla, brazo, antebrazo
_COL_N, _COL_F = "#2C3E50", "#9AA9B8"          # extremidad cercana / lejana


def _dir(a):
    r = math.radians(a)
    return (math.sin(r), -math.cos(r))


def _mv(p, a, ln):
    d = _dir(a)
    return (p[0] + d[0] * ln, p[1] + d[1] * ln)


def _ik(p, tgt, l1, l2, side):
    """Dos huesos de largo l1 y l2 desde p hacia tgt. side=±1 elige hacia dónde dobla la articulación."""
    dx, dy = tgt[0] - p[0], tgt[1] - p[1]
    raw = math.hypot(dx, dy)
    ux, uy = (dx / raw, dy / raw) if raw > 1e-6 else (0.0, 1.0)
    d = min(max(raw, abs(l1 - l2) + 0.1), l1 + l2 - 0.1)
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    mid = (p[0] + ux * a + side * h * (-uy), p[1] + uy * a + side * h * ux)
    return mid, (p[0] + ux * d, p[1] + uy * d)


def _limb(origin, spec, l1, l2):
    if spec[0] == "ik":
        return _ik(origin, spec[1], l1, l2, spec[2])
    if spec[0] == "rel":
        return _ik(origin, (origin[0] + spec[1][0], origin[1] + spec[1][1]), l1, l2, spec[2])
    mid = _mv(origin, spec[1], l1)          # "fk": ángulos absolutos
    return mid, _mv(mid, spec[2], l2)


def _lerp(a, b, f):
    if isinstance(a, (int, float)):
        return a + (b - a) * f
    if isinstance(a, (list, tuple)):
        return type(a)(_lerp(x, y, f) for x, y in zip(a, b))
    if isinstance(a, dict):
        return {k: _lerp(a[k], b[k], f) for k in a}
    return a


def _pose(hip, t, legs, arms, hd=0):
    return {"hip": hip, "t": t, "legs": legs, "arms": arms, "hd": hd}


def _frame(p):
    hip, t = p["hip"], p["t"]
    sh = _mv(hip, t, _LT)
    head = _mv(sh, t + p["hd"], 17)
    legs, arms = [], []
    for sp in p["legs"]:
        kn, an = _limb(hip, sp, _LM, _LS)
        legs.append([hip, kn, an, _mv(an, sp[3] if len(sp) > 3 else 90, 11)])
    for sp in p["arms"]:
        el, ha = _limb(sh, sp, _UA, _FA)
        arms.append([sh, el, ha])
    return {"hip": hip, "sh": sh, "head": head, "legs": legs, "arms": arms}


def _fr_front(k):
    sd, hd = k.get("sd", 0), k.get("hd", 0)
    sl, sr = (122, 44 + sd), (158, 44 + sd)
    arms = []
    for s, tg, side in ((sl, k["hl"], k.get("el", 1)), (sr, k["hr"], -k.get("el", 1))):
        el, ha = _ik(s, tg, _UA, _FA, side)
        arms.append([s, el, ha])
    return {"head": (140, 24 + hd), "sl": sl, "sr": sr, "arms": arms,
            "hipl": (131, 104), "hipr": (149, 104)}


def _n(v):
    return f"{v:.1f}"


def _pts(*ps):
    return " ".join(f"{_n(x)},{_n(y)}" for x, y in ps)


def _anim(attr, vals, dur):
    return (f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" '
            f'calcMode="linear" values="{";".join(vals)}"/>')


def _secuencia(keys, mk, n=8):
    if len(keys) == 1:
        return [mk(keys[0])], False
    out = []
    for a, b in zip(keys, keys[1:] + keys[:1]):
        for i in range(n):
            f = (1 - math.cos(math.pi * i / n)) / 2      # arranque y frenado suaves
            out.append(mk(_lerp(a, b, f)))
    out.append(out[0])
    return out, True


def _escena_svg(escena):
    out = []
    for s in escena:
        if s[0] == "line":
            out.append(f'<line x1="{s[1]}" y1="{s[2]}" x2="{s[3]}" y2="{s[4]}" stroke="{s[6] if len(s) > 6 else "#A1887F"}" '
                       f'stroke-width="{s[5]}" stroke-linecap="round"/>')
    return "".join(out)


def _poli(frames_pts, color, ancho, dur, anim):
    f0 = frames_pts[0]
    el = (f'<polyline points="{f0}" fill="none" stroke="{color}" stroke-width="{ancho}" '
          f'stroke-linecap="round" stroke-linejoin="round">')
    if anim:
        el += _anim("points", frames_pts, dur)
    return el + "</polyline>"


def _circ(cs, r, color, dur, anim):
    el = f'<circle cx="{_n(cs[0][0])}" cy="{_n(cs[0][1])}" r="{r}" fill="{color}">'
    if anim:
        el += _anim("cx", [_n(c[0]) for c in cs], dur) + _anim("cy", [_n(c[1]) for c in cs], dur)
    return el + "</circle>"


def _svg_lateral(titulo, keys, escena, pesos, cable, dur, nota):
    frames, anim = _secuencia(keys, _frame)
    nl, na = len(frames[0]["legs"]), len(frames[0]["arms"])
    partes = []
    # extremidades lejanas primero
    for i in range(nl - 1, 0, -1):
        partes.append(_poli([_pts(*f["legs"][i]) for f in frames], _COL_F, 5, dur, anim))
    for i in range(na - 1, 0, -1):
        partes.append(_poli([_pts(*f["arms"][i]) for f in frames], _COL_F, 4, dur, anim))
    partes.append(_poli([_pts(f["hip"], f["sh"]) for f in frames], _COL_N, 7, dur, anim))
    partes.append(_poli([_pts(*f["legs"][0]) for f in frames], _COL_N, 5, dur, anim))
    partes.append(_poli([_pts(*f["arms"][0]) for f in frames], _COL_N, 4, dur, anim))
    if cable:
        partes.append(_poli([_pts(cable, f["arms"][0][2]) for f in frames], "#B0B8C0", 1.5, dur, anim))
    partes.append(_circ([f["head"] for f in frames], 9, "#FF4B4B", dur, anim))
    if pesos:
        for i in range(na):
            partes.append(_circ([f["arms"][i][2] for f in frames], 6.5, "#FF8A00", dur, anim))
    return _marco(titulo, _escena_svg(escena) + "".join(partes), nota)


def _svg_frontal(titulo, keys, pesos, dur, nota):
    frames, anim = _secuencia(keys, _fr_front)
    partes = []
    for lado in ("hipl", "hipr"):
        x = 131 if lado == "hipl" else 149
        ax = 128 if lado == "hipl" else 152
        partes.append(f'<polyline points="{x},104 {ax},160" stroke="{_COL_N}" stroke-width="5" '
                      f'stroke-linecap="round" fill="none"/>')
    partes.append(_poli([_pts((140, f["sl"][1]), (140, 104)) for f in frames], _COL_N, 7, dur, anim))
    partes.append(_poli([_pts(f["sl"], f["sr"]) for f in frames], _COL_N, 6, dur, anim))
    partes.append(_poli([_pts(*f["arms"][0]) for f in frames], _COL_N, 4, dur, anim))
    partes.append(_poli([_pts(*f["arms"][1]) for f in frames], _COL_N, 4, dur, anim))
    partes.append(_circ([f["head"] for f in frames], 9, "#FF4B4B", dur, anim))
    if pesos:
        for i in range(2):
            partes.append(_circ([f["arms"][i][2] for f in frames], 6.5, "#FF8A00", dur, anim))
    return _marco(titulo, "".join(partes), nota)


def _marco(titulo, cuerpo, nota):
    t = escape(titulo)[:46]
    n = f'<text x="140" y="176" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#5B6B7B">{escape(nota)}</text>' if nota else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -40 280 220">'
            '<rect x="0" y="-40" width="280" height="220" rx="12" fill="#F4F6F8"/>'
            '<line x1="10" y1="164" x2="270" y2="164" stroke="#B8C2CC" stroke-width="3" stroke-linecap="round"/>'
            f'<text x="10" y="-24" font-family="sans-serif" font-size="11" font-weight="bold" fill="#5B6B7B">{t}</text>'
            f'{cuerpo}{n}</svg>')


# ---- Poses --------------------------------------------------------------
_PIES = [("ik", (114, 161), -1, 90), ("ik", (118, 161), -1, 90)]
_BANCO = [("line", 88, 121, 192, 121, 7), ("line", 100, 124, 100, 164, 4), ("line", 180, 124, 180, 164, 4)]
_PLANK_ANK = (205, 161)


def _plank_top(piernas):
    return _pose((134.9, 130.8), -66.7, piernas, [("ik", (89, 161), 1), ("ik", (93, 161), 1)])


def _patrones():
    P = {}
    P["sentadilla"] = dict(
        keys=[_pose((112, 87), 0, _PIES, [("rel", (14, 6), 1)]),
              _pose((88, 126), 38, _PIES, [("rel", (14, 6), 1)])],
        nota="Baja con la espalda recta y sube empujando el piso")
    P["peso_muerto"] = dict(
        keys=[_pose((110, 87), 0, _PIES, [("rel", (0, 48), 1)]),
              _pose((88, 100), 78, _PIES, [("rel", (0, 48), 1)])],
        nota="Cadera atrás, espalda neutra, barra pegada a las piernas")
    P["zancada"] = dict(
        keys=[_pose((118, 88), 0, [("ik", (146, 161), -1, 90), ("ik", (90, 161), -1, 90)], [("rel", (0, 48), 1)]),
              _pose((118, 120), 0, [("ik", (146, 161), -1, 90), ("ik", (84, 152), -1, 130)], [("rel", (0, 48), 1)])],
        nota="Baja recto; la rodilla delantera no pasa la punta del pie")
    P["prensa"] = dict(
        keys=[_pose((150, 128), 315, [("ik", (186, 92), -1, 0), ("ik", (190, 94), -1, 0)], [("rel", (30, 24), 1)]),
              _pose((150, 128), 315, [("ik", (206, 72), -1, 0), ("ik", (210, 74), -1, 0)], [("rel", (30, 24), 1)])],
        escena=[("line", 142, 136, 96, 90, 5), ("line", 142, 136, 176, 136, 5)], pesos=False,
        nota="Empuja sin bloquear las rodillas")
    P["talones"] = dict(
        keys=[_pose((112, 85), 0, [("ik", (112, 161), -1, 90), ("ik", (118, 161), -1, 90)], [("rel", (0, 48), 1)]),
              _pose((112, 76), 0, [("ik", (112, 152), -1, 140), ("ik", (118, 152), -1, 140)], [("rel", (0, 48), 1)])],
        nota="Sube en puntas, pausa arriba y baja lento")
    P["puente"] = dict(
        keys=[_pose((104, 156), 270, [("ik", (150, 161), -1, 90), ("ik", (156, 161), -1, 90)], [("ik", (112, 160), 1)]),
              _pose((97.3, 131), 240, [("ik", (150, 161), -1, 90), ("ik", (156, 161), -1, 90)], [("ik", (112, 160), 1)])],
        pesos=False, nota="Empuja con los talones y aprieta los glúteos arriba")
    P["elev_piernas"] = dict(
        keys=[_pose((104, 156), 270, [("fk", 90, 90, 0), ("fk", 90, 90, 0)], [("ik", (112, 160), 1)]),
              _pose((104, 156), 270, [("fk", 0, 0, -90), ("fk", 0, 0, -90)], [("ik", (112, 160), 1)])],
        pesos=False, nota="Sube las piernas con el abdomen, baja sin tocar el piso")
    P["crunch"] = dict(
        keys=[_pose((130, 156), 308, [("ik", (152, 128), -1, 90), ("ik", (198, 146), -1, 90)], [("rel", (-4, -14), 1)]),
              _pose((130, 156), 308, [("ik", (198, 146), -1, 90), ("ik", (152, 128), -1, 90)], [("rel", (-4, -14), 1)])],
        pesos=False, nota="Codo hacia la rodilla contraria, sin jalar el cuello")
    P["ext_cuad"] = dict(
        keys=[_pose((132, 124), 355, [("fk", 90, 180, 90), ("fk", 90, 180, 90)], [("rel", (10, 20), 1)]),
              _pose((132, 124), 355, [("fk", 90, 90, 45), ("fk", 90, 90, 45)], [("rel", (10, 20), 1)])],
        escena=[("line", 112, 132, 150, 132, 6), ("line", 112, 132, 106, 92, 5)], pesos=False,
        nota="Extiende la rodilla, pausa y baja controlado")
    P["curl_femoral"] = dict(
        keys=[_pose((150, 146), 270, [("fk", 90, 90, 45), ("fk", 90, 90, 45)], [("rel", (-14, 12), 1)]),
              _pose((150, 146), 270, [("fk", 90, 15, 45), ("fk", 90, 15, 45)], [("rel", (-14, 12), 1)])],
        escena=[("line", 60, 153, 172, 153, 6)], pesos=False,
        nota="Flexiona la rodilla y baja lento")
    P["cardio"] = dict(
        keys=[_pose((120, 88), 8, [("ik", (142, 140), -1, 90), ("ik", (94, 150), -1, 130)],
                    [("rel", (-16, 18), 1), ("rel", (16, -6), 1)]),
              _pose((120, 84), 8, [("ik", (94, 150), -1, 130), ("ik", (142, 140), -1, 90)],
                    [("rel", (16, -6), 1), ("rel", (-16, 18), 1)])],
        pesos=False, nota="Ritmo constante, respiración controlada")
    P["press_plano"] = dict(
        keys=[_pose((150, 112), 270, [("ik", (196, 158), -1, 90), ("ik", (202, 158), -1, 90)], [("fk", 150, 0)]),
              _pose((150, 112), 270, [("ik", (196, 158), -1, 90), ("ik", (202, 158), -1, 90)], [("fk", 0, 0)])],
        escena=_BANCO, nota="Baja al pecho con control y empuja hacia arriba")
    P["press_inclinado"] = dict(
        keys=[_pose((150, 126), 310, [("ik", (192, 158), -1, 90), ("ik", (198, 158), -1, 90)], [("fk", 150, 0)]),
              _pose((150, 126), 310, [("ik", (192, 158), -1, 90), ("ik", (198, 158), -1, 90)], [("fk", 0, 0)])],
        escena=[("line", 152, 134, 104, 92, 7), ("line", 152, 134, 178, 134, 6), ("line", 165, 136, 165, 164, 4)],
        nota="Banco inclinado: baja a la parte alta del pecho")
    P["press_hombro"] = dict(
        keys=[_pose((112, 87), 0, _PIES, [("fk", 150, 0)]),
              _pose((112, 87), 0, _PIES, [("fk", 5, 0)])],
        nota="Empuja sobre la cabeza sin arquear la espalda")
    P["jalon"] = dict(
        keys=[_pose((140, 128), 355, [("ik", (176, 161), -1, 90), ("ik", (182, 161), -1, 90)], [("rel", (8, -48), 1)]),
              _pose((140, 128), 355, [("ik", (176, 161), -1, 90), ("ik", (182, 161), -1, 90)], [("rel", (20, 10), 1)])],
        escena=[("line", 118, 134, 168, 134, 6), ("line", 118, 134, 110, 96, 5)], cable=(146, -30),
        nota="Lleva la barra al pecho apretando los dorsales")
    P["remo"] = dict(
        keys=[_pose((100, 100), 75, _PIES, [("rel", (0, 48), 1)]),
              _pose((100, 100), 75, _PIES, [("rel", (-22, 26), 1)])],
        nota="Espalda neutra; lleva el codo hacia la cadera")
    P["remo_polea"] = dict(
        keys=[_pose((112, 128), 15, [("ik", (180, 152), -1, 90), ("ik", (186, 152), -1, 90)], [("rel", (44, 10), 1)]),
              _pose((112, 128), -5, [("ik", (180, 152), -1, 90), ("ik", (186, 152), -1, 90)], [("rel", (10, 26), 1)])],
        escena=[("line", 90, 134, 125, 134, 6), ("line", 192, 112, 192, 164, 5)], cable=(268, 94),
        nota="Junta los omóplatos y regresa lento")
    P["curl"] = dict(
        keys=[_pose((112, 87), 0, _PIES, [("fk", 185, 178)]),
              _pose((112, 87), 0, _PIES, [("fk", 185, 25)])],
        nota="Codos pegados al cuerpo, sin balanceo")
    P["triceps_polea"] = dict(
        keys=[_pose((112, 87), 0, _PIES, [("fk", 180, 80)]),
              _pose((112, 87), 0, _PIES, [("fk", 180, 180)])],
        cable=(150, -20), nota="Codos fijos; extiende por completo")
    P["fondos"] = dict(
        keys=[_pose((110, 120), 0, [("ik", (186, 161), -1, 90), ("ik", (190, 161), -1, 90)], [("ik", (92, 116), 1)]),
              _pose((110, 150), 0, [("ik", (186, 161), -1, 90), ("ik", (190, 161), -1, 90)], [("ik", (92, 116), 1)])],
        escena=[("line", 40, 121, 100, 121, 7), ("line", 50, 124, 50, 164, 4), ("line", 92, 124, 92, 164, 4)],
        pesos=False, nota="Baja doblando los codos hacia atrás y empuja")
    P["flexion"] = dict(
        keys=[_plank_top([("ik", _PLANK_ANK, -1, 90), ("ik", (209, 161), -1, 90)]),
              _pose((129.4, 153.1), -84, [("ik", _PLANK_ANK, -1, 90), ("ik", (209, 161), -1, 90)],
                    [("ik", (86, 161), 1), ("ik", (90, 161), 1)])],
        pesos=False, nota="Cuerpo en línea recta; baja el pecho cerca del piso")
    P["plancha"] = dict(
        keys=[_pose((131.4, 141.7), -75.3, [("ik", _PLANK_ANK, -1, 90), ("ik", (209, 161), -1, 90)],
                    [("ik", (108, 161), 1), ("ik", (112, 161), 1)])],
        pesos=False, nota="Mantén la posición: abdomen y glúteos firmes")
    P["mountain"] = dict(
        keys=[_plank_top([("ik", _PLANK_ANK, -1, 90), ("ik", (209, 161), -1, 90)]),
              _plank_top([("ik", _PLANK_ANK, -1, 90), ("ik", (118, 150), 1, 90)]),
              _plank_top([("ik", _PLANK_ANK, -1, 90), ("ik", (209, 161), -1, 90)]),
              _plank_top([("ik", (118, 150), 1, 90), ("ik", (209, 161), -1, 90)])],
        pesos=False, nota="Rodillas al pecho alternando, a ritmo constante")
    P["burpee"] = dict(
        keys=[_pose((120, 87), 0, _PIES, [("ik", (122, 85), 1)]),
              _pose((92, 125), 60, _PIES, [("ik", (160, 161), 1)]),
              _plank_top([("ik", _PLANK_ANK, -1, 90), ("ik", (209, 161), -1, 90)]),
              _pose((92, 125), 60, _PIES, [("ik", (160, 161), 1)]),
              _pose((120, 70), 0, [("ik", (118, 150), -1, 90), ("ik", (122, 150), -1, 90)], [("ik", (124, -26), 1)])],
        pesos=False, nota="Agáchate, plancha, regresa y salta")
    P["press_frances"] = dict(
        keys=[_pose((150, 112), 270, [("ik", (196, 158), -1, 90), ("ik", (202, 158), -1, 90)], [("fk", 0, 0)]),
              _pose((150, 112), 270, [("ik", (196, 158), -1, 90), ("ik", (202, 158), -1, 90)], [("fk", 0, -110)])],
        escena=_BANCO, nota="Codos fijos: baja la barra hacia la frente y extiende")
    P["patada_gluteo"] = dict(
        keys=[_pose((160, 122), 270, [("fk", 160, 100, 90), ("fk", 180, 95, 90)], [("ik", (112, 161), 1)]),
              _pose((160, 122), 270, [("fk", 75, 75, 60), ("fk", 180, 95, 90)], [("ik", (112, 161), 1)])],
        pesos=False, nota="Empuja el talón atrás y arriba; aprieta el glúteo")
    P["elev_frontal"] = dict(
        keys=[_pose((112, 87), 0, _PIES, [("fk", 180, 180)]),
              _pose((112, 87), 0, _PIES, [("fk", 100, 100)])],
        nota="Sube al frente hasta el hombro sin balancearte")
    P["ext_cabeza"] = dict(
        keys=[_pose((112, 87), 0, _PIES, [("fk", 3, -160)]),
              _pose((112, 87), 0, _PIES, [("fk", 3, 5)])],
        nota="Codo junto a la cabeza: extiende y baja detrás")
    # Vista frontal
    P["laterales"] = dict(frontal=True, nota="Sube hasta la altura de los hombros",
                          keys=[dict(hl=(118, 94), hr=(162, 94)), dict(hl=(72, 48), hr=(208, 48))])
    P["pajaros"] = dict(frontal=True, nota="Torso inclinado: abre los brazos como alas",
                        keys=[dict(sd=26, hd=30, hl=(118, 118), hr=(162, 118)),
                              dict(sd=26, hd=30, hl=(72, 72), hr=(208, 72))])
    P["aperturas"] = dict(frontal=True, nota="Abre con control y junta frente al pecho",
                          keys=[dict(hl=(74, 56), hr=(206, 56)), dict(hl=(136, 62), hr=(144, 62))])
    P["encogimientos"] = dict(frontal=True, nota="Sube los hombros hacia las orejas y pausa",
                              keys=[dict(hl=(116, 94), hr=(164, 94)), dict(sd=-9, hl=(116, 85), hr=(164, 85))])
    for d in P.values():                       # vista frontal: mismas claves en todos los cuadros
        if d.get("frontal"):
            d["keys"] = [{"sd": 0, "hd": 0, **k} for k in d["keys"]]
    return P


_PATRONES = _patrones()

# Palabras clave (en minúsculas) -> patrón. Se evalúa en orden.
_REGLAS = [
    ("femoral", "curl_femoral"), ("curl", "curl"),
    ("mountain", "mountain"), ("burpee", "burpee"), ("plancha", "plancha"),
    ("flexion", "flexion"), ("fondos", "fondos"), ("tríceps en polea", "triceps_polea"),
    ("aperturas", "aperturas"), ("pájaros", "pajaros"), ("laterales", "laterales"),
    ("encogimientos", "encogimientos"), ("press inclinado", "press_inclinado"),
    ("press militar", "press_hombro"), ("press de hombro", "press_hombro"),
    ("press de banca", "press_plano"), ("press con mancuernas", "press_plano"),
    ("prensa", "prensa"), ("sentadilla b", "zancada"), ("zancada", "zancada"),
    ("sentadilla", "sentadilla"), ("peso muerto", "peso_muerto"),
    ("hip thrust", "puente"), ("puente", "puente"), ("talones", "talones"),
    ("extensión de cuádriceps", "ext_cuad"), ("elevación de piernas", "elev_piernas"),
    ("crunch", "crunch"), ("jalón", "jalon"), ("dominadas", "jalon"),
    ("remo", "remo"), ("cardio", "cardio"), ("hiit", "cardio"), ("caminata", "cardio"),
    ("superserie", "curl"), ("extensión de tríceps", "triceps_polea"),
]


_REGLAS_PRIMERO = [
    ("press francés", "press_frances"), ("sobre la cabeza", "ext_cabeza"), ("elevaciones frontales", "elev_frontal"),
    ("patada de glúteo", "patada_gluteo"), ("remo en máquina", "remo_polea"), ("face pull", "remo_polea"),
    ("press arnold", "press_hombro"),
]
_REGLAS_FINAL = [
    ("press declinado", "press_plano"), ("press en máquina", "press_plano"), ("buenos días", "peso_muerto"),
    ("step-up", "zancada"), ("russian twist", "crunch"), ("rodillas al pecho", "elev_piernas"),
    ("swing", "peso_muerto"), ("thruster", "sentadilla"), ("bicicleta", "cardio"), ("trote", "cardio"),
    ("elíptica", "cardio"), ("cuerda", "cardio"), ("escalera", "cardio"),
]
_REGLAS = _REGLAS_PRIMERO + _REGLAS + _REGLAS_FINAL


def patron_ejercicio(nombre):
    n = nombre.lower()
    if "remo" in n and "polea" in n:
        return "remo_polea"
    if "tríceps" in n and "polea" in n:
        return "triceps_polea"
    for clave, pat in _REGLAS:
        if clave in n and pat:
            return pat
    return None


@lru_cache(maxsize=64)
def svg_ejercicio(nombre):
    """SVG animado del movimiento (cadena que empieza con '<svg'), o None si no hay ilustración."""
    pat = patron_ejercicio(nombre)
    if not pat:
        return None
    d = _PATRONES[pat]
    if d.get("frontal"):
        return _svg_frontal(nombre, d["keys"], True, 2.6, d.get("nota", ""))
    return _svg_lateral(nombre, d["keys"], d.get("escena", []), d.get("pesos", True),
                        d.get("cable"), 2.6, d.get("nota", ""))


# ---------------------------------------------------------
# Respaldo completo: perfil + plan + progreso (descargar / cargar)
# ---------------------------------------------------------
MODOS = ["🐻 Modo Oso", "🐻‍❄️ Modo Osita", "👩‍❤️‍👨 Entrenamiento en pareja"]
NOMBRES = ("Oso", "Osita")
CAMPOS_FORM = {"edad": "edad", "peso": "peso", "estatura": "est", "sexo": "sexo",
               "actividad": "act", "objetivo": "obj", "dias": "dias"}


def kf(prefijo, sufijo):
    """Clave de un widget del perfil. Al cargar un respaldo cambia el sufijo para que los widgets
    nazcan con los valores guardados (sin pisar el estado de widgets ya creados)."""
    g = st.session_state.get("perfil_gen", 0)
    return f"{prefijo}_{sufijo}" if g == 0 else f"{prefijo}_{sufijo}_{g}"


def _restaurado():
    return st.session_state.get("_restaurado", {})


def _leer_form(prefijo):
    """Valores actuales del formulario de Oso u Osita (si no se está mostrando, usa lo restaurado)."""
    d = {}
    for campo, suf in CAMPOS_FORM.items():
        k = kf(prefijo, suf)
        if k in st.session_state:
            d[campo] = st.session_state[k]
        elif campo in _restaurado().get(prefijo, {}):
            d[campo] = _restaurado()[prefijo][campo]
    return d


def _num_rutina(n):
    try:
        return max(1, min(5, int(str(st.session_state.get(f"rutina_sel_{n}", "Rutina 1")).split()[-1])))
    except ValueError:
        return 1


def construir_respaldo():
    res = st.session_state.get("resultados") or []
    gen = st.session_state.get("chk_gen", 0)
    checklist, resumen = {}, []
    for r in res:
        n = r["nombre"]
        marcados = []
        for v in range(1, 6):
            for di, dia in enumerate(elegir_rutina(r["objetivo"], r["dias"], v, r["sexo"])):
                for ei, _ in enumerate(dia["ejercicios"]):
                    if f"chk_{n}_{gen}_{v}_{di}_{ei}" in _marcas():
                        marcados.append(f"{v}_{di}_{ei}")
        checklist[n] = marcados
        resumen.append({
            "nombre": n, "objetivo": r["objetivo"], "dias_por_semana": r["dias"],
            "rutina_elegida": f"Rutina {r.get('variante', 1)}",
            "calorias": int(r["calorias"]), "proteina_g": int(r["prot"]),
            "carbohidratos_g": int(r["carbos"]), "grasas_g": int(r["grasa"]),
            "agua_litros": round(r["agua"], 1), "comidas": plan_comidas(r),
            "rutina": [{"dia": d["dia"], "grupos": GRUPOS_DIA.get(d["dia"], []),
                        "ejercicios": d["ejercicios"]} for d in r["rutina"]],
        })
    return {
        "app": "oso_osita_fitness", "version": 3,
        "exportado": datetime.now().isoformat(timespec="seconds"),
        "perfil": {"modo": st.session_state.get(kf("modo", "perfil")),
                   "oso": _leer_form("oso"), "osita": _leer_form("osita")},
        "plan": {"datos": [{k: r[k] for k in ("nombre", "edad", "peso", "estatura", "sexo",
                                               "actividad", "objetivo", "dias")} for r in res],
                 "resumen": resumen},
        "preferencias": {"rutina": {n: _num_rutina(n) for n in NOMBRES},
                         "menu": {n: st.session_state.get(f"menu_sel_{n}", ESTILOS_MENU[0]) for n in NOMBRES}},
        "progreso": {"agua": {"fecha": date.today().isoformat(),
                              "vasos": {n: int(st.session_state.get(f"vasos_{n}", 0)) for n in NOMBRES}},
                     "checklist": checklist},
        "historial": st.session_state["historial"],
    }


def _validar_form(f):
    """Devuelve sólo los campos válidos de un formulario guardado."""
    ok = {}
    if not isinstance(f, dict):
        return ok

    def num(v, lo, hi):
        x = float(v)
        if not (lo <= x <= hi):
            raise ValueError("fuera de rango")
        return x

    for campo, fn in (("edad", lambda v: int(num(v, 12, 90))),
                      ("peso", lambda v: round(num(v, 30, 250), 1)),
                      ("estatura", lambda v: num(v, 120, 230))):
        try:
            ok[campo] = fn(f[campo])
        except (KeyError, TypeError, ValueError):
            pass
    if f.get("sexo") in ["Masculino", "Femenino"]:
        ok["sexo"] = f["sexo"]
    if f.get("actividad") in list(ACTIVIDAD):
        ok["actividad"] = f["actividad"]
    if f.get("objetivo") in [OBJ_MASA, OBJ_DEF]:
        ok["objetivo"] = f["objetivo"]
    if f.get("dias") in [3, 5]:
        ok["dias"] = int(f["dias"])
    return ok


def validar_respaldo(data):
    """Valida el JSON cargado y devuelve lo que se aplicará. Lanza ValueError si no es un respaldo."""
    if not isinstance(data, dict) or not any(k in data for k in ("perfil", "plan", "historial")):
        raise ValueError("estructura inválida")
    perfil = data.get("perfil") if isinstance(data.get("perfil"), dict) else {}
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
    prog = data.get("progreso") if isinstance(data.get("progreso"), dict) else {}

    resultados, vistos = [], set()
    items = plan.get("datos") if isinstance(plan.get("datos"), list) else []
    for it in items[:2]:
        if isinstance(it, dict) and it.get("nombre") in NOMBRES and it["nombre"] not in vistos:
            f = _validar_form(it)
            if len(f) == len(CAMPOS_FORM):
                resultados.append(calcular({"nombre": it["nombre"], **f}))
                vistos.add(it["nombre"])

    agua = {}
    ag = prog.get("agua") if isinstance(prog.get("agua"), dict) else {}
    if ag.get("fecha") == date.today().isoformat() and isinstance(ag.get("vasos"), dict):
        for n in NOMBRES:
            try:
                agua[n] = max(0, min(40, int(ag["vasos"][n])))
            except (KeyError, TypeError, ValueError):
                pass

    chk = prog.get("checklist") if isinstance(prog.get("checklist"), dict) else {}
    checklist = {n: {m for m in map(_parse_marca, chk[n]) if m} for n in NOMBRES
                 if isinstance(chk.get(n), list)}
    pref = data.get("preferencias") if isinstance(data.get("preferencias"), dict) else {}
    rp = pref.get("rutina") if isinstance(pref.get("rutina"), dict) else {}
    mp = pref.get("menu") if isinstance(pref.get("menu"), dict) else {}
    rutina_sel = {}
    for n in NOMBRES:
        try:
            v = int(rp[n])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= v <= 5:
            rutina_sel[n] = v
    return {
        "modo": perfil.get("modo") if perfil.get("modo") in MODOS else None,
        "forms": {p: _validar_form(perfil.get(p)) for p in ("oso", "osita")},
        "resultados": resultados, "agua": agua, "checklist": checklist,
        "rutina": rutina_sel, "menu": {n: mp[n] for n in NOMBRES if mp.get(n) in ESTILOS_MENU},
    }


def _parse_marca(x):
    """'rutina_dia_ejercicio' (o 'dia_ejercicio' de respaldos antiguos = Rutina 1) -> (rutina, dia, ejercicio)."""
    try:
        p = [int(t) for t in str(x).split("_")]
    except ValueError:
        return None
    if len(p) == 2:
        p = [1] + p
    if len(p) != 3 or not (1 <= p[0] <= 5) or p[1] < 0 or p[2] < 0:
        return None
    return tuple(p)


def aplicar_respaldo_pendiente():
    """Se ejecuta ANTES de crear los widgets: deja listos los valores guardados."""
    pend = st.session_state.pop("_pendiente_respaldo", None)
    if not pend:
        return
    forms = {p: f for p, f in pend["forms"].items() if f}
    if forms or pend["modo"] or pend["resultados"]:
        st.session_state["perfil_gen"] = st.session_state.get("perfil_gen", 0) + 1
        st.session_state["_restaurado"] = {**forms, "modo": pend["modo"]}
    for n, v in pend["rutina"].items():
        st.session_state[f"rutina_sel_{n}"] = f"Rutina {v}"
    for n, e in pend["menu"].items():
        st.session_state[f"menu_sel_{n}"] = e
    if pend["resultados"]:
        st.session_state["resultados"] = pend["resultados"]
        limpiar_checklist()
        gen = st.session_state["chk_gen"]
        guardadas = set()
        for r in pend["resultados"]:
            n = r["nombre"]
            marcados = pend["checklist"].get(n, set())
            sel = pend["rutina"].get(n, 1)
            total = hechos = 0
            for v in range(1, 6):
                for di, dia in enumerate(elegir_rutina(r["objetivo"], r["dias"], v, r["sexo"])):
                    for ei, _ in enumerate(dia["ejercicios"]):
                        marcado = (v, di, ei) in marcados
                        if marcado:
                            guardadas.add(f"chk_{n}_{gen}_{v}_{di}_{ei}")
                        if v == sel:
                            total += 1
                            hechos += int(marcado)
            st.session_state[f"celebrado_{n}"] = bool(total and hechos == total)
        st.session_state["_marcas"] = guardadas
    for n, v in pend["agua"].items():
        st.session_state[f"vasos_{n}"] = v


# ---------------------------------------------------------
# Componentes de UI
# ---------------------------------------------------------
def formulario(prefijo, nombre, sexo_def, peso_def, est_def):
    R = _restaurado().get(prefijo, {})
    acts = list(ACTIVIDAD)
    c1, c2 = st.columns(2)
    with c1:
        edad = st.number_input("Edad (años)", 12, 90, int(R.get("edad", 25)), 1, key=kf(prefijo, "edad"))
        peso = st.number_input("Peso (kg)", 30.0, 250.0, float(R.get("peso", peso_def)), 0.5, key=kf(prefijo, "peso"))
    with c2:
        estatura = st.number_input("Estatura (cm)", 120.0, 230.0, float(R.get("estatura", est_def)), 1.0,
                                   key=kf(prefijo, "est"))
        sexo = st.selectbox("Sexo biológico", ["Masculino", "Femenino"],
                            index=0 if R.get("sexo", sexo_def) == "Masculino" else 1, key=kf(prefijo, "sexo"))
    actividad = st.selectbox("🔥 Nivel de actividad física", acts,
                             index=acts.index(R.get("actividad", acts[0])), key=kf(prefijo, "act"))
    objetivo = st.radio("🎯 Objetivo principal", [OBJ_MASA, OBJ_DEF],
                        index=[OBJ_MASA, OBJ_DEF].index(R.get("objetivo", OBJ_MASA)), key=kf(prefijo, "obj"))
    dias = st.radio("📅 Días de entrenamiento por semana", [3, 5], horizontal=True,
                    index=[3, 5].index(R.get("dias", 3)),
                    format_func=lambda x: f"{x} días", key=kf(prefijo, "dias"))
    return {"nombre": nombre, "edad": edad, "peso": peso, "estatura": estatura,
            "sexo": sexo, "actividad": actividad, "objetivo": objetivo, "dias": dias}


def mostrar_ejemplo(nombre):
    """Ilustración animada del ejercicio + enlaces a video e imágenes."""
    try:
        svg = svg_ejercicio(nombre)
    except Exception:
        svg = None
    if svg:
        st.image(svg, width=320)
    else:
        st.caption("No hay ilustración para este ejercicio; usa los enlaces de abajo.")
    b1, b2 = st.columns(2)
    b1.link_button("🎥 Ver video",
                   "https://www.youtube.com/results?search_query=" + quote_plus(f"cómo hacer {nombre} técnica correcta"),
                   use_container_width=True)
    b2.link_button("🖼️ Ver imágenes",
                   "https://www.google.com/search?tbm=isch&q=" + quote_plus(f"{nombre} ejercicio"),
                   use_container_width=True)


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


def _marcas():
    """Ejercicios marcados (se conservan aunque cambies de rutina; los widgets ocultos pierden su estado)."""
    return st.session_state.setdefault("_marcas", set())


def limpiar_checklist():
    """Reinicia el checklist cambiando de 'generación' (las claves nuevas empiezan sin marcar)."""
    st.session_state["chk_gen"] = st.session_state.get("chk_gen", 0) + 1
    st.session_state["_marcas"] = set()
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
aplicar_respaldo_pendiente()

tab_perfil, tab_rutina, tab_comidas, tab_progreso, tab_tools = st.tabs(
    ["📋 Perfil", "🏋️ Rutina", "🍽️ Comidas", "📈 Progreso", "🧰 Herramientas"]
)

# ---- Perfil ----
with tab_perfil:
    _msg = st.session_state.pop("_msg_respaldo", None)
    if _msg:
        st.success(_msg)
    _m = _restaurado().get("modo")
    modo = st.radio(
        "Perfil activo:",
        MODOS,
        index=MODOS.index(_m) if _m in MODOS else 0,
        horizontal=True,
        key=kf("modo", "perfil"),
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
            opciones_rut = [f"Rutina {i}" for i in range(1, 6)]
            elegida = st.selectbox("🔀 Elige tu rutina", opciones_rut, key=f"rutina_sel_{nombre}")
            var = opciones_rut.index(elegida) + 1
            r["rutina"] = elegir_rutina(r["objetivo"], r["dias"], var, r["sexo"])
            r["variante"] = var
            st.caption("Rutina base de tu plan." if var == 1 else
                       f"{elegida}: ejercicios distintos con el mismo enfoque muscular por día.")
            barra = st.empty()
            hechos = total = 0
            for di, dia in enumerate(r["rutina"]):
                with st.expander(f"📌 {dia['dia']}", expanded=len(resultados) == 1):
                    grupos = GRUPOS_DIA.get(dia["dia"])
                    if grupos:
                        st.caption("🎯 Grupos musculares: " + ", ".join(grupos))
                    for ei, ej in enumerate(dia["ejercicios"]):
                        clave = f"chk_{nombre}_{st.session_state.get('chk_gen', 0)}_{var}_{di}_{ei}"
                        marcado = st.checkbox(f"**{ej['nombre']}** · {ej['series_reps']}",
                                              value=clave in _marcas(), key=clave)
                        (_marcas().add if marcado else _marcas().discard)(clave)
                        st.caption(f"💡 {ej['tips']}")
                        if st.toggle("🎬 Ver ejemplo", key=f"ver_{nombre}_{var}_{di}_{ei}"):
                            mostrar_ejemplo(ej["nombre"])
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
            estilo = st.selectbox("🍴 Tipo de menú", ESTILOS_MENU, key=f"menu_sel_{r['nombre']}")
            st.caption(f"Ideas pensadas para: {r['objetivo'].lower()}.")
            for c in plan_comidas(r):
                with st.expander(f"{c['comida']} · {c['kcal']} kcal", expanded=False):
                    a, b, d = st.columns(3)
                    a.metric("Proteína", f"{c['prot']} g")
                    b.metric("Carbos", f"{c['carbos']} g")
                    d.metric("Grasas", f"{c['grasa']} g")
                    for idea in IDEAS_MENU[r["objetivo"]][estilo][c["comida"]]:
                        st.write(f"🥗 {idea}")
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


# ---- Perfil: descargar / cargar historial de progreso (va al final para leer valores ya actualizados) ----
with tab_perfil:
    st.divider()
    st.subheader("💾 Historial de progreso")
    st.caption("Descarga tu historial para no volver a capturar nada: guarda tu perfil, rutina, comidas "
               "y progreso. Al abrir la app, cárgalo y todo queda como lo dejaste.")
    st.download_button(
        "⬇️ Descargar historial de progreso",
        data=json.dumps(construir_respaldo(), ensure_ascii=False, indent=2, default=str),
        file_name=f"historial_progreso_{date.today():%Y-%m-%d}.json",
        mime="application/json",
        use_container_width=True,
        key="dl_respaldo",
    )
    subido_resp = st.file_uploader("⬆️ Cargar historial de progreso", type=["json"], key="subir_respaldo")
    if subido_resp is None:
        st.session_state.pop("_ultimo_respaldo", None)
    else:
        marca_resp = f"{subido_resp.name}-{subido_resp.size}"
        if st.session_state.get("_ultimo_respaldo") != marca_resp:
            pend_ok, n_hist = None, 0
            try:
                texto_resp = subido_resp.getvalue().decode("utf-8")
                pend_ok = validar_respaldo(json.loads(texto_resp))
                n_hist = importar_historial(texto_resp)
            except Exception:
                pend_ok = None
                st.error("El archivo no es un historial de progreso válido.")
            if pend_ok is not None:
                partes = []
                if pend_ok["modo"] or any(pend_ok["forms"].values()):
                    partes.append("perfil")
                if pend_ok["resultados"]:
                    partes.append("rutina, comidas y checklist")
                if n_hist:
                    partes.append(f"{n_hist} registros de peso")
                st.session_state["_pendiente_respaldo"] = pend_ok
                st.session_state["_ultimo_respaldo"] = marca_resp
                st.session_state["_msg_respaldo"] = "✅ Historial cargado: " + (", ".join(partes) or "sin datos nuevos") + "."
                st.rerun()
