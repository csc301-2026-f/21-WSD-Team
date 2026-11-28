[English](#english) · [中文](#chinese)

<a id="english"></a>

# ALGO-01: Adaptive File Placement (D4 updated)

ALGO-01 recommends moving frequently read files from HDDs to SSDs in WSD's RAID0 mode. It uses historical file activity to predict future demand, considers access patterns, and selects a group of files that fits within the available SSD space.

## How it works

### File filtering

The algorithm starts with the latest valid activity record for each file. By default, it considers files on available HDDs with at least 0.1 reads per second and a read ratio of 80% or higher.

### Workload prediction (D4)

Different workloads benefit from different prediction methods. ALGO-01 compares three approaches:

| Method | How it works |
| --- | --- |
| Latest read rate | Uses the latest observed activity. |
| Moving average | Averages the read rate over the last five minutes. |
| Ridge regression | Learns workload patterns and predicts the average read rate for the next ten minutes. |

The Ridge model uses features such as read frequency, variance, trends, read/write ratio, active-window ratio, and available access-gap information. It uses scikit-learn's `StandardScaler` and `Ridge`.

Training samples use five minutes of activity as input and the following ten minutes as the target. The last twenty minutes of history are reserved for validation. The algorithm compares the three methods using mean absolute error (MAE) and chooses the best-performing one, preferring simpler methods in a tie. If Ridge wins, it is refitted on the full available history. Files with insufficient recent history fall back to their latest observed read rate.

### Spatial locality (D4)

Files with frequent non-sequential accesses can benefit from the lower access latency of SSDs. ALGO-01 uses the average read access gap (in bytes) to adjust each file's priority:

```text
spatial_factor = 1 + average_read_gap / (average_read_gap + 65536)
migration_score = estimated_read_rate * spatial_factor
```

The spatial factor defaults to 1 when recent gap measurements are unavailable. The resulting score estimates the relative benefit of placing a file on an SSD.

### File selection (D3–D4)

We formulate file selection as a 0/1 Knapsack problem, using file size as the weight and migration score as the value. Dynamic programming finds the best combination of files within the SSD space budget and recommendation limit.

Dominated-state pruning reduces the number of states explored. If the DP budget is exceeded, the algorithm switches to greedy selection. Each evaluation uses the SSD or NVMe drive with the largest usable space after reserves.

## Developer Guide

### Setup and testing

Use Python 3.10 or later and install the project dependencies. For standalone algorithm development, install scikit-learn and pytest in your Python environment:

```bash
python -m pip install "scikit-learn>=1.5,<2" pytest
```

From the repository root, try the existing mock example:

```bash
python -B -m backend.algorithms.algo01.demo --mock-input backend/algorithms/algo01/tests/fixtures/d2-advisory-monitoring-only.json
```

The example uses a file read 120 times in one minute and returns a labelled sample recommendation.

Run the algorithm and integration contract tests with:

```bash
python -B -m pytest backend/algorithms/algo01/tests -q -m "not benchmark"
python -m pytest tests/contract/test_algorithm_contract.py -v
```

Run the eight performance experiments separately with `python -B -m pytest backend/algorithms/algo01/tests -q -m benchmark`.

### Code structure

The main implementation is in [`backend/algorithms/algo01/`](../algo01/).

| File | Purpose |
| --- | --- |
| `raid0_policy.py` | Main recommendation pipeline |
| `inputs.py` | Input validation and policy settings |
| `candidates.py` | File filtering |
| `prediction.py` | Feature extraction, training, prediction and spatial scoring |
| `knapsack_selection.py` | Dynamic programming and state pruning |
| `greedy_selection.py` | Greedy selection and recommendation generation |
| `strategy_controller.py` | Selection strategy switching |
| `tests/` | Unit and regression tests |

Shared utilities are in [`backend/algorithms/common/`](../common/).

### Configuration

Policy settings can be changed through `mode_config`. Their defaults are defined in `inputs.py`.

| Setting | Default |
| --- | --- |
| Optimization goal | `performance` |
| Minimum read rate / read ratio | 0.1 reads/s / 80% |
| Activity window / maximum age | 60–3,600 s / 300 s |
| SSD reserve | Greater of 1 GiB and 10% of total capacity |
| Maximum recommendations | 10 |

Prediction settings are in `prediction.py`. The sampling tolerance is in `inputs.py`, and DP limits are in `knapsack_selection.py`.

| Parameter | Default |
| --- | --- |
| Activity window / history | 60 s / 60 min |
| Feature window / prediction horizon | 5 min / 10 min |
| Validation period | 20 min |
| Minimum training / validation samples | 20 / 5 |
| Ridge alpha | 1.0 |
| Sampling tolerance | 0.5 s |
| DP state / transition budget | 10,000 / 200,000 |

Training takes place during recommendation evaluation when sufficient history is available. Samples are collected across files on the same host.

### API and integration

CORE calls the algorithm through its existing interface:

```python
from backend.algorithms.algo01 import evaluate_raid0_policy

recommendations = evaluate_raid0_policy(
    devices=device_records,
    realtime={"host_id": host_id, "evaluation_time_utc": evaluation_time_utc},
    history={"file_activity": file_activity_records},
    mode_config={},
    capabilities=os_capabilities,
)
```

CORE supplies device information, the host ID and evaluation time, file activity, and platform capabilities. File monitoring requires `file_access_metrics=True`.

For prediction, provide up to one hour of consecutive 60-second file activity records with their original timestamps, read/write operation counts and file identities. The 0.5-second tolerance accommodates small sampling delays. The optional `read_average_gap` and `write_average_gap` fields supply spatial features. Mock activity is excluded from model training.

The result is a list of recommendations. A `move` action identifies a file and destination; `none` explains why no recommendation was generated. CORE and the OS backend handle approval and file migration.

## Non-Functional Requirements

- **Performance:** State pruning, bounded DP budgets and greedy fallback keep file selection manageable.
- **Reliability:** Input validation and prediction fallbacks allow the algorithm to handle incomplete or irregular telemetry.
- **Maintainability:** Separate prediction and selection modules, a stable API, and automated tests simplify future changes.
- **Safety and explainability:** Recommendations respect storage reserves and include the scoring rationale and approval requirements.

## Current limitations

Prediction quality depends on the collected history. Spatial scoring uses access-gap measurements as a locality heuristic. Each evaluation currently selects one SSD destination, and the migration score is an estimate of placement priority.

## Related documentation

- [Project README](../../../README.md)
- [CORE, OS and DB integration](policy_1_upstream_requirements.md)
- [Examples and test fixtures](algo01_fixtures.md)
- [Project API contracts](../../../docs/api-contracts.md)

---

<a id="chinese"></a>

# ALGO-01：自适应文件放置

ALGO-01 是 WSD 在 RAID0 模式下使用的文件放置推荐算法，负责筛选 HDD 上读取频繁的文件，推荐将其迁移至 SSD。算法利用历史文件活动预测未来负载，结合访问模式，在可用 SSD 容量内选择合适的文件组合。

## 算法设计

### 文件筛选

算法首先选取每个文件最新的有效活动记录。默认筛选位于可用 HDD 上、读取频率达到每秒 0.1 次且读操作占比达到 80% 的文件。

### 负载预测（D4）

不同类型的负载适合不同的预测方式。ALGO-01 比较以下三种方法：

| 方法 | 原理 |
| --- | --- |
| 最新读取频率 | 使用最近一次观测到的读取频率。 |
| 移动平均 | 计算最近五分钟的平均读取频率。 |
| Ridge 回归 | 学习历史负载特征，预测未来十分钟的平均读取频率。 |

Ridge 模型使用读取频率、方差、变化趋势、读写比例、活跃窗口比例以及可用的访问间距等特征。实现采用 scikit-learn 的 `StandardScaler` 和 `Ridge`。

每个训练样本使用五分钟的活动记录作为输入，随后十分钟的活动作为预测目标。历史数据中最近二十分钟用于验证。算法通过平均绝对误差（MAE）比较三种方法，选择表现最好的方法；误差相同时优先采用简单的方法。如果 Ridge 表现最佳，就使用全部可用历史重新训练。近期历史不足的文件回退至最新读取频率。

### 空间局部性（D4）

频繁进行非顺序访问的文件有望受益于 SSD 更低的访问延迟。ALGO-01 利用平均读取间距（单位为字节）调整文件的优先级：

```text
spatial_factor = 1 + average_read_gap / (average_read_gap + 65536)
migration_score = estimated_read_rate * spatial_factor
```

近期访问间距数据缺失时，空间因子默认为 1。最终的迁移评分用于估算文件迁移至 SSD 的相对收益。

### 文件选择（D3–D4）

我们将文件选择建模为 0/1 背包问题，以文件大小作为重量、迁移评分作为价值，通过动态规划在 SSD 容量预算和推荐数量限制内寻找最佳文件组合。

通过支配状态剪枝减少需要探索的状态数量。当计算量超过预设预算时，算法切换至贪心选择。每次评估选择扣除预留空间后可用容量最大的 SSD 或 NVMe 设备。

## 开发者指南

### 环境配置与测试

使用 Python 3.10 或更高版本并安装项目依赖。独立开发算法时，可以在 Python 环境中安装 scikit-learn 和 pytest：

```bash
python -m pip install "scikit-learn>=1.5,<2" pytest
```

在仓库根目录运行已有的模拟数据示例：

```bash
python -B -m backend.algorithms.algo01.demo --mock-input backend/algorithms/algo01/tests/fixtures/d2-advisory-monitoring-only.json
```

示例模拟了一个在一分钟内被读取 120 次的文件，并返回带有模拟数据标记的推荐。

运行算法测试和接口契约测试：

```bash
python -B -m pytest backend/algorithms/algo01/tests -q -m "not benchmark"
python -m pytest tests/contract/test_algorithm_contract.py -v
```

八个性能实验按需单独运行：`python -B -m pytest backend/algorithms/algo01/tests -q -m benchmark`。

### 代码结构

主要实现位于 [`backend/algorithms/algo01/`](../algo01/)。

| 文件 | 用途 |
| --- | --- |
| `raid0_policy.py` | 主推荐流程 |
| `inputs.py` | 输入校验与策略配置 |
| `candidates.py` | 文件筛选 |
| `prediction.py` | 特征提取、训练、预测与空间评分 |
| `knapsack_selection.py` | 动态规划与状态剪枝 |
| `greedy_selection.py` | 贪心选择与推荐生成 |
| `strategy_controller.py` | 选择策略切换 |
| `tests/` | 单元测试与回归测试 |

共享工具函数位于 [`backend/algorithms/common/`](../common/)。

### 配置参数

策略参数可以通过 `mode_config` 修改，默认值定义于 `inputs.py`。

| 配置项 | 默认值 |
| --- | --- |
| 优化目标 | `performance` |
| 最低读取频率 / 读操作占比 | 0.1 次/秒 / 80% |
| 活动窗口长度 / 记录最大年龄 | 60–3,600 秒 / 300 秒 |
| SSD 预留空间 | 1 GiB 与总容量的 10% 中的较大值 |
| 最大推荐数量 | 10 |

预测参数位于 `prediction.py`，采样容差位于 `inputs.py`，DP 计算预算位于 `knapsack_selection.py`。

| 参数 | 默认值 |
| --- | --- |
| 活动窗口 / 历史范围 | 60 秒 / 60 分钟 |
| 特征窗口 / 预测范围 | 5 分钟 / 10 分钟 |
| 验证期 | 20 分钟 |
| 最少训练样本 / 验证样本 | 20 / 5 |
| Ridge alpha | 1.0 |
| 采样容差 | 0.5 秒 |
| DP 状态数 / 转移次数预算 | 10,000 / 200,000 |

历史数据充足时，模型在推荐评估过程中训练。训练样本来自同一台主机上的多个文件。

### API 与集成

CORE 通过现有接口调用算法：

```python
from backend.algorithms.algo01 import evaluate_raid0_policy

recommendations = evaluate_raid0_policy(
    devices=device_records,
    realtime={"host_id": host_id, "evaluation_time_utc": evaluation_time_utc},
    history={"file_activity": file_activity_records},
    mode_config={},
    capabilities=os_capabilities,
)
```

CORE 提供设备信息、主机 ID、评估时间、文件活动记录和平台能力。文件监控需要 `file_access_metrics=True`。

预测功能需要最近一小时内连续的 60 秒文件活动记录，保留原始时间戳、读写操作次数及文件标识。0.5 秒的采样容差用于处理轻微调度偏差。可选字段 `read_average_gap` 和 `write_average_gap` 提供空间特征。模拟数据会被排除在模型训练之外。

接口返回推荐列表。`move` 表示建议迁移的文件与目标设备，`none` 说明未生成推荐的原因。文件迁移的批准与执行由 CORE 和 OS Backend 负责。

## 非功能性要求（NFR）

- **性能：** 通过状态剪枝、DP 计算预算和贪心回退控制文件选择的计算量。
- **可靠性：** 通过输入校验和预测回退处理不完整或不规则的监控数据。
- **可维护性：** 预测与选择模块独立，保留统一接口和自动化测试，便于后续扩展。
- **安全性与可解释性：** 推荐遵循存储预留要求，提供评分依据和批准条件。

## 当前限制

预测效果取决于采集到的历史数据。空间评分通过访问间距近似衡量局部性。目前每次评估选择一个 SSD 目标，迁移评分用于估算文件放置的优先级。

## 相关文档

- [项目 README](../../../README.md)
- [CORE、OS 和 DB 接入说明](policy_1_upstream_requirements.md)
- [样例与测试](algo01_fixtures.md)
- [项目 API 契约](../../../docs/api-contracts.md)
