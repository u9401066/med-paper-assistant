import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

const PROJECTS_DIR = path.join(process.cwd(), '..', 'projects');

interface RouteParams {
  params: Promise<{ slug: string }>;
}

export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const { slug } = await params;
    const focus = await request.json();
    
    const projectPath = path.join(PROJECTS_DIR, slug);
    const projectJsonPath = path.join(projectPath, 'project.json');
    
    // 讀取現有專案資訊
    let data;
    try {
      const content = await fs.readFile(projectJsonPath, 'utf-8');
      data = JSON.parse(content);
    } catch {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      );
    }

    // 更新 focus
    data.focus = {
      type: focus.type,
      section: focus.section,
      lastUpdated: new Date().toISOString(),
    };
    data.updated_at = new Date().toISOString();

    // 寫回檔案
    await fs.writeFile(projectJsonPath, JSON.stringify(data, null, 2));

    return NextResponse.json({
      success: true,
      project: {
        name: data.name,
        slug: data.slug || slug,
        description: data.description || '',
        paperType: data.paper_type || '',
        targetJournal: data.target_journal || '',
        status: data.status || 'concept',
        focus: data.focus,
        createdAt: data.created_at,
        updatedAt: data.updated_at,
        memo: data.memo,
      },
    });
  } catch (error) {
    console.error('Error updating focus:', error);
    return NextResponse.json(
      { error: 'Failed to update focus' },
      { status: 500 }
    );
  }
}
