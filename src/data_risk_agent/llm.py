from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import ExistingRisk, Incident, ResolvedFlow, RiskScenario, ValidationResult, ValidationVerdict


@dataclass(slots=True)
class DataIssueAssessment:
    is_data_issue: bool
    confidence: float
    signals: list[str]
    rationale: str


@dataclass(slots=True)
class RiskNarrative:
    description: str
    confidence: float
    business_impact: str | None = None


class DemoReasoningProvider:
    """Deterministic demo provider that simulates ready-made model responses."""

    def __init__(self, fixture_path: Path) -> None:
        with fixture_path.open("r", encoding="utf-8") as handle:
            self.fixture = json.load(handle)

    def assess_data_issue(self, incident: Incident) -> DataIssueAssessment:
        payload = self.fixture["incident_assessments"].get(incident.incident_id)
        if payload is None:
            return DataIssueAssessment(
                is_data_issue=False,
                confidence=0.0,
                signals=[],
                rationale="Для инцидента не задан демо-ответ по признакам риска данных.",
            )
        return DataIssueAssessment(
            is_data_issue=payload["is_data_issue"],
            confidence=payload["confidence"],
            signals=payload["signals"],
            rationale=payload["rationale"],
        )

    def generate_scenario(self, incident: Incident, flow: ResolvedFlow) -> RiskNarrative:
        key = f"{incident.incident_id}|{flow.process_id}|{flow.receiver_service_id}"
        payload = self.fixture["scenario_narratives"][key]
        return RiskNarrative(
            description=payload["description"],
            confidence=payload["confidence"],
            business_impact=payload.get("business_impact"),
        )

    def validate_scenario(self, scenario: RiskScenario) -> ValidationResult:
        payload = self.fixture["scenario_validations"][scenario.scenario_id]
        return ValidationResult(
            verdict=ValidationVerdict(payload["verdict"]),
            confidence=payload["confidence"],
            rationale=payload["rationale"],
            data_quality_signals=payload.get("data_quality_signals", []),
            rejection_reasons=payload.get("rejection_reasons", []),
        )

    def propose_merge(self, candidate_key: str, description: str, existing_risks: list[ExistingRisk]) -> str:
        payload = self.fixture["merge_proposals"].get(candidate_key)
        if payload:
            return payload
        if existing_risks:
            return (
                "Предлагается сопоставить новый риск с уже существующим процессным риском "
                "и решить, добавлять ли новый сценарий или обновлять описание старого риска."
            )
        return "На процессе не найден существующий риск, новый риск можно регистрировать отдельно."

    def explain_mitigation(self, work_id: str, work_title: str, work_description: str) -> str:
        payload = self.fixture["mitigation_rationales"].get(work_id)
        if payload:
            return payload
        return "Мероприятие потенциально снижает риск ухудшения качества данных и ошибочного бизнес-решения."
