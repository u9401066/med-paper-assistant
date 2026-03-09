import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getPythonArgs, loadSkillsAsInstructions, loadSkillContent, BUNDLED_SKILLS, BUNDLED_PROMPTS, BUNDLED_TEMPLATES, BUNDLED_AGENTS } from './utils';
import { findUvPath, installUvHeadless, getUvxPath, buildUvxCommand, buildMcpCommand, buildMcpEnv, ensureInstalledTool } from './uvManager';
import { shouldSkipMcpRegistration, isDevWorkspace as checkIsDevWorkspace, determinePythonPath, countMissingBundledItems, buildDevPythonPath } from './extensionHelpers';

let outputChannel: vscode.OutputChannel;
let resolvedUvPath: string | null = null;

export async function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('MedPaper Assistant');
    outputChannel.appendLine('MedPaper Assistant is activating...');

    // Step 1: Ensure uv is installed (needed for MCP server)
    await ensureUvReady(context);

    // Step 1.5: Marketplace mode auto-installs required persistent tool binaries.
    await ensureMarketplaceToolsReady(context);

    // Step 2: Register MCP Server Definition Provider
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

    // Auto-scaffold: check if workspace is missing skills/agents/prompts
    // Only prompt once per workspace (use globalState to track)
    autoScaffoldIfNeeded(context);

    outputChannel.appendLine('MedPaper Assistant activated successfully!');
}

/**
 * Ensure uv is installed. If not, offer to auto-install.
 * Stores the resolved uv path in module-level variable and globalState.
 */
async function ensureUvReady(context: vscode.ExtensionContext): Promise<void> {
    const log = (msg: string) => outputChannel.appendLine(`[uv] ${msg}`);

    log('Checking uv installation...');
    resolvedUvPath = await findUvPath(log);

    if (resolvedUvPath) {
        log(`uv is ready: ${resolvedUvPath}`);
        context.globalState.update('uvPath', resolvedUvPath);
        return;
    }

    // uv not found — offer auto-install
    log('uv not found, prompting user...');
    const choice = await vscode.window.showInformationMessage(
        'MedPaper Assistant 需要 "uv" (Python 套件管理器) 才能運行。要自動安裝嗎？\n安裝後會自動處理 Python 和所有相依套件。',
        '自動安裝 uv',
        '手動安裝',
        '取消'
    );

    if (choice === '自動安裝 uv') {
        resolvedUvPath = await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'MedPaper: 正在安裝 uv...',
                cancellable: false
            },
            async (progress) => {
                progress.report({ message: '下載並安裝 uv (Python 套件管理器)...' });
                const installed = await installUvHeadless(log);

                if (installed) {
                    progress.report({ message: '安裝完成！' });
                    context.globalState.update('uvPath', installed);

                    const reload = await vscode.window.showInformationMessage(
                        '✅ uv 安裝成功！請重新載入 VS Code 以完成設定。',
                        '重新載入'
                    );
                    if (reload === '重新載入') {
                        vscode.commands.executeCommand('workbench.action.reloadWindow');
                    }
                } else {
                    vscode.window.showErrorMessage(
                        'uv 安裝失敗。請手動安裝: https://docs.astral.sh/uv/',
                        '開啟安裝頁面'
                    ).then(c => {
                        if (c === '開啟安裝頁面') {
                            vscode.env.openExternal(vscode.Uri.parse('https://docs.astral.sh/uv/getting-started/installation/'));
                        }
                    });
                }
                return installed;
            }
        );
    } else if (choice === '手動安裝') {
        vscode.env.openExternal(vscode.Uri.parse('https://docs.astral.sh/uv/getting-started/installation/'));
    }
    // choice === '取消' → resolvedUvPath stays null
}

