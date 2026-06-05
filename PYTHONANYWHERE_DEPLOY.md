# StruDiv — PythonAnywhere 部署指南

已注册账号：https://www.pythonanywhere.com

---

## ⚡ 极速版（5 分钟）

### 1️⃣  上传代码

**Dashboard → Files → Upload a file**，把整个项目打包成 zip 上传，然后：

```bash
# 在 Bash 终端解压
unzip StruDiv.zip -d ~/StruDiv
```

或者用 Git（推荐）：
```bash
git clone https://github.com/Garnett-Liang/StruDiv.git
```

### 2️⃣  安装依赖

```bash
cd ~/StruDiv
python3.10 -m venv venv
source venv/bin/activate
pip install flask pyyaml openai requests
```

> 你的项目所有 LLM 都走 API，**不需要 torch/transformers**，这些足够。

### 3️⃣  配置 Web App

**Dashboard → Web → Add a new web app**
- 选 **Manual configuration**
- Python 版本 **3.10**

然后在 **Code** 区域找到 **WSGI configuration file**，点进去，**全部替换**为：

```python
import sys
import os

USERNAME = "你的用户名"                          # ← 改成你的
PROJECT_HOME = f"/home/{USERNAME}/StruDiv"

if PROJECT_HOME not in sys.path:
    sys.path.append(PROJECT_HOME)

# 激活虚拟环境
activate = os.path.join(PROJECT_HOME, 'venv', 'bin', 'activate_this.py')
if os.path.exists(activate):
    exec(open(activate).read(), {'__file__': activate})

# 启动真实 Flask 应用（完整功能，非模拟版）
from strudiv.web.app import app as application
```

### 4️⃣  配置静态文件

同一页面往下翻，**Static files** 区域添加：

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/你的用户名/StruDiv/strudiv/web/static/` |

### 5️⃣  重载

点顶部绿色 **Reload** 按钮。

打开 `https://你的用户名.pythonanywhere.com` 即可访问 🎉

---

## 注意事项

- 免费版 **每分钟最多 100 次请求**，个人演示完全够用
- 后台分析线程最长运行 **60 秒**（免费版限制），长推理链可能超时
- `configs/default.yaml` 中的 API 密钥已上传到仓库，建议部署后改为环境变量读取（可选）
- 如需 HTTPS，在 Security 区域勾选 Force HTTPS

---

## 更新代码

```bash
# 本地修改后推送
cd d:/Jupyter/StruDiv
git add .
git commit -m "update"
git push

# PythonAnywhere 上拉取
cd ~/StruDiv
git pull
source venv/bin/activate
pip install -r requirements-web.txt  # 如有新依赖
# 然后去 Web 页面点 Reload
```
