# YOUR PRODUCT/TEAM NAME

> Aim for 1000-2000 words. Be concise and analytical. We care about reasoning, impact, and integration quality, not length.

## 1. What Needed to Improve

Identify the most important gap or limitation after D2 and how you identified it.

## 2. What You Did

Describe what was implemented, key architectural or design changes, and integration challenges.

## 3. Before vs. After

The most noticeable improvement from D2 to D3 was the transition from a prototype-style interface toward a more cohesive application that could display real system information. Previously, the frontend relied more heavily on demonstration data and had a less consistent visual presentation. While the dashboard established the foundation for our intended features, it did not yet provide the same level of integration or usability expected from a functional storage-management tool.

After D3, the frontend was connected to the Windows backend, allowing it to retrieve and display backend-provided system information. This made the dashboard more meaningful because users could interact with information originating from their own system rather than relying solely on static examples. The CSS overhaul also created a more consistent appearance across pages, improving readability and making the application's different sections feel like parts of the same product.

Maintainability improved as well. By separating JavaScript responsibilities into modules, the frontend became easier to navigate and extend. This provides a stronger foundation for future features and reduces the difficulty of making changes as the application grows. Additionally, all frontend unit tests passed, providing confidence that the implemented changes did not introduce known regressions in the tested functionality.

Accessibility saw a particularly concrete improvement. Following the changes made during D3, the pages tested achieved a Lighthouse accessibility score of 100. This reflects progress in making the interface more accessible through improved semantic structure and other accessibility-focused adjustments.

Overall, the application moved beyond simply demonstrating what Wise Storage Director could look like. It became a more integrated, consistent, maintainable, and accessible interface. 

## 4. Reflection

What worked well, what was harder than expected, and how this affects your path to D4.
