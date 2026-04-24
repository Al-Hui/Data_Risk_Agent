from __future__ import annotations

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


def initialize_ui_state() -> None:
    st.session_state.setdefault("candidate_state", {})
    st.session_state.setdefault("decision_events", [])
    st.session_state.setdefault("flash_message", None)


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
    st.session_state["candidate_state"][candidate.candidate_id] = {
        "service_name": candidate.service_name,
        "service_id": candidate.service_id,
        "description": candidate.description,
        "status": candidate.status.value,
        "audit_log": list(candidate.audit_log),
    }


def set_flash_message(level: str, text: str) -> None:
    st.session_state["flash_message"] = {"level": level, "text": text}


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


def render_candidate_row(candidate) -> dict[str, str]:
    return {
        "Идентификатор кандидата": candidate.candidate_id,
        "Бизнес-процесс": candidate.process_name,
        "Фронтальная ИТ-услуга": f"{candidate.service_name} ({candidate.service_id})",
        "Процесс-носитель потерь": candidate.loss_process_name,
        "Инциденты-основания": ", ".join(candidate.incident_ids),
        "Статус": localize_status(candidate.status),
        "Уверенность": f"{candidate.validation.confidence:.2f}",
    }


initialize_ui_state()
agent = load_agent()
pipeline = agent.run()
apply_saved_candidate_state(pipeline.candidates)
metrics = agent.compute_quality_metrics(pipeline.candidates)
st.title("Агент Риска Данных v1")
st.caption("Пакетный анализ инцидентов, дашборд проверки и подготовка регистрации риска данных.")
render_flash_message()

risk_tab, metrics_tab = st.tabs(["Риски", "Метрики качества"])

