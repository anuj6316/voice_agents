import React from 'react';
import { VariableInspector } from './VariableInspector';
import { CallStackViewer } from './CallStackViewer';
import { OutputConsole } from './OutputConsole';

interface VisualizationPanelProps {
  variables: any[];
  callStack: any[];
  output: string;
}

export const VisualizationPanel: React.FC<VisualizationPanelProps> = ({ 
  variables, 
  callStack, 
  output 
}) => {
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden flex flex-col">
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Visualization</h2>
      </div>
      
      <div className="flex-grow flex flex-col gap-4 p-4">
        <div className="flex-grow">
          <VariableInspector variables={variables} />
        </div>
        
        <div className="flex-grow">
          <CallStackViewer stackFrames={callStack} />
        </div>
        
        <div className="flex-grow">
          <OutputConsole output={output} />
        </div>
      </div>
    </div>
  );
};