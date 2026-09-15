## Tablero interactivo SECOP II - SENA

# Importacion de librerias

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

import dash
from dash import dcc, html, Input, Output, State, ctx


# ---------------------------------------------------------------------------
# 1. Carga y preparacion de datos (una sola vez, al arrancar la app)
# ---------------------------------------------------------------------------

RUTA_CSV = "datos_limpios.csv"  # debe estar en la misma carpeta que este archivo

df = pd.read_csv(RUTA_CSV)
df["fecha_de_firma"] = pd.to_datetime(df["fecha_de_firma"], errors="coerce")


# Universo de negocio:
# contratacion individual de prestacion de servicios

dfb = df[df["es_contratacion_individual"] == True].copy()


NOMBRES_MES = {
    1: "Ene",
    2: "Feb",
    3: "Mar",
    4: "Abr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dic",
}

ORDEN_MESES = [NOMBRES_MES[m] for m in range(1, 13)]


dfb["nombre_mes"] = dfb["mes_firma"].map(NOMBRES_MES)
dfb["trimestre"] = ((dfb["mes_firma"] - 1) // 3 + 1)


TOTAL_NEGOCIO = dfb.shape[0]

CONTEO_REGIONAL_TOTAL = dfb["regional"].value_counts()
TODAS_REGIONALES = CONTEO_REGIONAL_TOTAL.index.tolist()
TOP8_DEFAULT = CONTEO_REGIONAL_TOTAL.head(8).index.tolist()


# ---------------------------------------------------------------------------
# Preparacion especifica de la Pregunta 2
# Recurrencia de proveedores y prorrogas
# ---------------------------------------------------------------------------

# Se conserva la misma logica del notebook analisis_pregunta2.ipynb,
# que trabaja sobre los 328.057 registros del SENA.

df["año"] = df["fecha_de_firma"].dt.year

df["dias_adicionados"] = pd.to_numeric(
    df["dias_adicionados"],
    errors="coerce",
)

df["tuvo_prorroga"] = (
    df["dias_adicionados"].fillna(0) > 0
)

TODAS_REGIONALES_P2 = sorted(
    df["regional"]
    .dropna()
    .unique()
    .tolist()
)


# ---------------------------------------------------------------------------
# KPIs fijos de la Pregunta 3
# ---------------------------------------------------------------------------

pct_ene_feb = round(
    dfb[dfb["mes_firma"].isin([1, 2])].shape[0]
    / TOTAL_NEGOCIO
    * 100,
    1,
)


tabla_chi = (
    dfb[dfb["regional"].isin(TOP8_DEFAULT)]
    .pivot_table(
        index="regional",
        columns="nombre_mes",
        values="id_contrato",
        aggfunc="count",
        fill_value=0,
    )
    .reindex(columns=ORDEN_MESES)
)


chi2, p_valor, gl, _ = stats.chi2_contingency(tabla_chi)


# ---------------------------------------------------------------------------
# Preparacion especifica de la Pregunta 1
# Tamano y concentracion del gasto
# ---------------------------------------------------------------------------

# Misma logica que analisis_pregunta1.ipynb:
# se excluyen los registros monetarios extremos
# (> $10.000 millones)
# unicamente para los calculos de valor contratado.

LIMITE_VALOR_EXTREMO = 10_000_000_000


DESCRIPCIONES_UNSPSC = {
    "80111600": "Servicios de personal temporal",
    "86101710": "Servicios de formación pedagógica",
    "80111601": "Asistencia de oficina o administrativa temporal",
    "80111620": "Servicios temporales de recursos humanos",
    "80111701": "Servicios de contratación de personal",
    "86101700": "Servicios de capacitación vocacional no científica",
    "80111504": "Formación o desarrollo laboral",
    "86101810": "Capacitación en habilidades personales",
    "85122200": "Servicios de evaluación y valoración de salud individual",
    "80161504": "Servicios de oficina",
    "80111621": "Servicios temporales de investigación y desarrollo",
    "80111607": "Necesidades de dotación de personal jurídico temporal",
    "80161500": "Servicios de apoyo gerencial",
    "86101800": "Entrenamiento en servicio y desarrollo de mano de obra",
    "93151507": "Procedimientos o servicios administrativos",
    "80101505": "Desarrollo de políticas u objetivos empresariales",
    "80111700": "Reclutamiento de personal",
    "86101705": "Capacitación administrativa",
}


dfb["unspsc"] = (
    pd.to_numeric(dfb["unspsc"], errors="coerce")
    .astype("Int64")
    .astype("string")
)


dfb["categoria_unspsc"] = dfb["unspsc"].fillna("Sin código UNSPSC")


dfb["descripcion_unspsc"] = (
    dfb["categoria_unspsc"]
    .map(DESCRIPCIONES_UNSPSC)
    .fillna("Otra categoría")
)


dfb["etiqueta_unspsc"] = (
    dfb["categoria_unspsc"].astype(str)
    + " - "
    + dfb["descripcion_unspsc"]
)


df_p1 = dfb[
    dfb["valor_del_contrato"] <= LIMITE_VALOR_EXTREMO
].copy()


N_EXTREMOS_EXCLUIDOS = dfb.shape[0] - df_p1.shape[0]


AÑOS_DISPONIBLES = sorted(
    df_p1["anio_firma"]
    .dropna()
    .unique()
    .tolist()
)


TOP8_UNSPSC_DEFAULT = (
    df_p1
    .groupby("etiqueta_unspsc")["valor_del_contrato"]
    .sum()
    .sort_values(ascending=False)
    .head(8)
    .index
    .tolist()
)


# ---------------------------------------------------------------------------
# KPIs globales Pregunta 1
# ---------------------------------------------------------------------------

GASTO_TOTAL_P1 = df_p1["valor_del_contrato"].sum()

CONTRATOS_TOTAL_P1 = df_p1["id_contrato"].nunique()

PERSONAS_TOTAL_P1 = df_p1["documento_proveedor"].nunique()

MEDIANA_TOTAL_P1 = df_p1["valor_del_contrato"].median()


_gasto_unspsc_global = (
    df_p1
    .groupby("etiqueta_unspsc")["valor_del_contrato"]
    .sum()
    .sort_values(ascending=False)
)


PCT_TOP5_UNSPSC = (
    _gasto_unspsc_global.head(5).sum()
    / GASTO_TOTAL_P1
    * 100
)


_gasto_regional_global = (
    df_p1
    .groupby("regional")["valor_del_contrato"]
    .sum()
    .sort_values(ascending=False)
)


PCT_TOP5_REGIONAL = (
    _gasto_regional_global.head(5).sum()
    / GASTO_TOTAL_P1
    * 100
)


# ---------------------------------------------------------------------------
# 2. App, colores institucionales y helpers de estilo
# ---------------------------------------------------------------------------

SENA_GREEN = "#87A995"
SENA_GREEN_DARK = "#5E7F6C"
SENA_ORANGE = "#D8A47F"

CARD_BG = "#FFFFFF"

TEXT_LIGHT = "#2D3832"
TEXT_MUTED = "#738078"

GREEN_SCALE = [
    "#F4F8F5",
    "#E8F0EA",
    "#D6E5DA",
    "#BED5C4",
    "#A3C1AB",
    "#87A995",
]


# ---------------------------------------------------------------------------
# Hoja de estilos usada en los ejemplos de clase
# ---------------------------------------------------------------------------

external_stylesheets = [
    "https://codepen.io/chriddyp/pen/bWLwgP.css"
]


app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
)

