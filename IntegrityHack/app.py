import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from openai import OpenAI
from os import getenv
from utils.db import init_db, SessionLocal, Object, Inspection, Defect
from datetime import datetime
from sqlalchemy import func


st.set_page_config(
    page_title="IntegrityOS – Demo",
    page_icon="🛰️",
    layout="wide",
)

# инициализируем БД (создаст таблицы, если их нет)
init_db()

# ---------- ГЛОБАЛЬНОЕ СОСТОЯНИЕ ----------

if "objects_df" not in st.session_state:
    st.session_state.objects_df = None

if "diagnostics_df" not in st.session_state:
    st.session_state.diagnostics_df = None

if "processed_df" not in st.session_state:
    st.session_state.processed_df = None


# ---------- МУЛЬТИЯЗЫЧНЫЙ UI ----------
# ---------- МУЛЬТИЯЗЫЧНЫЙ UI ----------
UI_TEXTS = {
    "ru": {
        "lang_name": "Русский",

        # Импорт
        "import_title": "Импорт данных",
        "objects_file": "Файл объектов (CSV)",
        "diagn_file": "Файл диагностик (CSV)",
        "load_btn": "Загрузить и обработать",
        "import_success": "Данные успешно загружены!",
        "import_first": "Сначала импортируйте данные.",
        "no_latlon": "В данных отсутствуют координаты (lat/lon).",

        # Карта
        "filters_title": "Фильтры",
        "object_type": "Тип объекта",
        "criticality": "Критичность",
        "quick_select": "Быстрый выбор",
        "only_high": "Только High",
        "high_medium": "High + Medium",
        "all": "Все",
        "map_title": "Карта объектов",
        "map_subtitle": "Интерактивная карта",
        "table_title": "Таблица объектов",
        "summary_title": "Сводка",
        "objects_metric": "Объектов",
        "high_metric": "High-крит.",
        "medium_metric": "Medium-крит.",
        "no_objects_for_filters": "Объекты не найдены для выбранных фильтров.",

        # ДЕФЕКТЫ
        "defects_title": "Список дефектов / диагностик",
        "defects_method": "Метод контроля",
        "defects_crit": "Критичность",
        "defects_date_range": "Диапазон дат",
        "defects_no_records": "По выбранным фильтрам нет записей.",
        "defects_table": "Таблица диагностик",
        "defects_summary": "Краткая статистика",
        "defects_count": "Количество диагностик",
        "defects_crit_dist": "Распределение по критичности",

        # ИСТОРИЯ
        "history_title": "История диагностик по объекту",
        "history_select_object": "Выберите объект",
        "history_no_objects": "В базе нет объектов. Загрузите данные на странице 'Импорт данных'.",
        "history_no_inspections": "Для выбранного объекта нет диагностик.",
        "history_table": "История обследований",
        "history_stats": "Статистика по критичности",
        "history_col_date": "Дата",
        "history_col_method": "Метод",
        "history_col_defect": "Есть дефект",
        "history_col_crit": "Критичность (ml_label)",
        "history_col_descr": "Описание",

        # ДАШБОРД
        "dashboard_title": "Дашборд диагностических данных",
        "dashboard_kpi_title": "KPI — ключевые показатели",
        "dashboard_kpi_inspections": "Обследований",
        "dashboard_kpi_objects": "Уникальных объектов",
        "dashboard_kpi_defects": "Найдено дефектов",
        "dashboard_kpi_high": "Высокая критичность",
        "dashboard_crit_title": "Распределение по критичности",
        "dashboard_crit_chart_title": "Распределение по критичности",
        "dashboard_crit_no_data": "Нет данных о критичности.",

        # ОТЧЁТ
        "report_title": "GPT-Отчёт по результатам диагностики",
        "report_summary_title": "Сводная информация",
        "report_generate_btn": "Сформировать отчёт",
        "report_wait_msg": "Генерируем отчёт…",
        "report_no_data": "Нет данных для отчёта. Загрузите CSV сначала.",

        # ЛЕВОЕ МЕНЮ
        "menu_select_page": "Бетти таңдаңыз",
        "menu_import": "Импорт данных",
        "menu_map": "Карта",
        "menu_defects": "Актуал",
        "menu_history": "История объекта",
        "menu_dashboard": "Дашборд",
        "menu_report": "Отчёт",

        # Импорт – подсказки
        "upload_hint": "Загрузите CSV-файлы объектов и диагностик.",
        "objects_label": "Файл объектов (CSV)",
        "diag_label": "Файл диагностик (CSV)",
        "upload_error_both": "Пожалуйста, загрузите оба файла.",
    },

    "kk": {
        "lang_name": "Қазақша",

        # Импорт
        "import_title": "Деректерді импорттау",
        "objects_file": "Объектілер файлы (CSV)",
        "diagn_file": "Диагностика файлы (CSV)",
        "load_btn": "Жүктеу және өңдеу",
        "import_success": "Деректер сәтті жүктелді!",
        "import_first": "Алдымен деректерді жүктеңіз.",
        "no_latlon": "lat/lon координаттары жоқ.",

        # Карта
        "filters_title": "Сүзгілер",
        "object_type": "Объект түрі",
        "criticality": "Критикалылық",
        "quick_select": "Жылдам таңдау",
        "only_high": "Тек High",
        "high_medium": "High + Medium",
        "all": "Барлығы",
        "map_title": "Объектілер картасы",
        "map_subtitle": "Интерактивті карта",
        "table_title": "Объектілер кестесі",
        "summary_title": "Жиынтық",
        "objects_metric": "Объектілер",
        "high_metric": "Жоғары крит.",
        "medium_metric": "Орта крит.",
        "no_objects_for_filters": "Сүзгі бойынша объект жоқ.",

        # ДЕФЕКТТЕР
        "defects_title": "Ақаулар тізімі",
        "defects_method": "Бақылау әдісі",
        "defects_crit": "Критикалылық",
        "defects_date_range": "Күндер диапазоны",
        "defects_no_records": "Бұл сүзгі бойынша дерек жоқ.",
        "defects_table": "Диагностика кестесі",
        "defects_summary": "Қысқаша статистика",
        "defects_count": "Диагностика саны",
        "defects_crit_dist": "Критикалылық бойынша үлестірім",

        # ТАРИХ
        "history_title": "Объект диагностика тарихы",
        "history_select_object": "Объект таңдаңыз",
        "history_no_objects": "Базада объект жоқ. Алдымен CSV жүктеңіз.",
        "history_no_inspections": "Бұл объект бойынша диагностика жоқ.",
        "history_table": "Тексеру тарихы",
        "history_stats": "Критикалылық статистикасы",
        "history_col_date": "Күні",
        "history_col_method": "Әдіс",
        "history_col_defect": "Ақау бар",
        "history_col_crit": "Критикалылық (ml_label)",
        "history_col_descr": "Сипаттамасы",

        # ДАШБОРД
        "dashboard_title": "Диагностика деректері дашборды",
        "dashboard_kpi_title": "KPI — негізгі көрсеткіштер",
        "dashboard_kpi_inspections": "Тексерулер",
        "dashboard_kpi_objects": "Уникалды объектілер",
        "dashboard_kpi_defects": "Анықталған ақаулар",
        "dashboard_kpi_high": "Жоғары критич.",
        "dashboard_crit_title": "Критикалылық бойынша үлестірім",
        "dashboard_crit_chart_title": "Критикалылық бойынша диаграмма",
        "dashboard_crit_no_data": "Критикалылық мәліметтері жоқ.",

        # ЕСЕП
        "report_title": "GPT-Есеп (диагностика нәтижелері)",
        "report_summary_title": "Жиынтық ақпарат",
        "report_generate_btn": "Есепті құру",
        "report_wait_msg": "GPT есеп жасауда…",
        "report_no_data": "Есеп үшін мәлімет жоқ. Алдымен CSV жүктеңіз.",

        # МЕНЮ
        "menu_select_page": "Бетті таңдаңыз",
        "menu_import": "Деректерді импорттау",
        "menu_map": "Карта",
        "menu_defects": "Ақаулар",
        "menu_history": "Объект тарихы",
        "menu_dashboard": "Дашборд",
        "menu_report": "Есеп",

        # Импорт
        "upload_hint": "Объект және диагностика CSV файлдарын жүктеңіз.",
        "objects_label": "Объектілер файлы (CSV)",
        "diag_label": "Диагностика файлы (CSV)",
        "upload_error_both": "Екі файлды да жүктеңіз.",
    },

    "en": {
        "lang_name": "English",

        # Import
        "import_title": "Data import",
        "objects_file": "Objects file (CSV)",
        "diagn_file": "Diagnostics file (CSV)",
        "load_btn": "Upload and process",
        "import_success": "Data loaded successfully!",
        "import_first": "Please upload data first.",
        "no_latlon": "Missing coordinates (lat/lon).",

        # Map
        "filters_title": "Filters",
        "object_type": "Object type",
        "criticality": "Criticality",
        "quick_select": "Quick select",
        "only_high": "Only High",
        "high_medium": "High + Medium",
        "all": "All",
        "map_title": "Objects map",
        "map_subtitle": "Interactive map",
        "table_title": "Objects table",
        "summary_title": "Summary",
        "objects_metric": "Objects",
        "high_metric": "High crit.",
        "medium_metric": "Medium crit.",
        "no_objects_for_filters": "No objects for selected filters.",

        # Defects
        "defects_title": "Diagnostics list",
        "defects_method": "Control method",
        "defects_crit": "Criticality",
        "defects_date_range": "Date range",
        "defects_no_records": "No records for these filters.",
        "defects_table": "Diagnostics table",
        "defects_summary": "Summary statistics",
        "defects_count": "Diagnostics count",
        "defects_crit_dist": "Criticality distribution",

        # History
        "history_title": "Object diagnostics history",
        "history_select_object": "Select object",
        "history_no_objects": "No objects in DB. Upload CSV first.",
        "history_no_inspections": "No diagnostics for this object.",
        "history_table": "Inspection history",
        "history_stats": "Criticality stats",
        "history_col_date": "Date",
        "history_col_method": "Method",
        "history_col_defect": "Defect",
        "history_col_crit": "Criticality (ml_label)",
        "history_col_descr": "Description",

        # Dashboard
        "dashboard_title": "Diagnostics dashboard",
        "dashboard_kpi_title": "KPI — key indicators",
        "dashboard_kpi_inspections": "Inspections",
        "dashboard_kpi_objects": "Unique objects",
        "dashboard_kpi_defects": "Found defects",
        "dashboard_kpi_high": "High criticality",
        "dashboard_crit_title": "Criticality distribution",
        "dashboard_crit_chart_title": "Criticality distribution chart",
        "dashboard_crit_no_data": "No criticality data.",

        # Report
        "report_title": "GPT Report on diagnostics",
        "report_summary_title": "Summary information",
        "report_generate_btn": "Generate report",
        "report_wait_msg": "Generating report with GPT…",
        "report_no_data": "No data for report.",

        # MENU
        "menu_select_page": "Select page",
        "menu_import": "Import data",
        "menu_map": "Map",
        "menu_defects": "Defects",
        "menu_history": "Object history",
        "menu_dashboard": "Dashboard",
        "menu_report": "Report",

        # Import
        "upload_hint": "Upload CSV files with objects and diagnostics.",
        "objects_label": "Objects file (CSV)",
        "diag_label": "Diagnostics file (CSV)",
        "upload_error_both": "Please upload both files.",
    },
}



