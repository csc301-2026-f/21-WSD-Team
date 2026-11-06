# YOUR PRODUCT/TEAM NAME - Individual Contributions (D3)

> For each team member: name, role, and specific contributions. Be precise about what you did, not how much you wrote.

**[Name]**, [Role]
> [Specific contributions: features built, PRs reviewed, infrastructure set up, etc.]

**[Danny Tran]**, [Frontend Development]
Following D2, the biggest limitation of our frontend was that, although the core pages and visualizations existed, the experience was still a skeleton of a prototype. Data integration wasn't yet seamless, the styling wasn't yet consistent, and the JavaScript needed better organization to make the application easier to maintain and test. Through reflection, integration testing, and feedback from working with the backend, I improved on the fact that the frontend needs to provide a reliable and cohesive user experience.

For D3, I connected the frontend to the Windows backend, allowing storage metrics and process information to be retrieved and displayed dynamically without relying on mock data. I also significantly overhauled the CSS, giving WSD a consistent visual identity and a much cleaner, more readable interface. On the accessibility side, I achieved a 100/100 Lighthouse accessibility score, introducing semantic HTML, proper landmarks, labelled controls, keyboard-focus indicators, and improved colour contrast. Additionally, I abstracted the JavaScript into more maintainable modules and implemented unit tests, all of which pass.

From the user's perspective, WSD has gone from a collection of prototype pages into a functional dashboard that presents live system information in a clear, consistent and much more accessible way. The biggest challenge was bringing the frontend and backend together while maintaining reliability. These improvements give us a much stronger foundation for D4, where we can focus on expanding functionality rather than rebuilding the fundamentals.
[Danny's PR Link] (https://github.com/csc301-2026-f/21-WSD-Team/pull/46)

**[Sahil Pathak]**, [Database]
One of the biggest limitations after D2 was a lack of CI testing and additional saftey features for our databases, this let errors like AttributeError from the database passing onto core causin unpredicatable behavior, potential crashes and wrong predictions. So I focused on improving our testing coverage and making our databse more fault tolerant.
Implemented comprehensive unit and contract tests for the database repository, covering cold-start queries, device/process metrics ingestion, UTC timestamp formatting, dynamic time-bucketing, and recommendation upserts. Diagnosed and resolved a CI pipeline failure where missing flask in the test runner environment prevented HTTP and DB integration test suites from loading. Hardened the SQLiteHistoryRepository against interface mismatches by adding safe no-op handling for file activity and preventing stale state during recommendation collisions. Reviewed backend PRs for Core adapter integration.

**[Jesslyn Perdana]**, [Algorithm II Design]
> [Specific contributions]
For D3, I upgraded the recommendation system to be able to take SSD caching as its second mode, and made it compatible with Algorithm 2 while maintaining compatibility with John's Algorithm 1, though it is currently not yet integrated into the CORE. I also refactored its greedy selection algorithm, and made it more personalized and distinguished compared to John's by making it prioritize compact, high-read-frequency files to optimize cache performance and to avoid it from acting like a 'hungry wolf' that swallowed massive files. With all 7 main files of Algorithm 2 implemented, I could add unit tests for the greedy selection algorithm and the SSD caching policy to ensure the features are working as intended, and created standard D3 mock input/output fixtures under the module's test directory. With the main unit tests and JSON fixtures implemented, in the team's GitHub Actions workflow, I configured the CI pipeline to automatically execute all the algorithm's unit tests and contract validations across Ubuntu and Windows with Python 3.10 and 3.12 on every push and pull request, ensuring zero regressions and successful tests before merging into main. Alongside the completion of the algorithm's 7 main files, these improvements could set up the foundation for the integration of Algorithm 2 into the CORE and focusing on expanding on other features or functionalities that could be of great use for Algorithm 2 in D4. 
[Jesslyn's PR Link] (https://github.com/csc301-2026-f/21-WSD-Team/pull/43)

**[Shengrong Wang]**, [CORE]
During D2, I completed most of the basic CORE implementation based on our API Contract.
Therefore, my main responsibilities in D3 were improving the existing implementation, fixing API compatibility issues, and ensuring CORE could work with the latest updates from other team members.

In PR #38, I enabled Windows Real Mode support in CORE and updated the Agent adapters and normalization functions to match the latest Windows and Linux Backend APIs.
This included converting Windows device and file IDs into the string format required by the API Contract, updating the FileActivity interface to use sampling windows, and fixing Linux sampling duration data types.
I also connected FileActivity data to ALGO-01 through the CORE recommendation function, updated the capability settings, and fixed compatibility issues in the Linux Adapter.
In addition, I added unit tests for Windows and Linux normalization and included them in the CI workflow.

I also contributed to the Windows Backend by implementing a helper function that combines FileActivity records with the same file path, summing their read/write operations and byte counts.
This change was submitted through PR #42 and later PR #45. Besides writing code, I reviewed Enrique's Windows Backend PR #39 and identified differences between its data types and the API Contract.
[PR Link] (https://github.com/csc301-2026-f/21-WSD-Team/pull/38) (https://github.com/csc301-2026-f/21-WSD-Team/pull/42) (https://github.com/csc301-2026-f/21-WSD-Team/pull/45)
[Code Review] (https://github.com/csc301-2026-f/21-WSD-Team/pull/39)

**[John Deng]**, [Team Lead, ALGO-01 Development & Integration]
My role in D3 was mainly leading the team in coordination and doing cross-component integration. I created multiple tables to let group members sign up for their midterm dates, trying to set adaptive deadlines for everyone, continuously tracking people's progress, reviewing pull requests whenever anyone requested it, and fixing bugs between the Windows Agent, CORE, and recommendation algorithms.

As for my algorithm part (ALGO-01), I implemented a Knapsack-based file selection strategy with dynamic programming, state pruning, and a Greedy fallback when computational limits are exceeded. I preserved the existing API, refactored the selection logic, and added meaningful unit tests and benchmarks to see if pruning really works well.

I also worked on D3 integration, just like in D2. I fixed Windows ETW file path attribution, delayed event recovery, file activity aggregation, and process identity tracking. I also corrected recommendation evaluation timing, temporarily treated NVMe as SSD, and introduced regression tests for Windows data collection and process history.

Besides, I actively reviewed teammates' pull requests, including CORE integration (PR #38), Windows Agent and File I/O monitoring (PR #39), ALGO-02 compatibility (PR #40), ALGO-02 tests and implementation (PR #43), and frontend improvements (PR #46). I pointed out bugs and API inconsistencies, gave possible solutions (in Discord channels or direct messages), and approved PRs after bugs fixed.

[John's PR Links] [#37](https://github.com/csc301-2026-f/21-WSD-Team/pull/37), [#47](https://github.com/csc301-2026-f/21-WSD-Team/pull/47)

[John's Code Reviews] [#38](https://github.com/csc301-2026-f/21-WSD-Team/pull/38), [#39](https://github.com/csc301-2026-f/21-WSD-Team/pull/39), [#40](https://github.com/csc301-2026-f/21-WSD-Team/pull/40), [#43](https://github.com/csc301-2026-f/21-WSD-Team/pull/43), [#46](https://github.com/csc301-2026-f/21-WSD-Team/pull/46), [#44](https://github.com/csc301-2026-f/21-WSD-Team/pull/44), [#52](https://github.com/csc301-2026-f/21-WSD-Team/pull/52)