app.title = "Tablero SECOP II - SENA"

server = app.server


# ---------------------------------------------------------------------------
# Helpers de estilo
# ---------------------------------------------------------------------------

def kpi_card(
    titulo,
    valor,
    accent=SENA_GREEN,
    card_id=None,
):

    kwargs = {}

    if card_id is not None:
        kwargs["id"] = card_id

    return html.Div(
        [
            html.P(
                titulo,
                className="kpi-label",
            ),

            html.H3(
                valor,
                className="kpi-value",
            ),
        ],

        className="kpi-card",

        style={
            "--accent": accent
        },

        **kwargs,
    )


def estilizar_figura(
    fig,
    altura=340,
):

    fig.update_layout(
        template="plotly_white",

        paper_bgcolor="rgba(0,0,0,0)",

        plot_bgcolor="rgba(0,0,0,0)",

        font_color=TEXT_LIGHT,

        title_font_size=14,

        margin=dict(
            l=10,
            r=10,
            t=45,
            b=10,
        ),

        height=altura,
    )

    fig.update_xaxes(
        gridcolor="#DDE5DF"
    )

    fig.update_yaxes(
        gridcolor="#DDE5DF"
    )

    return fig


DROPDOWN_STYLE = {
    "color": "#0b0b0b"
}


# ---------------------------------------------------------------------------
# 3. Seccion Pregunta 1
# Tamano y concentracion del gasto
# ---------------------------------------------------------------------------

