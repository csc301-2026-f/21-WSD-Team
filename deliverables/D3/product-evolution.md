# YOUR PRODUCT/TEAM NAME

> Aim for 1000-2000 words. Be concise and analytical. We care about reasoning, impact, and integration quality, not length.

## 1. What Needed to Improve

Identify the most important gap or limitation after D2 and how you identified it.

After D2, integration revealed two core issues: missing automated test suites in CI for the database repository, and broken integration test runs. The test runner failed on newly merged HTTP/integration tests because flask was omitted from the CI installation step. Furthermore, while D2 established the database schema, the repository lacked end-to-end unit tests verifying downsampling edge cases, recommendation updates, and graceful handling of unsupported OS features.

## 2. What You Did

Describe what was implemented, key architectural or design changes, and integration challenges.

Fixed the CI pipeline by adding the missing flask dependency to unblock test loading across the entire backend suite. Authored automated unit tests verifying the contract against SQLite. Validated UTC timestamp adherence (YYYY-MM-DDTHH:MM:SSZ), aggregation logic across bucket_seconds, and ON CONFLICT updates for recommendation approvals. Also added a safe no-op for ingest_file_activity() to prevent runtime errors during Core ingestion calls.

## 3. Before vs. After

Before, CI was failing to load backend integration tests due to the missing environment dependency, after, all unit and contract tests execute cleanly in automated checks. Before, database behavior relied on ad-hoc verification, after, regression tests run on every pull request to ensure schema and query contract compliance. Ingestion mismatches that previously caused AttributeError failures in Core now resolve silently and safely.

The most noticeable improvement from D2 to D3 was the transition from a prototype-style interface toward a more cohesive application that could display real system information. Previously, the frontend relied more heavily on demonstration data and had a less consistent visual presentation. While the dashboard established the foundation for our intended features, it did not yet provide the same level of integration or usability expected from a functional storage-management tool.

After D3, the frontend was connected to the Windows backend, allowing it to retrieve and display backend-provided system information. This made the dashboard more meaningful because users could interact with information originating from their own system rather than relying solely on static examples. The CSS overhaul also created a more consistent appearance across pages, improving readability and making the application's different sections feel like parts of the same product.

Maintainability improved as well. By separating JavaScript responsibilities into modules, the frontend became easier to navigate and extend. This provides a stronger foundation for future features and reduces the difficulty of making changes as the application grows. Additionally, all frontend unit tests passed, providing confidence that the implemented changes did not introduce known regressions in the tested functionality.

Accessibility saw a particularly concrete improvement. Following the changes made during D3, the pages tested achieved a Lighthouse accessibility score of 100. This reflects progress in making the interface more accessible through improved semantic structure and other accessibility-focused adjustments.

Overall, the application moved beyond simply demonstrating what Wise Storage Director could look like. It became a more integrated, consistent, maintainable, and accessible interface. 

## 4. Reflection

What worked well, what was harder than expected, and how this affects your path to D4.

Contract-first design made writing deterministic unit tests straightforward once interfaces were locked down. However, diagnosing pipeline failures highlighted how brittle CI environments can be when new web dependencies are introduced across branches. For D4, maintaining automated contract testing on every PR will be essential as the algorithms and frontend integrate directly with live telemetry.
