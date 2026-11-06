# WSD - wise storage device

> Aim for 1000-2000 words. Be concise and analytical. We care about reasoning, impact, and integration quality, not length.

## 1. What Needed to Improve

**ALGO-01 and Windows Integration:**
After D2, one limitation of ALGO-01 was that it mainly relied on a Greedy strategy to select files based on their access frequency. Although this was simple and efficient, it did not always make the best use of limited storage capacity. We wanted to improve the selection process without making the algorithm too computationally expensive.

Another important limitation was the integration of real file I/O monitoring on Windows. In D2, our recommendation system still relied on mock file activity, and the Windows Agent was not fully integrated with CORE. During D3 integration and code reviews, we found several issues with ETW event attribution. File paths were sometimes missing, and using nearby DiskIO events to identify a file's physical device could produce incorrect results, especially on systems with multiple disks. These problems affected the reliability of the data passed to our recommendation algorithms. But thankfully we fixed that in the end.

During D2, we mainly developed our components based on the API Contract. However, some APIs and methods were not implemented or made available until shortly before the demo, which left limited time for integration and testing.

In D3, John introduced a development schedule with deadlines for different tasks. However, it was still difficult to strictly follow this schedule because many of us were learning unfamiliar technologies, and some tasks turned out to be more complicated than expected. As new problems were discovered during development, some API designs and implementations needed to be changed.

Overall, this showed that maintaining API Contract can be challenging, especially with limited development time and unfamiliar technologies. For future deliverables, we hope to improve coordination between different components and make the integration more efficient, while maintaining enough flexibility to handle unexpected technical challenges.

After D2, integration revealed two core issues: missing automated test suites in CI for the database repository, and broken integration test runs. The test runner failed on newly merged HTTP/integration tests because flask was omitted from the CI installation step. Furthermore, while D2 established the database schema, the repository lacked end-to-end unit tests verifying downsampling edge cases, recommendation updates, and graceful handling of unsupported OS features.

## 2. What You Did

Backend - Linux:

Several improvements were made to the Linux backend after D2, focusing on error handling, testing, and new functionality.

First, we improved error handling by returning specific error codes instead of None when an operation fails. 
This allows Core to identify failures and handle them appropriately.

Second, we added test scripts to verify backend functionality. 
Since the backend interacts directly with operating system interfaces, 
some behaviours are environment-dependent and cannot be reliably tested through conventional CI pipelines. 
These scripts allow developers to validate functionality locally before integration.

Finally, we implemented a new File I/O tracking feature. 
This uses a kernel probe to monitor read and write operations on subscribed files. 
A hash table is maintained and updated whenever a monitored file is accessed. 
The Linux backend API then retrieves and processes the collected data before reporting it to Core. 
This separates low-level kernel monitoring from higher-level application logic.

