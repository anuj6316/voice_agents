import { CodeEditor } from './components/CodeEditor';
import { VisualizationPanel } from './components/VisualizationPanel';
import { ControlPanel } from './components/ControlPanel';
import { useCodeExecution } from './hooks/useCodeExecution';
import { AppStateProvider } from './contexts/AppStateContext';

function App() {
  const {
    code,
    setCode,
    isExecuting,
    currentLine,
    variables,
    callStack,
    output,
    executionSpeed,
    setExecutionSpeed,
    executeCode,
    pauseExecution,
    resetExecution,
    stepForward,
    stepBackward,
  } = useCodeExecution();

  return (
    <AppStateProvider>
      <div className="min-h-screen bg-gray-900 text-gray-100 flex flex-col">
        <header className="bg-gray-800 border-b border-gray-700 p-4">
          <div className="container mx-auto">
            <h1 className="text-2xl font-bold text-blue-400">Python Code Flow Visualizer</h1>
            <p className="text-gray-400">Visualize Python code execution line-by-line</p>
          </div>
        </header>

        <main className="flex-grow container mx-auto p-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="flex flex-col">
            <CodeEditor 
              code={code}
              onChange={setCode}
              currentLine={currentLine}
              isExecuting={isExecuting}
            />
            <ControlPanel
              isExecuting={isExecuting}
              executionSpeed={executionSpeed}
              onExecute={executeCode}
              onPause={pauseExecution}
              onReset={resetExecution}
              onStepForward={stepForward}
              onStepBackward={stepBackward}
              onSpeedChange={setExecutionSpeed}
            />
          </div>
          
          <VisualizationPanel
            variables={variables}
            callStack={callStack}
            output={output}
          />
        </main>

        <footer className="bg-gray-800 border-t border-gray-700 p-4 text-center text-gray-500 text-sm">
          <p>Python Code Flow Visualizer &copy; {new Date().getFullYear()}</p>
        </footer>
      </div>
    </AppStateProvider>
  );
}

export default App;