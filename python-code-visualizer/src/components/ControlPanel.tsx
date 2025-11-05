import React from 'react';
import { Play, Pause, RotateCcw, StepForward, StepBack, FastForward } from 'lucide-react';

interface ControlPanelProps {
  isExecuting: boolean;
  executionSpeed: number;
  onExecute: () => void;
  onPause: () => void;
  onReset: () => void;
  onStepForward: () => void;
  onStepBackward: () => void;
  onSpeedChange: (speed: number) => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  isExecuting,
  executionSpeed,
  onExecute,
  onPause,
  onReset,
  onStepForward,
  onStepBackward,
  onSpeedChange,
}) => {
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden mt-4">
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Execution Controls</h2>
      </div>
      
      <div className="p-4 flex flex-wrap items-center gap-4">
        <div className="flex gap-2">
          {!isExecuting ? (
            <button
              onClick={onExecute}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
            >
              <Play size={16} />
              Execute
            </button>
          ) : (
            <button
              onClick={onPause}
              className="flex items-center gap-2 bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded-lg transition-colors"
            >
              <Pause size={16} />
              Pause
            </button>
          )}
          
          <button
            onClick={onReset}
            className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <RotateCcw size={16} />
            Reset
          </button>
          
          <button
            onClick={onStepBackward}
            disabled={isExecuting}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <StepBack size={16} />
            Step Back
          </button>
          
          <button
            onClick={onStepForward}
            disabled={isExecuting}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <StepForward size={16} />
            Step Forward
          </button>
        </div>
        
        <div className="flex items-center gap-2">
          <FastForward size={16} />
          <label htmlFor="speed" className="text-sm">Speed:</label>
          <select
            id="speed"
            value={executionSpeed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            className="bg-gray-700 text-white px-2 py-1 rounded border border-gray-600"
          >
            <option value={0.5}>0.5x</option>
            <option value={1}>1x</option>
            <option value={2}>2x</option>
            <option value={4}>4x</option>
          </select>
        </div>
      </div>
    </div>
  );
};