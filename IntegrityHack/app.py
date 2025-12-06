import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from openai import OpenAI
from utils.db import init_db
init_db()
# для карты

# TODO: потом подключите свои утилиты
# from utils.data_utils import load_data, preprocess_data
# from utils.ml_utils import apply_ml_model
# from utils.report_utils import generate_gpt_report


# ---------- ГЛОБАЛЬНОЕ СОСТОЯНИЕ ----------

if "objects_df" not in st.session_state:
    st.session_state.objects_df = None

if "diagnostics_df" not in st.session_state:
    st.session_state.diagnostics_df = None

if "processed_df" not in st.session_state:
    st.session_state.processed_df = None


# ---------- ФУНКЦИИ ДЛЯ БЛОКОВ ----------

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def page_import():
    st.title("Импорт данных")

    st.write("Загрузите файлы Objects.csv и Diagnostics.csv")

    objects_file = st.file_uploader("Objects.csv", type=["csv"], key="objects_uploader")
    diagnostics_file = st.file_uploader("Diagnostics.csv", type=["csv"], key="diag_uploader")

    if st.button("Загрузить и обработать"):
        if objects_file is None or diagnostics_file is None:
            st.error("Пожалуйста, загрузите оба файла.")
            return

        objects_df = pd.read_csv(objects_file)
        diagnostics_df = pd.read_csv(diagnostics_file)

        # Здесь потом будет вызов функций из utils:
        # objects_df, diagnostics_df = preprocess_data(objects_df, diagnostics_df)
        # processed_df = apply_ml_model(objects_df, diagnostics_df)

        # Пока просто сохраним как есть
        st.session_state.objects_df = objects_df
        st.session_state.diagnostics_df = diagnostics_df
        st.session_state.processed_df = diagnostics_df  # временно

        st.success("Данные загружены!")
        st.write("Objects (первые 5 строк):")
        st.dataframe(objects_df.head())
        st.write("Diagnostics (первые 5 строк):")
        st.dataframe(diagnostics_df.head())

def page_map():
    st.title("Карта объектов")

    if st.session_state.objects_df is None:
        st.warning("Сначала загрузите данные на странице 'Импорт данных'.")
        return

    objects_df = st.session_state.objects_df.copy()

    # Проверим обязательные колонки
    required_cols = {"lat", "lon"}
    if not required_cols.issubset(objects_df.columns):
        st.error(f"В Objects.csv должны быть колонки: {required_cols}")
        st.dataframe(objects_df.head())
        return

    st.subheader("Фильтры")

    # Фильтр по типу объекта (если есть колонка type)
    if "type" in objects_df.columns:
        all_types = sorted(objects_df["type"].dropna().unique())
        selected_types = st.multiselect(
            "Тип объекта",
            options=all_types,
            default=all_types,
        )
        if selected_types:
            objects_df = objects_df[objects_df["type"].isin(selected_types)]

    # Фильтр по критичности (если есть колонка criticality)
    if "criticality" in objects_df.columns:
        all_crit = sorted(objects_df["criticality"].dropna().unique())
        selected_crit = st.multiselect(
            "Критичность",
            options=all_crit,
            default=all_crit,
        )
        if selected_crit:
            objects_df = objects_df[objects_df["criticality"].isin(selected_crit)]

    st.markdown("---")

    if objects_df.empty:
        st.warning("По выбранным фильтрам нет объектов.")
        return

    st.subheader("Карта")

    # Базовый центр карты — среднее по координатам
    midpoint = (
        objects_df["lat"].mean(),
        objects_df["lon"].mean(),
    )

    # Цвета для критичности (если нет criticality, будет один цвет)
    def get_color(row):
        if "criticality" not in objects_df.columns:
            return [0, 128, 255]  # синий
        crit = str(row["criticality"]).lower()
        if "high" in crit or "выс" in crit:
            return [255, 0, 0]      # красный
        elif "medium" in crit or "сред" in crit:
            return [255, 165, 0]    # оранжевый
        else:
            return [0, 200, 0]      # зелёный

    objects_df["color"] = objects_df.apply(get_color, axis=1)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=objects_df,
        get_position='[lon, lat]',
        get_fill_color='color',
        get_radius=50,
        pickable=True,
        radius_scale=5,
    )

    tooltip = {
        "html": "<b>{name}</b><br/>Тип: {type}<br/>Критичность: {criticality}",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=pdk.ViewState(
                latitude=midpoint[0],
                longitude=midpoint[1],
                zoom=10,
                pitch=0,
            ),
            layers=[layer],
            tooltip=tooltip,
        )
    )

    st.subheader("Таблица объектов")
    st.dataframe(objects_df.head(200))



