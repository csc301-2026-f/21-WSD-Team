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

**[Name]**, [Role]
> [Specific contributions]

**[Name]**, [Role]
> [Specific contributions]
