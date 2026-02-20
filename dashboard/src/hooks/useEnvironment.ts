'use client';

import { useState, useEffect } from 'react';

interface Environment {
  isVSCodeBrowser: boolean;
  isIframe: boolean;
  isLoaded: boolean;
}

/**
 * Detect if running in VS Code Simple Browser or iframe
 */
export function useEnvironment(): Environment {
  const [env, setEnv] = useState<Environment>({
    isVSCodeBrowser: false,
    isIframe: false,
    isLoaded: false,
  });

  useEffect(() => {
    const isIframe = window.self !== window.top;

    // VS Code Simple Browser detection
    const isVSCodeBrowser =
      navigator.userAgent.includes('VSCode') ||
      navigator.userAgent.includes('Electron') ||
      // Check if in iframe and parent might be VS Code
      (isIframe && document.referrer.includes('vscode'));

    setEnv({
      isVSCodeBrowser,
      isIframe,
      isLoaded: true,
    });
  }, []);

  return env;
}
