[English](#english) · [中文](#chinese)

<a id="english"></a>

# Examples and tests

The JSON files below contain simulated inputs and saved outputs for checking ALGO-01. A fixture is a fixed sample used by a test, so the same scenario can be repeated. These files can also help CORE and UI developers see what to pass and display.

Run from the repository root, which contains `backend/`:

```powershell
python -B -m unittest discover -s backend/algorithms/algo01/tests -v
python -B -m backend.algorithms.algo01.demo --mock-input backend/algorithms/algo01/tests/fixtures/d2-advisory-monitoring-only.json
```

The package uses Python 3.10 or later and needs no third-party packages. The local suite has 41 passing checks, run with Python 3.14.

## File recommendation examples

| Input | What to check | Saved output |
|---|---|---|
| [Monitoring without move support](../algo01/tests/fixtures/d2-advisory-monitoring-only.json) | Returns advice with move/pooling capabilities false. The reason shows `MOCK:` and unconfirmed execution support. | [Result](../algo01/tests/fixtures/d2-advisory-monitoring-only-output.json) |
| [Eligible HDD file](../algo01/tests/fixtures/d2-temp-valid.json) | Shows the five arguments and a file that qualifies. | [Result](../algo01/tests/fixtures/d2-temp-valid-output.json) |
| [Empty file history](../algo01/tests/fixtures/d2-temp-none.json) | Returns one `none` result, with no file or device IDs. | [Result](../algo01/tests/fixtures/d2-temp-none-output.json) |

For each example, the returned records have the eleven Recommendation fields. A move needs approval. A `none` result has `requires_approval=False` because it proposes no action. The demo prints an outer wrapper identifying the entire example as mock data; the direct function returns only the recommendation list.

## What the checks cover

| Area | Cases |
|---|---|
| Inputs | Missing data, optional path, file size filled by CORE, unknown operation counts and unsupported monitoring. |
| Activity | Window age and duration, latest-window selection, equivalent duplicates and conflicting latest records. |
| Selection | Read frequency/share thresholds, HDD source, SSD space reserve, cumulative file sizes and the recommendation limit. |
| Results | Field names, mock labels, unconfirmed execution support, unrelated invalid records leaving valid recommendation IDs unchanged, and invalid evaluation time raising an error. |

One capacity check gives two SSD entries 5 MiB free each and two 4 MiB files, with reserve disabled. Only one file is recommended because the call uses one target. This checks that rule; it does not test detection of shared physical storage. MiB means 1,048,576 bytes.

These are local policy and sample-data checks. Real OS collection, DB queries, CORE's HTTP response, UI display and ALGO-02 need separate integration tests.

## Process examples for US-01 / US-02

These examples describe process activity, not the per-file activity used to rank migration candidates:

| File | Purpose |
|---|---|
| [metrics_process.json](../algo01/tests/fixtures/upstream_juan/metrics_process.json) | Current process activity for US-01. |
| [process-history-mock.json](../algo01/tests/fixtures/process-history-mock.json) | Process observations over time for US-02. |
| [process-history-query-proposed.json](../algo01/tests/fixtures/process-history-query-proposed.json) | Proposed DB query shape; this JSON does not implement a query function. |
| [process-history-empty.json](../algo01/tests/fixtures/process-history-empty.json) | Empty process history. |

Compatibility note: the supplied QA `none` example uses `requires_approval=True`, while this policy returns `False` for `none`. Account for that difference when choosing an expected output for integration tests.

---

<a id="chinese"></a>

# 样例与测试

下面的 JSON 文件保存了 ALGO-01 的模拟输入和预期输出。测试中把这种固定样例称为 fixture，用来重复检查同一场景。CORE 和界面开发也可以借此了解要传什么、会返回什么。

在包含 `backend/` 的仓库根目录运行：

```powershell
python -B -m unittest discover -s backend/algorithms/algo01/tests -v
python -B -m backend.algorithms.algo01.demo --mock-input backend/algorithms/algo01/tests/fixtures/d2-advisory-monitoring-only.json
```

本包需要 Python 3.10 或以上，无第三方依赖。本地使用 Python 3.14，41 项检查通过。

## 文件推荐样例

| 输入 | 检查什么 | 保存的输出 |
|---|---|---|
| [支持监控但不能迁移](../algo01/tests/fixtures/d2-advisory-monitoring-only.json) | 迁移和文件池能力为 false 仍能给建议；原因带 `MOCK:`，并说明执行支持尚未确认 | [结果](../algo01/tests/fixtures/d2-advisory-monitoring-only-output.json) |
| [符合条件的 HDD 文件](../algo01/tests/fixtures/d2-temp-valid.json) | 展示五个参数和一个可以推荐的文件 | [结果](../algo01/tests/fixtures/d2-temp-valid-output.json) |
| [空文件历史](../algo01/tests/fixtures/d2-temp-none.json) | 只返回一条 `none`，没有文件或设备 ID | [结果](../algo01/tests/fixtures/d2-temp-none-output.json) |

每条结果都包含 Recommendation 的 11 个字段。移动建议需要批准；`none` 不提出动作，所以 `requires_approval=False`。演示命令还会在外层注明整个例子使用模拟数据；直接调用函数只返回推荐列表。

## 检查覆盖什么

| 范围 | 场景 |
|---|---|
| 输入 | 缺数据、路径可空、CORE 补文件大小、操作次数未知、不支持文件监控 |
| 活动记录 | 窗口新旧与长度、最新窗口选择、等价重复和最新记录冲突 |
| 文件选择 | 读取频率与占比门槛、HDD 来源、SSD 空间预留、累计文件大小和推荐数量上限 |
| 返回结果 | 字段、模拟标识、执行支持未确认、无关坏记录不改变有效推荐 ID，以及无效评估时间抛错 |

其中一个容量测试设置了两条各报 5 MiB 剩余空间的 SSD 记录、两个 4 MiB 文件，并关闭预留。因为整轮只用一个目标，结果只推荐一个文件。它检查的是这条规则，不是共享物理存储识别。1 MiB = 1,048,576 字节。

这些是本地算法和样例检查。真实 OS 采集、DB 查询、CORE 的 HTTP 响应、界面展示和 ALGO-02 还需各自的集成测试。

## US-01／US-02 进程样例

以下样例描述进程活动，与迁移推荐需要的单文件活动不同：

| 文件 | 用途 |
|---|---|
| [metrics_process.json](../algo01/tests/fixtures/upstream_juan/metrics_process.json) | US-01 当前进程活动 |
| [process-history-mock.json](../algo01/tests/fixtures/process-history-mock.json) | US-02 随时间变化的进程记录 |
| [process-history-query-proposed.json](../algo01/tests/fixtures/process-history-query-proposed.json) | DB 查询结构草案；JSON 本身没有实现查询函数 |
| [process-history-empty.json](../algo01/tests/fixtures/process-history-empty.json) | 空进程历史 |

兼容性说明：现有 QA 的 `none` 样例使用 `requires_approval=True`，本策略的 `none` 为 `False`。选择集成测试的预期输出时，需要留意这个差异。
