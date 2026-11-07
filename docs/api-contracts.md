# WSD D2 | Our Internal API Contracts & Team Checklists

> **VERSION: `v0.8` · STATUS: `TEAM DRAFT / NOT APPROVED` · DATE: 2026-10-08**  
> **Suggested path:** `docs/api-contracts.md`  
> **Document coordinator:** **John**  
> **TEAM 21:** This is **our working API contract**. Please fill in the parts you own, review the interfaces you will use, and raise questions directly in the PR. **All signatures and data structures below are proposals, not existing implementations or final decisions.** We can revise the proposed interfaces together, but we must notify affected consumers before merging an incompatible change.

---

> [!IMPORTANT]
> **HOW TO USE THIS DRAFT:** Find the section you own, fill in the bold **TODO** items, and link supporting examples. If you consume an API, review its data and error cases before agreeing to the contract. Names identify who is responsible; hypothetical examples use generic roles.

## START HERE | What to do in this document

> [!NOTE]
> **CHECKLIST KEY:** `- [ ]` = not completed; `- [x]` = completed. Keep the bold **TODO** label when you check a box. Checking an item means you have filled it in and added evidence; approval and verification are tracked separately.
>
> **PREVIEW NOTE:** GitHub does not reliably support custom Markdown font colors, so we use headings, bold labels, and native NOTE / TIP / IMPORTANT / WARNING / CAUTION callouts. You do not need any special Markdown extension to edit the source.


> [!IMPORTANT]
> **EVERYONE:** Please work on a branch and submit a PR. Fill in the assigned answer/evidence field, add a sample payload or fixture when relevant, and change `- [ ]` to `- [x]` after completing that item. **Keep the bold TODO marker.** A completed worksheet is not the same as an accepted API contract.
>
> **GitHub limitation:** A repository `.md` preview does **not automatically check a box** when you fill in the corresponding answer. If you want clickable task tracking, copy the checklist to a **GitHub Issue description**; you can then check the boxes from the Issue page. Any change to the version-controlled contract still requires a PR.

```text
OWNER                          CONSUMER                      QA [JUAN]
+------------------+         +------------------+         +------------------+
| [ ] Fill answers | ------> | [ ] Review fields| ------> | [ ] Add tests /  |
| [ ] Add examples |         | [ ] Accept/ask   |         |     fixtures     |
| [ ] Mark DONE *  |         |     for changes  |         | [ ] Verify code  |
+------------------+         +------------------+         +------------------+
      * Illustration only. The real tasks below all start unchecked.
```

### HOW-TO 0 | Abbreviations and ID naming rules — READ FIRST

> [!IMPORTANT]
> **READ THIS BEFORE THE TABLES:** `US-05` and `US-06` are **User Story references, not API function names**. We use the IDs below so we can trace each proposed API and test to our seven original D1 requirements. **The original user stories are quoted in §00.A**, and their proposed API mappings are in §00.B.

**Reference-ID convention**

```text
US-01 .. US-07   = the seven User Stories in D1 Planning Q4, in their original order
OS-01            = OS Agent contract #01
DB-01            = Database contract #01
ALGO-01          = Algorithm contract #01
CORE-01          = Integration / orchestration contract #01
HTTP-01a         = sub-endpoint "a" in HTTP contract #01
ACTION-01        = Storage Action contract #01
QA-01            = Quality Assurance contract #01
```

| Short form | Meaning | Where it is used |
|---|---|---|
| **US** | **User Story** | `US-01`–`US-07` map directly to the numbered stories in **D1 Q4**; these are requirements, not code identifiers. |
| **OS / WIN / LINUX** | Operating System / Windows Agent / Linux Agent | OS-specific telemetry, capabilities, and execution (Enrique / Mohan). |
| **CORE** | Integration / orchestration service | Coordinates shared data and component calls (Shengrong). |
| **DB** | Database | Stores observations and provides history queries (Sahil). |
| **ALGO** | Algorithm / Decision Maker | Produces storage recommendations (John / Jesslyn). |
| **HTTP** | Hypertext Transfer Protocol | Local dashboard endpoints consumed by the frontend (Shengrong / Danny). |
| **ACTION** | Storage operation | Preview / approved execution by the OS Agents. |
| **QA** | Quality Assurance | Contract tests, integration tests, benchmark and CI work (Juan). |
| **UI** | User Interface | Frontend screens and their data requirements (Danny). |
| **API** | Application Programming Interface | Agreed function signatures and/or HTTP endpoints. |
| **PR / CI** | Pull Request / Continuous Integration | GitHub reviews and automated test checks. |
| **D1 / D2 / MVP** | Deliverable 1 / Deliverable 2 / Minimum Viable Product | Course deliverables and product scope. |
| **I/O / IOPS** | Input/Output / I/O Operations per Second | Storage workload metrics. |
| **SSD / HDD / RAID 0** | Solid-State Drive / Hard Disk Drive / Redundant Array of Independent Disks, level 0 | Storage terminology; **WSD's `raid0` mode means file-level pooling, not block striping**. |
| **JSON / UTC** | JavaScript Object Notation / Coordinated Universal Time | Shared payload and timestamp formats. |

**Two frequently confused references**

- **US-05 — Recommendations:** The GUI shows which files are recommended for moving or caching on faster storage. **A recommendation alone does not execute anything.**
- **US-06 — Auto Mode:** After the user explicitly enables automatic behavior, WSD may automatically cache or move frequently accessed files **only when supported and safe**. This is an **execution/authorization feature**, not a third storage mode.

**Rules for new IDs:** Keep existing `US-01`–`US-07` unchanged because they correspond to our submitted D1 user stories. When proposing an additional API, use the appropriate module prefix (`OS`, `DB`, `ALGO`, `CORE`, `HTTP`, `ACTION`, `QA`), give it an unused identifier, and add it to **§01 API Contract Registry**. If we later add a new user story, label it as a *proposed new story*, not a replacement for a D1 story.

---

### HOW-TO 1 | Checkbox example (hypothetical; no team member assigned)

Suppose someone is documenting a **hypothetical** metrics API. This is only an example of how to edit a checklist; it is not a claim about any team's implementation.

Before:

```md
- [ ] **TODO · EXAMPLE PRODUCER** — Document supported I/O fields.
  - **Answer / evidence:** _Write here._
```

After the example producer documents the result and opens a PR:

```md
- [x] **TODO · EXAMPLE PRODUCER** — Document supported I/O fields.
  - **Answer / evidence:** `read_iops`: optional number; source: proposed adapter. Example fixture: `tests/fixtures/sample.json`; PR #... .
```

**Important:** Please edit the checkbox manually in the Markdown source. Consumer approval and QA verification use **separate** checkboxes.

### HOW-TO 2 | Team progress checklist

Please check one of these summary items **only after** the corresponding detailed worksheet is filled in and linked to a PR. The full checklist is still below.

- [ ] **TODO · ENRIQUE** — Windows contracts: complete §3 worksheet + success/failure examples; request consumer review.
- [ ] **TODO · MOHAN** — Linux contracts: complete §3 worksheet + feasibility/unsupported examples; request consumer review.
- [ ] **TODO · SHENGRONG** — Shared schemas, integration, HTTP: complete §§2 and 6, coordinate contracts with Danny and DB/ALGO.
- [x] **TODO · SAHIL** — Database contracts: complete §4, provide a representative historical result and empty/unsupported response.
- [ ] **TODO · JOHN + JESSLYN** — Algorithm contracts: complete §5, review required inputs from OS and DB and provide one fixture per storage mode.
- [ ] **TODO · DANNY** — Frontend requirements: complete §6, review endpoint shapes against every current UI screen.
- [ ] **TODO · JUAN** — Testing / benchmarks / CI: complete §8, attach fixtures, runnable tests, and PR/CI evidence.

**Our progress / evidence links:** Juan: mock fixtures started in `tests/fixtures/` on Juan-branch (devices, device/process metrics, empty history, RAID0 recommendations). Next: validator + first runnable test, CI draft. Waiting on producers for real success/error payloads (§08.4.2).

---

## TEAM OWNERSHIP | Producer, consumer and QA

```text
  [OS] Enrique & Mohan ──────┐       [DB] Sahil
                            ├───► [ALGO] John + Jesslyn
                Shengrong ──┤                 │
                (CORE)      └───► [UI] Danny ◄┘

  [QA] Juan: test contract + examples + integration + CI + benchmarks
            └── covers EVERY arrow and module above
```


| YOUR NAME | YOU OWN / FILL IN | WHO MUST REVIEW YOUR CONTRACT | REQUIRED FIRST RESULT |
|---|---|---|---|
| **Enrique** | **WIN** Windows OS agent: metrics, capabilities, storage actions | Shengrong + John/Jesslyn + Juan | Feasibility table + sample metrics and failures |
| **Mohan** | **LINUX** Linux OS agent: metrics, capabilities, pooling/caching actions | Shengrong + John/Jesslyn + Juan | Feasibility table + sample metrics and failures |
| **Shengrong** | **CORE** normalization, local orchestration, dashboard API, action dispatch | Danny + Sahil + John/Jesslyn + Juan | Same data format on either OS + local API draft |
| **Sahil** | **DB** write metrics, query history, settings, recommendations | John/Jesslyn + Shengrong + Juan | Query signatures + representative history fixture |
| **John + Jesslyn** | **ALGO** two storage modes; define policy inputs and recommendation outputs | Shengrong + Enrique/Mohan + Danny + Juan | Required data fields + one example per mode |
| **Danny** | **UI** dashboard API requirements, UI data consumption, review of HTTP contract | Shengrong + John/Jesslyn + Juan | Endpoint/field needs for existing screens |
| **Juan** | **QA** fixtures, API-contract checks, integration tests, benchmark harness, PR/CI tests | Each API producer; John/Shengrong coordinate | Test matrix + fixture layout + runnable smoke test |

### WORKFLOW | Repeat for every API boundary

```text
       [1] PRODUCER drafts the contract
                     |
                     v
       [2] CONSUMER checks that it is usable
                     |
                     v
       [3] JUAN defines how to verify it
                     |
                     v
       [4] PRODUCER + CONSUMER confirm in PR
                     |
                     v
       [5] IMPLEMENT -> RUN TESTS -> VERIFY

Changes later?  NEW PR + notify affected consumers + update fixtures/tests.
```

**Working agreements**

- **Producer = provides a function/service and maintains its implementation + proposed contract.**
- **Consumer = calls it or depends on its output; must review fields, behavior and edge cases.**
- **QA / Juan = producer of test code and fixtures, and reviewer of testability across all module boundaries.** No production API implementation is assigned to QA.
- Use **Git branches + PRs**. Do not directly change protected `main`.
- `P0` means **confirm the interface early**, not **implement every optional feature immediately**.
- When you own a task, keep it unchecked (`- [ ]`) until you have filled in the **Answer / evidence** field. Separate review checkboxes show whether consumers and QA have accepted it.

---

## 00 | PRODUCT SCOPE — Modes, goals, policies and data sources

> [!IMPORTANT]
> **ALL TEAM MEMBERS:** The two storage modes are **file-level RAID0 pooling** and **SSD caching**. Real-time/history are data sources, not modes. User-facing optimization goals are not automatically algorithm names.


From D1, the **two core storage modes** are:

```text
                         +-----------------------+
                         | USER / DASHBOARD      |
                         | Goal: (optional UI)   |
                         | Performance / Balanced|
                         | / Lifespan             |
                         +-----------+-----------+
                                     |
                         +-----------v-----------+
                         | DECISION MAKER         |
                         | [John + Jesslyn]       |
                         +-----+-------------+---+
                               |             |
                  +------------v--+      +---v------------------+
                  | MODE A: RAID0 |      | MODE B: SSD CACHING  |
                  | FILE-LEVEL    |      | SSD as cache medium  |
                  | POOLING       |      | for existing data    |
                  +--------+------+      +---------+------------+
                           |                       |
                      Placement /               Admission /
                      migration /               eviction /
                      balancing                 consistency rules
                           |                       |
                           +-----------+-----------+
                                       |
                             RECOMMENDATIONS
                                       |
                            User approval / safe
                            action execution only
```

**Definitions to preserve:**

1. `raid0` here means **performance-oriented file-level storage pooling**, NOT block-level RAID 0 striping.
2. `ssd_caching` means SSD caching; **cache-path redirection, validity and write semantics remain to be investigated** by OS producers.
3. **Real-time** and **historical** observations are *two types of input data*, **not two storage modes**. Either mode may use both.
4. `Performance / Balanced / Lifespan` are possible **user-facing goals**, **not an agreed algorithm enum**. Algorithm owners determine the actual policy rules/weights per mode; D2 need not implement all three.
5. `auto_apply` is authorization/workflow configuration, **not another storage mode**. Start in recommendation-only mode.
6. **RAM-disk / RAM caching is NOT a committed D1 implementation.** Do not require it in D2; optional future research only.

### 00.A | D1 Q4 — Original MVP user stories (verbatim; source of truth)

