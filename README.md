# StruDiv: Detecting Reasoning Hallucinations through Structural Step Analysis and Divergence Consensus

## 项目概述

StruDiv 是一个用于理解和检测推理幻觉的系统，通过分析推理结构和分歧来识别推理过程中的问题。系统接收来源不受限、正确性未知的现成推理链作为输入，输出各推理步骤的合理性判断结果、推理过程中可能存在的幻觉、错误步骤定位，以及幻觉类型与错误传播路径的结构化分析。

### 核心价值

- **结构分析**：深入分析推理链的结构，识别不同类型的推理步骤
- **分歧检测**：通过双模型验证和专家验证来识别潜在的幻觉
- **步骤级分析**：对每个推理步骤进行语义标注和针对性检查
- **结构化输出**：提供面向诊断的结构化结果，而非简单的正确性判断
- **API集成**：使用DeepSeek API进行推理验证，无需本地模型部署

## 系统架构

StruDiv Pipeline 包含三个主要模块：

### 1. Reasoning Formatter（推理格式化）
- 标准化推理链格式，确保一致的结构
- 处理输入的推理步骤，为后续分析做准备

### 2. Labeling Module（标签模块）
- 自动为每个推理步骤添加标签
- **统一标签集**：Statement / Deduction / Induction / Calculation / Assumption / Conclusion / ExternalFact
- 使用LLM对每个推理步骤进行分类

### 3. Reasoning Checker（推理验证模块）
- 针对不同标签类型进行针对性检查
- **跳过Statement步骤的检查**（它们是给定的已知事实）
- 采用双模型验证（STRICT/LENIENT模式）和专家验证流程
- 输出问题步骤定位和幻觉类型分析

## Pipeline 流程

### Stage 0: Reasoning Formatting（推理格式化）
- 标准化推理步骤格式
- 处理输入的推理链，确保格式一致

### Stage 1: Step Labeling（步骤标注）
- 输入：格式化后的推理链
- 输出：步骤标签序列
- 使用LLM对每个推理步骤进行分类
- 采用两轮分类和冲突验证机制，提高标签准确性

### Stage 2: Reasoning Analysis（推理分析）
- 检查推理步骤的逻辑一致性与合理性
- 针对不同标签类型进行针对性检查
- 跳过Statement步骤（它们是给定的已知事实）
- 采用双模型验证（STRICT/LENIENT模式）和专家验证流程
- 输出：
  1. 问题步骤定位
  2. 风险等级评估
  3. 详细的验证结果分析

## 数据集

### 支持的数据集

| 数据集 | 推理类型 | 状态 |
|--------|----------|------|
| **GSM8K** | 数学计算推理 | ✅ 推荐 |
| **Hotpot_qa** | 问答推理 | ✅ 推荐 |
| **Builder** | 通用推理 | ✅ 推荐 |
| **demo** | 示例推理 | ✅ 可选 |
| **LLM** | LLM生成推理 | ✅ 可选 |

### 数据集结构

项目中的数据集存储在 `data/` 目录下，每个数据集包含：
- `reasoning_chains.json`：推理链数据
- 其他辅助文件（如原始问题数据）

### 数据格式

所有数据集都使用统一的JSON格式：

```json
[
  {
    "id": 1,
    "question": "问题文本",
    "reasoning_chain": [
      "推理步骤1",
      "推理步骤2",
      "推理步骤3"
    ],
    "ground_truth": true  // 或 false, false_hard, false_easy等
  }
]
```

## 安装与使用

### 环境要求

- Python 3.8+
- DeepSeek API密钥（用于推理验证）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置DeepSeek API密钥

有三种方式设置API密钥：

1. **环境变量**：设置 `DEEPSEEK_API_KEY` 环境变量
2. **命令行参数**：使用 `--api-key` 参数传入
3. **交互式输入**：在交互式模式下根据提示输入

### 命令行使用

#### 批量处理数据集

```bash
# 使用GSM8K数据集
python strudiv/run_pipeline.py --dataset gsm8k --model deepseek-api --api-key YOUR_API_KEY

# 使用Hotpot_qa数据集
python strudiv/run_pipeline.py --dataset Hotpot_qa --model deepseek-api --api-key YOUR_API_KEY
```

#### 交互式模式

```bash
# 启动交互式模式
python strudiv/run_pipeline.py

# 系统会自动扫描data目录下的所有数据集并提供选择
# 当选择deepseek-api模型时，会提示输入API密钥
```

### Web界面使用

StruDiv 提供了用户友好的Web界面，用于交互式推理链分析。

#### 启动Web界面

```bash
# 启动Flask应用
python strudiv/web/app.py
```

然后在浏览器中访问：http://localhost:5000

#### Web界面功能

