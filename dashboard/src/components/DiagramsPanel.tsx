'use client';

import { useState, useCallback, useEffect } from 'react';
import { useProjects } from '@/hooks/useProjects';
import { useEnvironment } from '@/hooks/useEnvironment';
import { useDiagrams } from '@/hooks/useDiagrams';
import { DrawioEditor } from '@/components/DrawioEditor';
import { Diagram } from '@/types/diagram';

interface DiagramsPanelProps {
  projectSlug: string | null;
  isVSCodeBrowser: boolean;
}

// Diagram list item component
function DiagramListItem({
  diagram,
  isActive,
  onSelect,
  onDelete,
}: {
  diagram: Diagram;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const [showDelete, setShowDelete] = useState(false);

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer
                  transition-colors ${
                    isActive
                      ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700'
                      : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
      onClick={onSelect}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">📊</span>
        <div>
          <p className="font-medium text-gray-900 dark:text-gray-100 text-sm">{diagram.name}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {new Date(diagram.updatedAt).toLocaleDateString()}
          </p>
        </div>
      </div>
      {showDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (confirm(`Delete "${diagram.name}"?`)) {
              onDelete();
            }
          }}
          className="p-1 text-red-400 hover:text-red-600 rounded"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      )}
    </div>
  );
}

export function DiagramsPanel({ projectSlug, isVSCodeBrowser }: DiagramsPanelProps) {
  const {
    diagrams,
    currentDiagram,
    isLoading,
    error,
    loadDiagram,
    saveDiagram,
    deleteDiagram,
    createNewDiagram,
    closeDiagram,
    fetchDiagrams,
  } = useDiagrams(projectSlug);

  const [newDiagramName, setNewDiagramName] = useState('');
  const [showNewDialog, setShowNewDialog] = useState(false);

  // Handle save from editor
  const handleSave = useCallback(
    async (xml: string) => {
      if (!currentDiagram) return;
      
      const fileName = currentDiagram.id === 'new' 
        ? (newDiagramName || `diagram-${Date.now()}`) 
        : undefined;
      
      await saveDiagram(xml, currentDiagram.id, fileName);
    },
    [currentDiagram, newDiagramName, saveDiagram]
  );

  // Handle export
  const handleExport = useCallback(
    (data: { format: string; data: string }) => {
      // Download the exported file
      const link = document.createElement('a');
      link.download = `${currentDiagram?.fileName?.replace('.drawio', '') || 'diagram'}.${data.format}`;
      link.href = data.data;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
    [currentDiagram]
  );

  // Create new diagram
  const handleCreateNew = () => {
    if (newDiagramName.trim()) {
      createNewDiagram();
      setShowNewDialog(false);
      setNewDiagramName('');
    }
  };

  if (!projectSlug) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 dark:text-gray-400">Select a project first</p>
      </div>
    );
  }

  // If editing a diagram, show fullscreen editor
  if (currentDiagram) {
    return (
      <div className="fixed inset-0 z-50 bg-white dark:bg-gray-900 flex flex-col">
        {/* Editor Header */}
        <div className="flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-800 border-b dark:border-gray-700">
          <div className="flex items-center gap-2">
            <button
              onClick={closeDiagram}
              className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {currentDiagram.id === 'new' ? 'New Diagram' : currentDiagram.fileName}
            </span>
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1">
          <DrawioEditor
            initialXml={currentDiagram.content || undefined}
            onSave={handleSave}
            onExport={handleExport}
            projectSlug={projectSlug}
            diagramName={currentDiagram.fileName}
          />
        </div>
      </div>
    );
  }

  // Show diagram list
  return (
    <div className="space-y-4">
      {/* Header with New button */}
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-gray-900 dark:text-gray-100">Diagrams</h3>
        <button
          onClick={() => setShowNewDialog(true)}
          className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg
                    hover:bg-blue-700 transition-colors flex items-center gap-1"
        >
          <span>+</span> New Diagram
        </button>
      </div>

      {/* New Diagram Dialog */}
      {showNewDialog && (
        <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Diagram Name
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={newDiagramName}
              onChange={(e) => setNewDiagramName(e.target.value)}
              placeholder="e.g., consort-flowchart"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm
                        bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                        focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              onKeyDown={(e) => e.key === 'Enter' && handleCreateNew()}
              autoFocus
            />
            <button
              onClick={handleCreateNew}
              disabled={!newDiagramName.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg
                        hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create
            </button>
            <button
              onClick={() => {
                setShowNewDialog(false);
                setNewDiagramName('');
              }}
              className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 rounded-lg
                        hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Diagram List */}
      {isLoading && diagrams.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">Loading diagrams...</div>
      ) : diagrams.length === 0 ? (
        <div className="text-center py-8 bg-gray-50 dark:bg-gray-800 rounded-lg border border-dashed border-gray-300 dark:border-gray-600">
          <span className="text-3xl mb-2 block">🎨</span>
          <p className="text-gray-500 dark:text-gray-400 mb-1">No diagrams yet</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Create a new diagram or use Copilot to generate one
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {diagrams.map((diagram) => (
            <DiagramListItem
              key={diagram.id}
              diagram={diagram}
              isActive={false}
              onSelect={() => loadDiagram(diagram.id)}
              onDelete={() => deleteDiagram(diagram.id)}
            />
          ))}
        </div>
      )}

      {/* VS Code hint */}
      {isVSCodeBrowser && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-100 dark:border-blue-800 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            💡 <strong>Tip:</strong> Ask Copilot to create a diagram for you!
          </p>
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
            Try: &quot;Create a CONSORT flowchart for my study&quot;
          </p>
        </div>
      )}
    </div>
  );
}
