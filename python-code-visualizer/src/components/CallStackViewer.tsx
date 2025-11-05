import React from 'react';

interface StackFrame {
  id: string;
  functionName: string;
  fileName: string;
  lineNumber: number;
  localVariables: any[];
}

interface CallStackViewerProps {
  stackFrames: StackFrame[];
}

export const CallStackViewer: React.FC<CallStackViewerProps> = ({ stackFrames }) => {
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700">
        <h3 className="text-md font-semibold">Call Stack</h3>
      </div>
      
      <div className="p-2 max-h-40 overflow-y-auto">
        {stackFrames.length === 0 ? (
          <p className="text-gray-500 text-sm p-2">Call stack is empty</p>
        ) : (
          <ul className="space-y-1">
            {stackFrames.map((frame) => (
              <li 
                key={frame.id} 
                className="flex items-center p-2 bg-gray-800 rounded"
              >
                <span className="font-mono text-blue-400">{frame.functionName}</span>
                <span className="text-gray-500 mx-2">in</span>
                <span className="text-gray-400">{frame.fileName}:{frame.lineNumber}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};