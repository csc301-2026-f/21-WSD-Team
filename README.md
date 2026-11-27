# Wise Storage Director (WSD) — Team 21

Wise Storage Director (WSD) is a cross-platform storage management and optimization application designed to help users make better use of storage devices with different performance characteristics.

## Project Overview

Wise Storage Director (WSD) is a storage monitoring and optimization application designed to help users manage systems containing both SSDs and HDDs.

Different storage devices provide different levels of performance, yet users often lack the information needed to decide which files and workloads should benefit from faster storage.

Our project addresses this problem by monitoring disk, process, and file I/O activity, presenting performance information through a web interface, and providing recommendations for storage optimization.

**Partner Information:** WSD is a student-proposed CSC301 project without an external partner organization.

## Project Description

Many computers contain a mix of fast and slow storage devices, such as SSDs and HDDs. Users often have to manually decide where applications and files should be stored without knowing which data would benefit most from faster storage.

WSD monitors storage activity, presents information such as throughput, IOPS, latency, and workload behaviour, and provides recommendations about where data should be placed or cached.

The project aims to improve storage performance while keeping storage-management decisions understandable and controllable by the user.

## Current Features

WSD supports disk, process, and file I/O monitoring on Linux and Windows.

### US-01: Real-Time Process I/O Monitoring

- Identify running processes by name and PID.
- Monitor per-process read and write activity.
- Display updated I/O statistics through the frontend.
- Search processes by name or PID, and select a process to view its historical I/O activity.

### US-02: Historical I/O Statistics

- Collect and store I/O measurements using SQLite.
- Display historical process I/O activity.
- Visualize disk throughput and IOPS over time.

### US-03: RAID0 Mode

- On Linux, use an existing mergerfs pool to manage file placement across HDDs and SSDs.
- Move selected files between pool branches through the backend's file migration interface.

### US-05: Storage Optimization Recommendations

- Monitor file activity and analyze storage capacity. On Linux, users select files or folders to track; Windows collects file activity through ETW.
- **ALGO-01 (RAID0):** Predicts future read activity by selecting among Ridge regression, moving average, and the latest observed read rate. It considers spatial locality and uses Knapsack optimization with state pruning to select files within the available SSD capacity. Greedy selection serves as a fallback when the DP budget is exceeded.
- **ALGO-02 (SSD caching):** Generates cache recommendations using a greedy selection algorithm. CORE supports recommendation generation for both storage modes.
- Display recommended source and target devices, reasons, and constraints.

Demo mode uses clearly labelled sample activity. Real recommendations depend on file activity and available SSD/NVMe capacity. ALGO-01 can use observed activity while historical data is still being collected.

See the [ALGO-01 Developer Guide](backend/algorithms/docs/policy_1_readme.md) for algorithm details.

## Installation and Usage

