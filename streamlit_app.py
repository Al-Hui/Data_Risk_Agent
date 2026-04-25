from __future__ import annotations

import html
import importlib.util
import io
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from data_risk_agent import AppConfig, DataRiskAgent
from data_risk_agent.models import RegistrationMode, RiskStatus, ValidationVerdict


st.set_page_config(page_title="Агент Риска Данных", layout="wide")


STATUS_LABELS = {
    RiskStatus.NEW: "Новый",
    RiskStatus.REJECTED: "Отклонен",
    RiskStatus.VALIDATED: "Подтвержден агентом",
    RiskStatus.AUTO_READY: "Подтвержден агентом, готов к авторегистрации",
    RiskStatus.AUTO_REGISTERED: "Подтвержден агентом и зарегистрирован",
    RiskStatus.NEEDS_REVIEW: "Требует проверки",
    RiskStatus.USER_EDITED: "Исправлен пользователем",
    RiskStatus.REGISTERED: "Зарегистрирован",
}

VERDICT_LABELS = {
    ValidationVerdict.PASS: "Подтвержден",
    ValidationVerdict.FAIL: "Не подтвержден",
    ValidationVerdict.REVIEW: "Нужна проверка",
}


@st.cache_resource
def load_agent() -> DataRiskAgent:
    return DataRiskAgent(AppConfig.default())


