import React, { createContext, useContext, useReducer, ReactNode } from 'react';

// Define types for our application state
export interface Variable {
  name: string;
  value: any;
  type: string;
  scope: 'global' | 'local' | 'builtin';
  hasChanged: boolean;
}

export interface StackFrame {
  id: string;
  functionName: string;
  fileName: string;
  lineNumber: number;
  localVariables: Variable[];
}

export interface ExecutionState {
  isExecuting: boolean;
  isPaused: boolean;
  currentLine: number;
  variables: Variable[];
  callStack: StackFrame[];
  output: string;
  executionHistory: any[];
  currentStep: number;
}

export interface AppState {
  code: string;
  execution: ExecutionState;
  executionSpeed: number;
}

// Define action types
export type AppAction =
  | { type: 'SET_CODE'; payload: string }
  | { type: 'SET_EXECUTION_SPEED'; payload: number }
  | { type: 'START_EXECUTION' }
  | { type: 'PAUSE_EXECUTION' }
  | { type: 'RESUME_EXECUTION' }
  | { type: 'RESET_EXECUTION' }
  | { type: 'STEP_FORWARD' }
  | { type: 'STEP_BACKWARD' }
  | { type: 'UPDATE_CURRENT_LINE'; payload: number }
  | { type: 'UPDATE_VARIABLES'; payload: Variable[] }
  | { type: 'UPDATE_CALL_STACK'; payload: StackFrame[] }
  | { type: 'UPDATE_OUTPUT'; payload: string }
  | { type: 'ADD_TO_HISTORY'; payload: any }
  | { type: 'SET_CURRENT_STEP'; payload: number };

// Initial state
const initialState: AppState = {
  code: '# Enter your Python code here\nprint("Hello, World!")\nfor i in range(5):\n    print(f"Number: {i}")',
  execution: {
    isExecuting: false,
    isPaused: false,
    currentLine: 0,
    variables: [],
    callStack: [],
    output: '',
    executionHistory: [],
    currentStep: 0,
  },
  executionSpeed: 1,
};

// Reducer function
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_CODE':
      return { ...state, code: action.payload };
    
    case 'SET_EXECUTION_SPEED':
      return { ...state, executionSpeed: action.payload };
    
    case 'START_EXECUTION':
      return {
        ...state,
        execution: {
          ...state.execution,
          isExecuting: true,
          isPaused: false,
          currentLine: 1,
          variables: [],
          callStack: [],
          output: '',
          executionHistory: [],
          currentStep: 0,
        },
      };
    
    case 'PAUSE_EXECUTION':
      return {
        ...state,
        execution: {
          ...state.execution,
          isExecuting: false,
          isPaused: true,
        },
      };
    
    case 'RESUME_EXECUTION':
      return {
        ...state,
        execution: {
          ...state.execution,
          isExecuting: true,
          isPaused: false,
        },
      };
    
    case 'RESET_EXECUTION':
      return {
        ...state,
        execution: {
          ...state.execution,
          isExecuting: false,
          isPaused: false,
          currentLine: 0,
          variables: [],
          callStack: [],
          output: '',
          executionHistory: [],
          currentStep: 0,
        },
      };
    
    case 'STEP_FORWARD':
      return {
        ...state,
        execution: {
          ...state.execution,
          currentStep: state.execution.currentStep + 1,
        },
      };
    
    case 'STEP_BACKWARD':
      return {
        ...state,
        execution: {
          ...state.execution,
          currentStep: Math.max(0, state.execution.currentStep - 1),
        },
      };
    
    case 'UPDATE_CURRENT_LINE':
      return {
        ...state,
        execution: {
          ...state.execution,
          currentLine: action.payload,
        },
      };
    
    case 'UPDATE_VARIABLES':
      return {
        ...state,
        execution: {
          ...state.execution,
          variables: action.payload,
        },
      };
    
    case 'UPDATE_CALL_STACK':
      return {
        ...state,
        execution: {
          ...state.execution,
          callStack: action.payload,
        },
      };
    
    case 'UPDATE_OUTPUT':
      return {
        ...state,
        execution: {
          ...state.execution,
          output: action.payload,
        },
      };
    
    case 'ADD_TO_HISTORY':
      return {
        ...state,
        execution: {
          ...state.execution,
          executionHistory: [...state.execution.executionHistory, action.payload],
        },
      };
    
    case 'SET_CURRENT_STEP':
      return {
        ...state,
        execution: {
          ...state.execution,
          currentStep: action.payload,
        },
      };
    
    default:
      return state;
  }
}

// Create context
interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}

const AppStateContext = createContext<AppContextType | undefined>(undefined);

// Provider component
export const AppStateProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppStateContext.Provider value={{ state, dispatch }}>
      {children}
    </AppStateContext.Provider>
  );
};

// Custom hook to use the context
export const useAppState = () => {
  const context = useContext(AppStateContext);
  if (context === undefined) {
    throw new Error('useAppState must be used within an AppStateProvider');
  }
  return context;
};