import { NextRequest, NextResponse } from 'next/server';
import { readFile, writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

const PROJECTS_DIR = join(process.cwd(), '..', 'projects');

// GET /api/diagrams/[id]?project=slug - Get diagram content
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const projectSlug = request.nextUrl.searchParams.get('project');

  if (!projectSlug) {
    return NextResponse.json({ error: 'Project slug required' }, { status: 400 });
  }

  try {
    const fileName = Buffer.from(id, 'base64url').toString();
    const filePath = join(PROJECTS_DIR, projectSlug, 'results', 'figures', fileName);

    if (!existsSync(filePath)) {
      return NextResponse.json({ error: 'Diagram not found' }, { status: 404 });
    }

    const content = await readFile(filePath, 'utf-8');

    return NextResponse.json({
      id,
      fileName,
      content,
      projectSlug,
    });
  } catch (error) {
    console.error('Error reading diagram:', error);
    return NextResponse.json({ error: 'Failed to read diagram' }, { status: 500 });
  }
}

// PUT /api/diagrams/[id]?project=slug - Save diagram content
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const projectSlug = request.nextUrl.searchParams.get('project');

  if (!projectSlug) {
    return NextResponse.json({ error: 'Project slug required' }, { status: 400 });
  }

  try {
    const { content, fileName: newFileName } = await request.json();

    // Decode existing filename or use new filename
    let fileName: string;
    if (id === 'new') {
      fileName = newFileName || `diagram-${Date.now()}.drawio`;
      if (!fileName.endsWith('.drawio')) {
        fileName += '.drawio';
      }
    } else {
      fileName = Buffer.from(id, 'base64url').toString();
    }

    const figuresDir = join(PROJECTS_DIR, projectSlug, 'results', 'figures');
    const filePath = join(figuresDir, fileName);

    // Ensure directory exists
    if (!existsSync(figuresDir)) {
      await mkdir(figuresDir, { recursive: true });
    }

    await writeFile(filePath, content, 'utf-8');

    const newId = Buffer.from(fileName).toString('base64url');

    return NextResponse.json({
      success: true,
      id: newId,
      fileName,
      path: filePath,
      projectSlug,
    });
  } catch (error) {
    console.error('Error saving diagram:', error);
    return NextResponse.json({ error: 'Failed to save diagram' }, { status: 500 });
  }
}

// DELETE /api/diagrams/[id]?project=slug - Delete diagram
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const projectSlug = request.nextUrl.searchParams.get('project');

  if (!projectSlug) {
    return NextResponse.json({ error: 'Project slug required' }, { status: 400 });
  }

  try {
    const fileName = Buffer.from(id, 'base64url').toString();
    const filePath = join(PROJECTS_DIR, projectSlug, 'results', 'figures', fileName);

    if (!existsSync(filePath)) {
      return NextResponse.json({ error: 'Diagram not found' }, { status: 404 });
    }

    const { unlink } = await import('fs/promises');
    await unlink(filePath);

    return NextResponse.json({ success: true, deleted: fileName });
  } catch (error) {
    console.error('Error deleting diagram:', error);
    return NextResponse.json({ error: 'Failed to delete diagram' }, { status: 500 });
  }
}
