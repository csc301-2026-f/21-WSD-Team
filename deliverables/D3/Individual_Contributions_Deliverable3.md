# YOUR PRODUCT/TEAM NAME - Individual Contributions (D3)

> For each team member: name, role, and specific contributions. Be precise about what you did, not how much you wrote.

**[Name]**, [Role]
> [Specific contributions: features built, PRs reviewed, infrastructure set up, etc.]

**[Danny Tran]**, [Frontend Development]
Following D2, the biggest limitation of our frontend was that, although the core pages and visualizations existed, the experience was still a skeleton of a prototype. Data integration wasn't yet seamless, the styling wasn't yet consistent, and the JavaScript needed better organization to make the application easier to maintain and test. Through reflection, integration testing, and feedback from working with the backend, I improved on the fact that the frontend needs to provide a reliable and cohesive user experience.

For D3, I connected the frontend to the Windows backend, allowing storage metrics and process information to be retrieved and displayed dynamically without relying on mock data. I also significantly overhauled the CSS, giving WSD a consistent visual identity and a much cleaner, more readable interface. On the accessibility side, I achieved a 100/100 Lighthouse accessibility score, introducing semantic HTML, proper landmarks, labelled controls, keyboard-focus indicators, and improved colour contrast. Additionally, I abstracted the JavaScript into more maintainable modules and implemented unit tests, all of which pass.

From the user's perspective, WSD has gone from a collection of prototype pages into a functional dashboard that presents live system information in a clear, consistent and much more accessible way. The biggest challenge was bringing the frontend and backend together while maintaining reliability. These improvements give us a much stronger foundation for D4, where we can focus on expanding functionality rather than rebuilding the fundamentals.
[Danny's PR Link] (https://github.com/csc301-2026-f/21-WSD-Team/pull/46)

**[Enrique Alvarez Habegger]**, [Windows Backend Development]
Following D2, my main role was expanding upon the codebase I had already developed in order to accurately process IO events, while mainly focusing on getting File Metrics and Process Metrics successfully implemented, as well as integrating libraries necessary to complement the data the Windows Backend was already providing, such as specific process and file information that do not appear in IO events.

Since file-specific IO events contain a file path without the drive letter, additional code had to be implemented in order to accurately give an absolute path. This was done in part by creating an inner map of file identifiers to disk location with help from Microsoft's documentation on event fields and their usage, and filling the map with information acquired from disk-specific IO events. This disk location then had to be mapped to an accurate drive letter, thus requiring polling of the system's relevant storage information. Which is now cached at startup in order to retrieve it with little overhead.

With integration from the other parts, WSD can now display near real-time IO metrics on Windows for disks, processes, and files. The metrics are consistent with other related metrics, and contain the information asked of the Windows Backend.

I also validated John's implementation of NT volume mapping (PR #47), a feature I could not properly test myself from my machine, as it requires multiple logical disks. Being familiar with the codebase, I verified its implementation and soundness.

[Enrique's PR Link] [#39](https://github.com/csc301-2026-f/21-WSD-Team/pull/39)

[Enrique's Review] [#47](https://github.com/csc301-2026-f/21-WSD-Team/pull/47)


**[Name]**, [Role]
> [Specific contributions]

**[Name]**, [Role]
> [Specific contributions]

**[John Deng]**, [Team Lead, ALGO-01 Development & Integration]
My role in D3 was mainly leading the team in coordination and doing cross-component integration. I created multiple tables to let group members sign up for their midterm dates, trying to set adaptive deadlines for everyone, continuously tracking people's progress, reviewing pull requests whenever anyone requested it, and fixing bugs between the Windows Agent, CORE, and recommendation algorithms.

As for my algorithm part (ALGO-01), I implemented a Knapsack-based file selection strategy with dynamic programming, state pruning, and a Greedy fallback when computational limits are exceeded. I preserved the existing API, refactored the selection logic, and added meaningful unit tests and benchmarks to see if pruning really works well.

I also worked on D3 integration, just like in D2. I fixed Windows ETW file path attribution, delayed event recovery, file activity aggregation, and process identity tracking. I also corrected recommendation evaluation timing, temporarily treated NVMe as SSD, and introduced regression tests for Windows data collection and process history.

Besides, I actively reviewed teammates' pull requests, including CORE integration (PR #38), Windows Agent and File I/O monitoring (PR #39), ALGO-02 compatibility (PR #40), ALGO-02 tests and implementation (PR #43), and frontend improvements (PR #46). I pointed out bugs and API inconsistencies, gave possible solutions (in Discord channels or direct messages), and approved PRs after bugs fixed.

[John's PR Links] [#37](https://github.com/csc301-2026-f/21-WSD-Team/pull/37), [#47](https://github.com/csc301-2026-f/21-WSD-Team/pull/47)

[John's Code Reviews] [#38](https://github.com/csc301-2026-f/21-WSD-Team/pull/38), [#39](https://github.com/csc301-2026-f/21-WSD-Team/pull/39), [#40](https://github.com/csc301-2026-f/21-WSD-Team/pull/40), [#43](https://github.com/csc301-2026-f/21-WSD-Team/pull/43), [#46](https://github.com/csc301-2026-f/21-WSD-Team/pull/46), [#44](https://github.com/csc301-2026-f/21-WSD-Team/pull/44), [#52](https://github.com/csc301-2026-f/21-WSD-Team/pull/52)