"""
StruDiv Web Application — PythonAnywhere 兼容版
保留所有前端页面和交互，分析过程模拟运行
"""

import os
import json
import yaml
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

LOGS_DIR = os.path.join(BASE_DIR, 'web_results', 'logs')
RESULTS_DIR = os.path.join(BASE_DIR, 'web_results', 'results')
EXPERIMENTS_DIR = os.path.join(BASE_DIR, '..', '..', 'experiments', 'success')

for d in [LOGS_DIR, RESULTS_DIR]:
    os.makedirs(d, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = 'strudiv-secret-key-pa'


# ---------------------------------------------------------------------------
# 路由：页面
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('welcome.html')


@app.route('/analysis')
def analysis():
    return render_template('index.html')


@app.route('/result')
def result():
    return render_template('result.html')


# ---------------------------------------------------------------------------
# 路由：API — 分析请求（模拟版本）
# ---------------------------------------------------------------------------
@app.route('/analyze', methods=['POST'])
def analyze():
    reasoning_chain = request.form.get('reasoning_chain', '').strip().split('\n')
    reasoning_chain = [s.strip() for s in reasoning_chain if s.strip()]
    question = request.form.get('question', '')

    if not reasoning_chain:
        return jsonify({'error': '请输入推理链'}), 400

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"web_{timestamp}"

    log_file = os.path.join(LOGS_DIR, f"{session_id}.log")
    result_file = os.path.join(RESULTS_DIR, f"{session_id}.json")

    # 初始化日志
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"StruDiv Analysis Log - {datetime.now()}\n{'='*50}\n")
        f.write("[INFO] Pipeline initializing...\n")
        f.flush()

    # 模拟分析过程（后台线程）
    def run_mock_analysis(chain, q_text, lf, rf):
        import time
        labels_pool = ['Statement', 'Deduction', 'Conclusion', 'Premise', 'Inference']
        issues_pool = [
            'Jump in logic: conclusion does not follow from premises',
            'Missing intermediate step in deductive chain',
            'Potential contradiction with earlier statement',
            'Unsupported generalization from limited evidence',
            'Circular reasoning detected',
        ]

        # 模拟逐步分析
        for i, step in enumerate(chain):
            time.sleep(0.6)
            with open(lf, 'a', encoding='utf-8') as f:
                f.write(f"[STEP {i+1}/{len(chain)}] Analyzing: {step[:60]}...\n")
                f.flush()

        # 写入完成标志
        with open(lf, 'a', encoding='utf-8') as f:
            f.write("[INFO] Analysis complete.\n")
            f.write("[COMPLETE]\n")
            f.flush()

        # 模拟结果
        mock_result = {
            'sample': {
                'reasoning_chain': chain,
                'question': q_text,
                'id': rf.replace('.json', '').split('_')[-1]
            },
            'hallucination_analysis': {
                'issues_count': len(chain),
                'risk_level': 'Medium' if len(chain) > 3 else 'Low',
                'sample_risk_level': 'Medium' if len(chain) > 3 else 'Low',
                'total_risk_score': round(len(chain) * 12.5 + 5, 2),
                'labels': [labels_pool[i % len(labels_pool)] for i in range(len(chain))],
                'reasoning': chain,
                'problematic_steps': [
                    {
                        'step_index': i,
                        'label': labels_pool[i % len(labels_pool)],
                        'issues': [issues_pool[i % len(issues_pool)]]
                    }
                    for i in range(min(2, len(chain)))
                ],
                'error_types': {
                    'Logical Gap': ['Step 1 → Step 2 missing intermediate connection'],
                    'Unsupported Claim': ['Claim requires external validation']
                } if len(chain) >= 2 else {}
            },
            'timestamp': datetime.now().isoformat()
        }

        with open(rf, 'w', encoding='utf-8') as f:
            json.dump(mock_result, f, indent=2, ensure_ascii=False)

    threading.Thread(
        target=run_mock_analysis,
        args=(reasoning_chain, question, log_file, result_file)
    ).start()

    return jsonify({'success': True, 'session_id': session_id})


# ---------------------------------------------------------------------------
# 路由：SSE 日志流
# ---------------------------------------------------------------------------
@app.route('/api/log-stream/<session_id>')
def stream_log(session_id):
    log_file = os.path.join(LOGS_DIR, f"{session_id}.log")

    def generate():
        last_pos = 0
        while True:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    f.seek(last_pos)
                    new_data = f.read()
                    if new_data:
                        last_pos = f.tell()
                        for line in new_data.splitlines():
                            yield f"data: {line}\n"
                        yield "\n"
                    if "[COMPLETE]" in new_data or "[ERROR]" in new_data:
                        yield "data: [STREAM END]\n\n"
                        break
            time.sleep(0.2)

    return Response(generate(), mimetype='text/event-stream')


# ---------------------------------------------------------------------------
# 路由：获取分析结果
# ---------------------------------------------------------------------------
@app.route('/api/result/<session_id>')
def get_result(session_id):
    rf = os.path.join(RESULTS_DIR, f"{session_id}.json")
    if os.path.exists(rf):
        with open(rf, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'Result not ready'}), 404


# ---------------------------------------------------------------------------
# 路由：实验文件列表 & 结果
# ---------------------------------------------------------------------------
@app.route('/api/experiment-files')
def get_experiment_files():
    files = []
    if os.path.exists(EXPERIMENTS_DIR):
        for root, _, filenames in os.walk(EXPERIMENTS_DIR):
            for fn in filenames:
                if fn.endswith('.json') and not fn.startswith('results'):
                    files.append({'value': fn, 'label': fn})
    return jsonify(files)


@app.route('/api/experiment-result/<filename>')
def get_experiment_result(filename):
    for root, _, filenames in os.walk(EXPERIMENTS_DIR):
        if filename in filenames:
            fp = os.path.join(root, filename)
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'batch_info' not in data:
                data['batch_info'] = {
                    'dataset': 'Unknown', 'total_samples': 0,
                    'timestamp': datetime.now().isoformat(), 'config': {'model': 'Unknown'}
                }
            if 'results' not in data:
                data['results'] = []
            return jsonify(data)
    return jsonify({'error': 'File not found'}), 404


@app.route('/api/log/<session_id>')
def get_log(session_id):
    lf = os.path.join(LOGS_DIR, f"{session_id}.log")
    if os.path.exists(lf):
        with open(lf, 'r', encoding='utf-8') as f:
            return f.read()
    return "Analysis in progress..."


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
