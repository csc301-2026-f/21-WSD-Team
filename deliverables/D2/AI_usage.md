# AI Usage — Deliverable 2

This document outlines the extent of generative AI assistance used during the development of WSD features.

## Linux Backend (`backend/linux/`)

**Tools:** ChatGPT, Claude

**Usage:** AI was used to generate Linux terminal commands, assist with debugging, correct syntax and formatting, and suggest fixes to parts of the implementation logic. The generated commands and suggested changes were reviewed before use.

## Windows Backend (`backend/windows/`)

**Tools:** ChatGPT

**Usage:** AI was used to explore unfamiliar library APIs, generate initial ETW and WMI prototypes, and interpret runtime errors. The generated prototypes were subsequently reviewed, either rewritten manually or adapted and integrated into the larger implementation.

## Algorithm 1 (`backend/algorithms/algo01`)

**Tools:** ChatGPT, Codex

**Usage:** AI assisted in refining the independently designed algorithm through discussion and confirmation, followed by incremental code implementation based on the confirmed design. The resulting implementation was manually reviewed.

## Algorithm 2 (`backend/algorithms/algo02/`)

**Tools:** Gemini

**Usage:** AI was used as a reference for problem-solving and exploring implementation approaches when encountering difficulties. AI-generated solutions were not directly copied into the implementation.

## Backend Integration (`backend/core/bootstrap.py`, `backend/main.py`)

**Tools:** ChatGPT

**Usage:** AI was used to review and summarize existing module APIs and assist with unit test generation. The integration code was implemented manually.

## Frontend (`frontend/`)

**Tools:** ChatGPT

**Usage:** HTML and most CSS were written manually. AI was used to generate most JavaScript code and portions of the later CSS, which were integrated into the manually designed frontend layout and components.

## CORE & HTTP API (`backend/core/`)

**Tools:** ChatGPT

**Usage:** AI was used to identify and summarize changes in APIs across different components, including naming conventions and data structure differences, to assist with backend integration.

## Database (`backend/db/`)

**Tools:** ChatGPT

**Usage:** AI assisted in addressing database design challenges, including preventing process identity collisions using PID and start time, improving SQLite concurrency through Write-Ahead Logging (WAL), and designing SQL-based time bucketing for historical I/O aggregation.

## QA & Testing (`tests/`, `.github/workflows/`)

**Tools:** Claude

**Usage:** AI assisted in drafting mock JSON test fixtures based on the API contract schemas and setting up GitHub Actions workflows for automated ALGO-01 testing.

