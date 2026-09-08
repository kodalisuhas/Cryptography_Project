"""Tests for the AES encryption/decryption engine (ECB, CBC)."""

import pytest

from src.core.aes_cipher import AESCipher

# ---------------------------------------------------------------------------
# Authoritative known-answer vectors
#
# ECB: NIST FIPS 197, Appendix C (C.1 AES-128, C.2 AES-192, C.3 AES-256).
# CBC: NIST SP 800-38A, Appendix F.2.1 (CBC-AES128.Encrypt).
# Values transcribed verbatim from the NIST sources.
# ---------------------------------------------------------------------------

FIPS197_ECB_VECTORS = [
    # (label, key_hex, plaintext_hex, ciphertext_hex)
    (
        "AES-128",
        "2b7e151628aed2a6abf7158809cf4f3c",
        "3243f6a8885a308d313198a2e0370734",
        "3925841d02dc09fbdc118597196a0b32",
    ),
    (
        "AES-192",
        "8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b",
        "6bc1bee22e409f96e93d7e117393172a",
        "bd334f1d6e45f25ff712a214571fa5cc",
    ),
    (
        "AES-256",
        "603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4",
        "6bc1bee22e409f96e93d7e117393172a",
        "f3eed1bdb5d2a03c064b5a7e3db181f8",
    ),
]

# NIST SP 800-38A F.2.1 CBC-AES128: key, iv, single plaintext block, expected
# ciphertext block.
SP800_38A_CBC_AES128 = (
    "2b7e151628aed2a6abf7158809cf4f3c",  # key
    "000102030405060708090a0b0c0d0e0f",  # iv
    "6bc1bee22e409f96e93d7e117393172a",  # plaintext block P1
    "7649abac8119b246cee98e9b12e9197d",  # expected ciphertext block C1
)


def _h(hex_str: str) -> bytes:
    """Convert a hex string to bytes."""
    return bytes.fromhex(hex_str)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key_size", [128, 192, 256])
def test_init_valid_key_sizes(key_size):
    """Test valid key sizes for both modes."""
    for mode in ("ECB", "CBC"):
        cipher = AESCipher(key_size, mode)
        assert cipher.key_size == key_size
        assert cipher.mode == mode


@pytest.mark.parametrize("bad_size", [0, -128, 64, 512, 1.5, True, "128", None])
def test_init_invalid_key_size(bad_size):
    """Test invalid key sizes raise ValueError."""
    with pytest.raises(ValueError):
        AESCipher(bad_size, "ECB")


@pytest.mark.parametrize("bad_mode", ["CTR", "GCM", "ecb", "cbc", "", "AES", None])
def test_init_invalid_mode(bad_mode):
    """Test invalid modes raise ValueError."""
    with pytest.raises(ValueError):
        AESCipher(128, bad_mode)


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key_size,expected_len", [(128, 16), (192, 24), (256, 32)]
)
def test_generate_key_length_and_type(key_size, expected_len):
    """Test generate_key returns bytes of the correct length."""
    key = AESCipher(key_size, "CBC").generate_key()
    assert isinstance(key, bytes)
    assert len(key) == expected_len


def test_generate_key_non_deterministic():
    """Lightweight sanity check: two generated keys differ (not proof of
    cryptographic randomness quality; the CSPRNG source is os.urandom)."""
    cipher = AESCipher(256, "CBC")
    assert cipher.generate_key() != cipher.generate_key()


# ---------------------------------------------------------------------------
# IV generation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key_size", [128, 192, 256])
def test_generate_iv_cbc_length_and_type(key_size):
    """Test CBC generate_iv returns 16 random bytes."""
    iv = AESCipher(key_size, "CBC").generate_iv()
    assert isinstance(iv, bytes)
    assert len(iv) == 16


@pytest.mark.parametrize("key_size", [128, 192, 256])
def test_generate_iv_ecb_raises(key_size):
    """Test generate_iv raises ValueError for ECB mode."""
    with pytest.raises(ValueError):
        AESCipher(key_size, "ECB").generate_iv()


def test_generate_iv_non_deterministic():
    """Lightweight sanity check: two CBC IVs differ."""
    cipher = AESCipher(256, "CBC")
    assert cipher.generate_iv() != cipher.generate_iv()