with risk_tab:
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    metrics_col1.metric("Инциденты", pipeline.incidents_total)
    metrics_col2.metric("Кандидаты риска", len(pipeline.candidates))
    metrics_col3.metric("Авто-регистрация", sum(candidate.status == RiskStatus.AUTO_REGISTERED for candidate in pipeline.candidates))
    metrics_col4.metric("Требуют проверки", sum(candidate.status == RiskStatus.NEEDS_REVIEW for candidate in pipeline.candidates))

    st.subheader("Главная витрина рисков")
    st.dataframe([render_candidate_row(candidate) for candidate in pipeline.candidates], use_container_width=True)

    candidate_ids = [candidate.candidate_id for candidate in pipeline.candidates]
    selected_id = st.selectbox("Карточка риска", candidate_ids)
    candidate = agent.get_candidate(selected_id)
    generalization = summarize_generalization(candidate)

    st.markdown("### Проект нового риска")
    if is_registered_status(candidate.status):
        st.caption("Этот риск уже зарегистрирован.")
    else:
        st.caption("Это новый риск, который пока не зарегистрирован. При необходимости ниже можно вручную уточнить фронтальную ИТ-услугу.")
    st.write(f"**Бизнес-процесс:** {candidate.process_name}")

    service_col1, service_col2 = st.columns([2, 1])
    edited_service_name = service_col1.text_input(
        "Фронтальная ИТ-услуга",
        value=candidate.service_name,
    )
    edited_service_id = service_col2.text_input(
        "Идентификатор фронтальной ИТ-услуги",
        value=candidate.service_id,
    )

    st.write(f"**Процесс-носитель потерь:** {candidate.loss_process_name}")
    st.write(f"**Идентификаторы инцидентов-оснований:** {', '.join(candidate.incident_ids)}")
    edited_description = st.text_area("Редактируемое описание риска", value=candidate.description, height=180)
    st.write(f"**Валидация:** {localize_verdict(candidate.validation.verdict)} ({candidate.validation.confidence:.2f})")
    st.write(candidate.validation.rationale)
    if candidate.validation.data_quality_signals:
        st.write("**Сигналы качества данных:** " + ", ".join(candidate.validation.data_quality_signals))
    if candidate.validation.rejection_reasons:
        st.write("**Причины отклонения:** " + "; ".join(candidate.validation.rejection_reasons))

    st.markdown("#### Сценарии")
    for scenario in candidate.scenarios:
        with st.expander(f"{scenario.scenario_id} / {scenario.incident_id}", expanded=False):
            st.write(f"**Гипотеза:** {scenario.data_degradation_hypothesis}")
            st.write(f"**Влияние:** {scenario.business_impact}")
            st.write(f"**Роль услуги:** {scenario.role_description}")
            st.write("**Обоснование:**")
            for item in scenario.evidence:
                st.write(f"- {item}")

    st.markdown("### Имеющиеся зарегистрированные риски")
    if candidate.existing_risk_matches:
        for match in candidate.existing_risk_matches:
            with st.expander(f"{match.risk_id}: {match.title}", expanded=False):
                st.write("**Статус:** Это уже зарегистрированный риск.")
                st.write(match.description)
    else:
        st.info("Похожие существующие риски не найдены.")

    st.markdown("### Краткое обоснование по объединению")
    st.write(f"**Итоговый вывод:** {generalization['title']}")
    st.write(generalization["summary"])
    st.write(candidate.merge_proposal)

    st.markdown("### Предлагаемые меры митигации")
    if candidate.mitigation_candidates:
        for mitigation in candidate.mitigation_candidates:
            st.write(f"- {', '.join(mitigation.work_ids)}: {mitigation.description}")
            st.caption(mitigation.rationale)
    else:
        st.info("Подходящие мероприятия не найдены.")

    st.markdown("### Действия")
    can_validate = True
    can_reject = not is_registered_status(candidate.status)
    can_edit_and_register = not is_registered_status(candidate.status)
    can_register_as_proposed = (
        candidate.validation.verdict is ValidationVerdict.PASS
        and not is_registered_status(candidate.status)
    )
    can_register_mitigation = bool(candidate.mitigation_candidates) and candidate.status is not RiskStatus.REJECTED
    can_merge_with_existing = bool(candidate.existing_risk_matches) and not is_registered_status(candidate.status)
    can_keep_separate = bool(candidate.existing_risk_matches) and not is_registered_status(candidate.status)
    can_link_to_existing = (
        generalization["kind"] == "covered_by_existing"
        and bool(candidate.existing_risk_matches)
        and not is_registered_status(candidate.status)
    )

    available_main_actions: list[tuple[str, str]] = [("Проверить", "validate")]
    if can_reject:
        available_main_actions.append(("Отклонить", "reject"))
    if can_edit_and_register:
        available_main_actions.append(("Исправить и зарегистрировать", "edit_register"))
    if can_register_as_proposed:
        available_main_actions.append(("Зарегистрировать как предложено", "register_proposed"))
    if can_register_mitigation:
        available_main_actions.append(("Зарегистрировать меры", "register_mitigation"))

    action_columns = st.columns(len(available_main_actions))
    for column, (label, action_key) in zip(action_columns, available_main_actions, strict=False):
        if action_key == "validate" and column.button(label):
            verdict = agent.validate_risk(candidate.candidate_id).verdict
            set_flash_message("success", f"Результат проверки: {localize_verdict(verdict)}")
            st.rerun()
        if action_key == "reject" and column.button(label):
            candidate.service_name = edited_service_name.strip()
            candidate.service_id = edited_service_id.strip()
            candidate.status = RiskStatus.REJECTED
            candidate.audit_log.append("Кандидат отклонен пользователем.")
            persist_candidate_state(candidate)
            record_decision_event("rejected", candidate)
            set_flash_message("warning", "Кандидат переведен в статус 'Отклонен'.")
            st.rerun()
        if action_key == "edit_register" and column.button(label):
            candidate.service_name = edited_service_name.strip()
            candidate.service_id = edited_service_id.strip()
            updated = agent.apply_user_override(candidate.candidate_id, edited_description)
            task = agent.register_risk(updated.candidate_id, RegistrationMode.EDIT_AND_REGISTER)
            persist_candidate_state(updated)
            record_decision_event("corrected", updated)
            set_flash_message("success", task.message)
            st.rerun()
        if action_key == "register_proposed" and column.button(label):
            candidate.service_name = edited_service_name.strip()
            candidate.service_id = edited_service_id.strip()
            candidate.description = edited_description.strip()
            task = agent.register_risk(candidate.candidate_id, RegistrationMode.REGISTER_AS_PROPOSED)
            candidate.status = RiskStatus.REGISTERED
            persist_candidate_state(candidate)
            set_flash_message("success", task.message)
            st.rerun()
        if action_key == "register_mitigation" and column.button(label):
            candidate.service_name = edited_service_name.strip()
            candidate.service_id = edited_service_id.strip()
            mitigation_ids = [item for mitigation in candidate.mitigation_candidates for item in mitigation.work_ids]
            task = agent.register_mitigation(candidate.candidate_id, mitigation_ids)
            persist_candidate_state(candidate)
            set_flash_message("success", task.message)
            st.rerun()

    available_merge_actions: list[tuple[str, str]] = []
    if can_link_to_existing:
        available_merge_actions.append((generalization["action_label"], "link_existing"))
    elif can_merge_with_existing:
        available_merge_actions.append((generalization["action_label"], "merge_existing"))
    if can_keep_separate:
        available_merge_actions.append(("Оставить отдельным сценарием", "keep_separate"))

    if available_merge_actions:
        merge_columns = st.columns(len(available_merge_actions))
        for column, (label, action_key) in zip(merge_columns, available_merge_actions, strict=False):
            if action_key == "link_existing" and column.button(label):
                candidate.service_name = edited_service_name.strip()
                candidate.service_id = edited_service_id.strip()
                candidate.audit_log.append("Пользователь решил использовать существующий риск и привязать к нему инциденты-основания.")
                persist_candidate_state(candidate)
                set_flash_message("info", "Решение использовать существующий риск сохранено в журнале действий.")
                st.rerun()
            if action_key == "merge_existing" and column.button(label):
                candidate.service_name = edited_service_name.strip()
                candidate.service_id = edited_service_id.strip()
                candidate.audit_log.append("Пользователь подтвердил объединение с существующим риском.")
                persist_candidate_state(candidate)
                set_flash_message("info", "Решение об объединении сохранено в журнале действий.")
                st.rerun()
            if action_key == "keep_separate" and column.button(label):
                candidate.service_name = edited_service_name.strip()
                candidate.service_id = edited_service_id.strip()
                candidate.audit_log.append("Пользователь оставил риск отдельным сценарием.")
                persist_candidate_state(candidate)
                set_flash_message("info", "Решение сохранить отдельный сценарий сохранено в журнале действий.")
                st.rerun()

    action_hints: list[str] = []
    if not candidate.existing_risk_matches:
        action_hints.append("Кнопки по объединению скрыты, потому что похожие существующие риски не найдены.")
    if generalization["kind"] == "covered_by_existing":
        action_hints.append("Для этого кейса рекомендуется использовать уже зарегистрированный риск и не создавать новый отдельно.")
    if not candidate.mitigation_candidates:
        action_hints.append("Кнопка регистрации мер скрыта, потому что для этого риска не предложены мероприятия.")
    if candidate.validation.verdict is not ValidationVerdict.PASS and not is_registered_status(candidate.status):
        action_hints.append("Автоматическая регистрация скрыта, потому что риск пока не подтвержден валидатором.")
    if is_registered_status(candidate.status):
        action_hints.append("Кнопки регистрации и отклонения скрыты, потому что риск уже зарегистрирован.")

    for hint in action_hints:
        st.caption(hint)

    st.markdown("### Журнал действий")
    for message in candidate.audit_log:
        st.write(f"- {message}")

