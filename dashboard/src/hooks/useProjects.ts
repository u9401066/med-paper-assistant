'use client';

import { useState, useEffect, useCallback } from 'react';
import { Project, ProjectFocus } from '@/types/project';

interface UseProjectsResult {
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  selectProject: (slug: string) => Promise<void>;
  updateFocus: (focus: ProjectFocus) => Promise<void>;
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

  const selectProject = useCallback(async (slug: string) => {
    try {
      const res = await fetch('/api/projects/current', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug }),
      });
      
      if (!res.ok) throw new Error('Failed to switch project');
      
      const data = await res.json();
      setCurrentProject(data.project);
      
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