# ---------------------------------------------------------------------------
# Round trips (ECB and CBC) across key sizes and plaintext shapes
# ---------------------------------------------------------------------------

PLAINTEXTS = {
    "empty": b"",
    "short_5": b"Hello",
    "fifteen": b"A" * 15,
    "exact_block": b"B" * 16,
    "seventeen": b"C" * 17,
    "multi_block": b"D" * 33,
    "binary": bytes(range(256)) * 2,
}


@pytest.mark.parametrize("key_size", [128, 192, 256])
@pytest.mark.parametrize("label", sorted(PLAINTEXTS))
def test_ecb_round_trip(key_size, label):
    """Test ECB encrypt/decrypt round trip restores the exact plaintext."""
    cipher = AESCipher(key_size, "ECB")
    key = cipher.generate_key()
    plaintext = PLAINTEXTS[label]
    ciphertext = cipher.encrypt(plaintext, key)
    assert len(ciphertext) % 16 == 0
    assert cipher.decrypt(ciphertext, key) == plaintext


@pytest.mark.parametrize("key_size", [128, 192, 256])
@pytest.mark.parametrize("label", sorted(PLAINTEXTS))
def test_cbc_round_trip(key_size, label):
    """Test CBC encrypt/decrypt round trip restores the exact plaintext."""
    cipher = AESCipher(key_size, "CBC")
    key = cipher.generate_key()
    iv = cipher.generate_iv()
    plaintext = PLAINTEXTS[label]
    ciphertext = cipher.encrypt(plaintext, key, iv)
    assert len(ciphertext) % 16 == 0
    assert cipher.decrypt(ciphertext, key, iv) == plaintext


def test_empty_plaintext_cbc_returns_empty():
    """Test empty plaintext round trips to b'' in CBC."""
    cipher = AESCipher(256, "CBC")
    key = cipher.generate_key()
    iv = cipher.generate_iv()
    ciphertext = cipher.encrypt(b"", key, iv)
    assert len(ciphertext) == 16
    assert cipher.decrypt(ciphertext, key, iv) == b""


# ---------------------------------------------------------------------------
# Validation: keys
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key_size,bad_len", [(128, 15), (128, 17), (192, 23),
                                              (192, 25), (256, 31), (256, 33)])
def test_invalid_key_length(key_size, bad_len):
    """Test keys of the wrong length raise ValueError."""
    cipher = AESCipher(key_size, "CBC")
    iv = cipher.generate_iv()
    bad_key = b"A" * bad_len
    with pytest.raises(ValueError):
        cipher.encrypt(b"data", bad_key, iv)
    with pytest.raises(ValueError):
        cipher.decrypt(b"A" * 16, bad_key, iv)


@pytest.mark.parametrize("bad_key", ["a" * 16, 12345, None, [1] * 16])
def test_invalid_key_type(bad_key):
    """Test non-bytes keys raise ValueError."""
    cipher = AESCipher(128, "CBC")
    iv = cipher.generate_iv()
    with pytest.raises(ValueError):
        cipher.encrypt(b"data", bad_key, iv)
    with pytest.raises(ValueError):
        cipher.decrypt(b"A" * 16, bad_key, iv)


def test_bytearray_key_accepted():
    """Test bytearray keys are accepted."""
    cipher = AESCipher(128, "ECB")
    key = bytearray(cipher.generate_key())
    ct = cipher.encrypt(b"Hello World!", key)
    assert cipher.decrypt(ct, key) == b"Hello World!"


# ---------------------------------------------------------------------------
# Validation: plaintext / ciphertext
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_data", ["string", 12345, None, [1, 2, 3]])
def test_invalid_plaintext_type(bad_data):
    """Test non-bytes plaintext raises ValueError."""
    cipher = AESCipher(128, "ECB")
    key = cipher.generate_key()
    with pytest.raises(ValueError):
        cipher.encrypt(bad_data, key)


@pytest.mark.parametrize("bad_data", ["string", 12345, None, [1, 2, 3]])
def test_invalid_ciphertext_type(bad_data):
    """Test non-bytes ciphertext raises ValueError."""
    cipher = AESCipher(128, "ECB")
    key = cipher.generate_key()
    with pytest.raises(ValueError):
        cipher.decrypt(bad_data, key)


