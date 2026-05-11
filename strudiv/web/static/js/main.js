// AutoLabel Web Interface JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Form validation
    const form = document.getElementById('analysisForm');
    const reasoningTextarea = document.getElementById('reasoning_chain');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    // File loading functionality
    const experimentFileSelect = document.getElementById('experimentFile');
    const loadFileBtn = document.getElementById('loadFileBtn');

    // Load experiment files on page load only if elements exist
    if (experimentFileSelect && loadFileBtn) {
        loadExperimentFiles();
    }

    // SSE 流式日志连接对象（替换原来的轮询）
    let eventSource = null;

    // Auto-resize textarea
    reasoningTextarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 300) + 'px';
    });


    // Form submission
    form.addEventListener('submit', function(e) {
        // 核心：阻止表单默认提交（禁止刷新）
        e.preventDefault();

        const reasoningText = reasoningTextarea.value.trim();
        const lines = reasoningText.split('\n').filter(line => line.trim());

        if (lines.length < 2) {
            showToast('Please enter at least 2 reasoning steps', 'error');
            return;
        }

        // 显示日志区域
        const analysisLogSection = document.getElementById('analysisLogSection');
        if (analysisLogSection) analysisLogSection.style.display = 'block';

        // 按钮禁用
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

        const formData = new FormData(form);

        // AJAX提交，不刷新页面
        fetch(form.action, {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            
            // 获取后端真实的 session_id
            const realSessionId = data.session_id;
            sessionStorage.setItem('sessionId', realSessionId);
            
            // ✅ 启动 SSE 实时流式日志（无轮询，真正实时）
            loadLog(realSessionId);
            

        })
        .catch(err => {
            showToast(err.message, 'error');
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Reasoning Chain';
        });
    });
    

    function loadLog(sessionId) {
        if (!sessionId) return;

        if (eventSource) {
            eventSource.close();
        }

        const logContent = document.getElementById('logContent');
        logContent.innerHTML = '';

        eventSource = new EventSource(`/api/log-stream/${sessionId}`);

        let pre = document.createElement('pre');
        logContent.appendChild(pre);

        eventSource.onopen = function() {
            console.log("SSE connected");
        };

        eventSource.onmessage = function(e) {
            if (e.data === "[STREAM END]") {
                eventSource.close();
                const sessionId = sessionStorage.getItem('sessionId');
                if (sessionId) {
                    loadAnalysisResult(sessionId);
                }
                return;
            }

            pre.textContent += e.data + "\n";
            logContent.scrollTop = logContent.scrollHeight;
        };

        eventSource.onerror = function() {
            console.error("SSE error");
            eventSource.close();
        };
    }

    // Check if we have a session ID from URL (after redirect)
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    if (sessionId) {
        // Store session ID in sessionStorage
        sessionStorage.setItem('sessionId', sessionId);
        
        // Show log section
        const analysisLogSection = document.getElementById('analysisLogSection');
        if (analysisLogSection) {
            analysisLogSection.style.display = 'block';
        }
        
        // ✅ 使用 SSE 加载日志
        loadLog(sessionId);
        
        // Load and display analysis result
        loadAnalysisResult(sessionId);
    }
    