async function ensureMarketplaceToolsReady(context: vscode.ExtensionContext): Promise<void> {
    if (!resolvedUvPath) {
        outputChannel.appendLine('[Install] Skipping tool auto-install because uv is not ready.');
        return;
    }

    const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const isDevWorkspace = wsRoot ? checkIsDevWorkspace(wsRoot) : false;
    if (isDevWorkspace) {
        outputChannel.appendLine('[Install] Development workspace detected - skipping marketplace tool auto-install.');
        return;
    }

    if (wsRoot) {
        const mcpJsonPath = path.join(wsRoot, '.vscode', 'mcp.json');
        if (fs.existsSync(mcpJsonPath)) {
            try {
                const content = fs.readFileSync(mcpJsonPath, 'utf-8');
                if (shouldSkipMcpRegistration(content)) {
                    outputChannel.appendLine('[Install] User-managed mcp.json detected - skipping marketplace tool auto-install.');
                    return;
                }
            } catch {
                outputChannel.appendLine('[Install] Could not inspect .vscode/mcp.json - continuing with marketplace tool checks.');
            }
        }
    }

    const bundledToolPath = path.join(context.extensionPath, 'bundled', 'tool');
    const hasCguBundled = fs.existsSync(path.join(bundledToolPath, 'cgu'));
    const cguInWorkspace = wsRoot
        ? fs.existsSync(path.join(wsRoot, 'integrations', 'cgu', 'src', 'cgu'))
        : false;

    const toolSpecs: Array<{ packageName: string; binaryName?: string }> = [
        { packageName: 'med-paper-assistant' },
        { packageName: 'pubmed-search-mcp' },
        { packageName: 'zotero-keeper' },
        { packageName: 'drawio-mcp', binaryName: 'drawio-mcp-server' },
    ];

    if (hasCguBundled || cguInWorkspace) {
        toolSpecs.push({ packageName: 'creativity-generation-unit', binaryName: 'cgu-server' });
    }

    const log = (msg: string) => outputChannel.appendLine(`[Install] ${msg}`);

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'MedPaper: 正在檢查並安裝 MCP 相依套件...',
            cancellable: false,
        },
        async (progress) => {
            const total = toolSpecs.length;
            for (let i = 0; i < total; i++) {
                const spec = toolSpecs[i];
                progress.report({
                    message: `檢查 ${spec.binaryName || spec.packageName} (${i + 1}/${total})`,
                    increment: 100 / total,
                });
                await ensureInstalledTool(spec.packageName, spec.binaryName, undefined, log);
            }
        }
    );
}

