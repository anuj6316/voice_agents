# Python Code Flow Visualizer - Project Structure

This document explains the organization of the Python Code Flow Visualizer project.

## Directory Structure

```
python-code-visualizer/
├── src/
│   ├── components/          # React components
│   ├── contexts/            # React context providers
│   ├── hooks/               # Custom React hooks
│   ├── styles/              # CSS and styling files
│   ├── utils/               # Utility functions
│   ├── App.tsx             # Main application component
│   └── main.tsx            # Application entry point
├── public/                 # Static assets
├── tests/                  # Test files
├── index.html              # Main HTML file
├── package.json            # Project dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite build configuration
└── README.md               # Project documentation
```

## Component Architecture

### Core Components

1. **App.tsx** - Main application component that orchestrates all other components
2. **CodeEditor** - Monaco Editor integration for Python code input
3. **VisualizationPanel** - Container for visualization components
4. **ControlPanel** - Execution controls (play, pause, step, reset)
5. **VariableInspector** - Displays current variable states
6. **CallStackViewer** - Shows function call stack
7. **OutputConsole** - Displays program output

### State Management

- **AppStateContext** - Centralized state management using React Context and useReducer
- **useCodeExecution** - Custom hook for code execution logic

## Technologies Used

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and development server
- **Tailwind CSS** - Styling framework
- **Monaco Editor** - Code editor component
- **Lucide React** - Icon library

## Development Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test` - Run tests
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Key Features Implemented

1. **Code Editing** - Syntax-highlighted Python code editor
2. **Execution Visualization** - Line-by-line code execution highlighting
3. **Variable Tracking** - Real-time variable state monitoring
4. **Call Stack Display** - Function call hierarchy visualization
5. **Execution Controls** - Play, pause, step forward/backward, speed control
6. **Output Console** - Program output display

## Future Enhancements

1. Integration with Pyodide for actual Python code execution
2. Advanced debugging features (breakpoints, watch expressions)
3. Flow diagram generation
4. Code sharing functionality
5. Performance metrics and analysis
6. Dark/light theme toggle
7. Tutorial mode with example programs