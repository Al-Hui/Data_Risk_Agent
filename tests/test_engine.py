from __future__ import annotations

from pathlib import Path

from data_risk_agent import AppConfig, DataRiskAgent
from data_risk_agent.adapters import ExternalRiskRegistryClient
from data_risk_agent.models import RegistrationMode, RiskStatus, ValidationVerdict


EXPECTED_MAIN_RISK_DESCRIPTION = (
    "риск возникновения финансовых потерь из-за принятия неверного решния по кредитованию клиентов "
    "физических лиц вследствие некорректного расчета кредитного потенциала из-за использования "
    "данных низкого качества, поступающих в АПР Фронтбэк (CI12345667) от ЧАП Заря (CI94565765), "
    "по причине некорректно проведенных плановых работ по обновлению оборудования ФП Хадуп"
)


def build_agent() -> DataRiskAgent:
    project_root = Path(__file__).resolve().parents[1]
    return DataRiskAgent(AppConfig(data_dir=project_root / "data"))


def test_standard_incident_extracts_reference_and_resolves_receiver() -> None:
    agent = build_agent()
    scenarios = agent.analyze_incident("INC-1001")
    assert scenarios
    assert scenarios[0].source_service_id == "CI94565765"
    assert scenarios[0].service_id == "CI12345667"
    assert scenarios[0].matched_reference == "OF-3001"
    assert any("OF-3001" in evidence for evidence in scenarios[0].evidence)


def test_main_demo_risk_has_expected_description() -> None:
    agent = build_agent()
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P1340::CI12345667")
    assert candidate.process_name == "П1340 Кредитование клиентов ФЛ"
    assert candidate.service_name == "АПР Фронтбэк"
    assert candidate.description == EXPECTED_MAIN_RISK_DESCRIPTION


def test_unconfirmed_scenarios_are_not_included_in_candidates() -> None:
    agent = build_agent()
    result = agent.run()
    assert all(item.candidate_id != "P1180::CI66778899" for item in result.candidates)
    assert "INC-1005" in result.rejected_incidents


def test_nonstandard_data_incident_is_analyzed() -> None:
    agent = build_agent()
    scenarios = agent.analyze_incident("INC-1006")
    assert scenarios
    assert "несвоевременно загруженных данных" in scenarios[0].data_degradation_hypothesis


def test_nonstandard_non_data_incident_is_ignored() -> None:
    agent = build_agent()
    scenarios = agent.analyze_incident("INC-1004")
    assert scenarios == []


def test_multiple_incidents_merge_into_one_candidate() -> None:
    agent = build_agent()
    result = agent.run()
    merged = next(item for item in result.candidates if item.candidate_id == "P1340::CI12345667")
    assert {"INC-1001", "INC-1002"}.issubset(set(merged.incident_ids))
    assert len(merged.scenarios) >= 2


def test_multiple_unique_scenarios_are_separated_explicitly() -> None:
    agent = build_agent()
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P2210::CI22334455")
    assert "Сценарий 1:" in candidate.description
    assert "Сценарий 2:" in candidate.description


def test_existing_risk_lookup_uses_process_only() -> None:
    agent = build_agent()
    matches = agent.find_existing_risks("P1340")
    assert matches
    assert all(match.process_id == "P1340" for match in matches)
    assert all(match.similarity >= 0.80 for match in matches)


def test_candidate_shows_process_risks_without_service_filter() -> None:
    agent = build_agent()
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P2210::CI22334455")
    assert candidate.existing_risk_matches
    assert candidate.existing_risk_matches[0].risk_id == "R-1002"


def test_combination_risk_lookup_uses_process_and_service() -> None:
    agent = build_agent()
    exact_matches = agent.get_combination_risks("P1340", "CI12345667")
    no_matches = agent.get_combination_risks("P1340", "CI00000000")
    assert len(exact_matches) == 1
    assert exact_matches[0].risk_id == "R-1001"
    assert no_matches == []


def test_only_similar_existing_risks_are_returned() -> None:
    agent = build_agent()
    matches = agent.find_existing_risks("P1180")
    assert matches == []


def test_mitigation_candidates_are_suggested() -> None:
    agent = build_agent()
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P1340::CI12345667")
    assert candidate.mitigation_candidates
    assert candidate.mitigation_candidates[0].work_ids == ["W-1001"]


def test_high_confidence_candidate_with_existing_process_risk_is_not_auto_registered() -> None:
    agent = build_agent()
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P1340::CI12345667")
    assert candidate.validation.verdict == ValidationVerdict.PASS
    assert candidate.existing_risk_matches
    assert candidate.status == RiskStatus.VALIDATED


def test_user_override_changes_description_and_audit_log() -> None:
    agent = build_agent()
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P2210::CI22334455")
    agent.apply_user_override(candidate.candidate_id, "Новое описание риска")
    updated = agent.get_candidate(candidate.candidate_id)
    assert updated.description == "Новое описание риска"
    assert "изменено пользователем" in updated.audit_log[-1].lower()


def test_external_api_failure_moves_registration_to_manual_review() -> None:
    failing_client = ExternalRiskRegistryClient(always_fail=True)
    agent = build_agent()
    agent.risk_registry_client = failing_client
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P1340::CI12345667")
    task = agent.register_risk(candidate.candidate_id, RegistrationMode.EDIT_AND_REGISTER)
    assert task.audit_status.value == "MANUAL_REVIEW"


def test_register_as_proposed_marks_candidate_registered() -> None:
    agent = build_agent()
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P2210::CI22334455")
    task = agent.register_risk(candidate.candidate_id, RegistrationMode.REGISTER_AS_PROPOSED)
    assert task.audit_status.value == "SUCCESS"
    assert candidate.status == RiskStatus.REGISTERED


def test_quality_metrics_are_calculated() -> None:
    agent = build_agent()
    result = agent.run()
    candidate = next(item for item in result.candidates if item.candidate_id == "P2210::CI22334455")
    agent.apply_user_override(candidate.candidate_id, "Исправленное описание риска")
    candidate.status = RiskStatus.REJECTED
    candidate.audit_log.append("Кандидат отклонен пользователем.")

    metrics = agent.compute_quality_metrics(result.candidates)
    assert metrics.total_incidents == 20
    assert metrics.incidents_with_data_risk_signs == 17
    assert metrics.total_risk_candidates == 2
    assert metrics.rejected_risks >= 1
    assert metrics.corrected_risks >= 1
    assert metrics.trend
