from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st


# CONFIGURACIÓN GENERAL
st.set_page_config(
    page_title="Panorama de centrales eléctricas",
    page_icon="⚡",
    layout="wide"
)

sns.set_theme(style="whitegrid")


# FUNCIONES
@st.cache_data
def cargar_datos(ruta, modificacion):
    """Carga el archivo y prepara las columnas utilizadas."""
    datos = pd.read_csv(ruta)

    requeridas = [
        "country_long",
        "fuel1",
        "capacity_mw",
        "estimated_generation_gwh",
        "latitude",
        "longitude"
    ]

    faltantes = [
        columna for columna in requeridas
        if columna not in datos.columns
    ]

    if faltantes:
        raise ValueError(
            f"El archivo no contiene estas columnas: {faltantes}"
        )

    numericas = [
        "capacity_mw",
        "estimated_generation_gwh",
        "latitude",
        "longitude"
    ]

    for columna in numericas:
        datos[columna] = (
            pd.to_numeric(datos[columna], errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
        )

    for columna in ["country_long", "fuel1"]:
        datos[columna] = (
            datos[columna]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
            .fillna("Sin dato")
        )

    return datos


def mostrar_figura(figura):
    """Muestra la figura y libera sus recursos."""
    figura.tight_layout()
    st.pyplot(figura)
    plt.close(figura)


# PRESENTACIÓN
st.title("⚡ Panorama de centrales eléctricas")

st.write(
    "Explore la capacidad instalada y la generación estimada "
    "del dataset Global Power Plant Database."
)

st.caption(
    "MW expresa capacidad instalada; GWh expresa energía generada. "
    "La tabla, las métricas, los gráficos y el mapa responden "
    "a los filtros seleccionados."
)


# CARGA DEL DATASET
ruta = Path(__file__).parent / "global_power_plant_database.csv"

try:
    df = cargar_datos(str(ruta), ruta.stat().st_mtime)
except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"No fue posible cargar el dataset: {error}")
    st.info(
        "Coloque global_power_plant_database.csv "
        "en la misma carpeta que app.py."
    )
    st.stop()


# FILTROS CATEGÓRICOS
st.sidebar.header("Filtros")

pais = st.sidebar.selectbox(
    "País",
    ["Todos"] + sorted(df["country_long"].unique().tolist())
)

fuente = st.sidebar.selectbox(
    "Fuente principal",
    ["Todas"] + sorted(df["fuel1"].unique().tolist())
)


# FILTRO NUMÉRICO
capacidades = df["capacity_mw"].dropna()

if capacidades.empty:
    st.error("No hay capacidades numéricas válidas.")
    st.stop()

minimo = float(capacidades.min())
maximo = float(capacidades.max())

modo_rango = st.sidebar.radio(
    "Forma de seleccionar la capacidad",
    ["Deslizador", "Valores exactos"]
)

if minimo == maximo:
    rango = (minimo, maximo)
    st.sidebar.info(
        f"Todas las capacidades válidas son {minimo:g} MW."
    )

elif modo_rango == "Deslizador":
    rango = st.sidebar.slider(
        "Capacidad instalada (MW)",
        min_value=minimo,
        max_value=maximo,
        value=(minimo, maximo)
    )

else:
    limite_inferior = st.sidebar.number_input(
        "Capacidad mínima (MW)",
        min_value=minimo,
        max_value=maximo,
        value=minimo,
        step=1.0,
        format="%.2f",
        key="capacidad_minima"
    )

    limite_superior = st.sidebar.number_input(
        "Capacidad máxima (MW)",
        min_value=minimo,
        max_value=maximo,
        value=maximo,
        step=1.0,
        format="%.2f",
        key="capacidad_maxima"
    )

    rango = (limite_inferior, limite_superior)

st.sidebar.caption(
    "Seleccione «Valores exactos» para escribir, por ejemplo, "
    "un rango de 1 a 100 MW."
)

if rango[0] > rango[1]:
    st.error(
        "La capacidad mínima no puede superar la máxima. "
        "Corrija los valores del filtro."
    )
    st.stop()

st.sidebar.caption(
    "Los registros sin capacidad numérica válida quedan fuera "
    "del filtro de capacidad."
)


# APLICACIÓN DE FILTROS
mascara = df["capacity_mw"].between(rango[0], rango[1])

if pais != "Todos":
    mascara &= df["country_long"].eq(pais)

if fuente != "Todas":
    mascara &= df["fuel1"].eq(fuente)

filtrado = df.loc[mascara].copy()

