import json
import uuid
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from typing import Optional
from .crypto import sign_payload, generate_keypair
from .models import Keypair


class TrussClientError(Exception):
    pass


class TrussClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:4000",
        agent_id: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id

    @staticmethod
    def generate_keypair() -> Keypair:
        return generate_keypair()

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
    ) -> dict:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8") if body else None
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise TrussClientError(
                f"HTTP {e.code}: {error_body}"
            ) from e

    def create_mandate(
        self,
        mandate_id: str,
        agent_id: str,
        agent_name: str,
        issuing_principal: dict,
        scope: dict,
        jurisdiction_context: dict,
        validity: dict,
        private_key: str,
    ) -> dict:
        body = {
            "mandate_id": mandate_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "issuing_principal": issuing_principal,
            "scope": scope,
            "jurisdiction_context": jurisdiction_context,
            "validity": validity,
            "version": "1.0",
            "issuer_public_key": "",
            "signature": "",
        }
        sig_payload = {k: v for k, v in body.items() if k != "signature"}
        body["signature"] = sign_payload(sig_payload, private_key)
        return self._request("POST", "/mandates", body)

    def record_action(
        self,
        record_id: str,
        mandate_id: str,
        action_type: str,
        timestamp: str,
        agent_id: str,
        input_hash: str,
        output_hash: str,
        chain_position: int,
        prev_record_hash: Optional[str],
        private_key: str,
    ) -> dict:
        body = {
            "record_id": record_id,
            "mandate_id": mandate_id,
            "action_type": action_type,
            "timestamp": timestamp,
            "agent_id": agent_id,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "chain_position": chain_position,
            "prev_record_hash": prev_record_hash,
            "within_mandate": True,
            "signature": "",
        }
        sig_payload = {k: v for k, v in body.items() if k != "signature"}
        body["signature"] = sign_payload(sig_payload, private_key)
        return self._request("POST", "/actions", body)

    def get_mandate(self, mandate_id: str) -> dict:
        return self._request("GET", f"/mandates/{mandate_id}")

    def get_action(self, record_id: str) -> dict:
        return self._request("GET", f"/actions/{record_id}")

    def get_mandate_chain(self, mandate_id: str) -> dict:
        return self._request("GET", f"/mandates/{mandate_id}/chain")

    def action(
        self,
        action_type: str,
        mandate_id: str,
        private_key: str,
    ) -> "ActionContext":
        return ActionContext(
            client=self,
            action_type=action_type,
            mandate_id=mandate_id,
            private_key=private_key,
        )


class ActionContext:
    def __init__(
        self,
        client: TrussClient,
        action_type: str,
        mandate_id: str,
        private_key: str,
    ):
        self._client = client
        self._action_type = action_type
        self._mandate_id = mandate_id
        self._private_key = private_key
        self._input_hash: Optional[str] = None
        self._output_hash: Optional[str] = None

    def record_input(self, input_hash: str) -> None:
        self._input_hash = input_hash

    def record_output(self, output_hash: str) -> None:
        self._output_hash = output_hash

    def commit(
        self,
        agent_id: str,
        chain_position: int,
        prev_record_hash: Optional[str],
    ) -> dict:
        if self._input_hash is None:
            raise TrussClientError("input_hash not set. Call record_input() before commit.")
        if self._output_hash is None:
            raise TrussClientError("output_hash not set. Call record_output() before commit.")

        record_id = f"act_{uuid.uuid4().hex[:24]}"
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return self._client.record_action(
            record_id=record_id,
            mandate_id=self._mandate_id,
            action_type=self._action_type,
            timestamp=timestamp,
            agent_id=agent_id,
            input_hash=self._input_hash,
            output_hash=self._output_hash,
            chain_position=chain_position,
            prev_record_hash=prev_record_hash,
            private_key=self._private_key,
        )
