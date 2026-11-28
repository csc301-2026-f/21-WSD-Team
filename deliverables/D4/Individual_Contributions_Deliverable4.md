# WSD — Individual Contributions (D4)

## John Deng — Team Lead, ALGO-01 Development and Integration

Developed adaptive workload prediction and spatial locality scoring for ALGO-01. Conducted experiments, improved the algorithm, added regression tests, and updated documentation. Coordinated team progress and cross-component integration, identified compatibility issues, and reviewed teammates' PRs.

**Pull Requests:** [#63](https://github.com/csc301-2026-f/21-WSD-Team/pull/63), [#73](https://github.com/csc301-2026-f/21-WSD-Team/pull/73)

**Approved PRs:** [#61](https://github.com/csc301-2026-f/21-WSD-Team/pull/61), [#66](https://github.com/csc301-2026-f/21-WSD-Team/pull/66), [#67](https://github.com/csc301-2026-f/21-WSD-Team/pull/67), [#68](https://github.com/csc301-2026-f/21-WSD-Team/pull/68), [#71](https://github.com/csc301-2026-f/21-WSD-Team/pull/71), [#72](https://github.com/csc301-2026-f/21-WSD-Team/pull/72), [#74](https://github.com/csc301-2026-f/21-WSD-Team/pull/74)

**Additional Code Review:** [#62](https://github.com/csc301-2026-f/21-WSD-Team/pull/62)

## Mohan Sun — Linux Backend

Implemented mergerfs file migration, improved file activity monitoring, added partition mount information, strengthened input validation, and updated Linux documentation.

**Pull Requests:** [#61](https://github.com/csc301-2026-f/21-WSD-Team/pull/61), [#74](https://github.com/csc301-2026-f/21-WSD-Team/pull/74)

**Approved PRs:** [#62](https://github.com/csc301-2026-f/21-WSD-Team/pull/62), [#64](https://github.com/csc301-2026-f/21-WSD-Team/pull/64), [#72](https://github.com/csc301-2026-f/21-WSD-Team/pull/72), [#75](https://github.com/csc301-2026-f/21-WSD-Team/pull/75), [#76](https://github.com/csc301-2026-f/21-WSD-Team/pull/76)

## Enrique Alvarez Habegger — Windows Backend

Developed Windows file migration functionality and updated project documentation.

**Pull Requests:** [#69](https://github.com/csc301-2026-f/21-WSD-Team/pull/69), [#79](https://github.com/csc301-2026-f/21-WSD-Team/pull/79)

## Shengrong Wang — CORE and HTTP API

Integrated Linux file activity monitoring, file subscriptions, historical file activity, recommendation workflows, and file migration APIs. Improved capability reporting and mergerfs device identification.

**Pull Requests:** [#62](https://github.com/csc301-2026-f/21-WSD-Team/pull/62), [#70](https://github.com/csc301-2026-f/21-WSD-Team/pull/70), [#71](https://github.com/csc301-2026-f/21-WSD-Team/pull/71), [#72](https://github.com/csc301-2026-f/21-WSD-Team/pull/72)

**Approved PRs:** [#63](https://github.com/csc301-2026-f/21-WSD-Team/pull/63)

**Additional Code Review:** [#74](https://github.com/csc301-2026-f/21-WSD-Team/pull/74)

## Sahil Pathak — Database

Implemented historical file activity storage and queries, persistent file subscriptions, and file migration records.

**Pull Requests:** [#64](https://github.com/csc301-2026-f/21-WSD-Team/pull/64)

## Jesslyn Perdana — ALGO-02 Development

Developed a logistic regression-based prediction model for SSD caching recommendations and updated the corresponding algorithm and tests.

**Pull Requests:** [#65](https://github.com/csc301-2026-f/21-WSD-Team/pull/65)

## Danny Tran — Frontend Development

Implemented new frontend pages, file I/O monitoring, storage mode selection, improved recommendation displays, and user-approved file migration with progress tracking. Added frontend tests.

Following D3, I focused on connecting more of the frontend to the backend's current API and making the remaining workflows clearer to use. I updated the File I/O Monitoring page to show live activity and recent history, while preserving the mock-data preview. The page also received layout improvements for its charts and activity table, clearer summary values, and better empty and error states. I implemented temporary client-side history that collects observations over time, allowing users to view recent activity even without a dedicated historical file-activity endpoint. This required accounting for the structure of the backend's measurement windows so that throughput and operation values were interpreted correctly rather than incorrectly subtracting consecutive observations. I also ensured that mock and live data remain separate, preventing preview data from being mistaken for actual system activity. I fixed the historical activity test to use the same reference time as the cached observations, preventing old test data from expiring during the test.

On the Recommendations page, I made file names easier to recognize by showing the name from the activity path instead of only a file ID. I also added a confirmed file-move workflow: eligible recommendations show a Move File button, the dialog displays the source and destination, and confirming sends the recommendation ID to the existing API. The frontend then polls the returned action ID and displays whether the move is running, completed, or failed. A separate demo preview lets users see the interaction without sending a request or moving a file. I added tests for the move-action controls and API request, and audited the integrations against the current branch. Particular attention was given to ensuring that the frontend uses the existing API contracts rather than introducing new endpoints or assuming that an accepted request means a file has already been moved. The workflow also distinguishes between user confirmation, execution progress, and the final operation result, helping prevent misleading success notifications.

These updates made the frontend more useful for monitoring file activity and reviewing recommendations, while keeping preview behavior distinct from real system operations. They also improved the connection between the different parts of the application by making better use of the backend's existing capabilities and handling situations where data or operations are unavailable. The work involved coordinating several layers of the system, including frontend components, API requests, response handling, and backend action-status reporting. The main challenge was aligning frontend behavior with APIs that changed as backend work was merged. Overall, D3 involved not only adding functionality, but also improving integration reliability, testing, and the clarity of how users interact with storage monitoring and file-management features.

**Pull Requests:** [#68](https://github.com/csc301-2026-f/21-WSD-Team/pull/68), [#75](https://github.com/csc301-2026-f/21-WSD-Team/pull/75), [#80](https://github.com/csc301-2026-f/21-WSD-Team/pull/80)

**Approved PRs:** [#70](https://github.com/csc301-2026-f/21-WSD-Team/pull/70)

## Juan Sebastian Alexander — QA, Testing and CI/CD

Expanded automated test coverage, resolved CI failures, implemented automated builds and deployment for development and production environments, and prepared testing documentation.

**Pull Requests:** [#66](https://github.com/csc301-2026-f/21-WSD-Team/pull/66), [#67](https://github.com/csc301-2026-f/21-WSD-Team/pull/67), [#76](https://github.com/csc301-2026-f/21-WSD-Team/pull/76), [#81](https://github.com/csc301-2026-f/21-WSD-Team/pull/81)

**Additional Code Review:** [#74](https://github.com/csc301-2026-f/21-WSD-Team/pull/74)