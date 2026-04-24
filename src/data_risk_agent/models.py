from __future__ import annotations

from datetime import date
from dataclasses import dataclass, field
from enum import StrEnum


class IncidentCaseType(StrEnum):
    STANDARD = "STANDARD"
    NONSTANDARD = "NONSTANDARD"
    IGNORE = "IGNORE"


class RiskStatus(StrEnum):
    NEW = "NEW"
    REJECTED = "REJECTED"
    VALIDATED = "VALIDATED"
    AUTO_READY = "AUTO_READY"
    AUTO_REGISTERED = "AUTO_REGISTERED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    USER_EDITED = "USER_EDITED"
    REGISTERED = "REGISTERED"


class ValidationVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class RegistrationMode(StrEnum):
    REGISTER_AS_PROPOSED = "REGISTER_AS_PROPOSED"
    EDIT_AND_REGISTER = "EDIT_AND_REGISTER"
    REGISTER_MITIGATION = "REGISTER_MITIGATION"
    MERGE_WITH_EXISTING = "MERGE_WITH_EXISTING"
    KEEP_AS_SEPARATE_SCENARIO = "KEEP_AS_SEPARATE_SCENARIO"


class AuditStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass(slots=True)
class Incident:
    incident_id: str
    reported_at: date
    cause: str
    description: str
    service_id: str
    service_name: str
    solution: str


@dataclass(slots=True)
class ContractRecord:
    contract_id: str
    receiver_service_id: str
    receiver_service_name: str
    description: str


@dataclass(slots=True)
class ServiceRole:
    service_id: str
    service_name: str
    process_id: str
    process_name: str
    role_description: str
    process_outcome: str
    loss_process_id: str
    loss_process_name: str
    loss_possible: bool


@dataclass(slots=True)
class ExistingRisk:
    risk_id: str
    process_id: str
    process_name: str
    title: str
    description: str


@dataclass(slots=True)
class RemediationWork:
    work_id: str
    incident_id: str
    service_id: str
    title: str
    description: str


@dataclass(slots=True)
class ResolvedFlow:
    source_incident_id: str
    matched_reference: str | None
    receiver_service_id: str
    receiver_service_name: str
    process_id: str
    process_name: str
    role_description: str
    process_outcome: str
    loss_process_id: str
    loss_process_name: str
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RiskScenario:
    scenario_id: str
    incident_id: str
    service_id: str
    service_name: str
    process_id: str
    process_name: str
    loss_process_id: str
    loss_process_name: str
    role_description: str
    process_outcome: str
    data_degradation_hypothesis: str
    business_impact: str
    evidence: list[str]
    confidence: float


@dataclass(slots=True)
class ValidationResult:
    verdict: ValidationVerdict
    confidence: float
    rationale: str
    data_quality_signals: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MitigationCandidate:
    work_ids: list[str]
    description: str
    rationale: str


@dataclass(slots=True)
class ExistingRiskMatch:
    risk_id: str
    process_id: str
    process_name: str
    title: str
    description: str
    similarity: float
    rationale: str
    merge_proposal: str


@dataclass(slots=True)
class RegistrationTask:
    task_id: str
    candidate_id: str
    target_type: str
    mode: RegistrationMode
    payload: dict
    audit_status: AuditStatus
    message: str


@dataclass(slots=True)
class RiskCandidate:
    candidate_id: str
    process_id: str
    process_name: str
    service_id: str
    service_name: str
    loss_process_id: str
    loss_process_name: str
    incident_ids: list[str]
    scenarios: list[RiskScenario]
    description: str
    status: RiskStatus
    validation: ValidationResult
    existing_risk_matches: list[ExistingRiskMatch] = field(default_factory=list)
    mitigation_candidates: list[MitigationCandidate] = field(default_factory=list)
    merge_proposal: str = ""
    structured_facts: list[str] = field(default_factory=list)
    audit_log: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PipelineResult:
    incidents_total: int
    candidates: list[RiskCandidate]
    registration_tasks: list[RegistrationTask]
    ignored_incidents: list[str] = field(default_factory=list)
    rejected_incidents: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IncidentTrendPoint:
    period: str
    total_incidents: int
    incidents_with_data_risk_signs: int
    data_risk_share: float


@dataclass(slots=True)
class QualityMetrics:
    total_incidents: int
    incidents_with_data_risk_signs: int
    data_risk_share: float
    total_risk_candidates: int
    rejected_risks: int
    rejected_risk_share: float
    corrected_risks: int
    corrected_risk_share: float
    trend: list[IncidentTrendPoint] = field(default_factory=list)
