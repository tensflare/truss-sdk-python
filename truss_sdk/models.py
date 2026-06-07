from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Keypair:
    public_key: str
    private_key: str


@dataclass
class IssuingPrincipal:
    entity: str
    human_id: str
    role: str


@dataclass
class Scope:
    permitted_actions: list[str]
    forbidden_actions: list[str] = field(default_factory=list)
    permitted_data_classes: list[str] = field(default_factory=list)
    max_delegation_depth: int = 0
    resource_bounds: list[str] = field(default_factory=list)


@dataclass
class JurisdictionContext:
    deploying_org_jurisdiction: str
    operating_jurisdictions: list[str]
    regulatory_frameworks: list[str] = field(default_factory=list)


@dataclass
class Validity:
    issued_at: str
    expires_at: str
    single_use: bool = False


@dataclass
class Mandate:
    mandate_id: str
    version: str
    agent_id: str
    agent_name: str
    issuing_principal: IssuingPrincipal
    scope: Scope
    jurisdiction_context: JurisdictionContext
    validity: Validity
    signature: str
    issuer_public_key: str


@dataclass
class JurisdictionFlag:
    framework: str
    obligation: str
    severity: str
    article: Optional[str] = None
    guidance: Optional[str] = None


@dataclass
class JurisdictionEvaluation:
    evaluated_at: str
    frameworks_applied: list[str] = field(default_factory=list)
    status: str = "unknown"
    flags: list[JurisdictionFlag] = field(default_factory=list)


@dataclass
class ActionRecord:
    record_id: str
    mandate_id: str
    action_type: str
    timestamp: str
    agent_id: str
    input_hash: str
    output_hash: str
    within_mandate: bool = True
    jurisdiction_evaluation: Optional[JurisdictionEvaluation] = None
    chain_position: int = 0
    prev_record_hash: Optional[str] = None
    signature: str = ""
