import { NextRequest, NextResponse } from 'next/server';
import { readdir, stat, readFile } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

const PROJECTS_DIR = join(process.cwd(), '..', 'projects');

interface Diagram {
  id: string;
  name: string;
  fileName: string;
  path: string;
  createdAt: string;
  updatedAt: string;
}

// GET /api/diagrams?project=slug - List diagrams for a project
export async function GET(request: NextRequest) {
  const projectSlug = request.nextUrl.searchParams.get('project');
  
  if (!projectSlug) {
    return NextResponse.json({ error: 'Project slug required' }, { status: 400 });
  }

  const figuresDir = join(PROJECTS_DIR, projectSlug, 'results', 'figures');
  
  if (!existsSync(figuresDir)) {
    return NextResponse.json({ diagrams: [], projectSlug });
  }

  try {
    const files = await readdir(figuresDir);
    const drawioFiles = files.filter(f => f.endsWith('.drawio') || f.endsWith('.drawio.xml'));
    
    const diagrams: Diagram[] = await Promise.all(
      drawioFiles.map(async (fileName) => {
        const filePath = join(figuresDir, fileName);
        const stats = await stat(filePath);
        const name = fileName.replace(/\.drawio(\.xml)?$/, '');
        
        return {
          id: Buffer.from(fileName).toString('base64url'),
          name,
          fileName,
          path: filePath,
          createdAt: stats.birthtime.toISOString(),
          updatedAt: stats.mtime.toISOString(),
        };
      })
    );

    // Sort by updated time, newest first
    diagrams.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());

    return NextResponse.json({ diagrams, projectSlug });
  } catch (error) {
    console.error('Error listing diagrams:', error);
    return NextResponse.json({ error: 'Failed to list diagrams' }, { status: 500 });
  }
}