Juan: 
- End to End test [PR#41]: Starts the whole app in demo mode and checks every endpoint's response format, that recommendations follow the contract and point at real devices and that data survives the database and an app restart.

- HTTP contract tests [PR#41]: The US-02 history endpoint returns the agreed format an empty list when there is no history, `400` for invalid input without reaching the database and clean `404`/`500` errors. 

- US-02 integration tests: History saved through CORE comes back unchanged from the real database, unknown values stay `null` instead of `0` and a restarted app is kept separtae. 

- CI/CD pipeline (PR#41): Every PR now runs all tests on Windows and Linux and a build verification that packages the release installs it and smoke tests it in demo mode. When changes merge to `main` and all cheacks pass the package is published automatically as a GitHub Release
- 

CORE:

Most of the basic CORE and HTTP API work was already completed during D2, so my D3 work focused on improving compatibility with the updated backend implementations.

In PR #38, I enabled Windows Real Mode in CORE and updated the Windows and Linux Agent adapters and normalization functions to follow the latest APIs. For example, the Windows Backend used integer device IDs, while our API Contract required strings, so I added the necessary conversions. When the Windows FileActivity interface changed from start/end timestamps to a sampling window, I updated the adapter and connected FileActivity data to the CORE recommendation function, where it is passed to ALGO-01 with a 60-second window. I also updated the capability settings, fixed the Linux Adapter's unfinished FileActivity method to return an empty list instead of None, and added normalization unit tests to the CI workflow.

Besides CORE, I implemented a Windows helper that combines FileActivity records by path (PR #42 and #45). I also reviewed Enrique's PR #39 and pointed out timestamp and operation-count type mismatches with the API Contract. The main challenge was keeping CORE compatible while other components continued changing, which required frequent reviews and adjustments.


ALGO-01 and Windows Integration:

For ALGO-01, we introduced a Knapsack-based selection strategy using dynamic programming and state pruning. Instead of selecting files only through Greedy decisions, the new strategy considers different combinations of files under a limited storage budget. Since DP can become expensive when the number of candidates grows, we also added computational limits and a fallback to the original Greedy strategy. This allowed us to improve the selection process while keeping the algorithm practical for larger workloads. We also added unit tests and benchmarks to verify its correctness and performance.

For Windows integration, we worked on fixing the communication between the Windows Agent, CORE, and the recommendation system. One of the main changes was improving how ETW events are mapped to file paths and physical devices. Instead of relying on nearby DiskIO events, the updated implementation resolves NT volume paths directly and temporarily keeps unresolved FileIO events until their file information becomes available. We also improved file activity aggregation to avoid mixing events from different files, even when Windows reuses the same file identifiers.

Additionally, we fixed process identity tracking to distinguish processes that reuse the same PID, corrected the timing of recommendation evaluation, and added NVMe support to the storage capacity calculation. Regression tests were added to cover these cases. Together, these changes allowed the Windows backend to provide real file activity to CORE and generate recommendations based on actual workloads rather than only mock data.

Jesslyn: I successfully implemented the SSD Caching Policy, the recommendation system now accepted SSD caching as its second mode, though it is still not integrated into the CORE, and my greedy selection algorithm now prioritized compact, high-read-frequency files. I also added unit tests to ensure the features of the policy and the algorithm are functioning as intended along with JSON text features. After that, I configured Algorithm 2's CI pipeline to GitHub Actions workflow, so it can automatically execute the algorithm's unit tests and contract validations across Ubuntu nd Windows with Python 3.10 and 3.12 on every commits and pull requests, ensuring there are no issues before merging into main. Challenges I encountered included unit test failures commonly caused by misnamed parameters, constraints, functions, etc, that are resolved by using the terminal to figure out the causes, and a conflict when adding Algorithm 2's CI to the GitHub workflow that is resolved by raising the issue to my teammates, and accepting incoming changes.

Fixed the CI pipeline by adding the missing flask dependency to unblock test loading across the entire backend suite. Authored automated unit tests verifying the contract against SQLite. Validated UTC timestamp adherence (YYYY-MM-DDTHH:MM:SSZ), aggregation logic across bucket_seconds, and ON CONFLICT updates for recommendation approvals. Also added a safe no-op for ingest_file_activity() to prevent runtime errors during Core ingestion calls.

## 3. Before vs. After

Before, CI was failing to load backend integration tests due to the missing environment dependency, after, all unit and contract tests execute cleanly in automated checks. Before, database behavior relied on ad-hoc verification, after, regression tests run on every pull request to ensure schema and query contract compliance. Ingestion mismatches that previously caused AttributeError failures in Core now resolve silently and safely.

The most noticeable improvement from D2 to D3 was the transition from a prototype-style interface toward a more cohesive application that could display real system information. Previously, the frontend relied more heavily on demonstration data and had a less consistent visual presentation. While the dashboard established the foundation for our intended features, it did not yet provide the same level of integration or usability expected from a functional storage-management tool.

After D3, the frontend was connected to the Windows backend, allowing it to retrieve and display backend-provided system information. This made the dashboard more meaningful because users could interact with information originating from their own system rather than relying solely on static examples. The CSS overhaul also created a more consistent appearance across pages, improving readability and making the application's different sections feel like parts of the same product.

Maintainability improved as well. By separating JavaScript responsibilities into modules, the frontend became easier to navigate and extend. This provides a stronger foundation for future features and reduces the difficulty of making changes as the application grows. Additionally, all frontend unit tests passed, providing confidence that the implemented changes did not introduce known regressions in the tested functionality.

Accessibility saw a particularly concrete improvement. Following the changes made during D3, the pages tested achieved a Lighthouse accessibility score of 100. This reflects progress in making the interface more accessible through improved semantic structure and other accessibility-focused adjustments.

Overall, the application moved beyond simply demonstrating what Wise Storage Director could look like. It became a more integrated, consistent, maintainable, and accessible interface. 

CORE↓

Before D3, CORE supported only Linux Real Mode, and Windows File Activity had not yet been integrated into the recommended workflow.
Following PR #38, CORE supports Windows Real Mode, with updates to adapters and normalization functions to ensure compliance with API contract requirements. 
Furthermore, Windows File Activity has been integrated into ALGO-01, and normalization tests have been added to the CI pipeline.

## 4. Reflection

Database: 

What worked well, what was harder than expected, and how this affects your path to D4.
Contract-first design made writing deterministic unit tests straightforward once interfaces were locked down. However, diagnosing pipeline failures highlighted how brittle CI environments can be when new web dependencies are introduced across branches. For D4, maintaining automated contract testing on every PR will be essential as the algorithms and frontend integrate directly with live telemetry.

Linux backend:

One of the biggest challenges was interacting directly with the Linux kernel. 
This was significantly harder than expected, 
especially because it required switching from Python to C and learning unfamiliar kernel interfaces, data structures, and debugging techniques. 
Working with kernel probes also required a deeper understanding of how information is transferred between kernel space and user space.

At the same time, Core has been essential to the success of the project. 
By providing a common interface between different backend components and the application, 
Core allows team members to develop their features independently without needing to understand every implementation detail. 
This separation of responsibilities was key to bringing the different parts of the project together.


Moving toward D4, we will focus on testing and cooperation with the CORE team and ensuring smooth integration with Core.