@pytest.mark.parametrize("bad_len", [0, 1, 15, 17, 32, 33])
def test_non_block_aligned_ciphertext(bad_len):
    """Test ciphertext that is not a multiple of 16 raises ValueError."""
    cipher = AESCipher(128, "ECB")
    key = cipher.generate_key()
    with pytest.raises(ValueError):
        cipher.decrypt(b"A" * bad_len, key)


# ---------------------------------------------------------------------------
# Validation: IV
# ---------------------------------------------------------------------------


def test_cbc_missing_iv_raises():
    """Test CBC encryption/decryption without IV raises ValueError."""
    cipher = AESCipher(256, "CBC")
    key = cipher.generate_key()
    with pytest.raises(ValueError):
        cipher.encrypt(b"data", key)
    with pytest.raises(ValueError):
        cipher.decrypt(b"A" * 16, key)


@pytest.mark.parametrize("bad_len", [0, 8, 15, 17, 32])
def test_cbc_invalid_iv_length(bad_len):
    """Test CBC IVs of the wrong length raise ValueError."""
    cipher = AESCipher(256, "CBC")
    key = cipher.generate_key()
    bad_iv = b"B" * bad_len
    with pytest.raises(ValueError):
        cipher.encrypt(b"data", key, bad_iv)
    with pytest.raises(ValueError):
        cipher.decrypt(b"A" * 16, key, bad_iv)


@pytest.mark.parametrize("bad_iv", ["a" * 16, 12345, None, [1] * 16])
def test_cbc_invalid_iv_type(bad_iv):
    """Test CBC non-bytes IVs raise ValueError."""
    cipher = AESCipher(128, "CBC")
    key = cipher.generate_key()
    with pytest.raises(ValueError):
        cipher.encrypt(b"data", key, bad_iv)


def test_ecb_with_iv_raises():
    """Test supplying an IV to ECB mode raises ValueError."""
    cipher = AESCipher(256, "ECB")
    key = cipher.generate_key()
    iv = b"Z" * 16
    with pytest.raises(ValueError):
        cipher.encrypt(b"data", key, iv)
    with pytest.raises(ValueError):
        cipher.decrypt(b"A" * 16, key, iv)


def test_cbc_bytearray_iv_accepted():
    """Test bytearray IV is accepted for CBC."""
    cipher = AESCipher(128, "CBC")
    key = cipher.generate_key()
    iv = bytearray(cipher.generate_iv())
    ct = cipher.encrypt(b"Hello World!", key, iv)
    assert cipher.decrypt(ct, key, iv) == b"Hello World!"


def test_cbc_encrypt_does_not_auto_generate_iv():
    """Test CBC encryption does not silently generate an IV."""
    cipher = AESCipher(128, "CBC")
    key = cipher.generate_key()
    with pytest.raises(ValueError):
        cipher.encrypt(b"data", key)  # iv=None must error, not auto-generate


# ---------------------------------------------------------------------------
# Padding failure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["ECB", "CBC"])
def test_corrupted_ciphertext_raises_value_error_not_invalid_tag(mode):
    """Test corrupted ciphertext raises ValueError (never InvalidTag)."""
    from cryptography.exceptions import InvalidTag

    cipher = AESCipher(256, mode)
    key = cipher.generate_key()
    iv = None if mode == "ECB" else cipher.generate_iv()
    ct = bytearray(cipher.encrypt(b"Secret message here!", key, iv))
    # Corrupt a byte in the final (padding) block so the decrypted padding is
    # invalid for both ECB (independent blocks) and CBC (chained blocks).
    ct[-1] ^= 0xFF
    with pytest.raises(ValueError):
        cipher.decrypt(bytes(ct), key, iv)
    # ECB/CBC must never raise InvalidTag.
    try:
        cipher.decrypt(bytes(ct), key, iv)
    except ValueError:
        pass
    except InvalidTag as exc:  # pragma: no cover - guards the contract
        pytest.fail(f"InvalidTag must not be raised for {mode}: {exc}")


