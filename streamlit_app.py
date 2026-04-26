from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
FEEDBACK_CASES_PATH = PROJECT_ROOT / "data" / "feedback_cases.jsonl"
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
    st.session_state.setdefault("feedback_cases", [])
    st.session_state.setdefault("feedback_cases_loaded", False)
    st.session_state.setdefault("flash_message", None)
    st.session_state.setdefault("pending_confirmation", None)


def load_feedback_cases_from_storage() -> list[dict]:
    if not FEEDBACK_CASES_PATH.exists():
        return []
    items: list[dict] = []
    with FEEDBACK_CASES_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def append_feedback_case_to_storage(item: dict) -> None:
    FEEDBACK_CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_CASES_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def ensure_feedback_cases_loaded() -> None:
    if st.session_state.get("feedback_cases_loaded"):
        return
    st.session_state["feedback_cases"] = load_feedback_cases_from_storage()
    st.session_state["feedback_cases_loaded"] = True


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


def render_confirmation_version_preview(candidate, action: str) -> None:
    saved_state = st.session_state["candidate_state"][candidate.candidate_id]
    edited_service_name, edited_service_id, edited_description = read_editor_values(candidate)

    if action in {"apply_generated", "register_generated"}:
        preview_title = "Будет использована исходная версия агента"
        preview_service_name = saved_state["generated_service_name"]
        preview_service_id = saved_state["generated_service_id"]
        preview_description = saved_state["generated_description"]
    elif action in {"register_corrected", "link_existing", "merge_existing", "keep_separate", "reject_candidate"}:
        preview_title = "Будет использована текущая скорректированная пользователем версия"
        preview_service_name = edited_service_name
        preview_service_id = edited_service_id
        preview_description = edited_description
    else:
        return

    st.markdown(f"**{preview_title}**")
    st.write(f"**Фронтальная ИТ-услуга:** {preview_service_name} ({preview_service_id})")
    st.write("**Описание риска:**")
    st.code(preview_description or "Описание риска не заполнено", language=None)


