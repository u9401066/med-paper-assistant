import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getPythonArgs, loadSkillsAsInstructions, loadSkillContent, BUNDLED_SKILLS, BUNDLED_PROMPTS, BUNDLED_TEMPLATES } from './utils';

let outputChannel: vscode.OutputChannel;

export function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('MedPaper Assistant');
    outputChannel.appendLine('MedPaper Assistant is activating...');

    // Register MCP Server Definition Provider
    const mcpProvider = registerMcpServerProvider(context);
    context.subscriptions.push(mcpProvider);

    // Register Chat Participant Handler (optional enhancement)
    const chatHandler = registerChatParticipant(context);
    if (chatHandler) {
        context.subscriptions.push(chatHandler);
    }

    // Register Commands
    context.subscriptions.push(
        vscode.commands.registerCommand('mdpaper.startServer', () => {
            vscode.window.showInformationMessage('MedPaper MCP Server is managed automatically by VS Code.');
        }),
        vscode.commands.registerCommand('mdpaper.stopServer', () => {
            vscode.window.showInformationMessage('MedPaper MCP Server will stop when VS Code closes.');
        }),
        vscode.commands.registerCommand('mdpaper.showStatus', () => {
            outputChannel.show();
            outputChannel.appendLine(`[${new Date().toISOString()}] MedPaper Assistant Status: Active`);
        }),
        vscode.commands.registerCommand('mdpaper.autoPaper', () => {
            // Check if journal-profile template exists in workspace
            const wsFolder = vscode.workspace.workspaceFolders?.[0];
            if (wsFolder) {
                const templatePath = path.join(wsFolder.uri.fsPath, 'templates', 'journal-profile.template.yaml');
                if (!fs.existsSync(templatePath)) {
                    const bundledTemplate = path.join(context.extensionPath, 'templates', 'journal-profile.template.yaml');
                    if (fs.existsSync(bundledTemplate)) {
                        vscode.window.showWarningMessage(
                            'MedPaper: journal-profile.template.yaml 尚未存在於 workspace。Auto Paper Phase 0 需要此模板。要複製嗎？',
                            '複製模板', '稍後再說'
                        ).then(selection => {
                            if (selection === '複製模板') {
                                fs.mkdirSync(path.dirname(templatePath), { recursive: true });
                                fs.copyFileSync(bundledTemplate, templatePath);
                                vscode.window.showInformationMessage('MedPaper: journal-profile.template.yaml 已複製到 templates/');
                            }
                        });
                    }
                }
            }
            // Open Copilot chat with autopaper command
            vscode.commands.executeCommand('workbench.action.chat.open', {
                query: '@mdpaper /autopaper 全自動寫論文'
            });
        }),
        vscode.commands.registerCommand('mdpaper.setupWorkspace', () => {
            setupWorkspace(context);
        })
    );

    outputChannel.appendLine('MedPaper Assistant activated successfully!');
}

