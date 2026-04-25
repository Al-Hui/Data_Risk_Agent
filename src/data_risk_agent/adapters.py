from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .models import ContractRecord, ExistingRisk, Incident, RemediationWork, ServiceRole


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class IncidentSource:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_incidents(self) -> list[Incident]:
        return [
            Incident(
                incident_id=row["incident_id"],
                reported_at=date.fromisoformat(row["reported_at"]),
                cause=row["cause"],
                description=row["description"],
                service_id=row["service_id"],
                service_name=row["service_name"],
                solution=row["solution"],
            )
            for row in _read_csv(self.path)
        ]


class ContractRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_contracts(self) -> list[ContractRecord]:
        return [
            ContractRecord(
                contract_id=row["contract_id"],
                receiver_service_id=row["receiver_service_id"],
                receiver_service_name=row["receiver_service_name"],
                description=row["description"],
            )
            for row in _read_csv(self.path)
        ]


class ServiceRoleRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_roles(self) -> list[ServiceRole]:
        return [
            ServiceRole(
                service_id=row["service_id"],
                service_name=row["service_name"],
                process_id=row["process_id"],
                process_name=row["process_name"],
                role_description=row["role_description"],
                process_outcome=row["process_outcome"],
                loss_process_id=row["loss_process_id"],
                loss_process_name=row["loss_process_name"],
                loss_possible=row["loss_possible"].strip().lower() == "true",
            )
            for row in _read_csv(self.path)
        ]


class ExistingRiskSource:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_existing_risks(self) -> list[ExistingRisk]:
        return [
            ExistingRisk(
                risk_id=row["risk_id"],
                process_id=row["process_id"],
                process_name=row["process_name"],
                service_id=row["service_id"],
                service_name=row["service_name"],
                status=row["status"],
                title=row["title"],
                description=row["description"],
            )
            for row in _read_csv(self.path)
        ]


class RemediationWorkSource:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_works(self) -> list[RemediationWork]:
        return [
            RemediationWork(
                work_id=row["work_id"],
                incident_id=row["incident_id"],
                service_id=row["service_id"],
                service_name=row["service_name"],
                title=row["title"],
                description=row["description"],
            )
            for row in _read_csv(self.path)
        ]


class ExternalRiskRegistryClient:
    def __init__(self, always_fail: bool = False) -> None:
        self.always_fail = always_fail
        self.created_payloads: list[dict] = []

    def register(self, payload: dict) -> tuple[bool, str]:
        if self.always_fail or payload.get("force_fail"):
            return False, "Внешний API реестра рисков вернул ошибку."
        self.created_payloads.append(payload)
        return True, "Риск зарегистрирован во внешнем реестре."


class ExternalMitigationRegistryClient:
    def __init__(self, always_fail: bool = False) -> None:
        self.always_fail = always_fail
        self.created_payloads: list[dict] = []

    def register(self, payload: dict) -> tuple[bool, str]:
        if self.always_fail or payload.get("force_fail"):
            return False, "Внешний API реестра мероприятий вернул ошибку."
        self.created_payloads.append(payload)
        return True, "Мероприятие зарегистрировано во внешнем реестре."
