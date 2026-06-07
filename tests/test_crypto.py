import pytest
from truss_sdk.crypto import generate_keypair, sign_payload, verify_signature


class TestCrypto:
    def test_generate_keypair_returns_hex_keys(self):
        kp = generate_keypair()
        assert len(kp.public_key) == 64
        assert len(kp.private_key) == 128
        int(kp.public_key, 16)
        int(kp.private_key, 16)

    def test_sign_payload_and_verify_round_trip(self):
        kp = generate_keypair()
        payload = {"action": "test", "value": 42}

        sig = sign_payload(payload, kp.private_key)
        assert len(sig) == 128
        int(sig, 16)

        valid = verify_signature(payload, sig, kp.public_key)
        assert valid is True

    def test_verify_signature_rejects_wrong_key(self):
        kp1 = generate_keypair()
        kp2 = generate_keypair()
        payload = {"action": "test"}

        sig = sign_payload(payload, kp1.private_key)
        valid = verify_signature(payload, sig, kp2.public_key)
        assert valid is False

    def test_verify_signature_rejects_tampered_payload(self):
        kp = generate_keypair()
        payload = {"action": "test"}

        sig = sign_payload(payload, kp.private_key)
        tampered = {"action": "tampered"}
        valid = verify_signature(tampered, sig, kp.public_key)
        assert valid is False

    def test_signature_is_deterministic(self):
        kp = generate_keypair()
        payload = {"msg": "hello", "num": 1}

        sig1 = sign_payload(payload, kp.private_key)
        sig2 = sign_payload(payload, kp.private_key)
        assert sig1 == sig2