def inject_brand_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(33, 160, 56, 0.10), transparent 24%),
                linear-gradient(180deg, #f7fbf8 0%, #f2f7f3 100%);
        }
        .block-container {
            max-width: 1320px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }
        div[data-testid="stTabs"] button {
            font-weight: 600;
        }
        div.stButton > button {
            border-radius: 14px;
            border: 1px solid rgba(33, 160, 56, 0.18);
            background: linear-gradient(180deg, #ffffff 0%, #f3fbf5 100%);
            color: #134b22;
            font-weight: 600;
            min-height: 44px;
        }
        div.stButton > button:hover {
            border-color: rgba(33, 160, 56, 0.38);
            color: #0f3a1a;
        }
        .hero-shell {
            padding: 1.4rem 1.6rem;
            border-radius: 24px;
            background:
                linear-gradient(135deg, rgba(33, 160, 56, 0.96) 0%, rgba(50, 190, 80, 0.92) 100%);
            color: white;
            box-shadow: 0 22px 50px rgba(14, 80, 28, 0.18);
            margin-bottom: 1.1rem;
        }
        .hero-title {
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }
        .hero-subtitle {
            font-size: 1rem;
            line-height: 1.5;
            max-width: 880px;
            color: rgba(255,255,255,0.94);
        }
        .mini-stat {
            border-radius: 20px;
            padding: 1rem 1.1rem;
            background: rgba(255,255,255,0.86);
            border: 1px solid rgba(33, 160, 56, 0.10);
            box-shadow: 0 10px 25px rgba(33, 60, 40, 0.05);
        }
        .mini-stat-label {
            color: #51715c;
            font-size: 0.82rem;
            margin-bottom: 0.25rem;
        }
        .mini-stat-value {
            color: #163d22;
            font-size: 1.45rem;
            font-weight: 800;
            line-height: 1.05;
        }
        .mini-stat-sub {
            color: #5d7464;
            font-size: 0.86rem;
            margin-top: 0.35rem;
        }
        .section-kicker {
            color: #2f7a42;
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.3rem;
        }
        .section-title {
            color: #183a23;
            font-size: 1.25rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }
        .section-note {
            color: #567060;
            font-size: 0.95rem;
            margin-bottom: 0.9rem;
        }
        .status-chip {
            display: inline-block;
            padding: 0.3rem 0.7rem;
            border-radius: 999px;
            background: #e9f7ed;
            color: #176a2a;
            font-size: 0.84rem;
            font-weight: 700;
        }
        .verdict-box {
            border-radius: 18px;
            padding: 0.95rem 1rem;
            background: linear-gradient(180deg, #f9fcfa 0%, #f1f8f3 100%);
            border: 1px solid rgba(33, 160, 56, 0.11);
        }
        .decision-box {
            border-radius: 20px;
            padding: 1rem 1.1rem;
            background: linear-gradient(180deg, #f1fbf4 0%, #ffffff 100%);
            border: 1px solid rgba(33, 160, 56, 0.16);
        }
        .match-card {
            border-radius: 18px;
            padding: 1rem 1.05rem;
            background: #ffffff;
            border: 1px solid rgba(33, 160, 56, 0.12);
            box-shadow: 0 10px 24px rgba(31, 72, 43, 0.04);
            margin-bottom: 0.8rem;
        }
        .match-title {
            color: #163d22;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }
        .match-meta {
            color: #2b8744;
            font-size: 0.86rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }
        .soft-list {
            color: #32493a;
            margin-top: 0.4rem;
        }
        .method-note {
            border-radius: 18px;
            padding: 0.95rem 1rem;
            background: #f8faf8;
            border: 1px dashed rgba(33, 160, 56, 0.22);
            color: #506757;
        }
        .recommendation-shell {
            border-radius: 22px;
            padding: 1.15rem 1.2rem;
            background: linear-gradient(135deg, #eaf8ee 0%, #ffffff 100%);
            border: 1px solid rgba(33, 160, 56, 0.18);
            box-shadow: 0 12px 28px rgba(31, 72, 43, 0.05);
            margin-bottom: 1rem;
        }
        .recommendation-title {
            color: #1a4c28;
            font-size: 1.1rem;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }
        .queue-card-title {
            color: #183a23;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }
        .queue-card-meta {
            color: #547060;
            font-size: 0.9rem;
            margin-bottom: 0.55rem;
        }
        .queue-card-line {
            color: #274132;
            font-size: 0.92rem;
            margin-bottom: 0.18rem;
        }
        .queue-selected {
            color: #176a2a;
            font-weight: 700;
            font-size: 0.86rem;
            margin-bottom: 0.55rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_ui_state() -> None:
    st.session_state.setdefault("candidate_state", {})
    st.session_state.setdefault("decision_events", [])
    st.session_state.setdefault("flash_message", None)
    st.session_state.setdefault("pending_confirmation", None)


def ensure_candidate_state(candidates) -> None:
    saved_state = st.session_state["candidate_state"]
    for candidate in candidates:
        state = saved_state.setdefault(
            candidate.candidate_id,
            {
                "service_name": candidate.service_name,
                "service_id": candidate.service_id,
                "description": candidate.description,
                "status": candidate.status.value,
                "audit_log": list(candidate.audit_log),
                "generated_service_name": candidate.service_name,
                "generated_service_id": candidate.service_id,
                "generated_description": candidate.description,
            },
        )
        previous_generated_description = state.get("generated_description", candidate.description)
        previous_generated_service_name = state.get("generated_service_name", candidate.service_name)
        previous_generated_service_id = state.get("generated_service_id", candidate.service_id)

        if state.get("description") == previous_generated_description:
            state["description"] = candidate.description
        if state.get("service_name") == previous_generated_service_name:
            state["service_name"] = candidate.service_name
        if state.get("service_id") == previous_generated_service_id:
            state["service_id"] = candidate.service_id

        state["generated_service_name"] = candidate.service_name
        state["generated_service_id"] = candidate.service_id
        state["generated_description"] = candidate.description


def apply_saved_candidate_state(candidates) -> None:
    saved_state = st.session_state["candidate_state"]
    for candidate in candidates:
        state = saved_state.get(candidate.candidate_id)
        if not state:
            continue
        candidate.service_name = state["service_name"]
        candidate.service_id = state["service_id"]
        candidate.description = state["description"]
        candidate.status = RiskStatus(state["status"])
        candidate.audit_log = list(state["audit_log"])


def persist_candidate_state(candidate) -> None:
    current_state = st.session_state["candidate_state"].get(candidate.candidate_id, {})
    st.session_state["candidate_state"][candidate.candidate_id] = {
        "service_name": candidate.service_name,
        "service_id": candidate.service_id,
        "description": candidate.description,
        "status": candidate.status.value,
        "audit_log": list(candidate.audit_log),
        "generated_service_name": current_state.get("generated_service_name", candidate.service_name),
        "generated_service_id": current_state.get("generated_service_id", candidate.service_id),
        "generated_description": current_state.get("generated_description", candidate.description),
    }


def set_flash_message(level: str, text: str) -> None:
    st.session_state["flash_message"] = {"level": level, "text": text}


def editor_key(candidate_id: str, field_name: str) -> str:
    return f"editor::{candidate_id}::{field_name}"


def sync_editor_state(candidate) -> None:
    saved_state = st.session_state["candidate_state"][candidate.candidate_id]
    editor_defaults = {
        "service_name": saved_state["service_name"],
        "service_id": saved_state["service_id"],
        "description": saved_state["description"],
    }
    for field_name, value in editor_defaults.items():
        key = editor_key(candidate.candidate_id, field_name)
        if key not in st.session_state:
            st.session_state[key] = value


def read_editor_values(candidate) -> tuple[str, str, str]:
    service_name = st.session_state[editor_key(candidate.candidate_id, "service_name")].strip()
    service_id = st.session_state[editor_key(candidate.candidate_id, "service_id")].strip()
    description = st.session_state[editor_key(candidate.candidate_id, "description")].strip()
    return service_name, service_id, description


def open_confirmation(candidate_id: str, action: str) -> None:
    st.session_state["pending_confirmation"] = {
        "candidate_id": candidate_id,
        "action": action,
    }


@st.dialog("Подтверждение действия")
def render_confirmation_dialog(agent: DataRiskAgent, candidate) -> None:
    pending = st.session_state.get("pending_confirmation")
    if not pending or pending["candidate_id"] != candidate.candidate_id:
        return

    action = pending["action"]
    dialog_text = {
        "apply_generated": "Подтверждаете, что хотите разместить в поле сформированную агентом версию риска?",
        "register_corrected": "Подтверждаете регистрацию скорректированной версии риска?",
        "reject_candidate": "Укажите обоснование и подтвердите отклонение риска.",
    }.get(action, "Подтверждаете действие?")
    success_text = {
        "apply_generated": "Сформированная агентом версия размещена в редактируемом поле.",
        "register_corrected": None,
        "reject_candidate": None,
    }

    st.write(dialog_text)
    rejection_reason = ""
    if action == "reject_candidate":
        rejection_reason = st.text_area(
            "Обоснование отклонения",
            key=f"reject_reason::{candidate.candidate_id}",
            height=120,
            placeholder="Опишите, почему предлагаемый риск нужно отклонить",
        )
    confirm_col, cancel_col = st.columns(2)

    if confirm_col.button("Да", key=f"confirm_yes::{candidate.candidate_id}::{action}"):
        saved_state = st.session_state["candidate_state"][candidate.candidate_id]
        if action == "apply_generated":
            st.session_state[editor_key(candidate.candidate_id, "service_name")] = saved_state["generated_service_name"]
            st.session_state[editor_key(candidate.candidate_id, "service_id")] = saved_state["generated_service_id"]
            st.session_state[editor_key(candidate.candidate_id, "description")] = saved_state["generated_description"]
            set_flash_message("info", success_text[action])
        elif action == "register_corrected":
            service_name, service_id, description = read_editor_values(candidate)
            candidate.service_name = service_name
            candidate.service_id = service_id
            updated = agent.apply_user_override(candidate.candidate_id, description)
            task = agent.register_risk(updated.candidate_id, RegistrationMode.EDIT_AND_REGISTER)
            record_decision_event("corrected", updated)
            persist_candidate_state(updated)
            set_flash_message("success", task.message)
        elif action == "reject_candidate":
            if not rejection_reason.strip():
                st.warning("Нужно заполнить обоснование отклонения.")
                return
            service_name, service_id, description = read_editor_values(candidate)
            candidate.service_name = service_name
            candidate.service_id = service_id
            candidate.description = description
            candidate.status = RiskStatus.REJECTED
            candidate.audit_log.append(
                f"Кандидат отклонен пользователем. Обоснование: {rejection_reason.strip()}"
            )
            persist_candidate_state(candidate)
            record_decision_event("rejected", candidate)
            set_flash_message("warning", "Кандидат переведен в статус 'Отклонен'.")
        st.session_state["pending_confirmation"] = None
        st.rerun()

    if cancel_col.button("Нет", key=f"confirm_no::{candidate.candidate_id}::{action}"):
        st.session_state["pending_confirmation"] = None
        st.rerun()


def record_decision_event(event_type: str, candidate) -> None:
    st.session_state["decision_events"].append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event_type": event_type,
            "candidate_id": candidate.candidate_id,
            "process_name": candidate.process_name,
            "service_name": candidate.service_name,
        }
    )


def build_decision_trend_df() -> pd.DataFrame:
    decision_events = st.session_state.get("decision_events", [])
    if not decision_events:
        return pd.DataFrame()
    frame = pd.DataFrame(decision_events)
    frame["Период"] = pd.to_datetime(frame["timestamp"]).dt.strftime("%Y-%m-%d")
    grouped = (
        frame.groupby(["Период", "event_type"])
        .size()
        .unstack(fill_value=0)
        .rename(
            columns={
                "rejected": "Отклоненные риски",
                "corrected": "Скорректированные риски",
            }
        )
        .reset_index()
    )
    for column in ("Отклоненные риски", "Скорректированные риски"):
        if column not in grouped.columns:
            grouped[column] = 0
    return grouped[["Период", "Отклоненные риски", "Скорректированные риски"]]


def render_flash_message() -> None:
    flash_message = st.session_state.get("flash_message")
    if not flash_message:
        return
    if flash_message["level"] == "success":
        st.success(flash_message["text"])
    elif flash_message["level"] == "warning":
        st.warning(flash_message["text"])
    else:
        st.info(flash_message["text"])
    st.session_state["flash_message"] = None


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-shell">
            <div class="hero-title">Агент риска данных</div>
            <div class="hero-subtitle">
                Демо рабочего интерефейса агентной системы по идентификации риска данных
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stat_card(label: str, value: str, sublabel: str = "") -> None:
    sub_html = f'<div class="mini-stat-sub">{html.escape(sublabel)}</div>' if sublabel else ""
    st.markdown(
        f"""
        <div class="mini-stat">
            <div class="mini-stat-label">{html.escape(label)}</div>
            <div class="mini-stat-value">{html.escape(value)}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(kicker: str, title: str, note: str = "") -> None:
    note_html = f'<div class="section-note">{html.escape(note)}</div>' if note else ""
    st.markdown(
        f"""
        <div class="section-kicker">{html.escape(kicker)}</div>
        <div class="section-title">{html.escape(title)}</div>
        {note_html}
        """,
        unsafe_allow_html=True,
    )


def localize_status(status: RiskStatus) -> str:
    return STATUS_LABELS.get(status, str(status))


def localize_verdict(verdict: ValidationVerdict) -> str:
    return VERDICT_LABELS.get(verdict, str(verdict))


def localize_similarity(similarity: float) -> str:
    return "Похожий риск" if similarity >= 0.80 else "Не похожий риск"


def is_registered_status(status: RiskStatus) -> bool:
    return status in {RiskStatus.REGISTERED, RiskStatus.AUTO_REGISTERED}


def summarize_generalization(candidate) -> dict[str, str]:
    if not candidate.existing_risk_matches:
        return {
            "kind": "new_risk",
            "title": "Похожий зарегистрированный риск не найден",
            "summary": (
                "Для этого бизнес-процесса не найден похожий зарегистрированный риск. "
                "Текущую карточку следует рассматривать как проект нового риска."
            ),
            "action_label": "Зарегистрировать новый риск",
        }

    best_match = max(candidate.existing_risk_matches, key=lambda item: item.similarity)
    if best_match.similarity >= 0.90:
        return {
            "kind": "covered_by_existing",
            "title": "Существующий риск в целом покрывает новый сценарий",
            "summary": (
                f"Похожий риск {best_match.risk_id} '{best_match.title}' уже описывает близкий сценарий для этого процесса. "
                "Рекомендуется не создавать отдельный риск, а привязать инциденты-основания к существующему риску "
                "и при необходимости уточнить его описание."
            ),
            "action_label": "Привязать инциденты к существующему риску",
        }

    return {
        "kind": "extend_existing",
        "title": "Новый сценарий стоит обобщить с существующим риском",
        "summary": (
            f"На процессе уже есть похожий риск {best_match.risk_id} '{best_match.title}', "
            "но новый сценарий лучше отдельно рассмотреть и затем решить, обновлять ли описание старого риска "
            "или добавлять в него новый сценарий."
        ),
        "action_label": "Объединить с существующим риском",
    }


def process_risk_ids(agent: DataRiskAgent, candidate) -> str:
    process_risks = agent.get_process_risks(candidate.process_id)
    if not process_risks:
        return "Нет"
    return ", ".join(risk.risk_id for risk in process_risks)


def render_candidate_row(agent: DataRiskAgent, candidate) -> dict[str, str]:
    return {
        "Бизнес-процесс": candidate.process_name,
        "Фронтальная ИТ-услуга": f"{candidate.service_name} ({candidate.service_id})",
        "Имеющиеся риски": process_risk_ids(agent, candidate),
        "Инциденты-основания": ", ".join(candidate.incident_ids),
        "Статус": localize_status(candidate.status),
        "Результат проверки": localize_verdict(candidate.validation.verdict),
        "Уверенность": f"{candidate.validation.confidence:.2f}",
    }


def build_candidates_export_df(agent: DataRiskAgent, candidates) -> pd.DataFrame:
    rows = []
    for candidate in candidates:
        process_risks = agent.get_process_risks(candidate.process_id)
        rows.append(
            {
                "Бизнес-процесс": candidate.process_name,
                "Фронтальная ИТ-услуга": candidate.service_name,
                "Идентификатор ИТ-услуги": candidate.service_id,
                "Имеющиеся риски": ", ".join(risk.risk_id for risk in process_risks) if process_risks else "",
                "Инциденты-основания": ", ".join(candidate.incident_ids),
                "Количество сценариев": len(candidate.scenarios),
                "Статус": localize_status(candidate.status),
                "Результат проверки": localize_verdict(candidate.validation.verdict),
                "Описание риска": candidate.description,
            }
        )
    return pd.DataFrame(rows)


def dataframe_to_excel_bytes(frame: pd.DataFrame) -> bytes:
    engine = None
    if importlib.util.find_spec("openpyxl") is not None:
        engine = "openpyxl"
    elif importlib.util.find_spec("xlsxwriter") is not None:
        engine = "xlsxwriter"
    if engine is None:
        raise RuntimeError("Excel export engine is not available.")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine=engine) as writer:
        frame.to_excel(writer, index=False, sheet_name="Риски")
    output.seek(0)
    return output.getvalue()


def filter_candidates(agent: DataRiskAgent, candidates, process_filter: str, service_filter: str, status_filter: str, search_query: str):
    normalized_query = search_query.strip().lower()
    filtered = []
    for candidate in candidates:
        if process_filter != "Все процессы" and candidate.process_name != process_filter:
            continue
        if service_filter != "Все ИТ-услуги" and candidate.service_name != service_filter:
            continue
        if status_filter != "Все статусы" and localize_status(candidate.status) != status_filter:
            continue
        searchable_text = " ".join(
            [
                candidate.process_name,
                candidate.service_name,
                candidate.service_id,
                candidate.description,
                process_risk_ids(agent, candidate),
                " ".join(candidate.incident_ids),
            ]
        ).lower()
        if normalized_query and normalized_query not in searchable_text:
            continue
        filtered.append(candidate)
    return filtered


inject_brand_css()
initialize_ui_state()
agent = load_agent()
pipeline = agent.run()
ensure_candidate_state(pipeline.candidates)
apply_saved_candidate_state(pipeline.candidates)
metrics = agent.compute_quality_metrics(pipeline.candidates)

render_hero()
render_flash_message()

risk_tab, metrics_tab = st.tabs(["Риски для пользователей", "Метрики качества"])

with risk_tab:
    top_cards = st.columns(4)
    with top_cards[0]:
        render_stat_card("Всего рисков в работе", str(len(pipeline.candidates)), "Агрегировано по бизнес-процессам и ИТ-услугам")
    with top_cards[1]:
        render_stat_card(
            "Подтверждено агентом",
            str(sum(candidate.status in {RiskStatus.VALIDATED, RiskStatus.AUTO_READY, RiskStatus.AUTO_REGISTERED} for candidate in pipeline.candidates)),
            "Риски, которые агент считает подтвержденными",
        )
    with top_cards[2]:
        render_stat_card(
            "Требуют проверки",
            str(sum(candidate.status == RiskStatus.NEEDS_REVIEW for candidate in pipeline.candidates)),
            "Нужна ручная корректировка или решение пользователя",
        )
    with top_cards[3]:
        render_stat_card(
            "Похожие риски найдены",
            str(sum(bool(candidate.existing_risk_matches) for candidate in pipeline.candidates)),
            "Есть зарегистрированный риск, с которым нужно сопоставить новый сценарий",
        )

    render_section_header(
        "Очередь рисков",
        "Подберите нужный риск и откройте карточку",
        "Фильтры помогают быстро найти кейс по процессу, фронтальной ИТ-услуге или статусу проверки.",
    )

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.3, 1.3, 1.2, 1.7])
    process_options = ["Все процессы"] + sorted({candidate.process_name for candidate in pipeline.candidates})
    service_options = ["Все ИТ-услуги"] + sorted({candidate.service_name for candidate in pipeline.candidates})
    status_options = ["Все статусы"] + sorted({localize_status(candidate.status) for candidate in pipeline.candidates})

    selected_process = filter_col1.selectbox("Бизнес-процесс", process_options)
    selected_service = filter_col2.selectbox("Фронтальная ИТ-услуга", service_options)
    selected_status = filter_col3.selectbox("Статус", status_options)
    search_query = filter_col4.text_input("Поиск по описанию, идентификатору или инциденту")

    visible_candidates = filter_candidates(
        agent,
        pipeline.candidates,
        selected_process,
        selected_service,
        selected_status,
        search_query,
    )

    if not visible_candidates:
        st.info("По выбранным фильтрам риски не найдены. Попробуйте снять часть ограничений.")
    else:
        render_section_header(
            "Сводка",
            "Таблица по проанализированным сочетаниям",
            "Здесь собраны все найденные сочетания бизнес-процессов и фронтальных ИТ-услуг с текущими фильтрами.",
        )
        summary_df = build_candidates_export_df(agent, visible_candidates)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        excel_bytes = None
        excel_export_available = True
        try:
            excel_bytes = dataframe_to_excel_bytes(summary_df)
        except RuntimeError:
            excel_export_available = False
        export_col1, export_col2 = st.columns(2)
        export_col1.download_button(
            "Скачать CSV",
            data=summary_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="data_risk_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if excel_export_available and excel_bytes is not None:
            export_col2.download_button(
                "Скачать Excel",
                data=excel_bytes,
                file_name="data_risk_summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            export_col2.empty()

        visible_ids = [candidate.candidate_id for candidate in visible_candidates]
        current_selected_id = st.session_state.get("selected_candidate_id")
        if current_selected_id not in visible_ids:
            current_selected_id = visible_ids[0]
            st.session_state["selected_candidate_id"] = current_selected_id

        candidate = next(item for item in visible_candidates if item.candidate_id == current_selected_id)
        generalization = summarize_generalization(candidate)
        process_risks = agent.get_process_risks(candidate.process_id)
        sync_editor_state(candidate)
        if (st.session_state.get("pending_confirmation") or {}).get("candidate_id") == candidate.candidate_id:
            render_confirmation_dialog(agent, candidate)
        queue_box = st.container(border=True)
        with queue_box:
            st.markdown("### Очередь кейсов")
            st.caption("Выберите кейс из списка. Ниже на всю ширину откроется рабочая карточка по выбранному сочетанию.")
            header_cols = st.columns([2.4, 1.7, 1.1, 1.2, 1.1])
            header_cols[0].markdown("**Кейс**")
            header_cols[1].markdown("**Имеющиеся риски**")
            header_cols[2].markdown("**Инциденты**")
            header_cols[3].markdown("**Статус**")
            header_cols[4].markdown("**Действие**")
            for item in visible_candidates:
                is_selected = item.candidate_id == candidate.candidate_id
                row_cols = st.columns([2.4, 1.7, 1.1, 1.2, 1.1])
                row_cols[0].markdown(
                    f"**{html.escape(item.process_name)}**<br>{html.escape(item.service_name)} ({html.escape(item.service_id)})",
                    unsafe_allow_html=True,
                )
                row_cols[1].markdown(process_risk_ids(agent, item))
                row_cols[2].markdown(str(len(item.incident_ids)))
                row_cols[3].markdown(localize_status(item.status))
                if row_cols[4].button(
                    "Открыто" if is_selected else "Открыть",
                    key=f"open_candidate::{item.candidate_id}",
                    disabled=is_selected,
                    use_container_width=True,
                ):
                    st.session_state["selected_candidate_id"] = item.candidate_id
                    st.rerun()

        card_col = st.container()
        with card_col:
            render_section_header(
                "Рабочая карточка",
                "Принятие решения по риску",
                "Сначала оцените вывод агента, затем при необходимости скорректируйте проект риска и выберите подходящее действие.",
            )
            st.markdown(
                f"""
                <div class="recommendation-shell">
                    <div class="recommendation-title">{html.escape(generalization['title'])}</div>
                    <div>{html.escape(generalization['summary'])}</div>
                    <div style="margin-top:0.65rem;"><strong>Рекомендация агента:</strong> {html.escape(candidate.merge_proposal)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            passport_cols = st.columns(4)
            with passport_cols[0]:
                render_stat_card("Бизнес-процесс", candidate.process_name)
            with passport_cols[1]:
                render_stat_card("Фронтальная ИТ-услуга", candidate.service_name, candidate.service_id)
            with passport_cols[2]:
                render_stat_card("Имеющиеся риски на процессе", str(len(process_risks)), process_risk_ids(agent, candidate))
            with passport_cols[3]:
                render_stat_card("Инциденты-основания", str(len(candidate.incident_ids)), ", ".join(candidate.incident_ids[:3]) + ("..." if len(candidate.incident_ids) > 3 else ""))
            new_risk_box = st.container(border=True)
            with new_risk_box:
                st.markdown("### Проект нового риска")
                if is_registered_status(candidate.status):
                    st.markdown('<span class="status-chip">Этот риск уже зарегистрирован</span>', unsafe_allow_html=True)
                else:
                    st.caption(
                        "Если агент неверно определил фронтальную ИТ-услугу, ее можно вручную исправить здесь. "
                        "Это особенно полезно, когда сбой произошел в upstream-системе, а итоговое решение принимает downstream-система."
                    )

                st.write(f"**Бизнес-процесс:** {candidate.process_name}")
                st.markdown("**Редактируемая фронтальная ИТ-услуга**")
                service_col1, service_col2 = st.columns([2, 1])
                edited_service_name = service_col1.text_input(
                    "Фронтальная ИТ-услуга",
                    key=editor_key(candidate.candidate_id, "service_name"),
                )
                edited_service_id = service_col2.text_input(
                    "Идентификатор фронтальной ИТ-услуги",
                    key=editor_key(candidate.candidate_id, "service_id"),
                )
                st.caption("Если агент определил не ту сущность, здесь можно вручную исправить фронтальную ИТ-услугу.")

                fact_cols = st.columns(2)
                fact_cols[0].markdown(
                    f"**Процесс-носитель потерь:**<br>{html.escape(candidate.loss_process_name)}",
                    unsafe_allow_html=True,
                )
                fact_cols[1].markdown(
                    f"**Статус и проверка:**<br>{html.escape(localize_status(candidate.status))} / {html.escape(localize_verdict(candidate.validation.verdict))}",
                    unsafe_allow_html=True,
                )

                edited_description = st.text_area(
                    "Редактируемое описание риска",
                    key=editor_key(candidate.candidate_id, "description"),
                    height=220,
                )

                editor_action_columns = st.columns(3)
                if editor_action_columns[0].button(
                    "Разместить сформированную агентом версию",
                    key=f"apply_generated::{candidate.candidate_id}",
                ):
                    open_confirmation(candidate.candidate_id, "apply_generated")
                    st.rerun()
                if (
                    not is_registered_status(candidate.status)
                    and editor_action_columns[1].button(
                        "Зарегистрировать скорректированную версию",
                        key=f"register_corrected_editor::{candidate.candidate_id}",
                    )
                ):
                    open_confirmation(candidate.candidate_id, "register_corrected")
                    st.rerun()
                if (
                    not is_registered_status(candidate.status)
                    and editor_action_columns[2].button(
                        "Отклонить",
                        key=f"reject_editor::{candidate.candidate_id}",
                    )
                ):
                    open_confirmation(candidate.candidate_id, "reject_candidate")
                    st.rerun()

                can_merge_with_existing = bool(candidate.existing_risk_matches) and not is_registered_status(candidate.status)
                can_keep_separate = bool(candidate.existing_risk_matches) and not is_registered_status(candidate.status)
                can_link_to_existing = (
                    generalization["kind"] == "covered_by_existing"
                    and bool(candidate.existing_risk_matches)
                    and not is_registered_status(candidate.status)
                )

                available_editor_merge_actions: list[tuple[str, str]] = []
                if can_link_to_existing:
                    available_editor_merge_actions.append((generalization["action_label"], "link_existing"))
                elif can_merge_with_existing:
                    available_editor_merge_actions.append(("Объединить сценарии", "merge_existing"))
                if can_keep_separate:
                    available_editor_merge_actions.append(("Оставить отдельным сценарием", "keep_separate"))

                if available_editor_merge_actions:
                    st.markdown("**Решение по отношению к уже имеющемуся риску**")
                    merge_action_columns = st.columns(len(available_editor_merge_actions))
                    for column, (label, action_key) in zip(merge_action_columns, available_editor_merge_actions, strict=False):
                        if action_key == "link_existing" and column.button(label, key=f"link_existing_editor::{candidate.candidate_id}"):
                            candidate.service_name = edited_service_name.strip()
                            candidate.service_id = edited_service_id.strip()
                            candidate.description = edited_description.strip()
                            candidate.audit_log.append(
                                "Пользователь решил использовать существующий риск и привязать к нему инциденты-основания."
                            )
                            persist_candidate_state(candidate)
                            set_flash_message("info", "Решение использовать существующий риск сохранено в журнале действий.")
                            st.rerun()
                        if action_key == "merge_existing" and column.button(label, key=f"merge_existing_editor::{candidate.candidate_id}"):
                            candidate.service_name = edited_service_name.strip()
                            candidate.service_id = edited_service_id.strip()
                            candidate.description = edited_description.strip()
                            candidate.audit_log.append(
                                "Пользователь подтвердил объединение нового сценария с уже имеющимся риском."
                            )
                            persist_candidate_state(candidate)
                            set_flash_message("info", "Решение об объединении сценариев сохранено в журнале действий.")
                            st.rerun()
                        if action_key == "keep_separate" and column.button(label, key=f"keep_separate_editor::{candidate.candidate_id}"):
                            candidate.service_name = edited_service_name.strip()
                            candidate.service_id = edited_service_id.strip()
                            candidate.description = edited_description.strip()
                            candidate.audit_log.append(
                                "Пользователь решил дополнить описание уже имеющегося риска новым сценарием с соответствующей пометкой."
                            )
                            persist_candidate_state(candidate)
                            set_flash_message(
                                "info",
                                "Решение сохранить новый сценарий внутри уже имеющегося риска сохранено в журнале действий.",
                            )
                            st.rerun()

                st.markdown(
                    f"""
                    <div class="verdict-box">
                        <div><strong>Комментарий агента по валидации:</strong></div>
                        <div>{html.escape(candidate.validation.rationale)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if candidate.validation.rejection_reasons:
                    st.write("**Причины отклонения:** " + "; ".join(candidate.validation.rejection_reasons))

            existing_risks_box = st.container(border=True)
            with existing_risks_box:
                st.markdown("### Имеющиеся риски на процессе")
                if process_risks:
                    for risk in process_risks:
                        with st.expander(f"{risk.risk_id} · {risk.title}", expanded=False):
                            st.write(f"**Фронтальная ИТ-услуга:** {risk.service_name} ({risk.service_id})")
                            st.write(f"**Описание риска:** {risk.description}")
                            st.write(f"**Статус:** {risk.status}")
                else:
                    st.info("На этом бизнес-процессе зарегистрированные риски пока не найдены.")

            scenario_box = st.container(border=True)
            with scenario_box:
                st.markdown("### Сценарии риска")
                if len(candidate.scenarios) == 1:
                    scenario = candidate.scenarios[0]
                    st.write(f"**Сценарий 1:** {scenario.data_degradation_hypothesis}")
                    st.write(f"**Влияние:** {scenario.business_impact}")
                    st.write(f"**Роль ИТ-услуги:** {scenario.role_description}")
                else:
                    scenario_tabs = st.tabs([f"Сценарий {index}" for index in range(1, len(candidate.scenarios) + 1)])
                    for tab, scenario in zip(scenario_tabs, candidate.scenarios, strict=False):
                        with tab:
                            st.write(f"**Формулировка сценария:** {scenario.data_degradation_hypothesis}")
                            st.write(f"**Влияние:** {scenario.business_impact}")
                            st.write(f"**Роль ИТ-услуги:** {scenario.role_description}")
                            st.write("**Основания:**")
                            for item in scenario.evidence:
                                st.write(f"- {item}")

            mitigation_box = st.container(border=True)
            with mitigation_box:
                st.markdown("### Предлагаемые меры митигации")
                can_register_mitigations = (
                    is_registered_status(candidate.status)
                    or agent.has_process_risks(candidate.process_id)
                )
                if candidate.mitigation_candidates:
                    for mitigation in candidate.mitigation_candidates:
                        checkbox_key = f"mitigation::{candidate.candidate_id}::{','.join(mitigation.work_ids)}"
                        st.checkbox(
                            f"{', '.join(mitigation.work_ids)}: {mitigation.description}",
                            key=checkbox_key,
                        )
                        st.caption(
                            f"Работы проводятся на ИТ-услуге: {mitigation.service_name} ({mitigation.service_id})"
                        )
                        st.caption(mitigation.rationale)

                    selected_mitigation_ids = [
                        work_id
                        for mitigation in candidate.mitigation_candidates
                        if st.session_state.get(
                            f"mitigation::{candidate.candidate_id}::{','.join(mitigation.work_ids)}",
                            False,
                        )
                        for work_id in mitigation.work_ids
                    ]

                    if can_register_mitigations:
                        if st.button(
                            "Зарегистрировать выбранные меры",
                            key=f"register_selected_mitigations::{candidate.candidate_id}",
                            disabled=not selected_mitigation_ids,
                        ):
                            task = agent.register_mitigation(candidate.candidate_id, selected_mitigation_ids)
                            persist_candidate_state(candidate)
                            set_flash_message("success", task.message)
                            st.rerun()
                        if not selected_mitigation_ids:
                            st.caption("Отметьте галочками меры, которые нужно зарегистрировать.")
                    else:
                        st.info(
                            "Регистрация мер будет доступна после появления зарегистрированного риска на этом бизнес-процессе."
                        )
                else:
                    st.info("Подходящие мероприятия не найдены.")

            with st.expander("Показать журнал действий", expanded=False):
                for message in candidate.audit_log:
                    st.write(f"- {message}")

with metrics_tab:
    render_section_header(
        "Внутренний контур",
        "Метрики качества работы системы",
        "Эта вкладка нужна методологам и не предназначена для обычных пользователей процесса.",
    )
    st.markdown(
        '<div class="method-note">Здесь собраны метрики по качеству работы агента: доля инцидентов с признаками риска данных, доля отклонений, доля корректировок и их динамика во времени.</div>',
        unsafe_allow_html=True,
    )

    method_cards = st.columns(3)
    with method_cards[0]:
        render_stat_card(
            "Доля инцидентов с признаками риска данных",
            f"{metrics.data_risk_share:.0%}",
            f"{metrics.incidents_with_data_risk_signs} из {metrics.total_incidents}",
        )
    with method_cards[1]:
        render_stat_card(
            "Доля отклоненных рисков",
            f"{metrics.rejected_risk_share:.0%}",
            f"{metrics.rejected_risks} из {metrics.total_risk_candidates}",
        )
    with method_cards[2]:
        render_stat_card(
            "Доля скорректированных рисков",
            f"{metrics.corrected_risk_share:.0%}",
            f"{metrics.corrected_risks} из {metrics.total_risk_candidates}",
        )

    st.markdown("### Динамика инцидентов с признаками риска данных")
    trend_df = pd.DataFrame(
        [
            {
                "Период": point.period,
                "Доля инцидентов с признаками риска данных": point.data_risk_share,
            }
            for point in metrics.trend
        ]
    )
    if not trend_df.empty:
        st.line_chart(trend_df.set_index("Период"))

    metrics_table_df = pd.DataFrame(
        [
            {
                "Период": point.period,
                "Всего инцидентов": point.total_incidents,
                "Инцидентов с признаками риска данных": point.incidents_with_data_risk_signs,
                "Доля": f"{point.data_risk_share:.0%}",
            }
            for point in metrics.trend
        ]
    )
    if not metrics_table_df.empty:
        st.dataframe(metrics_table_df, use_container_width=True, hide_index=True)

    st.markdown("### Динамика отклонений и корректировок")
    decision_trend_df = build_decision_trend_df()
    if not decision_trend_df.empty:
        st.line_chart(decision_trend_df.set_index("Период"))
        st.dataframe(decision_trend_df, use_container_width=True, hide_index=True)
    else:
        st.info("Пока нет пользовательских действий по отклонению или корректировке рисков, поэтому график пуст.")
