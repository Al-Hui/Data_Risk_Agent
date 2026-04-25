from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from itertools import count

from .adapters import (
    ContractRegistry,
    ExistingRiskSource,
    ExternalMitigationRegistryClient,
    ExternalRiskRegistryClient,
    IncidentSource,
    RemediationWorkSource,
    ServiceRoleRegistry,
)
from .config import AppConfig
from .llm import DemoReasoningProvider
from .models import (
    AuditStatus,
    ExistingRisk,
    ExistingRiskMatch,
    Incident,
    IncidentCaseType,
    MitigationCandidate,
    PipelineResult,
    QualityMetrics,
    RegistrationMode,
    RegistrationTask,
    ResolvedFlow,
    RiskCandidate,
    RiskScenario,
    RiskStatus,
    IncidentTrendPoint,
    ValidationResult,
    ValidationVerdict,
)
from .utils import extract_references, normalize_text, unique_preserve_order


class DataRiskAgent:
    def __init__(
        self,
        config: AppConfig,
        incident_source: IncidentSource | None = None,
        contract_registry: ContractRegistry | None = None,
        role_registry: ServiceRoleRegistry | None = None,
        existing_risk_source: ExistingRiskSource | None = None,
        remediation_work_source: RemediationWorkSource | None = None,
        llm: DemoReasoningProvider | None = None,
        risk_registry_client: ExternalRiskRegistryClient | None = None,
        mitigation_registry_client: ExternalMitigationRegistryClient | None = None,
    ) -> None:
        self.config = config
        self.incident_source = incident_source or IncidentSource(config.data_dir / "incidents.csv")
        self.contract_registry = contract_registry or ContractRegistry(config.data_dir / "contracts.csv")
        self.role_registry = role_registry or ServiceRoleRegistry(config.data_dir / "service_roles.csv")
        self.existing_risk_source = existing_risk_source or ExistingRiskSource(config.data_dir / "existing_risks.csv")
        self.remediation_work_source = remediation_work_source or RemediationWorkSource(config.data_dir / "remediation_works.csv")
        self.llm = llm or DemoReasoningProvider(config.data_dir / "demo_reasoning.json")
        self.risk_registry_client = risk_registry_client or ExternalRiskRegistryClient()
        self.mitigation_registry_client = mitigation_registry_client or ExternalMitigationRegistryClient()
        self._task_seq = count(1)
        self._candidate_cache: dict[str, RiskCandidate] = {}

    def run(self) -> PipelineResult:
        incidents = self.incident_source.list_incidents()
        grouped_candidates: dict[tuple[str, str], list[RiskCandidate]] = defaultdict(list)
        ignored_incidents: list[str] = []
        rejected_incidents: list[str] = []

        for incident in incidents:
            scenarios = self.analyze_incident(incident.incident_id)
            if not scenarios:
                case_type = self.classify_incident(incident)
                if case_type is IncidentCaseType.IGNORE:
                    ignored_incidents.append(incident.incident_id)
                else:
                    rejected_incidents.append(incident.incident_id)
                continue
            per_incident_candidates = self._build_candidates_from_scenarios(scenarios)
            for candidate in per_incident_candidates:
                grouped_candidates[(candidate.process_id, candidate.service_id)].append(candidate)

        merged_candidates = [self.merge_candidates(candidates) for candidates in grouped_candidates.values()]
        final_candidates: list[RiskCandidate] = []
        registration_tasks: list[RegistrationTask] = []
        for candidate in merged_candidates:
            all_process_risks = self._list_process_risks(candidate.process_id)
            candidate.existing_risk_matches = self.find_existing_risks(candidate.process_id)
            has_existing_process_risks = bool(all_process_risks)
            candidate.merge_proposal = self.llm.propose_merge(candidate.candidate_id, candidate.description, [
                ExistingRisk(
                    risk_id=match.risk_id,
                    process_id=match.process_id,
                    process_name=match.process_name,
                    service_id=match.service_id,
                    service_name=match.service_name,
                    status=match.status,
                    title=match.title,
                    description=match.description,
                )
                for match in candidate.existing_risk_matches
            ])
            candidate.mitigation_candidates = self.suggest_mitigations(candidate.candidate_id)
            if candidate.validation.verdict is ValidationVerdict.PASS:
                candidate.status = RiskStatus.VALIDATED
                if (
                    candidate.validation.confidence >= self.config.auto_register_threshold
                    and not has_existing_process_risks
                ):
                    candidate.status = RiskStatus.AUTO_READY
                    task = self.register_risk(candidate.candidate_id, RegistrationMode.REGISTER_AS_PROPOSED)
                    registration_tasks.append(task)
                    if task.audit_status is AuditStatus.SUCCESS:
                        candidate.status = RiskStatus.AUTO_REGISTERED
                    else:
                        candidate.status = RiskStatus.NEEDS_REVIEW
            elif candidate.validation.verdict is ValidationVerdict.FAIL:
                candidate.status = RiskStatus.REJECTED
            else:
                candidate.status = RiskStatus.NEEDS_REVIEW
            final_candidates.append(candidate)
            self._candidate_cache[candidate.candidate_id] = candidate

        return PipelineResult(
            incidents_total=len(incidents),
            candidates=sorted(final_candidates, key=lambda item: item.candidate_id),
            registration_tasks=registration_tasks,
            ignored_incidents=ignored_incidents,
            rejected_incidents=rejected_incidents,
        )

    def list_candidates(self) -> list[RiskCandidate]:
        if not self._candidate_cache:
            self.run()
        return list(self._candidate_cache.values())

    def compute_quality_metrics(self, candidates: list[RiskCandidate] | None = None) -> QualityMetrics:
        incidents = self.incident_source.list_incidents()
        trend_buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "data_risk": 0})
        incidents_with_data_risk_signs = 0

        for incident in incidents:
            period = incident.reported_at.strftime("%Y-%m")
            trend_buckets[period]["total"] += 1
            if self.classify_incident(incident) is not IncidentCaseType.IGNORE:
                incidents_with_data_risk_signs += 1
                trend_buckets[period]["data_risk"] += 1

        active_candidates = candidates if candidates is not None else self.list_candidates()
        total_risk_candidates = len(active_candidates)
        rejected_risks = sum(
            candidate.status is RiskStatus.REJECTED
            or any("отклонен пользователем" in message.lower() for message in candidate.audit_log)
            for candidate in active_candidates
        )
        corrected_risks = sum(
            candidate.status is RiskStatus.USER_EDITED
            or any("изменено пользователем" in message.lower() for message in candidate.audit_log)
            for candidate in active_candidates
        )

        trend = [
            IncidentTrendPoint(
                period=period,
                total_incidents=bucket["total"],
                incidents_with_data_risk_signs=bucket["data_risk"],
                data_risk_share=(bucket["data_risk"] / bucket["total"]) if bucket["total"] else 0.0,
            )
            for period, bucket in sorted(trend_buckets.items())
        ]

        return QualityMetrics(
            total_incidents=len(incidents),
            incidents_with_data_risk_signs=incidents_with_data_risk_signs,
            data_risk_share=(incidents_with_data_risk_signs / len(incidents)) if incidents else 0.0,
            total_risk_candidates=total_risk_candidates,
            rejected_risks=rejected_risks,
            rejected_risk_share=(rejected_risks / total_risk_candidates) if total_risk_candidates else 0.0,
            corrected_risks=corrected_risks,
            corrected_risk_share=(corrected_risks / total_risk_candidates) if total_risk_candidates else 0.0,
            trend=trend,
        )

    def get_candidate(self, candidate_id: str) -> RiskCandidate:
        if not self._candidate_cache:
            self.run()
        return self._candidate_cache[candidate_id]

    def classify_incident(self, incident: Incident) -> IncidentCaseType:
        text = normalize_text(incident.cause, incident.description)
        references = extract_references(text)
        if references or any(keyword in text for keyword in ("контракт", "оферт", "тракт")):
            return IncidentCaseType.STANDARD
        assessment = self.llm.assess_data_issue(incident)
        return IncidentCaseType.NONSTANDARD if assessment.is_data_issue else IncidentCaseType.IGNORE

    def analyze_incident(self, incident_id: str) -> list[RiskScenario]:
        incident = next(item for item in self.incident_source.list_incidents() if item.incident_id == incident_id)
        case_type = self.classify_incident(incident)
        if case_type is IncidentCaseType.IGNORE:
            return []
        flows = self._resolve_flows(incident, case_type)
        scenarios: list[RiskScenario] = []
        for flow in flows:
            if not flow.loss_process_name:
                continue
            narrative = self.llm.generate_scenario(incident, flow)
            scenario = RiskScenario(
                scenario_id=f"SCN-{incident.incident_id}-{flow.process_id}",
                incident_id=incident.incident_id,
                service_id=flow.receiver_service_id,
                service_name=flow.receiver_service_name,
                process_id=flow.process_id,
                process_name=flow.process_name,
                loss_process_id=flow.loss_process_id,
                loss_process_name=flow.loss_process_name,
                role_description=flow.role_description,
                process_outcome=flow.process_outcome,
                data_degradation_hypothesis=narrative.description,
                business_impact=narrative.business_impact or (
                    f"Процесс '{flow.loss_process_name}' может принять неверное решение "
                    f"из-за данных из сервиса {flow.receiver_service_name}."
                ),
                evidence=flow.evidence,
                confidence=narrative.confidence,
            )
            validation = self.llm.validate_scenario(scenario)
            if validation.verdict is ValidationVerdict.PASS:
                scenarios.append(scenario)
        return scenarios

    def validate_risk(self, candidate_id: str) -> ValidationResult:
        candidate = self.get_candidate(candidate_id)
        return candidate.validation

    def merge_candidates(self, candidates: list[RiskCandidate]) -> RiskCandidate:
        base = candidates[0]
        all_scenarios = [scenario for candidate in candidates for scenario in candidate.scenarios]
        incident_ids = unique_preserve_order(
            incident_id
            for candidate in candidates
            for incident_id in candidate.incident_ids
        )
        validations = [candidate.validation for candidate in candidates]
        pass_confidences = [item.confidence for item in validations if item.verdict is ValidationVerdict.PASS]
        review_confidences = [item.confidence for item in validations if item.verdict is ValidationVerdict.REVIEW]
        if pass_confidences:
            verdict = ValidationVerdict.PASS
            confidence = max(pass_confidences)
            rationale = "Все включенные в карточку сценарии подтверждают риск данных для этой пары процесс + ИТ-услуга."
        elif review_confidences:
            verdict = ValidationVerdict.REVIEW
            confidence = max(review_confidences)
            rationale = "Подтвержденные сценарии не найдены, поэтому риск требует ручной проверки."
        else:
            verdict = ValidationVerdict.FAIL
            confidence = max((item.confidence for item in validations), default=0.2)
            rationale = "Ни один сценарий не подтвердил риск данных."
        validation = ValidationResult(
            verdict=verdict,
            confidence=confidence,
            rationale=rationale,
            data_quality_signals=unique_preserve_order(
                signal
                for item in validations
                for signal in item.data_quality_signals
            ),
            rejection_reasons=unique_preserve_order(
                reason
                for item in validations
                for reason in item.rejection_reasons
            ),
        )
        description = self._format_candidate_description(all_scenarios)
        merged = replace(
            base,
            candidate_id=f"{base.process_id}::{base.service_id}",
            incident_ids=incident_ids,
            scenarios=all_scenarios,
            description=description,
            validation=validation,
            structured_facts=unique_preserve_order(
                fact
                for candidate in candidates
                for fact in candidate.structured_facts
            ),
            audit_log=unique_preserve_order(
                log
                for candidate in candidates
                for log in candidate.audit_log
            ),
        )
        self._candidate_cache[merged.candidate_id] = merged
        return merged

    def _format_candidate_description(self, scenarios: list[RiskScenario]) -> str:
        scenario_descriptions = unique_preserve_order(
            scenario.data_degradation_hypothesis for scenario in scenarios
        )
        if len(scenario_descriptions) <= 1:
            return scenario_descriptions[0] if scenario_descriptions else ""
        return "\n\n".join(
            f"Сценарий {index}: {description}"
            for index, description in enumerate(scenario_descriptions, start=1)
        )

    def _list_process_risks(self, process_id: str) -> list[ExistingRisk]:
        return [
            risk for risk in self.existing_risk_source.list_existing_risks()
            if risk.process_id == process_id
        ]

    def get_process_risks(self, process_id: str) -> list[ExistingRisk]:
        return self._list_process_risks(process_id)

    def has_process_risks(self, process_id: str) -> bool:
        return bool(self._list_process_risks(process_id))

    def find_existing_risks(self, process_id: str) -> list[ExistingRiskMatch]:
        matches: list[ExistingRiskMatch] = []
        existing_risks = self._list_process_risks(process_id)
        for risk in existing_risks:
            similarity = round(self._estimate_similarity(risk), 2)
            if similarity < 0.80:
                continue
            matches.append(
                ExistingRiskMatch(
                    risk_id=risk.risk_id,
                    process_id=risk.process_id,
                    process_name=risk.process_name,
                    service_id=risk.service_id,
                    service_name=risk.service_name,
                    status=risk.status,
                    title=risk.title,
                    description=risk.description,
                    similarity=similarity,
                    rationale="Риск признан похожим, потому что относится к тому же процессу и описывает близкий сценарий ошибочного решения на некачественных данных.",
                    merge_proposal=(
                        f"Рассмотреть объединение с риском '{risk.title}' "
                        "или добавить новый сценарий риска данных."
                    ),
                )
            )
        return matches

    def _estimate_similarity(self, risk: ExistingRisk) -> float:
        text = normalize_text(risk.title, risk.description)
        score = 0.60
        keyword_groups = (
            ("кредит", "скоринг", "потенциал"),
            ("лимит", "выплат"),
            ("данн", "качеств"),
            ("решени", "расчет"),
        )
        for keywords in keyword_groups:
            if any(keyword in text for keyword in keywords):
                score += 0.1
        return min(score, 0.95)

    def suggest_mitigations(self, candidate_id: str) -> list[MitigationCandidate]:
        candidate = self.get_candidate(candidate_id)
        works = self.remediation_work_source.list_works()
        related: list[MitigationCandidate] = []
        for work in works:
            if work.incident_id in candidate.incident_ids or work.service_id == candidate.service_id:
                rationale = self.llm.explain_mitigation(work.work_id, work.title, work.description)
                related.append(
                    MitigationCandidate(
                        work_ids=[work.work_id],
                        service_id=work.service_id,
                        service_name=work.service_name,
                        description=f"{work.title}: {work.description}",
                        rationale=rationale,
                    )
                )
        return related

    def register_risk(self, candidate_id: str, mode: RegistrationMode) -> RegistrationTask:
        candidate = self.get_candidate(candidate_id)
        payload = {
            "candidate_id": candidate.candidate_id,
            "process_id": candidate.process_id,
            "process_name": candidate.process_name,
            "service_id": candidate.service_id,
            "service_name": candidate.service_name,
            "loss_process_id": candidate.loss_process_id,
            "loss_process_name": candidate.loss_process_name,
            "incident_ids": candidate.incident_ids,
            "description": candidate.description,
            "merge_proposal": candidate.merge_proposal,
        }
        ok, message = self.risk_registry_client.register(payload)
        task = RegistrationTask(
            task_id=f"REG-{next(self._task_seq)}",
            candidate_id=candidate_id,
            target_type="risk",
            mode=mode,
            payload=payload,
            audit_status=AuditStatus.SUCCESS if ok else AuditStatus.MANUAL_REVIEW,
            message=message,
        )
        candidate.audit_log.append(message)
        if ok:
            candidate.status = RiskStatus.REGISTERED if mode is not RegistrationMode.REGISTER_AS_PROPOSED else candidate.status
        return task

    def register_mitigation(self, candidate_id: str, mitigation_ids: list[str]) -> RegistrationTask:
        candidate = self.get_candidate(candidate_id)
        payload = {
            "candidate_id": candidate.candidate_id,
            "process_id": candidate.process_id,
            "service_id": candidate.service_id,
            "mitigation_ids": mitigation_ids,
        }
        ok, message = self.mitigation_registry_client.register(payload)
        task = RegistrationTask(
            task_id=f"REG-{next(self._task_seq)}",
            candidate_id=candidate_id,
            target_type="mitigation",
            mode=RegistrationMode.REGISTER_MITIGATION,
            payload=payload,
            audit_status=AuditStatus.SUCCESS if ok else AuditStatus.MANUAL_REVIEW,
            message=message,
        )
        candidate.audit_log.append(message)
        return task

    def apply_user_override(self, candidate_id: str, new_description: str) -> RiskCandidate:
        candidate = self.get_candidate(candidate_id)
        candidate.description = new_description.strip()
        candidate.status = RiskStatus.USER_EDITED
        candidate.audit_log.append("Описание риска изменено пользователем.")
        return candidate

    def _build_candidates_from_scenarios(self, scenarios: list[RiskScenario]) -> list[RiskCandidate]:
        candidates: list[RiskCandidate] = []
        for scenario in scenarios:
            validation = self.llm.validate_scenario(scenario)
            if any("не извлечен" in evidence.lower() for evidence in scenario.evidence):
                validation = ValidationResult(
                    verdict=ValidationVerdict.REVIEW,
                    confidence=min(validation.confidence, 0.6),
                    rationale="Риск найден, но идентификатор контракта/оферты не извлечен и требует ручной проверки.",
                    data_quality_signals=validation.data_quality_signals,
                    rejection_reasons=["Не извлечен идентификатор контракта или оферты."],
                )
            if validation.verdict is not ValidationVerdict.PASS:
                continue
            description = scenario.data_degradation_hypothesis
            candidate = RiskCandidate(
                candidate_id=f"{scenario.process_id}::{scenario.service_id}::{scenario.incident_id}",
                process_id=scenario.process_id,
                process_name=scenario.process_name,
                service_id=scenario.service_id,
                service_name=scenario.service_name,
                loss_process_id=scenario.loss_process_id,
                loss_process_name=scenario.loss_process_name,
                incident_ids=[scenario.incident_id],
                scenarios=[scenario],
                description=description,
                status=RiskStatus.NEW,
                validation=validation,
                structured_facts=[
                    f"ИТ-услуга {scenario.service_name} участвует в процессе {scenario.process_name}.",
                    f"Процесс завершается результатом: {scenario.process_outcome}.",
                    f"Потери реализуются в процессе: {scenario.loss_process_name}.",
                ],
                audit_log=["Кандидат сформирован из инцидента."],
            )
            candidates.append(candidate)
            self._candidate_cache[candidate.candidate_id] = candidate
        return candidates

    def _resolve_flows(self, incident: Incident, case_type: IncidentCaseType) -> list[ResolvedFlow]:
        roles = self.role_registry.list_roles()
        contracts = {item.contract_id: item for item in self.contract_registry.list_contracts()}
        flows: list[ResolvedFlow] = []
        text = normalize_text(incident.cause, incident.description)
        references = extract_references(text)

        if case_type is IncidentCaseType.STANDARD and references:
            for reference in references:
                contract = contracts.get(reference)
                if not contract:
                    continue
                matching_roles = [
                    role for role in roles
                    if role.service_id == contract.receiver_service_id
                ]
                for role in matching_roles:
                    if not role.loss_possible:
                        continue
                    flows.append(
                        ResolvedFlow(
                            source_incident_id=incident.incident_id,
                            matched_reference=reference,
                            receiver_service_id=contract.receiver_service_id,
                            receiver_service_name=contract.receiver_service_name,
                            process_id=role.process_id,
                            process_name=role.process_name,
                            role_description=role.role_description,
                            process_outcome=role.process_outcome,
                            loss_process_id=role.loss_process_id,
                            loss_process_name=role.loss_process_name,
                            evidence=[
                                f"Из инцидента извлечен идентификатор {reference}.",
                                f"По реестру контрактов получатель данных: {contract.receiver_service_name}.",
                                f"Роль в процессе: {role.role_description}.",
                            ],
                        )
                    )

        if flows:
            return flows

        if case_type is IncidentCaseType.STANDARD and not references:
            matching_roles = [
                role for role in roles
                if role.service_id == incident.service_id and role.loss_possible
            ]
            for role in matching_roles:
                flows.append(
                    ResolvedFlow(
                        source_incident_id=incident.incident_id,
                        matched_reference=None,
                        receiver_service_id=role.service_id,
                        receiver_service_name=role.service_name,
                        process_id=role.process_id,
                        process_name=role.process_name,
                        role_description=role.role_description,
                        process_outcome=role.process_outcome,
                        loss_process_id=role.loss_process_id,
                        loss_process_name=role.loss_process_name,
                        evidence=[
                            "Идентификатор оферты/контракта не извлечен из инцидента.",
                            "Кейс направлен на ручную проверку по роли ИТ-услуги в процессе.",
                            f"Роль ИТ-услуги в процессе: {role.role_description}.",
                        ],
                    )
                )
            if flows:
                return flows

        assessment = self.llm.assess_data_issue(incident)
        if not assessment.is_data_issue:
            return []

        matching_roles = [
            role for role in roles
            if role.service_id == incident.service_id and role.loss_possible
        ]
        for role in matching_roles:
            flows.append(
                ResolvedFlow(
                    source_incident_id=incident.incident_id,
                    matched_reference=references[0] if references else None,
                    receiver_service_id=role.service_id,
                    receiver_service_name=role.service_name,
                    process_id=role.process_id,
                    process_name=role.process_name,
                    role_description=role.role_description,
                    process_outcome=role.process_outcome,
                    loss_process_id=role.loss_process_id,
                    loss_process_name=role.loss_process_name,
                    evidence=[
                        "Кейс обработан как нестандартный инцидент с признаками ухудшения данных.",
                        f"Выявленные сигналы: {', '.join(assessment.signals)}.",
                        f"Роль ИТ-услуги в процессе: {role.role_description}.",
                    ],
                )
            )
        return flows