with metrics_tab:
    st.subheader("Метрики качества работы системы")
    st.caption("Эта вкладка нужна для внутренней методологической оценки качества работы системы.")

    quality_col1, quality_col2, quality_col3 = st.columns(3)
    quality_col1.metric(
        "Доля инцидентов с признаками риска данных",
        f"{metrics.data_risk_share:.0%}",
        f"{metrics.incidents_with_data_risk_signs} из {metrics.total_incidents}",
    )
    quality_col2.metric(
        "Доля отклоненных рисков",
        f"{metrics.rejected_risk_share:.0%}",
        f"{metrics.rejected_risks} из {metrics.total_risk_candidates}",
    )
    quality_col3.metric(
        "Доля скорректированных рисков",
        f"{metrics.corrected_risk_share:.0%}",
        f"{metrics.corrected_risks} из {metrics.total_risk_candidates}",
    )

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
        st.caption("Как со временем меняется доля инцидентов с признаками риска данных")
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
    st.caption("Как со временем меняется число рисков, которые пользователи отклоняют или корректируют.")
    decision_trend_df = build_decision_trend_df()
    if not decision_trend_df.empty:
        st.line_chart(decision_trend_df.set_index("Период"))
        st.dataframe(decision_trend_df, use_container_width=True, hide_index=True)
    else:
        st.info("Пока нет пользовательских действий по отклонению или корректировке рисков, поэтому график пуст.")