function registerMcpServerProvider(context: vscode.ExtensionContext): vscode.Disposable {
    // Check if user has their own mcp.json - if so, skip auto-registration
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders) {
        const mcpJsonPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'mcp.json');
        if (fs.existsSync(mcpJsonPath)) {
            outputChannel.appendLine('[MCP] Found .vscode/mcp.json - skipping auto-registration (use local config instead)');
            // Return a no-op disposable
            return { dispose: () => {} };
        }
    }

    // Skills are loaded from the extension's bundled directory
    // and used by the chat participant for /autopaper command

    const provider: vscode.McpServerDefinitionProvider = {
        onDidChangeMcpServerDefinitions: new vscode.EventEmitter<void>().event,

        provideMcpServerDefinitions(token: vscode.CancellationToken): vscode.ProviderResult<vscode.McpServerDefinition[]> {
            const pythonPath = getPythonPath(context);
            const workspaceFolders = vscode.workspace.workspaceFolders;

            outputChannel.appendLine(`[MCP] Using Python Path: ${pythonPath}`);

            // Determine PYTHONPATH
            // Include bundled tools and workspace src (for development)
            let pythonPathEnv = path.join(context.extensionPath, 'bundled', 'tool');
            if (workspaceFolders) {
                const srcPath = path.join(workspaceFolders[0].uri.fsPath, 'src');
                const integrationsPath = path.join(workspaceFolders[0].uri.fsPath, 'integrations');

                if (fs.existsSync(srcPath)) {
                    pythonPathEnv = `${srcPath}${path.delimiter}${pythonPathEnv}`;
                }

                // Add integration src paths for development
                const cguSrc = path.join(integrationsPath, 'cgu', 'src');
                if (fs.existsSync(cguSrc)) {
                    pythonPathEnv = `${cguSrc}${path.delimiter}${pythonPathEnv}`;
                }
            }

            const definitions: vscode.McpServerDefinition[] = [];

            // 1. MedPaper Assistant
            const mdpaperArgs = getPythonArgs(pythonPath, 'med_paper_assistant.interfaces.mcp');
            outputChannel.appendLine(`[MCP] MedPaper Args: ${mdpaperArgs.join(' ')}`);
            definitions.push(new vscode.McpStdioServerDefinition(
                'MedPaper Assistant',
                pythonPath,
                mdpaperArgs,
                {
                    PYTHONPATH: pythonPathEnv
                }
            ));

            // 2. CGU (only if available in workspace or bundled)
            const cguBundled = path.join(context.extensionPath, 'bundled', 'tool', 'cgu');
            const cguInWorkspace = workspaceFolders
                ? fs.existsSync(path.join(workspaceFolders[0].uri.fsPath, 'integrations', 'cgu', 'src', 'cgu'))
                : false;
            if (cguBundled && fs.existsSync(cguBundled) || cguInWorkspace || pythonPath === 'uvx') {
                const cguArgs = getPythonArgs(pythonPath, 'cgu.server');
                outputChannel.appendLine(`[MCP] CGU Args: ${cguArgs.join(' ')}`);
                definitions.push(new vscode.McpStdioServerDefinition(
                    'CGU Creativity',
                    pythonPath,
                    cguArgs,
                    {
                        PYTHONPATH: pythonPathEnv
                    }
                ));
            } else {
                outputChannel.appendLine('[MCP] CGU not found — skipping registration');
            }

            // 3. Draw.io (only register, will fail gracefully if uvx/drawio-mcp not installed)
            definitions.push(new vscode.McpStdioServerDefinition(
                'Draw.io Diagrams',
                'uvx',
                ['--from', 'drawio-mcp', 'drawio-mcp-server'],
                {
                    DRAWIO_NEXTJS_URL: 'http://localhost:3000'
                }
            ));

            return definitions;
        },

        resolveMcpServerDefinition(
            definition: vscode.McpServerDefinition,
            token: vscode.CancellationToken
        ): vscode.ProviderResult<vscode.McpServerDefinition> {
            outputChannel.appendLine(`Resolving MCP server: ${definition.label}`);
            return definition;
        }
    };

    // Use VS Code API to register the provider
    return vscode.lm.registerMcpServerDefinitionProvider('mdpaper', provider);
}



