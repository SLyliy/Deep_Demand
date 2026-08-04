# Deep Demand MVP

一句话需求澄清演示页，支持两种运行模式：

- `LLM 模式`：配置公司大模型环境变量后，前端调用 Flask 后端，再由后端调用大模型接口
- `Mock 模式`：未配置环境变量时，后端自动返回规则生成的模拟结果，页面仍可完整运行

## 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 配置环境变量

如需接入公司大模型，请在启动前配置：

```bash
export LLM_API_KEY="your_api_key"
export LLM_BASE_URL="https://your-llm-endpoint"
export LLM_MODEL="your-model-name"
```

说明：

- `LLM_API_KEY`：大模型密钥
- `LLM_BASE_URL`：OpenAI 兼容接口根地址或完整 `chat/completions` 地址
- `LLM_MODEL`：模型名

如果这 3 个变量任意一个未配置，系统会自动进入 `mock` 模式。

## 3. 启动 Flask

```bash
python3 app.py
```

默认地址：

```text
http://127.0.0.1:8000
```

## 4. 打开前端页面

浏览器访问：

```text
http://127.0.0.1:8000
```

建议不要直接双击 `index.html`，因为新版本前端会调用同源 `/api/analyze` 和 `/api/refine` 接口。

## 5. Mock 模式是否可运行

可以。

未配置任何 `LLM_*` 环境变量时：

- `POST /api/analyze` 会返回规则生成的三维判断、真实诉求猜测、建议提交版本和快速选择项
- `POST /api/refine` 会根据用户选择生成优化后的建议提交版本
- 前端页面可正常演示完整流程

## 6. 可测试输入

1. 研发改了图纸和BOM版本，采购和生产经常不知道影响哪些物料，试产时才发现版本不一致。
2. 新品上市资料销售和售后各自保存一份，政策更新后没人确认，客户沟通口径经常不一致。
3. 经销商订单签完以后，销售总要去问计划和仓库发货到哪一步，客户催了才发现交付风险。
4. 生产计划调整后，供应链要人工查SAP库存、采购在途和缺料影响，等车间来问才发现物料不够。
5. 业务看同一个订单，在SAP、MES和WMS里状态不一致，ITBP每次都要人工拉群确认口径。

## 7. 运行合成评测集

当前还没有真实业务输入时，可以先用 `eval_cases.json` 中的 ITBP 合成样例做回归评测：

```bash
python3 run_eval.py --mode fast
```

输出包含通过用例数、平均分和失败检查项。合成样例覆盖 IPD、IPMS、MTC、SD、DSTE、Supply、Manufacturing、Procurement、Quality、MBTIT，以及 PLM、ERP/SAP、SRM、MES、WMS、DMS 等常见系统。合成样例只用于建立第一版基准，拿到真实业务输入后应继续补充或替换。

快速分析结果中：

- `related_systems`：用户原话明确提到的系统。
- `candidate_systems`：根据业务域和业务对象推断出的候选系统，需要后续确认。
- `diagnosis.source_evidence`：从原话中保留的关键证据短语，用于避免诊断丢失业务现场。
