import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

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
        })
    );

    outputChannel.appendLine('MedPaper Assistant activated successfully!');
}

function registerMcpServerProvider(context: vscode.ExtensionContext): vscode.Disposable {
    // Determine Python path
    const pythonPath = getPythonPath(context);
    const bundledToolPath = path.join(context.extensionPath, 'bundled', 'tool');
    
    // Load skills for server instructions
    const skillsPath = path.join(context.extensionPath, 'skills');
    const instructions = loadSkillsAsInstructions(skillsPath);

    const provider: vscode.McpServerDefinitionProvider = {
        onDidChangeMcpServerDefinitions: new vscode.EventEmitter<void>().event,
        
        provideMcpServerDefinitions(token: vscode.CancellationToken): vscode.ProviderResult<vscode.McpServerDefinition[]> {
            const definition = new vscode.McpStdioServerDefinition(
                'MedPaper Assistant',  // label
                pythonPath,            // command
                ['-m', 'mdpaper_mcp'], // args
                {                      // env
                    PYTHONPATH: bundledToolPath,
                    MDPAPER_INSTRUCTIONS: instructions,
                    MDPAPER_EXTENSION_PATH: context.extensionPath
                }
            );
            return [definition];
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
    // Note: This API might need adjustment based on actual VS Code version
    return vscode.lm.registerMcpServerDefinitionProvider('mdpaper', provider);
}

function registerChatParticipant(context: vscode.ExtensionContext): vscode.Disposable | null {
    try {
        const handler: vscode.ChatRequestHandler = async (
            request: vscode.ChatRequest,
            chatContext: vscode.ChatContext,
            stream: vscode.ChatResponseStream,
            token: vscode.CancellationToken
        ) => {
            // Handle different commands
            switch (request.command) {
                case 'search':
                    stream.markdown('🔍 使用 MCP 工具搜尋 PubMed...\n\n');
                    stream.markdown('請在 Agent Mode 中使用此功能，MCP 工具會自動被調用。');
                    break;
                
                case 'draft':
                    stream.markdown('✍️ 準備撰寫論文章節...\n\n');
                    stream.markdown('請提供章節類型和主題，我會協助您撰寫。');
                    break;
                
                case 'concept':
                    stream.markdown('💡 發展研究概念...\n\n');
                    stream.markdown('請描述您的研究想法，我會幫您驗證 novelty。');
                    break;
                
                case 'project':
                    stream.markdown('📁 專案管理...\n\n');
                    stream.markdown('使用 `/mdpaper.project` 來建立或管理研究專案。');
                    break;
                
                case 'format':
                    stream.markdown('📄 匯出 Word 文件...\n\n');
                    stream.markdown('請確保已完成所有章節的撰寫。');
                    break;
                
                default:
                    // General query - provide guidance
                    stream.markdown(`## MedPaper Assistant\n\n`);
                    stream.markdown(`您好！我是 MedPaper Assistant，專門協助醫學論文撰寫。\n\n`);
                    stream.markdown(`### 可用指令\n`);
                    stream.markdown(`- \`/search\` - 搜尋 PubMed 文獻\n`);
                    stream.markdown(`- \`/draft\` - 撰寫論文章節\n`);
                    stream.markdown(`- \`/concept\` - 發展研究概念\n`);
                    stream.markdown(`- \`/project\` - 管理研究專案\n`);
                    stream.markdown(`- \`/format\` - 匯出 Word 文件\n\n`);
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
                    { prompt: '搜尋相關文獻', label: '🔍 Search Literature' },
                    { prompt: '開始撰寫草稿', label: '✍️ Start Drafting' },
                    { prompt: '驗證研究概念', label: '💡 Validate Concept' }
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
    if (configuredPath && fs.existsSync(configuredPath)) {
        return configuredPath;
    }

    // 2. Check bundled Python (for standalone distribution)
    const bundledPython = path.join(context.extensionPath, 'bundled', 'python', 'bin', 'python3');
    if (fs.existsSync(bundledPython)) {
        return bundledPython;
    }

    // 3. Try uvx (recommended)
    return 'uvx';
}

function loadSkillsAsInstructions(skillsPath: string): string {
    const instructions: string[] = [];
    
    if (!fs.existsSync(skillsPath)) {
        return '';
    }

    const skillDirs = fs.readdirSync(skillsPath, { withFileTypes: true })
        .filter(dirent => dirent.isDirectory())
        .map(dirent => dirent.name);

    for (const skillDir of skillDirs) {
        const skillFile = path.join(skillsPath, skillDir, 'SKILL.md');
        if (fs.existsSync(skillFile)) {
            const content = fs.readFileSync(skillFile, 'utf-8');
            instructions.push(`## Skill: ${skillDir}\n\n${content}`);
        }
    }

    return instructions.join('\n\n---\n\n');
}

export function deactivate() {
    outputChannel?.appendLine('MedPaper Assistant deactivated.');
}
