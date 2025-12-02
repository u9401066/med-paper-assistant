'use client';

import { useRef, useCallback, useState, useEffect } from 'react';
import { DrawIoEmbed, DrawIoEmbedRef, EventExport } from 'react-drawio';

interface DrawioEditorProps {
  initialXml?: string;
  onSave?: (xml: string, png?: string) => void;
  onExport?: (data: { format: string; data: string }) => void;
  projectSlug?: string;
  diagramName?: string;
}

export function DrawioEditor({
  initialXml,
  onSave,
  onExport,
  projectSlug,
  diagramName = 'diagram',
}: DrawioEditorProps) {
  const drawioRef = useRef<DrawIoEmbedRef>(null);
  const [isReady, setIsReady] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Handle export event (triggered by save action in Draw.io)
  const handleExport = useCallback(
    (data: EventExport) => {
      if (data.format === 'xml' && data.xml) {
        // XML export - this is what we save
        setIsSaving(true);
        onSave?.(data.xml);
        setLastSaved(new Date());
        setIsSaving(false);
      } else if (data.format === 'png' && data.data) {
        // PNG export
        onExport?.({ format: 'png', data: data.data });
      } else if (data.format === 'svg' && data.data) {
        // SVG export
        onExport?.({ format: 'svg', data: data.data });
      }
    },
    [onSave, onExport]
  );

  // Export as XML (save)
  const handleSaveClick = useCallback(() => {
    if (drawioRef.current) {
      drawioRef.current.exportDiagram({
        format: 'xml',
      });
    }
  }, []);

  // Export as PNG
  const handleExportPng = useCallback(() => {
    if (drawioRef.current) {
      drawioRef.current.exportDiagram({
        format: 'png',
      });
    }
  }, []);

  // Export as SVG
  const handleExportSvg = useCallback(() => {
    if (drawioRef.current) {
      drawioRef.current.exportDiagram({
        format: 'svg',
      });
    }
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-2 bg-gray-100 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">
            {diagramName}
          </span>
          {projectSlug && (
            <span className="text-xs text-gray-500">
              in {projectSlug}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {/* Save Status */}
          {lastSaved && (
            <span className="text-xs text-gray-500">
              Saved {lastSaved.toLocaleTimeString()}
            </span>
          )}
          
          {/* Save Button */}
          <button
            onClick={handleSaveClick}
            disabled={!isReady || isSaving}
            className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg
                      hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                      transition-colors flex items-center gap-1"
          >
            {isSaving ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Saving...
              </>
            ) : (
              <>💾 Save</>
            )}
          </button>

          {/* Export Dropdown */}
          <div className="relative group">
            <button
              disabled={!isReady}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg
                        hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed
                        transition-colors"
            >
              📤 Export
            </button>
            <div className="absolute right-0 mt-1 w-32 bg-white border border-gray-200 rounded-lg shadow-lg
                          opacity-0 invisible group-hover:opacity-100 group-hover:visible
                          transition-all z-10">
              <button
                onClick={handleExportPng}
                className="w-full px-3 py-2 text-sm text-left hover:bg-gray-50"
              >
                PNG Image
              </button>
              <button
                onClick={handleExportSvg}
                className="w-full px-3 py-2 text-sm text-left hover:bg-gray-50"
              >
                SVG Vector
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Draw.io Editor */}
      <div className="flex-1 relative">
        {!isReady && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50 z-10">
            <div className="text-center">
              <svg className="w-8 h-8 mx-auto mb-2 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <p className="text-sm text-gray-500">Loading Draw.io...</p>
            </div>
          </div>
        )}
        
        <DrawIoEmbed
          ref={drawioRef}
          xml={initialXml}
          onExport={handleExport}
          onLoad={() => setIsReady(true)}
          urlParameters={{
            // UI configuration
            ui: 'kennedy', // Clean UI theme
            spin: true,
            libraries: true,
            saveAndExit: false, // We handle save ourselves
            noSaveBtn: true, // Hide default save button
            noExitBtn: true, // Hide exit button
            // Enable features
            modified: true,
            keepmodified: true,
          }}
          configuration={{
            // Custom libraries for medical diagrams
            defaultLibraries: 'general;basic;arrows2;flowchart',
          }}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
          }}
        />
      </div>
    </div>
  );
}
