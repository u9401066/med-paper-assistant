'use client';

import { useState } from 'react';
import { useProjects } from '@/hooks/useProjects';
import { useEnvironment } from '@/hooks/useEnvironment';
import { ProjectSelector } from '@/components/ProjectSelector';
import { FocusSelector } from '@/components/FocusSelector';
import { ProjectCard } from '@/components/ProjectCard';
import { EnvironmentBadge } from '@/components/EnvironmentBadge';
import { ProjectFocus } from '@/types/project';

type TabType = 'projects' | 'focus' | 'diagrams';

export default function Home() {
  const { projects, currentProject, isLoading, error, selectProject, updateFocus, refresh } = useProjects();
  const { isVSCodeBrowser } = useEnvironment();
  const [activeTab, setActiveTab] = useState<TabType>('projects');

  const handleFocusChange = (focus: ProjectFocus) => {
    updateFocus(focus);
  };

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'projects', label: 'Projects', icon: '📁' },
    { id: 'focus', label: 'Focus', icon: '🎯' },
    { id: 'diagrams', label: 'Diagrams', icon: '🎨' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl">📝</span>
              <h1 className="font-semibold text-gray-900">MedPaper</h1>
            </div>
            <div className="flex items-center gap-2">
              <EnvironmentBadge />
              <button
                onClick={refresh}
                disabled={isLoading}
                className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100
                          disabled:opacity-50"
                title="Refresh"
              >
                <svg className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>
          
          {/* Current Project Selector */}
          <div className="mt-3">
            <ProjectSelector
              projects={projects}
              currentProject={currentProject}
              onSelect={selectProject}
              isLoading={isLoading}
            />
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-t border-gray-100">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-2 text-sm font-medium transition-colors
                         ${activeTab === tab.id
                           ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                           : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                         }`}
            >
              <span className="mr-1">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* Main Content */}
      <main className="p-4 pb-20">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Projects Tab */}
        {activeTab === 'projects' && (
          <div className="space-y-3">
            {isLoading && projects.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                Loading projects...
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-2">No projects yet</p>
                <p className="text-sm text-gray-400">
                  Create a project using Copilot Chat
                </p>
              </div>
            ) : (
              projects.map((project) => (
                <ProjectCard
                  key={project.slug}
                  project={project}
                  isActive={currentProject?.slug === project.slug}
                  onClick={() => selectProject(project.slug)}
                />
              ))
            )}
          </div>
        )}

        {/* Focus Tab */}
        {activeTab === 'focus' && (
          <div>
            {currentProject ? (
              <>
                <div className="mb-4 p-3 bg-white rounded-lg border border-gray-200">
                  <h2 className="font-medium text-gray-900">{currentProject.name}</h2>
                  {currentProject.description && (
                    <p className="text-sm text-gray-500 mt-1">{currentProject.description}</p>
                  )}
                </div>
                <FocusSelector
                  currentFocus={currentProject.focus}
                  onFocusChange={handleFocusChange}
                />
                
                {/* Copilot Hint */}
                <div className="mt-6 p-3 bg-blue-50 border border-blue-100 rounded-lg">
                  <p className="text-sm text-blue-700">
                    💡 <strong>Tip:</strong> Copilot will now use this focus to provide relevant help.
                  </p>
                  {currentProject.focus?.type === 'drafting' && currentProject.focus.section && (
                    <p className="text-sm text-blue-600 mt-1">
                      Try asking: &quot;Help me write the {currentProject.focus.section} section&quot;
                    </p>
                  )}
                </div>
              </>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">Select a project first</p>
              </div>
            )}
          </div>
        )}

        {/* Diagrams Tab */}
        {activeTab === 'diagrams' && (
          <div>
            {currentProject ? (
              <div className="space-y-4">
                <div className="p-4 bg-white rounded-lg border border-gray-200">
                  <h3 className="font-medium text-gray-900 mb-2">Diagrams</h3>
                  <p className="text-sm text-gray-500">
                    Project diagrams will appear here.
                  </p>
                </div>
                
                {isVSCodeBrowser ? (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-700">
                      🎨 Draw.io editor opens in a separate browser tab when in VS Code.
                    </p>
                    <button
                      onClick={() => window.open('http://localhost:3001', '_blank')}
                      className="mt-2 px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg text-sm font-medium
                                hover:bg-yellow-200 transition-colors"
                    >
                      Open Draw.io Editor
                    </button>
                  </div>
                ) : (
                  <div className="p-4 bg-gray-100 border border-gray-200 rounded-lg text-center">
                    <p className="text-sm text-gray-500 mb-2">Draw.io Editor</p>
                    <p className="text-xs text-gray-400">Embedded editor coming soon...</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">Select a project first</p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-3">
        <div className="text-center text-xs text-gray-400">
          {currentProject ? (
            <span>
              Working on: <strong className="text-gray-600">{currentProject.name}</strong>
              {currentProject.focus && (
                <> • {currentProject.focus.type}
                  {currentProject.focus.section && ` → ${currentProject.focus.section}`}
                </>
              )}
            </span>
          ) : (
            <span>No project selected</span>
          )}
        </div>
      </footer>
    </div>
  );
}
