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
- [ ] **TODO · SAHIL** — Database contracts: complete §4, provide a representative historical result and empty/unsupported response.
- [ ] **TODO · JOHN + JESSLYN** — Algorithm contracts: complete §5, review required inputs from OS and DB and provide one fixture per storage mode.
- [ ] **TODO · DANNY** — Frontend requirements: complete §6, review endpoint shapes against every current UI screen.
- [ ] **TODO · JUAN** — Testing / benchmarks / CI: complete §8, attach fixtures, runnable tests, and PR/CI evidence.

**Our progress / evidence links:** _Add PR number(s), review date(s), and any blockers here._

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
  - **Answer / evidence:** _Write here, or link a QA test matrix / PR._

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
  - **Decision / evidence:** _Write here._
- [ ] **TODO · SHENGRONG + SAHIL + JOHN/JESSLYN + JUAN** — Agree on required/optional fields, `null`, empty collections, and explicit `UNSUPPORTED` semantics.
  - **Decision / evidence:** _Write here._

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

### 03.1 | ENRIQUE — WINDOWS PRODUCER CHECKLIST

> [!NOTE]
> **IF YOU OWN THE WINDOWS AGENT:** Please complete each **TODO** below and provide evidence. **CORE + ALGO reviewers:** Confirm the data is usable. **QA:** Define test cases.


- [ ] **TODO · ENRIQUE** — Actual module path / language / callable signatures
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE** — Windows data source(s) and permissions required
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE** — Available device metrics and units / unavailable fields
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE** — Process I/O and file-level attribution feasibility
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE** — Sample cadence and measured overhead
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE** — File-level pooling and SSD cache feasibility (WinFsp or alternative)
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE** — Return shape for unsupported/error conditions
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · ENRIQUE** — One success fixture, one unsupported fixture, relevant PR
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._

### 03.2 | MOHAN — LINUX PRODUCER CHECKLIST

> [!NOTE]
> **IF YOU OWN THE LINUX AGENT:** Please complete each **TODO** below and document unsupported capabilities. **CORE + ALGO reviewers:** Confirm the data is usable. **QA:** Test fixtures and failures.


- [ ] **TODO · MOHAN** — Actual module path / language / callable signatures
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · MOHAN** — Linux data source(s), permissions and supported distributions
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · MOHAN** — Available device/process/file metrics and units
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · MOHAN** — Sample cadence and measured overhead
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · MOHAN** — mergerFS file-level placement/migration semantics and limitations
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · MOHAN** — SSD cache mechanism (FUSE/symlink/alternative), redirect + coherency
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · MOHAN** — Return shape for unsupported/error conditions
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · MOHAN** — One success fixture, one unsupported fixture, relevant PR
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._

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


- [ ] **TODO · SAHIL** — Database engine, table/schema approach, migrations
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SAHIL** — Concrete Python callable/module or service adapter
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SAHIL** — Raw vs aggregated history; filter/time-window/bucket semantics
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SAHIL** — Empty database, missing/stale data, retention, timestamp policy
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SAHIL** — Stable device/process IDs; optional file history source
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SAHIL** — Expected query cost, indexes and batch limits
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SAHIL** — Document history needed for US-02 and benchmark comparison data retention/queries for US-07; do not generate a time-saved number from device IOPS alone.
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SAHIL** — Success + empty + invalid-input examples/fixtures
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._

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

### 05.1 | JOHN + JESSLYN — ALGORITHM PRODUCER CHECKLIST

> [!IMPORTANT]
> **IF YOU OWN THE ALGORITHM:** Please complete each **TODO** below with proposed input/output behavior. **CORE + OS + UI reviewers:** Check whether you can use the result. **QA:** Cover both modes and edge cases.


- [ ] **TODO · JOHN + JESSLYN** — **RAID0** minimum *required* fields vs optional telemetry
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JOHN + JESSLYN** — **SSD caching** minimum required fields vs optional telemetry
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JOHN + JESSLYN** — Actual policy functions/heuristics and configuration keys
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JOHN + JESSLYN** — User goal translation (if adopted; do not hard-code three algorithms)
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JOHN + JESSLYN** — Missing/stale/file-level-unavailable data fallback
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JOHN + JESSLYN** — Allowed recommendation actions, constraints, reason format
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JOHN + JESSLYN** — Example recommendation for RAID0 + caching and a `none` case
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._

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


- [ ] **TODO · SHENGRONG** — Local transport/framework and bind/security model
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SHENGRONG** — How OS agent gets selected and normalized
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SHENGRONG** — Ingestion loop and/or event cadence
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SHENGRONG** — How DB / Algorithm get called (including the unresolved history route)
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SHENGRONG** — Response envelope; 4xx/5xx/error/unsupported behavior
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · SHENGRONG** — One real or mocked end-to-end JSON response + branch/PR
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._

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
- [ ] **TODO · JUAN** — **T-DB-01:** Ingestion-to-history round-trip.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-DB-02:** Empty history / unavailable file telemetry.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-ALG-01:** RAID0 algorithm contract with valid/invalid inputs.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-ALG-02:** SSD cache capacity guard.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-ALG-03:** Policy/goal change and stable output schema.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-HTTP-01:** HTTP success / empty / invalid responses.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-UI-01:** Frontend missing/unsupported data state.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-E2E-01:** End-to-end data IDs and recommendation flow.
  - **Test path / result / CI run:** _Fill in after running._
- [ ] **TODO · JUAN** — **T-ACT-01:** Preview/approval/interruption safety — LATER.
  - **Test path / result / CI run:** _Fill in after running._

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


- [ ] **TODO · JUAN** — Test framework and Python version(s)
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JUAN** — Fixtures format/schema source of truth
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JUAN** — Exactly which test cases run on every PR vs manual hardware tests
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JUAN** — Mocking approach when Windows/Linux test host is unavailable
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JUAN** — Benchmark tools/commands, workload methodology, result format
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JUAN** — CI runner/OS compatibility, commands, time budget, branch/PR
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JUAN** — Add D1 Q4 traceability test plan: US-01 live process metrics; US-02 per-app history; US-03/04 action safety; US-05 recommendation; US-06 auto-mode opt-in; US-07 evidence-based estimated time saved.
  - **Answer / evidence:** _Write here, or link fixtures/tests / PR; then check the box above._
- [ ] **TODO · JUAN** — First runnable example: validate one fixture + print pass/fail
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._
- [ ] **TODO · JUAN** — Integration failure reporting / issue template and test evidence
  - **Answer / evidence:** _Write here, or link the design / fixture / PR; then check the box above._

#### 08.4.2 | ALL PRODUCERS — Evidence Juan needs

> [!NOTE]
> **IF YOU PRODUCE AN API:** Please provide fixtures and expected outputs so QA can create meaningful automated checks.


- [ ] **TODO · ALL PRODUCERS** — At least one **valid success payload** per proposed P0 API.
- [ ] **TODO · ALL PRODUCERS** — At least one **empty/unsupported/error payload** if applicable.
- [ ] **TODO · ALL PRODUCERS** — Clearly specified units, null behavior, stable identifiers and allowed enum values.
- [ ] **TODO · ALL PRODUCERS** — A callable implementation, stub or mock adapter for automated tests.
- [ ] **TODO · ALL PRODUCERS** — A named person to investigate a failed contract or integration test.

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
