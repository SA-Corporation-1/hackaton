import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from openai import OpenAI

from utils.db import init_db, SessionLocal, Object, Inspection, Defect
from datetime import datetime

# инициализируем БД (создаст таблицы, если их нет)
init_db()

# ---------- ГЛОБАЛЬНОЕ СОСТОЯНИЕ ----------

if "objects_df" not in st.session_state:
    st.session_state.objects_df = None

if "diagnostics_df" not in st.session_state:
    st.session_state.diagnostics_df = None

if "processed_df" not in st.session_state:
    st.session_state.processed_df = None


# ---------- ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ ----------

def import_objects_to_db(objects_df: pd.DataFrame):
    """Сохраняем данные Objects.csv в таблицу objects."""
    session = SessionLocal()
    try:
        for _, row in objects_df.iterrows():
            try:
                obj = Object(
                    id=int(row["object_id"]),
                    object_name=str(row.get("object_name", "")),
                    object_type=str(row.get("object_type", "")),
                    pipeline=str(row.get("pipeline", "")),
                    lat=float(row["lat"]) if "lat" in row and pd.notna(row["lat"]) else None,
                    lon=float(row["lon"]) if "lon" in row and pd.notna(row["lon"]) else None,
                    year=int(row["year"]) if "year" in row and pd.notna(row["year"]) else None,
                    material=str(row.get("material", "")),
                )
                session.merge(obj)   # upsert
            except Exception as e:
                print("Ошибка при импорте объекта:", e)
                continue
        session.commit()
    finally:
        session.close()


def import_diagnostics_to_db(diagnostics_df: pd.DataFrame):
    """Сохраняем данные Diagnostics.csv в таблицы inspections и defects."""
    session = SessionLocal()
    try:
        for _, row in diagnostics_df.iterrows():
            try:
                date_raw = row.get("date", None)
                date_parsed = pd.to_datetime(date_raw, errors="coerce")
                if pd.isna(date_parsed):
                    continue

                defect_raw = str(row.get("defect_found", "")).lower()
                defect_found = defect_raw in ("1", "true", "yes", "да")

                insp = Inspection(
                    id=int(row["diag_id"]),
                    object_id=int(row["object_id"]),
                    date=date_parsed.date(),
                    method=str(row.get("method", "")),
                    temperature=float(row["temperature"]) if "temperature" in row and pd.notna(row["temperature"]) else None,
                    humidity=float(row["humidity"]) if "humidity" in row and pd.notna(row["humidity"]) else None,
                    illumination=float(row["illumination"]) if "illumination" in row and pd.notna(row["illumination"]) else None,
                    defect_found=defect_found,
                    defect_descr=str(row.get("defect_description", "")),
                    quality_grade=str(row.get("quality_grade", "")),
                    param1=float(row["param1"]) if "param1" in row and pd.notna(row["param1"]) else None,
                    param2=float(row["param2"]) if "param2" in row and pd.notna(row["param2"]) else None,
                    param3=float(row["param3"]) if "param3" in row and pd.notna(row["param3"]) else None,
                    ml_label=str(row.get("ml_label", "")),
                )
                session.merge(insp)

                if defect_found:
                    defect = Defect(
                        inspection_id=insp.id,
                        depth=insp.param1,
                        length=insp.param2,
                        width=insp.param3,
                        severity=insp.ml_label,
                        description=insp.defect_descr,
                    )
                    session.add(defect)

            except Exception as e:
                print("Ошибка при импорте диагностики:", e)
                continue

        session.commit()
    finally:
        session.close()


def debug_db_panel():
    """Небольшая панель проверки, что база реально работает."""
    st.markdown("### Проверка базы данных (debug)")
    try:
        session = SessionLocal()
        objects_count = session.query(Object).count()
        inspections_count = session.query(Inspection).count()
        defects_count = session.query(Defect).count()
        session.close()

        st.write(f"Объектов в базе: **{objects_count}**")
        st.write(f"Диагностик в базе: **{inspections_count}**")
        st.write(f"Дефектов в базе: **{defects_count}**")
    except Exception as e:
        st.error(f"Ошибка при работе с базой данных: {e}")


# ---------- КЛИЕНТ OPENAI ----------

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# ---------- ФУНКЦИИ ДЛЯ БЛОКОВ ----------

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

        # сохраняем в session_state, как раньше
        st.session_state.objects_df = objects_df
        st.session_state.diagnostics_df = diagnostics_df
        st.session_state.processed_df = diagnostics_df  # временно

        # дополнительно сохраняем в БД
        import_objects_to_db(objects_df)
        import_diagnostics_to_db(diagnostics_df)

        st.success("Данные загружены и сохранены в базе данных!")

        st.write("Objects (первые 5 строк):")
        st.dataframe(objects_df.head())
        st.write("Diagnostics (первые 5 строк):")
        st.dataframe(diagnostics_df.head())

        debug_db_panel()


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

    cols_to_show = [
        col for col in diagnostics_df.columns
        if col not in ["date_parsed"]
    ]
    st.dataframe(diagnostics_df[cols_to_show].head(300))

    st.subheader("Краткая статистика")
    st.write("Количество диагностик:", len(diagnostics_df))

    if crit_col is not None:
        st.write("Распределение по критичности:")
        st.dataframe(diagnostics_df[crit_col].value_counts())