function registerChatParticipant(context: vscode.ExtensionContext): vscode.Disposable | null {
    try {
        // Pre-load skill summaries for chat context
        const skillsPath = path.join(context.extensionPath, 'skills');

        const handler: vscode.ChatRequestHandler = async (
            request: vscode.ChatRequest,
            chatContext: vscode.ChatContext,
            stream: vscode.ChatResponseStream,
            token: vscode.CancellationToken
        ) => {
            // Handle different commands
            switch (request.command) {
                case 'search':
                    stream.markdown('🔍 **文獻搜尋模式**\n\n');
                    stream.markdown('在 Agent Mode 中，我可以使用以下 MCP 工具：\n');
                    stream.markdown('- `search_literature` - PubMed 搜尋\n');
                    stream.markdown('- `find_related_articles` - 相關文獻\n');
                    stream.markdown('- `save_reference_mcp` - 儲存文獻\n\n');
                    stream.markdown('💡 請切換到 **Agent Mode** 使用完整功能。');
                    break;

                case 'draft':
                    stream.markdown('✍️ **草稿撰寫模式**\n\n');
                    stream.markdown('在 Agent Mode 中，我可以：\n');
                    stream.markdown('- 撰寫 Introduction、Methods、Results、Discussion\n');
                    stream.markdown('- 自動插入 [[wikilink]] 引用\n');
                    stream.markdown('- 字數控制和 Anti-AI 檢查\n\n');
                    stream.markdown('💡 請切換到 **Agent Mode** 使用完整功能。');
                    break;

                case 'concept':
                    stream.markdown('💡 **研究概念發展**\n\n');
                    stream.markdown('在 Agent Mode 中，我可以：\n');
                    stream.markdown('- 發展研究概念 (concept.md)\n');
                    stream.markdown('- 驗證 novelty（三輪評分）\n');
                    stream.markdown('- 文獻缺口分析\n\n');
                    stream.markdown('💡 請切換到 **Agent Mode** 使用完整功能。');
                    break;

                case 'project':
                    stream.markdown('📁 **專案管理**\n\n');
                    stream.markdown('在 Agent Mode 中，使用以下工具：\n');
                    stream.markdown('- `create_project` / `list_projects` / `switch_project`\n');
                    stream.markdown('- `setup_project_interactive` - 互動設定\n');
                    stream.markdown('- `get_paper_types` - 可用論文類型\n\n');
                    stream.markdown('💡 請切換到 **Agent Mode** 使用完整功能。');
                    break;

                case 'format':
                    stream.markdown('📄 **Word 匯出**\n\n');
                    stream.markdown('匯出流程：\n');
                    stream.markdown('1. `list_templates` → 選擇模板\n');
                    stream.markdown('2. `start_document_session` → 開始編輯\n');
                    stream.markdown('3. `insert_section` → 插入各章節\n');
                    stream.markdown('4. `save_document` → 儲存 .docx\n\n');
                    stream.markdown('💡 請切換到 **Agent Mode** 使用完整功能。');
                    break;

                case 'autopaper': {
                    // Load auto-paper skill
                    const autoPaperSkill = loadSkillContent(skillsPath, 'auto-paper');
                    stream.markdown('🚀 **全自動論文撰寫 (Auto Paper)**\n\n');
                    stream.markdown('### 11-Phase Pipeline + 42 Hooks\n\n');
                    stream.markdown('| Phase | 名稱 | 說明 |\n');
                    stream.markdown('|-------|------|------|\n');
                    stream.markdown('| 0 | 期刊定位 | journal-profile.yaml 設定 |\n');
                    stream.markdown('| 1 | 寫作計畫 | manuscript-plan.yaml 產出 |\n');
                    stream.markdown('| 2 | 文獻搜索 | 並行搜尋 + 儲存 |\n');
                    stream.markdown('| 3 | 概念發展 | concept.md 撰寫 |\n');
                    stream.markdown('| 4 | Novelty 驗證 | 三輪評分 ≥ 75 |\n');
                    stream.markdown('| 5 | 逐節撰寫 | Introduction → Methods → Results → Discussion |\n');
                    stream.markdown('| 6 | 引用同步 | sync_references |\n');
                    stream.markdown('| 7 | 全稿審查 | Autonomous Review |\n');
                    stream.markdown('| 8 | Word 匯出 | 產生 .docx |\n');
                    stream.markdown('| 9 | 投稿準備 | Cover letter, checklist |\n');
                    stream.markdown('| 10 | Meta-Learning | 更新 SKILL + Hooks |\n\n');
                    stream.markdown('### 品質保證：42 Checks（4 層 Audit Hooks）\n\n');
                    stream.markdown('- **Hook A** (post-write): 字數、引用密度、Anti-AI、Wikilink\n');
                    stream.markdown('- **Hook B** (post-section): 概念一致、🔒 保護、方法學、寫作順序\n');
                    stream.markdown('- **Hook C** (post-manuscript): 全稿一致性、投稿清單、時間一致性\n');
                    stream.markdown('- **Hook D** (meta-learning): SKILL/Hook 自我改進\n\n');
                    if (autoPaperSkill) {
                        stream.markdown('---\n\n<details><summary>📖 完整 Auto-Paper Skill</summary>\n\n');
                        stream.markdown(autoPaperSkill);
                        stream.markdown('\n\n</details>\n\n');
                    }
                    stream.markdown('💡 **請切換到 Agent Mode**，然後輸入「全自動寫論文」開始。');
                    break;
                }

                case 'analysis':
                    stream.markdown('📊 **資料分析模式**\n\n');
                    stream.markdown('在 Agent Mode 中，可用工具：\n');
                    stream.markdown('- `analyze_dataset` - 摘要統計\n');
                    stream.markdown('- `run_statistical_test` - t-test、correlation 等\n');
                    stream.markdown('- `create_plot` - 建立圖表\n');
                    stream.markdown('- `generate_table_one` - 生成 Table 1\n\n');
                    stream.markdown('💡 請切換到 **Agent Mode** 使用完整功能。');
                    break;

                case 'strategy':
                    stream.markdown('🎯 **搜尋策略設定**\n\n');
                    stream.markdown('在 Agent Mode 中，我可以：\n');
                    stream.markdown('- 定義搜尋關鍵字和 MeSH terms\n');
                    stream.markdown('- 設定 inclusion/exclusion criteria\n');
                    stream.markdown('- 產生多組搜尋查詢並行執行\n\n');
                    stream.markdown('💡 請切換到 **Agent Mode** 使用完整功能。');
                    break;

                case 'help':
                    stream.markdown('## 📚 MedPaper Assistant 完整指令列表\n\n');
                    stream.markdown('### 💬 Chat 指令 (@mdpaper)\n\n');
                    stream.markdown('| 指令 | 說明 |\n');
                    stream.markdown('|------|------|\n');
                    stream.markdown('| `/search` | 搜尋 PubMed 文獻 |\n');
                    stream.markdown('| `/draft` | 撰寫論文章節 |\n');
                    stream.markdown('| `/concept` | 發展研究概念 |\n');
                    stream.markdown('| `/project` | 管理研究專案 |\n');
                    stream.markdown('| `/format` | 匯出 Word 文件 |\n');
                    stream.markdown('| `/autopaper` | 🚀 全自動寫論文 |\n');
                    stream.markdown('| `/analysis` | 資料分析與統計 |\n');
                    stream.markdown('| `/strategy` | 搜尋策略設定 |\n');
                    stream.markdown('| `/help` | 顯示本說明 |\n\n');
                    stream.markdown('### 🎯 Command Palette (Ctrl+Shift+P)\n\n');
                    stream.markdown('| 指令 | 說明 |\n');
                    stream.markdown('|------|------|\n');
                    stream.markdown('| `MedPaper: Auto Paper` | 全自動寫論文 |\n');
                    stream.markdown('| `MedPaper: Show Status` | 顯示狀態 |\n\n');
                    stream.markdown('### 🔧 Agent Mode 自然語言\n\n');
                    stream.markdown('直接在 Agent Mode 輸入：\n');
                    stream.markdown('- 「全自動寫論文」「一鍵寫論文」→ Auto Paper Pipeline\n');
                    stream.markdown('- 「找論文」「搜尋 PubMed」→ 文獻搜尋\n');
                    stream.markdown('- 「寫 Introduction」→ 草稿撰寫\n');
                    stream.markdown('- 「驗證 novelty」→ 概念驗證\n');
                    break;

                default:
                    // General query - provide guidance
                    stream.markdown(`## MedPaper Assistant\n\n`);
                    stream.markdown(`您好！我是 MedPaper Assistant，專門協助醫學論文撰寫。\n\n`);
                    stream.markdown(`### ⭐ 主打功能\n`);
                    stream.markdown(`- \`/autopaper\` - 🚀 **全自動寫論文** (9-Phase Pipeline + Hooks)\n\n`);
                    stream.markdown(`### 所有指令\n`);
                    stream.markdown(`- \`/search\` - 搜尋 PubMed 文獻\n`);
                    stream.markdown(`- \`/draft\` - 撰寫論文章節\n`);
                    stream.markdown(`- \`/concept\` - 發展研究概念\n`);
                    stream.markdown(`- \`/project\` - 管理研究專案\n`);
                    stream.markdown(`- \`/format\` - 匯出 Word 文件\n`);
                    stream.markdown(`- \`/analysis\` - 資料分析\n`);
                    stream.markdown(`- \`/strategy\` - 搜尋策略\n`);
                    stream.markdown(`- \`/help\` - 顯示完整說明\n\n`);
                    stream.markdown(`💡 **建議**：在 Agent Mode 中使用以獲得完整的 MCP 工具支援。`);
            }

            return { metadata: { command: request.command } };
        };

        const participant = vscode.chat.createChatParticipant('medpaper.assistant', handler);
        participant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'media', 'icon.png');

        // Follow-up provider
        participant.followupProvider = {
            provideFollowups(result, context, token) {
                return [
                    { prompt: '全自動寫論文', label: '🚀 Auto Paper', command: 'autopaper' },
                    { prompt: '搜尋相關文獻', label: '🔍 Search Literature', command: 'search' },
                    { prompt: '開始撰寫草稿', label: '✍️ Start Drafting', command: 'draft' },
                    { prompt: '驗證研究概念', label: '💡 Validate Concept', command: 'concept' }
                ];
            }
        };

        return participant;
    } catch (error) {
        outputChannel.appendLine(`Chat participant registration skipped: ${error}`);
        return null;
    }
}

