# StruDiv — PythonAnywhere 部署指南

## 前提

已注册 PythonAnywhere 免费账号：https://www.pythonanywhere.com

---

## 第一步：上传代码到 PythonAnywhere

登录后，打开 **Dashboard → Files**，在 Bash 终端中执行：

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/StruDiv.git  # 或者你的仓库地址

# 如果还没推送到 GitHub，也可以直接在 Files 页面手动上传
```

> 没有 Git 仓库？也可以在本地把项目打包成 zip，然后在 PythonAnywhere 的 **Files** 页面上传并解压。

---

## 第二步：创建虚拟环境并安装依赖

打开 **Dashboard → Consoles → Bash**，执行：

```bash
# 进入项目目录
cd ~/StruDiv

# 创建虚拟环境（Python 3.10 免费版支持）
python3.10 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装 Web 依赖（轻量版，不含 torch）
pip install flask==3.1.3 pyyaml==6.0.3
```

---

## 第三步：配置 WSGI 文件

打开 **Dashboard → Web**，点击 **Add a new web app**：

1. 选择 **Manual configuration**
2. Python 版本选 **3.10**
3. 下一步完成

然后在 **Code** 区域找到 **WSGI configuration file**，点击进入编辑，**替换全部内容**为：

```python
import sys
import os

# ===== 修改为你的用户名 =====
USERNAME = "你的PythonAnywhere用户名"

# 项目路径
PROJECT_HOME = f"/home/{USERNAME}/StruDiv"
if PROJECT_HOME not in sys.path:
    sys.path.append(PROJECT_HOME)

# 激活虚拟环境
activate_this = os.path.join(PROJECT_HOME, 'venv', 'bin', 'activate_this.py')
if os.path.exists(activate_this):
    exec(open(activate_this).read(), {'__file__': activate_this})

# 导入 Flask 应用
from strudiv.web.app_pa import app as application
```

将 `YOUR_USERNAME` 改成你的 PythonAnywhere 用户名。

---

## 第四步：配置静态文件

在同一个 **Web** 页面，找到 **Static files** 区域，添加：

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/你的用户名/StruDiv/strudiv/web/static/` |

---

## 第五步：配置强制 HTTPS（可选）

在 **Web** 页面的 **Security** 区域，勾选 **Force HTTPS**。

---

## 第六步：重载网站

回到 **Web** 页面顶部，点击绿色的 **Reload** 按钮。

等待几秒，访问 `https://你的用户名.pythonanywhere.com`

你应该就能看到 StruDiv 的界面了！ 🎉

---

## 效果说明

这个部署版本使用 `app_pa.py`（轻量模拟版）：
- ✅ 所有 3 个页面完整渲染（welcome、analysis、result）
- ✅ SSE 日志流实时输出
- ✅ 分析按钮点击后模拟运行（逐行输出日志 + 生成结果）
- ✅ 实验结果页面可以查看文件
- ✅ 不依赖 torch/transformers（免费版也能装）

> 如需完整分析功能（真实 AI 调用），需要 PythonAnywhere **$5/月 付费套餐** 并安装完整依赖。

---

## 更新代码

每次修改本地代码后：

```bash
# 在本地提交
git add .
git commit -m "update"
git push

# 在 PythonAnywhere Bash 中更新
cd ~/StruDiv
git pull

# 重载网站
# 点击 Web 页面的 Reload 按钮
```