def page_dashboard():
    st.title("Дашборд диагностики объектов")

    # проверяем наличие данных
    if "objects_df" not in st.session_state or "diagnostics_df" not in st.session_state:
        st.warning("Сначала загрузите данные на странице «Импорт данных».")
        return

    objects = st.session_state["objects_df"].copy()
    diagnostics = st.session_state["diagnostics_df"].copy()

    if objects.empty or diagnostics.empty:
        st.warning("Таблицы пустые. Проверьте загрузку CSV.")
        return

    # дата → год
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

    # 3. ФИЛЬТРЫ
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

    # 4. KPI
    st.markdown("### Сводные показатели (с учётом фильтров)")

    total_inspections = len(filtered)
    total_objects = filtered["object_id"].nunique() if "object_id" in filtered.columns else 0
    total_defects = int(filtered["defect_found"].sum())

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
            defects.groupby("method")["defect_found"].sum().reset_index()
        )
        fig = px.bar(
            df_methods,
            x="method",
            y="defect_found",
            labels={"method": "Метод контроля", "defect_found": "Количество дефектов"},
            title="Количество дефектов по методам контроля",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет данных о дефектах для построения графика.")


def page_report():
    st.title("GPT-Отчёт по результатам диагностики")

    # 1. Проверяем, что данные загружены
    if "diagnostics_df" not in st.session_state or "objects_df" not in st.session_state:
        st.warning("Сначала загрузите данные на странице «Импорт данных».")
        return

    # 2. Берём копии датафреймов
    objects = st.session_state["objects_df"].copy()
    diagnostics = st.session_state["diagnostics_df"].copy()

    if diagnostics.empty or objects.empty:
        st.warning("Таблицы пустые. Загрузите корректные CSV.")
        return

    # 3. ГАРАНТИРУЕМ НУЖНЫЕ КОЛОНКИ

    # date → year
    if "date" in diagnostics.columns:
        diagnostics["date"] = pd.to_datetime(diagnostics["date"], errors="coerce")
        diagnostics["year"] = diagnostics["date"].dt.year
    else:
        diagnostics["year"] = None

    # defect_found: если нет — создаём из severity
    if "defect_found" not in diagnostics.columns:
        if "severity" in diagnostics.columns:
            diagnostics["defect_found"] = diagnostics["severity"].apply(
                lambda x: 1 if str(x).lower() != "low" else 0
            )
        else:
            diagnostics["defect_found"] = 0

    # ml_label: если нет — делаем из severity
    if "ml_label" not in diagnostics.columns:
        if "severity" in diagnostics.columns:
            diagnostics["ml_label"] = diagnostics["severity"].astype(str).str.lower()
        else:
            diagnostics["ml_label"] = "unknown"

    # 4. KPI
    total_inspections = len(diagnostics)
    total_objects = objects["object_id"].nunique() if "object_id" in objects.columns else 0
    total_defects = int(diagnostics["defect_found"].sum())

    # Методы контроля (только по дефектам)
    if "method" in diagnostics.columns:
        method_stats = (
            diagnostics[diagnostics["defect_found"] == 1]
            .groupby("method")["defect_found"]
            .sum()
            .sort_values(ascending=False)
            .to_dict()
        )
    else:
        method_stats = {}

    # Критичность
    if "ml_label" in diagnostics.columns:
        crit_stats = diagnostics["ml_label"].value_counts().to_dict()
    else:
        crit_stats = {}

    # Динамика по годам
    if "year" in diagnostics.columns and diagnostics["year"].notna().any():
        year_stats = (
            diagnostics.dropna(subset=["year"])
            .groupby("year")["object_id"]
            .count()
            .sort_index()
            .to_dict()
        )
    else:
        year_stats = {}

    # Топ-объекты
    if "object_id" in diagnostics.columns:
        top_objects_series = (
            diagnostics[diagnostics["defect_found"] == 1]
            .groupby("object_id")["defect_found"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        top_objects = top_objects_series.to_dict()
    else:
        top_objects = {}

    # 5. Показываем сводку на экране
    st.subheader("Сводная информация (данные дашборда)")
    st.write("Обследований:", total_inspections)
    st.write("Объектов:", total_objects)
    st.write("Дефектов:", total_defects)
    st.write("Методы (дефекты по методам):", method_stats)
    st.write("Распределение по критичности:", crit_stats)
    st.write("Динамика по годам:", year_stats)
    st.write("Топ проблемных объектов:", top_objects)

    # 6. GPT-отчёт
    if st.button("Сформировать отчёт"):
        with st.spinner("Генерация полного инженерного отчёта..."):

            prompt = f"""
Ты — инженер по промышленной безопасности. 
Ниже данные технического дашборда IntegrityOS, который анализирует объекты инфраструктуры.

Проанализируй эти данные как эксперт и составь:

1) Общую оценку ситуации  
2) Краткий анализ дефектов  
3) Какие методы контроля наиболее эффективны  
4) Какие объекты наиболее проблемные и почему  
5) Что нужно сделать в первую очередь (приоритетный план работы)  
6) Риски, если ничего не делать  
7) Профессиональные рекомендации инженера  

ДАННЫЕ ДАШБОРДА:


- Всего обследований: {total_inspections}
- Всего объектов: {total_objects}
- Количество дефектов: {total_defects}

Методы контроля (дефекты):
{method_stats}

Распределение по критичности:
{crit_stats}

Динамика по годам:
{year_stats}

Топ проблемных объектов (object_id → количество дефектов):
{top_objects}

Проанализируй эти данные и сформируй профессиональный технический отчёт. 
Не выдумывай данные — анализируй только то, что дано.
"""

            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=prompt,
            )

            report = response.output_text

        st.subheader("Готовый GPT-Отчёт")
        st.markdown(report)

        st.download_button(
            "Скачать отчёт",
            report,
            "integrity_gpt_report.txt",
            "text/plain"
        )


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
