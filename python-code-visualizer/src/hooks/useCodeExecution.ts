import { useState, useCallback, useEffect } from 'react';
import { useAppState } from '../contexts/AppStateContext';

export const useCodeExecution = () => {
  const { state, dispatch } = useAppState();
  const [isExecuting, setIsExecuting] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentLine, setCurrentLine] = useState(0);
  const [variables, setVariables] = useState<any[]>([]);
  const [callStack, setCallStack] = useState<any[]>([]);
  const [output, setOutput] = useState('');
  const [executionSpeed, setExecutionSpeed] = useState(1);

  // Set code
  const setCode = useCallback((code: string) => {
    dispatch({ type: 'SET_CODE', payload: code });
  }, [dispatch]);

  // Execute code
  const executeCode = useCallback(async () => {
    dispatch({ type: 'START_EXECUTION' });
    setIsExecuting(true);
    setIsPaused(false);
    setCurrentLine(1);
    setVariables([]);
    setCallStack([]);
    setOutput('');

    try {
      const response = await fetch('/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: state.code }),
      });

      if (!response.ok) {
        throw new Error('Failed to execute code');
      }

      const result = await response.json();

      if (result.error) {
        setOutput(result.error);
        setIsExecuting(false);
        return;
      }

      const { trace, output } = result;
      let traceIndex = 0;

      const executeNextLine = () => {
        if (traceIndex < trace.length && isExecuting && !isPaused) {
          const { line, variables } = trace[traceIndex];
          setCurrentLine(line);
          dispatch({ type: 'UPDATE_CURRENT_LINE', payload: line });

          const formattedVariables = Object.entries(variables).map(([name, { value, type }]) => ({
            name,
            value,
            type,
            scope: 'global', // Placeholder
            hasChanged: true, // Placeholder
          }));

          setVariables(formattedVariables);
          dispatch({ type: 'UPDATE_VARIABLES', payload: formattedVariables });

          traceIndex++;
          setTimeout(executeNextLine, 1000 / executionSpeed);
        } else {
          setIsExecuting(false);
          setOutput(output);
          dispatch({ type: 'UPDATE_OUTPUT', payload: output });
        }
      };

      executeNextLine();
    } catch (error) {
      console.error(error);
      setOutput('An error occurred while executing the code.');
      setIsExecuting(false);
    }
  }, [state.code, isExecuting, isPaused, executionSpeed, dispatch]);

  // Pause execution
  const pauseExecution = useCallback(() => {
    dispatch({ type: 'PAUSE_EXECUTION' });
    setIsExecuting(false);
    setIsPaused(true);
  }, [dispatch]);

  // Reset execution
  const resetExecution = useCallback(() => {
    dispatch({ type: 'RESET_EXECUTION' });
    setIsExecuting(false);
    setIsPaused(false);
    setCurrentLine(0);
    setVariables([]);
    setCallStack([]);
    setOutput('');
  }, [dispatch]);

  // Step forward
  const stepForward = useCallback(() => {
    dispatch({ type: 'STEP_FORWARD' });
    // Implementation for stepping forward
  }, [dispatch]);

  // Step backward
  const stepBackward = useCallback(() => {
    dispatch({ type: 'STEP_BACKWARD' });
    // Implementation for stepping backward
  }, [dispatch]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      setIsExecuting(false);
      setIsPaused(false);
    };
  }, []);

  return {
    code: state.code,
    setCode,
    isExecuting,
    isPaused,
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
  };
};