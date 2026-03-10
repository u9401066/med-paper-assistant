import * as vscode from 'vscode';

const DRAWIO_WEB_URL = 'http://localhost:6002';

let currentPanel: DrawioPanel | undefined;

/**
 * WebviewPanel wrapper for embedding Draw.io editor inside VS Code.
 *
 * Architecture:
 * - Extension ←→ Webview: postMessage (VS Code API)
 * - Webview ←→ Draw.io API: fetch() to localhost:6002/api/mcp
 * - Polls for user save events every 3 seconds
 */
export class DrawioPanel {
    public static readonly viewType = 'mdpaper.drawioEditor';
    private readonly _panel: vscode.WebviewPanel;
    private readonly _disposables: vscode.Disposable[] = [];
    private _onDidSaveDiagram = new vscode.EventEmitter<{ xml: string; tabName: string }>();

    /** Fires when the user saves a diagram in the Draw.io editor. */
    public readonly onDidSaveDiagram = this._onDidSaveDiagram.event;

    /**
     * Create or reveal the Draw.io WebviewPanel.
     * Returns the singleton DrawioPanel instance.
     */
    public static createOrShow(): DrawioPanel {
        const column = vscode.ViewColumn.Beside;

        if (currentPanel) {
            currentPanel._panel.reveal(column);
            return currentPanel;
        }

        const panel = vscode.window.createWebviewPanel(
            DrawioPanel.viewType,
            'Draw.io Editor',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        currentPanel = new DrawioPanel(panel);
        return currentPanel;
    }

    /** Get the current panel instance if it exists. */
    public static get current(): DrawioPanel | undefined {
        return currentPanel;
    }

    private constructor(panel: vscode.WebviewPanel) {
        this._panel = panel;
        this._panel.webview.html = this._getHtml();
        this._panel.iconPath = vscode.Uri.parse('data:image/svg+xml,' + encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><text y="13" font-size="13">📐</text></svg>'
        ));

        this._panel.onDidDispose(() => {
            currentPanel = undefined;
            this._dispose();
        }, null, this._disposables);

        this._panel.webview.onDidReceiveMessage(
            this._handleMessage.bind(this),
            null,
            this._disposables
        );
    }

    /** Underlying WebviewPanel. */
    public get panel(): vscode.WebviewPanel {
        return this._panel;
    }

    /**
     * Load a diagram XML into the Draw.io editor.
     * Sends the XML to the Draw.io frontend via its HTTP API (relayed through the webview).
     */
    public async loadDiagram(xml: string, tabName?: string): Promise<void> {
        await this._panel.webview.postMessage({
            command: 'loadDiagram',
            xml,
            tabName: tabName || 'Diagram',
        });
    }

    /**
     * Request the current diagram content from the Draw.io editor.
     * Returns the XML string, or null on timeout/error.
     */
    public getDiagramXml(): Promise<string | null> {
        return new Promise<string | null>((resolve) => {
            const timeout = setTimeout(() => {
                listener.dispose();
                resolve(null);
            }, 5000);

            const listener = this._panel.webview.onDidReceiveMessage(msg => {
                if (msg.type === 'diagramContent') {
                    clearTimeout(timeout);
                    listener.dispose();
                    resolve(msg.xml || null);
                }
            });

            this._panel.webview.postMessage({ command: 'getDiagramContent' });
        });
    }