function registerMcpServerProvider(context: vscode.ExtensionContext): vscode.Disposable {
    // Check if user has their own mcp.json WITH mdpaper already defined
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders) {
        const mcpJsonPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'mcp.json');
        if (fs.existsSync(mcpJsonPath)) {
            try {
                const content = fs.readFileSync(mcpJsonPath, 'utf-8');
                if (shouldSkipMcpRegistration(content)) {
                    outputChannel.appendLine('[MCP] Found mdpaper in .vscode/mcp.json - skipping auto-registration');
                    return { dispose: () => {} };
                }
                outputChannel.appendLine('[MCP] Found .vscode/mcp.json but no mdpaper defined - proceeding with auto-registration');
            } catch {
                outputChannel.appendLine('[MCP] Could not read .vscode/mcp.json - proceeding with auto-registration');
            }
        }
    }

    // Skills are loaded from the extension's bundled directory
    // and used by the chat participant for /autopaper command

    const provider: vscode.McpServerDefinitionProvider = {
        onDidChangeMcpServerDefinitions: new vscode.EventEmitter<void>().event,

        provideMcpServerDefinitions(token: vscode.CancellationToken): vscode.ProviderResult<vscode.McpServerDefinition[]> {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            const wsRoot = workspaceFolders?.[0]?.uri.fsPath;

            // Detect development workspace (has src/med_paper_assistant/ source code)
            const isDevWorkspace = wsRoot ? checkIsDevWorkspace(wsRoot) : false;

            // Use stored uv path, or fallback
            const uvPath = resolvedUvPath || (context.globalState.get<string>('uvPath')) || 'uv';
            const uvxPath = getUvxPath(uvPath);

            outputChannel.appendLine(`[MCP] Mode: ${isDevWorkspace ? 'development' : 'marketplace'}, uv: ${uvPath}, uvx: ${uvxPath}`);

            const definitions: vscode.McpServerDefinition[] = [];

            // --- 1. MedPaper Assistant ---
            let mdpaperCommand: string;
            let mdpaperArgs: string[];
            let mcpEnv: Record<string, string>;

            const bundledToolPath = path.join(context.extensionPath, 'bundled', 'tool');

            if (isDevWorkspace && wsRoot) {
                // Development: use workspace source via uv run
                const pythonPath = getPythonPath(context);
                mdpaperCommand = pythonPath;
                mdpaperArgs = getPythonArgs(pythonPath, 'med_paper_assistant.interfaces.mcp');

                // Dev PYTHONPATH: workspace src + integrations + bundled
                const pythonPathEnv = buildDevPythonPath(wsRoot, bundledToolPath);

                mcpEnv = buildMcpEnv({ workspaceDir: wsRoot, pythonPath: pythonPathEnv });
            } else {
                // Marketplace: prefer pre-installed tool, fallback to uvx
                const [cmd, args, preInstalled] = buildMcpCommand(uvPath, 'med-paper-assistant');
                mdpaperCommand = cmd;
                mdpaperArgs = args;
                mcpEnv = buildMcpEnv({ workspaceDir: wsRoot });
                if (preInstalled) {
                    outputChannel.appendLine(`[MCP] MedPaper: using pre-installed binary (skipping uvx)`);
                }
            }

            outputChannel.appendLine(`[MCP] MedPaper: ${mdpaperCommand} ${mdpaperArgs.join(' ')}`);
            definitions.push(new vscode.McpStdioServerDefinition(
                'MedPaper Assistant',
                mdpaperCommand,
                mdpaperArgs,
                mcpEnv
            ));

            // --- 2. CGU ---
            const hasCguBundled = fs.existsSync(path.join(bundledToolPath, 'cgu'));
            const cguInWorkspace = wsRoot
                ? fs.existsSync(path.join(wsRoot, 'integrations', 'cgu', 'src', 'cgu'))
                : false;

            if (hasCguBundled || cguInWorkspace) {
                let cguCommand: string;
                let cguArgs: string[];

                if (isDevWorkspace || cguInWorkspace) {
                    const pythonPath = getPythonPath(context);
                    cguCommand = pythonPath;
                    cguArgs = getPythonArgs(pythonPath, 'cgu.server');
                } else {
                    // Marketplace: prefer pre-installed, fallback to uvx
                    const [cmd, args, preInstalled] = buildMcpCommand(uvPath, 'creativity-generation-unit', 'cgu-server');
                    cguCommand = cmd;
                    cguArgs = args;
                    if (preInstalled) {
                        outputChannel.appendLine(`[MCP] CGU: using pre-installed binary (skipping uvx)`);
                    }
                }

                outputChannel.appendLine(`[MCP] CGU: ${cguCommand} ${cguArgs.join(' ')}`);
                definitions.push(new vscode.McpStdioServerDefinition(
                    'CGU Creativity',
                    cguCommand,
                    cguArgs,
                    mcpEnv
                ));
            } else {
                outputChannel.appendLine('[MCP] CGU not found — skipping registration');
            }

            // --- 3. PubMed Search ---
            const pubmedInWorkspace = wsRoot
                ? fs.existsSync(path.join(wsRoot, 'integrations', 'pubmed-search-mcp', 'src', 'pubmed_search'))
                : false;

            let pubmedCommand: string;
            let pubmedArgs: string[];

            if (pubmedInWorkspace) {
                pubmedCommand = uvPath;
                pubmedArgs = [
                    'run',
                    '--directory', path.join(wsRoot!, 'integrations', 'pubmed-search-mcp'),
                    'pubmed-search-mcp'
                ];
                outputChannel.appendLine('[MCP] PubMed Search: using workspace integration');
            } else {
                const [cmd, args, preInstalled] = buildMcpCommand(uvPath, 'pubmed-search-mcp');
                pubmedCommand = cmd;
                pubmedArgs = args;
                if (preInstalled) {
                    outputChannel.appendLine('[MCP] PubMed Search: using pre-installed binary (skipping uvx)');
                }
            }

            outputChannel.appendLine(`[MCP] PubMed Search: ${pubmedCommand} ${pubmedArgs.join(' ')}`);
            definitions.push(new vscode.McpStdioServerDefinition(
                'PubMed Search',
                pubmedCommand,
                pubmedArgs,
                {
                    ...mcpEnv,
                    ENTREZ_EMAIL: process.env.ENTREZ_EMAIL || 'medpaper@example.com'
                }
            ));

            // --- 4. Zotero Keeper ---
            const [zoteroCommand, zoteroArgs, zoteroPreInstalled] = buildMcpCommand(uvPath, 'zotero-keeper');
            if (zoteroPreInstalled) {
                outputChannel.appendLine('[MCP] Zotero Keeper: using pre-installed binary (skipping uvx)');
            }
            outputChannel.appendLine(`[MCP] Zotero Keeper: ${zoteroCommand} ${zoteroArgs.join(' ')}`);
            definitions.push(new vscode.McpStdioServerDefinition(
                'Zotero Keeper',
                zoteroCommand,
                zoteroArgs,
                mcpEnv
            ));

            // --- 5. Draw.io ---
            const [drawioCmd, drawioArgs, drawioPreInstalled] = buildMcpCommand(
                uvPath, 'drawio-mcp', 'drawio-mcp-server'
            );
            if (drawioPreInstalled) {
                outputChannel.appendLine(`[MCP] Draw.io: using pre-installed binary (skipping uvx)`);
                definitions.push(new vscode.McpStdioServerDefinition(
                    'Draw.io Diagrams',
                    drawioCmd,
                    [],
                    { ...mcpEnv, DRAWIO_NEXTJS_URL: 'http://localhost:3000' }
                ));
            } else {
                definitions.push(new vscode.McpStdioServerDefinition(
                    'Draw.io Diagrams',
                    uvxPath,
                    ['--from', 'drawio-mcp', 'drawio-mcp-server'],
                    { ...mcpEnv, DRAWIO_NEXTJS_URL: 'http://localhost:3000' }
                ));
            }

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
    const config = vscode.workspace.getConfiguration('mdpaper');
    const configuredPath = config.get<string>('pythonPath');
    const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

    return determinePythonPath({
        configuredPath: configuredPath || undefined,
        wsRoot,
        extensionPath: context.extensionPath,
    });
}



async function autoScaffoldIfNeeded(context: vscode.ExtensionContext): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        return;
    }

    const wsRoot = workspaceFolders[0].uri.fsPath;
    const extPath = context.extensionPath;

    const { missingSkills, missingAgents, missingPrompts, total: totalMissing } =
        countMissingBundledItems(wsRoot, extPath, BUNDLED_SKILLS, BUNDLED_AGENTS, BUNDLED_PROMPTS);

    if (totalMissing === 0) {
        outputChannel.appendLine('[AutoScaffold] Workspace already has all skills/agents/prompts.');
        return;
    }

    // Use workspace-specific state key to avoid re-prompting
    const stateKey = `mdpaper.scaffolded.${wsRoot}`;
    const alreadyPrompted = context.globalState.get<boolean>(stateKey);

    if (alreadyPrompted) {
        outputChannel.appendLine(`[AutoScaffold] Already prompted for this workspace (${totalMissing} items missing). Run "MedPaper: Setup Workspace" to update.`);
        return;
    }

    const detail = [];
    if (missingSkills > 0) { detail.push(`${missingSkills} skills`); }
    if (missingAgents > 0) { detail.push(`${missingAgents} agents`); }
    if (missingPrompts > 0) { detail.push(`${missingPrompts} prompts`); }

    const selection = await vscode.window.showInformationMessage(
        `MedPaper: 偵測到 workspace 缺少 ${detail.join('、')}。要設定嗎？`,
        '設定 Workspace',
        '稍後再說',
        '不再提醒'
    );

    if (selection === '設定 Workspace') {
        await setupWorkspace(context);
    } else if (selection === '不再提醒') {
        await context.globalState.update(stateKey, true);
    }
    // '稍後再說' → do nothing, will prompt again next activation
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

    // 6. Copy agents → .github/agents/
    for (const agent of BUNDLED_AGENTS) {
        const src = path.join(extPath, 'agents', `${agent}.agent.md`);
        const dst = path.join(wsRoot, '.github', 'agents', `${agent}.agent.md`);
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(src, dst);
            copied++;
        }
    }

    if (copied > 0) {
        vscode.window.showInformationMessage(
            `MedPaper: 已設定 ${copied} 個檔案（skills、prompts、agents、instructions、templates）到 workspace。重新載入視窗以啟用全部功能。`,
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
