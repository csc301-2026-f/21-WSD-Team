# YOUR PRODUCT/TEAM NAME

> Aim for 1000-2000 words. Be concise and analytical. We care about reasoning, impact, and integration quality, not length.

## 1. What Needed to Improve

Identify the most important gap or limitation after D2 and how you identified it.

## 2. What You Did

Describe what was implemented, key architectural or design changes, and integration challenges.

Juan: 
- End to End test [PR#41]: Starts the whole app in demo mode and checks every endpoint's response format, that recommendations follow the contract and point at real devices and that data survives the database and an app restart.

- HTTP contract tests [PR#41]: The US-02 history endpoint returns the agreed format an empty list when there is no history, `400` for invalid input without reaching the database and clean `404`/`500` errors. 

- US-02 integration tests: History saved through CORE comes back unchanged from the real database, unknown values stay `null` instead of `0` and a restarted app is kept separtae. 

- CI/CD pipeline (PR#41): Every PR now runs all tests on Windows and Linux and a build verification that packages the release installs it and smoke tests it in demo mode. When changes merge to `main` and all cheacks pass the package is published automatically as a GitHub Release
- 
## 3. Before vs. After

Show concrete improvements: workflow clarity, speed, error reduction, reliability, etc.

## 4. Reflection

What worked well, what was harder than expected, and how this affects your path to D4.
