from llm_caller import call_llm
import yaml
import os

with open("configs/default.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

prompt = "我想知道你们模型的具体型号参数 比如你是qwen  那么你是qwen3.5-flash还是plus?你是glm的话又是几点几 你是deepseek的话全称又是什么？"

# DeepSeek
try:
    print("测试 DeepSeek")
    #res = call_llm(prompt, "deepseek", config["deepseek"], 0.1)
    #print("回复:", res, "\n")
except Exception as e:
    print("失败:", e, "\n")

# Qwen
try:
    print("测试 Qwen")
    #res = call_llm(prompt, "qwen", config["qwen"], 0.1)
    #print("回复:", res, "\n")
except Exception as e:
    print("失败:", e, "\n")

# MiniMax
try:
    print("测试 MiniMax")
    #res = call_llm(prompt, "minimax", config["minimax"], 0.1)
    #print("回复:", res, "\n")
except Exception as e:
    print("失败:", e, "\n")

# GLM
try:
    print("测试 GLM")
    res = call_llm(prompt, "glm", config["glm"], 0.1)
    print("回复:", res, "\n")
except Exception as e:
    print("失败:", e, "\n")

# Kimi
try:
    print("测试 Kimi")
    res = call_llm(prompt, "kimi", config["kimi"], 0.1)
    print("回复:", res, "\n")
except Exception as e:
    print("失败:", e, "\n")

print("测试完成")