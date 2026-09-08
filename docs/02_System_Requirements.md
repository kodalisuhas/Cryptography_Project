# System Requirements: Performance and Security Analysis of AES Encryption

## System Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│            - CLI Interactive Menu & Terminal UI              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     Business Logic Layer                     │
│    - AES Engine (128, 192, 256-bit / ECB, CBC)               │
│    - RSA Engine & Blowfish Engine                            │
│    - Classical Ciphers (Caesar, Vigenère)                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        Analysis Layer                        │
│    - Benchmarking Engine (Execution Time, Memory, Throughput)│
│    - Security Evaluator (ECB Penguin, Avalanche Effect)      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        Utility Layer                         │
│    - Key & IV Generators (CSPRNG)                            │
│    - Padding Utilities (PKCS7) & Data Type Converters        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      Persistence Layer                       │
│    - File I/O Operations                                     │
│    - CSV Metrics Export & Matplotlib Plot Generation         │
└──────────────────────────────────────────────────────────────┘
```

The application follows a layered modular architecture comprising five primary layers: the **Presentation Layer** handles user interactions via a command-line interface; the **Business Logic Layer** implements the cryptographic operations (AES, RSA, Blowfish, and classical ciphers); the **Analysis Layer** coordinates performance metrics measurement, benchmarking runs, and security demonstration routines; the **Utility Layer** provides cryptographically secure randomness, padding, and conversion helpers; and the **Persistence Layer** manages file system I/O, data logging in CSV format, and graph plotting export. This structured layout ensures strict separation of concerns, scalability, and ease of unit testing across all modules.

---

## Assumptions and Constraints

### Assumptions
- **Python Runtime:** Python 3.10 or higher (64-bit) is pre-installed on the host operating system.
- **Network Access:** An active Internet connection is available during initial environment setup and dependency installation.
- **Version Control:** All team members possess a GitHub account and have Git installed and authenticated locally.
- **Hardware Resources:** The development and execution host has at least 4 GB RAM and 2 GB free disk space available.

### Constraints
- **Interface Limitations:** CLI-based application only; no graphical user interface (GUI) or web interface is provided in this release.
- **Database Dependency:** No relational or NoSQL database is utilized; all outputs are persisted as local text, CSV, and image files.
- **Host-Dependent Benchmarks:** Performance and throughput measurements directly depend on the underlying host machine's hardware architecture, CPU clock speed, OS process scheduling, and ambient workload.
- **Memory Footprint:** In-memory file processing limits single-run operations on constrained systems without chunking mechanisms.

---

## 1. Introduction

This document outlines the hardware, software, and system requirements necessary to build, test, and deploy the Cryptographic Analysis System. All team members must ensure their development environment meets these specifications.

---

## 2. Hardware Requirements

### Minimum Specifications (For Development)

| Component | Minimum Requirement | Recommended |
| :--- | :--- | :--- |
| **Processor (CPU)** | Intel Core i3 / AMD Ryzen 3 (2.0 GHz+) | Intel Core i5+ / AMD Ryzen 5+ |
| **RAM** | 4 GB | 8 GB+ |
| **Storage** | 1 GB free space | 5 GB+ free space |
| **Display** | 1024 x 768 resolution | 1920 x 1080+ |
| **Network** | Internet connection (for installation) | High-speed internet |

### Minimum Specifications (For Running the Application)

| Component | Minimum Requirement |
| :--- | :--- |
| **Processor** | Any processor (1.0 GHz+) |
| **RAM** | 512 MB |
| **Storage** | 100 MB free space |

### Notes on Hardware:
- **Performance Benchmarking:** For accurate performance measurements, ensure your system is not running heavy background applications.
- **Large Files:** Testing with large files (100 MB+) may require additional RAM.
- **Graph Generation:** `matplotlib` graph generation works fine on minimum hardware.

---

## 3. Software Requirements

### Operating System

| OS | Version | Compatibility |
| :--- | :--- | :---: |
| **Windows** | Windows 10 64-bit / Windows 11 64-bit | ✅ Fully Supported |
| **macOS** | macOS 11 (Big Sur) or higher | ✅ Fully Supported |
| **Linux** | Ubuntu 20.04+, Debian 11+, Fedora 36+ | ✅ Fully Supported |

### Programming Language

| Component | Version | Notes |
| :--- | :--- | :--- |
| **Python** | Python 3.10 or higher | Python 3.11+ recommended |
| **PIP** | Latest version | For dependency management |

### Why Python 3.10+?
- Type hints (`|` union syntax) introduced in 3.10
- Performance improvements in 3.11
- Better error messages in 3.11+

---

## 4. Python Dependencies

### Core Dependencies (`requirements.txt`)

| Library | Minimum Version | Purpose |
| :--- | :--- | :--- |
| **cryptography** | 42.0.0+ | AES, RSA, Blowfish implementation |
| **matplotlib** | 3.7.0+ | Graph generation |
| **pandas** | 2.0.0+ | Data manipulation and CSV export |
| **numpy** | 1.24.0+ | Mathematical operations |
| **pytest** | 7.0.0+ | Unit testing |
| **tabulate** | 0.9.0+ | Terminal table formatting |
| **pyyaml** | 6.0.0+ | Configuration file parsing |

### Optional Dependencies

| Library | Version | Purpose |
| :--- | :--- | :--- |
| **seaborn** | 0.12.0+ | Prettier graphs (optional) |
| **black** | Latest | Code formatting (optional) |
| **pylint** | Latest | Code quality checks (optional) |
| **mypy** | Latest | Type checking (optional) |

---

## 5. Installation Steps

### Step 1: Verify Python Installation
```bash
python --version
# OR
python3 --version
```
*Expected Output:* `Python 3.10.x` or higher

### Step 2: Verify PIP Installation
```bash
pip --version
# OR
pip3 --version
```

### Step 3: Create Virtual Environment (Recommended)

**Windows:**
```cmd
python -m venv venv
venv\Scriptsctivate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Verify Installation
```bash
python -c "import cryptography; import matplotlib; import pandas; print('All dependencies installed successfully!')"
```

