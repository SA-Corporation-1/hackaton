import plotly.express as px
from utils.db import init_db
init_db()
import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from openai import OpenAI
# -----------------------------------------------------------
#  PAGE 1 — ИМПОРТ ДАННЫХ
# -----------------------------------------------------------

def page_import_data():
    st.title("Импорт данных")

    obj_file = st.file_uploader("Objects.csv", type=["csv"])
    diag_file = st.file_uploader("Diagnostics.csv", type=["csv"])

    if st.button("Загрузить и обработать"):
        if obj_file is None or diag_file is None:
            st.error("Загрузите оба файла.")
            return

        objects = pd.read_csv(obj_file)
        diagnostics = pd.read_csv(diag_file)

        # Подготовка данных
        if "date" in diagnostics.columns:
            diagnostics["date"] = pd.to_datetime(diagnostics["date"], errors="coerce")
            diagnostics["year"] = diagnostics["date"].dt.year
        else:
            diagnostics["year"] = None

        if "severity" in diagnostics.columns:
            diagnostics["defect_found"] = diagnostics["severity"].apply(
                lambda x: 1 if str(x).lower() != "low" else 0
            )
            diagnostics["ml_label"] = diagnostics["severity"].astype(str).str.lower()
        else:
            diagnostics["defect_found"] = 0
            diagnostics["ml_label"] = "unknown"

        st.session_state["objects_df"] = objects
        st.session_state["diagnostics_df"] = diagnostics

        st.success("Данные успешно загружены!")


# -----------------------------------------------------------
#  PAGE 2 — ДАШБОРД
# -----------------------------------------------------------

def page_dashboard():
    st.title("Дашборд диагностики объектов")

    # Проверка данных
    if "objects_df" not in st.session_state or "diagnostics_df" not in st.session_state:
        st.warning("Сначала загрузите данные на странице «Импорт данных».")
        return

    objects = st.session_state["objects_df"]
    diagnostics = st.session_state["diagnostics_df"]

    if objects.empty or diagnostics.empty:
        st.warning("Таблицы пустые.")
        return

    # Фильтры
    st.sidebar.subheader("Фильтры")

    years = sorted(diagnostics["year"].dropna().unique().tolist())
    year_filter = st.sidebar.selectbox("Год", ["Все годы"] + [str(y) for y in years])

    methods = sorted(diagnostics["method"].dropna().unique().tolist()) if "method" in diagnostics.columns else []
    method_filter = st.sidebar.selectbox("Метод контроля", ["Все методы"] + methods)

    crits = sorted(diagnostics["ml_label"].dropna().unique().tolist())
    crit_filter = st.sidebar.selectbox("Критичность", ["Все уровни"] + crits)

    filtered = diagnostics.copy()

    if year_filter != "Все годы":
        filtered = filtered[filtered["year"] == int(year_filter)]

    if method_filter != "Все методы":
        filtered = filtered[filtered["method"] == method_filter]

    if crit_filter != "Все уровни":
        filtered = filtered[filtered["ml_label"] == crit_filter]

    # KPI
    st.subheader("Сводные показатели")

    defects = filtered[filtered["defect_found"] == 1]

    total_inspections = len(filtered)
    total_objects = filtered["object_id"].nunique()
    total_defects = defects["defect_found"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Обследований", total_inspections)
    col2.metric("Объектов", total_objects)
    col3.metric("Дефектов", total_defects)

    st.markdown("---")

    # -----------------------------------------------------------
    # ГРАФИК 1: ДЕФЕКТЫ ПО МЕТОДАМ
    # -----------------------------------------------------------

    st.subheader("Дефекты по методам контроля")

    if not defects.empty and "method" in defects.columns:
        df_methods = (
            defects.groupby("method")["defect_found"]
            .sum()
            .reset_index()
            .sort_values("defect_found", ascending=False)
        )