st.caption(
    f"Selección activa: país = {pais}; fuente = {fuente}; "
    f"capacidad entre {rango[0]:,.2f} y {rango[1]:,.2f} MW."
)


# EXPLORACIÓN
st.header("Exploración de datos")

if filtrado.empty:
    st.warning(
        "No hay centrales que cumplan los filtros seleccionados. "
        "Amplíe el rango de capacidad o cambie el país o la fuente. "
        "No se presentan métricas, gráficos ni mapa para esta selección."
    )

else:
    media = filtrado["capacity_mw"].mean()
    desviacion = filtrado["capacity_mw"].std()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Registros seleccionados",
        f"{len(filtrado):,}"
    )

    c2.metric(
        "Capacidad media (MW)",
        f"{media:,.2f}"
    )

    c3.metric(
        "Desviación estándar (MW)",
        f"{desviacion:,.2f}"
        if pd.notna(desviacion)
        else "No disponible"
    )

    st.caption(
        "La desviación estándar describe cuánto varían las capacidades "
        "respecto a su media. Su cálculo requiere al menos dos registros."
    )

    st.dataframe(filtrado)


    # VISUALIZACIONES
    st.header("Visualizaciones")

    st.caption(
        "Los siguientes gráficos utilizan únicamente "
        "los registros de la selección activa."
    )


    # GRÁFICO 1: BARRAS
    frecuencias = filtrado["fuel1"].value_counts()

    fig, ax = plt.subplots(figsize=(10, 5))

    frecuencias.sort_values().plot.barh(
        ax=ax,
        color="steelblue"
    )

    ax.set_title("Cantidad de centrales por fuente principal")
    ax.set_xlabel("Número de registros")
    ax.set_ylabel("Fuente principal de energía")

    mostrar_figura(fig)

    st.write(
        "El gráfico permite comparar la cantidad de centrales "
        "por fuente de energía. Una mayor cantidad de registros "
        "no implica una mayor capacidad total ni una mayor generación. "
        "Si se selecciona una sola fuente, aparece una sola barra."
    )


    # GRÁFICO 2: BOXPLOT
    fig, ax = plt.subplots(figsize=(10, 4))

    sns.boxplot(
        data=filtrado,
        x="capacity_mw",
        color="lightblue",
        ax=ax
    )

    ax.set_title("Distribución de la capacidad instalada")
    ax.set_xlabel("Capacidad instalada (MW)")
    ax.set_ylabel("Centrales seleccionadas")

    mostrar_figura(fig)

    st.write(
        "El diagrama de caja permite observar la dispersión "
        "y las capacidades alejadas de los valores habituales. "
        "Los puntos extremos no son necesariamente errores: "
        "pueden representar centrales de gran tamaño."
    )


    # GRÁFICO 3: DISPERSIÓN
    pares = filtrado.dropna(
        subset=["capacity_mw", "estimated_generation_gwh"]
    )

    st.caption(
        f"Registros con capacidad y generación estimada disponibles: "
        f"{len(pares):,}. "
        f"Registros excluidos de este gráfico: "
        f"{len(filtrado) - len(pares):,}."
    )

    if pares.empty:
        st.info(
            "No hay datos completos para representar "
            "la relación entre capacidad y generación estimada."
        )

    else:
        fig, ax = plt.subplots(figsize=(10, 5))

        sns.scatterplot(
            data=pares,
            x="capacity_mw",
            y="estimated_generation_gwh",
            alpha=0.35,
            s=20,
            ax=ax
        )

        ax.set_title("Capacidad instalada y generación estimada")
        ax.set_xlabel("Capacidad instalada (MW)")
        ax.set_ylabel("Generación estimada (GWh)")

        mostrar_figura(fig)

        st.write(
            "Cada punto representa una central del conjunto seleccionado. "
            "Este gráfico permite explorar la asociación entre capacidad "
            "y generación estimada. Una asociación positiva no demuestra "
            "por sí sola causalidad ni mayor eficiencia."
        )


    # MAPA
    st.header("Ubicación de las centrales")

    coordenadas_validas = (
        filtrado["latitude"].between(-90, 90)
        & filtrado["longitude"].between(-180, 180)
    )

    representables = int(coordenadas_validas.sum())
    no_representables = len(filtrado) - representables

    st.write(
        f"Registros representables: **{representables:,}**. "
        f"Registros no representables: **{no_representables:,}**."
    )

    st.caption(
        "Se excluyen únicamente del mapa las filas con coordenadas "
        "ausentes o fuera de rango. Cada fila se cuenta una sola vez. "
        "Una coordenada dentro del rango no garantiza que la ubicación "
        "registrada sea correcta."
    )

    if representables > 0:
        st.map(
            filtrado.loc[
                coordenadas_validas,
                ["latitude", "longitude"]
            ]
        )
    else:
        st.info(
            "La selección no contiene coordenadas válidas "
            "para mostrar en el mapa."
        )

    st.write(
        "La vista espacial ayuda a reconocer concentraciones "
        "geográficas de centrales. Las zonas con pocos puntos "
        "también pueden reflejar una cobertura incompleta de datos."
    )