function getPythonPath(context: vscode.ExtensionContext): string {
    // 1. Check user configuration
    const config = vscode.workspace.getConfiguration('mdpaper');
    const configuredPath = config.get<string>('pythonPath');
    if (configuredPath) {
        // If it's just "uv" or "uvx", return it as is
        if (configuredPath === 'uv' || configuredPath === 'uvx') {
            return configuredPath;
        }
        if (fs.existsSync(configuredPath)) {
            return configuredPath;
        }
    }

    // 2. Prefer 'uv' if workspace has pyproject.toml (uv-managed project)
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders) {
        const pyprojectPath = path.join(workspaceFolders[0].uri.fsPath, 'pyproject.toml');
        if (fs.existsSync(pyprojectPath)) {
            // This is likely a uv-managed project, use 'uv' to ensure proper environment
            return 'uv';
        }
    }

    // 3. Check for virtual environment in workspace (fallback for non-uv projects)
    if (workspaceFolders) {
        for (const folder of workspaceFolders) {
            const venvPaths = [
                path.join(folder.uri.fsPath, '.venv', 'bin', 'python'),
                path.join(folder.uri.fsPath, '.venv', 'bin', 'python3'),
                path.join(folder.uri.fsPath, '.venv', 'Scripts', 'python.exe'),
                path.join(folder.uri.fsPath, 'venv', 'bin', 'python'),
                path.join(folder.uri.fsPath, 'venv', 'Scripts', 'python.exe'),
            ];
            for (const venvPath of venvPaths) {
                if (fs.existsSync(venvPath)) {
                    return venvPath;
                }
            }
        }
    }

    // 4. Check bundled Python (for standalone distribution)
    const bundledPython = path.join(context.extensionPath, 'bundled', 'python', 'bin', 'python3');
    if (fs.existsSync(bundledPython)) {
        return bundledPython;
    }

    // 5. Prefer uvx for auto-install from PyPI (one-click experience)
    return 'uvx';
}