# ---------------------------------------------------------------------------
# Wrong key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["ECB", "CBC"])
@pytest.mark.parametrize("key_size", [128, 256])
def test_wrong_key_never_returns_original_plaintext(mode, key_size):
    """Test decrypting with a different valid key.

    A wrong key may raise ValueError (invalid padding) or return bytes; if it
    returns bytes, those bytes must not equal the original plaintext.
    """
    cipher = AESCipher(key_size, mode)
    key1 = cipher.generate_key()
    key2 = cipher.generate_key()
    while key2 == key1:  # ensure a different key for this test
        key2 = cipher.generate_key()
    iv = None if mode == "ECB" else cipher.generate_iv()
    plaintext = b"A" * 16
    ct = cipher.encrypt(plaintext, key1, iv)
    try:
        result = cipher.decrypt(ct, key2, iv)
    except ValueError:
        pass  # invalid padding from wrong key is acceptable
    else:
        assert result != plaintext


# ---------------------------------------------------------------------------
# Determinism / diffusion (lightweight sanity checks)
# ---------------------------------------------------------------------------


def test_ecb_deterministic():
    """Test ECB produces identical ciphertext for the same key/plaintext."""
    cipher = AESCipher(256, "ECB")
    key = cipher.generate_key()
    pt = b"A" * 32
    assert cipher.encrypt(pt, key) == cipher.encrypt(pt, key)


def test_cbc_iv_mixing():
    """Test CBC produces different ciphertext when the IV differs."""
    cipher = AESCipher(256, "CBC")
    key = cipher.generate_key()
    pt = b"A" * 32
    iv1 = cipher.generate_iv()
    iv2 = cipher.generate_iv()
    ct1 = cipher.encrypt(pt, key, iv1)
    ct2 = cipher.encrypt(pt, key, iv2)
    assert ct1 != ct2
    # Both decrypt back to the same plaintext with their own IVs.
    assert cipher.decrypt(ct1, key, iv1) == pt
    assert cipher.decrypt(ct2, key, iv2) == pt


def test_one_bit_diffusion_sanity_check():
    """Lightweight diffusion check: flipping one plaintext bit changes the
    ciphertext by at least one byte.

    This is a correctness sanity check only, not a substitute for the project's
    later dedicated avalanche-effect security analysis (Analysis layer).
    """
    cipher = AESCipher(256, "ECB")
    key = cipher.generate_key()
    plaintext = bytearray(b"A" * 16)
    ciphertext = cipher.encrypt(bytes(plaintext), key)
    plaintext[0] ^= 0x01  # flip exactly one bit in the first byte
    modified_ciphertext = cipher.encrypt(bytes(plaintext), key)
    assert ciphertext != modified_ciphertext
    assert len(ciphertext) == len(modified_ciphertext)


# ---------------------------------------------------------------------------
# Known-answer vectors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,key_hex,pt_hex,ct_hex", FIPS197_ECB_VECTORS
)
def test_fips197_ecb_known_answer_vector(label, key_hex, pt_hex, ct_hex):
    """Test the ECB first block against the FIPS 197 Appendix C vector.

    Our engine pads a 16-byte input to a 2-block payload (plaintext +
    16 bytes of 0x10); ECB encrypts each block independently, so the first
    ciphertext block must equal the NIST single-block ciphertext.
    """
    key_size = int(label.split("-")[1])
    cipher = AESCipher(key_size, "ECB")
    ciphertext = cipher.encrypt(_h(pt_hex), _h(key_hex))
    assert ciphertext[:16] == _h(ct_hex)
    # The padded engine also decrypts its own output back to the plaintext.
    assert cipher.decrypt(ciphertext, _h(key_hex)) == _h(pt_hex)


def test_sp800_38a_cbc_known_answer_vector():
    """Test the CBC first block against the NIST SP 800-38A F.2.1 vector.

    Block 1 = E_K(P1 XOR IV); our engine pads a 16-byte input to 2 blocks, so
    the first ciphertext block must equal the NIST expected block.
    """
    key_hex, iv_hex, pt_hex, ct_hex = SP800_38A_CBC_AES128
    cipher = AESCipher(128, "CBC")
    ciphertext = cipher.encrypt(_h(pt_hex), _h(key_hex), _h(iv_hex))
    assert ciphertext[:16] == _h(ct_hex)
    assert cipher.decrypt(ciphertext, _h(key_hex), _h(iv_hex)) == _h(pt_hex)
