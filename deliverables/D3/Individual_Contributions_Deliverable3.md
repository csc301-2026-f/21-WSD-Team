# YOUR PRODUCT/TEAM NAME - Individual Contributions (D3)

> For each team member: name, role, and specific contributions. Be precise about what you did, not how much you wrote.

**[Name]**, [Role]
> [Specific contributions: features built, PRs reviewed, infrastructure set up, etc.]

**[Danny Tran]**, [Frontend Development]
Following D2, the biggest limitation of our frontend was that, although the core pages and visualizations existed, the experience was still a skeleton of a prototype. Data integration wasn't yet seamless, the styling wasn't yet consistent, and the JavaScript needed better organization to make the application easier to maintain and test. Through reflection, integration testing, and feedback from working with the backend, I improved on the fact that the frontend needs to provide a reliable and cohesive user experience.

For D3, I connected the frontend to the Windows backend, allowing storage metrics and process information to be retrieved and displayed dynamically without relying on mock data. I also significantly overhauled the CSS, giving WSD a consistent visual identity and a much cleaner, more readable interface. On the accessibility side, I achieved a 100/100 Lighthouse accessibility score, introducing semantic HTML, proper landmarks, labelled controls, keyboard-focus indicators, and improved colour contrast. Additionally, I abstracted the JavaScript into more maintainable modules and implemented unit tests, all of which pass.

From the user's perspective, WSD has gone from a collection of prototype pages into a functional dashboard that presents live system information in a clear, consistent and much more accessible way. The biggest challenge was bringing the frontend and backend together while maintaining reliability. These improvements give us a much stronger foundation for D4, where we can focus on expanding functionality rather than rebuilding the fundamentals.
[Danny's PR Link] (https://github.com/csc301-2026-f/21-WSD-Team/pull/46)

**[Jesslyn Perdana]**, [Algorithm II Design]
> [Specific contributions]
For D3, I upgraded the recommendation system to be able to take SSD caching as its second mode, and made it compatible with Algorithm 2 while maintaining compatibility with John's Algorithm 1, though it is currently not yet integrated into the CORE. I also refactored its greedy selection algorithm, and made it more personalized and distinguished compared to John's by making it prioritize compact, high-read-frequency files to optimize cache performance and to avoid it from acting like a 'hungry wolf' that swallowed massive files. With all 7 main files of Algorithm 2 implemented, I could add unit tests for the greedy selection algorithm and the SSD caching policy to ensure the features are working as intended, and created standard D3 mock input/output fixtures under the module's test directory. With the main unit tests and JSON fixtures implemented, in the team's GitHub Actions workflow, I configured the CI pipeline to automatically execute all the algorithm's unit tests and contract validations across Ubuntu and Windows with Python 3.10 and 3.12 on every push and pull request, ensuring zero regressions and successful tests before merging into main. Alongside the completion of the algorithm's 7 main files, these improvements could set up the foundation for the integration of Algorithm 2 into the CORE and focusing on expanding on other features or functionalities that could be of great use for Algorithm 2 in D4. 
[Jesslyn's PR Link] (https://github.com/csc301-2026-f/21-WSD-Team/pull/43)

**[Name]**, [Role]
> [Specific contributions]

**[Name]**, [Role]
> [Specific contributions]
