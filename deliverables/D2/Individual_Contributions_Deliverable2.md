# Team 21 – WSD
## Individual Contributions – Deliverable 2

### John Deng
**Role:** Team lead, API coordination, ALGO-01 development, backend integration, and release management for D2.

**Contributions:**
- Drafted and coordinated the shared D2 API contract.
- Implemented ALGO-01 file-placement recommendations, including input validation, ranking logic, unit tests, and documentation.
- Integrated Linux Agent, CORE, database, recommendation algorithm, and Flask into the application entry point.
- Added Demo Mode and supporting test fixtures.
- Developed and published the standalone Linux v1.0.0 release, including packaging and installation instructions.
- Coordinated technical discussions, reviewed PRs, and managed integration and release preparations.

**Evidence:** [PR #17](https://github.com/csc301-2026-f/21-WSD-Team/pull/17), [PR #22](https://github.com/csc301-2026-f/21-WSD-Team/pull/22), [PR #30](https://github.com/csc301-2026-f/21-WSD-Team/pull/30), [PR #34](https://github.com/csc301-2026-f/21-WSD-Team/pull/34), [Linux Release v1.0.1](https://github.com/csc301-2026-f/21-WSD-Team/releases/tag/v1.0.0).

### Shengrong Wang
**Role:** CORE development, API implementation, and backend component integration.

**Contributions:**
- Contributed to the shared API contract and data-flow design.
- Implemented CORE adapters for OS Agent, database, and recommendation algorithms.
- Developed data normalization and HTTP API interfaces for frontend communication.
- Added capabilities reporting and support for mock data in Demo Mode.
- Integrated Linux process metrics into CORE.

**Evidence:** [PR #19](https://github.com/csc301-2026-f/21-WSD-Team/pull/19), [PR #28](https://github.com/csc301-2026-f/21-WSD-Team/pull/28).

**Status:** CORE integration requires final verification.

### Mohan Sun

**Role:** Linux backend development and OS-level I/O monitoring.

**Contributions:**

- Implemented Linux storage device discovery and disk I/O collection.
- Implemented process-level I/O monitoring and interval-based metric sampling.
- Developed Linux Agent interfaces and data models for CORE integration.
- Prepared a D2 frontend walkthrough with screenshots and instructions for TA verification.

**Evidence:** [PR #27](https://github.com/csc301-2026-f/21-WSD-Team/pull/27), [D2 Frontend Walkthrough](https://github.com/csc301-2026-f/21-WSD-Team/blob/main/deliverables/D2/WSD_TA_Frontend_Walkthrough.md).

### Enrique Alvarez Habegger

**Role:** Windows backend development and ETW-based I/O monitoring.

**Contributions:**

- Developed Windows storage device and telemetry data models.
- Implemented the initial ETW event transport, decoding, and aggregation components.
- Developed WMI-based device discovery and Windows Agent interfaces.
- Added Windows-related API documentation and team meeting minutes.

**Evidence:** [PR #32](https://github.com/csc301-2026-f/21-WSD-Team/pull/32), [PR #33](https://github.com/csc301-2026-f/21-WSD-Team/pull/33).

**Status:** Initial implementation submitted; full Windows integration and verification remain incomplete.

### Sahil Pathak

**Role:** Database development and historical I/O storage.

**Contributions:**

- Designed the SQLite database schema for devices, I/O metrics, recommendations, and application settings.
- Implemented `SQLiteHistoryRepository` for data ingestion and historical queries.
- Added database fixtures and unit tests for empty results and ingestion/query round-trips.
- Documented database APIs and integration requirements.

**Evidence:** [PR #21](https://github.com/csc301-2026-f/21-WSD-Team/pull/21), [PR #25](https://github.com/csc301-2026-f/21-WSD-Team/pull/25).

### Jesslyn Perdana

**Role:** ALGO-02 SSD caching recommendation development.

**Contributions:**

- Developed the initial ALGO-02 module structure and configuration.
- Implemented input validation and file candidate selection for SSD caching.
- Developed greedy caching selection logic with SSD capacity constraints.
- Added recommendation logic intended to preserve original files while proposing SSD caching.

**Evidence:** [PR #24](https://github.com/csc301-2026-f/21-WSD-Team/pull/24).

**Status:** Core selection components submitted; the public algorithm entry point and integration remain incomplete.

### Danny Tran

**Role:** Frontend development and backend API integration.

**Contributions:**

- Developed the WSD frontend dashboard and navigation interfaces.
- Connected frontend components to backend HTTP APIs for dynamic data display.
- Implemented interfaces for real-time and historical disk/process I/O statistics.
- Added frontend support for displaying storage recommendations and associated information.

**Evidence:** [PR #31](https://github.com/csc301-2026-f/21-WSD-Team/pull/31).

### Juan Alexander

**Role:** QA, contract testing, and continuous integration.

**Contributions:**

- Created mock API response fixtures and initial QA documentation.
- Implemented GitHub Actions CI for ALGO-01 tests on Windows and Ubuntu with Python 3.10 and 3.12.
- Developed ALGO-01 contract and regression tests for output structure, device availability, capacity constraints, and safe recommendations.
- Updated QA testing requirements and documentation in the shared API contract.

**Evidence:** [PR #20](https://github.com/csc301-2026-f/21-WSD-Team/pull/20), [PR #23](https://github.com/csc301-2026-f/21-WSD-Team/pull/23), [PR #29](https://github.com/csc301-2026-f/21-WSD-Team/pull/29).