seccion_p1 = html.Div([

    html.Div([

        kpi_card(
            "Valor contratado (filtro)",
            "",
            accent=SENA_GREEN,
            card_id="kpi-valor-p1",
        ),

        kpi_card(
            "Contratos",
            "",
            accent=SENA_ORANGE,
            card_id="kpi-contratos-p1",
        ),

        kpi_card(
            "Personas",
            "",
            accent=SENA_ORANGE,
            card_id="kpi-personas-p1",
        ),

        kpi_card(
            "Valor mediano",
            "",
            accent=SENA_GREEN,
            card_id="kpi-mediana-p1",
        ),

    ], className="kpi-row"),


    html.Div([

        html.Div([

            html.Label(
                "Año de firma"
            ),

            dcc.Dropdown(
                id="filtro-anio-p1",

                options=[
                    {
                        "label": str(int(a)),
                        "value": a,
                    }
                    for a in AÑOS_DISPONIBLES
                ],

                value=[],

                multi=True,

                placeholder="Todos los años",
            ),

        ], className="filter-col"),


        html.Div([

            html.Label(
                "Regional"
            ),

            dcc.Dropdown(
                id="filtro-regional-p1",

                options=[
                    {
                        "label": r,
                        "value": r,
                    }
                    for r in TODAS_REGIONALES
                ],

                value=[],

                multi=True,

                placeholder="Todas las regionales",
            ),

        ], className="filter-col"),


        html.Div([

            html.Label(
                "Categoría UNSPSC"
            ),

            dcc.Dropdown(
                id="filtro-unspsc-p1",

                options=[
                    {
                        "label": u,
                        "value": u,
                    }
                    for u in sorted(
                        dfb["etiqueta_unspsc"].unique()
                    )
                ],

                value=[],

                multi=True,

                placeholder="Todas las categorías",
            ),

        ], className="filter-col"),

    ], className="filter-panel"),


    html.Div([

        html.Div(
            dcc.Graph(
                id="grafico-unspsc-p1",

                config={
                    "displayModeBar": False
                },
            ),

            className="chart-card",
        ),


        html.Div(
            dcc.Graph(
                id="grafico-regional-p1",

                config={
                    "displayModeBar": False
                },
            ),

            className="chart-card",
        ),

    ], className="charts-row"),


    html.Div(
        id="texto-hallazgo-p1",

        className="insight-box",
    ),

])


@app.callback(
    Output(
        "kpi-valor-p1",
        "children",
    ),

    Output(
        "kpi-contratos-p1",
        "children",
    ),

    Output(
        "kpi-personas-p1",
        "children",
    ),

    Output(
        "kpi-mediana-p1",
        "children",
    ),

    Output(
        "grafico-unspsc-p1",
        "figure",
    ),

    Output(
        "grafico-regional-p1",
        "figure",
    ),

    Output(
        "texto-hallazgo-p1",
        "children",
    ),

    Input(
        "filtro-anio-p1",
        "value",
    ),

    Input(
        "filtro-regional-p1",
        "value",
    ),

    Input(
        "filtro-unspsc-p1",
        "value",
    ),
)

