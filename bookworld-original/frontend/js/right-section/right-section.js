// right-section.js
class RightSection {
    constructor() {
        this.currentTab = 'api-panel';
        this.apiPanel = new APIPanel();
        this.settingsPanel = new SettingsPanel();
        this.init();
    }

    init() {
        this.initTabSwitching();
        
        // WebSocket监听
        window.addEventListener('websocket-message', (event) => {
            const message = event.detail;
            if (message.type === 'initial_data' && message.data.settings) {
                this.settingsPanel.updateSettings(message.data.settings);
            }
        });
    }

    initTabSwitching() {
        const tabButtons = document.querySelectorAll('.right-toolbar .tab-btn');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                
                const targetPanelId = button.getAttribute('data-target');
                
                tabButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                document.querySelectorAll('.tab-panel').forEach(panel => {
                    panel.classList.remove('active');
                });
                document.getElementById(targetPanelId).classList.add('active');
                
                this.currentTab = targetPanelId;
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const rightSection = new RightSection();
});
