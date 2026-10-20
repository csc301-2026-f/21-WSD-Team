# Team 21 – WSD
## Individual Contributions – Deliverable 2

### John Deng
**Role:** Team lead, API coordination, and ALGO-01 development.

**Contributions:**
- Drafted and coordinated the shared D2 API contract.
- Implemented the ALGO-01 file-placement recommendation algorithm.
- Added input validation, recommendation logic, unit tests, and supporting documentation.
- Coordinated technical discussions and reviewed team contributions.

**Evidence:** [PR #17](https://github.com/csc301-2026-f/21-WSD-Team/pull/17), [PR #22](https://github.com/csc301-2026-f/21-WSD-Team/pull/22).

### Shengrong Wang
**Role:** CORE development and API integration.

**Contributions:**
- Contributed to the shared API contract and data-flow design.
- Developed initial CORE components for normalization and communication between OS agents, database, and algorithms.

**Evidence:** [PR #19](https://github.com/csc301-2026-f/21-WSD-Team/pull/19), `shengrong/d2-core`.

**Status:** CORE integration requires final verification.

### Mohan Sun
**Role:** Linux backend development.

**Contributions:**
- Defined initial Linux system API signatures and example return values.
- Worked on Linux device and process information collection interfaces.

**Evidence:** `feat/linux_backend`.

**Status:** Working implementation and test evidence pending verification.

### Enrique
**Role:** Windows backend development.

**Contributions:**
- Defined Windows storage device and telemetry data models.
- Developed initial ETW event aggregation logic for device and process metrics.
- Established interfaces for Windows event collection and device discovery.

**Evidence:** `enrique/d2-api-windows`.

**Status:** Live collection and integration pending verification.

### Sahil
**Role:** Database design and historical data storage.

**Contributions:**
- Developed the database API design and supporting documentation.
- Defined proposed SQLite storage behavior, data access interfaces, and test fixtures.

**Evidence:** [PR #21](https://github.com/csc301-2026-f/21-WSD-Team/pull/21).

**Status:** Database implementation pending verification.

### Jesslyn
**Role:** ALGO-02 SSD caching recommendation development.

**Contributions:**
- Created the initial ALGO-02 module structure.
- Implemented preliminary input validation and caching configuration defaults.

**Evidence:** [PR #24](https://github.com/csc301-2026-f/21-WSD-Team/pull/24).

**Status:** Recommendation algorithm implementation in progress.

### Danny
**Role:** Frontend dashboard development.

**Contributions:**
- [Add verified D2 frontend implementation, integration work, and relevant PR links.]

**Status:** D2 contribution evidence to be confirmed.

### Juan
**Role:** QA, testing, and continuous integration.

**Contributions:**
- Created mock API response fixtures and initial QA documentation.
- Implemented GitHub Actions CI for ALGO-01 unit testing on Windows and Ubuntu.

**Evidence:** [PR #20](https://github.com/csc301-2026-f/21-WSD-Team/pull/20), [PR #23](https://github.com/csc301-2026-f/21-WSD-Team/pull/23).

**Status:** Initial QA and CI contributions merged; broader integration tests remain to be completed.