def page_defects():
    st.title("Список дефектов / диагностик")

    if st.session_state.diagnostics_df is None:
        st.warning("Сначала загрузите данные на странице 'Импорт данных'.")
        return

    diagnostics_df = st.session_state.diagnostics_df.copy()

    st.subheader("Фильтры")

    # Фильтр по методу
    if "method" in diagnostics_df.columns:
        all_methods = sorted(diagnostics_df["method"].dropna().unique())
        selected_methods = st.multiselect(
            "Метод контроля",
            options=all_methods,
            default=all_methods,
        )
        if selected_methods:
            diagnostics_df = diagnostics_df[diagnostics_df["method"].isin(selected_methods)]

    # Фильтр по критичности / severity
    crit_col = None
    if "criticality" in diagnostics_df.columns:
        crit_col = "criticality"
    elif "severity" in diagnostics_df.columns:
        crit_col = "severity"

    if crit_col is not None:
        all_crit = sorted(diagnostics_df[crit_col].dropna().unique())
        selected_crit = st.multiselect(
            "Критичность",
            options=all_crit,
            default=all_crit,
        )
        if selected_crit:
            diagnostics_df = diagnostics_df[diagnostics_df[crit_col].isin(selected_crit)]

    # Фильтр по диапазону дат (если есть колонка date)
    if "date" in diagnostics_df.columns:
        # Попробуем привести к datetime
        diagnostics_df["date_parsed"] = pd.to_datetime(
            diagnostics_df["date"], errors="coerce"
        )
        min_date = diagnostics_df["date_parsed"].min()
        max_date = diagnostics_df["date_parsed"].max()

        if pd.notnull(min_date) and pd.notnull(max_date):
            start_date, end_date = st.date_input(
                "Диапазон дат",
                value=(min_date.date(), max_date.date()),
            )

            if start_date and end_date:
                mask = (diagnostics_df["date_parsed"].dt.date >= start_date) & (
                    diagnostics_df["date_parsed"].dt.date <= end_date
                )
                diagnostics_df = diagnostics_df[mask]

    st.markdown("---")

    if diagnostics_df.empty:
        st.warning("По выбранным фильтрам нет записей.")
        return

    st.subheader("Таблица диагностик")

    # Выбор колонок для отображения (чтобы не было слишком много)
    cols_to_show = [
        col for col in diagnostics_df.columns
        if col not in ["date_parsed"]
    ]
    st.dataframe(diagnostics_df[cols_to_show].head(300))

    # Опционально: небольшой summary
    st.subheader("Краткая статистика")
    st.write("Количество диагностик:", len(diagnostics_df))

    if crit_col is not None:
        st.write("Распределение по критичности:")
        st.dataframe(diagnostics_df[crit_col].value_counts())



def page_dashboard():
    st.title("Дашборд диагностики объектов")

    # 1. Проверка данных
    if "objects_df" not in st.session_state or "diagnostics_df" not in st.session_state:
        st.warning("Сначала загрузите данные на странице «Импорт данных».")
        return

    objects = st.session_state["objects_df"].copy()
    diagnostics = st.session_state["diagnostics_df"].copy()

    if objects.empty or diagnostics.empty:
        st.warning("Таблицы пустые. Проверьте загрузку CSV.")
        return

    # 2. Предобработка (страховка)
    # Дата → год
    if "date" in diagnostics.columns:
        diagnostics["date"] = pd.to_datetime(diagnostics["date"], errors="coerce")
        diagnostics["year"] = diagnostics["date"].dt.year
    else:
        diagnostics["year"] = None

    # defect_found
    if "defect_found" not in diagnostics.columns:
        if "severity" in diagnostics.columns:
            diagnostics["defect_found"] = diagnostics["severity"].apply(
                lambda x: 1 if str(x).lower() != "low" else 0
            )
        else:
            diagnostics["defect_found"] = 0

    # ml_label
    if "ml_label" not in diagnostics.columns:
        if "severity" in diagnostics.columns:
            diagnostics["ml_label"] = diagnostics["severity"].astype(str).str.lower()
        else:
            diagnostics["ml_label"] = "unknown"

    # 3. ФИЛЬТРЫ (слева сверху)
    st.sidebar.subheader("Фильтры дашборда")

    # Год
    years = sorted(diagnostics["year"].dropna().unique().tolist())
    year_filter = st.sidebar.selectbox(
        "Год обследования", ["Все годы"] + [str(y) for y in years]
    )

    # Метод контроля
    methods = sorted(diagnostics["method"].dropna().unique().tolist()) if "method" in diagnostics.columns else []
    method_filter = st.sidebar.selectbox(
        "Метод контроля", ["Все методы"] + methods
    )

    # Критичность (по ml_label)
    crits = sorted(diagnostics["ml_label"].dropna().unique().tolist())
    crit_filter = st.sidebar.selectbox(
        "Критичность (ml_label)", ["Все уровни"] + crits
    )

    # Применяем фильтры
    filtered = diagnostics.copy()

    if year_filter != "Все годы":
        filtered = filtered[filtered["year"] == int(year_filter)]

    if method_filter != "Все методы" and "method" in filtered.columns:
        filtered = filtered[filtered["method"] == method_filter]

    if crit_filter != "Все уровни":
        filtered = filtered[filtered["ml_label"] == crit_filter]

    # 4. KPI по отфильтрованным данным
    st.markdown("### Сводные показатели (с учётом фильтров)")

    total_inspections = len(filtered)
    total_objects = filtered["object_id"].nunique() if "object_id" in filtered.columns else 0
    total_defects = int(filtered["defect_found"].sum())

    # высокая критичность
    if "criticality" in objects.columns:
        high_crit_objects = (
            objects["criticality"].astype(str).str.lower().eq("high").sum()
        )
    else:
        if "object_id" in filtered.columns:
            high_ids = filtered.loc[filtered["ml_label"] == "high", "object_id"].dropna().unique()
            high_crit_objects = len(high_ids)
        else:
            high_crit_objects = 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Обследований", total_inspections)
    col2.metric("Объектов", total_objects)
    col3.metric("Дефектов", total_defects)
    col4.metric("Объектов с высокой критичностью", high_crit_objects)

    st.markdown("---")

    # 5. Бар-чарт: дефекты по методам
    st.subheader("Дефекты по методам контроля")
    defects = filtered[filtered["defect_found"] == 1]

    if "method" in filtered.columns and not defects.empty:
        df_methods = (
            defects.groupby("method")["defect_found"]

        )

