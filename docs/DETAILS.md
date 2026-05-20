## 补充文档：docs/DETAILS.md

# StruDiv 详细文档

## 1. 系统架构详解

StruDiv 流水线包含三个主要模块：

1. **Reasoning Formatter（推理格式化）**  
   标准化输入推理链的格式（编号、步骤长度等），必要时调用 LLM 重构。

2. **Labeling Module（标签模块）**  
   两轮散度驱动的标注：
   - 第一轮：DeepSeek + MiniMax 并行标注
   - 第二轮：Qwen 冲突消解  
   输出七类标签。

3. **Reasoning Checker（推理验证模块）**  
   - 根据标签路由到对应的专用检验器（Deduction、Calculation、Induction、Assumption、Conclusion、ExternalFact）  
   - 双模型并行验证（STRICT：DeepSeek temp=0.3；LENIENT：MiniMax temp=0.9）  
   - 结果一致则直接输出；冲突则触发第二轮多专家投票  
   - 输出问题步骤定位、幻觉类型分析、风险等级。

## 2. 完整项目结构

```
StruDiv/
├── strudiv/                      # 核心模块
│   ├── run_pipeline.py           # 主运行脚本
│   ├── scripts/                  # 核心脚本
│   │   ├── pipeline.py           # 主Pipeline类
│   │   ├── reasoning_formatter.py  # 推理格式化
│   │   ├── label_steps.py          # 步骤标注
│   │   ├── reasoning_checker.py # 推理错误检测
│   │   ├── llm_caller.py           # LLM调用（DeepSeek API）
│   │   ├── test_api.py             # API测试脚本
│   └── web/                      # Web界面
│       ├── app.py                # Flask应用
│       ├── templates/            # HTML模板
│       │   ├── welcome.html
│       │   ├── index.html
│       │   └── result.html
│       └── static/               # 静态文件
│           ├── css/
│           ├── js/
│           └── workflow.png
├── configs/                      # 配置文件
│   └── default.yaml
├── data/                         # 数据集目录
│   ├── Builder/
│   ├── Hotpot_qa/
│   ├── LLM/
│   ├── demo/
│   └── gsm8k/
├── experiments/                  # 实验结果
│   ├── success/                  # 成功的实验结果
│   ├── default/
│   └── test/
├── requirements.txt              # 依赖列表
└── README.md                     # 本文档
```

## 3. 数据集格式

所有数据集使用统一的 JSON 格式：

```json
[
  {
    "id": 1,
    "question": "问题文本",
    "reasoning_chain": ["步骤1", "步骤2", "..."],
    "ground_truth": true   // 或 false, false_hard, false_easy
  }
]
```
ground_truth 取值：true（无幻觉）、false_hard（隐蔽幻觉）、false_easy（明显幻觉）。

## 4. 标签体系详细说明
标签	含义	检查重点
Statement	给定事实或问题中的已知信息	跳过检查
Deduction	必然从前序推导出的结论	逻辑必然性、量词、概念漂移、谬误等（7维度）
Induction	基于证据的泛化归纳	证据充分性、样本代表性、反例（6维度）
Calculation	数值或符号计算	算术正确性、数值使用、单位一致性（3维度，容忍微小舍入）
Assumption	临时引入的假设	新颖性、必要性、与已有信息一致性
Conclusion	最终答案	是否被前序充分支持、过度断言（5维度，允许常识省略）
ExternalFact	引入的新事实	客观真实、相关性

## 5. 第二轮专家投票机制
当双模型结论冲突时，调用以下专家模型独立投票（温度均为 0.2）：

专家角色	底层模型	判断侧重
逻辑专家	Qwen3.5	逻辑有效性、谬误、链条断裂
事实准确性专家	MiniMax	事实错误、数值/实体矛盾
推理有效性专家	DeepSeek	结论是否被前序充分支持、连贯性
最终判决为多数决，置信度 = max(YES, NO) / 3。系统还支持扩展至五位专家（含自洽性专家 Kimi、幻觉分析专家 GLM）。

## 结果分析