---

## 6. Development Tools (Recommended)

### Version Control

| Tool | Version | Purpose |
| :--- | :--- | :--- |
| **Git** | 2.30+ | Version control |
| **GitHub** | (Online) | Repository hosting |
| **GitHub Desktop** | Latest | Git GUI (optional) |

### Code Editor / IDE

| Tool | Purpose | Recommendation |
| :--- | :--- | :---: |
| **VS Code** | Code editing | ✅ Recommended |
| **PyCharm** | Code editing | ✅ Alternative |
| **Antigravity** | AI-powered development | ✅ For this project |
| **Gemini CLI** | AI assistance | ✅ For this project |

### VS Code Extensions (Recommended)

| Extension | Purpose |
| :--- | :--- |
| **Python** | Python language support |
| **Pylance** | Type checking and IntelliSense |
| **GitLens** | Git history and blame |
| **Markdown All in One** | Markdown editing |
| **Python Docstring Generator** | Auto-generate docstrings |
| **Better Comments** | Organized comments |
| **GitHub Pull Requests** | PR management |

---

## 7. Project Structure Verification

After installation, verify the project structure:
```bash
tree /F
```
*Expected Output:* Complete folder tree as defined in the architecture document.

---

## 8. Environment Variables (Optional)

Create `.env` file in root directory (for future use):
```env
# Environment Variables (Optional)
PROJECT_NAME="Cryptography_AES_Analysis"
PYTHONPATH="src"
LOG_LEVEL="INFO"
BENCHMARK_ITERATIONS=5
```
> **Note:** These are optional and not required for basic functionality.

---

## 9. Testing Requirements

### Hardware for Testing

| Test Type | Minimum Requirement |
| :--- | :--- |
| **Unit Tests** | Any system (1-2 seconds per test) |
| **Integration Tests** | Any system (5-10 seconds per test) |
| **Performance Tests** | Stable system (5-10 minutes total) |
| **Large File Tests** | 4+ GB RAM recommended |