def page_report():
    st.title("GPT-отчёт по диагностике и рискам")

    # 1. Проверяем, что есть данные
    if "diagnostics_df" not in st.session_state or "objects_df" not in st.session_state:
        st.warning("Сначала загрузите данные на странице «Импорт данных».")
        return

    diagnostics = st.session_state["diagnostics_df"].copy()
    objects = st.session_state["objects_df"].copy()

    if diagnostics.empty or objects.empty:
        st.warning("Данные загружены, но таблицы пустые.")
        return

    # 2. Страхуемся, если коллеги ещё не сделали defect_found / ml_label
    if "severity" in diagnostics.columns:
        if "defect_found" not in diagnostics.columns:
            diagnostics["defect_found"] = diagnostics["severity"].apply(
                lambda x: 1 if str(x).lower() != "low" else 0
            )
        if "ml_label" not in diagnostics.columns:
            diagnostics["ml_label"] = diagnostics["severity"].astype(str).str.lower()
    else:
        diagnostics["defect_found"] = diagnostics.get("defect_found", 0)
        diagnostics["ml_label"] = diagnostics.get("ml_label", "unknown")

    # 3. Считаем KPI
    total_inspections = len(diagnostics)
    total_objects = objects["object_id"].nunique() if "object_id" in objects.columns else None
    total_defects = int(diagnostics["defect_found"].sum())

    # распределение по критичности
    crit_dist = (
        diagnostics["ml_label"]
        .value_counts()
        .to_dict()
        if "ml_label" in diagnostics.columns
        else {}
    )

    # топ проблемных объектов
    if "object_id" in diagnostics.columns:
        defect_rows = diagnostics[diagnostics["defect_found"] == 1]
        top_objects = (
            defect_rows.groupby("object_id")
            .size()
            .sort_values(ascending=False)
            .head(5)
        )
    else:
        top_objects = pd.Series(dtype=int)

    st.subheader("Краткая сводка по данным")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Обследований", total_inspections)
    with col2:
        st.metric("Объектов", total_objects if total_objects is not None else "—")
    with col3:
        st.metric("Выявлено дефектов", total_defects)

    if not top_objects.empty:
        st.markdown("Топ-5 объектов по количеству дефектов:")
        st.dataframe(top_objects.rename("defects"), use_container_width=True)
    else:
        st.info("В данных не найдено объектов с дефектами (defect_found == 1).")

    st.markdown("---")

if st.button("Сформировать GPT-отчёт"):
    with st.spinner("GPT анализирует данные..."):
        st.info("GPT временно недоступен. Отчёт не сформирован.")


# ---------- МЕНЮ СТРАНИЦ ----------

st.sidebar.title("IntegrityOS – Demo")

page = st.sidebar.radio(
    "Выберите страницу",
    [
        "Импорт данных",
        "Карта",
        "Дефекты",
        "Дашборд",
        "Отчёт",
    ],
)

if page == "Импорт данных":
    page_import()
elif page == "Карта":
    page_map()
elif page == "Дефекты":
    page_defects()
elif page == "Дашборд":
    page_dashboard()
elif page == "Отчёт":
    page_report()