async function setupWorkspace(context: vscode.ExtensionContext): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('請先開啟一個 workspace 資料夾。');
        return;
    }

    const wsRoot = workspaceFolders[0].uri.fsPath;
    const extPath = context.extensionPath;
    let copied = 0;

    // 1. Copy skills → .claude/skills/
    for (const skill of BUNDLED_SKILLS) {
        const src = path.join(extPath, 'skills', skill, 'SKILL.md');
        const dst = path.join(wsRoot, '.claude', 'skills', skill, 'SKILL.md');
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(src, dst);
            copied++;
        }
    }

    // 2. Copy prompts → .github/prompts/
    for (const prompt of BUNDLED_PROMPTS) {
        const src = path.join(extPath, 'prompts', `${prompt}.prompt.md`);
        const dst = path.join(wsRoot, '.github', 'prompts', `${prompt}.prompt.md`);
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(src, dst);
            copied++;
        }
    }

    // 3. Copy _capability-index.md
    const idxSrc = path.join(extPath, 'prompts', '_capability-index.md');
    const idxDst = path.join(wsRoot, '.github', 'prompts', '_capability-index.md');
    if (fs.existsSync(idxSrc) && !fs.existsSync(idxDst)) {
        fs.mkdirSync(path.dirname(idxDst), { recursive: true });
        fs.copyFileSync(idxSrc, idxDst);
        copied++;
    }

    // 4. Copy copilot-instructions.md (only if not exists)
    const instrSrc = path.join(extPath, 'copilot-instructions.md');
    const instrDst = path.join(wsRoot, '.github', 'copilot-instructions.md');
    if (fs.existsSync(instrSrc) && !fs.existsSync(instrDst)) {
        fs.mkdirSync(path.dirname(instrDst), { recursive: true });
        fs.copyFileSync(instrSrc, instrDst);
        copied++;
    }

    // 5. Copy templates → templates/ (overwrite if outdated)
    for (const tmpl of BUNDLED_TEMPLATES) {
        const src = path.join(extPath, 'templates', tmpl);
        const dst = path.join(wsRoot, 'templates', tmpl);
        if (fs.existsSync(src)) {
            const needsCopy = !fs.existsSync(dst) ||
                fs.readFileSync(src, 'utf-8') !== fs.readFileSync(dst, 'utf-8');
            if (needsCopy) {
                fs.mkdirSync(path.dirname(dst), { recursive: true });
                fs.copyFileSync(src, dst);
                copied++;
            }
        } else {
            outputChannel.appendLine(`[Setup] ⚠️ Bundled template missing: ${tmpl}`);
        }
    }

    if (copied > 0) {
        vscode.window.showInformationMessage(
            `MedPaper: 已設定 ${copied} 個檔案（skills、prompts、instructions、templates）到 workspace。重新載入視窗以啟用全部功能。`,
            '重新載入'
        ).then(selection => {
            if (selection === '重新載入') {
                vscode.commands.executeCommand('workbench.action.reloadWindow');
            }
        });
    } else {
        vscode.window.showInformationMessage('MedPaper: Workspace 已是最新，無需更新。');
    }

    outputChannel.appendLine(`[Setup] Copied ${copied} files to workspace`);
}

export function deactivate() {
    outputChannel?.appendLine('MedPaper Assistant deactivated.');
}
