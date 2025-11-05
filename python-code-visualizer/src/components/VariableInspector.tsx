import React from 'react';

interface Variable {
  name: string;
  value: any;
  type: string;
  scope: 'global' | 'local' | 'builtin';
  hasChanged: boolean;
}

interface VariableInspectorProps {
  variables: Variable[];
}

export const VariableInspector: React.FC<VariableInspectorProps> = ({ variables }) => {
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700">
        <h3 className="text-md font-semibold">Variables</h3>
      </div>
      
      <div className="p-2 max-h-40 overflow-y-auto">
        {variables.length === 0 ? (
          <p className="text-gray-500 text-sm p-2">No variables to display</p>
        ) : (
          <ul className="space-y-1">
            {variables.map((variable, index) => (
              <li 
                key={index} 
                className={`flex justify-between items-center p-2 rounded ${variable.hasChanged ? 'bg-yellow-900 bg-opacity-50' : 'bg-gray-800'}`}
              >
                <span className="font-mono text-blue-400">{variable.name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400 text-sm">{variable.type}</span>
                  <span className="font-mono text-green-400">
                    {typeof variable.value === 'object' 
                      ? JSON.stringify(variable.value) 
                      : String(variable.value)}
                  </span>
                  {variable.hasChanged && (
                    <span className="text-xs bg-yellow-500 text-yellow-900 px-1 rounded">NEW</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};