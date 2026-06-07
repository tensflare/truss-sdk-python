import pytest
from unittest.mock import patch, MagicMock
from truss_sdk.client import TrussClient, TrussClientError, ActionContext


class TestTrussClient:
    def test_generate_keypair_returns_keypair(self):
        kp = TrussClient.generate_keypair()
        assert len(kp.public_key) == 64
        assert len(kp.private_key) == 128

    @patch("truss_sdk.client.urlopen")
    def test_create_mandate(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"mandate_id": "mnd_1", "status": "active"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = TrussClient(api_key="tr_test_key")
        result = client.create_mandate(
            mandate_id="mnd_1",
            agent_id="agt_1",
            agent_name="Test Agent",
            issuing_principal={"entity": "org_1", "human_id": "usr_1", "role": "Admin"},
            scope={"permitted_actions": ["read"]},
            jurisdiction_context={"deploying_org_jurisdiction": "US", "operating_jurisdictions": ["US"]},
            validity={"issued_at": "2026-01-01T00:00:00Z", "expires_at": "2026-12-31T00:00:00Z"},
            private_key="ab" * 64,
        )
        assert result["mandate_id"] == "mnd_1"
        assert result["status"] == "active"

        request = mock_urlopen.call_args[0][0]
        assert request.method == "POST"
        assert request.full_url.endswith("/mandates")
        assert "Bearer tr_test_key" in request.headers.get("Authorization", "")

    @patch("truss_sdk.client.urlopen")
    def test_get_mandate(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"mandate_id": "mnd_1", "status": "active"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = TrussClient(api_key="tr_test_key")
        result = client.get_mandate("mnd_1")
        assert result["mandate_id"] == "mnd_1"

        request = mock_urlopen.call_args[0][0]
        assert request.full_url.endswith("/mandates/mnd_1")

    @patch("truss_sdk.client.urlopen")
    def test_record_action(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"record_id": "act_1", "chain_position": 1}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = TrussClient(api_key="tr_test_key")
        result = client.record_action(
            record_id="act_1",
            mandate_id="mnd_1",
            action_type="read",
            timestamp="2026-01-01T00:00:00Z",
            agent_id="agt_1",
            input_hash="sha256:abc",
            output_hash="sha256:def",
            chain_position=1,
            prev_record_hash=None,
            private_key="ab" * 64,
        )
        assert result["record_id"] == "act_1"

    @patch("truss_sdk.client.urlopen")
    def test_http_error_raises_truss_error(self, mock_urlopen):
        import urllib.error

        error_resp = MagicMock()
        error_resp.read.return_value = b'{"error": "Invalid API key"}'
        error_resp.code = 401
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://localhost:4000/me", 401, "Unauthorized", {}, error_resp
        )

        client = TrussClient(api_key="bad_key")
        with pytest.raises(TrussClientError, match="401"):
            client.get_mandate("mnd_1")


class TestActionContext:
    @patch("truss_sdk.client.urlopen")
    def test_commit_requires_input_and_output(self, mock_urlopen):
        client = TrussClient(api_key="tr_test_key")
        ctx = client.action("read", "mnd_1", "ab" * 64)

        with pytest.raises(TrussClientError, match="input_hash"):
            ctx.commit("agt_1", 1, None)

        ctx.record_input("sha256:abc")
        with pytest.raises(TrussClientError, match="output_hash"):
            ctx.commit("agt_1", 1, None)

    @patch("truss_sdk.client.urlopen")
    def test_commit_sends_signed_action(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"record_id": "act_xyz", "chain_position": 1}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = TrussClient(api_key="tr_test_key")
        ctx = client.action("write", "mnd_1", "ab" * 64)
        ctx.record_input("sha256:in")
        ctx.record_output("sha256:out")

        result = ctx.commit(agent_id="agt_1", chain_position=1, prev_record_hash=None)
        assert result["record_id"] == "act_xyz"

        request = mock_urlopen.call_args[0][0]
        body = request.data
        assert b"sha256:in" in body
        assert b"sha256:out" in body
        assert b"signature" in body
