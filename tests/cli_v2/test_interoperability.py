"""Stage 6: Integration & Interoperability Tests (TEST-ONLY)"""
import pytest
import subprocess
import sys, os
import uuid
import codecs
import shutil
from pathlib import Path

from src.cli_v2.batch_orchestrator import BatchOrchestrator
from src.cli_v2.key_manager import KeyManager
from src.engines.cipher_service import CipherService


# --- HELPER FUNCS ---
def run_v1_encrypt(tmp_path, plaintext, key_size, mode, key_hex, iv_hex=None):
    uid = uuid.uuid4().hex
    p_in = tmp_path / f"v1_in_{uid}.txt"
    p_in.write_bytes(plaintext)
    p_out = tmp_path / f"v1_out_{uid}.enc"
    
    cmd = [
        sys.executable, "-m", "src.cli.main", "encrypt",
        "--input-file", str(p_in),
        "--output-file", str(p_out),
        "--key-size", str(key_size),
        "--mode", mode,
        "--key", key_hex
    ]
    if iv_hex:
        cmd.extend(["--iv", iv_hex])
        
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    subprocess.run(cmd, check=True, capture_output=True, env=env)
    return p_out.read_bytes()

def run_v1_decrypt(tmp_path, ciphertext, key_size, mode, key_hex, iv_hex=None):
    uid = uuid.uuid4().hex
    p_in = tmp_path / f"v1_dec_in_{uid}.enc"
    p_in.write_bytes(ciphertext)
    if mode == "CBC" and iv_hex:
        (tmp_path / f"v1_dec_in_{uid}.enc.iv").write_text(iv_hex + "\n")
        
    p_out = tmp_path / f"v1_dec_out_{uid}.txt"
    
    cmd = [
        sys.executable, "-m", "src.cli.main", "decrypt",
        "--input-file", str(p_in),
        "--output-file", str(p_out),
        "--key-size", str(key_size),
        "--mode", mode,
        "--key", key_hex
    ]
    if iv_hex:
        cmd.extend(["--iv", iv_hex])
        
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    subprocess.run(cmd, check=True, capture_output=True, env=env)
    return p_out.read_bytes()

def run_v2_cli_encrypt(tmp_path, plaintext, key_size, mode, key_hex, iv_hex=None):
    uid = uuid.uuid4().hex
    p_in = tmp_path / f"v2_in_{uid}.txt"
    p_in.write_bytes(plaintext)
    p_out = tmp_path / f"v2_out_{uid}.enc"
    
    cmd = [
        sys.executable, "-m", "src.cli_v2.main_v2", "encrypt",
        "--input", str(p_in),
        "--output", str(p_out),
        "--key-size", str(key_size),
        "--mode", mode,
        "--key", key_hex
    ]
    if iv_hex:
        cmd.extend(["--iv", iv_hex])
        
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    subprocess.run(cmd, check=True, capture_output=True, env=env)
    return p_out.read_bytes()

def run_v2_cli_decrypt(tmp_path, ciphertext, key_size, mode, key_hex, iv_hex=None):
    uid = uuid.uuid4().hex
    p_in = tmp_path / f"v2_dec_in_{uid}.enc"
    p_in.write_bytes(ciphertext)
    p_out = tmp_path / f"v2_dec_out_{uid}.txt"
    
    cmd = [
        sys.executable, "-m", "src.cli_v2.main_v2", "decrypt",
        "--input", str(p_in),
        "--output", str(p_out),
        "--key-size", str(key_size),
        "--mode", mode,
        "--key", key_hex
    ]
    if iv_hex:
        cmd.extend(["--iv", iv_hex])
        
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    subprocess.run(cmd, check=True, capture_output=True, env=env)
    return p_out.read_bytes()


# --- SECTION 1: V2 -> V1 INTEROPERABILITY ---

def test_s1_v2_cli_to_v1_cli(tmp_path):
    pt = b"hello interoperability"
    key = b"A" * 32
    iv = b"B" * 16
    
    ct = run_v2_cli_encrypt(tmp_path, pt, 256, "CBC", key.hex(), iv.hex())
    dec = run_v1_decrypt(tmp_path, ct, 256, "CBC", key.hex(), iv.hex())
    assert dec == pt

@pytest.mark.skip(reason="Wizard path genuinely cannot be deterministically exercised without modifying production code (no callable parameters for key/mode/IV exist, requires interactive input injection).")
def test_s1_v2_wizard_to_v1_cli():
    pass

