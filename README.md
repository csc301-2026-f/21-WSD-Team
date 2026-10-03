# Wise Storage Director (WSD) — Team 21

Wise Storage Director (WSD) is a cross-platform storage management and optimization application designed to help users make better use of storage devices with different performance characteristics.

## Partner Intro

WSD is a student-proposed CSC301 project and does not have an external partner organization.

The project is developed by Team 21 as part of CSC301 at the University of Toronto.

## Project Description

Many computers contain a mix of fast and slow storage devices, such as SSDs and HDDs. Users often have to manually decide where applications and files should be stored without knowing which data would benefit most from faster storage.

WSD monitors storage activity, presents information such as throughput, IOPS, latency, and workload behaviour, and provides recommendations about where data should be placed or cached.

The project aims to improve storage performance while keeping storage-management decisions understandable and controllable by the user.

## Key Features

The current prototype includes:

- A dashboard showing detected storage devices and storage usage.
- Storage performance statistics such as IOPS and throughput.
- Process and workload information.
- Storage optimization recommendations.
- Configurable workload priorities.
- SSD caching and storage-pooling configuration mockups.
- Support for both simplified controls and more detailed options for advanced users.

The current D1 version is an interactive prototype and does not yet include the complete storage-management backend.

## Instructions

### Running the current prototype

The prototype can be opened locally in either of the following ways.

### Option 1: Open directly in a browser

Open:

`frontend/html/index.html`

in a modern web browser.

### Option 2: Run with Python

From the repository root, run:

```bash
python backend/main.py
```

This will open the frontend prototype in the default web browser.

No account or login is required for the current prototype.

## Development Requirements

For the current D1 prototype:

- Python 3
- A modern web browser
- Git
- Windows or Linux

The frontend currently uses:

- HTML
- CSS
- JavaScript

The backend and storage-management components are still under development. We are currently considering Python for the initial Windows and Linux backend agents.

## Deployment and GitHub Workflow

Project work is coordinated using GitHub and Discord.

Team members work on separate Git branches and submit changes through pull requests. Pull requests are reviewed by other team members before being merged into the `main` branch.

GitHub Issues are used to track important project tasks and deliverables. Discord is used for day-to-day communication, progress updates, and technical discussion.

The team also holds a weekly meeting, normally on Tuesday at 7 PM, to review progress, discuss blockers, assign work, and make design decisions.

## Coding Standards and Guidelines

Code should be readable, modular, and clearly named. Team members should avoid unnecessary duplication and document non-obvious behaviour where appropriate.

Changes should be tested before being submitted through a pull request.

## Licenses

WSD is a student-proposed project and the team currently intends to keep the project open source.

The exact open-source license has not yet been selected and will be finalized as development progresses.

## Deployed URL / Access Instructions

The D1 prototype currently runs locally and is not deployed to a public server.

To access it, clone the repository and either open:

`frontend/html/index.html`

or run:

```bash
python backend/main.py
```

## Team

- John Deng — Coordination and Algorithm Design
- Jesslyn — Algorithm Design
- Mohan — Linux Backend
- Enrique — Windows Backend
- Shengrong — Cross-platform Backend Integration
- Danny — Frontend
- Sahil — Database
- Juan — Benchmarking, Validation, QA, and DevOps
