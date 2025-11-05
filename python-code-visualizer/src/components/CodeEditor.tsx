import React from 'react';
import Editor from '@monaco-editor/react';

interface CodeEditorProps {
  code: string;
  onChange: (value: string) => void;
  currentLine?: number;
  isExecuting?: boolean;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({ 
  code, 
  onChange,
  currentLine = 0,
  isExecuting = false
}) => {
  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      onChange(value);
    }
  };

  const handleEditorDidMount = (editor: any) => {
    // Highlight current line if executing
    if (currentLine > 0 && isExecuting) {
      editor.revealLineInCenter(currentLine);
      // Line highlighting implementation would go here
    }
  };

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden flex-grow">
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Code Editor</h2>
      </div>
      <div className="h-96">
        <Editor
          height="100%"
          defaultLanguage="python"
          value={code}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            readOnly: isExecuting,
          }}
        />
      </div>
    </div>
  );
};