    /**
     * Request the list of open tabs from the Draw.io editor.
     */
    public getTabs(): Promise<Array<{ id: string; name: string; active: boolean }>> {
        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                listener.dispose();
                resolve([]);
            }, 5000);

            const listener = this._panel.webview.onDidReceiveMessage(msg => {
                if (msg.type === 'tabsList') {
                    clearTimeout(timeout);
                    listener.dispose();
                    resolve(msg.tabs || []);
                }
            });

            this._panel.webview.postMessage({ command: 'getTabs' });
        });
    }

    private _handleMessage(message: Record<string, unknown>) {
        switch (message.type) {
            case 'ready':
                // Webview iframe loaded successfully
                break;
            case 'diagramSaved':
                this._onDidSaveDiagram.fire({
                    xml: message.xml as string,
                    tabName: (message.tabName as string) || '',
                });
                break;
            case 'error':
                vscode.window.showErrorMessage(`Draw.io: ${message.message}`);
                break;
        }
    }

    private _getHtml(): string {
        const nonce = getNonce();
        return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'none';
                   frame-src ${DRAWIO_WEB_URL};
                   connect-src ${DRAWIO_WEB_URL};
                   script-src 'nonce-${nonce}';
                   style-src 'unsafe-inline';">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Draw.io Editor</title>
    <style>
        body, html {
            margin: 0; padding: 0;
            width: 100%; height: 100%;
            overflow: hidden;
            background: var(--vscode-editor-background, #1e1e1e);
        }
        iframe { width: 100%; height: 100%; border: none; }
        .loading {
            display: flex; align-items: center; justify-content: center;
            height: 100%;
            font-family: var(--vscode-font-family, sans-serif);
            color: var(--vscode-foreground, #ccc);
            font-size: 14px;
            flex-direction: column; gap: 12px;
        }
        .loading .spinner {
            width: 24px; height: 24px;
            border: 3px solid var(--vscode-foreground, #ccc);
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <span>正在載入 Draw.io Editor...</span>
    </div>
    <iframe id="drawio-frame" src="${DRAWIO_WEB_URL}" style="display:none;"></iframe>
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const iframe = document.getElementById('drawio-frame');
        const loading = document.getElementById('loading');
        const API_URL = '${DRAWIO_WEB_URL}/api/mcp';

        // --- Iframe lifecycle ---
        iframe.onload = () => {
            loading.style.display = 'none';
            iframe.style.display = 'block';
            vscode.postMessage({ type: 'ready' });
        };
        iframe.onerror = () => {
            loading.querySelector('span').textContent =
                '無法載入 Draw.io。請確認 Draw.io Web Server 已啟動。';
            loading.querySelector('.spinner').style.display = 'none';
            vscode.postMessage({ type: 'error', message: 'Failed to load Draw.io editor' });
        };

        // --- Handle commands from extension ---
        window.addEventListener('message', async (event) => {
            const msg = event.data;
            if (!msg || !msg.command) return;

            switch (msg.command) {
                case 'getDiagramContent': {
                    try {
                        const resp = await fetch(API_URL + '?action=get');
                        const data = await resp.json();
                        vscode.postMessage({
                            type: 'diagramContent',
                            xml: data.xml || null,
                            tabId: data.tabId,
                            tabName: data.tabName,
                        });
                    } catch (e) {
                        vscode.postMessage({ type: 'diagramContent', xml: null, error: String(e) });
                    }
                    break;
                }
                case 'loadDiagram': {
                    try {
                        const resp = await fetch(API_URL, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                action: 'display',
                                xml: msg.xml,
                                tabName: msg.tabName,
                            }),
                        });
                        const data = await resp.json();
                        vscode.postMessage({ type: 'diagramLoaded', tabId: data.tabId });
                    } catch (e) {
                        vscode.postMessage({
                            type: 'error',
                            message: 'Failed to load diagram: ' + String(e),
                        });
                    }
                    break;
                }
                case 'getTabs': {
                    try {
                        const resp = await fetch('${DRAWIO_WEB_URL}/api/tabs');
                        const data = await resp.json();
                        vscode.postMessage({ type: 'tabsList', tabs: data.tabs || [] });
                    } catch (e) {
                        vscode.postMessage({ type: 'tabsList', tabs: [] });
                    }
                    break;
                }
            }
        });

        // --- Poll for user save events (Phase 3 bidirectional) ---
        let lastEventTime = 0;
        setInterval(async () => {
            try {
                const resp = await fetch(
                    API_URL + '?action=events&since=' + lastEventTime
                );
                const data = await resp.json();
                if (data.events && data.events.length > 0) {
                    for (const event of data.events) {
                        if (event.type === 'save') {
                            vscode.postMessage({
                                type: 'diagramSaved',
                                tabName: event.tabName,
                                xml: event.xml,
                            });
                        }
                        lastEventTime = Math.max(
                            lastEventTime,
                            event.timestamp || 0
                        );
                    }
                }
            } catch (_) {
                // Silently ignore polling errors
            }
        }, 3000);
    </script>
</body>
</html>`;
    }

    private _dispose() {
        this._onDidSaveDiagram.dispose();
        while (this._disposables.length) {
            this._disposables.pop()?.dispose();
        }
    }
}

function getNonce(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < 32; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}
