
"""
StruDiv Web Application
"""

import os
import sys
import json
import yaml
from datetime import datetime
import threading
from flask import Flask, render_template, request, jsonify, session, Response

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from strudiv.scripts.pipeline import StruDivPipeline

# Load configuration from YAML file
CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "default.yaml")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    DEFAULT_CONFIG = yaml.safe_load(f)
# 确保 web_results 目录存在
WEB_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_results')
LOGS_DIR = os.path.join(WEB_RESULTS_DIR, 'logs')
RESULTS_DIR = os.path.join(WEB_RESULTS_DIR, 'results')

for dir_path in [WEB_RESULTS_DIR, LOGS_DIR, RESULTS_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
app = Flask(__name__)

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPERIMENTS_DIR = os.path.join(PROJECT_ROOT, 'experiments', 'success')

@app.route('/')
def index():
    """Welcome page"""
    return render_template('welcome.html')

@app.route('/analysis')
def analysis():
    """Main analysis page"""
    return render_template('index.html')

@app.route('/result')
def result():
    """Results page"""
    return render_template('result.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze reasoning chain for a single problem"""
    # 获取前端输入
    reasoning_chain = request.form.get('reasoning_chain', '').strip().split('\n')
    reasoning_chain = [step.strip() for step in reasoning_chain if step.strip()]
    question = request.form.get('question', '')
    
    if not reasoning_chain:
        return render_template('index.html', error='Please enter a reasoning chain')
    
    # 生成唯一标识符
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"web_{timestamp}"
    
    # 创建日志文件
    log_file = os.path.join(LOGS_DIR, f"{session_id}.log")
    result_file = os.path.join(RESULTS_DIR, f"{session_id}.json")
    
    # 加载配置
    # 加载默认配置（包含所有模型的 API 密钥）
    config = DEFAULT_CONFIG.copy()
    
    # 创建 pipeline
    pipeline = StruDivPipeline(config)
    # 直接设置 log_file 属性
    pipeline.log_file = log_file
    # 初始化日志文件
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"StruDiv Web Analysis Log - {datetime.now()}\n")
        f.write("="*50 + "\n")
    
    # 准备样本数据
    sample = {
        'id': session_id,
        'reasoning_chain': reasoning_chain,
        'question': question
    }
    def run_pipeline_async(pipeline, sample, result_file):
        try:
            result = pipeline.run(sample, batch_mode=False)

            result_data = {
                'sample': sample,
                'hallucination_analysis': result,
                'timestamp': datetime.now().isoformat(),
            }

            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            with open(pipeline.log_file, 'a') as f:
                f.write(f"[ERROR] {str(e)}\n")
                f.flush()
            
    threading.Thread(
        target=run_pipeline_async,
        args=(pipeline, sample, result_file)
    ).start()

    return jsonify({
        'success': True,
        'session_id': session_id
    })    
    
    


@app.route('/api/experiment-files')
def get_experiment_files():
    """Get list of experiment files"""
    try:
        files = []
        
        # Scan experiments directory
        if os.path.exists(EXPERIMENTS_DIR):
            for root, dirs, filenames in os.walk(EXPERIMENTS_DIR):
                for filename in filenames:
                    # 排除以 'results' 开头的文件
                    if filename.endswith('.json') and not filename.startswith('results'):
                        files.append({
                            'value': filename,
                            'label': filename
                        })
        
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/experiment-result/<filename>')
def get_experiment_result(filename):
    """Get experiment result by filename"""
    try:
        # Search for the file in experiments directory
        for root, dirs, filenames in os.walk(EXPERIMENTS_DIR):
            if filename in filenames:
                file_path = os.path.join(root, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Ensure the data has the expected structure
                if not isinstance(data, dict):
                    return jsonify({'error': 'Invalid file format'}), 400
                
                # Add default values if missing
                if 'batch_info' not in data:
                    data['batch_info'] = {
                        'dataset': 'Unknown',
                        'total_samples': 0,
                        'timestamp': datetime.now().isoformat(),
                        'config': {'model': 'Unknown'}
                    }
                
                if 'results' not in data:
                    data['results'] = []
                
                return jsonify(data)
        
        return jsonify({'error': 'File not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/log/<session_id>')
def get_log(session_id):
    """Get log content for a session"""
    log_file = os.path.join(LOGS_DIR, f"{session_id}.log")
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "Evaluation in progress. Full log will be displayed upon completion."

@app.route('/api/log-stream/<session_id>')
def stream_log(session_id):
    log_file = os.path.join(LOGS_DIR, f"{session_id}.log")
    
    def generate():
        import time
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

@app.route('/api/result/<session_id>')
def get_result(session_id):
    """Get analysis result for a session"""
    result_file = os.path.join(RESULTS_DIR, f"{session_id}.json")
    print(f"[DEBUG] Looking for: {result_file}")   # 查看控制台输出
    if os.path.exists(result_file):
        with open(result_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'Result file not found'}), 404
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)