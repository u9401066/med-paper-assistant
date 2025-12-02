'use client';

import { useEnvironment } from '@/hooks/useEnvironment';

export function EnvironmentBadge() {
  const { isVSCodeBrowser, isIframe, isLoaded } = useEnvironment();

  if (!isLoaded) return null;

  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      {isVSCodeBrowser && (
        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
          VS Code
        </span>
      )}
      {isIframe && !isVSCodeBrowser && (
        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
          Embedded
        </span>
      )}
    </div>
  );
}
