from utils.db import init_db
init_db()
import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from openai import OpenAI
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

client = OpenAI(api_key="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")


def page_report():
    st.title("GPT-Отчёт по диагностике")

    if "diagnostics_df" not in st.session_state:
        st.warning("Сначала загрузите данные на странице 'Импорт данных'.")
        return

    diagnostics = st.session_state["diagnostics_df"]
    objects = st.session_state["objects_df"]

    # KPI
    total_inspections = len(diagnostics)
    total_objects = objects["object_id"].nunique()
    total_defects = diagnostics["defect_found"].sum()

    top_objects = (
        diagnostics[diagnostics["defect_found"] == 1]
        .groupby("object_id")
        .size()
        .sort_values(ascending=False)
        .head(5)
    )

    st.write("Общее количество обследований:", total_inspections)
    st.write("Количество объектов:", total_objects)
    st.write("Количество дефектов:", total_defects)

    if st.button("Сформировать отчёт"):
        st.spinner("GPT генерирует отчёт...")

        prompt = f"""
Сформируй технический отчёт по данным диагностики.

Обследований: {total_inspections}
Объектов: {total_objects}
Дефектов: {total_defects}

Проблемные объекты:
{top_objects.to_string()}

Структура отчёта:
1. Общая оценка состояния
2. Анализ критичности
3. Основные риски
4. Рекомендации
5. Приоритетные объекты

Пиши коротко, техническим языком.
"""

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        report = response.output_text
        st.subheader("Сформированный отчёт:")
        st.markdown(report)

        st.download_button(
            label="Скачать отчёт",
            data=report,
            file_name="report.txt",
            mime="text/plain"
        )


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
    st.title("Дашборд по диагностике и рискам")

    # --- 1. Проверяем, что данные загружены ---
    diagnostics_df = st.session_state.get("diagnostics_df")
    objects_df = st.session_state.get("objects_df")

    if diagnostics_df is None:
        st.warning("Сначала загрузите данные на странице «Импорт данных».")
        return

    # Копия, чтобы не портить оригинал
    diagnostics = diagnostics_df.copy()

    # --- 2. Лёгкая предобработка ---

    # Дата → год
    if "date" in diagnostics.columns:
        diagnostics["date"] = pd.to_datetime(diagnostics["date"], errors="coerce")
        diagnostics["year"] = diagnostics["date"].dt.year
    else:
        diagnostics["year"] = None

    # Флаг дефекта: приведём к int (если есть колонка)
    if "defect_found" in diagnostics.columns:
        diagnostics["defect_found"] = diagnostics["defect_found"].astype(int)
    else:
        diagnostics["defect_found"] = 0

    # --- 3. Верхние KPI (метрики) ---

    total_inspections = len(diagnostics)
    total_objects = (
        diagnostics["object_id"].nunique()
        if "object_id" in diagnostics.columns
        else None
    )
    total_defects = int(diagnostics["defect_found"].sum())

    if "ml_label" in diagnostics.columns:
        high_crit_count = (diagnostics["ml_label"] == "high").sum()
        medium_crit_count = (diagnostics["ml_label"] == "medium").sum()
        normal_crit_count = (diagnostics["ml_label"] == "normal").sum()
    else:
        high_crit_count = medium_crit_count = normal_crit_count = None

    st.subheader("Ключевые показатели")

    kpi_cols = st.columns(4)

    with kpi_cols[0]:
        st.metric(
            label="Всего обследований",
            value=f"{total_inspections}",
        )

    with kpi_cols[1]:
        if total_objects is not None:
            st.metric(
                label="Уникальных объектов",
                value=f"{total_objects}",
            )
        else:
            st.metric(
                label="Уникальных объектов",
                value="—",
            )

    with kpi_cols[2]:
        st.metric(
            label="Найдено дефектов",
            value=f"{total_defects}",
        )

    with kpi_cols[3]:
        if high_crit_count is not None:
            st.metric(
                label="High-критичность",
                value=f"{high_crit_count}",
                help="Количество записей, отнесённых к классу риска high по ML-модели",
            )
        else:
            st.metric(
                label="High-критичность",
                value="—",
            )

    st.markdown("---")

    # --- 4. График: дефекты по методам контроля ---

    st.subheader("Дефекты по методам контроля")

    if "method" in diagnostics.columns:
        by_method = (
            diagnostics.groupby("method", as_index=False)["defect_found"]
            .sum()
            .rename(columns={"defect_found": "defects"})
        )

        fig_methods = px.bar(
            by_method,
            x="method",
            y="defects",
            title="Количество дефектов по методам контроля",
            labels={"method": "Метод контроля", "defects": "Количество дефектов"},
        )
        fig_methods.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_methods, use_container_width=True)
    else:
        st.info("В данных нет колонки 'method' — график по методам контроля недоступен.")

    st.markdown("---")

    # --- 5. График: распределение по критичности (ML labels) ---

    st.subheader("Распределение по критичности (ML-классификация)")

    if "ml_label" in diagnostics.columns:
        by_label = (
            diagnostics["ml_label"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "ml_label", "ml_label": "count"})
        )

        fig_labels = px.pie(
            by_label,
            names="ml_label",
            values="count",
            title="Распределение записей по критичности",
        )
        st.plotly_chart(fig_labels, use_container_width=True)

        # Дополнительно — текстовая сводка
        st.caption(
            "На диаграмме видно долю записей с критичностью normal / medium / high. "
            "Эти значения рассчитываются ML-моделью на основе атрибутов диагностики."
        )
    else:
        st.info("В данных нет колонки 'ml_label' — распределение по критичности недоступно.")

    st.markdown("---")

    # --- 6. Динамика обследований по годам ---

    st.subheader("Динамика обследований по годам")

    if diagnostics["year"].notna().any():
        by_year = (
            diagnostics.dropna(subset=["year"])
            .groupby("year", as_index=False)
            .size()
            .rename(columns={"size": "inspections"})
        )

        fig_year = px.line(
            by_year,
            x="year",
            y="inspections",
            markers=True,
            title="Количество обследований по годам",
            labels={"year": "Год", "inspections": "Количество обследований"},
        )
        fig_year.update_layout(xaxis=dict(dtick=1), margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_year, use_container_width=True)
    else:
        st.info("В данных нет корректной даты обследования — график по годам недоступен.")

    st.markdown("---")

    # --- 7. Топ-5 объектов по количеству дефектов ---

    st.subheader("Топ-5 объектов по количеству дефектов")

    if "object_id" in diagnostics.columns:
        # Считаем только дефектные записи
        defect_rows = diagnostics[diagnostics["defect_found"] == 1]
        if not defect_rows.empty:
            top_objects = (
                defect_rows.groupby("object_id", as_index=False)["defect_found"]
                .count()
                .rename(columns={"defect_found": "defects"})
                .sort_values("defects", ascending=False)
                .head(5)
            )

            # При наличии objects_df можно подтянуть, например, имя/тип объекта
            if objects_df is not None and "object_id" in objects_df.columns:
                # Попробуем слить по object_id
                top_objects = top_objects.merge(
                    objects_df,
                    on="object_id",
                    how="left",
                    suffixes=("", "_obj"),
                )

            st.dataframe(
                top_objects,
                use_container_width=True,
            )
            st.caption(
                "Таблица показывает объекты с наибольшим количеством зафиксированных дефектов. "
                "Они являются приоритетными кандидатами для детального анализа и планирования ремонтных работ."
            )
        else:
            st.info("В данных нет записей с дефектами (defect_found == 1).")
    else:
        st.info("В данных нет колонки 'object_id' — невозможно построить топ объектов.")



def page_report():
    st.title("Отчёт по рискам")

    if st.session_state.diagnostics_df is None:
        st.warning("Сначала загрузите данные на странице 'Импорт данных'.")
        return

    diagnostics_df = st.session_state.diagnostics_df.copy()

    st.write("Ниже будет текстовый отчёт с использованием GPT.")

    if st.button("Сгенерировать отчёт (через GPT)"):
        # TODO: собрать статистику и вызвать generate_gpt_report(...)
        # Сейчас просто заглушка
        dummy_report = """
        Пример отчёта:
        - Общее число диагностик: {}
        - (Потом сюда подставим реальные цифры и текст от GPT)
        """.format(len(diagnostics_df))
        st.text(dummy_report)


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