@st.dialog("Подтверждение действия")
def render_confirmation_dialog(agent: DataRiskAgent, candidate) -> None:
    pending = st.session_state.get("pending_confirmation")
    if not pending or pending["candidate_id"] != candidate.candidate_id:
        return

    action = pending["action"]
    dialog_text = {
        "apply_generated": "Подтверждаете, что хотите разместить в поле сформированную агентом версию риска?",
        "register_generated": "Подтверждаете регистрацию версии риска в формулировке агента?",
        "register_corrected": "Подтверждаете регистрацию скорректированной версии риска?",
        "link_existing": "Подтверждаете привязку инцидентов-оснований к уже существующему риску без изменения его описания?",
        "merge_existing": "Подтверждаете обобщение существующего риска с учетом нового сценария?",
        "keep_separate": "Подтверждаете добавление нового сценария в уже существующий риск?",
        "reject_candidate": "Укажите обоснование и подтвердите отклонение риска.",
    }.get(action, "Подтверждаете действие?")
    success_text = {
        "apply_generated": "Сформированная агентом версия размещена в редактируемом поле.",
        "register_generated": None,
        "register_corrected": None,
        "reject_candidate": None,
    }

    st.write(dialog_text)
    render_confirmation_version_preview(candidate, action)
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
        elif action == "register_generated":
            candidate.service_name = saved_state["generated_service_name"]
            candidate.service_id = saved_state["generated_service_id"]
            candidate.description = saved_state["generated_description"]
            candidate.audit_log.append("Пользователь зарегистрировал риск в формулировке агента.")
            task = agent.register_risk(candidate.candidate_id, RegistrationMode.REGISTER_AS_PROPOSED)
            record_feedback_case(
                "register_generated",
                "Зарегистрирована версия агента",
                candidate,
                "Пользователь принял исходную формулировку агента без изменений.",
            )
            persist_candidate_state(candidate)
            set_flash_message("success", task.message)
        elif action == "register_corrected":
            service_name, service_id, description = read_editor_values(candidate)
            candidate.service_name = service_name
            candidate.service_id = service_id
            updated = agent.apply_user_override(candidate.candidate_id, description)
            task = agent.register_risk(updated.candidate_id, RegistrationMode.EDIT_AND_REGISTER)
            record_decision_event("corrected", updated)
            record_feedback_case(
                "register_corrected",
                "Зарегистрирована скорректированная версия",
                updated,
                "Пользователь вручную скорректировал формулировку или сущности перед регистрацией.",
            )
            persist_candidate_state(updated)
            set_flash_message("success", task.message)
        elif action == "link_existing":
            service_name, service_id, description = read_editor_values(candidate)
            candidate.service_name = service_name
            candidate.service_id = service_id
            candidate.description = description
            candidate.audit_log.append(
                "Пользователь решил привязать инциденты-основания к уже существующему риску без изменения его описания."
            )
            record_feedback_case(
                "link_existing",
                "Инциденты привязаны к существующему риску",
                candidate,
                "Пользователь не увидел необходимости менять описание существующего риска.",
            )
            persist_candidate_state(candidate)
            set_flash_message("info", "Решение привязать инциденты к существующему риску сохранено в журнале действий.")
        elif action == "merge_existing":
            service_name, service_id, description = read_editor_values(candidate)
            candidate.service_name = service_name
            candidate.service_id = service_id
            candidate.description = description
            candidate.audit_log.append(
                "Пользователь решил обобщить существующий риск и обновить его описание с учетом нового сценария."
            )
            record_feedback_case(
                "merge_existing",
                "Существующий риск обобщен",
                candidate,
                "Пользователь решил, что существующий риск нужно расширить с учетом нового сценария.",
            )
            persist_candidate_state(candidate)
            set_flash_message("info", "Решение по обобщению существующего риска сохранено в журнале действий.")
        elif action == "keep_separate":
            service_name, service_id, description = read_editor_values(candidate)
            candidate.service_name = service_name
            candidate.service_id = service_id
            candidate.description = description
            candidate.audit_log.append(
                "Пользователь решил дополнить существующий риск новым сценарием с соответствующей пометкой."
            )
            record_feedback_case(
                "keep_separate",
                "Добавлен новый сценарий в существующий риск",
                candidate,
                "Пользователь решил сохранить новый кейс как отдельный сценарий внутри уже существующего риска.",
            )
            persist_candidate_state(candidate)
            set_flash_message("info", "Решение дополнить существующий риск новым сценарием сохранено в журнале действий.")
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
            record_feedback_case(
                "reject_candidate",
                "Риск отклонен",
                candidate,
                rejection_reason.strip(),
            )
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


def feedback_reward(action: str) -> float:
    rewards = {
        "register_generated": 1.0,
        "register_corrected": 0.4,
        "link_existing": 0.2,
        "merge_existing": 0.1,
        "keep_separate": 0.1,
        "reject_candidate": -1.0,
    }
    return rewards.get(action, 0.0)


def learning_mode_for_action(action: str) -> str:
    modes = {
        "register_generated": "positive_acceptance",
        "register_corrected": "supervised_correction",
        "link_existing": "routing_correction",
        "merge_existing": "merge_decision",
        "keep_separate": "scenario_boundary_decision",
        "reject_candidate": "negative_rejection",
    }
    return modes.get(action, "manual_review")


def learning_note_for_action(action: str) -> str:
    notes = {
        "register_generated": "Агентный вариант принят без изменений. Логика сработала корректно.",
        "register_corrected": "Пользователь изменил формулировку или сущности. Нужно улучшать текст риска или определение фронтальной ИТ-услуги.",
        "link_existing": "Агенту стоит точнее понимать, когда достаточно привязать инциденты к уже существующему риску без изменения описания.",
        "merge_existing": "Агенту стоит лучше предлагать обобщение с уже имеющимся риском вместо отдельного проектного описания.",
        "keep_separate": "Агенту стоит лучше различать, когда новый кейс должен стать отдельным сценарием внутри уже имеющегося риска.",
        "reject_candidate": "Нужно пересматривать правила отбора или валидации, потому что пользователь не подтвердил предложенный риск.",
    }
    return notes.get(action, "Требуется дополнительный разбор кейса методологом.")


def build_learning_prompt(candidate, saved_state: dict) -> str:
    return (
        f"Бизнес-процесс: {candidate.process_name}\n"
        f"Фронтальная ИТ-услуга: {candidate.service_name} ({candidate.service_id})\n"
        f"Инциденты-основания: {', '.join(candidate.incident_ids)}\n"
        f"Исходная версия агента: {saved_state.get('generated_description', '')}"
    )


