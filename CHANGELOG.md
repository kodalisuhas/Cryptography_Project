# Changelog
Sprint 1: AES Core + Padding 2026-09-08
- ✅ Padding Module (src/utils/padding.py)
  - ✅ `pad()` method
  - ✅ `unpad()` method
  - ✅ `is_padded()` method
  - ✅ `get_padding_length()` method
  - ✅ Unit tests (tests/test_padding.py)

- ✅ AES Module (src/core/aes_cipher.py)
  - ✅ `__init__()` method
  - ✅ `generate_key()` method
  - ✅ `generate_iv()` method
  - ✅ `encrypt()` method
  - ✅ `decrypt()` method
  - ✅ Unit tests (tests/test_aes.py)


## [Unreleased] - 2026-09-08

### Added

- Pure-Python PKCS#7 padding utility module (`src/utils/padding.py`) supporting block sizes 1–255.
- Complete unit test suite (`tests/test_padding.py`) with 30 tests covering boundary, alignment, and parameter validation cases.
- Comprehensive Task 1.1 documentation suite under `docs/` (research, plan, implementation report, code review, and verification).

## v0.1 Foundation

### Added

- Complete project folder structure
- Project documentation
- Architecture documentation
- Methodology documentation
- API interface specification
- AI engineering framework
- Git workflow
- Development environment setup