> [!IMPORTANT]
> **ALL TEAM MEMBERS:** The seven statements below are copied **verbatim** from [D1 Planning, Q4](https://github.com/csc301-2026-f/21-WSD-Team/blob/main/deliverables/D1/planning.md). These are our previously submitted user stories. **Do not replace them with new illustrative user stories.** The API mappings are **proposed contracts**, not proof that the feature has been implemented or scheduled for completion in D2.

**US-01 — Real-time per-application I/O**

> As a storage enthusiast, I want to open the GUI in order to monitor the real-time I/O status of each running application.

**US-02 — Historical I/O of an individual application**

> As a storage enthusiast, I want to open the GUI and navigate to an individual application in order to monitor its historical I/O usage.

**US-03 — RAID 0 mode**

> As a college student with an old computer with slow storage, I want to enable RAID 0 mode in order to maximize storage capacity and move I/O-intensive files to the fastest disk.

**US-04 — Caching mode**

> As a college student with an old computer with slow storage, I want to enable caching mode in order to retain data integrity and copy I/O-intensive files to the caching disk.

**US-05 — File placement/caching recommendations**

> As a college student with an old computer with slow storage, I want to open the GUI in order to get recommendations on which files should be moved/cached on the fastest disk.

**US-06 — Auto mode**

> As a college student with an old computer with slow storage, I want to enable auto mode in order to automatically have frequently accessed files cached/moved to the fastest storage device on my computer.

**US-07 — Estimated time saved**

> As a college student with an old computer with slow storage, I want to open the GUI in order to see an approximation of how much time was saved by this app.

### 00.B | D1 user story → proposed API mapping and implementation gaps

| D1 ID | Required experience | Initial contract mapping | Producer(s) to clarify | Consumer(s) / QA | Status / key caveat |
|---|---|---|---|---|---|
| **US-01** | Per-process live I/O in GUI | **OS-02 → CORE-01 → HTTP-01e** | Enrique / Mohan; Shengrong | Danny; Juan | PROPOSED; per-process source/units and sampling interval must be confirmed |
| **US-02** | Historical I/O for one application | **OS-02 → DB-01 `query_process_history` → HTTP-01m** | Enrique / Mohan; Sahil; Shengrong | Danny; Juan | **GAP FIX:** explicit HTTP history endpoint; process-instance identity across restarts needs agreement |
| **US-03** | Enable file-level RAID 0 / pooling and placement | **OS-01/03, ALGO-01, ACTION-01, HTTP-01i/j/k** | Mohan / Enrique; John / Jesslyn; Shengrong | Danny; Juan | INVESTIGATE; *not* block RAID0; mounting, path routing and safe migration are not assumed implemented |
| **US-04** | Enable SSD caching and retain source integrity | **OS-01/03, ALGO-02, ACTION-01, HTTP-01i/j/k** | Mohan / Enrique; John / Jesslyn; Shengrong | Danny; Juan | INVESTIGATE; simple SSD copies alone do not constitute a functioning cache |
| **US-05** | Display file move/cache recommendations | **OS-03 + DB-01 → ALGO-01/02 → HTTP-01g** | Mohan / Enrique; Sahil; John / Jesslyn; Shengrong | Danny; Juan | PROPOSED; recommendation must not fabricate file heat or silently execute an action |
| **US-06** | Explicitly enable automatic cache/move behavior | **HTTP-01i + CORE-01 + ACTION-01** | Shengrong; Mohan / Enrique | Danny; John / Jesslyn; Juan | **GAP FIX:** opt-in, supported-action allowlist, safety checks and clear on/off state; no implicit execution |
| **US-07** | Estimated time saved shown in GUI | **QA-02 + DB-01 + HTTP-01n** | Juan (measurements); Sahil (storage); Shengrong (API) | Danny; John / Jesslyn | **GAP FIX:** return `unavailable` if no comparable baseline/after evidence; never invent a time-saved figure |

**Scope reminder:** All seven were described in D1 Q4. That does **not** mean each feature is technically feasible or must be fully implemented in D2. Feasibility, safe behavior and the D2 milestone need separate confirmation.

- [ ] **TODO · ENRIQUE + MOHAN + SHENGRONG** — Confirm whether OS-02 supports per-process real-time I/O (US-01) on each platform; include one response and unavailable-field behavior.
  - **Answer / evidence:** _Write here, or link an API sample / PR._
- [ ] **TODO · SAHIL + SHENGRONG + DANNY** — Agree on process-history API fields, stable process identity and the history UI path (US-02).
  - **Answer / evidence:** _Write here, or link an API sample / PR._
- [ ] **TODO · ENRIQUE + MOHAN + JOHN/JESSLYN** — Record what file placement and caching operations are technically feasible and safe (US-03 / US-04 / US-05).
  - **Answer / evidence:** _Write here, or link an API sample / PR._
- [ ] **TODO · SHENGRONG + DANNY + ENRIQUE + MOHAN** — Specify explicit Auto Mode authorization and safe-execution restrictions (US-06).
  - **Answer / evidence:** _Write here, or link an API sample / PR._
- [ ] **TODO · JUAN + SAHIL + SHENGRONG + DANNY** — Define measurable baseline/comparison data and missing-evidence behavior for time-saved estimates (US-07).
  - **Answer / evidence:** _Write here, or link a benchmark or fixture / PR._
- [ ] **TODO · JUAN** — Trace the seven D1 stories to at least one agreed contract test or a clearly documented unsupported/deferred path; do not claim a passing test for an unimplemented feature.
   - **Answer / evidence:** Draft mapping: US-01 → T-OS-01/02, T-HTTP-01 · US-02 → T-DB-01/02, T-HTTP-01 (needs HTTP-01m history test) · US-03/04 → T-ALG-01/02, execution DEFERRED via T-ACT-01 · US-05 → T-ALG-01..03, T-UI-01, T-E2E-01 · US-06 → **gap: no test ID yet, propose T-AUTO-01** · US-07 → **gap: no test ID yet, propose T-IMPACT-01**. To be confirmed with team.

### 00.1 | Shared data flow (Juan tests every boundary)

```text
 +----------------------+        +-----------------------+
 | WINDOWS [Enrique]    |        | LINUX [Mohan]         |
 | devices/process I/O  |        | devices/process I/O   |
 +-----------+----------+        +-----------+-----------+
             |                               |
             +-------------+-----------------+
                           |
                           v
             +-----------------------------+
             | CORE [Shengrong]             |
             | normalize IDs/units/caps     |
             | ingest / retrieve / route    |
             +------+----------------+------+
                    |                |
                    v                v
             +------------+   +-----------------------+
             | DB [Sahil] |-->| ALGO [John + Jesslyn] |
             | history    |   | RAID0 / SSD caching   |
             | settings   |   | realtime + history    |
             +------------+   +-----------+-----------+
                                          |
                                          v
             +-----------------------------+-----------+
             | CORE [Shengrong]                         |
             | recommendations -> local HTTP API       |
             +----------------------+------------------+
                                    |
                                    v
                            +---------------+
                            | UI [Danny]    |
                            | review/approve|
                            +---------------+

   +------------------------------------------------------+
   | QA [JUAN] -> contract tests / fixtures / benchmarks  |
   |   checks: WIN, LINUX, CORE, DB, ALGO, UI, actions    |
   +------------------------------------------------------+

**Note:** Logical arrows do not dictate process boundaries. We still need to agree
whether CORE passes DB query results to ALGO or ALGO calls an injected DB
repository interface. ALGO should NOT depend on raw SQL/table internals.
```

---

## 01 | API CONTRACT REGISTRY — Ownership and status

> [!NOTE]
> **COORDINATION — JOHN:** Keep ownership and status current. **Checking a TODO does not mean an API has been accepted, implemented, or verified.**


**Status legend:** `PROPOSED` -> `UNDER REVIEW` -> `ACCEPTED` -> `IMPLEMENTED` -> `VERIFIED`. `UNSUPPORTED` is an allowed, documented capability result.

| API ID | Boundary / function set | PRODUCER | CONSUMER / ACCEPTANCE REVIEWER | TEST REVIEWER | Priority | Status |
|---|---|---|---|---|---|---|
| **OS-01** | Device discovery and capabilities | **Enrique / Mohan** (per platform) | Shengrong; John/Jesslyn | **Juan** | P0 | PROPOSED |
| **OS-02** | Device + process I/O samples | **Enrique / Mohan** | Shengrong; Sahil; John/Jesslyn | **Juan** | P0 | PROPOSED |
| **OS-03** | Optional file activity / file mapping | **Enrique / Mohan** | John/Jesslyn; Shengrong; Sahil | **Juan** | P1 | INVESTIGATE |
| **CORE-01** | Normalize, ingest, decide, surface data | **Shengrong** | Sahil; John/Jesslyn; Danny | **Juan** | P0 | PROPOSED |
| **DB-01** | Persist observations + history queries | **Sahil** | Shengrong; John/Jesslyn | **Juan** | P0 | PROPOSED |
| **ALGO-01** | RAID0 recommendation API | **John + Jesslyn** | Shengrong; Enrique/Mohan; Danny | **Juan** | P0 | PROPOSED |
| **ALGO-02** | SSD caching recommendation API | **John + Jesslyn** | Shengrong; Enrique/Mohan; Danny | **Juan** | P0* | PROPOSED |
| **HTTP-01** | Dashboard HTTP/JSON API | **Shengrong** | **Danny** | **Juan** | P0 | PROPOSED |
| **ACTION-01** | Preview / approved storage action | **Enrique / Mohan**, dispatch Shengrong | John/Jesslyn; Danny | **Juan** | P1/P2 | INVESTIGATE |
| **QA-01** | Fixtures / contract + negative tests | **Juan** | All module owners | John + Shengrong | P0 | PROPOSED |
| **QA-02** | Benchmarks + before/after evaluation | **Juan** | John/Jesslyn; OS agents; Danny (results) | John + Shengrong | P1 | PROPOSED |
| **QA-03** | CI/PR smoke and integration checks | **Juan** | All developers | John + Shengrong | P0 | PROPOSED |

`*` P0 = define input/output and use mock data; actual SSD cache implementation depends on feasibility and safety.

### 01.1 | Contract review worksheet — Copy for each API

> **If you are a Producer:** Fill in this worksheet for each new or changed API. **If you are a Consumer:** Confirm the interface covers what you need. **For QA:** Review how we will test it.

**API ID:** _enter ID_  
**Producer:** _fill in owner_ · **Consumers:** _fill in reviewers_ · **QA reviewer:** _fill in test owner_  
**Signature / endpoint:** _paste exact signature or endpoint_  
**Required fields / types / units:** _enter_  
**Optional / missing / access-denied behavior:** _enter_  
**Success example:** _paste JSON/fixture path_  
**Failure or unsupported example:** _paste JSON/fixture path_  
**Platform limits:** _enter_  
**Evidence / PR:** _paste link_

- [ ] **TODO · PRODUCER** — Signature and input/output schemas filled in; sample values supplied.
- [ ] **TODO · PRODUCER** — Errors, capability limits and unsupported cases documented.
- [ ] **TODO · CONSUMER(S)** — API provides the needed fields and behavior, or a mutually agreed fallback.
- [ ] **TODO · JUAN** — Test fixture and validation/negative-test plan available.
- [ ] **TODO · PRODUCER + CONSUMER** — Agreement recorded in the PR discussion.
- [ ] **TODO · IMPLEMENTED** — Callable implementation merged (separate from contract acceptance).
- [ ] **TODO · VERIFIED** — Automated tests passed with linked evidence (separate from implementation).

**Consumer reviewer(s) + date:** _names / date / PR comments_  
**QA reviewer + date:** _name / date / PR comments_

---


#### ALGO-01 | Contract Review — John

**API ID:** `ALGO-01`  
**Producer:** John (ALGO-01 implementation), Jesslyn (shared algorithm review)  
**Consumers:** Shengrong (CORE), Enrique/Mohan (OS), Danny (UI)  
**QA reviewer:** Juan  

**Signature / endpoint:**  
`evaluate_raid0_policy(devices, realtime, history, mode_config, capabilities) -> list[dict]`

**Required fields / types / units:**  
See [§05.1 — ALGO-01](#algo-01-spec) for the required inputs and algorithm rules. We use the existing Device, FileActivity and Recommendation structures defined in §02.1 and §02.2. File sizes and device capacities are measured in bytes, timestamps use UTC, and read/write counts refer to operations within a sampling interval.

**Optional / missing / access-denied behavior:**  
See [§05.1 — Missing data fallback](#algo-01-spec). Files without the required information are skipped. If file-level data is unavailable or no suitable SSD is found, ALGO-01 returns `none`. Invalid evaluation time raises `PolicyInputError`.

**Success example:**  
- [Input](../backend/algorithms/algo01/tests/fixtures/d2-temp-valid.json)
- [Expected output](../backend/algorithms/algo01/tests/fixtures/d2-temp-valid-output.json)

A simulated HDD file with 120 reads in 60 seconds. The algorithm recommends SSD placement when enough space is available.

**Failure or unsupported example:**  
- [Input](../backend/algorithms/algo01/tests/fixtures/d2-temp-none.json)
- [Expected output](../backend/algorithms/algo01/tests/fixtures/d2-temp-none-output.json)

No file-level activity is available, so the algorithm returns `none`.

**Platform limits:**  
See [§05.1 — ALGO-01 limitations](#algo-01-spec). For D2, the algorithm only supports the `performance` goal and selects one SSD per evaluation. It recommends file placement but does not move files, implement caching or estimate actual performance improvements.

**Evidence / PR:**  
Local implementation and tests: `backend/algorithms/algo01/`

Test command:  
`python -B -m unittest discover -s backend/algorithms/algo01/tests -v`

PR: Pending. CORE integration has not been completed.

- [x] **TODO · PRODUCER** — Signature and input/output schemas filled in; sample values supplied.
- [x] **TODO · PRODUCER** — Errors, capability limits and unsupported cases documented.
- [ ] **TODO · CONSUMER(S)** — API provides the needed fields and behavior, or a mutually agreed fallback.
- [x] **TODO · JUAN** — Test fixture and validation/negative-test plan available.
- [ ] **TODO · PRODUCER + CONSUMER** — Agreement recorded in the PR discussion.
- [ ] **TODO · IMPLEMENTED** — Callable implementation merged.
- [ ] **TODO · VERIFIED** — Automated tests passed with linked evidence.

**Consumer reviewer(s) + date:** Pending.  
**QA reviewer + date:** Pending.

---

## 02 | SHARED DATA SCHEMAS — Owner: Shengrong

> [!NOTE]
> **PRODUCER / COORDINATION: SHENGRONG** · **DATA PRODUCERS: ENRIQUE, MOHAN, SAHIL**  
> **CONSUMERS / REVIEWERS: JOHN, JESSLYN, DANNY** · **QA: JUAN**


**Shared rules**

- UTC ISO-8601 timestamps, for example `2026-10-08T21:00:00Z` (format illustration only).
- Use **bytes**, **bytes_per_sec**, **ops_per_sec (IOPS)**, **milliseconds** for latency, and specify sample windows.
- `null` / missing capability != measurement `0`.
- We need consistent device IDs across telemetry, database, recommendations, and action execution. If you own an OS agent, document whether IDs remain stable after a reboot.
- A process instance needs `(pid, start_time_utc)` or an equivalent unique ID; do **not** assume PIDs never repeat.
- File-level measurements may be unavailable or privacy/permission-sensitive. Do not infer an individual hot file merely from device IOPS.
- [ ] **TODO · SHENGRONG + ALL REVIEWERS** — Decide the JSON `schema_version` strategy and backward compatibility policy.
  - **Decision / schema link:** _Write the agreed version format and PR link here; then check above._

### 02.1 | Common data records (proposed)

```python
# Device
{
    "host_id": str, "device_id": str, "display_name": str,
    "media_type": str | None,              # "hdd"/"ssd"/"unknown"
    "capacity_bytes": int | None,
    "free_bytes": int | None,
    "mount_points": list[str],
    "is_available": bool,
}

# DeviceMetric
{
    "host_id": str, "device_id": str, "timestamp_utc": str,
    "sample_window_seconds": float,
    "read_bytes_per_sec": float | None,
    "write_bytes_per_sec": float | None,
    "read_iops": float | None,
    "write_iops": float | None,
    "avg_read_latency_ms": float | None,
    "avg_write_latency_ms": float | None,
    "source": str,
}

# ProcessMetric
{
    "host_id": str, "pid": int, "start_time_utc": str | None,
    "process_name": str | None, "timestamp_utc": str,
    "sample_window_seconds": float,
    "read_bytes_per_sec": float | None,
    "write_bytes_per_sec": float | None,
    "attributed_device_id": str | None,
}

# FileActivity (OPTIONAL: only with verified file-level data)
{
    "host_id": str, "file_id": str | None, "path": str | None,
    "device_id": str | None, "window_start_utc": str,
    "window_end_utc": str, "read_bytes": int | None,
    "write_bytes": int | None, "read_ops": int | None,
    "write_ops": int | None, "file_size_bytes": int | None,
    "source": str,
}
```

### 02.2 | Recommendation record — Not action authorization

```python
{
    "recommendation_id": str,
    "mode": str,                   # "raid0" or "ssd_caching"
    "action": str,                 # tentative: move/cache/evict/none
    "file_id": str | None,
    "source_device_id": str | None,
    "target_device_id": str | None,
    "reason": str,
    "created_at_utc": str,
    "requires_approval": bool,
    "estimated_benefit": dict | None,
    "constraints": list[str],
}
```

### 02.3 | ALL REVIEWERS — Shared schema acceptance

- [ ] **TODO · SHENGRONG + ENRIQUE + MOHAN** — Every metric is labeled raw / derived / estimated and a source is specified.
  - **Decision / evidence:** 

| Metric | Source Type | Windows Source | Linux Source |  Windows Evidence | Linux Evidence |
---|---|---|---|---|---|
| DeviceMetric | raw + derived(for Linux) | ETW | /proc/diskstats | Kernel IO Tracing (ETW) | Linux kernel I/O statistics fields |
| ProcessMetric | raw(read/write bps for Windows) + derived(for Linux) | ETW | /proc/<pid>/io | Kernel IO Tracing (ETW) | Linux kernel 3.3 /proc/<pid>/io - Display the IO accounting fields |
| FileMetric (Linux) / FileActivity | raw counters + derived (interval differences, average gap) for Linux | Not yet emitted | eBPF fentry/fexit on kernel `vfs_read`/`vfs_write` family (BCC) | — | Linux backend §03 "File tracking records"; live test on Fedora 44 |

- [ ] **TODO · SHENGRONG + SAHIL + JOHN/JESSLYN + JUAN** — Agree on required/optional fields, `null`, empty collections, and explicit `UNSUPPORTED` semantics.
  - **Decision / evidence:** 
    Proposed:
  - 
| value | definition |
---|---|
| 0 | the field is defined and a valid and measured value of zero |
| null | the field is defined but no valid value |
| [] | a valid return value empty collections |
| UNSUPPORTED | the requested metric is not supported by the platform |

---

## 03 | OS AGENTS — Producers: Enrique (Windows), Mohan (Linux)

> [!NOTE]
> **PRODUCER: ENRIQUE — WINDOWS / MOHAN — LINUX**  
> **CONSUMER REVIEW: SHENGRONG, JOHN, JESSLYN, SAHIL (as applicable)** · **QA: JUAN**


**Priority:** OS-01/02 P0; OS-03 optional P1; storage actions later.

```text
      OS [Enrique / Mohan]       CORE [Shengrong]      ALGO [John/Jesslyn]
   +---------------------+     +------------------+    +-----------------+
   | get_capabilities()  |---->| normalize shape  |--->| check supported |
   | list_devices()      |---->| normalize IDs    |--->| compute advice  |
   | sample_*_io()       |---->| validate units   |    +-----------------+
   +---------------------+     +------------------+
              ^                        |
              +-------- JUAN tests ----+
```

### PROPOSED PYTHON SIGNATURES — Producer must confirm

```python
def get_capabilities() -> dict: ...
def list_devices() -> list[dict]: ...
def sample_device_io(interval_seconds: float) -> list[dict]: ...
def sample_process_io(interval_seconds: float) -> list[dict]: ...
def sample_file_activity(interval_seconds: float, limit: int = 100) -> list[dict]: ...  # OPTIONAL
```


### Python signatures — Linux Backend

Current implemented interface:

```python
class LinuxBackend:
    def __init__(self, host_id: str): ...
    def start(self) -> ErrorCode | None: ...
    def close(self) -> None: ...
    def refresh_disk_collect(self) -> None: ...

    def list_devices(self) -> list[Drive]: ...
    def list_processes(self) -> list[Process]: ...

    def get_device_io(
        self, interval_seconds: int, device_name: str
    ) -> DriveMetric | None: ...

    def get_process_io(
        self, interval_seconds: int, pid: int
    ) -> ProcessMetric | None: ...

    def track_file(self, file_path: str) -> ErrorCode | File: ...
    def track_folder(self, folder_path: str) -> ErrorCode | tuple[File, ...]: ...
    def untrack_file(self, file: File) -> ErrorCode | None: ...
    def untrack_folder(self, files: tuple[File, ...]) -> ErrorCode | None: ...
    def list_tracked_files(self) -> tuple[File, ...]: ...

    def get_all_file_stats(
        self, interval_seconds: int
    ) -> dict[File, FileMetric | None]: ...
```

`get_capabilities()` is not implemented. `sample_device_io()` and `sample_process_io()` are replaced by `get_device_io()` / `get_process_io()` on background-collected history. `sample_file_activity()` is replaced by the track/untrack calls plus `get_all_file_stats()`.

**Typical usage**

```python
backend = LinuxBackend("host-1")
err = backend.start()        # None, or ErrorCode.FILE_TRACER_UNAVAILABLE (disk/process still run)

file = backend.track_file("/home/user/data.db")        # File, or ErrorCode
files = backend.track_folder("/home/user/projects")    # tuple[File, ...], or ErrorCode

stats = backend.get_all_file_stats(5)                  # {File: FileMetric | None}
for f, metric in stats.items():
    if metric is not None:
        print(f.absolute_path, metric.read_completed_bytes, metric.read_average_gap)

backend.untrack_file(file)
backend.untrack_folder(files)
backend.close()
```

**Sampling history and interval limits** (`constants.py`)

All three collectors sample in a daemon thread about once per second. `interval_seconds` counts one-second samples and must be at least 1 and smaller than the history length.

| Collector | History length | Largest usable `interval_seconds` | `interval_seconds <= 0` |
|---|---|---|---|
| Disk | 600 | 599 | returns `None` |
| Process | 10 | 9 | raises `ValueError` |
| File | 10 | 9 | raises `ValueError` (only while started; returns `{}` when stopped) |

At most 16,384 files can be tracked at once (`MAX_TRACKED_FILES`).

#### File tracking records

`File` identifies a tracked file:

| Field | Type | Meaning |
|---|---|---|
| `absolute_path` | `str` | Canonical absolute path, symlinks resolved |
| `inode` | `int` | `st_ino` from `os.stat()` at the last check |
| `device` | `int` | `st_dev` from `os.stat()` at the last check (raw value, not a block device name) |

Two `File` objects are equal, and hash equally, when `absolute_path` is equal. `inode` and `device` are not compared. A file replaced at the same path (for example an editor saving through rename) therefore keeps the same record, and its counters continue.

`FileMetric` is the activity of one file over an interval (difference of two cumulative samples):

| Field | Type | Units / meaning |
|---|---|---|
| `file` | `File` | File, with its most recent inode/device |
| `timestamp` | `str` | UTC ISO 8601, start of the interval |
| `duration` | `int` | Requested interval in seconds |
| `read_attempts` | `int` | Read calls on the file, including failed and zero-byte reads |
| `read_requested_bytes` | `int` | Bytes requested by read calls |
| `read_success_ops` | `int` | Read calls that returned more than 0 bytes |
| `read_completed_bytes` | `int` | Bytes actually returned by reads |
| `read_average_gap` | `float \| None` | Mean distance in bytes between where each successful read started and where the previous read on the same open file ended. `0` = fully sequential. `None` if no read contributed a gap in the interval |
| `write_attempts` | `int` | Write calls on the file |
| `write_requested_bytes` | `int` | Bytes requested by write calls |
| `write_success_ops` | `int` | Write calls that wrote more than 0 bytes |
| `write_completed_bytes` | `int` | Bytes actually written |
| `write_average_gap` | `float \| None` | Write equivalent of `read_average_gap` |

Gap details: the gap of an operation is `|start − previous_end|`, tracked per open file description (each `open()`), separately for reads and writes. The first operation after each `open()` has no previous operation and does not contribute.

`get_all_file_stats()` returns `None` for a file until it has been present in `interval_seconds + 1` samples, for example right after it is tracked.

**Suggested mapping to the shared `FileActivity` record (§02.1)** for CORE:

| `FileActivity` field | Linux source |
|---|---|
| `path` | `file.absolute_path` |
| `window_start_utc` / `window_end_utc` | `timestamp` / `timestamp + duration` seconds |
| `read_bytes` / `write_bytes` | `read_completed_bytes` / `write_completed_bytes` |
| `read_ops` / `write_ops` | `read_success_ops` / `write_success_ops` |
| `file_size_bytes` | **Not provided by `FileMetric`.** Collected internally, but not exposed; CORE can `os.stat()` the path for now |
| `device_id` | **Not provided.** `File.device` is a raw `st_dev`, not a block device name like `nvme0n1` |
| `file_id` | Not provided; `absolute_path` is the stable identifier |
| `source` | Suggested `"linux_ebpf"` |

#### Requirements for file tracking

- Root, or `CAP_BPF` + `CAP_PERFMON`.
- BCC Python bindings (`python3-bpfcc` on Debian/Ubuntu, `python3-bcc` on Fedora). **`file.py` imports BCC at module load, so without BCC installed, importing the Linux backend fails with `ModuleNotFoundError`, and device and process collection are unavailable too.**
- Kernel headers for the running kernel (BCC compiles the probe program on every `start()`).
- A kernel with BTF and fentry/fexit support. `vfs_read` and `vfs_write` must be traceable; `vfs_readv`, `vfs_writev`, `vfs_iter_read` and `vfs_iter_write` are attached when the kernel exposes them.
- If the probe program cannot be loaded (no fentry support, missing headers, insufficient privileges), `start()` returns `ErrorCode.FILE_TRACER_UNAVAILABLE`. Disk and process collection still start. The exception is kept in `backend.file_collector.last_error`.

**Expected capabilities** (each owner must mark **working / planned / unsupported**):

```python
{
    "device_metrics": bool,
    "process_metrics": bool,
    "process_to_device_attribution": bool,
    "file_access_metrics": bool,
    "file_level_pooling": bool,
    "ssd_caching": bool,
    "file_move": bool,
    "dry_run_action": bool,
    "notes": list[str],
}
```
### Expected capabilities — Linux

| Capability | Status | Notes |
|---|---|---|
| `device_metrics` | **Implemented; verification pending** | Background sampling of `/proc/diskstats`, bounded history, interval differences |
| `process_metrics` | **Implemented; verification pending** | Background sampling of `/proc/[pid]/io`, bounded history, interval differences; permission limits apply |
| `process_to_device_attribution` | **Unsupported** | `/proc/[pid]/io` does not identify physical devices |
| `file_access_metrics` | **Implemented; verified on one host** | eBPF (BCC) fentry/fexit probes on the kernel VFS read/write functions; per-file attempts, requested/completed bytes, successful operations and average access gap. Live test passed on Fedora 44, kernel 7.2.7, btrfs, before the latest refactor (see §03.2) |
| `file_level_pooling` | **Planned** | No mergerFS integration |
| `ssd_caching` | **Planned** | No cache/redirection implementation |
| `file_move` | **Planned** | No file migration function |
| `dry_run_action` | **Planned** | No dry-run function |

**Notes:**
- Disk, process and file collectors sample in daemon threads at a target cadence of about one second; observed elapsed intervals may differ.
- Metrics are differences between cumulative samples; collection history is in memory only and is cleared by `close()`.
- File counters describe application requests at the VFS layer, not physical disk I/O. Reads served from the page cache are counted.
- Not counted: memory-mapped I/O, `sendfile`, `splice`, `copy_file_range`, and I/O submitted through io_uring, because these do not go through the probed functions. For `readv`/`writev` calls with more than 16 buffers, requested bytes count only the first 16.
- When a file is tracked (and again after it is replaced), the backend opens it once and issues a 0-byte read so the kernel can report how it identifies the file. This read is not counted. It is needed because `stat()` can report a different device than the kernel uses (for example btrfs subvolumes).
- `track_folder()` is a snapshot: files created later are not picked up. Symlinks are not followed. A second path to an already tracked file (hard link) returns the first path's `File`.
- Callable capability reporting (`get_capabilities()`) is unavailable.
- No overhead benchmark has been run for any collector.

---

### Python signatures — Windows Backend

Current access point:
```python
__init__.py
     def create_backend(host_id: str) -> WindowsBackend
```
Current implemented interface:

```python
class WindowsBackend:
    # don't call __init__, call create_backend instead
    def __init__(self, host_id: str,etw_source: EtwSource,device_provider: DeviceProvider): ...

    def start(self) -> None: ...
    def close(self) -> None: ...

    def get_devices(self) -> list[Device]: ...

    def get_device_metrics(
        self,
        sample_window_seconds: float = 10.0,
    ) -> list[DeviceMetric]: ...

    def get_process_metrics(
        self,
        sample_window_seconds: float = 10.0,
    ) -> list[ProcessMetric]: ...

    def get_file_activity(
        self,
        sample_window_seconds: int,
        now_ns: int | None = None,
    ) -> list[FileActivity]:

    def get_collection_health(self) -> CollectionHealth:
```

The coded `get_file_activity()`, and `get_collection_health` interfaces do not work as of now.


### Expected capabilities — Windows

| Capability | Status | Notes |
|---|---|---|
| `device_metrics` | **Implemented; verification pending** | Tracing every single DiskIO event the kernel fires and logging it with disk number |
| `process_metrics` | **Planned** | Already tracing every single FileIO event the kernel fires as to also catch cache hits, can order by PID |
| `process_to_device_attribution` | **Planned** | Can sort/filter DiskIO events by PID if required |
| `file_access_metrics` | **Planned** | Tracing FileIO events, need to complete the path with drive letter. |
| `file_level_pooling` | **Planned** | WinFsp envisioned |
| `ssd_caching` | **Planned** | No cache/redirection implementation |
| `file_move` | **Planned** | No file migration function |
| `dry_run_action` | **Planned** | No dry-run function |
  
**Notes:**
- Device and process information is represented using frozen Python dataclasses.
- Collects events with a callback: only runs when needed with as little overhead as required.
- Metrics are always cumulative viewed events: no history from before tracking started is available.
- FileIO metrics are currently unavailable.
---

### 03.1 | ENRIQUE — WINDOWS PRODUCER CHECKLIST

> [!NOTE]
> **IF YOU OWN THE WINDOWS AGENT:** Please complete each **TODO** below and provide evidence. **CORE + ALGO reviewers:** Confirm the data is usable. **QA:** Define test cases.


- [x] **TODO · ENRIQUE** — Actual module path / language / callable signatures
  - **Answer / evidence:**
  - Python 3; 
    - `backend.py` (public API), 
    - `contracts.py` (frozen dataclasses),
    - `aggregation.py` (keeps all processed events and uses them to create metrics),
    - `device_provider.py` (discovers disks and mount points with WMI), 
    - `etw_source.py` (ETW DiskIO and FileIO events decoder),
    - `transport.py` (Kernel tracking setup),
    - `__init.py__` (links the modules together with create_backend),
    - `__main__.py` (callable from the admin console with python -m),   
    The implemented `WindowsBackend` API is listed above. `create_backend(host_id : str)` is constructed with the required argument.
- [x] **TODO · ENRIQUE** — Windows data source(s) and permissions required
  - **Answer / evidence:**
    - ETW:
      - automatically receive IO events as they are being processed
      - admin permission required as it uses the kernel
    - WMI:
      - discover all disks and mount points
      - admin permission may be required
- [x] **TODO · ENRIQUE** — Available process/file/device IO metrics and units / unavailable fields

  - **Answer / evidence:**
 
| Record | Fields | Units / source |
|---|---|---|
| `DeviceMetric` | `host_id`, `device_id`, `timestamp_utc`, `sample_window_seconds`, `read_bytes_per_sec`, `write_bytes_per_sec`, `read_iops`, `write_iops`, `avg_read_latency_ms`, `avg_write_latency_ms`, `source` | UTC ISO 8601; requested seconds (`float`); bytes; completed disk operations from ETW |
| `ProcessMetric` | `host_id`, `pid`, `start_time_utc`, `process_name`, `timestamp_utc`, `sample_window_seconds`, `read_bytes_per_sec`, `write_bytes_per_sec`, `attributed_device_id` | UTC ISO 8601; requested seconds (`float`); bytes requested by this PID, based on the I/O operations it emitted |
| `FileActivity` | `host_id`, `file_id`, `path`, `device_id`, `window_start_utc`, `window_end_utc`, `read_bytes`, `write_bytes`, `read_ops`, `write_ops`, `file_size_bytes`, `source` | UTC ISO 8601; file path determined by `FileObject` name attribution using other `FileIo` events; drive/volume mapping determined through correlation with storage metadata and, where possible, `DiskIo` events; not yet emitted |
| `Device` | `host_id`, `device_id`, `display_name`, `media_type`, `capacity_bytes`, `free_bytes`, `mount_points`, `is_available` | WMI; capacity reported for each disk/device |
  
- [x] **TODO · ENRIQUE** — Sample cadence and measured overhead
  - **Answer / evidence:**
  Event handling happens by callback, so cadence is as fast as events happen. Overhead not yet measured.

  **Known Limitations**
  - FileIO events are dropped if no prior DiskIO event has mapped their FileObject to a physical drive
  - Likewise DiskIO events will not count towards a file's diskIO if no prior FileIO event has mapped it to its FileObject
  - A FileIO event is only duplicated as DiskIO event if it misses the cache
  - Process name may not always be obtainable

- [ ] **TODO · ENRIQUE** — File-level pooling and SSD cache feasibility (WinFsp or alternative)
  - **Answer / evidence:** WinFsp still considered for this
- [x] **TODO · ENRIQUE** — Return shape for unsupported/error conditions
  - **Answer / evidence:**
    - Any unavailable field will be None
    - A metric (e.g. read IOPS) with 0 events contributing towards it (e.g. only writes) will be marked as None
    - 
- [ ] **TODO · ENRIQUE** — One success fixture, one unsupported fixture, relevant PR
  - **Answer / evidence:**
    
    ```python
    DeviceMetric(host_id='debug session', device_id=0, timestamp_utc='2026-10-22T10:34:00.795578Z'
        , sample_window_seconds=1, read_bytes_per_sec=81920.0, write_bytes_per_sec=37888.0
        , read_iops=2.0, write_iops=7.0, avg_read_latency_ms=None
        , avg_write_latency_ms=None, source='windows_etw')
    ```
    Bad call:
    ```python
    backend.get_device_metrics(-1)
    raises ValueError
    ```
Remaining Work:
  - properly filter by FileIO or DiskIO for their respective metrics
  - properly assign FileIO paths
  - measure collection health and dropped events
  - move from pid to either (start_time,pid) or process name
  - investigate WinFsp

---

**Current milestone:** The Windows backend currently implements EWT to track system-wide IO operations for disk, file, and processes alike. While only diskIO can effectively be measures as of now, the events pertaining to file and process operations are processed correctly. ssd caching, integration tests, process start time and storage actions remain to be implemented.


## 03.2 | MOHAN — LINUX PRODUCER CHECKLIST

- [x] **TODO · MOHAN** — Actual module path / language / callable signatures

  **Answer / evidence:** 
- Python 3; 
  - `backend.py` (public API), 
  - `collector.py` (disk, process and file sampler threads), 
  - `drive.py` (Drive related OS api)
  - `process.py` (Process related OS api)
  - `file.py` (file tracking: eBPF probe program, BCC loader, path helpers)
  - `models.py` (frozen dataclasses and `ErrorCode`), 
  - `constants.py` (sample-history lengths, tracking limits, `/proc` field indexes).
  - `tests/test_file_tracking.py` (unit tests, fake kernel probe), `tests/live_file_tracking.py` (live test, needs root + BCC), `tests/diagnose_file_tracking.py` (diagnostic for probe/key mismatches).

    The implemented `LinuxBackend` API is listed above. All three collectors receive data via background sampling. `DiskIOCollector(tuple(self.list_devices()))` is constructed with the required argument. This API does **not** implement the earlier proposed dictionary-based signatures.

- [x] **TODO · MOHAN** — Linux data source(s), permissions and supported distributions

  **Answer / evidence:**
  - `/proc/diskstats`: device sector and operation counters; sampled once per batch.
  - `/proc/[pid]/io`: per-process byte and syscall counters; access can be denied.
  - `/proc/[pid]/comm`: process name.
  - `/proc/[pid]/stat` (start time in clock ticks since boot) + `btime` from `/proc/stat`: process start time, used with the PID to tell processes apart when PIDs are reused.
  - `/sys/class/block/<device>/queue/rotational`, `lsblk`, `shutil.disk_usage()`: media type, device enumeration, partitions and filesystem space.
  - eBPF fentry/fexit probes on `vfs_read`, `vfs_write`, `vfs_readv`, `vfs_writev`, `vfs_iter_read`, `vfs_iter_write`, loaded through BCC: per-file I/O counters. Requires root (or `CAP_BPF` + `CAP_PERFMON`), BCC, kernel headers, and a kernel with BTF + fentry support.
  - `os.stat()`: file identity, size, and replacement detection for tracked files.
  - No automatic privilege escalation. Intended for standard Linux systems with procfs, sysfs and `lsblk`. File tracking verified on Fedora 44 (kernel 7.2.7, btrfs); other distributions not yet validated.

- [x] **TODO · MOHAN** — Available device/process/file metrics and units

  **Answer / evidence:**

  | Record | Fields | Units / source |
  |---|---|---|
  | `DriveMetric` | `timestamp`, `duration`, `read_bytes`, `write_bytes`, `read_count`, `write_count` | UTC ISO 8601; requested seconds (`int`); bytes; completed disk operations from `/proc/diskstats` |
  | `ProcessMetric` | `timestamp`, `duration`, `read_bytes`, `write_bytes`, `reads_complete`, `writes_complete` | UTC ISO 8601; requested seconds (`int`); bytes attributed by `/proc/[pid]/io`; `syscr`/`syscw` syscall counts |
  | `Drive` | `timestamp`, `device_id`, `model`, `serial`, `size_bytes`, `media_type`, `partitions` | Device metadata; partition `size_bytes`/`available_bytes` report filesystem usage, or zero if unavailable |
  | `Process` | `pid`, `name`, `start_time_timestamp` | Process metadata; start time is UTC ISO 8601 from `/proc/[pid]/stat` + boot time |
  | `File` | `absolute_path`, `inode`, `device` | Canonical path; `st_ino` / raw `st_dev` from `os.stat()`; equality by path only |
  | `FileMetric` | `file`, `timestamp`, `duration`, `read_attempts`, `read_requested_bytes`, `read_success_ops`, `read_completed_bytes`, `read_average_gap`, `write_attempts`, `write_requested_bytes`, `write_success_ops`, `write_completed_bytes`, `write_average_gap` | UTC ISO 8601; requested seconds (`int`); call counts; bytes; average gap in bytes (`float`) or `None`. Full definitions in the File tracking records table above |

  `FileSample` (cumulative counters plus `size_bytes`) and `FileCounters` are internal and not returned by the public API.

  Not provided: process-to-file attribution (which process did the I/O), file size in `FileMetric`, and the block device a file lives on.

- [ ] **TODO · MOHAN** — Sample cadence and measured overhead

  **Answer / evidence:**

  Device sampling:
  - Dedicated background thread, target cadence 1 second, scheduled with `time.monotonic()`
  - Thread-safe history protected by `threading.Lock`
  - Maximum history length: 600 samples
  - Nonblocking retrieval: `get_device_io()` calculates the difference between historical samples for a requested interval

  Process sampling:
  - Dedicated background thread, target cadence 1 second; each tick enumerates all processes and reads `/proc/[pid]/io`
  - Maximum history length: 10 samples
  - Nonblocking retrieval: `get_process_io()` compares two stored samples; the process must be present in both, with matching identity (PID + start time)

  File sampling:
  - Dedicated background thread, target cadence 1 second; each tick reads the kernel counters for every tracked file and `os.stat()`s each tracked path to detect replacement
  - Kernel-side counting is continuous (every matching read/write is counted as it happens); only the reading of totals is once per second
  - Maximum history length: 10 samples
  - Nonblocking retrieval via `get_all_file_stats()`

  **Measured overhead: Not available.**

  CPU usage, memory consumption, sampling latency, and performance under large process counts or heavy file I/O have not been benchmarked. File tracking adds one kernel map lookup to every VFS read/write on the system; this has not been measured.

  **Known limitations:**
  - Returned `duration` is the requested interval rather than measured elapsed time.
  - The configured `DEFAULT_SAMPLE_INTERVAL` constant is not currently used by any collector loop.

- [ ] **TODO · MOHAN** — mergerFS file-level placement/migration semantics and limitations

  **Answer / evidence:**

  **Status: Planned; not implemented.**
- 
- [ ] **TODO · MOHAN** — SSD cache mechanism (FUSE/symlink/alternative), redirect + coherency

  **Answer / evidence:**

  **Status: Planned; mechanism not selected.**
- 
- [x] **TODO · MOHAN** — Return shape for unsupported/error conditions

  **Answer / evidence:**

  | Operation | Current behavior |
  |---|---|
  | `start()` | `None` on success or if already started; `ErrorCode.FILE_TRACER_UNAVAILABLE` if the file tracer could not load (disk/process still start) |
  | `list_devices()` | Calls discovery even if the backend is stopped; handled `lsblk`/JSON failures return `[]` |
  | `list_processes()` | Returns `[]` while stopped; otherwise enumerates accessible processes |
  | `get_device_io(interval_seconds, device_name)` | `None` if stopped, interval ≤ 0, unknown drive, insufficient history or missing sample entry |
  | `get_process_io(interval_seconds, pid)` | `None` if stopped, insufficient history, PID missing from either sample, or PID reused by a different process. **Raises `ValueError` if `interval_seconds <= 0`** |
  | `refresh_disk_collect()` | No-op while stopped; when running, replaces the disk collector and resets its history |
  | `track_file(file_path)` | `File` on success, or if the path is already tracked (existing `File` returned). Works before `start()`. Errors: `PATH_NOT_ABSOLUTE`, `FILE_NOT_FOUND`, `NOT_A_REGULAR_FILE`, `PERMISSION_DENIED` (cannot stat, or cannot be opened while the tracer is running), `TRACKING_LIMIT_REACHED`, `FILE_TRACER_UNAVAILABLE` |
  | `track_folder(folder_path)` | `tuple[File, ...]` (empty tuple for an empty folder). Files that cannot be tracked are skipped silently; if the limit is reached, files tracked so far are returned. Errors: `PATH_NOT_ABSOLUTE`, `FILE_NOT_FOUND`, `NOT_A_DIRECTORY`, `PERMISSION_DENIED`, `FILE_TRACER_UNAVAILABLE` |
  | `untrack_file(file)` | `None`, or `FILE_NOT_TRACKED`. History for the file is discarded |
  | `untrack_folder(files)` | `None`, or `FILE_NOT_TRACKED` if any file was not tracked; the others are still untracked |
  | `list_tracked_files()` | Tuple of tracked `File`s (empty if none); works while stopped |
  | `get_all_file_stats(interval_seconds)` | `{}` while stopped. While started: every tracked `File` mapped to a `FileMetric`, or to `None` if history is insufficient. **Raises `ValueError` if `interval_seconds <= 0`** |

  `ErrorCode` values (`models.py`): `SUCESS = 0`, `PROCESS_NOT_FOUND = 1`, `PROCESS_PID_REUSED = 2`, `BACKEND_NOT_STARTED = 3`, `INVALID_TIME_INTERVAL = 4`, `PATH_NOT_ABSOLUTE = 5`, `FILE_NOT_FOUND = 6`, `NOT_A_REGULAR_FILE = 7`, `NOT_A_DIRECTORY = 8`, `PERMISSION_DENIED = 9`, `FILE_NOT_TRACKED = 10`, `TRACKING_LIMIT_REACHED = 11`, `FILE_TRACER_UNAVAILABLE = 12`. Codes 0–4 are not returned by the public API (the process collector uses 1, 2 and 4 internally; the device/process APIs return `None` instead).

  Limitations:
  - Device and process APIs still return `None` without distinguishing permission errors, missing processes and other handled failures.
  - Unsupported capability responses have not been standardized across platforms.
  - Some subprocess or background-thread failures may propagate or terminate collection.

- [ ] **TODO · MOHAN** — One success fixture, one unsupported fixture, relevant PR

  Remaining work:
  - Validate historical sample accuracy.
  - Implementing raid-0 mode and caching mode automation.
---

**Current milestone:** The Linux backend implements device discovery, process discovery with start-time identity, background device/process I/O collection, interval-based metric retrieval, and per-file I/O tracking through eBPF (add/remove files while running, with access-pattern gaps), verified with a live test on one host. Benchmarks, multi-distribution validation, a capability API, pooling/caching operations, and safe storage actions remain outstanding.

### 03.3 | OS CONSUMERS + JUAN — Review and test checklist

- [ ] **TODO · SHENGRONG** — Windows/Linux outputs can be mapped into the same normalized schema.
- [ ] **TODO · JOHN + JESSLYN** — We receive enough data to calculate *safe* RAID0/caching recommendations, or have a clear fallback.
- [ ] **TODO · SAHIL** — Confirm that we can store sample IDs and timestamps unambiguously.
- [ ] **TODO · JUAN** — Fixture validates types/units/nullability and unsupported capability flags.
- [ ] **TODO · JUAN** — Sampling failure, access denied, disappearing drive and empty sample do not crash integration.

---

## 04 | DATABASE — Producer: Sahil

> [!TIP]
> **PRODUCER: SAHIL** · **CONSUMERS: JOHN, JESSLYN, SHENGRONG** · **QA: JUAN**  
> Historical file access data must not be fabricated when the OS agents cannot collect it.


**Priority:** DB-01 P0.

```text
 OS -> [CORE/Shengrong] --ingest--> [DB/Sahil]
                                   |        ^
                                   |        |
                              query history |
                                   v        |
                         [ALGO John/Jesslyn]
                         (via service OR injected DB adapter;
                          exact call route to be agreed)
```

### Initial signatures (PROPOSAL)

```python
def upsert_devices(devices: list[dict]) -> None: ...
def ingest_device_metrics(samples: list[dict]) -> None: ...
def ingest_process_metrics(samples: list[dict]) -> None: ...
def ingest_file_activity(samples: list[dict]) -> None: ...  # OPTIONAL

def query_device_history(device_ids: list[str], start_utc: str,
                         end_utc: str, bucket_seconds: int | None = None) -> list[dict]: ...
def query_process_history(process_instance_ids: list[str], start_utc: str,
                          end_utc: str, bucket_seconds: int | None = None) -> list[dict]: ...
def query_file_heat(start_utc: str, end_utc: str, limit: int = 100,
                    device_ids: list[str] | None = None) -> list[dict]: ...  # CONDITIONAL

def get_settings() -> dict: ...
def save_settings(settings: dict) -> None: ...
def save_recommendations(items: list[dict]) -> None: ...
def list_recommendations(mode: str | None = None) -> list[dict]: ...
```

### 04.1 | SAHIL — DATABASE PRODUCER CHECKLIST

> [!TIP]
> **IF YOU OWN THE DATABASE:** Please complete each **TODO** below, including query examples. **ALGO + CORE reviewers:** Confirm that the history queries meet our needs. **QA:** Test save/query round-trips.

- [x] **TODO · SAHIL** — Database engine, table/schema approach, migrations
  - **Answer / evidence:** Proposed design: Embedded SQLite with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) for concurrent local access without external server dependencies. Schema to be auto-initialized on startup via `CREATE TABLE IF NOT EXISTS`; migrations planned via a lightweight `schema_version` pragma table. (Status: Implemented).

- [x] **TODO · SAHIL** — Concrete Python callable/module or service adapter
  - **Answer / evidence:** Proposed interface: `wsd.db.repository.SQLiteHistoryRepository` implementing the abstract `HistoryRepository` protocol. Core and Algorithm modules consume plain Python dictionaries/dataclasses—no SQL syntax or database connection handles leak across component boundaries. (Status: Implemented).

- [x] **TODO · SAHIL** — Raw vs aggregated history; filter/time-window/bucket semantics
  - **Answer / evidence:** Proposed design: Raw telemetry samples stored chronologically. History queries accept `bucket_seconds`:
    - `bucket_seconds=None`: Returns raw recorded samples within `[start_utc, end_utc]`.
    - `bucket_seconds > 0`: Aggregates samples using SQL `AVG(read_bytes_per_sec)`, `MAX()`, and `AVG(read_iops)` binned by timestamp intervals.

- [x] **TODO · SAHIL** — Empty database, missing/stale data, retention, timestamp policy
  - **Answer / evidence:** 
    - Queries on an empty database or non-existent time windows return an empty list `[]` with status 200 (never raises an uncaught exception or returns fabricated zeroes).
    - All timestamps normalized to UTC ISO-8601 strings (`YYYY-MM-DDTHH:MM:SSZ`).
    - Retention policy: Planned background rolling pruning for raw telemetry older than 7 days.

- [x] **TODO · SAHIL** — Stable device/process IDs; optional file history source
  - **Answer / evidence:** 
    - Devices tracked by persistent hardware IDs (`device_id`).
    - Processes identified using composite strings: `f"{pid}_{start_time_utc}"` to prevent PID collision across restarts (US-02).
    - If the OS agent does not provide file activity, `query_file_heat()` returns an explicit empty list `[]` with status indicating file tracking is unsupported—heat scores are never guessed.

- [x] **TODO · SAHIL** — Expected query cost, indexes and batch limits
  - **Answer / evidence:** Composite indexes planned for `(device_id, timestamp_utc)` and `(process_instance_id, timestamp_utc)`. Ingestion planned with batched transactions (`executemany`) up to 500 records per commit. **Performance note:** `<10ms` for 24-hour historical queries is an unverified design target, not an empirically measured benchmark. Actual latency will be verified in QA benchmarks.

- [x] **TODO · SAHIL** — Document history needed for US-02 and benchmark comparison data retention/queries for US-07; do not generate a time-saved number from device IOPS alone.
  - **Answer / evidence:** US-02 historical process queries handled via `query_process_history`. US-07 (estimated time saved) delegates impact calculation to QA benchmark baselines: DB stores baseline run IDs and actual run durations, returning `{"status": "unavailable"}` if no direct baseline benchmark exists.

- [x] **TODO · SAHIL** — Success + empty + invalid-input examples/fixtures
  - **Answer / evidence:** Fixtures committed to repository branch under `tests/fixtures/`:
    - Device History Success: `tests/fixtures/history_sample.json`
    - Empty Result: `tests/fixtures/history_empty.json`
    - Process History (US-02): `tests/fixtures/process_history_sample.json`
    - Unsupported File Heat: `tests/fixtures/file_heat_unsupported.json`

### 04.2 | DB CONSUMERS + JUAN — Review and test checklist

- [ ] **TODO · JOHN + JESSLYN** — Historical queries support *both* RAID0 and SSD caching algorithms; no accidental SQL dependency.
- [ ] **TODO · JOHN + JESSLYN** — Confirm that we can request the required time windows and aggregations and detect insufficient samples.
- [ ] **TODO · SHENGRONG** — Ingestion and query interfaces agree on IDs and timestamps.
- [ ] **TODO · JUAN** — Round-trip ingest -> query matches fixture; empty history and duplicate/replayed ingestion are tested.
- [ ] **TODO · JUAN** — `query_file_heat()` returns `UNSUPPORTED`/empty when no file-level source exists; never fabricated heat.

### 04.3 | SHENGRONG + SAHIL + ALGO — Open integration decision

- [ ] **TODO · SHENGRONG + SAHIL + JOHN/JESSLYN** — Agree whether CORE fetches history for ALGO or ALGO calls a provided `HistoryRepository` interface. Both are options; avoid requiring ALGO to know raw SQL.
  - **Chosen design + justification / PR link:** _Write here._

---

## 05 | ALGORITHM / DECISION MAKER — Producers: John and Jesslyn

> [!IMPORTANT]
> **PRODUCERS: JOHN + JESSLYN** · **CONSUMERS: SHENGRONG, DANNY, ENRIQUE, MOHAN** · **QA: JUAN**  
> **IF YOU OWN THE ALGORITHM:** Please define the input/output contracts for both storage modes and review the OS/DB interfaces needed by our algorithms.


**Priority:** ALGO-01/02 interface P0.

```text
       REAL-TIME [OS]        HISTORICAL [DB]
              \                 /
               \               /
                +-------------+
                | Normalized  |
                | inputs      |
                +------+------+ 
                       |
              +--------v---------+
              | Decision Maker   |
              | [John + Jesslyn] |
              +-----+-------+----+
                    |       |
              RAID0 |       | SSD CACHING
                    v       v
            [placement]   [cache admission/eviction]
                    \       /
                     \     /
                [Recommendation]
                         |
                [Shengrong -> Danny]

 User-facing Performance / Balanced / Lifespan goals, if adopted,
 can be translated into policy parameters; these goals do not require separate algorithms.
```

### Initial signatures (PROPOSAL)

```python
def evaluate_raid0_policy(
    devices: list[dict], realtime: dict, history: dict,
    mode_config: dict, capabilities: dict
) -> list[dict]: ...

def evaluate_ssd_caching_policy(
    devices: list[dict], realtime: dict, history: dict,
    mode_config: dict, capabilities: dict
) -> list[dict]: ...
```

<a id="algo-01-spec"></a>

### 05.1 | JOHN + JESSLYN — ALGORITHM PRODUCER CHECKLIST

> [!IMPORTANT]
> **IF YOU OWN THE ALGORITHM:** Please complete each **TODO** below with proposed input/output behavior. **CORE + OS + UI reviewers:** Check whether you can use the result. **QA:** Cover both modes and edge cases.


- [x] **TODO · JOHN + JESSLYN** — **RAID0** minimum *required* fields vs optional telemetry
  - **Answer / evidence:** 
    - **Required:** Device ID, media type (HDD/SSD), availability, and target SSD's free space. ALGO-01 in my design would propose some candidates of files to move, so for each file, I require a file ID, source device ID, file size, read and write op counts, sampling intervals(timesteps), and data source(eg. Mock? from Windows? Linux?). CORE also provides the host ID and evaluation time.
    - **Optional:** File path, read and write bytes during sample interval, judgement on wether and operation is sequential or random I/O(classification), latency, I/O queue depth(when multiple tasks are all unfinishing on same storage device, depth++, just like ready queue in CSC369), and detailed per device performance metrics.
- [ ] **TODO · JOHN + JESSLYN** — **SSD caching** minimum required fields vs optional telemetry
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JOHN + JESSLYN** — Actual policy functions/heuristics and configuration keys
  - **ALGO-01 (John):** `evaluate_raid0_policy(devices, realtime, history, mode_config, capabilities)`
      - **For D2, the algorithm follows these rules:**
        1. Use the most recent valid I/O activity record for each file.
        2. Consider files on HDDs with at least 0.1 read operations per second, where reads account for at least 80% of total read/write operations.
        3. Prioritize files with higher read frequencies. If two files have the same frequency, prioritize the smaller file.
        4. Select the SSD with the most available space after reserving capacity.
        5. Recommend moving eligible files to the selected SSD, deducting each file's size from the remaining capacity.
      - **Configuration:** The default thresholds are 0.1 reads/second and 80% reads. The algorithm reserves at least 1 GiB or 10% of the SSD's total capacity, whichever is larger, and generates at most 10 recommendations.
      - **Limitations:** For D2, only the `performance` goal is supported. The algorithm generates recommendations but does not move files or estimate actual performance improvements.
    - **ALGO-02 (Jesslyn):** Pending Jesslyn's implementation details.
- [ ] **TODO · JOHN + JESSLYN** — User goal translation (if adopted; do not hard-code three algorithms)
  - **Answer / evidence:**
    - **ALGO-01 (John):** For D2, I only support the `performance` goal. The algorithm tries to find frequently read files on HDDs and recommends moving them to SSDs if enough space is available.
    - Other goals, such as `balanced` and `lifespan`, are not implemented yet. The algorithm returns `none` for unsupported goals instead of running three separate algorithms.
    - **ALGO-02 (Jesslyn):** Pending.
- [ ] **TODO · JOHN + JESSLYN** — Missing/stale/file-level-unavailable data fallback
  - **Answer / evidence:** 
    - **ALGO-01 (John):**
      1. If file-level I/O data is unavailable, return `none`. Per-process or per-device I/O cannot tell us which specific files are frequently accessed.
      2. If a file is missing important information (like file ID, size, read or write counts, etc.), skip that file.
      3. If the I/O data is too old (more than 300 seconds), ignore it.
      4. If no SSD is available or there is not enough space, return `none`.
      5. If the evaluation time is invalid, raise `PolicyInputError`.
- [ ] **TODO · JOHN + JESSLYN** — Allowed recommendation actions, constraints, reason format
  - **Answer / evidence:** 
    - **ALGO-01 (John):** The algorithm currently only returns two actions: `move` and `none`.
      - `move` means the algorithm recommends placing a file on an SSD. It does NOT actually move the file, and user approval is required.
      - `none` means no suitable recommendation can be made. The reason should explain why.
      - Each recommendation will explain which file is selected, where it should be moved, and why it was selected.
      - Simulated data is marked as `MOCK`.
      - `estimated_benefit=null` because we haven't measured the actual performance improvement.
- [ ] **TODO · JOHN + JESSLYN** — Example recommendation for RAID0 + caching and a `none` case
  - **Answer / evidence:** - **Answer / evidence:**
    - **ALGO-01 (John):** Suppose we have a 4 MiB file on an HDD. During a 60-second sampling interval, it is read 120 times and written 0 times. Its read frequency is 2 IOPS, and 100% of its I/O operations are reads. Since this file meets our thresholds, if an SSD has enough free space, the algorithm recommends moving it to that SSD (`action="move"`). User approval is required, and no actual file movement occurs in stage D2.
    - **None case:** If no file-level I/O data is available, the algorithm returns `action="none"` with a reason explaining that the required data is missing.

### 05.2 | ALGORITHM CONSUMERS + JUAN — Review and test checklist

- [ ] **TODO · SHENGRONG** — Can invoke each mode without knowing its internal scoring implementation.
- [ ] **TODO · ENRIQUE/MOHAN** — The proposed action types are safe/implementable on the respective platform or clearly unsupported.
- [ ] **TODO · DANNY** — Recommendation reason/target/status can actually be displayed to the user.
- [ ] **TODO · JUAN** — Given identical input fixture and configuration, outputs follow schema and safety constraints.
- [ ] **TODO · JUAN** — Null metrics, empty history, no SSD/free capacity, unsupported caching and conflicting options produce safe results.
- [ ] **TODO · JUAN** — Explainable output does not claim measured performance improvement unless benchmarked.

---


### 05.3 | ALGORITHM ACCEPTANCE GATES — Signed off separately

- [ ] **TODO · JOHN + JESSLYN** — Both mode-specific input/output schemas have examples, source fields and missing-data behavior.
- [ ] **TODO · OS / DB CONSUMER REVIEW** — John and Jesslyn reviewed OS and DB upstream contracts; blockers or negotiated fallbacks are recorded.
- [ ] **TODO · SHENGRONG + OS OWNERS + DANNY** — Consumers confirm recommendation/action fields are usable and safe to display.
- [ ] **TODO · JUAN** — Algorithm fixtures and negative tests are reviewed (not necessarily implemented yet).

> [!IMPORTANT]
> Checking Algorithm **TODO** items does **not** mean that downstream consumers have accepted the contract or that QA has verified the implementation.

---

## 06 | INTEGRATION AND FRONTEND — Shengrong and Danny

> [!NOTE]
> **HTTP / INTEGRATION PRODUCER: SHENGRONG** · **PRIMARY HTTP CONSUMER: DANNY**  
> **RELATED REVIEWERS: SAHIL, JOHN, JESSLYN** · **QA: JUAN**


**Priority:** CORE-01 / HTTP-01 P0.

```text
 [WIN/LINUX OS] ----+
                    |
 [DB/Sahil] --------+--> [CORE / LOCAL SERVICE] ---> HTTP/JSON ---> [UI/Danny]
                    |    [Shengrong]                         dashboard
 [ALGO/John/Jesslyn]+ 
                      ^                                 ^
                      +---------- JUAN contract tests --+
```

### 06.1 | Dashboard HTTP endpoints (initial proposals)

| ID | Verb | Endpoint | UI use case | Owner / reviewer |
|---|---|---|---|---|
| HTTP-01a | GET | `/api/v1/health` | service/agent availability | Shengrong -> Danny |
| HTTP-01b | GET | `/api/v1/capabilities` | disable unsupported controls | Shengrong -> Danny |
| HTTP-01c | GET | `/api/v1/devices` | device list / disk usage | Shengrong -> Danny |
| HTTP-01d | GET | `/api/v1/metrics/latest` | realtime device charts | Shengrong -> Danny |
| HTTP-01e | GET | `/api/v1/processes/latest` | process I/O list | Shengrong -> Danny |
| HTTP-01f | GET | `/api/v1/metrics/history?...` | device history chart | Shengrong -> Danny |
| HTTP-01g | GET | `/api/v1/recommendations?mode=...` | action suggestions | Shengrong -> Danny |
| HTTP-01h | POST | `/api/v1/recommendations/refresh` | request recalculation, **read-only** | Shengrong -> Danny |
| HTTP-01i | GET/PATCH | `/api/v1/settings` | mode settings / workload priority | Shengrong -> Danny |
| HTTP-01j | POST | `/api/v1/actions/preview` | show safe preview (later) | Shengrong -> Danny |
| HTTP-01k | POST | `/api/v1/actions/execute` | require approval (later) | Shengrong -> Danny |
| HTTP-01l | GET | `/api/v1/actions/{action_id}` | action progress/status (later) | Shengrong -> Danny |
| HTTP-01m | GET | `/api/v1/processes/history?process_instance_id=...&start_utc=...&end_utc=...` | **US-02**: individual application's historical I/O; source DB-01 | Shengrong -> Danny |
| HTTP-01n | GET | `/api/v1/impact/estimate?...` | **US-07**: evidence-based estimate of time saved; `unavailable` without baseline/comparison | Shengrong -> Danny; Juan reviews metric definition |

### 06.2 | SHENGRONG — INTEGRATION PRODUCER CHECKLIST

> [!NOTE]
> **IF YOU OWN CORE/INTEGRATION:** Please fill in each **TODO** below. **UI + DB + ALGO reviewers:** Confirm the behavior and response shape. **QA:** Test the integration path.


- [X] **TODO · SHENGRONG** — Local transport/framework and bind/security model
  - **Answer / evidence:** local HTTP + JSON. Bind to localhost
- [X] **TODO · SHENGRONG** — How OS agent gets selected and normalized
  - **Answer / evidence:** Through Windows/Linux Agent depends on host OS, normalized to DeviceMetric and ProcessMetric
- [X] **TODO · SHENGRONG** — Ingestion loop and/or event cadence
  - **Answer / evidence:** Every second
- [X] **TODO · SHENGRONG** — How DB / Algorithm get called (including the unresolved history route)
  - **Answer / evidence:** Core retrieves required history data from DB and latest data from agents then combines them and passes to Algorithm
- [X] **TODO · SHENGRONG** — Response envelope; 4xx/5xx/error/unsupported behavior
  - **Answer / evidence:** Response envelope: **status** indicates whether the request is succeeded or failed , **data** indicates the data contained, **error** indicates error type, null if the status is success

| Status | Definition | Notes |
---|---|---|
| 4xx | Invalid request | Return "error" with error code and message |
| 5xx | Core error | Return "error" with error code and message |
| UNSUPPORTED | Request is not supported | Return UNSUPPORTED error code |
- [X] **TODO · SHENGRONG** — One real or mocked end-to-end JSON response + branch/PR
  - **Answer / evidence:** 
```json
{
  "status": "success",
  "data": {
    "host_id": "host_mock",
    "device_id": "disk_mock",
    "timestamp_utc": "2026-10-11T08:30:57Z",
    "sample_window_seconds": 1,
    "read_bytes_per_sec": 1919810,
    "write_bytes_per_sec": 114514,
    "read_iops": 150.5,
    "write_iops": 40.0,
    "avg_read_latency_ms": null,
    "avg_write_latency_ms": null,
    "source": "mock"
  },
  "error": null
}
```
**Branch**: `shengrong/d2-contract`

### 06.3 | DANNY — FRONTEND CONSUMER CHECKLIST

> [!NOTE]
> **IF YOU OWN THE FRONTEND:** Please list what the UI needs from the HTTP API. **CORE reviewer:** Confirm feasibility. **QA:** Test the UI with mock responses and missing-data states.


- [ ] **TODO · DANNY** — Required endpoints for current prototype pages
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · DANNY** — Which exact fields need to be shown, sorted or filtered
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · DANNY** — Polling/update cadence and loading/empty/error states
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · DANNY** — How to present the two modes, goal, config and user approval
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · DANNY** — How to label unavailable metrics and unsupported features
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · DANNY** — Confirm per-process historical graph/drill-down fields for US-02, Auto Mode controls for US-06, and an evidence-aware "time saved" display for US-07.
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · DANNY** — Mock response / screenshot / relevant UI PR
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._

### 06.4 | HTTP CONSUMERS + JUAN — Review and test checklist

- [ ] **TODO · DANNY** — Can render screens against fixtures while core API implementation is unfinished.
- [ ] **TODO · SHENGRONG** — No CORS/localhost/authentication assumptions are silently left unresolved.
- [ ] **TODO · JUAN** — Endpoint method/path/schema/status/error checked with mocked server and frontend smoke test.
- [ ] **TODO · JUAN** — Missing metrics must not display fake zeros or imply an unsupported mode is working.

---

## 07 | STORAGE ACTIONS — Safety gate: Enrique, Mohan, Shengrong

> [!CAUTION]
> **PRODUCERS: ENRIQUE / MOHAN (OS execution), SHENGRONG (dispatch)**  
> **CONSUMERS: JOHN, JESSLYN, DANNY** · **SAFETY TEST OWNER: JUAN**  
> No simulated cache copy, recommendation, or UI toggle is sufficient evidence that a safe action executor exists.


**Priority:** Dry-run P1; real filesystem mutations P2, pending feasibility.

```text
 [ALGO] --recommend--> [UI] --user confirms--> [CORE] --preview-->
       [PLATFORM ADAPTER] --capability & safety checks--> [execute]

 NO auto execution just because a recommendation exists.
 Preview != execute. "File copied" != "Working SSD cache".
```

```python
def preview_storage_action(request: dict) -> dict: ...
def execute_approved_action(request: dict) -> dict: ...
def get_storage_action_status(action_id: str) -> dict: ...
```

### 07.1 | ENRIQUE + MOHAN — Storage action feasibility checklist

> [!CAUTION]
> **IF YOU OWN A PLATFORM BACKEND:** Please fill in these **TODO** items **separately for Windows and Linux**. Do not check a capability as supported unless you can provide evidence.


- [ ] **TODO · ENRIQUE + MOHAN** — RAID0: What does placement/migration mean on your platform?
  - **Answer / evidence:** _Write your supported behavior, limitations and PR/fixture link here._
- [ ] **TODO · ENRIQUE + MOHAN** — SSD cache: How does an app access the cache? Is it redirected?
  - **Answer / evidence:** _Write your supported behavior, limitations and PR/fixture link here._
- [ ] **TODO · ENRIQUE + MOHAN** — Cache coherency: What if the source or cached copy changes?
  - **Answer / evidence:** _Write your supported behavior, limitations and PR/fixture link here._
- [ ] **TODO · ENRIQUE + MOHAN** — Crash/interruption/power-loss recovery and rollback behavior
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE + MOHAN** — Permissions, free-space checks, locking and file-in-use failures
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE + MOHAN** — Is a dry-run feasible? What cannot be promised?
  - **Answer / evidence:** _Write your supported behavior, limitations and PR/fixture link here._

### 07.2 | JUAN — Storage action safety checklist

> [!CAUTION]
> **IF YOU OWN QA:** Check an item **only after** you have test evidence. Keep all storage-action safety tests isolated from actual user data.


- [ ] **TODO · JUAN** — Preview makes **no filesystem changes**.
- [ ] **TODO · JUAN** — No approval / unsupported capability / invalid target -> no execution.
- [ ] **TODO · JUAN** — Insufficient space and permission denied -> safe failure.
- [ ] **TODO · JUAN** — Interrupted copy/move/cache does not silently delete or corrupt source data.
- [ ] **TODO · JUAN** — Status and error report align with actual observed state.
- [ ] **TODO · JUAN** — Tests use **disposable test files and explicit test directories**; never run destructive tests against real user data.

---

## 08 | QA / BENCHMARK / CI — Producer: Juan

> [!TIP]
> **PRODUCER: JUAN** · **CONSUMERS: ALL MODULE OWNERS**  
> **REVIEWERS: JOHN, SHENGRONG, AND THE RELEVANT MODULE PRODUCER**  
> **QA work:** Please provide fixtures, API/integration tests, benchmarks, and CI. **All module owners:** Please fix defects found in the modules you implement.


**Priority:** QA-01 / QA-03 P0; QA-02 P1. If you produce an API, use the shared fixtures and tests to check your module.

**QA IS A CODE-CONTRIBUTING ROLE:** Build reusable test scripts, fixtures, mock data, test runners, GitHub Actions workflows, parsers, and benchmarks. Reviewing PRs alone is not the whole QA deliverable.

### 08.1 | QA — Required deliverables

```text
                   TEST LAYERS — OWNED BY JUAN

  +--------------------------------------------------------+
  | CONTRACT TESTS                 [P0 / weekend]          |
  | Types / units / schemas / missing data / unsupported   |
  +--------------------------------------------------------+
                        |
                        v
  +--------------------------------------------------------+
  | INTEGRATION TESTS              [P0]                    |
  | Agent -> Core -> DB -> Algorithm -> HTTP -> UI smoke    |
  +--------------------------------------------------------+
                        |
                        v
  +--------------------------------------------------------+
  | FAILURE & SAFETY TESTS          [P0 + later actions]   |
  | Agent gone / empty DB / no SSD / permission / crash    |
  +--------------------------------------------------------+
                        |
                        v
  +--------------------------------------------------------+
  | BENCHMARKS                      [P1]                    |
  | Before/after IOPS, throughput, latency, copy/load time |
  +--------------------------------------------------------+
                        |
                        v
  +--------------------------------------------------------+
  | AUTOMATION / CI                 [P0]                    |
  | PR runs checks -> visible pass/fail output             |
  +--------------------------------------------------------+
```

### 08.2 | Test API / CLI signatures (proposal only)

```python
# CLI scripts or equivalent test modules are fine.
def validate_fixture_schema(fixture_path: str, schema_name: str) -> dict: ...
def run_contract_suite(component: str, fixtures_dir: str) -> dict: ...
def run_integration_smoke(base_url: str, fixtures_dir: str) -> dict: ...
def run_benchmark(workload_spec_path: str, output_dir: str) -> dict: ...
def compare_benchmark_runs(baseline_path: str, optimized_path: str) -> dict: ...
```

**Suggested repository layout (Juan may change with PR):**

```text
 WSD repo
 +-- backend/              (OS / CORE owners)
 +-- frontend/             (Danny)
 +-- tests/                <-- JUAN OWNS test harness
 |   +-- fixtures/
 |   |   +-- devices.json
 |   |   +-- metrics_device.json
 |   |   +-- metrics_process.json
 |   |   +-- history_empty.json
 |   |   +-- history_sample.json
 |   |   +-- recommendations_raid0.json
 |   |   +-- recommendations_cache.json
 |   |   +-- unsupported_capabilities.json
 |   +-- contract/
 |   |   +-- test_os_schema.py
 |   |   +-- test_db_contract.py
 |   |   +-- test_algorithm_contract.py
 |   |   +-- test_http_contract.py
 |   +-- integration/
 |   |   +-- test_end_to_end.py
 |   +-- benchmarks/
 |       +-- workloads/            (config files)
 |       +-- run_benchmark.py
 |       +-- compare_results.py
 +-- .github/workflows/
 |   +-- tests.yml          <-- JUAN PROPOSES CI
 +-- docs/api-contracts.md  (all owners review)
```

### 08.3 | Cross-module test matrix — QA ownership

| TEST ID | Producer under test | Scenario | Expected outcome | Juan's script / fixture | Status |
|---|---|---|---|---|---|
| **T-OS-01** | Enrique / Mohan | Device sample valid | Schema + units + timestamp valid | _add test/fixture link_ | NOT STARTED |
| **T-OS-02** | Enrique / Mohan | Metric unsupported / no permissions | Explicit unsupported/missing, no fake zero | _add test/fixture link_ | NOT STARTED |
| **T-OS-03** | Enrique / Mohan | Drive disappears / bad interval | Predictable error, no crash | _add test/fixture link_ | NOT STARTED |
| **T-DB-01** | Sahil | Ingest, query historical range | IDs and values preserved, documented aggregation | _add test/fixture link_ | NOT STARTED |
| **T-DB-02** | Sahil | Empty DB / missing file telemetry | Empty or supported error semantics | _add test/fixture link_ | NOT STARTED |
| **T-ALG-01** | John / Jesslyn | RAID0 valid/invalid input | Valid recommendation or safe `none` | _add test/fixture link_ | NOT STARTED |
| **T-ALG-02** | John / Jesslyn | Cache capacity too small | Never recommend infeasible cache action | _add test/fixture link_ | NOT STARTED |
| **T-ALG-03** | John / Jesslyn | Same data, different user goal/options | Valid output; no undocumented claims | _add test/fixture link_ | NOT STARTED |
| **T-HTTP-01** | Shengrong | Normal/empty/invalid response | Correct status and JSON format | _add test/fixture link_ | NOT STARTED |
| **T-UI-01** | Danny | Missing data/unsupported mode | Safe display; no invented values | _add test/fixture link_ | NOT STARTED |
| **T-E2E-01** | All | Agent sample -> UI recommendation | Consistent IDs and data across modules | _add test/fixture link_ | NOT STARTED |
| **T-ACT-01** | Enrique / Mohan / Shengrong | Preview/no approval/interrupted action | No unsafe mutation, truthful status | _add test/fixture link_ | LATER |

### 08.3.1 | JUAN — Executable test completion checklist

> [!TIP]
> **JUAN OWNS** the executable test checklist. Every checked item must link to a fixture, test script, CI run, or test result.


Each tick means **the test exists, has been run, and its results are linked**. Updating the planning table by itself is not enough. Link a skipped/unsupported result clearly rather than marking an unrun test as passed.

- [ ] **TODO · JUAN** — **T-OS-01:** Valid device sample schema, units and timestamp.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-OS-02:** Unsupported metric / access-denied response.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-OS-03:** Disappearing drive / invalid sampling interval.
  - **Test path / result / CI run:** _Fill in after running._
- [x] **TODO · JUAN** — **T-DB-01:** Ingestion-to-history round-trip.
  - tests/integration/test_us02_history.py (CORE → real DB → CORE) + Sahil’s tests/test_db_contract.py; in CI
- [x] **TODO · JUAN** — **T-DB-02:** Empty history / unavailable file telemetry.
  - tests/integration/test_us02_history.py (empty history, null≠0) + tests/test_db_contract.py (file heat unsupported → []); in CI
- [x] **TODO · JUAN** — **T-ALG-01:** RAID0 algorithm contract with valid/invalid inputs.
  - **Test path / result / CI run:** Unit tests by John in `backend/algorithms/algo01/tests/` (41 pass); fixtures and expected outputs reviewed by Juan in #22; run automatically in CI (#23).
- [ ] **TODO · JUAN** — **T-ALG-02:** SSD cache capacity guard.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-ALG-03:** Policy/goal change and stable output schema.
  - **Test path / result / CI run:** _Fill in after running._
- [x] **TODO · JUAN** — **T-HTTP-01:** HTTP success / empty / invalid responses.
  - tests/contract/test_http_contract.py: 200 envelope, empty, 400 invalid input, 404, 500
- [ ] **TODO · JUAN** — **T-UI-01:** Frontend missing/unsupported data state.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-E2E-01:** End-to-end data IDs and recommendation flow.
  - tests/integration/test_e2e_demo.py: whole app in demo mode, device IDs consistent, DB round-trip + restart
- [x] **TODO · JUAN** — **T-ACT-01:** Preview/approval/interruption safety — LATER.
  - **08.4 | Reproducible benchmark contract
- [x] **TODO · JUAN** — ALGO-02 QA contract tests (mode `ssd_caching`, original never moved, capacity guard T-ALG-02) once John's ALGO-02 is ready.
- [x] **TODO · JUAN** — T-HTTP-01 for HTTP-01m `/processes/history` once the endpoint exists.
- [x] **TODO · JUAN** — Test duplicate/replayed ingestion (required by §04.2, not yet covered).
- [x] **TODO · JUAN** — QA-02 benchmark plan for US-07 baselines (§04 delegates time-saved evidence to QA).

### 08.4 | Reproducible benchmark contract

Juan should define workload configs rather than hard-code one person's machine. **Never promise a performance gain before measuring it.** Minimum proposed fields:

```python
{
    "test_id": str,
    "host_id": str,
    "platform": str,
    "device_ids": list[str],
    "workload_name": str,              # e.g. sequential copy / random I/O / app load
    "workload_parameters": dict,       # file size, threads, mix, queue depth, etc.
    "warmup_seconds": float,
    "repetitions": int,
    "cache_state": str,                # cold / warm / unspecified
    "wsd_mode": str,                   # baseline / raid0 / ssd_caching
    "start_time_utc": str,
    "results": dict,                   # throughput, IOPS, latency, duration, units
}
```

Benchmarks should record: **hardware + filesystem**, OS, SSD/HDD identity, baseline vs optimization, repeated trials, workload sizes, warm/cold cache state, and measurement limits. A raw speed-test number without context is not a reproducible comparison.

#### 08.4.1 | JUAN — QA / DevOps producer checklist

> [!TIP]
> **IF YOU OWN QA/DEVOPS:** Please complete the **TODO** items with implementation details and links to test code, fixtures, runs, or PRs.


- [x] **TODO · JUAN** — Test framework and Python version(s)
  - **Answer / evidence:** `pytest` runner (also runs `unittest` files); `flask` test client for HTTP. CI on Python 3.10 (minimum) and 3.12. See `.github/workflows/tests.yml` 
- [x] **TODO · JUAN** — Fixtures format/schema source of truth
  - **Answer / evidence:** JSON files in `tests/fixtures/` (Juan-branch). Source of truth = §02 of this doc. Any schema change = one PR updating §02 + fixtures together. Fixtures are MOCK until producers send real payloads (§08.4.2).
- [x] **TODO · JUAN** — Exactly which test cases run on every PR vs manual hardware tests
  - **Answer / evidence:** Every PR + push to `main`: everything in `tests/` (contract, HTTP, US-02 integration, end-to-end demo, DB, demo data, collector) + ALGO-01 unit tests, all on mock/demo data. Manual only: benchmarks on real SSD+HDD (QA-02) and storage-action safety tests (T-ACT-01, later).
- [x] **TODO · JUAN** — Mocking approach when Windows/Linux test host is unavailable
  - **Answer / evidence:** Fake agent returning `tests/fixtures/` JSON (US-02 test); fake CORE + Flask test client (HTTP tests); built-in demo mode for the whole app (end-to-end test). No real OS needed in CI. (PR #__)
- [ ] **TODO · JUAN** — Benchmark tools/commands, workload methodology, result format
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [x] **TODO · JUAN** — CI runner/OS compatibility, commands, time budget, branch/PR
  - **Answer / evidence:** GitHub Actions, `ubuntu-latest` + `windows-latest` × Python 3.10/3.12 (4 jobs), 10-min timeout, runs on every PR and push to `main`. (#23)
- [ ] **TODO · JUAN** — Add D1 Q4 traceability test plan: US-01 live process metrics; US-02 per-app history; US-03/04 action safety; US-05 recommendation; US-06 auto-mode opt-in; US-07 evidence-based estimated time saved.
  - **Answer / evidence:** _Write here, or link fixtures/tests / PR; then check the box above._
- [ ] **TODO · JUAN** — First runnable example: validate one fixture + print pass/fail
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [x] **TODO · JUAN** — Integration failure reporting / issue template and test evidence
  - **Answer / evidence:** Failures show as a red CI check on the PR. Cross-module bugs are filed as GitHub Issues assigned to the owner. Known bugs are kept visible in tests with `expectedFailure` until fixed.

#### 08.4.2 | ALL PRODUCERS — Evidence Juan needs

> [!NOTE]
> **IF YOU PRODUCE AN API:** Please provide fixtures and expected outputs so QA can create meaningful automated checks.


- [ ] **TODO · ALL PRODUCERS** — At least one **valid success payload** per proposed P0 API.
- [ ] **TODO · ALL PRODUCERS** — At least one **empty/unsupported/error payload** if applicable.
- [ ] **TODO · ALL PRODUCERS** — Clearly specified units, null behavior, stable identifiers and allowed enum values.
- [ ] **TODO · ALL PRODUCERS** — A callable implementation, stub or mock adapter for automated tests.
- [ ] **TODO · ALL PRODUCERS** — A named person to investigate a failed contract or integration test.

**ALGO-01 — John**

1. **Success example:** `d2-temp-valid.json`. A frequently read HDD file receives an SSD placement recommendation (`action="move"`), provided enough space is available.
2. **Negative example:** `d2-temp-none.json`. If file-level activity is unavailable, the algorithm returns `action="none"`. Invalid evaluation time raises `PolicyInputError`.
3. **Data format:** See [§05.1](#algo-01-spec). File sizes and capacities are in bytes, timestamps use UTC, and read/write operation counts refer to each sampling interval. `null` means unknown, not zero. File and device IDs identify the monitored objects; recommendation IDs identify generated records. Allowed actions are `move` and `none`.
4. **Implementation:** `evaluate_raid0_policy(devices, realtime, history, mode_config, capabilities)`. Tests can be run from the repository root using:
   `python -B -m unittest discover -s backend/algorithms/algo01/tests -v`
5. **Responsible developer:** John. I will investigate and fix bugs related to ALGO-01. CORE/OS/DB integration issues will be discussed with the corresponding developers.


**Test ownership rule:** **QA owns the test infrastructure and test code.** If you own an implementation, please fix the bugs found in your module. A passing test confirms the specified behavior only; it does not guarantee every storage operation is safe or fast.

---

## 09 | END-TO-END EXAMPLE — SSD caching recommendation

> [!NOTE]
> **HYPOTHETICAL WORKFLOW EXAMPLE:** This shows how an SSD-caching recommendation could move between components. The actual implementation is still to be agreed. QA checks each interface boundary.


**D1 User Story US-05 (verbatim):**

> As a college student with an old computer with slow storage, I want to open the GUI in order to get recommendations on which files should be moved/cached on the fastest disk.

This example follows **US-05** and illustrates an **SSD-caching recommendation**, *not* an executed cache operation. The implementation must separately address **US-04** (enable caching mode and preserve integrity) and **US-06** (explicitly enable Auto Mode).

```text
 STEP 1  [OS AGENT]         Collect supported telemetry
                     |
 STEP 2  [CORE SERVICE]     Normalize and validate fields
                     |
 STEP 3  [DATABASE]         Store samples / query history
                     |
 STEP 4  [ALGORITHM]        Evaluate caching policy
                     |
 STEP 5  [CORE SERVICE]     Return recommendations over local API
                     |
 STEP 6  [FRONTEND]         Display reason and approval options
                     |
 STEP 7  [QA / TESTS]       Validate data contracts at EVERY boundary

 ACTUAL FILE CHANGE?  Separate user approval + OS action safety gate.
```

**Questions that MUST be answered to make this real:**

- **OS Agent:** Can we measure per-file access and file location? If SSD caching is proposed, how do reads reach cached data?
- **Database:** Can we query measured file activity when available and clearly represent unavailable history?
- **Algorithm:** Which inputs are essential for a safe caching recommendation? What is the fallback when file heat cannot be measured?
- **Core / Integration:** How do we move data between modules and report errors to the UI?
- **Frontend:** How do we show the recommendation, explanation, warnings, and approval controls?
- **QA:** How do we test successful, unsupported, and safely rejected paths?

---

## 10 | PR REVIEW AND CHANGE CONTROL — Required

> [!WARNING]
> **REQUIRED:** Notify every affected consumer before merging an incompatible change. Update the contract, fixtures, and tests in the same PR or a coordinated PR set.


1. **No interface is frozen by this proposal.** Please investigate feasibility, fill in your worksheet, and discuss changes with affected consumers before implementation.
2. **Producer + impacted consumer approval** is required for the initial agreed contract. **Juan reviews testability and fixtures.**
3. For later changes in **signature, field name/type/unit, nullability, error semantics, capability flags, action behavior or HTTP route**, create a PR, update this document and fixtures, and **notify all impacted consumers in Discord BEFORE merging**.
4. If breaking, document **migration approach**, identify consumers that must update, and attach test results.
5. Distinguish **ACCEPTED** (agreed) from **IMPLEMENTED** (code exists) from **VERIFIED** (tests/evidence); use **UNSUPPORTED** when accurate.
6. Do **not** claim a copy to SSD is a functioning cache; read routing and coherency are part of the mechanism.
7. Real storage mutations require explicit authorization and safety checks. Never treat an algorithm recommendation as approval.

### 10.1 | Change and acceptance log — Fill in PR

| API ID | PR link / producer | Consumer approval | Juan test/fixture review | Result | Date |
|---|---|---|---|---|---|
| OS-01/02 | _add link / name_ | _add link / name_ | _add link / name_ | PROPOSED | pending |
| DB-01 | _add link / name_ | _add link / name_ | _add link / name_ | PROPOSED | pending |
| ALGO-01/02 | _add link / name_ | _add link / name_ | _add link / name_ | PROPOSED | pending |
| HTTP-01 | _add link / name_ | _add link / name_ | _add link / name_ | PROPOSED | pending |
| QA-01/03 | _add link / name_ | _add link / name_ | _add link / name_ | PROPOSED | pending |

---

### 10.2 | Contract acceptance checkboxes — Separate from implementation

- [ ] **TODO · OS-01/02** — Enrique + Mohan contract updates received; Shengrong + Algorithm consumer review recorded; Juan fixtures reviewed.
- [ ] **TODO · DB-01** — Sahil contract received; John/Jesslyn + Shengrong agree; Juan fixtures reviewed.
- [ ] **TODO · ALGO-01/02** — John/Jesslyn publish RAID0 and SSD-caching signatures/examples; Shengrong/OS owners/Danny review; Juan test plan recorded.
- [ ] **TODO · HTTP-01** — Shengrong publishes endpoint shapes; Danny signs off on UI needs; Juan test plan recorded.
- [ ] **TODO · QA-01/03** — Juan submits reusable test fixtures/scripts/CI draft; all relevant owners and John/Shengrong review.

**Approval PR links / date:** _Fill in after review._

---

## 11 | D2 STARTER SEQUENCE — Suggested, not official requirements

> [!NOTE]
> **PLANNING GUIDANCE ONLY:** `P0` is interface/fixture agreement; it is not a promise that risky file operations are complete in D2.


```text
   NOW                         NEXT                        LATER
   ---                         ----                        -----
  [1] Review APIs    --->  [4] Stub/mock each API  ---> [7] Hardware benches
  [2] Add fixtures   --->  [5] Run integration     ---> [8] Action dry-run
  [3] Juan adds CI   --->  [6] Dashboard demo      ---> [9] Real safe actions
```

- [ ] **TODO · TEAM** — Fill in your assigned worksheet and request any missing data from the APIs you consume.
- [ ] **TODO · SHENGRONG** — Confirm the normalization schema and transport after consumer review.
- [ ] **TODO · SAHIL** — Provide historical query examples and documented empty-history behavior.
- [ ] **TODO · JOHN + JESSLYN** — Provide one explainable recommendation fixture for each storage mode.
- [ ] **TODO · DANNY** — Connect the existing dashboard to mock API responses before switching to real data.
- [ ] **TODO · JUAN** — Add baseline contract tests and CI to detect incompatible changes in PRs.
- [ ] **TODO · TEAM** — At least one OS provides authentic device metrics for the first integration demonstration; do not claim Windows/Linux parity until validated.

---

## D1 USER STORY REVIEW | Before accepting this draft

- [ ] **TODO · JOHN + JESSLYN** — Review US-03/04/05 mapping and confirm proposed recommendation inputs without introducing a new user story.
- [ ] **TODO · DANNY + SHENGRONG** — Review US-01/02/06/07 HTTP/data flow needs against the actual D1 prototype UI.
- [ ] **TODO · JUAN** — Verify every original US-01 through US-07 has a measurable or explicitly deferred test path.

---

## SOURCE DOCUMENTS | GitHub D1 references

- [D1 planning: Q4 user stories, Q5 architecture, Q13/Q14 risks](https://github.com/csc301-2026-f/21-WSD-Team/blob/main/deliverables/D1/planning.md)
- [D1 meeting notes — Sep 26 (RAID0/SSD caching, memory caching deferred)](https://github.com/csc301-2026-f/21-WSD-Team/blob/main/deliverables/D1/minutes/pv%20cs301%2026%209.txt)
- [Existing settings prototype (SSD caching and file-level RAID0)](https://github.com/csc301-2026-f/21-WSD-Team/blob/main/frontend/html/settings.html)
- [README — current implementation is a prototype](https://github.com/csc301-2026-f/21-WSD-Team/blob/main/README.md)

**IMPORTANT — Review gates are separate:** Checking a producer task does **not** imply consumer approval or a passing test. We track consumer review and QA verification with separate checkboxes.

**Before implementation:** Please confirm feasibility with the relevant Producer and Consumer. This document is **our starting proposal**, not approval to implement an unsupported storage feature.
