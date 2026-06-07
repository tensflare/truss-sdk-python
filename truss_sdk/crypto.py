import json
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
from .models import Keypair


def generate_keypair() -> Keypair:
    signing_key = SigningKey.generate()
    public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("ascii")
    seed = signing_key.encode(encoder=HexEncoder).decode("ascii")
    private_key = seed + public_key
    return Keypair(public_key=public_key, private_key=private_key)


def _canonical_json(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _hex_to_seed(key_hex: str) -> bytes:
    raw = bytes.fromhex(key_hex)
    if len(raw) == 32:
        return raw
    if len(raw) == 64:
        return raw[:32]
    raise ValueError(
        f"Invalid key length: expected 32 or 64 bytes, got {len(raw)}"
    )


def sign_payload(payload: dict, private_key_hex: str) -> str:
    canonical = _canonical_json(payload)
    seed = _hex_to_seed(private_key_hex)
    signing_key = SigningKey(seed)
    signed = signing_key.sign(canonical)
    return signed.signature.hex()


def verify_signature(payload: dict, signature_hex: str, public_key_hex: str) -> bool:
    canonical = _canonical_json(payload)
    signature = bytes.fromhex(signature_hex)
    verify_key = VerifyKey(public_key_hex, encoder=HexEncoder)
    try:
        verify_key.verify(canonical, signature)
        return True
    except BadSignatureError:
        return False
