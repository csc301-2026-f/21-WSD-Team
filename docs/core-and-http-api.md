# CORE

---

## 1. Overview
CORE is the integration layer of WSD. It connects OS agents, database, algorithms and frontend.
The main purpose of CORE is to provide interface for different components, normalize and pass data through normalizers and adapters, manage data collection and provide endpoints for the frontend.

---

## 2. CORE Structure
| File | Description |
| --- | --- |
| `agent_adapter.py` | Wrap Windows and Linux agent interfaces for CORE |
| `algo_adapter.py` | Wrap algorithm interfaces for CORE |
| `db_adapter.py` | Wrap database interfaces for CORE |
| `normalization.py` | Normalize raw data from OS agents |
| `service.py` | Connect all adapters and handle application logic |
| `bootstrap.py` | Initialize all components in backend |
| `collector_agent.py` | Collect data periodically |
| `http_api.py` | Define HTTP endpoints |
| `response.py` | Provide format for HTTP response |
| `demo_data.py` | Provide mocked data for demo mode |
| `frontend_routes.py` | Serve frontend files through Flask |

---

## 3. Setup
When WSD starts, “bootstrap.py” will select the agent based on the operating system, initialize the database and adapters, and create the CORE service and HTTP application.

During initialization, CORE will create a data directory if it does not exist, and generate a host_id if it does not exist.

---

## 4. Usage
CORE supports real mode and demo mode. In real mode, CORE collects real I/O data from current machine environment by OS agents and save data to database periodically. In demo mode, sample data is provided to generate recommendations for testing.

The frontend communicates with CORE through HTTP API. User can access monitoring data, historical data, recommendations, file tracking and file move functions from the frontend UI. The HTTP endpoints are defined in http_api.py

---

## 5. HTTP API
| Method | Endpoint | Description |
| --- | --- |---|
| GET | `/api/v1/devices` | Get storage device information |
| GET | `/api/v1/metrics/latest` | Get current device I/O metrics |
| GET | `/api/v1/processes/latest` | Get current process I/O metrics |
| GET | `/api/v1/processes/history` | Get historical process I/O data |
| GET | `/api/v1/recommendations` | Get saved recommendations |
| POST | `/api/v1/recommendations/refresh` | Generate recommendations |
| GET | `/api/v1/capabilities` | Get available system capabilities |
| GET | `/api/v1/files/activity/latest` | Get current file I/O activity |
| GET | `/api/v1/files/subscriptions` | Get file and folder subscriptions |
| POST | `/api/v1/files/subscriptions` | Start tracking a file or folder |
| DELETE | `/api/v1/files/subscriptions` | Stop tracking a file or folder |
| POST | `/api/v1/actions/execute` | Move file using file and destination paths or a recommendation ID |
| GET | `/api/v1/actions/<action_id>` | Get the progress and result of a movement |

<sub>*File and folder subscription management and file move execution are currently supported on Linux.

---

## 6.Non-functional Requirements
**Compatibility**: CORE supports both Windows and Linux system

**Maintainability**: Different parts are separated into modules to reduce coupling, CORE connect them by using adapters

**Reliability**: CORE will log error regardless of whether an error affects the program's execution by using the logger

**Data Consistency**: Raw data from different operating system are normalized in CORE

---

## 7. Maintenance Instruction
Since CORE uses adapters to wrap interface from different components, CORE mainly needs to change the corresponding adapter and normalization functions while the related component changes their interfaces or data formats.

Changes related to algorithm interfaces should be made in algo_adapter.py. Changes related to Windows and Linux agent interfaces should be made in agent_adapter.py, and changes related to database interfaces should be made in db_adapter.py. 
If the data formats returned by the OS agents change, the corresponding functions in normalization.py should also be updated. New application logic should be added to service.py, while new HTTP endpoints and changes to existing endpoints should be handled in http_api.py. 
Changes related to component initialization should be made in bootstrap.py.