// api-panel.js
class APIPanel {
    constructor() {
        // 初始化时从服务器获取配置
        this.init();
    }

    async init() {
        this.providerSelect = document.getElementById('api-provider');
        this.modelSelect = document.getElementById('api-model');
        this.keysContainer = document.querySelector('.api-keys-container');
        
        // 从服务器获取配置
        await this.fetchAPIConfigs();
        
        this.providerSelect.addEventListener('change', () => this.updateProviderUI());
        this.initAPIForm();
        this.updateProviderUI(); // 初始化UI
    }

    async fetchAPIConfigs() {
        try {
            // 发送WebSocket消息请求配置
            if (window.ws && window.ws.readyState === WebSocket.OPEN) {
                window.ws.send(JSON.stringify({
                    type: 'request_api_configs'
                }));
            }

            // 添加一次性事件监听器来接收配置
            await new Promise((resolve) => {
                const configHandler = (event) => {
                    const message = JSON.parse(event.data);
                    if (message.type === 'api_configs') {
                        this.modelConfigs = message.data;
                        window.removeEventListener('message', configHandler);
                        resolve();
                    }
                };
                window.ws.addEventListener('message', configHandler);
            });

            // 初始化提供商选择器
            this.initProviderSelect();
        } catch (error) {
            console.error('获取API配置失败:', error);
            // 使用默认配置作为后备
            this.modelConfigs = this.getDefaultConfigs();
            this.initProviderSelect();
        }
    }

    getDefaultConfigs() {
        // 默认配置作为后备
        return {
            openai: {
                label: 'OpenAI API Key',
                models: ['gpt-3.5-turbo', 'gpt-4'],
                envKey: 'OPENAI_API_KEY'
            },
            anthropic: {
                label: 'Claude API Key',
                models: ['claude-3-opus', 'claude-3-sonnet'],
                envKey: 'ANTHROPIC_API_KEY'
            }
        };
    }

    initProviderSelect() {
        this.providerSelect.innerHTML = Object.entries(this.modelConfigs)
            .map(([key, config]) => `
                <option value="${key}">${config.label.split(' API Key')[0]}</option>
            `)
            .join('');
    }

    updateProviderUI() {
        const provider = this.providerSelect.value;
        
        // 更新API密钥输入区域
        this.keysContainer.innerHTML = this.createKeyInput(
            this.modelConfigs[provider].label,
            this.modelConfigs[provider].envKey
        );

        // 更新模型选择器
        this.modelSelect.innerHTML = this.modelConfigs[provider].models
            .map(model => `<option value="${model}">${model}</option>`)
            .join('');
            
        // 为密码可见性切换添加事件监听
        const toggles = document.querySelectorAll('.toggle-visibility');
        toggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                const input = e.target.previousElementSibling;
                const type = input.type === 'password' ? 'text' : 'password';
                input.type = type;
                e.target.innerHTML = type === 'password' ? '👁️' : '👁️‍🗨️';
            });
        });
    }

    createKeyInput(label, envKey) {
        return `
            <div class="api-key-input">
                <label>${label}</label>
                <div style="position: relative;">
                    <input type="password" 
                           data-env-key="${envKey}" 
                           placeholder="Enter API Key">
                    <span class="toggle-visibility">👁️</span>
                </div>
            </div>
        `;
    }

    initAPIForm() {
        const submitBtn = document.querySelector('.api-submit-btn');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                const provider = this.providerSelect.value;
                const model = this.modelSelect.value;
                const apiKey = document.querySelector(`[data-env-key="${this.modelConfigs[provider].envKey}"]`).value;

                if (window.ws && window.ws.readyState === WebSocket.OPEN) {
                    window.ws.send(JSON.stringify({
                        type: 'api_settings',
                        data: {
                            provider: provider,
                            model: model,
                            apiKey: apiKey,
                            envKey: this.modelConfigs[provider].envKey
                        }
                    }));
                }
            });
        }
    }
}

// 初始化API面板
document.addEventListener('DOMContentLoaded', () => {
    new APIPanel();
});
