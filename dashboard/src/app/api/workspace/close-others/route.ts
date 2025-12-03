import { NextRequest, NextResponse } from 'next/server';

/**
 * POST /api/workspace/close-others
 * 
 * Request to close files from other projects.
 * Since we can't directly control VS Code tabs from the browser,
 * this endpoint returns instructions for the user.
 */
export async function POST(request: NextRequest) {
  try {
    const { keepProjectSlug } = await request.json();
    
    if (!keepProjectSlug) {
      return NextResponse.json(
        { error: 'keepProjectSlug is required' },
        { status: 400 }
      );
    }

    // 由於無法從瀏覽器直接控制 VS Code tabs，
    // 我們返回指引讓用戶手動操作，或使用 MCP 工具
    
    // 嘗試透過 MCP HTTP API 調用 (如果有的話)
    // 目前 MCP 是透過 stdio，所以無法直接從 Next.js 調用
    
    // 返回建議操作
    return NextResponse.json({
      success: true,
      message: 'Close request received',
      instructions: {
        method1: {
          name: 'Keyboard Shortcut',
          steps: ['Press Ctrl+K, W to close all editors', 'Dashboard will open new project files'],
        },
        method2: {
          name: 'Context Menu',
          steps: ['Right-click on a tab', 'Select "Close Others"'],
        },
        method3: {
          name: 'Command Palette',
          steps: ['Press Ctrl+Shift+P', 'Type "Close All Editors"', 'Press Enter'],
        },
      },
      keepProjectSlug,
    });
  } catch (error) {
    console.error('Error processing close request:', error);
    return NextResponse.json(
      { error: 'Failed to process request' },
      { status: 500 }
    );
  }
}
