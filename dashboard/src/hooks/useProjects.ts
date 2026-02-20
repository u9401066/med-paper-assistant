'use client';

import { useState, useEffect, useCallback } from 'react';
import { Project, ProjectFocus } from '@/types/project';

interface UseProjectsResult {
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  selectProject: (slug: string, options?: { openFiles?: boolean; closeOthers?: boolean }) => Promise<void>;
  updateFocus: (focus: ProjectFocus) => Promise<void>;
}

// 用 vscode:// URI 開啟文件
function openFileInVSCode(filePath: string) {
  // vscode://file/path/to/file
  const uri = `vscode://file${filePath}`;
  window.open(uri, '_blank');
}

export function useProjects(): UseProjectsResult {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const res = await fetch('/api/projects');
      if (!res.ok) throw new Error('Failed to fetch projects');

      const data = await res.json();
      setProjects(data.projects);
      setCurrentProject(data.current);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const selectProject = useCallback(async (
    slug: string,
    options: { openFiles?: boolean; closeOthers?: boolean } = { openFiles: true, closeOthers: false }
  ) => {
    try {
      // 1. 如果要關閉其他專案的文件
      if (options.closeOthers) {
        // 使用 VS Code command URI 關閉所有編輯器
        // vscode://command:workbench.action.closeAllEditors
        window.open('vscode://command:workbench.action.closeAllEditors', '_blank');

        // 等待一下讓 VS Code 處理
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      // 2. 切換專案
      const res = await fetch('/api/projects/current', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, openFiles: options.openFiles }),
      });

      if (!res.ok) throw new Error('Failed to switch project');

      const data = await res.json();
      setCurrentProject(data.project);

      // 3. 開啟專案文件
      if (options.openFiles && data.filesToOpen?.length > 0) {
        // 稍微延遲開啟，避免太快
        for (const filePath of data.filesToOpen) {
          openFileInVSCode(filePath);
          await new Promise(resolve => setTimeout(resolve, 200));
        }
      }

      // Refresh to update list
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [refresh]);

  const updateFocus = useCallback(async (focus: ProjectFocus) => {
    if (!currentProject) return;

    try {
      const res = await fetch(`/api/projects/${currentProject.slug}/focus`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(focus),
      });

      if (!res.ok) throw new Error('Failed to update focus');

      const data = await res.json();
      setCurrentProject(data.project);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [currentProject]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    projects,
    currentProject,
    isLoading,
    error,
    refresh,
    selectProject,
    updateFocus,
  };
}