- **推理链输入**：支持多行文本输入，每行一个推理步骤
- **问题输入**：支持输入原始问题，帮助更好地理解推理上下文
- **模型选择**：支持DeepSeek API
- **实时日志**：显示分析过程的实时日志
- **详细分析**：显示完整的推理链分析结果，包括：
  - 步骤标签分布
  - 推理验证结果
  - 问题步骤识别
  - 风险等级评估

## 标签类型说明

| 标签类型 | 说明 | 示例 |
|---------|-----|------|
| **Statement** | 陈述前提或已知信息（客观前提） | "All researchers who publish papers attend conferences" |
| **Deduction** | 从前提推导出结论 | "Therefore, some AI researchers attend conferences" |
| **Induction** | 从具体案例归纳一般规律 | 从多个例子推导出一般规则 |
| **Calculation** | 执行数学计算 | "2 × 18 = 36" |
| **Assumption** | 引入新假设 | "Assuming the data is accurate..." |
| **Conclusion** | 最终答案或总结 | "Final Answer: 39 yuan" |
| **ExternalFact** | 引入外部事实 | "According to recent studies..." |

## 推理验证流程

StruDiv 采用先进的双模型验证和专家验证流程，确保推理分析的准确性：

### 第一轮验证：双模型分析
- **STRICT模式**（temperature=0.3）：严格的逻辑验证
- **LENIENT模式**（temperature=0.9）：宽松的实践推理评估
- 如果两轮结果一致，直接采用该结果
- 如果两轮结果不一致，进入第二轮专家验证

### 第二轮验证：专家验证
- **逻辑专家**：评估推理的逻辑一致性
- **事实专家**：评估推理的事实准确性
- **推理专家**：评估推理的有效性
- 根据专家投票确定最终结果

## 项目结构

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

## 系统设计理念

### 1. 推理链作为诊断对象

系统不再生成推理，而是接收来源不受限、正确性未知的现成推理链作为输入，最终输出为：
- 各推理步骤的合理性判断结果
- 推理过程中可能存在的幻觉、错误步骤定位
- 幻觉类型与错误传播路径的结构化分析

### 2. 步骤级针对性检查

- 每个推理步骤首先被赋予明确的语义角色标签
- 针对不同标签，系统预先设计对应的验证检查点
- LLM的作用被限定为：根据给定检查点，识别是否存在对应的违规或高风险行为

### 3. 客观前提保护机制

- 系统自动识别客观前提（给定的已知事实）
- 客观前提自动标记为`Statement`
- **客观前提不进行幻觉检查**（避免误报）

### 4. 结构化输出

输出面向诊断的结构化结果，包括：
- 推理链中潜在幻觉或错误步骤的定位
- 不同类型幻觉在推理结构中的分布特征
- 推理错误的传播关系与影响范围

### 5. 多模型验证

- 采用双模型验证（STRICT/LENIENT模式）提高检测准确性
- 引入专家验证机制解决模型分歧
- 综合多维度评估结果，提高系统的可靠性

## 实验与评估

### 评估指标

- **问题检测率**：正确识别问题步骤的比例
- **误报率**：将正常步骤误判为问题的比例
- **风险等级准确性**：风险等级评估的准确性
- **验证一致性**：不同验证模式之间的一致性

### 实验设置

1. **不同数据集的推理行为差异**：GSM8K vs Hotpot_qa vs Builder
2. **验证流程效果**：双模型验证 vs 专家验证
3. **客观前提保护效果**：验证Statement步骤不被误判为问题

## 故障排除

### 常见问题

1. **API调用失败**
   - 确保DeepSeek API密钥正确
   - 检查网络连接
   - 查看API调用频率限制

2. **路径错误**
   - 确保从项目根目录运行脚本
   - 检查数据文件路径是否正确

3. **编码问题**
   - 确保使用UTF-8编码的文件
   - 在Windows上可能需要设置控制台编码

### 性能优化

- **减少推理链长度**：过长的推理链会增加分析时间
- **批量处理**：使用批量处理模式提高效率
- **合理设置API调用频率**：避免触发API限制

## 开发说明

### 本地开发

1. 克隆仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 运行测试：`python strudiv/run_pipeline.py --dataset demo --model deepseek-api --api-key YOUR_API_KEY`

### 自定义配置

可以通过修改`configs/default.yaml`来自定义：
- 输出目录

## 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 许可证

本项目采用Apache-2.0许可证。

## 引用

如果使用本项目，请引用：

```bibtex
@misc{strudiv2024,
  title={StruDiv: Understanding and Detecting Reasoning Hallucinations through Structure and Divergence},
  author={Your Name},
  year={2024},
  url={https://github.com/your-repo/strudiv}
}
```