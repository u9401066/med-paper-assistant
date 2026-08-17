'use client';

import { useState, useCallback, useEffect } from 'react';
import { Diagram } from '@/types/diagram';

async function requestDiagrams(projectSlug: string, signal?: AbortSignal): Promise<Diagram[]> {
  const res = await fetch(`/api/diagrams?project=${projectSlug}`, { signal });
  if (!res.ok) throw new Error('Failed to fetch diagrams');
  const data = await res.json();
  return data.diagrams || [];
}

export function useDiagrams(projectSlug: string | null) {
  const [diagrams, setDiagrams] = useState<Diagram[]>([]);
  const [loadedProjectSlug, setLoadedProjectSlug] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentDiagram, setCurrentDiagram] = useState<{
    id: string;
    content: string;
    fileName: string;
  } | null>(null);

  // Fetch diagrams list
  const fetchDiagrams = useCallback(async () => {
    if (!projectSlug) {
      setDiagrams([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const items = await requestDiagrams(projectSlug);
      setDiagrams(items);
      setLoadedProjectSlug(projectSlug);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [projectSlug]);

  // Load diagram content
  const loadDiagram = useCallback(async (diagramId: string) => {
    if (!projectSlug) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/diagrams/${diagramId}?project=${projectSlug}`);
      if (!res.ok) throw new Error('Failed to load diagram');

      const data = await res.json();
      setCurrentDiagram({
        id: data.id,
        content: data.content,
        fileName: data.fileName,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [projectSlug]);

  // Save diagram
  const saveDiagram = useCallback(async (
    content: string,
    diagramId: string = 'new',
    fileName?: string
  ) => {
    if (!projectSlug) {
      setError('No project selected');
      return null;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/diagrams/${diagramId}?project=${projectSlug}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, fileName }),
      });

      if (!res.ok) throw new Error('Failed to save diagram');

      const data = await res.json();

      // Refresh list
      await fetchDiagrams();

      // Update current diagram
      setCurrentDiagram({
        id: data.id,
        content,
        fileName: data.fileName,
      });

      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [projectSlug, fetchDiagrams]);

  // Delete diagram
  const deleteDiagram = useCallback(async (diagramId: string) => {
    if (!projectSlug) return false;

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/diagrams/${diagramId}?project=${projectSlug}`, {
        method: 'DELETE',
      });

      if (!res.ok) throw new Error('Failed to delete diagram');

      // Clear current if it was deleted
      if (currentDiagram?.id === diagramId) {
        setCurrentDiagram(null);
      }

      // Refresh list
      await fetchDiagrams();

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [projectSlug, currentDiagram, fetchDiagrams]);

  // Create new diagram
  const createNewDiagram = useCallback(() => {
    setCurrentDiagram({
      id: 'new',
      content: '',
      fileName: `diagram-${Date.now()}.drawio`,
    });
  }, []);

  // Close current diagram
  const closeDiagram = useCallback(() => {
    setCurrentDiagram(null);
  }, []);

  // Fetch on mount or project change
  useEffect(() => {
    if (!projectSlug) return;

    const controller = new AbortController();
    const requestedSlug = projectSlug;
    void requestDiagrams(requestedSlug, controller.signal)
      .then((items) => {
        setDiagrams(items);
        setLoadedProjectSlug(requestedSlug);
        setError(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setLoadedProjectSlug(requestedSlug);
        setError(err instanceof Error ? err.message : 'Unknown error');
      });

    return () => controller.abort();
  }, [projectSlug]);

  const projectDiagrams = projectSlug === loadedProjectSlug ? diagrams : [];
  const isProjectLoading = projectSlug !== null && projectSlug !== loadedProjectSlug;

  return {
    diagrams: projectDiagrams,
    currentDiagram,
    isLoading: isLoading || isProjectLoading,
    error,
    fetchDiagrams,
    loadDiagram,
    saveDiagram,
    deleteDiagram,
    createNewDiagram,
    closeDiagram,
  };
}