def actualizar_pregunta1(
    anios_sel,
    regionales_sel,
    unspsc_sel,
):

    d = df_p1


    if anios_sel:
        d = d[
            d["anio_firma"].isin(anios_sel)
        ]


    if regionales_sel:
        d = d[
            d["regional"].isin(regionales_sel)
        ]


    if unspsc_sel:
        d = d[
            d["etiqueta_unspsc"].isin(unspsc_sel)
        ]


    if d.empty:

        vacio = estilizar_figura(
            go.Figure().update_layout(
                title="Sin datos para esta selección"
            )
        )

        return (
            [
                html.P(
                    "Valor contratado (filtro)",
                    className="kpi-label",
                ),

                html.H3(
                    "$0",
                    className="kpi-value",
                ),
            ],

            [
                html.P(
                    "Contratos",
                    className="kpi-label",
                ),

                html.H3(
                    "0",
                    className="kpi-value",
                ),
            ],

            [
                html.P(
                    "Personas",
                    className="kpi-label",
                ),

                html.H3(
                    "0",
                    className="kpi-value",
                ),
            ],

            [
                html.P(
                    "Valor mediano",
                    className="kpi-label",
                ),

                html.H3(
                    "$0",
                    className="kpi-value",
                ),
            ],

            vacio,

            vacio,

            "No hay contratos que cumplan los filtros seleccionados.",
        )


    gasto_f = d["valor_del_contrato"].sum()

    contratos_f = d["id_contrato"].nunique()

    personas_f = d["documento_proveedor"].nunique()

    mediana_f = d["valor_del_contrato"].median()


    kpis = [

        [
            html.P(
                "Valor contratado (filtro)",
                className="kpi-label",
            ),

            html.H3(
                f"${gasto_f / 1_000_000_000_000:,.2f} B",
                className="kpi-value",
            ),
        ],


        [
            html.P(
                "Contratos",
                className="kpi-label",
            ),

            html.H3(
                f"{contratos_f:,}",
                className="kpi-value",
            ),
        ],


        [
            html.P(
                "Personas",
                className="kpi-label",
            ),

            html.H3(
                f"{personas_f:,}",
                className="kpi-value",
            ),
        ],


        [
            html.P(
                "Valor mediano",
                className="kpi-label",
            ),

            html.H3(
                f"${mediana_f / 1_000_000:,.1f} M",
                className="kpi-value",
            ),
        ],

    ]


    gasto_unspsc = (
        d
        .groupby("etiqueta_unspsc")["valor_del_contrato"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .sort_values()
    )


    fig_unspsc = px.bar(
        gasto_unspsc,

        x=(
            gasto_unspsc.values
            / 1_000_000_000_000
        ),

        y=gasto_unspsc.index,

        orientation="h",

        labels={
            "x": "Valor contratado (billones)",
            "y": "",
        },

        title=(
            "Concentración del valor contratado "
            "por categoría UNSPSC"
        ),
    )


    fig_unspsc.update_traces(
        marker_color=SENA_GREEN
    )


    estilizar_figura(
        fig_unspsc
    )


    gasto_regional = (
        d
        .groupby("regional")["valor_del_contrato"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .sort_values()
    )


    fig_regional = px.bar(
        gasto_regional,

        x=(
            gasto_regional.values
            / 1_000_000_000_000
        ),

        y=gasto_regional.index,

        orientation="h",

        labels={
            "x": "Valor contratado (billones)",
            "y": "",
        },

        title=(
            "Concentración del valor contratado "
            "por regional"
        ),
    )


    fig_regional.update_traces(
        marker_color=SENA_ORANGE
    )


    estilizar_figura(
        fig_regional
    )


    texto = (
        f"Con la selección actual: "
        f"${gasto_f / 1_000_000_000_000:,.2f} billones "
        f"en {contratos_f:,} contratos con {personas_f:,} personas "
        f"(valor mediano ${mediana_f / 1_000_000:,.1f} millones). "

        f"A nivel global "
        f"(excluyendo {N_EXTREMOS_EXCLUIDOS} registros monetarios extremos), "
        f"las 5 principales categorías UNSPSC concentran "
        f"{PCT_TOP5_UNSPSC:.1f}% del valor contratado y las 5 "
        f"principales regionales {PCT_TOP5_REGIONAL:.1f}%. "

        f"La concentración es mucho mayor por tipo de servicio "
        f"que por regional. "

        f"Kruskal-Wallis entre las 5 regionales de mayor valor "
        f"confirma diferencias significativas en la distribución "
        f"del valor del contrato (p < 0.001)."
    )


    return (
        *kpis,
        fig_unspsc,
        fig_regional,
        texto,
    )


# ---------------------------------------------------------------------------
# 4. Seccion Pregunta 2
# Recurrencia y estabilidad
# ---------------------------------------------------------------------------

seccion_p2 = html.Div([

    html.Div([

        kpi_card(
            "Proveedores",
            "",
            accent=SENA_GREEN,
            card_id="kpi-proveedores-p2",
        ),

        kpi_card(
            "Proveedores recurrentes",
            "",
            accent=SENA_ORANGE,
            card_id="kpi-recurrentes-p2",
        ),

        kpi_card(
            "Contratados en 2 o más años",
            "",
            accent=SENA_GREEN,
            card_id="kpi-anios-p2",
        ),

        kpi_card(
            "Contratos con prórroga",
            "",
            accent=SENA_ORANGE,
            card_id="kpi-prorrogas-p2",
        ),

    ], className="kpi-row"),


    html.Div([

        html.Div([

            html.Label(
                "Regional"
            ),

            dcc.Dropdown(
                id="filtro-regional-p2",

                options=[
                    {
                        "label": r,
                        "value": r,
                    }
                    for r in TODAS_REGIONALES_P2
                ],

                value=[],

                multi=True,

                placeholder="Todas las regionales",
            ),

        ],

        className="filter-col",

        style={
            "flexBasis": "100%"
        }),

    ], className="filter-panel"),


    html.Div([

        html.Div(
            dcc.Graph(
                id="grafico-recurrencia-p2",

                config={
                    "displayModeBar": False
                },
            ),

            className="chart-card",
        ),


        html.Div(
            dcc.Graph(
                id="grafico-prorrogas-p2",

                config={
                    "displayModeBar": False
                },
            ),

            className="chart-card",
        ),

    ], className="charts-row"),


    html.Div([

        html.Div(
            dcc.Graph(
                id="grafico-anios-p2",

                config={
                    "displayModeBar": False
                },
            ),

            className="chart-card full-width",
        ),

    ], className="charts-row"),


    html.Div(
        id="texto-hallazgo-p2",

        className="insight-box",
    ),

])


@app.callback(

    Output(
        "kpi-proveedores-p2",
        "children",
    ),

    Output(
        "kpi-recurrentes-p2",
        "children",
    ),

    Output(
        "kpi-anios-p2",
        "children",
    ),

    Output(
        "kpi-prorrogas-p2",
        "children",
    ),

    Output(
        "grafico-recurrencia-p2",
        "figure",
    ),

    Output(
        "grafico-prorrogas-p2",
        "figure",
    ),

    Output(
        "grafico-anios-p2",
        "figure",
    ),

    Output(
        "texto-hallazgo-p2",
        "children",
    ),

    Input(
        "filtro-regional-p2",
        "value",
    ),
)

def actualizar_pregunta2(
    regionales_sel,
):

    d = df.copy()


    if regionales_sel:

        d = d[
            d[
                "regional"
            ].isin(
                regionales_sel
            )
        ]


    if d.empty:

        vacio = estilizar_figura(
            go.Figure().update_layout(
                title="Sin datos para esta selección"
            )
        )

        return (

            [
                html.P(
                    "Proveedores",
                    className="kpi-label",
                ),

                html.H3(
                    "0",
                    className="kpi-value",
                ),
            ],

            [
                html.P(
                    "Proveedores recurrentes",
                    className="kpi-label",
                ),

                html.H3(
                    "0%",
                    className="kpi-value",
                ),
            ],

            [
                html.P(
                    "Contratados en 2 o más años",
                    className="kpi-label",
                ),

                html.H3(
                    "0%",
                    className="kpi-value",
                ),
            ],

            [
                html.P(
                    "Contratos con prórroga",
                    className="kpi-label",
                ),

                html.H3(
                    "0%",
                    className="kpi-value",
                ),
            ],

            vacio,
            vacio,
            vacio,

            "No hay contratos que cumplan los filtros seleccionados.",
        )


    contratos_por_proveedor = (

        d

        .groupby(
            "documento_proveedor"
        )[
            "id_contrato"
        ]

        .nunique()

        .reset_index(
            name="numero_contratos"
        )

    )


    total_proveedores = len(
        contratos_por_proveedor
    )


    proveedores_recurrentes = (
        contratos_por_proveedor[
            "numero_contratos"
        ]
        .ge(2)
        .sum()
    )


    porcentaje_recurrentes = (
        proveedores_recurrentes
        / total_proveedores
        * 100
    )


    anios_por_proveedor = (

        d

        .groupby(
            "documento_proveedor"
        )[
            "año"
        ]

        .nunique()

        .reset_index(
            name="numero_años"
        )

    )


    proveedores_varios_anios = (
        anios_por_proveedor[
            "numero_años"
        ]
        .ge(2)
        .sum()
    )


    porcentaje_varios_anios = (
        proveedores_varios_anios
        / total_proveedores
        * 100
    )


    total_contratos = (
        d[
            "id_contrato"
        ]
        .nunique()
    )


    contratos_prorrogados = (
        d.loc[
            d[
                "tuvo_prorroga"
            ],
            "id_contrato"
        ]
        .nunique()
    )


    porcentaje_prorrogados = (
        contratos_prorrogados
        / total_contratos
        * 100
    )


    dias_prorroga = (
        d.loc[
            d[
                "tuvo_prorroga"
            ],
            "dias_adicionados"
        ]
        .dropna()
    )


    mediana_dias_prorroga = (
        dias_prorroga.median()
        if not dias_prorroga.empty
        else 0
    )


    recurrencia_prorroga = (

        d

        .groupby(
            "documento_proveedor"
        )

        .agg(
            numero_contratos=(
                "id_contrato",
                "nunique"
            ),
            contratos_prorrogados=(
                "tuvo_prorroga",
                "sum"
            ),
        )

        .reset_index()

    )


    def clasificar_recurrencia(n):

        if n == 1:
            return "1 contrato"

        elif n <= 3:
            return "2-3 contratos"

        elif n <= 5:
            return "4-5 contratos"

        elif n <= 10:
            return "6-10 contratos"

        else:
            return "Más de 10 contratos"


    orden_grupos = [
        "1 contrato",
        "2-3 contratos",
        "4-5 contratos",
        "6-10 contratos",
        "Más de 10 contratos",
    ]


    recurrencia_prorroga[
        "grupo_recurrencia"
    ] = (
        recurrencia_prorroga[
            "numero_contratos"
        ]
        .apply(
            clasificar_recurrencia
        )
    )


    proveedores_por_grupo = (

        recurrencia_prorroga[
            "grupo_recurrencia"
        ]

        .value_counts()

        .reindex(
            orden_grupos,
            fill_value=0
        )

        .rename_axis(
            "grupo_recurrencia"
        )

        .reset_index(
            name="numero_proveedores"
        )

    )


    fig_recurrencia = px.bar(

        proveedores_por_grupo,

        x="grupo_recurrencia",

        y="numero_proveedores",

        labels={
            "grupo_recurrencia":
                "Número de contratos",
            "numero_proveedores":
                "Número de proveedores",
        },

        title=(
            "Proveedores según número de contratos"
        ),

        category_orders={
            "grupo_recurrencia":
                orden_grupos
        },

    )


    fig_recurrencia.update_traces(
        marker_color=SENA_GREEN
    )


    estilizar_figura(
        fig_recurrencia
    )


    analisis_recurrencia = (

        recurrencia_prorroga

        .groupby(
            "grupo_recurrencia"
        )

        .agg(
            contratos=(
                "numero_contratos",
                "sum"
            ),
            contratos_prorrogados=(
                "contratos_prorrogados",
                "sum"
            ),
        )

        .reindex(
            orden_grupos
        )

        .fillna(0)

        .reset_index()

    )


    analisis_recurrencia[
        "tasa_prorroga"
    ] = (
        analisis_recurrencia[
            "contratos_prorrogados"
        ]
        / analisis_recurrencia[
            "contratos"
        ]
        .replace(
            0,
            pd.NA
        )
        * 100
    ).fillna(0)


    fig_prorrogas = px.bar(

        analisis_recurrencia,

        x="grupo_recurrencia",

        y="tasa_prorroga",

        labels={
            "grupo_recurrencia":
                "Número de contratos",
            "tasa_prorroga":
                "Contratos prorrogados (%)",
        },

        title=(
            "Tasa de prórroga según recurrencia del proveedor"
        ),

        category_orders={
            "grupo_recurrencia":
                orden_grupos
        },

    )


    fig_prorrogas.update_traces(
        marker_color=SENA_ORANGE
    )


    estilizar_figura(
        fig_prorrogas
    )


    distribucion_anios = (

        anios_por_proveedor[
            "numero_años"
        ]

        .value_counts()

        .sort_index()

        .reset_index()

    )


    distribucion_anios.columns = [
        "numero_años",
        "numero_proveedores",
    ]


    fig_anios = px.bar(

        distribucion_anios,

        x="numero_años",

        y="numero_proveedores",

        labels={
            "numero_años":
                "Número de años diferentes",
            "numero_proveedores":
                "Número de proveedores",
        },

        title=(
            "Proveedores según número de años con contratos"
        ),

    )


    fig_anios.update_traces(
        marker_color=SENA_GREEN_DARK
    )


    estilizar_figura(
        fig_anios,
        altura=330
    )


    kpis = [

        [
            html.P(
                "Proveedores",
                className="kpi-label",
            ),

            html.H3(
                f"{total_proveedores:,}",
                className="kpi-value",
            ),
        ],

        [
            html.P(
                "Proveedores recurrentes",
                className="kpi-label",
            ),

            html.H3(
                f"{porcentaje_recurrentes:.1f}%",
                className="kpi-value",
            ),
        ],

        [
            html.P(
                "Contratados en 2 o más años",
                className="kpi-label",
            ),

            html.H3(
                f"{porcentaje_varios_anios:.1f}%",
                className="kpi-value",
            ),
        ],

        [
            html.P(
                "Contratos con prórroga",
                className="kpi-label",
            ),

            html.H3(
                f"{porcentaje_prorrogados:.2f}%",
                className="kpi-value",
            ),
        ],

    ]


    texto = (

        f"Con la selección actual se observan "
        f"{total_proveedores:,} proveedores. "

        f"El {porcentaje_recurrentes:.2f}% "
        f"tiene al menos dos contratos y el "
        f"{porcentaje_varios_anios:.2f}% "
        f"fue contratado en dos o más años diferentes. "

        f"El {porcentaje_prorrogados:.2f}% "
        f"de los contratos tuvo prórroga, con una mediana "
        f"de {mediana_dias_prorroga:.0f} días adicionados. "

        f"La tasa de prórroga aumenta conforme crece "
        f"la recurrencia del proveedor."

    )


    return (
        *kpis,
        fig_recurrencia,
        fig_prorrogas,
        fig_anios,
        texto,
    )


# ---------------------------------------------------------------------------
# 5. Seccion Pregunta 3
# Estacionalidad y distribucion geografica
# ---------------------------------------------------------------------------

seccion_p3 = html.Div([


    html.Div([

        kpi_card(
            "Contratos analizados",
            f"{TOTAL_NEGOCIO:,}",
            accent=SENA_GREEN,
        ),

        kpi_card(
            "Regionales",
            f"{dfb['regional'].nunique()}",
            accent=SENA_GREEN,
        ),

        kpi_card(
            "Concentración Ene-Feb",
            f"{pct_ene_feb}%",
            accent=SENA_ORANGE,
        ),

        kpi_card(
            "Chi-cuadrado (mes x regional)",
            "p < 0.001",
            accent=SENA_ORANGE,
        ),

    ], className="kpi-row"),


    html.Div([

        html.Div([

            html.Label(
                "Regionales a mostrar"
            ),

            dcc.Dropdown(
                id="filtro-regionales",

                options=[
                    {
                        "label": r,
                        "value": r,
                    }
                    for r in TODAS_REGIONALES
                ],

                value=[],

                multi=True,

                placeholder="Selecciona una o mas regionales...",
            ),

        ],

        className="filter-col",

        style={
            "flexBasis": "100%"
        }),

    ], className="filter-panel"),


    html.Div([

        html.Div(
            dcc.Graph(
                id="grafico-barras-regional",

                config={
                    "displayModeBar": False
                },
            ),

            className="chart-card",
        ),


        html.Div(
            dcc.Graph(
                id="grafico-linea-mes",

                config={
                    "displayModeBar": False
                },
            ),

            className="chart-card",
        ),

    ], className="charts-row"),


    html.Div([

        html.Div(
            dcc.Graph(
                id="grafico-heatmap",

                config={
                    "displayModeBar": False
                },
            ),

            className="chart-card full-width",
        ),

    ], className="charts-row"),


    html.Div(
        id="texto-hallazgo",

        className="insight-box",
    ),

])


@app.callback(
    Output(
        "grafico-barras-regional",
        "figure",
    ),

    Output(
        "grafico-linea-mes",
        "figure",
    ),

    Output(
        "grafico-heatmap",
        "figure",
    ),

    Output(
        "texto-hallazgo",
        "children",
    ),

    Input(
        "filtro-regionales",
        "value",
    ),
)

def actualizar_pregunta3(
    regionales_sel,
):

    if not regionales_sel:
        regionales_sel = TOP8_DEFAULT


    d = dfb[
        dfb["regional"].isin(
            regionales_sel
        )
    ]


    conteo = (
        d["regional"]
        .value_counts()
        .sort_values()
    )


    fig_barras = px.bar(
        conteo,

        x=conteo.values,

        y=conteo.index,

        orientation="h",

        labels={
            "x": "Numero de contratos",
            "y": "",
        },

        title=(
            "Contratos por regional "
            "(selección actual)"
        ),
    )


    fig_barras.update_traces(
        marker_color=SENA_GREEN
    )


    estilizar_figura(
        fig_barras
    )


    conteo_mes = (
        d["nombre_mes"]
        .value_counts()
        .reindex(ORDEN_MESES)
        .fillna(0)
    )


    fig_linea = px.line(
        x=conteo_mes.index,

        y=conteo_mes.values,

        markers=True,

        labels={
            "x": "Mes de firma",
            "y": "Numero de contratos",
        },

        title=(
            "Estacionalidad mensual "
            "(selección actual)"
        ),
    )


    fig_linea.update_traces(
        line_color=SENA_ORANGE,
        marker_color=SENA_ORANGE,
    )


    estilizar_figura(
        fig_linea
    )


    tabla = (
        d
        .pivot_table(
            index="regional",

            columns="nombre_mes",

            values="id_contrato",

            aggfunc="count",

            fill_value=0,
        )

        .reindex(
            columns=ORDEN_MESES
        )

        .loc[
            [
                r
                for r in regionales_sel
                if r in d["regional"].unique()
            ]
        ]
    )


    fig_heatmap = px.imshow(
        tabla,

        text_auto=True,

        aspect="auto",

        color_continuous_scale=GREEN_SCALE,

        labels=dict(
            x="Mes",
            y="Regional",
            color="Contratos",
        ),

        title=(
            "Heatmap mes x regional "
            "(selección actual)"
        ),
    )


    estilizar_figura(
        fig_heatmap,
        altura=420,
    )


    texto = (
        f"Con las regionales seleccionadas "
        f"se observan {d.shape[0]:,} contratos "
        f"({d.shape[0] / TOTAL_NEGOCIO * 100:.1f}% "
        f"del universo de negocio). "

        f"A nivel global, el {pct_ene_feb}% "
        f"de toda la contratación se firma "
        f"en enero-febrero, y la prueba "
        f"chi-cuadrado "
        f"(chi2={chi2:.1f}, gl={gl}, p<0.001) "
        f"confirma que el patrón mensual varía "
        f"significativamente entre regionales: "
        f"no existe una única ventana nacional "
        f"de contratación."
    )


    return (
        fig_barras,
        fig_linea,
        fig_heatmap,
        texto,
    )


# ---------------------------------------------------------------------------
# 6. Layout general
# sidebar de navegacion + contenido
# ---------------------------------------------------------------------------

SECCIONES = {
    "p1": (
        "nav-p1",
        "tab-p1",
        seccion_p1,
    ),

    "p2": (
        "nav-p2",
        "tab-p2",
        seccion_p2,
    ),

    "p3": (
        "nav-p3",
        "tab-p3",
        seccion_p3,
    ),
}


app.layout = html.Div(
    className="app-shell",

    children=[

        html.Div(
            className="sidebar",

            children=[

                html.Div(
                    className="brand",

                    children=[

                        html.Div(
                            "S",
                            className="brand-icon",
                        ),

                        html.Div([

                            html.Div(
                                "SENA · SECOP II",
                                className="brand-text",
                            ),

                            html.Div(
                                "Tablero de contratación",
                                className="brand-sub",
                            ),

                        ]),

                    ],
                ),


                html.Div(
                    className="nav-section-label",
                    children="Preguntas de negocio",
                ),


                html.Button(
                    [
                        html.Span(
                            className="nav-dot"
                        ),

                        "Pregunta 1 · Tamaño y concentración",
                    ],

                    id="nav-p1",

                    n_clicks=0,

                    className="nav-item active",
                ),


                html.Button(
                    [
                        html.Span(
                            className="nav-dot"
                        ),

                        "Pregunta 2 · Recurrencia y estabilidad",
                    ],

                    id="nav-p2",

                    n_clicks=0,

                    className="nav-item",
                ),


                html.Button(
                    [
                        html.Span(
                            className="nav-dot"
                        ),

                        "Pregunta 3 · Estacionalidad y geografía",
                    ],

                    id="nav-p3",

                    n_clicks=0,

                    className="nav-item",
                ),


                html.Div(
                    className="sidebar-footer",

                    children=[

                        html.Div(
                            "Analítica Computacional "
                            "para la Toma de Decisiones"
                        ),

                        html.Div(
                            "Proyecto 1 · "
                            "Contratación pública SENA"
                        ),

                    ],
                ),

            ],
        ),


        html.Div(
            className="main",

            children=[

                html.Div(
                    className="topbar",

                    children=[
                        html.H2(
                            id="titulo-seccion"
                        )
                    ],
                ),


                html.Div(
                    id="tab-p1",
                    children=seccion_p1,
                ),


                html.Div(
                    id="tab-p2",

                    children=seccion_p2,

                    style={
                        "display": "none"
                    },
                ),


                html.Div(
                    id="tab-p3",

                    children=seccion_p3,

                    style={
                        "display": "none"
                    },
                ),

            ],
        ),

    ],
)


TITULOS = {
    "p1":
        "Pregunta 1 · Tamaño y concentración del gasto",

    "p2":
        "Pregunta 2 · Recurrencia y estabilidad",

    "p3":
        "Pregunta 3 · Estacionalidad y distribución geográfica",
}


@app.callback(
    Output(
        "tab-p1",
        "style",
    ),

    Output(
        "tab-p2",
        "style",
    ),

    Output(
        "tab-p3",
        "style",
    ),

    Output(
        "nav-p1",
        "className",
    ),

    Output(
        "nav-p2",
        "className",
    ),

    Output(
        "nav-p3",
        "className",
    ),

    Output(
        "titulo-seccion",
        "children",
    ),

    Input(
        "nav-p1",
        "n_clicks",
    ),

    Input(
        "nav-p2",
        "n_clicks",
    ),

    Input(
        "nav-p3",
        "n_clicks",
    ),
)

def cambiar_seccion(
    n1,
    n2,
    n3,
):

    activo = "p1"

    disparador = ctx.triggered_id


    if disparador in (
        "nav-p1",
        "nav-p2",
        "nav-p3",
    ):

        activo = disparador.replace(
            "nav-",
            "",
        )


    estilos = {
        k: (
            {
                "display": "none"
            }

            if k != activo

            else

            {
                "display": "block"
            }
        )

        for k in (
            "p1",
            "p2",
            "p3",
        )
    }


    clases = {
        k: (
            "nav-item active"

            if k == activo

            else

            "nav-item"
        )

        for k in (
            "p1",
            "p2",
            "p3",
        )
    }


    return (
        estilos["p1"],
        estilos["p2"],
        estilos["p3"],

        clases["p1"],
        clases["p2"],
        clases["p3"],

        TITULOS[activo],
    )


# ---------------------------------------------------------------------------
# Ejecucion
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=8050,
    )