TYPE_LABELS = {
    "en": {
        "Lake": "Lake",
    },
    "ru": {
        "Lake": "Озеро",
    },
    "kk": {
        "Lake": "Көл",
    },
}

CRIT_LABELS = {
    "en": {
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
    },
    "ru": {
        "High": "Высокая",
        "Medium": "Средняя",
        "Low": "Низкая",
    },
    "kk": {
        "High": "Жоғары",
        "Medium": "Орташа",
        "Low": "Төмен",
    },
}



# язык по умолчанию — русский
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "ru"


def t(key: str) -> str:
    """Берём строку для текущего языка, если нет — возвращаем ключ."""
    lang = st.session_state.get("ui_lang", "ru")
    return UI_TEXTS.get(lang, UI_TEXTS["ru"]).get(key, key)



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
    """Сохраняем Diagnostics.csv в таблицы inspections и defects."""
    session = SessionLocal()
    try:
        for idx, row in diagnostics_df.iterrows():
            try:
                # генерируем diag_id по порядку (1, 2, 3, ...)
                diag_id = int(idx) + 1

                # дата
                date_raw = row.get("date", None)
                date_parsed = pd.to_datetime(date_raw, errors="coerce")
                if pd.isna(date_parsed):
                    continue

                # severity → defect_found + ml_label
                severity_raw = str(row.get("severity", "")).strip()
                severity_lower = severity_raw.lower()
                defect_found = severity_lower != "low"  # всё, что не Low — считаем дефектом

                insp = Inspection(
                    id=diag_id,
                    object_id=int(row["object_id"]),
                    date=date_parsed.date(),
                    method=str(row.get("method", "")),
                    temperature=None,
                    humidity=None,
                    illumination=None,
                    defect_found=defect_found,
                    defect_descr=str(row.get("description", "")),
                    quality_grade=None,
                    param1=None,
                    param2=None,
                    param3=None,
                    ml_label=severity_lower,  # high / medium / low
                )
                session.merge(insp)

                # если есть дефект — создаём запись в таблице defects
                if defect_found:
                    defect = Defect(
                        inspection_id=insp.id,
                        depth=None,
                        length=None,
                        width=None,
                        severity=severity_lower,
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
    st.title(t("import_title"))

    st.write(t("upload_hint"))

    # 1) Загрузка файлов
    objects_file = st.file_uploader(t("objects_label"), type="csv")
    diagnostics_file = st.file_uploader(t("diag_label"), type="csv")

    # 2) Кнопка "Загрузить и обработать"
    if st.button(t("load_btn")):
        if objects_file is None or diagnostics_file is None:
            st.error(t("upload_error_both"))
            return

        # 3) Чтение CSV
        try:
            objects_df = pd.read_csv(objects_file)
            diagnostics_df = pd.read_csv(diagnostics_file)
        except Exception as e:
            st.error(f"Ошибка при чтении CSV: {e}")
            return

        # 4) Кладём в session_state
        st.session_state.objects_df = objects_df
        st.session_state.diagnostics_df = diagnostics_df
        st.session_state.processed_df = diagnostics_df  # как было у тебя

        # 5) Сохраняем в БД
        try:
            import_objects_to_db(objects_df)
            import_diagnostics_to_db(diagnostics_df)
        except Exception as e:
            st.error(f"Ошибка при сохранении в базу данных: {e}")
            return

        # 6) Сообщение об успехе
        st.success(t("import_success"))

        # 7) Превью таблиц + debug
        st.write("Objects (первые 5 строк):")
        st.dataframe(objects_df.head())

        st.write("Diagnostics (первые 5 строк):")
        st.dataframe(diagnostics_df.head())

        debug_db_panel()



def page_map():
    import pydeck as pdk

    st.title(t("map_title"))

    # ---------- 1. Проверяем, что данные загружены ----------
    if st.session_state.objects_df is None:
        st.warning(t("import_first"))
        return

    objects_df = st.session_state.objects_df.copy()

    # Проверяем наличие координат
    required_cols = {"lat", "lon"}
    if not required_cols.issubset(objects_df.columns):
        st.error(t("no_latlon"))
        st.dataframe(objects_df.head())
        return

    # ---------- 2. Настраиваем признаки ----------
    # Столбец типа
    if "type" in objects_df.columns:
        type_col = "type"
    elif "object_type" in objects_df.columns:
        type_col = "object_type"
    else:
        type_col = None

    # Столбец критичности
    if "criticality" in objects_df.columns:
        crit_col = "criticality"
    elif "ml_label" in objects_df.columns:
        crit_col = "ml_label"
    else:
        crit_col = None

    # Язык интерфейса
    lang = st.session_state.get("ui_lang", "ru")

    # Локализация типа и критичности
    TYPE_LABELS = {
        "en": {"Lake": "Lake"},
        "ru": {"Lake": "Озеро"},
        "kk": {"Lake": "Көл"},
    }

    CRIT_LABELS = {
        "en": {"High": "High", "Medium": "Medium", "Low": "Low"},
        "ru": {"High": "Высокая", "Medium": "Средняя", "Low": "Низкая"},
        "kk": {"High": "Жоғары", "Medium": "Орташа", "Low": "Төмен"},
    }

    # ---------- 3. Лэйаут: фильтры + карта ----------
    filters_col, map_col = st.columns([1, 3])

    # ======== ФИЛЬТРЫ ========
    with filters_col:
        st.subheader(t("filters_title"))

        # ---- Фильтр по типу объекта ----
        if type_col:
            all_types = sorted(objects_df[type_col].dropna().unique())

            def type_format(v: str) -> str:
                return TYPE_LABELS.get(lang, {}).get(str(v), str(v))

            selected_types = st.multiselect(
                t("object_type"),
                options=all_types,
                default=all_types,
                format_func=type_format,
            )
            if selected_types:
                objects_df = objects_df[objects_df[type_col].isin(selected_types)]

        # ---- Фильтр по критичности ----
        if crit_col:
            all_crit = sorted(objects_df[crit_col].dropna().unique())

            def crit_format(v: str) -> str:
                return CRIT_LABELS.get(lang, {}).get(str(v), str(v))

            selected_crit = st.multiselect(
                t("criticality"),
                options=all_crit,
                default=all_crit,
                format_func=crit_format,
            )
            if selected_crit:
                objects_df = objects_df[objects_df[crit_col].isin(selected_crit)]

        # ---- Быстрый выбор ----
        st.markdown(f"**{t('quick_select')}:**")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button(t("only_high")) and crit_col:
                objects_df = objects_df[
                    objects_df[crit_col].astype(str).str.lower() == "high"
                ]
        with c2:
            if st.button(t("high_medium")) and crit_col:
                objects_df = objects_df[
                    objects_df[crit_col].astype(str)
                    .str.lower()
                    .isin(["high", "medium"])
                ]
        with c3:
            if st.button(t("all")):
                # просто оставляем objects_df как есть
                pass

        # Если после фильтров ничего не осталось
        if objects_df.empty:
            st.warning(t("no_objects_for_filters"))
            return

    # ======== КАРТА + ТАБЛИЦА ========
    with map_col:
        st.subheader(t("map_subtitle"))

        # ---------- 3.1. Авто zoom ----------
        lat_min, lat_max = float(objects_df["lat"].min()), float(
            objects_df["lat"].max()
        )
        lon_min, lon_max = float(objects_df["lon"].min()), float(
            objects_df["lon"].max()
        )
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        max_range = max(lat_range, lon_range)

        if max_range < 0.1:
            zoom = 12
        elif max_range < 1:
            zoom = 9
        elif max_range < 10:
            zoom = 6
        else:
            zoom = 4

        # ---------- 3.2. Цвет по критичности ----------
        def get_color(row):
            if not crit_col:
                return [0, 128, 255]  # синий по умолчанию
            crit = str(row[crit_col]).lower()
            if "high" in crit:
                return [255, 0, 0]  # красный
            elif "medium" in crit:
                return [255, 165, 0]  # оранжевый
            elif "low" in crit:
                return [0, 200, 0]  # зелёный
            else:
                return [100, 149, 237]  # голубой

        objects_df["color"] = objects_df.apply(get_color, axis=1)

        midpoint = (
            float(objects_df["lat"].mean()),
            float(objects_df["lon"].mean()),
        )

        viz_df = objects_df.copy()

        # ---------- 3.3. Формируем UI-поля по языку ----------

        # Имя объекта
        if lang == "kk" and "name_kk" in viz_df.columns:
            viz_df["name_ui"] = viz_df["name_kk"]
        elif lang == "en" and "name_en" in viz_df.columns:
            viz_df["name_ui"] = viz_df["name_en"]
        elif "name_ru" in viz_df.columns:
            viz_df["name_ui"] = viz_df["name_ru"]
        elif "name" in viz_df.columns:
            viz_df["name_ui"] = viz_df["name"]
        else:
            viz_df["name_ui"] = ""

        # Область / регион
        if lang == "kk" and "oblast_kk" in viz_df.columns:
            viz_df["region_ui"] = viz_df["oblast_kk"]
        elif lang == "en" and "oblast_en" in viz_df.columns:
            viz_df["region_ui"] = viz_df["oblast_en"]
        elif "oblast_ru" in viz_df.columns:
            viz_df["region_ui"] = viz_df["oblast_ru"]
        elif "oblast" in viz_df.columns:
            viz_df["region_ui"] = viz_df["oblast"]
        else:
            viz_df["region_ui"] = ""

        # Тип объекта (Lake → Озеро/Көл/т.б.)
        if type_col and type_col in viz_df.columns:
            def map_type(v):
                return TYPE_LABELS.get(lang, {}).get(str(v), str(v))

            viz_df["type_ui"] = viz_df[type_col].astype(str).map(map_type)
        else:
            viz_df["type_ui"] = ""

        # Тип воды
        if lang == "kk" and "water_type_kk" in viz_df.columns:
            viz_df["water_type_ui"] = viz_df["water_type_kk"]
        elif lang == "en" and "water_type_en" in viz_df.columns:
            viz_df["water_type_ui"] = viz_df["water_type_en"]
        elif "water_type_ru" in viz_df.columns:
            viz_df["water_type_ui"] = viz_df["water_type_ru"]
        elif "water_type" in viz_df.columns:
            viz_df["water_type_ui"] = viz_df["water_type"]
        else:
            viz_df["water_type_ui"] = ""

        # Фауна
        if lang == "kk" and "fauna_kk" in viz_df.columns:
            viz_df["fauna_ui"] = viz_df["fauna_kk"]
        elif lang == "en" and "fauna_en" in viz_df.columns:
            viz_df["fauna_ui"] = viz_df["fauna_en"]
        elif "fauna_ru" in viz_df.columns:
            viz_df["fauna_ui"] = viz_df["fauna_ru"]
        elif "fauna" in viz_df.columns:
            viz_df["fauna_ui"] = viz_df["fauna"]
        else:
            viz_df["fauna_ui"] = ""

        # Дата паспорта и тех. состояние – одинаковые для всех языков
        viz_df["passport_date_ui"] = (
            viz_df["passport_date"] if "passport_date" in viz_df.columns else ""
        )
        viz_df["tech_state_ui"] = (
            viz_df["tech_state"].astype(str)
            if "tech_state" in viz_df.columns
            else ""
        )

        # Координаты
        for src, dst in [
            ("coords_center", "coords_center_ui"),
            ("coords_north", "coords_north_ui"),
            ("coords_south", "coords_south_ui"),
            ("coords_east", "coords_east_ui"),
            ("coords_west", "coords_west_ui"),
        ]:
            if src in viz_df.columns:
                viz_df[dst] = viz_df[src]
            else:
                viz_df[dst] = ""

        # Критичность в UI
        if crit_col:
            def map_crit(v):
                return CRIT_LABELS.get(lang, {}).get(str(v), str(v))

            viz_df["crit_ui"] = viz_df[crit_col].astype(str).map(map_crit)
        else:
            viz_df["crit_ui"] = ""

        # Если нет object_id — создаём
        if "object_id" not in viz_df.columns:
            viz_df["object_id"] = range(1, len(viz_df) + 1)

        # ---------- 3.4. Лейблы для подписи полей ----------
        if lang == "kk":
            type_label = "Объект түрі"
            crit_label = "Критикалылық"
            id_label = "ID"
            region_label = "Облыс"
            water_type_label = "Су түрі"
            fauna_label = "Фауна"
            passport_label = "Паспорт күні"
            tech_label = "Тех. жағдай"
            coords_label = "Координаттар"
            center_label = "Ортасы"
            north_label = "Солтүстік"
            south_label = "Оңтүстік"
            east_label = "Шығыс"
            west_label = "Батыс"
        elif lang == "en":
            type_label = "Type"
            crit_label = "Criticality"
            id_label = "ID"
            region_label = "Region"
            water_type_label = "Water type"
            fauna_label = "Fauna"
            passport_label = "Passport date"
            tech_label = "Tech state"
            coords_label = "Coordinates"
            center_label = "Center"
            north_label = "North"
            south_label = "South"
            east_label = "East"
            west_label = "West"
        else:  # ru
            type_label = "Тип объекта"
            crit_label = "Критичность"
            id_label = "ID"
            region_label = "Область"
            water_type_label = "Тип воды"
            fauna_label = "Фауна"
            passport_label = "Дата паспорта"
            tech_label = "Тех. состояние"
            coords_label = "Координаты"
            center_label = "Центр"
            north_label = "Север"
            south_label = "Юг"
            east_label = "Восток"
            west_label = "Запад"

        # ---------- 3.5. Tooltip HTML ----------
        tooltip_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 12px; padding: 8px 10px;">
          <div style="font-weight: 600; font-size: 13px; margin-bottom: 6px;">{{name_ui}}</div>

          <div><b>{region_label}:</b> {{region_ui}}</div>
          <div><b>{type_label}:</b> {{type_ui}}</div>
          <div><b>{water_type_label}:</b> {{water_type_ui}}</div>
          <div><b>{fauna_label}:</b> {{fauna_ui}}</div>
          <div><b>{passport_label}:</b> {{passport_date_ui}}</div>
          <div><b>{tech_label}:</b> {{tech_state_ui}}</div>

          <hr style="border: 0; border-top: 1px solid #374151; margin: 6px 0;" />

          <div style="margin-bottom: 2px;"><b>{coords_label}:</b></div>
          <div>{center_label}: {{coords_center_ui}}</div>
          <div>{north_label}: {{coords_north_ui}}</div>
          <div>{south_label}: {{coords_south_ui}}</div>
          <div>{east_label}: {{coords_east_ui}}</div>
          <div>{west_label}: {{coords_west_ui}}</div>

          <hr style="border: 0; border-top: 1px solid #374151; margin: 6px 0;" />

          <div><b>{id_label}:</b> {{object_id}}</div>
          <div><b>{crit_label}:</b> {{crit_ui}}</div>
        </div>
        """

        # ---------- 3.6. PyDeck карта ----------
        tile_layer = pdk.Layer(
            "TileLayer",
            data="https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            min_zoom=0,
            max_zoom=22,
            tile_size=256,
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=viz_df,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius=80,
            pickable=True,
        )

        deck = pdk.Deck(
            layers=[tile_layer, layer],
            initial_view_state=pdk.ViewState(
                latitude=midpoint[0],
                longitude=midpoint[1],
                zoom=zoom,
                pitch=0,
            ),
            map_style=None,
            tooltip={"html": tooltip_html, "style": {"backgroundColor": "#111827", "color": "white"}},
        )

        st.pydeck_chart(deck, use_container_width=True)

        # ---------- 3.7. Таблица и метрики ----------
        st.subheader(t("table_title"))
        st.dataframe(
            objects_df.drop(columns=["color"], errors="ignore"),
            use_container_width=True,
        )

        st.markdown(f"### {t('summary_title')}")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(t("objects_metric"), len(objects_df))
        if crit_col:
            with c2:
                st.metric(
                    t("high_metric"),
                    int(
                        objects_df[crit_col]
                        .astype(str)
                        .str.lower()
                        .eq("high")
                        .sum()
                    ),
                )
            with c3:
                st.metric(
                    t("medium_metric"),
                    int(
                        objects_df[crit_col]
                        .astype(str)
                        .str.lower()
                        .eq("medium")
                        .sum()
                    ),
                )



def _crit_format(value: str) -> str:
    """Локализуем High/Medium/Low в зависимости от языка UI."""
    lang = st.session_state.get("ui_lang", "ru")
    key = str(value).strip()
    # пробуем и с заглавной, и в нижнем регистре
    return (
        CRIT_LABELS.get(lang, {}).get(key, None)
        or CRIT_LABELS.get(lang, {}).get(key.capitalize(), key)
    )


def page_defects():
    st.title(t("defects_title"))

    if st.session_state.diagnostics_df is None:
        st.warning(t("import_first"))
        return

    diagnostics_df = st.session_state.diagnostics_df.copy()

    st.subheader(t("filters_title"))

    # ---- фильтр по методу ----
    if "method" in diagnostics_df.columns:
        all_methods = sorted(diagnostics_df["method"].dropna().unique())
        selected_methods = st.multiselect(
            t("defects_method"),
            options=all_methods,
            default=all_methods,
        )
        if selected_methods:
            diagnostics_df = diagnostics_df[
                diagnostics_df["method"].isin(selected_methods)
            ]

    # ---- фильтр по критичности ----
    crit_col = None
    if "criticality" in diagnostics_df.columns:
        crit_col = "criticality"
    elif "severity" in diagnostics_df.columns:
        crit_col = "severity"

    if crit_col is not None:
        all_crit = sorted(diagnostics_df[crit_col].dropna().unique())
        selected_crit = st.multiselect(
            t("defects_crit"),
            options=all_crit,
            default=all_crit,
            format_func=_crit_format,
        )
        if selected_crit:
            diagnostics_df = diagnostics_df[
                diagnostics_df[crit_col].isin(selected_crit)
            ]

    # ---- фильтр по датам ----
    if "date" in diagnostics_df.columns:
        diagnostics_df["date_parsed"] = pd.to_datetime(
            diagnostics_df["date"], errors="coerce"
        )
        min_date = diagnostics_df["date_parsed"].min()
        max_date = diagnostics_df["date_parsed"].max()

        if pd.notnull(min_date) and pd.notnull(max_date):
            start_date, end_date = st.date_input(
                t("defects_date_range"),
                value=(min_date.date(), max_date.date()),
            )
            if start_date and end_date:
                mask = (
                    diagnostics_df["date_parsed"].dt.date >= start_date
                ) & (diagnostics_df["date_parsed"].dt.date <= end_date)
                diagnostics_df = diagnostics_df[mask]

    st.markdown("---")

    if diagnostics_df.empty:
        st.warning(t("defects_no_records"))
        return

    # Таблица
    st.subheader(t("defects_table"))
    cols_to_show = [
        c for c in diagnostics_df.columns if c not in ["date_parsed"]
    ]
    st.dataframe(diagnostics_df[cols_to_show].head(300), use_container_width=True)

    # Краткая статистика
    st.subheader(t("defects_summary"))
    st.write(f"{t('defects_count')}: {len(diagnostics_df)}")

    if crit_col is not None:
        st.write(t("defects_crit_dist") + ":")
        counts = diagnostics_df[crit_col].value_counts().reset_index()
        counts.columns = ["_crit_raw", "count"]
        counts[t("criticality")] = counts["_crit_raw"].apply(_crit_format)
        st.dataframe(
            counts[[t("criticality"), "count"]],
            use_container_width=True,
        )


def page_history():
    st.title(t("history_title"))

    session = SessionLocal()
    try:
        objects = session.query(Object).order_by(Object.id).all()
    except Exception as e:
        st.error(f"Ошибка при чтении объектов из базы: {e}")
        session.close()
        return

    if not objects:
        st.info(t("history_no_objects"))
        session.close()
        return

    # options: "2 – Кольсоль" и т.п.
    options = {
        f"{obj.id} – {obj.object_name}": obj.id for obj in objects
    }
    selected_label = st.selectbox(
        t("history_select_object"),
        list(options.keys()),
    )
    selected_object_id = options[selected_label]

    # тянем все обследования по объекту
    try:
        inspections = (
            session.query(Inspection)
            .filter(Inspection.object_id == selected_object_id)
            .order_by(Inspection.date.desc())
            .all()
        )
    except Exception as e:
        st.error(f"Ошибка при чтении диагностик из базы: {e}")
        session.close()
        return
    finally:
        session.close()

    if not inspections:
        st.info(t("history_no_inspections"))
        return

    # формируем DataFrame
    data = []
    col_date = t("history_col_date")
    col_method = t("history_col_method")
    col_defect = t("history_col_defect")
    col_crit = t("history_col_crit")
    col_descr = t("history_col_descr")

    for insp in inspections:
        data.append(
            {
                col_date: insp.date,
                col_method: insp.method,
                col_defect: bool(insp.defect_found),
                col_crit: _crit_format(insp.ml_label),
                col_descr: insp.defect_descr,
            }
        )

    df_hist = pd.DataFrame(data)

    st.subheader(t("history_table"))
    st.dataframe(df_hist, use_container_width=True)

    st.markdown("---")
    st.subheader(t("history_stats"))
    if col_crit in df_hist.columns:
        st.write(df_hist[col_crit].value_counts())


def page_dashboard():
    st.title(t("dashboard_title"))

    if (
        "diagnostics_df" not in st.session_state
        or "objects_df" not in st.session_state
    ):
        st.warning(t("import_first"))
        return

    diagnostics = st.session_state["diagnostics_df"].copy()
    objects = st.session_state["objects_df"].copy()

    if diagnostics.empty or objects.empty:
        st.warning(t("no_objects_for_filters"))
        return

    # дата / год
    if "date" in diagnostics.columns:
        diagnostics["date"] = pd.to_datetime(
            diagnostics["date"], errors="coerce"
        )
        diagnostics["year"] = diagnostics["date"].dt.year
    else:
        diagnostics["year"] = None

    # severity нормализуем
    if "severity" in diagnostics.columns:
        diagnostics["severity"] = (
            diagnostics["severity"].astype(str).str.lower()
        )
    elif "criticality" in diagnostics.columns:
        diagnostics["severity"] = (
            diagnostics["criticality"].astype(str).str.lower()
        )
    else:
        diagnostics["severity"] = "unknown"

    if "defect_found" not in diagnostics.columns:
        diagnostics["defect_found"] = diagnostics["severity"].apply(
            lambda x: 0 if x == "low" else 1
        )

    st.markdown("## " + t("dashboard_kpi_title"))

    col1, col2, col3, col4 = st.columns(4)
    total_inspections = len(diagnostics)
    total_objects = objects["object_id"].nunique()
    total_defects = int(diagnostics["defect_found"].sum())
    total_high = (diagnostics["severity"] == "high").sum()

    col1.metric(t("dashboard_kpi_inspections"), total_inspections)
    col2.metric(t("dashboard_kpi_objects"), total_objects)
    col3.metric(t("dashboard_kpi_defects"), total_defects)
    col4.metric(t("dashboard_kpi_high"), total_high)

    st.markdown("---")

    # -------- распределение по критичности --------
    st.subheader(t("dashboard_crit_title"))

    if diagnostics["severity"].notna().any():
        crit_counts = (
            diagnostics["severity"].value_counts().reset_index()
        )
        crit_counts.columns = ["severity_raw", "count"]
        crit_counts["severity_ui"] = crit_counts["severity_raw"].apply(
            _crit_format
        )

        fig = px.bar(
            crit_counts,
            x="severity_ui",
            y="count",
            title=t("dashboard_crit_chart_title"),
            labels={
                "severity_ui": t("criticality"),
                "count": "count",
            },
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(t("dashboard_crit_no_data"))

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

            # Показ и HTML-версия
            st.subheader("Готовый GPT-Отчёт")
            st.markdown(report)

            html_text = report.strip()
            html_text = html_text.replace("\n\n", "</p><p>")
            html_text = html_text.replace("\n", "<br>")

            html_report = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>IntegrityOS – GPT-отчёт</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 30px;
            line-height: 1.6;
            font-size: 16px;
        }}
        p {{
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
<p>{html_text}</p>
</body>
</html>
"""

            st.download_button(
                "Скачать отчёт (HTML)",
                html_report,
                "integrity_gpt_report.html",
                "text/html"
            )

# ---------- МЕНЮ СТРАНИЦ ----------

st.sidebar.title("IntegrityOS – Demo")

# выбор языка интерфейса
lang_code = st.sidebar.selectbox(
    "Язык интерфейса",
    ["ru", "kk", "en"],
    format_func=lambda code: UI_TEXTS[code]["lang_name"],
    index=["ru", "kk", "en"].index(st.session_state.ui_lang),
)
st.session_state.ui_lang = lang_code

# выбор страницы — подписи берём из UI_TEXTS
page = st.sidebar.radio(
    t("menu_select_page"),
    ["menu_import", "menu_map", "menu_defects", "menu_history", "menu_dashboard", "menu_report"],
    format_func=lambda key: UI_TEXTS[lang_code][key],
)

# роутинг
if page == "menu_import":
    page_import()
elif page == "menu_map":
    page_map()
elif page == "menu_defects":
    page_defects()
elif page == "menu_history":
    page_history()
elif page == "menu_dashboard":
    page_dashboard()
elif page == "menu_report":
    page_report()