Download an appropriate Linux or Windows package from [GitHub Releases](https://github.com/csc301-2026-f/21-WSD-Team/releases). Development pre-releases include both packages.

### Linux

The Linux package targets **Ubuntu 24.04 x86-64** and includes a standalone executable and installation script.

See the [Linux Installation Guide](packaging/linux/README.md) for installation, dependencies, and remote access. For RAID0 mode, prepare an existing pool using the [mergerfs Setup Guide](backend/linux/mergerfs_setup.txt).

### Windows

See the **[Windows Setup Guide](packaging/windows/README.md)** for the desktop launcher, source setup, portable builds, and screenshots. Choose **Start Monitoring** for real activity or **Start Demo** for sample data. Real monitoring requests Administrator access.

### Running WSD on Linux

After installation, choose one of the following modes.

**Real Mode — Disk and Process Monitoring**

```bash
~/.local/bin/wsd
```

Collects real disk and process I/O measurements from the Linux operating system.

**Demo Mode — Storage Recommendations**

```bash
~/.local/bin/wsd --demo
```

Uses sample file-activity data to demonstrate storage placement recommendations.

Once started, open:

**http://127.0.0.1:5000/**

Stop the current mode using `Ctrl+C` before switching modes.

## Testing the Main Features

| User Story | Mode | How to Test |
|---|---|---|
| US-01: Real-Time Process I/O | Real | Open **Disk Usage Statistics**, locate the **Application I/O** table, search by process name or PID, and observe read/write activity. |
| US-02: Historical I/O | Real | Select a process in **Application I/O** or under **Process I/O History**, and observe its historical activity. |
| US-05: Storage Recommendations | Demo | Open **Main Dashboard**, click **Refresh Recommendations**, and review the generated sample-data recommendations. |
| US-05: Storage Recommendations | Windows Real | Run WSD with Administrator access, generate file read activity on an HDD, and refresh recommendations. |
| US-05: Storage Recommendations | Linux Real | Configure a mergerfs pool for RAID0 mode, track a file or folder on the pool, generate read activity, and refresh recommendations after activity has been collected. |

For predictive recommendations, keep WSD running while it collects historical file activity. See the **[Windows Setup Guide](packaging/windows/README.md)** for startup screenshots. The **[D2 Frontend Walkthrough](deliverables/D2/WSD_TA_Frontend_Walkthrough.md)** documents the earlier D2 interface.

## System Architecture

WSD uses a modular architecture:

**OS Agent → CORE → Database / Algorithms → HTTP API → Frontend**

- **OS Agent:** Collects storage device information and I/O statistics.
- **CORE:** Coordinates communication and data processing across components.
- **Database:** Stores devices, historical I/O measurements, file subscriptions, recommendations, and file migration records using SQLite.
- **Algorithms:** Generate file placement and caching recommendations using device information and historical file activity.
- **HTTP API:** Exposes monitoring data and recommendations through Flask.
- **Frontend:** Presents device information, performance charts, process statistics, and recommendations.

For detailed component interfaces and data structures, see [API Contracts](docs/api-contracts.md).

## Current Limitations

- Linux file I/O monitoring requires users to select files or folders to track. RAID0 file placement requires an existing mergerfs pool.
- Windows supports file activity monitoring and recommendations. Recommended file moves are currently supported by the Linux backend.
- SSD caching recommendations are available through the algorithm interface; cache execution is not implemented.
- Predictive recommendations depend on the availability and quality of historical file activity.
- Physical RAID creation is outside the current implementation.

## Development and GitHub Workflow

Team development is organized using feature branches and pull requests.

Changes are reviewed before being merged into `main`. GitHub Actions runs automated Python tests on Windows and Ubuntu using Python 3.10 and 3.12, including algorithm, CORE, HTTP, database, and integration tests. Frontend tests run with `npm test`. The pipeline also runs lint and package build checks.

The CI/CD workflow in [`.github/workflows/tests.yml`](.github/workflows/tests.yml) builds Linux and Windows packages. Successful pushes to `main` publish development pre-releases; successful pushes to `release` publish release builds.

For local testing, see the [Testing Guide](docs/testing.md). The Linux real-machine test script is available at [`scripts/linux_local_test.sh`](scripts/linux_local_test.sh).

Team coordination takes place through regular meetings, GitHub Issues, and Discord.

## Developer Guide

Use the platform setup guides below to install dependencies and run the application from source. The algorithms use scikit-learn, and the Python tests use pytest; the CI workflow records the dependencies used in automated checks.

The main implementation is organized under `backend/` and `frontend/`. CORE connects the OS agents, database, algorithms, and HTTP API. When changing a shared interface, update the API documentation and the relevant contract tests. See the component guides and testing instructions below for development and maintenance.

## Non-Functional Requirements

- **Performance:** ALGO-01 uses dominated-state pruning and bounded computational budgets to control the cost of file selection.
- **Reliability:** Input validation, sampling tolerance, and adaptive prediction and selection fallbacks help the algorithm handle incomplete history and varying workloads.
- **Maintainability:** Candidate filtering, prediction, and file selection are separated into independent modules, with automated tests and a dedicated developer guide.
- **Safety:** ALGO-01 reserves SSD capacity and includes approval and execution-validation requirements in its recommendations.
- **Accessibility:** The D3 frontend introduced semantic HTML, labelled controls, keyboard navigation, and improved colour contrast. The pages tested in D3 achieved a Lighthouse accessibility score of 100.

## Documentation

- [Linux Installation Guide](packaging/linux/README.md)
- [Windows Setup Guide](packaging/windows/README.md)
- [D2 Frontend Walkthrough](deliverables/D2/WSD_TA_Frontend_Walkthrough.md)
- [API Contracts](docs/api-contracts.md)
- [D2 Iteration Review](deliverables/D2/iteration-02-review.md)
- [Individual Contributions](deliverables/D2/Individual_Contributions_Deliverable2.md)
- [D2 AI Usage Disclosure](deliverables/D2/AI_usage.md)
- [D3 Product Evolution Report](deliverables/D3/product-evolution.md)
- [D3 Individual Contributions](deliverables/D3/Individual_Contributions_Deliverable3.md)
- [D3 AI Usage Disclosure](deliverables/D3/AI_usage.md)

### User Guides

- [Linux Installation Guide](packaging/linux/README.md)
- [Windows Setup Guide](packaging/windows/README.md)
- [mergerfs Setup Guide](backend/linux/mergerfs_setup.txt)
- [D2 Frontend Walkthrough](deliverables/D2/WSD_TA_Frontend_Walkthrough.md)

### Developer Guides

- [ALGO-01: Adaptive File Placement](backend/algorithms/docs/policy_1_readme.md)
- [File I/O Monitoring Frontend Design Notes](docs/file-io-monitoring-frontend.md)
- [API Contracts](docs/api-contracts.md)
- [Testing Guide](docs/testing.md)

### Project Deliverables

- [D1 Project Planning](deliverables/D1/planning.md)
- [D2 Iteration Review](deliverables/D2/iteration-02-review.md)
- [D2 Individual Contributions](deliverables/D2/Individual_Contributions_Deliverable2.md)
- [D2 AI Usage Disclosure](deliverables/D2/AI_usage.md)
- [D3 Product Evolution Report](deliverables/D3/product-evolution.md)
- [D3 Individual Contributions](deliverables/D3/Individual_Contributions_Deliverable3.md)
- [D3 AI Usage Disclosure](deliverables/D3/AI_usage.md)
- [D4 AI Usage Disclosure](deliverables/D4/AI_usage.md)

## License

Wise Storage Director is licensed under the **GNU General Public License version 3 (GPLv3)**.

We selected GPLv3 to keep WSD open source and ensure that redistributed derivative versions preserve the freedoms to access, modify, and share the software under the same license.

See [LICENSE](LICENSE) for the complete license terms and [COPYRIGHT.md](COPYRIGHT.md) for ownership and third-party licensing.

## Team

- **John Deng:** Team Lead, Algorithm Design, and Integration
- **Shengrong Wang:** CORE and HTTP API Integration
- **Mohan Sun:** Linux Backend
- **Enrique Alvarez Habegger:** Windows Backend
- **Sahil Pathak:** Database
- **Jesslyn Perdana:** Algorithm Design
- **Danny Tran:** Frontend
- **Juan Alexander:** QA, Testing, and CI