# VALIDACIÓN ESTADÍSTICA ORIGINAL
st.header("Validación estadística del análisis original")

st.info(
    "Los siguientes resultados corresponden al EDA de la Tarea 3 "
    "y no se recalculan con los filtros activos."
)

resumen_original = pd.DataFrame({
    "Fuente": ["Solar", "Wind"],
    "Registros": [5424, 5084],
    "Capacidad media (MW)": [10.628, 45.791]
})

st.table(resumen_original)

st.markdown("""
**Comparación:** capacidad instalada de centrales solares y eólicas.

- **Hipótesis nula:** las medias de capacidad instalada son iguales.
- **Hipótesis alternativa:** las medias son diferentes.
- **Prueba aplicada:** t de Welch para muestras independientes.
- **Estadístico t:** −23.5534.
- **p-value:** 3.724047 × 10⁻¹¹⁷.
- **Nivel de significancia:** 0.05.

**Interpretación en lenguaje claro:** en el análisis original, las
centrales eólicas presentaron una capacidad media aproximadamente
**35.16 MW mayor** que las solares. La prueba aporta evidencia
estadística de una diferencia entre las medias, bajo sus supuestos,
por lo que se rechaza la hipótesis de igualdad.

Este resultado **no demuestra causalidad ni mayor eficiencia**
de una tecnología. La capacidad instalada mide potencia, no
eficiencia. La composición y cobertura del dataset también
limitan la generalización de esta comparación.
""")


# NARRATIVA: MÁS DE 150 PALABRAS
st.header("Hallazgos del análisis original")

st.caption(
    "Esta narrativa resume el conjunto original del EDA. "
    "Los gráficos anteriores muestran la selección activa "
    "y pueden presentar resultados distintos al aplicar filtros."
)

st.markdown("""
### ¿Qué analicé?

Analicé 28,664 registros de centrales eléctricas del dataset
Global Power Plant Database. El objetivo fue explorar la
distribución de las fuentes de energía, la capacidad instalada
y su relación con la generación estimada. También revisé
la dispersión de los valores, la presencia de datos faltantes
y las limitaciones que afectan su interpretación. El dashboard
permite consultar estas características por país, fuente
principal y rango de capacidad.

### ¿Qué encontré?

En el conjunto original, la fuente hidroeléctrica presentó
7,034 registros, seguida de la solar con 5,424 y la eólica
con 5,084. El **gráfico de barras** permite explorar estas
frecuencias y observar cómo cambia su composición al aplicar
filtros. El **diagrama de caja** muestra que las capacidades
son heterogéneas y que existen centrales de gran tamaño
alejadas de los valores más habituales. Por otra parte,
la capacidad instalada y la generación estimada presentaron
una correlación positiva de 0.909 en 27,536 registros completos.
El **gráfico de dispersión** permite examinar esta asociación.

### ¿Qué significa?

El número de centrales no describe por sí solo su aporte
energético, porque sus capacidades pueden ser muy diferentes.
Los valores extremos requieren una revisión contextual y no
deben eliminarse automáticamente. Asimismo, la correlación
entre capacidad y generación estimada no demuestra causalidad.
Antes de interpretar esta relación, es necesario revisar
cómo se calcularon las estimaciones y si su método utiliza
la capacidad instalada como uno de sus componentes.

### ¿Qué se recomendaría?

Utilizar el dashboard como una herramienta de exploración
inicial y comparar países y fuentes antes de formular
conclusiones. Para apoyar decisiones de inversión o
planificación, se recomienda incorporar datos actualizados
de generación real, costos, demanda y condiciones locales.
También conviene revisar las coordenadas y los registros
incompletos utilizando fuentes confiables. Las conclusiones
describen el archivo analizado y no deben presentarse como
un inventario completo y actualizado del sistema eléctrico
mundial.
""")

st.caption(
    "Fuente: Global Power Plant Database. "
    "Dashboard basado en el análisis exploratorio de la Tarea 3."
)