// Load analysis result function 
    function loadAnalysisResult(sessionId) {
        if (!sessionId) return;
        
        fetch(`/api/result/${sessionId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                
                // 获取外层 hallucination_analysis
                const outerHA = data.hallucination_analysis || {};
                // 获取内层（如果存在）
                const innerHA = outerHA.hallucination_analysis || {};
                const hasNesting = innerHA && Object.keys(innerHA).length > 0;
                
                // 基础信息优先取外层
                const issuesCount = outerHA.issues_count ?? innerHA.issues_count ?? 0;
                const riskLevel = outerHA.risk_level || outerHA.sample_risk_level || innerHA.sample_risk_level || 'Unknown';
                const totalRiskScore = outerHA.total_risk_score ?? innerHA.total_risk_score ?? 0;
                const labels = outerHA.labels || [];
                const reasoning = outerHA.reasoning || data.sample?.reasoning_chain || [];
                
                // 创建结果显示区域
                const resultSection = document.createElement('div');
                resultSection.id = 'analysisResultSection';
                resultSection.className = 'mt-4 p-4 border rounded bg-light';
                
                let html = `
                    <h5><i class="fas fa-chart-bar"></i> Analysis Result</h5>
                    <div class="mb-3">
                        <strong>Model:</strong> ${data.model || 'N/A'}<br>
                        <strong>Timestamp:</strong> ${data.timestamp ? formatTimestamp(data.timestamp) : 'N/A'}<br>
                        <strong>Issues Found:</strong> ${issuesCount}<br>
                        <strong>Risk Level:</strong> <span class="badge bg-${getRiskColor(riskLevel)}">${riskLevel}</span><br>
                        <strong>Total Risk Score:</strong> ${totalRiskScore.toFixed(2)}
                    </div>
                `;
                
                // 显示推理链 + 标签
                if (reasoning && Array.isArray(reasoning) && reasoning.length) {
                    html += `
                        <div class="mt-3">
                            <strong>Reasoning Chain:</strong>
                            <ol class="list-group list-group-numbered">
                    `;
                    reasoning.forEach((step, index) => {
                        const label = labels[index] || 'Unknown';
                        let cleanStep = step.replace(/^"|",?$/g, '');
                        html += `<li class="list-group-item">${cleanStep || ''} <span class="badge bg-secondary float-end">${label}</span></li>`;
                    });
                    html += `</ol></div>`;
                }
                
                // 获取错误详情来源
                const detailSource = hasNesting ? innerHA : outerHA;
                
                // 显示 error_types（问题原因分析）
                if (detailSource.error_types && Object.keys(detailSource.error_types).length > 0) {
                    html += `
                        <div class="mt-3">
                            <strong><i class="fas fa-exclamation-triangle"></i> Detailed Issue Analysis (Error Types):</strong>
                            <ul class="list-group mt-2">
                    `;
                    for (const [label, errors] of Object.entries(detailSource.error_types)) {
                        if (errors && errors.length) {
                            const errorList = errors.map(err => {
                                if (typeof err === 'string') return err;
                                return err.message || JSON.stringify(err);
                            }).join('<br>');
                            html += `<li class="list-group-item"><strong>${label}:</strong><br>${errorList}</li>`;
                        }
                    }
                    html += `</ul></div>`;
                }
                
                // 显示 problematic steps
                if (detailSource.problematic_steps && Array.isArray(detailSource.problematic_steps)) {
                    const stepsWithIssues = detailSource.problematic_steps.filter(step => step?.issues && step.issues.length > 0);
                    if (stepsWithIssues.length > 0) {
                        html += `
                            <div class="mt-3">
                                <strong>Diagnosis (Problematic Steps):</strong>
                                <ul class="list-group">
                        `;
                        stepsWithIssues.forEach((step, index) => {
                            if (!step) return;
                            let issueHtml = '<ul class="mt-1">';
                            step.issues.forEach(issue => { issueHtml += `<li>${issue}</li>`; });
                            issueHtml += '</ul>';
                            html += `
                                <li class="list-group-item list-group-item-danger">
                                    Step ${step.step_index || (index + 1)} (${step.label || 'Unknown'}): Issues found (${step.issues.length})
                                    ${issueHtml}
                                </li>
                            `;
                        });
                        html += `</ul></div>`;
                    }
                } else if (detailSource.step_verification_results && Array.isArray(detailSource.step_verification_results)) {
                    const stepsWithIssues = detailSource.step_verification_results.filter(step => step.issues && step.issues.length > 0);
                    if (stepsWithIssues.length > 0) {
                        html += `
                            <div class="mt-3">
                                <strong>Diagnosis (Issues from Verification):</strong>
                                <ul class="list-group">
                        `;
                        stepsWithIssues.forEach((step, idx) => {
                            let issueHtml = '<ul class="mt-1">';
                            step.issues.forEach(issue => { issueHtml += `<li>${issue}</li>`; });
                            issueHtml += '</ul>';
                            html += `
                                <li class="list-group-item list-group-item-danger">
                                    Step ${step.step_index || (idx + 1)} (${step.label || 'Unknown'}) : ${issueHtml}
                                </li>
                            `;
                        });
                        html += `</ul></div>`;
                    }
                }
                
                resultSection.innerHTML = html;
                
                // 替换已有结果区域
                const existingSection = document.getElementById('analysisResultSection');
                if (existingSection) existingSection.remove();
                const analysisLogSection = document.getElementById('analysisLogSection');
                if (analysisLogSection) {
                    analysisLogSection.parentNode.insertBefore(resultSection, analysisLogSection.nextSibling);
                } else {
                    form.parentNode.appendChild(resultSection);
                }
                
                // 重置按钮
                if (analyzeBtn) {
                    analyzeBtn.disabled = false;
                    analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Reasoning Chain';
                }
            })
            .catch(error => {
                console.error('Error loading analysis result:', error);
                showToast('Failed to load analysis result: ' + error.message, 'error');
                if (analyzeBtn) {
                    analyzeBtn.disabled = false;
                    analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Reasoning Chain';
                }
            });
    }

    // Toast notification function
    function showToast(message, type = 'info') {
        const toastContainer = document.createElement('div');
        toastContainer.className = 'position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1100';

        const toastHtml = `
            <div class="toast show" role="alert">
                <div class="toast-header">
                    <i class="fas fa-${type === 'error' ? 'exclamation-triangle text-danger' : type === 'warning' ? 'exclamation-circle text-warning' : 'check-circle text-success'} me-2"></i>
                    <strong class="me-auto">AutoLabel</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;

        toastContainer.innerHTML = toastHtml;
        document.body.appendChild(toastContainer);

        // Auto remove after 5 seconds
        setTimeout(() => {
            toastContainer.remove();
        }, 5000);

        // Remove on close button click
        toastContainer.querySelector('.btn-close').addEventListener('click', function() {
            toastContainer.remove();
        });
    }

    // Example data loader
    const exampleBtn = document.getElementById('loadExample');
    if (exampleBtn) {
        exampleBtn.addEventListener('click', function() {
            const exampleText = `All researchers who publish papers attend conferences (universal conditional premise)
Some AI researchers publish papers (existential premise)
The AI researchers mentioned satisfy the condition of publishing papers
Anyone who publishes papers attends conferences
Therefore, some AI researchers attend conferences`;

            reasoningTextarea.value = exampleText;
            reasoningTextarea.style.height = 'auto';
            reasoningTextarea.style.height = reasoningTextarea.scrollHeight + 'px';

            document.getElementById('question').value = 'All researchers who publish papers attend conferences. Some AI researchers publish papers. Therefore, some AI researchers attend conferences.';

            showToast('Example loaded! You can now analyze or preview.', 'success');
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (!analyzeBtn.disabled) {
                form.dispatchEvent(new Event('submit'));
            }
        }


    });

    // Clear result button
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            // Clear session ID
            sessionStorage.removeItem('sessionId');
            
            // ✅ 关闭 SSE 连接
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            
            // Hide log section
            const analysisLogSection = document.getElementById('analysisLogSection');
            if (analysisLogSection) {
                analysisLogSection.style.display = 'none';
            }
            
            // Remove result section
            const analysisResultSection = document.getElementById('analysisResultSection');
            if (analysisResultSection) {
                analysisResultSection.remove();
            }
            
            // Remove file result section
            const fileResultSection = document.getElementById('fileResultSection');
            if (fileResultSection) {
                fileResultSection.remove();
            }
            
            // Reset analyze button
            if (analyzeBtn) {
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Reasoning Chain';
            }
            
            showToast('Result cleared successfully!', 'success');
        });
    }

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // File loading functionality
    function loadExperimentFiles() {
        // Show loading state
        experimentFileSelect.innerHTML = '<option value="">-- Loading files... --</option>';

        // Call API to get experiment files
        fetch('/api/experiment-files')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }

                // Populate dropdown
                experimentFileSelect.innerHTML = '<option value="">-- Select Experiment File --</option>';
                data.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file.value;
                    option.textContent = file.label;
                    experimentFileSelect.appendChild(option);
                });

                if (data.length === 0) {
                    showToast('No experiment files found', 'info');
                }
            })
            .catch(error => {
                experimentFileSelect.innerHTML = '<option value="">-- Error loading files --</option>';
                showToast('Failed to load experiment files: ' + error.message, 'error');
            });
    }

    // Load selected file only if elements exist
    if (loadFileBtn && experimentFileSelect) {
        loadFileBtn.addEventListener('click', function() {
            const selectedFile = experimentFileSelect.value;
            
            if (!selectedFile) {
                showToast('Please select an experiment file first', 'warning');
                return;
            }

            // Show loading state
            loadFileBtn.disabled = true;
            loadFileBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';

            // Call API to get experiment result
            fetch(`/api/experiment-result/${selectedFile}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }

                    // Display result
                    displayFileResult(data);

                    // Reset button
                    loadFileBtn.disabled = false;
                    loadFileBtn.innerHTML = '<i class="fas fa-file-import"></i> Load Selected File';

                    showToast('File loaded successfully!', 'success');
                })
                .catch(error => {
                    // Reset button
                    loadFileBtn.disabled = false;
                    loadFileBtn.innerHTML = '<i class="fas fa-file-import"></i> Load Selected File';

                    showToast('Failed to load file: ' + error.message, 'error');
                });
        });
    }

    // Display file result
    function displayFileResult(result) {
        // Create result display section
        const resultSection = document.createElement('div');
        resultSection.id = 'fileResultSection';
        resultSection.className = 'mt-4 p-4 border rounded bg-light';

        // Check if result is valid
        if (!result) {
            resultSection.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    Invalid result data
                </div>
            `;
            form.parentNode.appendChild(resultSection);
            return;
        }

        let html = `
            <h5><i class="fas fa-file-alt"></i> Experiment Result</h5>
            <div class="mb-3">
                <strong>Dataset:</strong> ${result.batch_info?.dataset || 'N/A'}<br>
                <strong>Total Samples:</strong> ${result.batch_info?.total_samples || 'N/A'}<br>
                <strong>Timestamp:</strong> ${result.batch_info?.timestamp ? formatTimestamp(result.batch_info.timestamp) : 'N/A'}<br>
                <strong>Model:</strong> ${result.batch_info?.config?.model || 'N/A'}
            </div>
        `;

        if (result.results && Array.isArray(result.results) && result.results.length > 0) {
            html += '<h6 class="mt-3">Sample Results:</h6>';
            result.results.forEach((sample, index) => {
                if (!sample) return;
                
                html += `
                    <div class="mt-2 p-2 border rounded">
                        <strong>Sample ${index + 1}: ${sample.id || 'N/A'}</strong><br>
                        <strong>Risk Level:</strong> <span class="badge bg-${getRiskColor(sample.sample_risk_level || sample.risk_level || 'Unknown')}">${sample.sample_risk_level || sample.risk_level || 'Unknown'}</span><br>
                        <strong>Issues:</strong> ${sample.issues_count || 0}<br>
                        <div class="mt-2">
                            <strong>Reasoning Chain:</strong>
                            <ol class="list-group list-group-numbered">
                `;
                
                // Try different possible locations for reasoning chain
                let reasoningChain = null;
                if (sample.reasoning_chain && Array.isArray(sample.reasoning_chain)) {
                    reasoningChain = sample.reasoning_chain;
                } else if (sample.sample && sample.sample.reasoning_chain && Array.isArray(sample.sample.reasoning_chain)) {
                    reasoningChain = sample.sample.reasoning_chain;
                } else if (sample.original_reasoning && Array.isArray(sample.original_reasoning)) {
                    reasoningChain = sample.original_reasoning;
                } else if (sample.reasoning && Array.isArray(sample.reasoning)) {
                    reasoningChain = sample.reasoning;
                }
                
                if (reasoningChain) {
                    reasoningChain.forEach(step => {
                        html += `<li class="list-group-item">${step || ''}</li>`;
                    });
                } else {
                    html += '<li class="list-group-item text-muted">No reasoning chain available</li>';
                }
                
                html += `
                            </ol>
                        </div>
                `;
                
                // Try different possible locations for diagnosis
                let diagnosisSteps = null;
                if (sample.diagnosis?.steps && Array.isArray(sample.diagnosis.steps)) {
                    diagnosisSteps = sample.diagnosis.steps;
                } else if (sample.reverified_results && Array.isArray(sample.reverified_results)) {
                    // Convert reverified_results to steps format
                    diagnosisSteps = sample.reverified_results.map((revResult, index) => {
                        return {
                            label: revResult.label || 'Unknown',
                            issues: revResult.issues || [],
                            step_text: revResult.step_description || revResult.step || '',
                            step_index: revResult.step_index || index
                        };
                    });
                } else if (sample.hallucination_analysis?.reverified_results && Array.isArray(sample.hallucination_analysis.reverified_results)) {
                    // Convert reverified_results to steps format (new format in hallucination_analysis)
                    diagnosisSteps = sample.hallucination_analysis.reverified_results.map((revResult, index) => {
                        return {
                            label: revResult.label || 'Unknown',
                            issues: revResult.issues || [],
                            step_text: revResult.step_description || revResult.step || '',
                            step_index: revResult.step_index || index
                        };
                    });
                } else if (sample.hallucination_analysis?.reverification_results && Array.isArray(sample.hallucination_analysis.reverification_results)) {
                    // Convert reverification_results to steps format (old format)
                    diagnosisSteps = sample.hallucination_analysis.reverification_results.map((revResult, index) => {
                        return {
                            label: revResult.label || 'Unknown',
                            issues: revResult.issues || [],
                            step_text: revResult.step_text || '',
                            step_index: revResult.step_index || index
                        };
                    });
                } else if (sample.hallucination_analysis?.problematic_steps && Array.isArray(sample.hallucination_analysis.problematic_steps)) {
                    // Convert problematic_steps to steps format
                    diagnosisSteps = sample.hallucination_analysis.problematic_steps.map((probStep, index) => {
                        return {
                            label: probStep.label || 'Unknown',
                            issues: probStep.issues || []
                        };
                    });
                }
                
                // Check if the sample has any issues using issues_count
                const hasIssues = sample.issues_count && sample.issues_count > 0;
                
                if (hasIssues && diagnosisSteps) {
                    // Filter to only include steps with issues
                    const stepsWithIssues = diagnosisSteps.filter(step => {
                        return step && step.issues && Array.isArray(step.issues) && step.issues.length > 0;
                    });
                    
                    if (stepsWithIssues.length > 0) {
                        html += `
                            <div class="mt-2">
                                <strong>Diagnosis (Issues Found):</strong>
                                <ul class="list-group">
                        `;
                        
                        stepsWithIssues.forEach((step, stepIndex) => {
                            if (!step) return;
                            
                            // Format issue descriptions without truncation
                            let issueHtml = '<ul class="mt-1">';
                            step.issues.forEach(issue => {
                                issueHtml += `<li>${issue}</li>`;
                            });
                            issueHtml += '</ul>';
                            
                            html += `
                                <li class="list-group-item list-group-item-danger">
                                    Step ${step.step_index || (stepIndex + 1)} (${step.label || 'Unknown'}): Issues found (${step.issues.length})
                                    ${issueHtml}
                                </li>
                            `;
                        });
                        
                        html += '</ul></div>';
                    }
                }
                
                html += `
                    </div>
                `;
            });
        } else {
            html += '<div class="alert alert-info mt-3">No results available in this experiment file</div>';
        }

        resultSection.innerHTML = html;

        // Remove existing result section if any
        const existingSection = document.getElementById('fileResultSection');
        if (existingSection) {
            existingSection.remove();
        }

        // Add new result section
        form.parentNode.appendChild(resultSection);
    }
});

// Utility functions
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

function getRiskColor(riskLevel) {
    if(!riskLevel) return 'secondary';
    switch(riskLevel.toLowerCase()) {
        case 'low': return 'success';
        case 'medium': return 'warning';
        case 'high': return 'danger';
        default: return 'secondary';
    }
}

function getRiskIcon(riskLevel) {
    if(!riskLevel) return 'fas fa-question-circle text-secondary';
    switch(riskLevel.toLowerCase()) {
        case 'low': return 'fas fa-shield-alt text-success';
        case 'medium': return 'fas fa-exclamation-triangle text-warning';
        case 'high': return 'fas fa-exclamation-circle text-danger';
        default: return 'fas fa-question-circle text-secondary';
    }
}