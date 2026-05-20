# StruDiv: 面向推理幻觉的结构化步骤分析与散度一致性检测系统

StruDiv 是一个用于检测大语言模型推理链中“推理幻觉”的系统。它通过分析推理步骤的结构一致性，并利用多模型验证之间的分歧（散度）来定位问题步骤、识别幻觉类型和错误传播路径。

**核心特点**：
- 自动对推理步骤进行语义分类（Statement / Deduction / Induction / Calculation / Assumption / Conclusion / ExternalFact）
- 双模型（严格/宽松）并行验证 + 多专家散度投票机制
- 输出步骤级检测结果、风险等级、幻觉类型分析
- 支持 GSM8K、HotpotQA 以及 LLM 自生成数据集

**实验结果**（与人工标准答案对比）：
| 数据集 | 准确率 |
|--------|--------|
| HotpotQA | 95.83% |
| GSM8K   | 94.00% |
| LLM 生成 | 97.50% |

## 快速开始

### 环境要求
- Python 3.8+
- DeepSeek API 密钥，Qwen API 密钥

### 安装

```bash
git clone https://github.com/Garnett-Liang/StruDiv.git
cd StruDiv
conda create -n strudiv python=3.9.25
conda activate strudiv
pip install -r requirements.txt
```

### 配置 API 密钥
将你的 API 密钥填入 configs/default.yaml 文件中（详细配置说明见补充文档）。

### 运行示例
#### 批量处理数据集
```bash
python strudiv/run_pipeline.py --dataset gsm8k      # GSM8K
python strudiv/run_pipeline.py --dataset Hotpot_qa  # HotpotQA
python strudiv/run_pipeline.py --dataset LLM        # LLM生成数据
```

#### 交互式模式
```bash
python strudiv/run_pipeline.py
```

#### Web 界面
```bash
python strudiv/web/app.py
# 访问 http://localhost:5000
```

#### 主要结果复现
```bash
python strudiv/run_pipeline.py --dataset gsm8k      # GSM8K
python strudiv/run_pipeline.py --dataset Hotpot_qa  # HotpotQA
python strudiv/run_pipeline.py --dataset LLM        # LLM生成数据
```
分别运行上述批量处理命令即可复现三个数据集上的实验结果。详细结果分析见补充文档。

### 引用
如果您在研究中使用了 StruDiv，请引用：

bibtex
@software{Liang_StruDiv_2026,
  author = {Liang, Jiaxuan},
  title = {StruDiv: Detecting Reasoning Hallucinations through Structural Step Analysis and Divergence Consensus},
  year = {2026},
  url = {https://github.com/Garnett-Liang/StruDiv}
}

### 许可证
