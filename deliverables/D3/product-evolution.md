# YOUR PRODUCT/TEAM NAME

> Aim for 1000-2000 words. Be concise and analytical. We care about reasoning, impact, and integration quality, not length.

## 1. What Needed to Improve

Identify the most important gap or limitation after D2 and how you identified it.

## 2. What You Did

Describe what was implemented, key architectural or design changes, and integration challenges.

Jesslyn: I successfully implemented the SSD Caching Policy, the recommendation system now accepted SSD caching as its second mode, though it is still not integrated into the CORE, and my greedy selection algorithm now prioritized compact, high-read-frequency files. I also added unit tests to ensure the features of the policy and the algorithm are functioning as intended along with JSON text features. After that, I configured Algorithm 2's CI pipeline to GitHub Actions workflow, so it can automatically execute the algorithm's unit tests and contract validations across Ubuntu nd Windows with Python 3.10 and 3.12 on every commits and pull requests, ensuring there are no issues before merging into main. Challenges I encountered included unit test failures commonly caused by misnamed parameters, constraints, functions, etc, that are resolved by using the terminal to figure out the causes, and a conflict when adding Algorithm 2's CI to the GitHub workflow that is resolved by raising the issue to my teammates, and accepting incoming changes.

## 3. Before vs. After

The most noticeable improvement from D2 to D3 was the transition from a prototype-style interface toward a more cohesive application that could display real system information. Previously, the frontend relied more heavily on demonstration data and had a less consistent visual presentation. While the dashboard established the foundation for our intended features, it did not yet provide the same level of integration or usability expected from a functional storage-management tool.

After D3, the frontend was connected to the Windows backend, allowing it to retrieve and display backend-provided system information. This made the dashboard more meaningful because users could interact with information originating from their own system rather than relying solely on static examples. The CSS overhaul also created a more consistent appearance across pages, improving readability and making the application's different sections feel like parts of the same product.

Maintainability improved as well. By separating JavaScript responsibilities into modules, the frontend became easier to navigate and extend. This provides a stronger foundation for future features and reduces the difficulty of making changes as the application grows. Additionally, all frontend unit tests passed, providing confidence that the implemented changes did not introduce known regressions in the tested functionality.

Accessibility saw a particularly concrete improvement. Following the changes made during D3, the pages tested achieved a Lighthouse accessibility score of 100. This reflects progress in making the interface more accessible through improved semantic structure and other accessibility-focused adjustments.

Overall, the application moved beyond simply demonstrating what Wise Storage Director could look like. It became a more integrated, consistent, maintainable, and accessible interface. 

## 4. Reflection

What worked well, what was harder than expected, and how this affects your path to D4.