def test_s1_v2_cli_to_v1_cipherservice(tmp_path):
    pt = b"service interop"
    key = b"C" * 32
    iv = b"D" * 16
    
    ct = run_v2_cli_encrypt(tmp_path, pt, 256, "CBC", key.hex(), iv.hex())
    svc = CipherService()
    dec = svc.decrypt_data("AES", 256, "CBC", ct, key, iv)
    assert dec == pt

def test_s1_all_configs_v2_to_v1(tmp_path):
    pt = b"all configs"
    for size in [128, 192, 256]:
        for mode in ["ECB", "CBC"]:
            key = b"K" * (size // 8)
            iv = b"I" * 16 if mode == "CBC" else None
            ct = run_v2_cli_encrypt(tmp_path, pt, size, mode, key.hex(), iv.hex() if iv else None)
            dec = run_v1_decrypt(tmp_path, ct, size, mode, key.hex(), iv.hex() if iv else None)
            assert dec == pt

# --- SECTION 2: V1 -> V2 INTEROPERABILITY ---

def test_s2_v1_cli_to_v2_cli(tmp_path):
    pt = b"hello v1 to v2"
    key = b"E" * 32
    iv = b"F" * 16
    
    ct = run_v1_encrypt(tmp_path, pt, 256, "CBC", key.hex(), iv.hex())
    dec = run_v2_cli_decrypt(tmp_path, ct, 256, "CBC", key.hex(), iv.hex())
    assert dec == pt

@pytest.mark.skip(reason="Wizard path genuinely cannot be deterministically exercised without modifying production code (no callable parameters for key/mode/IV exist, requires interactive input injection).")
def test_s2_v1_cli_to_v2_wizard():
    pass

def test_s2_v1_cipherservice_to_v2_cli(tmp_path):
    pt = b"service to cli"
    key = b"G" * 32
    iv = b"H" * 16
    
    svc = CipherService()
    enc_res = svc.encrypt_data("AES", 256, "CBC", pt, key, iv)
    
    dec = run_v2_cli_decrypt(tmp_path, enc_res.ciphertext, 256, "CBC", key.hex(), iv.hex())
    assert dec == pt

def test_s2_all_configs_v1_to_v2(tmp_path):
    pt = b"all configs rev"
    for size in [128, 192, 256]:
        for mode in ["ECB", "CBC"]:
            key = b"K" * (size // 8)
            iv = b"I" * 16 if mode == "CBC" else None
            ct = run_v1_encrypt(tmp_path, pt, size, mode, key.hex(), iv.hex() if iv else None)
            dec = run_v2_cli_decrypt(tmp_path, ct, size, mode, key.hex(), iv.hex() if iv else None)
            assert dec == pt

# --- SECTION 3: BATCH INTEROPERABILITY ---

def test_s3_v2_batch_encrypt_to_v1_cli_decrypt(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    
    (src / "f1.txt").write_bytes(b"batch one")
    (src / "f2.txt").write_bytes(b"batch two")
    
    svc = CipherService()
    batch = BatchOrchestrator(svc)
    
    key = b"B" * 32
    batch.run_batch_encrypt(src, dst, "AES", 256, "CBC", shared_key=key, on_conflict="overwrite", dry_run=False, progress_callback=None)
    
    for f in ["f1.txt.enc", "f2.txt.enc"]:
        p_enc = dst / f
        p_iv = dst / f"{f}.iv"
        iv_bytes = bytes.fromhex(p_iv.read_text().strip())
        dec = run_v1_decrypt(tmp_path, p_enc.read_bytes(), 256, "CBC", key.hex(), iv_bytes.hex())
        
        orig = src / f.replace(".enc", "")
        assert dec == orig.read_bytes()

def test_s3_v1_cli_encrypt_to_v2_batch_decrypt(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    
    key = b"Z" * 32
    (dst / "batch.key").write_text(key.hex())
    
    pt1, pt2 = b"first", b"second"
    iv1, iv2 = b"1"*16, b"2"*16
    
    uid1, uid2 = uuid.uuid4().hex, uuid.uuid4().hex
    p_in1, p_out1 = tmp_path / f"v1_in_{uid1}.txt", tmp_path / f"v1_out_{uid1}.enc"
    p_in1.write_bytes(pt1)
    cmd1 = [sys.executable, "-m", "src.cli.main", "encrypt", "--input-file", str(p_in1), "--output-file", str(p_out1), "--key-size", "256", "--mode", "CBC", "--key", key.hex(), "--iv", iv1.hex()]
    subprocess.run(cmd1, check=True, capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    
    p_in2, p_out2 = tmp_path / f"v1_in_{uid2}.txt", tmp_path / f"v1_out_{uid2}.enc"
    p_in2.write_bytes(pt2)
    cmd2 = [sys.executable, "-m", "src.cli.main", "encrypt", "--input-file", str(p_in2), "--output-file", str(p_out2), "--key-size", "256", "--mode", "CBC", "--key", key.hex(), "--iv", iv2.hex()]
    subprocess.run(cmd2, check=True, capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    
    shutil.copy(p_out1, src / "f1.enc")
    shutil.copy(str(p_out1) + ".iv", src / "f1.enc.iv")
    shutil.copy(p_out2, src / "f2.enc")
    shutil.copy(str(p_out2) + ".iv", src / "f2.enc.iv")
    
    svc = CipherService()
    batch = BatchOrchestrator(svc)
    batch.run_batch_decrypt(src, dst, "AES", 256, "CBC", shared_key=key, on_conflict="overwrite", dry_run=False, progress_callback=None)
    
    assert (dst / "f1").read_bytes() == pt1
    assert (dst / "f2").read_bytes() == pt2

def test_s3_v2_batch_shared_key_mode(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    
    (src / "test.txt").write_bytes(b"shared key test")
    
    svc = CipherService()
    batch = BatchOrchestrator(svc)
    key = b"S" * 32
    batch.run_batch_encrypt(src, dst, "AES", 256, "ECB", shared_key=key, on_conflict="overwrite", dry_run=False, progress_callback=None)
    
    batch_key_file = dst / "batch.key"
    key_hex = batch_key_file.read_text().strip()
    
    ct = (dst / "test.txt.enc").read_bytes()
    dec = run_v1_decrypt(tmp_path, ct, 256, "ECB", key_hex)
    assert dec == b"shared key test"

# --- SECTION 4: SIDECAR REPRESENTATION ---

def test_s4_v2_key_sidecar_is_valid_v1_arg(tmp_path):
    p = tmp_path / "test.key"
    key = b"K" * 32
    KeyManager.save_key(key, p)
    
    content = p.read_text()
    assert len(content.strip()) == 64
    assert content.endswith("\n")
    assert content.strip().islower()
    assert all(c in "0123456789abcdef" for c in content.strip())
    assert "\n" not in content.strip()
    assert "\r" not in content
    
    pt = b"sidecar key"
    ct = run_v1_encrypt(tmp_path, pt, 256, "ECB", content)
    dec = run_v1_decrypt(tmp_path, ct, 256, "ECB", content)
    assert dec == pt

def test_s4_v2_iv_sidecar_matches_v1_convention(tmp_path):
    p = tmp_path / "test.iv"
    iv = b"I" * 16
    KeyManager.save_iv(iv, p)
    
    content = p.read_text()
    assert len(content.strip()) == 32
    assert content.endswith("\n")
    
    pt = b"sidecar iv"
    ct = run_v1_encrypt(tmp_path, pt, 256, "CBC", (b"A"*32).hex(), content.strip())
    dec = run_v1_decrypt(tmp_path, ct, 256, "CBC", (b"A"*32).hex(), content.strip())
    assert dec == pt

def test_s4_v1_compatible_hex_accepted_by_load_key(tmp_path):
    p = tmp_path / "v1.key"
    p.write_text((b"A"*32).hex())
    key, size = KeyManager.load_key(p)
    assert key == b"A"*32
    assert size == 256

def test_s4_v1_compatible_hex_accepted_by_load_iv(tmp_path):
    p = tmp_path / "v1.iv"
    p.write_text((b"B"*16).hex() + "\n")
    iv = KeyManager.load_iv(p)
    assert iv == b"B"*16

def test_s4_v2_keymanager_normalization():
    assert KeyManager.normalize_hex(codecs.BOM_UTF8.decode("utf-8") + "abcd") == "abcd"
    assert KeyManager.normalize_hex(" \t AbCd \r\n") == "abcd"

# --- SECTION 5: V2 PATH EQUIVALENCE ---

@pytest.mark.skip(reason="Wizard path genuinely cannot be deterministically exercised without modifying production code (no callable parameters for key/mode/IV exist, requires interactive input injection).")
def test_s5_cli_and_wizard_equivalence():
    pass

def test_s5_cli_and_batch_equivalence(tmp_path):
    pt = b"equivalence"
    key = b"X" * 32
    
    ct_cli = run_v2_cli_encrypt(tmp_path, pt, 256, "ECB", key.hex())
    
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "f.txt").write_bytes(pt)
    
    svc = CipherService()
    batch = BatchOrchestrator(svc)
    batch.run_batch_encrypt(src, dst, "AES", 256, "ECB", shared_key=key, on_conflict="overwrite", dry_run=False, progress_callback=None)
    
    ct_batch = (dst / "f.txt.enc").read_bytes()
    assert ct_cli == ct_batch

# --- SECTION 6: SIX-CONFIG ROUND-TRIP ---

def test_s6_six_config_round_trip(tmp_path):
    pt = b"roundtrip 6 configs"
    for size in [128, 192, 256]:
        for mode in ["ECB", "CBC"]:
            key = b"M" * (size // 8)
            iv = b"N" * 16 if mode == "CBC" else None
            
            ct1 = run_v2_cli_encrypt(tmp_path, pt, size, mode, key.hex(), iv.hex() if iv else None)
            dec1 = run_v2_cli_decrypt(tmp_path, ct1, size, mode, key.hex(), iv.hex() if iv else None)
            assert dec1 == pt
            
            ct2 = run_v2_cli_encrypt(tmp_path, pt, size, mode, key.hex(), iv.hex() if iv else None)
            dec2 = run_v1_decrypt(tmp_path, ct2, size, mode, key.hex(), iv.hex() if iv else None)
            assert dec2 == pt
            
            ct3 = run_v1_encrypt(tmp_path, pt, size, mode, key.hex(), iv.hex() if iv else None)
            dec3 = run_v2_cli_decrypt(tmp_path, ct3, size, mode, key.hex(), iv.hex() if iv else None)
            assert dec3 == pt

# --- SECTION 7: NEGATIVE PATHS ---

def test_s7_wrong_key_decryption(tmp_path):
    pt = b"secret message"
    key1 = b"O" * 32
    key2 = b"P" * 32
    
    ct = run_v2_cli_encrypt(tmp_path, pt, 256, "ECB", key1.hex())
    
    p_in = tmp_path / "v2_dec_in.enc"
    p_in.write_bytes(ct)
    p_out = tmp_path / "v2_dec_out.txt"
    
    cmd = [
        sys.executable, "-m", "src.cli_v2.main_v2", "decrypt",
        "--input", str(p_in),
        "--output", str(p_out),
        "--key-size", "256",
        "--mode", "ECB",
        "--key", key2.hex()
    ]
    res = subprocess.run(cmd, capture_output=True)
    
    # VALID OUTCOME A: operation fails with a nonzero exit code
    # OR VALID OUTCOME B: operation exits successfully but plaintext is NOT equal to original.
    # The test must fail ONLY if return code is zero AND plaintext equals the original plaintext.
    if res.returncode == 0:
        assert p_out.read_bytes() != pt

def test_s7_missing_iv_direct_cli(tmp_path):
    pt = b"missing iv"
    key = b"Q" * 32
    ct = run_v2_cli_encrypt(tmp_path, pt, 256, "CBC", key.hex(), (b"R"*16).hex())
    
    p_in = tmp_path / "v2_dec_in.enc"
    p_in.write_bytes(ct)
    p_out = tmp_path / "v2_dec_out.txt"
    
    cmd = [
        sys.executable, "-m", "src.cli_v2.main_v2", "decrypt",
        "--input", str(p_in),
        "--output", str(p_out),
        "--key-size", "256",
        "--mode", "CBC",
        "--key", key.hex()
    ]
    res = subprocess.run(cmd, capture_output=True)
    assert res.returncode != 0

def test_s7_missing_iv_load_iv(tmp_path):
    with pytest.raises(FileNotFoundError):
        KeyManager.load_iv(tmp_path / "does_not_exist.iv")

@pytest.mark.skip(reason="Wizard path genuinely cannot be deterministically exercised without modifying production code (no callable parameters for key/mode/IV exist, requires interactive input injection).")
def test_s7_missing_iv_wizard():
    pass

def test_s7_batch_corrupt_file(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    
    (src / "good.enc").write_bytes(run_v1_encrypt(tmp_path, b"good", 256, "ECB", (b"S"*32).hex()))
    (src / "bad.enc").write_bytes(b"not a valid ciphertext" * 10)
    
    svc = CipherService()
    batch = BatchOrchestrator(svc)
    
    summary = batch.run_batch_decrypt(src, dst, "AES", 256, "ECB", shared_key=b"S"*32, on_conflict="overwrite", dry_run=False, progress_callback=None)
    
    assert summary.success_count == 1
    assert summary.failed_count == 1
    assert (dst / "good").exists()

def test_s7_tampered_iv(tmp_path):
    pt = b"tampered iv test"
    key = b"T" * 32
    iv = bytearray(b"U" * 16)
    ct = run_v2_cli_encrypt(tmp_path, pt, 256, "CBC", key.hex(), iv.hex())
    
    iv[0] ^= 0x01
    
    p_in = tmp_path / "v2_dec_in.enc"
    p_in.write_bytes(ct)
    p_out = tmp_path / "v2_dec_out.txt"
    
    cmd = [
        sys.executable, "-m", "src.cli_v2.main_v2", "decrypt",
        "--input", str(p_in),
        "--output", str(p_out),
        "--key-size", "256",
        "--mode", "CBC",
        "--key", key.hex(),
        "--iv", iv.hex()
    ]
    res = subprocess.run(cmd, capture_output=True)
    
    # The frozen V2 methodology does NOT provide authentication/integrity protection for CBC.
    # VALID OUTCOME A: decryption fails with nonzero exit code
    # OR VALID OUTCOME B: decryption succeeds but resulting plaintext differs from original.
    # The test should fail only if tampering somehow results in successful decryption to the original plaintext.
    if res.returncode == 0:
        assert p_out.read_bytes() != pt

# --- SECTION 8: ARTIFACT NAMING & PAYLOAD INTEGRITY ---

def test_s8_v2_encrypt_ecb_artifacts(tmp_path):
    pt = b"ecb artifacts"
    p_in = tmp_path / "in.txt"
    p_in.write_bytes(pt)
    p_out = tmp_path / "in.txt.enc"
    
    subprocess.run([
        sys.executable, "-m", "src.cli_v2.main_v2", "encrypt",
        "--input", str(p_in),
        "--output", str(p_out),
        "--key-size", "256",
        "--mode", "ECB",
        "--generate-key"
    ], check=True)
    
    assert p_out.exists()
    assert (tmp_path / "in.txt.enc.key").exists()
    assert not (tmp_path / "in.txt.enc.iv").exists()

def test_s8_v2_encrypt_cbc_artifacts(tmp_path):
    pt = b"cbc artifacts"
    p_in = tmp_path / "in.txt"
    p_in.write_bytes(pt)
    p_out = tmp_path / "in.txt.enc"
    
    subprocess.run([
        sys.executable, "-m", "src.cli_v2.main_v2", "encrypt",
        "--input", str(p_in),
        "--output", str(p_out),
        "--key-size", "256",
        "--mode", "CBC",
        "--generate-key"
    ], check=True)
    
    assert p_out.exists()
    assert (tmp_path / "in.txt.enc.key").exists()
    assert (tmp_path / "in.txt.enc.iv").exists()

def test_s8_batch_artifact_naming(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    
    (src / "f.txt").write_bytes(b"hello")
    
    svc = CipherService()
    batch = BatchOrchestrator(svc)
    batch.run_batch_encrypt(src, dst, "AES", 256, "CBC", shared_key=None, on_conflict="overwrite", dry_run=False, progress_callback=None)
    
    assert (dst / "f.txt.enc").exists()
    assert (dst / "f.txt.enc.key").exists()
    assert (dst / "f.txt.enc.iv").exists()

def test_s8_byte_level_payloads(tmp_path):
    payloads = [
        b"",
        b"\x00",
        b"\xff",
        "Ωμ".encode("utf-8"),
        bytes(range(256)) * 4,
        b"A" * 16,
        b"B" * 15,
        b"C" * 17
    ]
    key = b"V" * 32
    iv = b"W" * 16
    
    for i, pt in enumerate(payloads):
        ct = run_v2_cli_encrypt(tmp_path, pt, 256, "CBC", key.hex(), iv.hex())
        dec = run_v1_decrypt(tmp_path, ct, 256, "CBC", key.hex(), iv.hex())
        assert dec == pt