def record_feedback_case(action: str, action_label: str, candidate, rationale: str = "") -> None:
    saved_state = st.session_state["candidate_state"][candidate.candidate_id]
    item = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "candidate_id": candidate.candidate_id,
        "process_name": candidate.process_name,
        "service_name": candidate.service_name,
        "service_id": candidate.service_id,
        "incident_ids": ", ".join(candidate.incident_ids),
        "agent_version": saved_state.get("generated_description", ""),
        "user_version": candidate.description,
        "action_code": action,
        "action_label": action_label,
        "rationale": rationale or "Без дополнительного комментария",
        "learning_note": learning_note_for_action(action),
        "reward_signal": feedback_reward(action),
        "learning_mode": learning_mode_for_action(action),
        "learning_prompt": build_learning_prompt(candidate, saved_state),
        "preferred_response": candidate.description if action != "register_generated" else saved_state.get("generated_description", ""),
        "rejected_response": saved_state.get("generated_description", "") if action in {"register_corrected", "reject_candidate"} else "",
    }
    st.session_state["feedback_cases"].append(item)
    append_feedback_case_to_storage(item)


def build_learning_dataset_df() -> pd.DataFrame:
    feedback_cases = st.session_state.get("feedback_cases", [])
    if not feedback_cases:
        return pd.DataFrame()
    frame = pd.DataFrame(feedback_cases)
    frame["Время"] = pd.to_datetime(frame["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return frame[
        [
            "Время",
            "candidate_id",
            "action_label",
            "reward_signal",
            "learning_mode",
            "learning_prompt",
            "preferred_response",
            "rejected_response",
        ]
    ].rename(
        columns={
            "candidate_id": "Кейс",
            "action_label": "Сигнал пользователя",
            "reward_signal": "Reward",
            "learning_mode": "Режим обучения",
            "learning_prompt": "Контекст кейса",
            "preferred_response": "Предпочтительный ответ",
            "rejected_response": "Отклоненный ответ",
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


def build_feedback_cases_df() -> pd.DataFrame:
    feedback_cases = st.session_state.get("feedback_cases", [])
    if not feedback_cases:
        return pd.DataFrame()
    frame = pd.DataFrame(feedback_cases)
    frame["Время"] = pd.to_datetime(frame["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return frame[
        [
            "Время",
            "candidate_id",
            "process_name",
            "service_name",
            "service_id",
            "incident_ids",
            "action_label",
            "rationale",
            "learning_note",
            "agent_version",
            "user_version",
        ]
    ].rename(
        columns={
            "candidate_id": "Кейс",
            "process_name": "Бизнес-процесс",
            "service_name": "Фронтальная ИТ-услуга",
            "service_id": "Идентификатор ИТ-услуги",
            "incident_ids": "Инциденты-основания",
            "action_label": "Ответ пользователя",
            "rationale": "Обоснование пользователя",
            "learning_note": "Что корректировать в агенте",
            "agent_version": "Предложение агента",
            "user_version": "Итоговая версия по кейсу",
        }
    )


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


def find_combination_risks(process_risks, service_id: str, service_name: str):
    normalized_service_id = service_id.strip()
    normalized_service_name = service_name.strip().casefold()
    matches = []
    for risk in process_risks:
        if normalized_service_id and risk.service_id == normalized_service_id:
            matches.append(risk)
            continue
        if not normalized_service_id and normalized_service_name and risk.service_name.casefold() == normalized_service_name:
            matches.append(risk)
    return matches


def summarize_generalization(candidate, exact_combination_risks) -> dict[str, str]:
    if exact_combination_risks:
        risk_ids = ", ".join(risk.risk_id for risk in exact_combination_risks)
        return {
            "kind": "exact_combination_exists",
            "title": "На этом сочетании уже есть зарегистрированный риск",
            "summary": (
                f"Для сочетания {candidate.process_name} + {candidate.service_name} ({candidate.service_id}) "
                f"уже найден риск {risk_ids}. Новый риск создавать не нужно: можно либо уточнить существующий, "
                "либо дополнить его новым сценарием, либо просто привязать к нему инциденты-основания."
            ),
            "action_label": "Привязать инциденты к существующему риску",
        }

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
        source_services = ", ".join(
            dict.fromkeys(
                f"{scenario.source_service_name} ({scenario.source_service_id})"
                for scenario in candidate.scenarios
            )
        )
        references = ", ".join(
            dict.fromkeys(
                scenario.matched_reference
                for scenario in candidate.scenarios
                if scenario.matched_reference
            )
        )
        rows.append(
            {
                "Бизнес-процесс": candidate.process_name,
                "Источник проблемных данных": source_services,
                "Контракт/оферта": references,
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


def build_chain_lines(candidate) -> list[str]:
    grouped: dict[tuple[str, str, str | None, str, str, str], list[str]] = {}
    for scenario in candidate.scenarios:
        key = (
            f"{scenario.source_service_name} ({scenario.source_service_id})",
            f"{scenario.service_name} ({scenario.service_id})",
            scenario.matched_reference,
            scenario.loss_process_name,
            scenario.role_description,
            scenario.process_outcome,
        )
        grouped.setdefault(key, []).append(scenario.incident_id)

    lines: list[str] = []
    for (
        source_service,
        receiver_service,
        matched_reference,
        loss_process_name,
        role_description,
        process_outcome,
    ), incident_ids in grouped.items():
        incident_part = f"По {len(incident_ids)} инцидентам"
        if source_service == receiver_service:
            source_part = f"проблема с данными была зафиксирована непосредственно в {receiver_service}"
        else:
            reference_part = f" по {matched_reference}" if matched_reference else ""
            source_part = (
                f"данные от {source_service}{reference_part} поступали в {receiver_service}"
            )
        line = (
            f"{incident_part} {source_part}; "
            f"в процессе эта ИТ-услуга {role_description}; "
            f"итог процесса: {process_outcome}; "
            f"потери реализуются в процессе {loss_process_name}."
        )
        lines.append(line)
    return lines


inject_brand_css()
initialize_ui_state()
ensure_feedback_cases_loaded()
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
        st.download_button(
            "Скачать CSV",
            data=summary_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="data_risk_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )

        visible_ids = [candidate.candidate_id for candidate in visible_candidates]
        current_selected_id = st.session_state.get("selected_candidate_id")
        if current_selected_id not in visible_ids:
            current_selected_id = visible_ids[0]
            st.session_state["selected_candidate_id"] = current_selected_id

        candidate = next(item for item in visible_candidates if item.candidate_id == current_selected_id)
        process_risks = agent.get_process_risks(candidate.process_id)
        exact_combination_risks = find_combination_risks(process_risks, candidate.service_id, candidate.service_name)
        generalization = summarize_generalization(candidate, exact_combination_risks)
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

            chain_box = st.container(border=True)
            with chain_box:
                st.markdown("### Цепочка данных и потерь")
                st.caption("Кратко поясняет, откуда пришли проблемные данные, как они участвуют в процессе и где могут реализоваться потери.")
                for line in build_chain_lines(candidate):
                    st.write(f"- {line}")

            new_risk_box = st.container(border=True)
            with new_risk_box:
                box_title = "### Проект уточнения существующего риска" if exact_combination_risks else "### Проект нового риска"
                st.markdown(box_title)
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
                current_exact_combination_risks = find_combination_risks(process_risks, edited_service_id, edited_service_name)
                has_exact_combination_risk = bool(current_exact_combination_risks)

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

                utility_columns = st.columns(2)
                if utility_columns[0].button(
                    "Разместить сформированную агентом версию",
                    key=f"apply_generated::{candidate.candidate_id}",
                ):
                    open_confirmation(candidate.candidate_id, "apply_generated")
                    st.rerun()
                if not is_registered_status(candidate.status):
                    if has_exact_combination_risk:
                        st.markdown("**Доступные решения по существующему риску на этом сочетании**")
                        decision_columns = st.columns(5)
                        if decision_columns[0].button(
                            "Зарегистрировать скорректированную версию",
                            key=f"register_corrected_editor::{candidate.candidate_id}",
                        ):
                            open_confirmation(candidate.candidate_id, "register_corrected")
                            st.rerun()
                        if decision_columns[1].button(
                            "Привязать инциденты к существующему риску",
                            key=f"link_existing_editor::{candidate.candidate_id}",
                        ):
                            open_confirmation(candidate.candidate_id, "link_existing")
                            st.rerun()
                        if decision_columns[2].button(
                            "Обобщить существующий риск",
                            key=f"merge_existing_editor::{candidate.candidate_id}",
                        ):
                            open_confirmation(candidate.candidate_id, "merge_existing")
                            st.rerun()
                        if decision_columns[3].button(
                            "Дополнить новым сценарием",
                            key=f"keep_separate_editor::{candidate.candidate_id}",
                        ):
                            open_confirmation(candidate.candidate_id, "keep_separate")
                            st.rerun()
                        if decision_columns[4].button(
                            "Отклонить",
                            key=f"reject_editor::{candidate.candidate_id}",
                        ):
                            open_confirmation(candidate.candidate_id, "reject_candidate")
                            st.rerun()
                    else:
                        st.markdown("**Доступные решения по новому риску**")
                        decision_columns = st.columns(3)
                        if decision_columns[0].button(
                            "Зарегистрировать версию агента",
                            key=f"register_generated_editor::{candidate.candidate_id}",
                        ):
                            open_confirmation(candidate.candidate_id, "register_generated")
                            st.rerun()
                        if decision_columns[1].button(
                            "Зарегистрировать скорректированную версию",
                            key=f"register_corrected_editor::{candidate.candidate_id}",
                        ):
                            open_confirmation(candidate.candidate_id, "register_corrected")
                            st.rerun()
                        if decision_columns[2].button(
                            "Отклонить",
                            key=f"reject_editor::{candidate.candidate_id}",
                        ):
                            open_confirmation(candidate.candidate_id, "reject_candidate")
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
        '<div class="method-note">Здесь собраны метрики по качеству работы агента: доля инцидентов с признаками риска данных, доля отклонений, доля корректировок и их динамика во времени. Ниже также ведется база разбора кейсов и контур обучающей обратной связи, который можно использовать для последующего обучения по предпочтениям и корректировкам.</div>',
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

    st.markdown("### База запросов и ответов по кейсам")
    st.caption(
        "Этот реестр нужен методологам: по нему видно, как агент сформулировал кейс, как ответил пользователь и что именно стоит корректировать в логике агента."
    )
    feedback_cases_df = build_feedback_cases_df()
    if not feedback_cases_df.empty:
        st.dataframe(feedback_cases_df, use_container_width=True, hide_index=True)
    else:
        st.info("Пока база разбора кейсов пуста. Она начнет наполняться после пользовательских решений по карточкам рисков.")

    st.markdown("### Контур обучающей обратной связи")
    st.caption(
        "Каждое пользовательское решение сохраняется как обучающий пример: с reward-сигналом, типом корректировки и готовыми полями для последующей донастройки агента."
    )
    learning_dataset_df = build_learning_dataset_df()
    if not learning_dataset_df.empty:
        learning_cards = st.columns(3)
        with learning_cards[0]:
            render_stat_card("Обучающих примеров", str(len(learning_dataset_df)))
        with learning_cards[1]:
            corrected_examples = int((learning_dataset_df["Режим обучения"] == "supervised_correction").sum())
            render_stat_card("Примеров с корректировкой", str(corrected_examples))
        with learning_cards[2]:
            negative_examples = int((learning_dataset_df["Reward"] < 0).sum())
            render_stat_card("Негативных сигналов", str(negative_examples))

        export_cols = st.columns(2)
        export_cols[0].download_button(
            "Скачать обучающую выборку CSV",
            data=learning_dataset_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="data_risk_learning_dataset.csv",
            mime="text/csv",
            use_container_width=True,
        )
        export_cols[1].download_button(
            "Скачать JSONL для дообучения",
            data="\n".join(json.dumps(item, ensure_ascii=False) for item in st.session_state["feedback_cases"]).encode("utf-8"),
            file_name="data_risk_learning_dataset.jsonl",
            mime="application/jsonl",
            use_container_width=True,
        )
        st.dataframe(learning_dataset_df, use_container_width=True, hide_index=True)
    else:
        st.info("Пока нет обучающих примеров. Они появятся после пользовательских решений по карточкам рисков.")
