import React from 'react';

interface OutputConsoleProps {
  output: string;
}

export const OutputConsole: React.FC<OutputConsoleProps> = ({ output }) => {
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700">
        <h3 className="text-md font-semibold">Output Console</h3>
      </div>
      
      <div className="p-2 bg-black max-h-40 overflow-y-auto font-mono text-sm">
        {output ? (
          <pre className="whitespace-pre-wrap text-green-400">{output}</pre>
        ) : (
          <p className="text-gray-500">No output yet...</p>
        )}
      </div>
    </div>
  );
};