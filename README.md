# Wise Storage Director (WSD) — Team 21

Wise Storage Director (WSD) is a cross-platform storage management and optimization application designed to help users make better use of storage devices with different performance characteristics.

## Project Overview

Wise Storage Director (WSD) is a storage monitoring and optimization application designed to help users manage systems containing both SSDs and HDDs.

Different storage devices provide different levels of performance, yet users often lack the information needed to decide which files and workloads should benefit from faster storage.

Our project addresses this problem by monitoring disk and process I/O activity, presenting performance information through a web interface, and providing recommendations for storage optimization.

**Partner Information:** WSD is a student-proposed CSC301 project without an external partner organization.

## Project Description

Many computers contain a mix of fast and slow storage devices, such as SSDs and HDDs. Users often have to manually decide where applications and files should be stored without knowing which data would benefit most from faster storage.

WSD monitors storage activity, presents information such as throughput, IOPS, latency, and workload behaviour, and provides recommendations about where data should be placed or cached.

The project aims to improve storage performance while keeping storage-management decisions understandable and controllable by the user.

## Current Features

The development version supports real disk and process I/O monitoring on Linux and Windows.

### US-01: Real-Time Process I/O Monitoring

- Identify running processes by name and PID.
- Monitor per-process read and write activity.
- Display updated I/O statistics through the frontend.

### US-02: Historical I/O Statistics

- Collect and store I/O measurements using SQLite.
- Display historical process I/O activity.
- Visualize disk throughput and IOPS over time.

### US-05: Storage Optimization Recommendations

- Analyze file access patterns and available storage capacity.
- Generate file-placement recommendations using ALGO-01.
- Display recommended source and target devices, reasons, and constraints.
- On Windows, evaluate real file activity for eligible HDD-to-SSD moves.

Demo mode uses clearly marked sample file activity. Real recommendations depend on suitable files and available SSD space; WSD may return no suggestion. Recommendations are advisory only; WSD does not automatically migrate or cache files.

## Installation and Usage

### Linux Release (D2)

The D2 package targets **Ubuntu 24.04 x86-64 Linux** and predates the Windows support described below.

**[Download WSD v1.0.0](https://github.com/csc301-2026-f/21-WSD-Team/releases/tag/v1.0.0)**

The package includes a standalone executable and an installation script.

For complete installation instructions, system requirements, and remote-access instructions, see the **[Linux Installation Guide](packaging/linux/README.md)**.

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
| US-01: Real-Time Process I/O | Real | Open **Disk Usage Statistics**, locate the **Application I/O** table, and observe process read/write activity. |
| US-02: Historical I/O | Real | Open **Disk Usage Statistics**, select a process under **Process I/O History**, and observe its collected activity over time. |
| US-05: Storage Recommendations | Demo | Open **Main Dashboard**, click **Refresh Recommendations**, and review the generated placement suggestions. |

On Windows, the same recommendation button also evaluates real file activity in monitoring mode. A suggestion requires eligible HDD files and available SSD space.

See the **[Windows Setup Guide](packaging/windows/README.md)** for startup screenshots. The **[D2 Frontend Walkthrough](deliverables/D2/WSD_TA_Frontend_Walkthrough.md)** documents the earlier D2 interface.

## System Architecture

WSD uses a modular architecture:

**OS Agent → CORE → Database / Algorithms → HTTP API → Frontend**

- **OS Agent:** Collects storage device information and I/O statistics.
- **CORE:** Coordinates communication and data processing across components.
- **Database:** Stores devices, historical I/O measurements, and recommendations using SQLite.
- **Algorithms:** Evaluate storage activity and generate optimization recommendations.
- **HTTP API:** Exposes monitoring data and recommendations through Flask.
- **Frontend:** Presents device information, performance charts, process statistics, and recommendations.

For detailed component interfaces and data structures, see [API Contracts](docs/api-contracts.md).

## Current Limitations

Windows monitoring, process history, and file-level collection are connected to CORE and the web interface. Recommendations still depend on sufficient file data, reliable source-device identification, and available target capacity.

Linux recommendation demonstrations currently use sample file activity. Automatic file migration and executable SSD caching are not implemented.

The published D2 Linux package does not include the later Windows integration or launcher.

## Development and GitHub Workflow

Team development is organized using feature branches and pull requests.

Changes are reviewed before being merged into `main`. GitHub Actions is used to automatically run selected unit and contract tests across supported Python versions and operating systems.

Team coordination takes place through regular meetings, GitHub Issues, and Discord.

## Documentation

- [Linux Installation Guide](packaging/linux/README.md)
- [Windows Setup Guide](packaging/windows/README.md)
- [D2 Frontend Walkthrough](deliverables/D2/WSD_TA_Frontend_Walkthrough.md)
- [API Contracts](docs/api-contracts.md)
- [D2 Iteration Review](deliverables/D2/iteration-02-review.md)
- [Individual Contributions](deliverables/D2/Individual_Contributions_Deliverable2.md)
- [AI Usage Disclosure](deliverables/D2/AI_usage.md)

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
