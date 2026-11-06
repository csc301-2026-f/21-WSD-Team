# YOUR PRODUCT/TEAM NAME

> Aim for 1000-2000 words. Be concise and analytical. We care about reasoning, impact, and integration quality, not length.

## 1. What Needed to Improve

Identify the most important gap or limitation after D2 and how you identified it.

During D2, we mainly developed our components based on the API Contract. However, some APls and methods were not implemented or made available until shortly before the demo, which left limited time for integration and testing.

In D3, John introduced a development schedule with deadlines for different tasks. However, it was still difficult to strictly follow this schedule because many of us were learning unfamiliar knowledges, and some tasks turned out to be more complicated than expected. As new problems were discovered during development, some API designs and implementations needed to be changed.

Overall, this showed that maintaining APl Contract can be challenging, especially with limited development time and unfamiliar technologies. For future deliverables, we hope to improve coordination between different components and make the integration more efficient, while maintaining enough flexibility to handle unexpected technical challenges.

## 2. What You Did

Describe what was implemented, key architectural or design changes, and integration challenges.

Most of the basic CORE and HTTP API work was already completed during D2, so my D3 work focused on improving compatibility with the updated backend implementations.

In PR #38, I enabled Windows Real Mode in CORE and updated the Windows and Linux Agent adapters and normalization functions to follow the latest APls. For example, the Windows Backend used integer device IDs, while our API Contract required strings, so I added the necessary conversions. When the Windows FileActivity interface changed from start/end timestamps to a sampling window, I updated the adapter and connected FileActivity data to the CORE recommendation function, where it is passed to ALGO-01 with a 60-second window. I also updated the capability settings, fixed the Linux Adapter's unfinished FileActivity method to return an empty list instead of None, and added normalization unit tests to the Cl workflow.

Besides CORE, I implemented a Windows helper that combines FileActivity records by path (PR #42 and #45). I also reviewed Enrique's PR #39 and pointed out timestamp and operation-count type mismatches with the APl Contract. The main challenge was keeping CORE compatible while other components continued changing, which required frequent reviews and adjustments.

## 3. Before vs. After

The most noticeable improvement from D2 to D3 was the transition from a prototype-style interface toward a more cohesive application that could display real system information. Previously, the frontend relied more heavily on demonstration data and had a less consistent visual presentation. While the dashboard established the foundation for our intended features, it did not yet provide the same level of integration or usability expected from a functional storage-management tool.

After D3, the frontend was connected to the Windows backend, allowing it to retrieve and display backend-provided system information. This made the dashboard more meaningful because users could interact with information originating from their own system rather than relying solely on static examples. The CSS overhaul also created a more consistent appearance across pages, improving readability and making the application's different sections feel like parts of the same product.

Maintainability improved as well. By separating JavaScript responsibilities into modules, the frontend became easier to navigate and extend. This provides a stronger foundation for future features and reduces the difficulty of making changes as the application grows. Additionally, all frontend unit tests passed, providing confidence that the implemented changes did not introduce known regressions in the tested functionality.

Accessibility saw a particularly concrete improvement. Following the changes made during D3, the pages tested achieved a Lighthouse accessibility score of 100. This reflects progress in making the interface more accessible through improved semantic structure and other accessibility-focused adjustments.

Overall, the application moved beyond simply demonstrating what Wise Storage Director could look like. It became a more integrated, consistent, maintainable, and accessible interface. 

## 4. Reflection

What worked well, what was harder than expected, and how this affects your path to D4.
