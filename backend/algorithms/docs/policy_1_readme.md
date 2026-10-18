[English](#english) · [中文](#chinese)

<a id="english"></a>

# ALGO-01: file recommendations

ALGO-01 helps WSD choose files to consider moving from a mechanical hard drive (HDD) to a solid-state drive (SSD). CORE, the backend component connecting the other modules, supplies device details and recent file activity. The algorithm returns suggestions for the dashboard to display.

The D2 policy looks for HDD files that are read often and mostly read rather than written. It ranks them by read frequency, then checks whether an SSD has enough room for each whole file. This is an initial selection rule: frequent reads alone do not establish that moving a file will improve performance. The policy does not yet distinguish random access from large sequential reads.

The interface calls this mode `raid0`. The function returns advice; it does not create a RAID array or move files. The current goal is performance. A policy for extending drive life is not implemented yet.

## Try an example

Run this from the repository root, the folder containing `backend/`:

```powershell
python -B -m backend.algorithms.algo01.demo --mock-input backend/algorithms/algo01/tests/fixtures/d2-advisory-monitoring-only.json
```

The sample describes a video on an HDD, read 120 times in 60 seconds, and an SSD with enough free space. The result is a `move` suggestion. Its reason begins with `MOCK:` because the activity is simulated. The sample also reports that file monitoring works but file moving is unavailable, so the result explains that execution support is unconfirmed.

To call the algorithm directly, run this Python example from the same folder:

```python
import json
from pathlib import Path
from backend.algorithms.algo01 import evaluate_raid0_policy, PolicyInputError

sample = Path("backend/algorithms/algo01/tests/fixtures/d2-advisory-monitoring-only.json")
data = json.loads(sample.read_text(encoding="utf-8"))
try:
    recommendations = evaluate_raid0_policy(**data)
    print(recommendations)
except PolicyInputError as error:
    print(error.code)
```

The result is a list of recommendations. `action="move"` means a file is worth considering; approval and execution checks are still required. If no file qualifies, the list contains one `action="none"` result explaining why. A missing or invalid evaluation time raises `PolicyInputError`.

## Read next

| What you need | Guide |
|---|---|
| Prepare inputs and display results | [CORE, OS and DB integration](policy_1_upstream_requirements.md) |
| Look up rules, settings, fields or functions | [Reference](policy_1_reference.md) |
| Reuse helpers in ALGO-02 | [Shared helpers for Jesslyn](policy_1_jesslyn_reuse.md) |
| Run tests and inspect sample data | [Examples and tests](algo01_fixtures.md) |
| Check the status of model-based selection | [Policy learning](policy_1_learning.md) |

## D2 integration progress

| User story | What this package provides | Remaining integration |
|---|---|---|
| US-01: current process activity | Process sample data and checks. This story does not call the file recommendation function. | OS process collection, CORE's API and the process display. |
| US-02: past process activity | Process history and query examples. The proposed DB name `query_process_history(...)` is not a function in this package. | DB history queries and the CORE/UI connection. |
| US-05: file recommendations | `evaluate_raid0_policy(...)` returns recommendations in one call. CORE does not need to call the internal scoring functions. | CORE supplies the inputs and handles errors; DB supplies history; the UI displays the result. The complete flow still needs integration testing. Jesslyn's cache policy is separate. |

The local suite contains 41 passing checks using simulated data. The complete OS → DB/CORE → dashboard flow has not been verified.

For a first real-data example, use an ordinary file that can be handled on its own, such as a document, movie, music track or short video. Run the sample first, then replace its records with observations from one computer. Installed applications and games may depend on other files or fixed paths; this policy does not check those dependencies or detect anti-cheat software.

---

<a id="chinese"></a>

# ALGO-01：文件推荐

ALGO-01 帮助 WSD 筛选值得从机械硬盘（HDD）迁往固态硬盘（SSD）的文件。CORE 是后端里连接各模块的部分，负责提供设备信息和最近的文件活动；算法返回建议，供界面展示。

D2 的判断是：先找出 HDD 上读得频繁、读多写少的文件，按读取频率排序，再逐个检查 SSD 是否放得下整个文件。这是一条初步筛选规则：读得频繁并不等于移动后一定更快。目前还不能区分随机访问和大块连续读取。

接口把这个模式称为 `raid0`。函数只返回建议，不创建 RAID 阵列，也不移动文件。目前实现的是性能目标，延长硬盘寿命的策略尚未实现。

## 先跑一个例子

在包含 `backend/` 的仓库根目录运行：

```powershell
python -B -m backend.algorithms.algo01.demo --mock-input backend/algorithms/algo01/tests/fixtures/d2-advisory-monitoring-only.json
```

样例描述了 HDD 上的一个视频：60 秒内读了 120 次，SSD 也有足够空间。返回的 `move` 表示建议移动。因为活动是模拟的，原因以 `MOCK:` 开头。样例还设置了“支持文件监控，但不能移动文件”，所以结果会说明执行支持尚未确认。

要直接调用算法，可以在同一目录运行下面的 Python 例子：

```python
import json
from pathlib import Path
from backend.algorithms.algo01 import evaluate_raid0_policy, PolicyInputError

sample = Path("backend/algorithms/algo01/tests/fixtures/d2-advisory-monitoring-only.json")
data = json.loads(sample.read_text(encoding="utf-8"))
try:
    recommendations = evaluate_raid0_policy(**data)
    print(recommendations)
except PolicyInputError as error:
    print(error.code)
```

返回值是推荐列表。`action="move"` 表示这个文件值得考虑，仍需批准和执行前检查。没有合适文件时，列表只有一条 `action="none"`，说明原因。评估时间缺失或无效时，函数抛出 `PolicyInputError`。

## 接下来读哪里

| 要做什么 | 文档 |
|---|---|
| 准备输入、展示结果 | [CORE、OS 和 DB 接入说明](policy_1_upstream_requirements.md) |
| 查规则、设置、字段或函数 | [参考文档](policy_1_reference.md) |
| 在 ALGO-02 中复用辅助函数 | [给 Jesslyn 的复用说明](policy_1_jesslyn_reuse.md) |
| 跑测试、看样例 | [样例与测试](algo01_fixtures.md) |
| 了解模型选文件的开发状态 | [策略学习](policy_1_learning.md) |

## D2 接入进度

| 用户故事 | 本包提供什么 | 还需接通什么 |
|---|---|---|
| US-01：当前进程活动 | 进程样例和检查；这个故事不调用文件推荐函数 | OS 进程采集、CORE 接口和进程展示页面 |
| US-02：历史进程活动 | 进程历史和查询样例；`query_process_history(...)` 是 DB 接口草案名，不是本包里的函数 | DB 历史查询，以及 CORE 与界面的连接 |
| US-05：文件推荐 | 调用一次 `evaluate_raid0_policy(...)` 即可拿到建议，CORE 无需逐个调用内部评分函数 | CORE 提供输入并处理错误，DB 提供历史，界面展示结果；完整流程还需集成测试。Jesslyn 的缓存策略是另一部分 |

目前 41 项本地检查通过，使用的是模拟数据。OS → DB／CORE → 界面的完整流程尚未验证。

首次接真实数据时，可以先选一个能独立处理的普通文件，例如文档、电影、音乐或短视频。先运行样例，再换成同一台电脑的实际记录。已安装应用和游戏可能依赖其他文件或固定路径；本策略尚不检查这些依赖，也不识别反作弊软件。
