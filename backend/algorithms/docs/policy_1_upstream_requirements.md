[English](#english) · [中文](#chinese)

<a id="english"></a>

# Connecting ALGO-01

CORE collects current device information from the OS agent and file activity from the OS agent or DB, then passes those records to `evaluate_raid0_policy(...)`. One call returns the recommendations needed by the display. The algorithm does not query the DB or collect activity itself.

## How CORE passes the inputs

The example below assumes CORE has already obtained the named records and evaluation time:

```python
from backend.algorithms.algo01 import evaluate_raid0_policy, PolicyInputError

try:
    recommendations = evaluate_raid0_policy(
        devices=device_records,
        realtime={"host_id": host_id, "evaluation_time_utc": evaluation_time_utc},
        history={"file_activity": file_activity_records},
        mode_config={},
        capabilities=os_capabilities,
    )
except PolicyInputError as error:
    print(error.code)  # Report the input error through CORE's error handling.
```

These requirements are for the input CORE prepares. CORE can fill existing fields using file metadata it has checked, such as adding a known size to `file_size_bytes` for the same file and device. A single OS response does not need to contain every value.

| Data | What ALGO-01 needs |
|---|---|
| Computer and devices | One `host_id`, device IDs, media types and availability. SSDs also need total/free capacity in bytes. |
| Each file | File and source-device IDs, positive file size, read/write operation counts, observation start/end times and a source label. |
| Evaluation time | A UTC timestamp in `realtime.evaluation_time_utc`, used to decide whether observations are recent. |
| OS capabilities | `file_access_metrics=True` for file monitoring. `file_move` and `file_level_pooling` may be false; advice can still be generated. |

`path`, `read_bytes` and `write_bytes` may be `null`. Unknown read/write **operation counts** cannot be used for ranking; they must not be converted to zero. Device or process totals do not describe an individual file's activity.

By default, an observation covers 60–3,600 seconds and ended within five minutes of evaluation. Several windows per file are accepted; the algorithm chooses the latest valid one, removes equivalent duplicates and skips conflicts. It does not add overlapping counts. See the [reference](policy_1_reference.md) for settings and exact rules.

For simulated activity, preserve `source="mock"` or `source="mock:<description>"`. The returned reason and conditions carry that label.

## Where the result goes

| Integration point | Information passed on |
|---|---|
| OS → CORE, Enrique / Mohan | Device records, file observations and supported capabilities. |
| DB → CORE, Sahil | Stored file observations with their original source labels and time windows. |
| CORE → algorithm, Shengrong | The five arguments shown above; the returned list feeds CORE's recommendation response. Invalid evaluation time is reported as `PolicyInputError`. |
| CORE → UI, Danny | File/device IDs, reason, approval requirement and conditions. Keep `MOCK:` visible when present. A `none` result supplies an explanation instead of a file to move. |
| Integration tests, Juan | The same input should produce the same output; check the sample and failure cases in [Examples and tests](algo01_fixtures.md), then the real collection-to-display flow. |

A `move` recommendation does not confirm that the OS can carry it out. Execution still needs approval and current checks of file identity, path compatibility, permissions and free space. ALGO-01 does not clean up files already on the SSD.

For D2, each call uses one SSD destination. Two device IDs can refer to the same storage space; the current records do not identify that relationship, so the algorithm does not combine their reported free capacity.

Start integration with a document or media file that can be moved independently. Application dependencies, whole-game relocation and anti-cheat detection are not implemented in this policy.

---

<a id="chinese"></a>

# 接入 ALGO-01

CORE 从 OS Agent 获取当前设备信息，从 OS Agent 或 DB 获取文件活动，再把这些记录交给 `evaluate_raid0_policy(...)`。调用一次即可拿到供界面展示的建议。算法本身不查询 DB，也不采集活动。

## CORE 怎样传入数据

下面的例子假定 CORE 已经拿到对应记录和评估时间：

```python
from backend.algorithms.algo01 import evaluate_raid0_policy, PolicyInputError

try:
    recommendations = evaluate_raid0_policy(
        devices=device_records,
        realtime={"host_id": host_id, "evaluation_time_utc": evaluation_time_utc},
        history={"file_activity": file_activity_records},
        mode_config={},
        capabilities=os_capabilities,
    )
except PolicyInputError as error:
    print(error.code)  # 通过 CORE 自己的错误处理报告输入问题。
```

这些要求针对 CORE 准备的输入。CORE 可以用核对过的文件元数据补齐已有字段，例如给同一个文件、同一个设备的记录补上已知的 `file_size_bytes`。一份 OS 响应不必包含所有值。

| 数据 | ALGO-01 需要什么 |
|---|---|
| 电脑和设备 | 一个 `host_id`，以及设备 ID、介质类型和可用状态；SSD 还需总容量和剩余容量，单位为字节 |
| 每个文件 | 文件 ID、来源设备 ID、正数文件大小、读写操作次数、观察起止时间和数据来源 |
| 评估时间 | `realtime.evaluation_time_utc` 中的 UTC 时间，用来判断记录是否足够新 |
| OS 能力 | `file_access_metrics=True`，表示支持文件监控。`file_move` 和 `file_level_pooling` 可以为 false，仍能生成建议 |

`path`、`read_bytes` 和 `write_bytes` 可以为 `null`。未知的读写**操作次数**无法用于排序，不能改成零。整个设备或进程的总量也不能当作某个文件的活动。

默认每条观察覆盖 60～3600 秒，结束时间距评估不超过五分钟。一个文件可以有多个窗口：算法选最新有效窗口，合并等价重复记录，遇到冲突则跳过；不累加重叠次数。设置和完整判断见[参考文档](policy_1_reference.md)。

模拟活动保留 `source="mock"` 或 `source="mock:说明"`，返回的原因和条件也会带上标记。

## 结果交给哪里

| 接入位置 | 传递什么 |
|---|---|
| OS → CORE，Enrique／Mohan | 设备记录、文件观察和支持的能力 |
| DB → CORE，Sahil | 保存的文件观察，保留原来源标记和时间窗口 |
| CORE → 算法，Shengrong | 上面的五个参数；返回列表供 CORE 的推荐响应使用。无效评估时间通过 `PolicyInputError` 报告 |
| CORE → 界面，Danny | 文件／设备 ID、原因、是否需批准和相关条件。有 `MOCK:` 时保留显示；`none` 提供无建议的解释，没有待移动文件 |
| 集成测试，Juan | 相同输入应得到相同输出；先参考[样例与测试](algo01_fixtures.md)里的正常和失败场景，再检查真实采集到展示的流程 |

`move` 建议不代表 OS 已经能执行。真正移动时仍需批准，并检查当前文件身份、路径兼容性、权限和剩余空间。ALGO-01 不清理已经在 SSD 上的文件。

D2 每轮只使用一个 SSD 目标。两个设备 ID 可能指向同一份存储空间，而现有记录无法识别这种关系，因此算法不把它们报告的剩余容量加起来使用。

首次接入可以从能独立移动的文档或媒体文件开始。本策略尚未实现应用依赖检查、整个游戏迁移和反作弊识别。
