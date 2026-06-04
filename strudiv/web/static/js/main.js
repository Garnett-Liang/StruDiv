// ============================================================
// StruDiv Web Interface — Unified JavaScript
// Handles: index.html (analysis), result.html (experiment viewer)
// ============================================================

document.addEventListener('DOMContentLoaded', function() {

    // =========================================
    // Shared Utility Functions
    // =========================================

    function formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }

    function getRiskColor(riskLevel) {
        if (!riskLevel) return 'secondary';
        switch (riskLevel.toLowerCase()) {
            case 'low': return 'success';
            case 'medium': return 'warning';
            case 'high': return 'danger';
            default: return 'secondary';
        }
    }

    function getRiskIcon(riskLevel) {
        if (!riskLevel) return 'fas fa-question-circle text-secondary';
        switch (riskLevel.toLowerCase()) {
            case 'low': return 'fas fa-shield-alt text-success';
            case 'medium': return 'fas fa-exclamation-triangle text-warning';
            case 'high': return 'fas fa-exclamation-circle text-danger';
            default: return 'fas fa-question-circle text-secondary';
        }
    }

    function getNested(obj, path, defaultValue) {
        defaultValue = (defaultValue !== undefined) ? defaultValue : 'N/A';
        return path.split('.').reduce(function(acc, key) {
            return (acc && acc[key] !== undefined) ? acc[key] : defaultValue;
        }, obj);
    }

    // =========================================
    // Unified Toast Notification
    // =========================================
    function showToast(message, type) {
        type = type || 'info';
        if (!message) {
            console.warn('Empty message passed to showToast');
            message = 'Notification';
        }

        var iconMap = {
            'error': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'success': 'check-circle',
            'info': 'info-circle'
        };
        var iconColorMap = {
            'error': 'text-danger',
            'warning': 'text-warning',
            'success': 'text-success',
            'info': 'text-info'
        };
        var icon = iconMap[type] || 'info-circle';
        var iconColor = iconColorMap[type] || 'text-info';
        var borderColorMap = {
            'error': '#dc3545',
            'warning': '#ffc107',
            'success': '#28a745',
            'info': '#0dcaf0'
        };
        var borderColor = borderColorMap[type] || '#0dcaf0';

        var container = document.createElement('div');
        container.className = 'toast-container-custom';
        container.innerHTML =
            '<div class="toast-custom toast-' + type + '" role="alert">' +
                '<div class="toast-header">' +
                    '<i class="fas fa-' + icon + ' ' + iconColor + ' me-2"></i>' +
                    '<strong class="me-auto">StruDiv</strong>' +
                    '<button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>' +
                '</div>' +
                '<div class="toast-body">' + message + '</div>' +
            '</div>';
        document.body.appendChild(container);

        // Auto-remove after 5 seconds
        setTimeout(function() {
            if (container && container.parentNode) {
                container.remove();
            }
        }, 5000);

        // Remove on close button click
        var closeBtn = container.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                if (container && container.parentNode) {
                    container.remove();
                }
            });
        }
    }

    // =========================================
    // Skeleton Loading Helpers
    // =========================================
    function renderSkeletonLines(count) {
        count = count || 4;
        var html = '';
        for (var i = 0; i < count; i++) {
            html += '<div class="skeleton skeleton-text" style="width:' + (85 - i * 10) + '%"></div>';
        }
        return html;
    }

    function renderSkeletonBlocks(count) {
        count = count || 3;
        var html = '';
        for (var i = 0; i < count; i++) {
            html += '<div class="skeleton skeleton-block"></div>';
        }
        return html;
    }

    // =========================================
    // Scroll-triggered Animations
    // =========================================
    if ('IntersectionObserver' in window) {
        var animatedElements = document.querySelectorAll('.step-card, .how-card, .card.shadow');
        if (animatedElements.length > 0) {
            var scrollObserver = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                        scrollObserver.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1 });

            animatedElements.forEach(function(el) {
                // Only animate if not already visible
                var rect = el.getBoundingClientRect();
                if (rect.top > window.innerHeight) {
                    el.style.opacity = '0';
                    el.style.transform = 'translateY(24px)';
                    el.style.transition = 'opacity 0.5s ease, transform 0.5s cubic-bezier(0.2, 0.9, 0.4, 1.1)';
                    scrollObserver.observe(el);
                }
            });
        }
    }

    // =========================================
    // PAGE: index.html — Analysis Form
    // =========================================
    var form = document.getElementById('analysisForm');
    var reasoningTextarea = document.getElementById('reasoning_chain');
    var analyzeBtn = document.getElementById('analyzeBtn');
    var clearBtn = document.getElementById('clearBtn');
    var eventSource = null;

    if (form && reasoningTextarea) {
        // Auto-resize textarea
        reasoningTextarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 300) + 'px';
        });

        // Form submission (AJAX, no page reload)
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            var reasoningText = reasoningTextarea.value.trim();
            var lines = reasoningText.split('\n').filter(function(line) { return line.trim(); });

            if (lines.length < 2) {
                showToast('Please enter at least 2 reasoning steps', 'error');
                return;
            }

            // Show log section with skeleton loading
            var analysisLogSection = document.getElementById('analysisLogSection');
            if (analysisLogSection) {
                analysisLogSection.style.display = 'block';
            }

            var logContent = document.getElementById('logContent');
            if (logContent) {
                logContent.innerHTML =
                    '<div class="text-center text-muted mb-3">' +
                        '<div class="spinner-border spinner-border-sm me-2" role="status"></div>' +
                        '<span>Initializing analysis pipeline...</span>' +
                    '</div>' +
                    renderSkeletonLines(5);
            }

            // Disable button
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

            var formData = new FormData(form);

            fetch(form.action, {
                method: 'POST',
                body: formData
            })
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if (data.error) throw new Error(data.error);

                var realSessionId = data.session_id;
                sessionStorage.setItem('sessionId', realSessionId);

                // Start SSE real-time log streaming
                loadLog(realSessionId);
            })
            .catch(function(err) {
                showToast(err.message, 'error');
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Reasoning Chain';
            });
        });

        // ---------- SSE Log Streaming ----------
        function loadLog(sessionId) {
            if (!sessionId) return;

            if (eventSource) {
                eventSource.close();
            }

            var logContent = document.getElementById('logContent');
            logContent.innerHTML = '';

            eventSource = new EventSource('/api/log-stream/' + sessionId);

            var pre = document.createElement('pre');
            logContent.appendChild(pre);

            eventSource.onopen = function() {
                console.log("SSE connected");
            };

            eventSource.onmessage = function(e) {
                if (e.data === "[STREAM END]") {
                    eventSource.close();
                    var sid = sessionStorage.getItem('sessionId');
                    if (sid) {
                        loadAnalysisResult(sid);
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

        // ---------- Load Analysis Result ----------
        function loadAnalysisResult(sessionId) {
            if (!sessionId) return;

            // Show skeleton while loading result
            var logContent = document.getElementById('logContent');
            var existingResult = document.getElementById('analysisResultSection');
            if (!existingResult && logContent) {
                var skeletonDiv = document.createElement('div');
                skeletonDiv.id = 'analysisResultSkeleton';
                skeletonDiv.className = 'mt-3 p-3';
                skeletonDiv.innerHTML =
                    '<div class="skeleton skeleton-text" style="width:40%"></div>' +
                    renderSkeletonLines(3) +
                    '<div class="skeleton skeleton-block mt-3"></div>' +
                    '<div class="skeleton skeleton-block"></div>';
                var analysisLogSection = document.getElementById('analysisLogSection');
                if (analysisLogSection) {
                    analysisLogSection.parentNode.insertBefore(skeletonDiv, analysisLogSection.nextSibling);
                }
            }

            fetch('/api/result/' + sessionId)
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (data.error) throw new Error(data.error);

                    // Remove skeleton
                    var skeleton = document.getElementById('analysisResultSkeleton');
                    if (skeleton) skeleton.remove();

                    // Extract data
                    var outerHA = data.hallucination_analysis || {};
                    var innerHA = outerHA.hallucination_analysis || {};
                    var hasNesting = innerHA && Object.keys(innerHA).length > 0;

                    var issuesCount = outerHA.issues_count;
                    if (issuesCount === undefined) issuesCount = innerHA.issues_count;
                    if (issuesCount === undefined) issuesCount = 0;

                    var riskLevel = outerHA.risk_level || outerHA.sample_risk_level || innerHA.sample_risk_level || 'Unknown';
                    var totalRiskScore = outerHA.total_risk_score;
                    if (totalRiskScore === undefined) totalRiskScore = innerHA.total_risk_score;
                    if (totalRiskScore === undefined) totalRiskScore = 0;

                    var labels = outerHA.labels || [];
                    var reasoning = outerHA.reasoning || (data.sample ? data.sample.reasoning_chain : null) || [];

                    // Create result section
                    var resultSection = document.createElement('div');
                    resultSection.id = 'analysisResultSection';
                    resultSection.className = 'mt-4 p-4 result-card';

                    var html =
                        '<h5><i class="fas fa-chart-bar"></i> Analysis Result</h5>' +
                        '<div class="mb-3">' +
                            '<strong>Model:</strong> ' + (data.model || 'N/A') + '<br>' +
                            '<strong>Timestamp:</strong> ' + (data.timestamp ? formatTimestamp(data.timestamp) : 'N/A') + '<br>' +
                            '<strong>Issues Found:</strong> ' + issuesCount + '<br>' +
                            '<strong>Risk Level:</strong> <span class="badge bg-' + getRiskColor(riskLevel) + '">' + riskLevel + '</span><br>' +
                            '<strong>Total Risk Score:</strong> ' + Number(totalRiskScore).toFixed(2) +
                        '</div>';

                    // Reasoning chain with labels
                    if (reasoning && Array.isArray(reasoning) && reasoning.length) {
                        html +=
                            '<div class="mt-3">' +
                                '<strong>Reasoning Chain:</strong>' +
                                '<ol class="list-group list-group-numbered">';
                        reasoning.forEach(function(step, index) {
                            var label = labels[index] || 'Unknown';
                            var cleanStep = String(step).replace(/^"|",?$/g, '');
                            html += '<li class="list-group-item">' + (cleanStep || '') +
                                        ' <span class="badge bg-secondary float-end">' + label + '</span>' +
                                    '</li>';
                        });
                        html += '</ol></div>';
                    }

                    // Error types
                    var detailSource = hasNesting ? innerHA : outerHA;
                    if (detailSource.error_types && Object.keys(detailSource.error_types).length > 0) {
                        html +=
                            '<div class="mt-3">' +
                                '<strong><i class="fas fa-exclamation-triangle"></i> Detailed Issue Analysis (Error Types):</strong>' +
                                '<ul class="list-group mt-2">';
                        for (var labelKey in detailSource.error_types) {
                            if (detailSource.error_types.hasOwnProperty(labelKey)) {
                                var errors = detailSource.error_types[labelKey];
                                if (errors && errors.length) {
                                    var errorList = errors.map(function(err) {
                                        if (typeof err === 'string') return err;
                                        return err.message || JSON.stringify(err);
                                    }).join('<br>');
                                    html += '<li class="list-group-item"><strong>' + labelKey + ':</strong><br>' + errorList + '</li>';
                                }
                            }
                        }
                        html += '</ul></div>';
                    }

                    // Problematic steps
                    if (detailSource.problematic_steps && Array.isArray(detailSource.problematic_steps)) {
                        var stepsWithIssues = detailSource.problematic_steps.filter(function(step) {
                            return step && step.issues && step.issues.length > 0;
                        });
                        if (stepsWithIssues.length > 0) {
                            html +=
                                '<div class="mt-3">' +
                                    '<strong>Diagnosis (Problematic Steps):</strong>' +
                                    '<ul class="list-group">';
                            stepsWithIssues.forEach(function(step, index) {
                                if (!step) return;
                                var issueHtml = '<ul class="mt-1">';
                                step.issues.forEach(function(issue) { issueHtml += '<li>' + issue + '</li>'; });
                                issueHtml += '</ul>';
                                html +=
                                    '<li class="list-group-item list-group-item-danger">' +
                                        'Step ' + (step.step_index || (index + 1)) + ' (' + (step.label || 'Unknown') + '): Issues found (' + step.issues.length + ')' +
                                        issueHtml +
                                    '</li>';
                            });
                            html += '</ul></div>';
                        }
                    } else if (detailSource.step_verification_results && Array.isArray(detailSource.step_verification_results)) {
                        var stepsWithIssuesV = detailSource.step_verification_results.filter(function(step) {
                            return step.issues && step.issues.length > 0;
                        });
                        if (stepsWithIssuesV.length > 0) {
                            html +=
                                '<div class="mt-3">' +
                                    '<strong>Diagnosis (Issues from Verification):</strong>' +
                                    '<ul class="list-group">';
                            stepsWithIssuesV.forEach(function(step, idx) {
                                var issueHtml = '<ul class="mt-1">';
                                step.issues.forEach(function(issue) { issueHtml += '<li>' + issue + '</li>'; });
                                issueHtml += '</ul>';
                                html +=
                                    '<li class="list-group-item list-group-item-danger">' +
                                        'Step ' + (step.step_index || (idx + 1)) + ' (' + (step.label || 'Unknown') + ') : ' + issueHtml +
                                    '</li>';
                            });
                            html += '</ul></div>';
                        }
                    }

                    resultSection.innerHTML = html;

                    // Replace existing result section
                    var existingSection = document.getElementById('analysisResultSection');
                    if (existingSection) existingSection.remove();
                    var analysisLogSection = document.getElementById('analysisLogSection');
                    if (analysisLogSection) {
                        analysisLogSection.parentNode.insertBefore(resultSection, analysisLogSection.nextSibling);
                    } else if (form) {
                        form.parentNode.appendChild(resultSection);
                    }

                    // Reset button
                    if (analyzeBtn) {
                        analyzeBtn.disabled = false;
                        analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Reasoning Chain';
                    }
                })
                .catch(function(error) {
                    console.error('Error loading analysis result:', error);
                    showToast('Failed to load analysis result: ' + error.message, 'error');
                    var skeleton = document.getElementById('analysisResultSkeleton');
                    if (skeleton) skeleton.remove();
                    if (analyzeBtn) {
                        analyzeBtn.disabled = false;
                        analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Reasoning Chain';
                    }
                });
        }

        // ---------- Keyboard Shortcut: Ctrl+Enter to submit ----------
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                if (analyzeBtn && !analyzeBtn.disabled) {
                    form.dispatchEvent(new Event('submit'));
                }
            }
        });
    }

    // ---------- Clear Result Button ----------
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            sessionStorage.removeItem('sessionId');

            if (typeof eventSource !== 'undefined' && eventSource) {
                eventSource.close();
                eventSource = null;
            }

            var analysisLogSection = document.getElementById('analysisLogSection');
            if (analysisLogSection) {
                analysisLogSection.style.display = 'none';
            }

            var analysisResultSection = document.getElementById('analysisResultSection');
            if (analysisResultSection) {
                analysisResultSection.remove();
            }

            var fileResultSection = document.getElementById('fileResultSection');
            if (fileResultSection) {
                fileResultSection.remove();
            }

            if (analyzeBtn) {
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Reasoning Chain';
            }

            showToast('Result cleared successfully!', 'success');
        });
    }

    // ---------- Load Example Button ----------
    var exampleBtn = document.getElementById('loadExample');
    if (exampleBtn && reasoningTextarea) {
        exampleBtn.addEventListener('click', function() {
            var exampleText =
                'All researchers who publish papers attend conferences (universal conditional premise)\n' +
                'Some AI researchers publish papers (existential premise)\n' +
                'The AI researchers mentioned satisfy the condition of publishing papers\n' +
                'Anyone who publishes papers attends conferences\n' +
                'Therefore, some AI researchers attend conferences';

            reasoningTextarea.value = exampleText;
            reasoningTextarea.style.height = 'auto';
            reasoningTextarea.style.height = reasoningTextarea.scrollHeight + 'px';

            var questionField = document.getElementById('question');
            if (questionField) {
                questionField.value = 'All researchers who publish papers attend conferences. Some AI researchers publish papers. Therefore, some AI researchers attend conferences.';
            }

            showToast('Example loaded! You can now analyze.', 'success');
        });
    }

    // ---------- Session ID from URL (after redirect) ----------
    var urlParams = new URLSearchParams(window.location.search);
    var sessionId = urlParams.get('session_id');
    if (sessionId) {
        sessionStorage.setItem('sessionId', sessionId);

        var analysisLogSection = document.getElementById('analysisLogSection');
        if (analysisLogSection) {
            analysisLogSection.style.display = 'block';
        }

        // loadLog and loadAnalysisResult are only defined when form exists
        if (typeof loadLog === 'function') {
            loadLog(sessionId);
        }
        if (typeof loadAnalysisResult === 'function') {
            loadAnalysisResult(sessionId);
        }
    }

    // =========================================
    // PAGE: result.html — Experiment Files
    // =========================================
    var experimentFileSelect = document.getElementById('experimentFile');
    var loadFileBtn = document.getElementById('loadFileBtn');

    if (experimentFileSelect && loadFileBtn) {
        loadExperimentFiles();

        loadFileBtn.addEventListener('click', function() {
            var selectedFile = experimentFileSelect.value;

            if (!selectedFile) {
                showToast('Please select an experiment file first', 'warning');
                return;
            }

            loadFileBtn.disabled = true;
            loadFileBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';

            var fileResultSection = document.getElementById('fileResultSection');
            if (fileResultSection) fileResultSection.style.display = 'block';

            var resultContent = document.getElementById('resultContent');
            if (resultContent) {
                resultContent.innerHTML =
                    '<div class="text-center text-muted mb-2">' +
                        '<div class="spinner-border spinner-border-sm me-2" role="status"></div>' +
                        '<span>Loading experiment result...</span>' +
                    '</div>' +
                    renderSkeletonBlocks(4);
            }

            fetch('/api/experiment-result/' + selectedFile)
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (data.error) throw new Error(data.error);
                    displayFileResult(data);
                    loadFileBtn.disabled = false;
                    loadFileBtn.innerHTML = '<i class="fas fa-file-import"></i> Load Selected File';
                    showToast('File loaded successfully!', 'success');
                })
                .catch(function(error) {
                    loadFileBtn.disabled = false;
                    loadFileBtn.innerHTML = '<i class="fas fa-file-import"></i> Load Selected File';
                    showToast('Failed to load file: ' + error.message, 'error');
                    if (resultContent) {
                        resultContent.innerHTML =
                            '<div class="alert alert-danger">' +
                                '<i class="fas fa-exclamation-triangle"></i> ' +
                                'Failed to load experiment result: ' + error.message +
                            '</div>';
                    }
                });
        });
    }

    function loadExperimentFiles() {
        if (!experimentFileSelect) return;
        experimentFileSelect.innerHTML = '<option value="">-- Loading files... --</option>';

        fetch('/api/experiment-files')
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.error) throw new Error(data.error);

                experimentFileSelect.innerHTML = '<option value="">-- Select Experiment File --</option>';
                data.forEach(function(file) {
                    var option = document.createElement('option');
                    option.value = file.value;
                    option.textContent = file.label;
                    experimentFileSelect.appendChild(option);
                });

                if (data.length === 0) {
                    showToast('No experiment files found', 'info');
                }
            })
            .catch(function(error) {
                experimentFileSelect.innerHTML = '<option value="">-- Error loading files --</option>';
                showToast('Failed to load experiment files: ' + error.message, 'error');
            });
    }

    function displayFileResult(result) {
        var resultContent = document.getElementById('resultContent');
        if (!resultContent) {
            // Fallback: create section if it doesn't exist
            var resultSection = document.createElement('div');
            resultSection.id = 'fileResultSection';
            resultSection.className = 'mt-4 p-4 result-card';
            // Try to append near form or body
            var formEl = document.getElementById('analysisForm');
            if (formEl) {
                formEl.parentNode.appendChild(resultSection);
            } else {
                var mainCard = document.querySelector('.card-body');
                if (mainCard) {
                    mainCard.appendChild(resultSection);
                } else {
                    document.body.appendChild(resultSection);
                }
            }
            resultContent = resultSection;
        }

        if (!result) {
            resultContent.innerHTML =
                '<div class="alert alert-danger">' +
                    '<i class="fas fa-exclamation-triangle"></i> Invalid result data' +
                '</div>';
            return;
        }

        var html =
            '<h5><i class="fas fa-file-alt"></i> Experiment Result</h5>' +
            '<div class="mb-3">' +
                '<strong>Dataset:</strong> ' + (getNested(result, 'batch_info.dataset')) + '<br>' +
                '<strong>Total Samples:</strong> ' + (getNested(result, 'batch_info.total_samples')) + '<br>' +
                '<strong>Timestamp:</strong> ' + (result.batch_info && result.batch_info.timestamp ? formatTimestamp(result.batch_info.timestamp) : 'N/A') + '<br>' +
                '<strong>Model:</strong> ' + (getNested(result, 'batch_info.config.model')) +
            '</div>';

        if (result.results && Array.isArray(result.results) && result.results.length > 0) {
            html += '<h6 class="mt-3">Sample Results:</h6>';
            result.results.forEach(function(sample, index) {
                if (!sample) return;

                var sampleId = sample.id || getNested(sample, 'sample.id', 'Sample ' + (index + 1));
                var groundTruth = sample.ground_truth || getNested(sample, 'sample.ground_truth', 'Unknown');
                var riskLevel = getNested(sample, 'hallucination_analysis.sample_risk_level',
                    getNested(sample, 'hallucination_analysis.risk_level', sample.risk_level || 'Unknown'));
                var issuesCount = sample.issues_count || getNested(sample, 'hallucination_analysis.issues_count', 0);
                var labels = sample.labels || getNested(sample, 'sample.labels', []);

                var groundTruthBadge = '';
                var truthLabel = String(groundTruth).toLowerCase();
                if (truthLabel === 'true' || truthLabel === 'true_hard' || truthLabel === 'true_easy') {
                    groundTruthBadge = '<span class="badge bg-success ms-2">Ground Truth: TRUE</span>';
                } else if (truthLabel === 'false' || truthLabel === 'false_hard' || truthLabel === 'false_easy') {
                    groundTruthBadge = '<span class="badge bg-danger ms-2">Ground Truth: FALSE</span>';
                } else {
                    groundTruthBadge = '<span class="badge bg-secondary ms-2">Ground Truth: ' + groundTruth + '</span>';
                }

                html +=
                    '<div class="mt-3 p-3 border rounded">' +
                        '<div class="d-flex justify-content-between align-items-center flex-wrap">' +
                            '<div>' +
                                '<strong>Sample ' + (index + 1) + ': ' + sampleId + '</strong>' +
                                groundTruthBadge +
                            '</div>' +
                            '<div>' +
                                '<span class="badge bg-' + getRiskColor(riskLevel) + '">Risk: ' + riskLevel + '</span>' +
                                '<span class="badge bg-info ms-1">Issues: ' + issuesCount + '</span>' +
                            '</div>' +
                        '</div>';

                // Reasoning chain
                var reasoningChain = null;
                if (sample.reasoning_chain && Array.isArray(sample.reasoning_chain)) reasoningChain = sample.reasoning_chain;
                else if (sample.sample && sample.sample.reasoning_chain && Array.isArray(sample.sample.reasoning_chain)) reasoningChain = sample.sample.reasoning_chain;
                else if (sample.original_reasoning && Array.isArray(sample.original_reasoning)) reasoningChain = sample.original_reasoning;
                else if (sample.reasoning && Array.isArray(sample.reasoning)) reasoningChain = sample.reasoning;

                if (reasoningChain && reasoningChain.length > 0) {
                    html += '<div class="mt-3"><strong>Reasoning Chain:</strong><ol class="list-group list-group-numbered mt-2">';
                    reasoningChain.forEach(function(step, stepIdx) {
                        var stepLabel = (labels && labels[stepIdx]) ? '<span class="badge bg-secondary ms-2">' + labels[stepIdx] + '</span>' : '';
                        html +=
                            '<li class="list-group-item d-flex justify-content-between align-items-start">' +
                                '<span class="flex-grow-1">' + step + '</span>' +
                                stepLabel +
                            '</li>';
                    });
                    html += '</ol></div>';
                } else {
                    html += '<div class="alert alert-warning mt-3">No reasoning chain available</div>';
                }

                // Diagnosis steps
                var diagnosisSteps = null;
                if (sample.diagnosis && sample.diagnosis.steps && Array.isArray(sample.diagnosis.steps)) {
                    diagnosisSteps = sample.diagnosis.steps;
                } else if (sample.reverified_results && Array.isArray(sample.reverified_results)) {
                    diagnosisSteps = sample.reverified_results.map(function(revResult, idx) {
                        return {
                            label: revResult.label || 'Unknown',
                            issues: revResult.issues || [],
                            step_text: revResult.step_description || revResult.step || '',
                            step_index: revResult.step_index || idx
                        };
                    });
                } else if (sample.hallucination_analysis && sample.hallucination_analysis.reverified_results && Array.isArray(sample.hallucination_analysis.reverified_results)) {
                    diagnosisSteps = sample.hallucination_analysis.reverified_results.map(function(revResult, idx) {
                        return {
                            label: revResult.label || 'Unknown',
                            issues: revResult.issues || [],
                            step_text: revResult.step_description || revResult.step || '',
                            step_index: revResult.step_index || idx
                        };
                    });
                } else if (sample.hallucination_analysis && sample.hallucination_analysis.problematic_steps && Array.isArray(sample.hallucination_analysis.problematic_steps)) {
                    diagnosisSteps = sample.hallucination_analysis.problematic_steps.map(function(probStep) {
                        return {
                            label: probStep.label || 'Unknown',
                            issues: probStep.issues || []
                        };
                    });
                }

                var hasIssues = (issuesCount > 0);
                if (hasIssues && diagnosisSteps) {
                    var stepsWithIssues = diagnosisSteps.filter(function(step) {
                        return step && step.issues && step.issues.length > 0;
                    });
                    if (stepsWithIssues.length > 0) {
                        html += '<div class="mt-3"><strong>Diagnosis (Issues Found):</strong><ul class="list-group mt-2">';
                        stepsWithIssues.forEach(function(step, stepIndex) {
                            var issueHtml = '<ul class="mt-1 mb-0">';
                            step.issues.forEach(function(issue) { issueHtml += '<li>' + issue + '</li>'; });
                            issueHtml += '</ul>';
                            html +=
                                '<li class="list-group-item list-group-item-danger">' +
                                    'Step ' + (step.step_index || (stepIndex + 1)) + ' (' + (step.label || 'Unknown') + '): ' + step.issues.length + ' issue(s)' +
                                    issueHtml +
                                '</li>';
                        });
                        html += '</ul></div>';
                    }
                } else if (hasIssues && !diagnosisSteps) {
                    html += '<div class="alert alert-danger mt-3">Issues detected but no detailed diagnosis available.</div>';
                }

                // Error types
                if (sample.hallucination_analysis && sample.hallucination_analysis.error_types && Object.keys(sample.hallucination_analysis.error_types).length > 0) {
                    html += '<div class="mt-3"><strong>Error Types:</strong><ul class="list-group mt-2">';
                    for (var labelKey in sample.hallucination_analysis.error_types) {
                        if (sample.hallucination_analysis.error_types.hasOwnProperty(labelKey)) {
                            var errs = sample.hallucination_analysis.error_types[labelKey];
                            if (errs && errs.length) {
                                html += '<li class="list-group-item error-type-item"><strong>' + labelKey + ':</strong> ' + errs.join('; ') + '</li>';
                            }
                        }
                    }
                    html += '</ul></div>';
                }

                html += '</div>';
            });
        } else {
            html += '<div class="alert alert-info mt-3">No results available in this experiment file</div>';
        }

        resultContent.innerHTML = html;
    }

    // =========================================
    // Bootstrap Tooltips Init
    // =========================================
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (tooltipTriggerList.length > 0) {
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

});
