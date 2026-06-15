const App = {
    state: {
        currentArtifact: null,
        currentPage: 1,
        totalPages: 1,
        cultureFilter: '',
        keywordFilter: '',
        riskFilter: '',
        alertStatusFilter: '',
        alertTypeFilter: '',
        spectrumType: 'raman',
        currentView: 'density',
        wsConnected: false
    },

    init() {
        this.bindEvents();
        this.loadArtifacts();
        this.loadStats();
        this.loadAlerts();
        this.startTimeUpdate();
        this.connectWebSocket();
    },

    bindEvents() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        document.getElementById('culture-filter').addEventListener('change', (e) => {
            this.state.cultureFilter = e.target.value;
            this.state.currentPage = 1;
            this.loadArtifacts();
        });

        document.getElementById('search-input').addEventListener('input', 
            this.debounce((e) => {
                this.state.keywordFilter = e.target.value;
                this.state.currentPage = 1;
                this.loadArtifacts();
            }, 300)
        );

        document.getElementById('risk-filter').addEventListener('change', (e) => {
            this.state.riskFilter = e.target.value;
            this.loadArtifacts();
        });

        document.getElementById('btn-prev').addEventListener('click', () => {
            if (this.state.currentPage > 1) {
                this.state.currentPage--;
                this.loadArtifacts();
            }
        });

        document.getElementById('btn-next').addEventListener('click', () => {
            if (this.state.currentPage < this.state.totalPages) {
                this.state.currentPage++;
                this.loadArtifacts();
            }
        });

        document.getElementById('btn-start-sim').addEventListener('click', () => {
            this.startSimulator();
        });

        document.getElementById('btn-stop-sim').addEventListener('click', () => {
            this.stopSimulator();
        });

        document.querySelectorAll('.btn-view').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchView(e.target.dataset.view);
            });
        });

        document.getElementById('alert-status-filter').addEventListener('change', (e) => {
            this.state.alertStatusFilter = e.target.value;
            this.loadAlerts();
        });

        document.getElementById('alert-type-filter').addEventListener('change', (e) => {
            this.state.alertTypeFilter = e.target.value;
            this.loadAlerts();
        });

        document.getElementById('spectrum-type').addEventListener('change', (e) => {
            this.state.spectrumType = e.target.value;
            this.updateSpectrumChart();
        });
    },

    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('hidden', content.id !== `tab-${tabName}`);
        });

        if (tabName === 'detail' && this.state.currentArtifact) {
            this.updateDetailView();
        }
    },

    switchView(viewName) {
        this.state.currentView = viewName;
        document.querySelectorAll('.btn-view').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === viewName);
        });
        this.updateJadeCanvas();
    },

    async loadArtifacts() {
        try {
            const data = await API.getArtifacts(
                this.state.currentPage,
                CONFIG.PAGINATION.PAGE_SIZE,
                this.state.cultureFilter,
                this.state.keywordFilter
            );

            this.state.totalPages = Math.ceil(data.total / CONFIG.PAGINATION.PAGE_SIZE);
            document.getElementById('page-info').textContent = 
                `第 ${this.state.currentPage} / ${this.state.totalPages} 页`;

            this.renderArtifacts(data.data);
        } catch (e) {
            console.error('加载玉器列表失败:', e);
        }
    },

    renderArtifacts(artifacts) {
        const grid = document.getElementById('artifact-grid');
        grid.innerHTML = '';

        artifacts.forEach(artifact => {
            const card = document.createElement('div');
            card.className = 'artifact-card';
            card.dataset.id = artifact.artifact_id;

            const riskLevel = this.getRiskLevel(artifact);
            card.classList.add(`${riskLevel}-risk`);

            card.innerHTML = `
                <div class="card-image">
                    <canvas width="200" height="150"></canvas>
                    <div class="card-risk-badge ${riskLevel}">
                        ${this.getRiskText(riskLevel)}
                    </div>
                </div>
                <div class="card-info">
                    <div class="card-name">${artifact.name}</div>
                    <div class="card-id">${artifact.artifact_id}</div>
                    <div class="card-tags">
                        <span class="card-tag">${artifact.culture}</span>
                        <span class="card-tag">${artifact.jade_type}</span>
                    </div>
                </div>
            `;

            card.addEventListener('click', () => {
                this.selectArtifact(artifact);
            });

            grid.appendChild(card);

            const canvas = card.querySelector('canvas');
            JadeCanvas.drawJade(canvas, artifact.jade_type);
        });
    },

    getRiskLevel(artifact) {
        if (artifact.is_suspected_forgery) return 'high';
        return 'low';
    },

    getRiskText(level) {
        const texts = { high: '高风险', medium: '中风险', low: '低风险' };
        return texts[level] || '未知';
    },

    async selectArtifact(artifact) {
        this.state.currentArtifact = artifact;
        this.switchTab('detail');
        await this.loadArtifactDetail();
    },

    async loadArtifactDetail() {
        const artifact = this.state.currentArtifact;
        if (!artifact) return;

        document.getElementById('detail-name').textContent = artifact.name;
        document.getElementById('info-id').textContent = artifact.artifact_id;
        document.getElementById('info-culture').textContent = artifact.culture;
        document.getElementById('info-type').textContent = artifact.jade_type;
        document.getElementById('info-site').textContent = artifact.excavation_site || '-';
        document.getElementById('info-year').textContent = artifact.excavation_year || '-';
        
        const size = artifact.size || {};
        document.getElementById('info-size').textContent = 
            `${(size.length||0).toFixed(1)} × ${(size.width||0).toFixed(1)} × ${(size.thickness||0).toFixed(1)} cm`;
        document.getElementById('info-weight').textContent = 
            `${(artifact.weight||0).toFixed(1)} g`;

        this.updateJadeCanvas();
        
        try {
            await Promise.all([
                this.runDiffusion(),
                this.runAnomalyDetection()
            ]);
        } catch (e) {
            console.error('加载详情数据失败:', e);
        }
    },

    updateJadeCanvas() {
        const artifact = this.state.currentArtifact;
        if (!artifact) return;

        const canvas = document.getElementById('jade-canvas');
        const view = this.state.currentView;

        if (view === 'original') {
            JadeCanvas.drawJade(canvas, artifact.jade_type);
            document.getElementById('forgery-badge').classList.add('hidden');
        } else if (view === 'density') {
            this.loadAndDrawDensityMap();
        } else if (view === 'diffusion') {
            this.drawDiffusionView();
        }
    },

    async loadAndDrawDensityMap() {
        const artifact = this.state.currentArtifact;
        if (!artifact) return;

        try {
            const data = await API.getDensityMap(artifact.artifact_id);
            
            const canvas = document.getElementById('jade-canvas');
            
            if (data.density_map && data.density_map.length > 0) {
                DensityMap.drawOverlay(canvas, artifact.jade_type, data.density_map, {
                    colorScheme: 'viridis',
                    contour: true
                });
            } else {
                JadeCanvas.drawJade(canvas, artifact.jade_type);
            }

            this.updateForgeryBadge();
            
        } catch (e) {
            console.error('加载密度图失败:', e);
            JadeCanvas.drawJade(canvas, artifact.jade_type);
        }
    },

    drawDiffusionView() {
        const canvas = document.getElementById('jade-canvas');
        const artifact = this.state.currentArtifact;
        JadeCanvas.drawJade(canvas, artifact.jade_type);
        this.updateForgeryBadge();
    },

    updateForgeryBadge() {
        const badge = document.getElementById('forgery-badge');
        const artifact = this.state.currentArtifact;
        
        if (artifact && artifact.is_suspected_forgery) {
            badge.classList.remove('hidden');
            document.getElementById('forgery-value').textContent = '高风险';
        } else {
            badge.classList.add('hidden');
        }
    },

    async runDiffusion() {
        const artifact = this.state.currentArtifact;
        if (!artifact) return;

        try {
            const result = await API.runDiffusion(artifact.artifact_id, {
                temperature: 25,
                humidity: 50,
                time_hours: 5000
            });

            if (result.fe3_diffusion && result.mn2_diffusion) {
                document.getElementById('fe-depth').textContent = 
                    result.penetration_depth_fe_mm.toFixed(3) + ' mm';
                document.getElementById('mn-depth').textContent = 
                    result.penetration_depth_mn_mm.toFixed(3) + ' mm';
                document.getElementById('max-depth').textContent = 
                    result.max_penetration_mm.toFixed(3) + ' mm';

                SpectrumChart.drawDiffusion(
                    '#diffusion-chart',
                    result.fe3_diffusion,
                    result.mn2_diffusion
                );
            }
        } catch (e) {
            console.error('扩散模拟失败:', e);
        }
    },

    async runAnomalyDetection() {
        const artifact = this.state.currentArtifact;
        if (!artifact) return;

        try {
            const result = await API.runAnomalyDetection(artifact.artifact_id);

            SpectrumChart.drawAnomalyChart(
                '#anomaly-chart',
                result.anomaly_score || 0,
                result.forgery_probability || 0
            );

            const reasonsDiv = document.getElementById('anomaly-reasons');
            if (result.anomaly_reasons && result.anomaly_reasons.length > 0) {
                reasonsDiv.innerHTML = result.anomaly_reasons
                    .map(r => `<div class="anomaly-reason">• ${r}</div>`)
                    .join('');
            } else {
                reasonsDiv.innerHTML = '<div style="color: #2ed573; font-size: 12px;">✓ 未发现明显异常特征</div>';
            }

            const forgeryValue = document.getElementById('forgery-value');
            const badge = document.getElementById('forgery-badge');
            
            if (result.forgery_probability > 0.7) {
                badge.classList.remove('hidden');
                forgeryValue.textContent = (result.forgery_probability * 100).toFixed(1) + '%';
                
                const canvas = document.getElementById('jade-canvas');
                JadeCanvas.drawForgeryFrame(canvas, result.forgery_probability);
            }

        } catch (e) {
            console.error('异常检测失败:', e);
        }
    },

    async loadStats() {
        try {
            const stats = await API.getStatsSummary();
            
            document.getElementById('total-artifacts').textContent = stats.total_artifacts || 200;
            document.getElementById('hongshan-count').textContent = stats.hongshan_count || 100;
            document.getElementById('liangzhu-count').textContent = stats.liangzhu_count || 100;
            document.getElementById('active-alerts').textContent = stats.active_alerts || 0;
            document.getElementById('high-risk').textContent = stats.high_risk_artifacts || 0;
            document.getElementById('devices-online').textContent = stats.devices_online || 40;
        } catch (e) {
            console.error('加载统计数据失败:', e);
        }
    },

    async loadAlerts() {
        try {
            const data = await API.getAlerts(
                this.state.alertStatusFilter,
                this.state.alertTypeFilter
            );
            this.renderAlerts(data.data || []);
        } catch (e) {
            console.error('加载告警失败:', e);
        }
    },

    renderAlerts(alerts) {
        const list = document.getElementById('alerts-list');
        
        if (alerts.length === 0) {
            list.innerHTML = '<div style="text-align: center; color: #888; padding: 40px;">暂无告警信息</div>';
            return;
        }

        list.innerHTML = alerts.map(alert => {
            const time = new Date(alert.timestamp || Date.now()).toLocaleString('zh-CN');
            const typeText = alert.alert_type === 'diffusion' ? '沁色深度' : '作伪识别';
            const severityClass = alert.severity === 'critical' ? 'critical' : 'warning';
            const acknowledged = alert.status === 'acknowledged';

            return `
                <div class="alert-item ${severityClass} ${acknowledged ? 'acknowledged' : ''}" 
                     data-id="${alert._id}">
                    <div class="alert-main">
                        <div class="alert-type">${typeText}告警</div>
                        <div class="alert-message">${alert.message || ''}</div>
                        <div class="alert-message" style="margin-top: 5px;">
                            玉器编号: ${alert.artifact_id || '-'}
                        </div>
                    </div>
                    <div class="alert-meta">
                        <div class="alert-time">${time}</div>
                        <div class="alert-status">${acknowledged ? '已确认' : '未处理'}</div>
                        ${!acknowledged ? `
                            <div class="alert-actions" style="margin-top: 8px;">
                                <button onclick="App.acknowledgeAlert('${alert._id}')">确认</button>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    },

    async acknowledgeAlert(alertId) {
        try {
            await API.acknowledgeAlert(alertId);
            this.loadAlerts();
            this.loadStats();
        } catch (e) {
            console.error('确认告警失败:', e);
        }
    },

    async startSimulator() {
        try {
            await API.startSimulator(30);
            document.getElementById('sim-status').textContent = '运行中...';
            document.getElementById('sim-status').style.color = '#2ed573';
        } catch (e) {
            console.error('启动模拟器失败:', e);
        }
    },

    async stopSimulator() {
        try {
            await API.stopSimulator();
            document.getElementById('sim-status').textContent = '已停止';
            document.getElementById('sim-status').style.color = '#ff6b6b';
        } catch (e) {
            console.error('停止模拟器失败:', e);
        }
    },

    updateSpectrumChart() {
        const artifact = this.state.currentArtifact;
        if (!artifact) return;

        const type = this.state.spectrumType;
        const container = document.getElementById('spectrum-chart');

        document.getElementById('spec-artifact-id').textContent = artifact.artifact_id;

        if (type === 'raman') {
            API.getRamanSpectrum(artifact.artifact_id).then(data => {
                if (data && !data.error) {
                    SpectrumChart.drawRaman(container, data);
                    document.getElementById('spec-device').textContent = data.device_id || '-';
                    document.getElementById('spec-time').textContent = 
                        new Date(data.timestamp || Date.now()).toLocaleString('zh-CN');
                }
            }).catch(e => {
                this.generateMockSpectrum('raman', container, artifact);
            });
        } else {
            API.getXRFSpectrum(artifact.artifact_id).then(data => {
                if (data && !data.error) {
                    SpectrumChart.drawXRF(container, data);
                    document.getElementById('spec-device').textContent = data.device_id || '-';
                    document.getElementById('spec-time').textContent = 
                        new Date(data.timestamp || Date.now()).toLocaleString('zh-CN');
                }
            }).catch(e => {
                this.generateMockSpectrum('xrf', container, artifact);
            });
        }
    },

    generateMockSpectrum(type, container, artifact) {
        const numPoints = 512;
        const spectrum = [];
        const wavelengths = [];

        if (type === 'raman') {
            for (let i = 0; i < numPoints; i++) {
                wavelengths.push(100 + (i / numPoints) * 1900);
                let val = 0;
                val += Math.exp(-Math.pow((wavelengths[i] - 200) / 30, 2)) * 1.0;
                val += Math.exp(-Math.pow((wavelengths[i] - 380) / 40, 2)) * 0.8;
                val += Math.exp(-Math.pow((wavelengths[i] - 520) / 50, 2)) * 1.5;
                val += Math.exp(-Math.pow((wavelengths[i] - 1080) / 45, 2)) * 0.9;
                val += Math.random() * 0.05;
                spectrum.push(val);
            }
            SpectrumChart.drawRaman(container, { wavelengths, spectrum_data: spectrum });
        } else {
            for (let i = 0; i < numPoints; i++) {
                wavelengths.push((i / numPoints) * 15);
                let val = 0.05 * Math.exp(-wavelengths[i] / 2);
                val += Math.exp(-Math.pow((wavelengths[i] - 0.525) / 0.05, 2)) * 1.2;
                val += Math.exp(-Math.pow((wavelengths[i] - 1.74) / 0.06, 2)) * 1.5;
                val += Math.exp(-Math.pow((wavelengths[i] - 6.40) / 0.04, 2)) * 0.4;
                val += Math.random() * 0.01;
                spectrum.push(val);
            }
            SpectrumChart.drawXRF(container, { energies: wavelengths, spectrum_data: spectrum });
        }

        document.getElementById('spec-device').textContent = '模拟设备';
        document.getElementById('spec-time').textContent = new Date().toLocaleString('zh-CN');
    },

    updateDetailView() {
        this.loadArtifactDetail();
    },

    connectWebSocket() {
        try {
            const wsUrl = CONFIG.WS_URL + '/alerts/';
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                this.state.wsConnected = true;
                document.getElementById('connection-status').textContent = '● 实时监测中';
                document.getElementById('connection-status').className = 'status-indicator online';
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'alert' && data.data) {
                        this.handleWebSocketAlert(data.data);
                    }
                } catch (e) {
                    console.error('解析WebSocket消息失败:', e);
                }
            };

            ws.onclose = () => {
                this.state.wsConnected = false;
                document.getElementById('connection-status').textContent = '● 连接断开';
                document.getElementById('connection-status').className = 'status-indicator offline';
                
                setTimeout(() => {
                    this.connectWebSocket();
                }, 5000);
            };

            ws.onerror = (e) => {
                console.warn('WebSocket连接错误');
            };

            this.ws = ws;

        } catch (e) {
            console.warn('WebSocket不可用，降级为轮询模式');
            document.getElementById('connection-status').textContent = '● 轮询模式';
            document.getElementById('connection-status').className = 'status-indicator offline';
        }
    },

    handleWebSocketAlert(alertData) {
        this.showAlertToast(alertData);
        this.loadAlerts();
        this.loadStats();
    },

    showAlertToast(alertData) {
        const toast = document.getElementById('alert-toast');
        const title = document.getElementById('toast-title');
        const message = document.getElementById('toast-message');

        title.textContent = alertData.alert_type === 'diffusion' ? '沁色深度告警' : '作伪识别告警';
        message.textContent = `${alertData.artifact_id}: ${alertData.message || '检测到异常'}`;

        toast.classList.remove('hidden');

        setTimeout(() => {
            this.hideAlertToast();
        }, 5000);
    },

    hideAlertToast() {
        document.getElementById('alert-toast').classList.add('hidden');
    },

    startTimeUpdate() {
        const updateTime = () => {
            const now = new Date();
            document.getElementById('current-time').textContent = 
                now.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
        };

        updateTime();
        setInterval(updateTime, 1000);
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

function hideAlertToast() {
    App.hideAlertToast();
}