### Test Data Requirements

| Data Type | Size | Purpose |
| :--- | :--- | :--- |
| **Small Text** | 1 KB | Unit tests |
| **Medium Text** | 1 MB | Performance tests |
| **Large Text** | 10 MB | Benchmark tests |
| **Image** | 1-5 MB | ECB Penguin demo |
| **Random Data** | Configurable | Stress testing |

---

## 10. Network Requirements

| Requirement | Details |
| :--- | :--- |
| **Installation** | Internet required for downloading dependencies |
| **Operation** | No internet required (offline operation) |
| **GitHub** | Internet required for commits/pushes |
| **Updates** | Internet required for updating dependencies |

---

## 11. System Compatibility Matrix

| Feature | Windows | macOS | Linux |
| :--- | :---: | :---: | :---: |
| **AES Encryption** | ✅ | ✅ | ✅ |
| **RSA Encryption** | ✅ | ✅ | ✅ |
| **Blowfish** | ✅ | ✅ | ✅ |
| **Classical Ciphers** | ✅ | ✅ | ✅ |
| **Graph Generation** | ✅ | ✅ | ✅ |
| **CSV Export** | ✅ | ✅ | ✅ |
| **Performance Timing** | ✅ | ✅ | ✅ |
| **File Operations** | ✅ | ✅ | ✅ |
| **CLI Interface** | ✅ | ✅ | ✅ |

---

## 12. Troubleshooting

### Common Issues

| Issue | Solution |
| :--- | :--- |
| **python not recognized** | Install Python and add to PATH |
| **pip not found** | Reinstall Python with pip included |
| **Dependency conflicts** | Use `pip install --upgrade` or create fresh venv |
| **matplotlib GUI error** | Use `matplotlib.use('Agg')` for headless (server) |
| **Permission errors** | Run terminal as administrator (Windows) or use `sudo` (Linux) |
| **Git not initialized** | Run `git init` in project root |

### Performance Testing Issues

| Issue | Solution |
| :--- | :--- |
| **Inconsistent timings** | Run multiple iterations and average |
| **Background processes** | Close other applications during benchmarks |
| **CPU throttling** | Ensure proper cooling and power settings |

---

## 13. Security Considerations

| Aspect | Recommendation |
| :--- | :--- |
| **Keys** | Generated keys should NOT be committed to Git |
| **Encrypted Data** | Test data should be stored in `data/` folder (ignored by Git) |
| **Sensitive Info** | Never hardcode keys or passwords in code |
| **Input Validation** | Validate all user inputs to prevent injection |
| **Error Handling** | Don't expose sensitive information in error messages |

---

## 14. Documentation Requirements

| Document | Status | Location |
| :--- | :---: | :--- |
| **Project Proposal** | Completed | `docs/01_Project_Proposal.md` |
| **System Requirements** | In Progress | `docs/02_System_Requirements.md` |
| **Architecture Design** | Pending | `docs/03_Architecture_Design.md` |
| **Methodology** | Pending | `docs/04_Methodology.md` |
| **API Specification** | Pending | `docs/05_API_Interface_Spec.md` |

---

## 15. Team Member Setup Checklist

Each team member must complete:
1. Install Python 3.10+
2. Install Git
3. Clone the repository
4. Create virtual environment
5. Install dependencies
6. Verify folder structure
7. Configure Git user (name + email)
8. Create feature branch
9. Test the environment

---

## 16. Verification Commands

Run these commands to verify everything is working:

```bash
# Verify Python version
python --version

# Verify dependencies
pip list

# Verify Git
git --version

# Verify project structure
tree /F

# Verify Git status
git status

# Verify Git remote
git remote -v
```

---

## 17. Support and Help

| Resource | Where to Find |
| :--- | :--- |
| **Documentation** | `docs/` folder |
| **Team Communication** | WhatsApp / Discord / GitHub Discussions |
| **GitHub Issues** | For bug reports and feature requests |
| **Stack Overflow** | For general Python questions |
| **Official Docs** | https://docs.python.org/ |

---

## Document Metadata
- **Status:** Ready for Review
- **Version:** 1.0
- **Date:** January 2026
- **Next Action:** Team review and approval

---

## Recommendations & System Improvements

1. **Broaden Document Title for Multi-Algorithm Scope**
   - **Explanation:** The current title references only AES, while the system explicitly specifies support for RSA, Blowfish, and classical ciphers.
   - **Recommendation:** Rename title to:
     - *System Requirements: Cryptography Testing Lab and Performance Analysis System*, or
     - *System Requirements for the Cryptographic Analysis System*
   - **Benefit:** Accurately reflects the system requirements for all cryptographic modules.

2. **Explicitly Clarify Supported Python Runtime and Architecture**
   - **Explanation:** New releases or 32-bit builds can cause subtle wheel build errors or performance anomalies during benchmarking.
   - **Recommendation:** Explicitly specify that **64-bit Python** installation is required, and note that **Python 3.13 is not officially tested**.
   - **Benefit:** Guarantees binary wheel compatibility for cryptography and pandas libraries across all operating systems.

3. **Increase Minimum Free Storage Allocation to 2 GB**
   - **Explanation:** Virtual environment packages, benchmark dataset files, generated high-resolution PNG graphs, and local Git version history easily surpass 1 GB.
   - **Recommendation:** Update development minimum free disk space to **2 GB**.
   - **Benefit:** Prevents disk quota exhaustion during multi-iteration stress tests.

4. **Add Benchmark Hardware Variance Disclaimer**
   - **Explanation:** Benchmark timing values will vary across individual team and evaluation machines.
   - **Recommendation:** Add the following note under Hardware Requirements:
     > *Benchmark results may vary depending on CPU architecture, background processes, power-saving profiles, and operating system process scheduling.*
   - **Benefit:** Protects project validity during viva defense when demonstrating results on varying hardware.

5. **Formalize GitHub Account Requirement in Development Tools**
   - **Explanation:** Source code versioning and collaborative pull request workflows require verified GitHub accounts.
   - **Recommendation:** Add `GitHub Account` under Section 6 Development Tools for collaboration and PR management.
   - **Benefit:** Ensures all team members are properly configured for collaboration before development begins.

6. **Adjust Default Benchmark Iterations in Environment Configuration**
   - **Explanation:** Setting `BENCHMARK_ITERATIONS=5` is insufficient for statistically stable benchmarking.
   - **Recommendation:** Update the default configuration in `.env` to `BENCHMARK_ITERATIONS=100` (allowing local override for quick unit runs).
   - **Benefit:** Yields reliable, statistically sound benchmark curves while filtering out transient OS scheduling spikes.

7. **Refine Test Data Specification for Large Payload Stress Testing**
   - **Explanation:** 10 MB payload tests are insufficient to evaluate memory consumption under heavy loads.
   - **Recommendation:** Adjust the test data size matrix:
     - *Small Text:* 1 KB (Unit Tests)
     - *Medium Text:* 1 MB (Performance Tests)
     - *Large Text:* 10–100 MB (Stress Testing)
   - **Benefit:** Allows comprehensive throughput evaluation across small, medium, and heavy workloads.

8. **Mandate Cryptographically Secure Random Number Generation (CSPRNG)**
   - **Explanation:** Insecure pseudo-random number generators (such as standard `random`) compromise key and IV confidentiality.
   - **Recommendation:** Add to Security Considerations that all key and IV generation routines must strictly utilize `secrets` or `os.urandom()`.
   - **Benefit:** Guarantees cryptographic entropy compliance with standard security benchmarks.

9. **Standardize Documentation Status Identifiers**
   - **Explanation:** Informal emoji status markers (`🔄`, `⏳`, `✅`) should be standardized for academic reporting and document exports.
   - **Recommendation:** Replace markers with formalized terms: `Completed`, `In Progress`, `Pending`, and `Draft`.
   - **Benefit:** Generates clean, professional PDF and printable documentation reports.
