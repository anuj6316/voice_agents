I'll help you create a detailed prompt for building a Python code visualization webapp. Here's a comprehensive prompt you can use:

---

# Python Code Flow Visualizer - Detailed Project Prompt

## Project Overview

Build a web application that visualizes Python code execution line-by-line, showing how the program flows through conditional statements, loops, function calls, and variable states in real-time.

## Core Features Required

### 1. Code Input & Execution

- Provide a code editor (Monaco Editor or CodeMirror) with Python syntax highlighting
- Allow users to paste or type Python code
- Support for basic Python syntax (variables, functions, loops, conditionals, classes)
- Input field for program inputs (stdin simulation)
- Execute button to start visualization

### 2. Line-by-Line Visualization

- Highlight the current line being executed with a distinct color (e.g., yellow background)
- Show line numbers clearly
- Display execution flow with animated transitions between lines
- Support for:
  
  - Sequential execution
  - Conditional branches (if/elif/else) - show which branch is taken
  - Loop iterations (for/while) - indicate loop counter/condition
  - Function calls - show jump to function definition and return
  - Try-except blocks - visualize exception handling flow

### 3. Variable State Tracking

- Real-time variable watch panel showing:
  
  - Variable name
  - Current value
  - Data type
  - Highlight when values change
- Support for different data types:
  
  - Primitives (int, float, str, bool)
  - Collections (list, dict, tuple, set)
  - Objects (show attributes)
- Stack frame visualization for function scopes

### 4. Call Stack Visualization

- Display the call stack as functions are invoked
- Show current function context
- Visualize function returns and stack unwinding
- Display function parameters and local variables per frame

### 5. Execution Controls

- Play/Pause execution
- Step forward (execute next line)
- Step backward (undo last execution)
- Speed control slider (slow, medium, fast)
- Reset/restart execution
- Skip to end

### 6. Flow Diagram (Optional Enhanced Feature)

- Generate a flowchart alongside code execution
- Show decision points (diamonds for if/else)
- Show loops (rectangular boxes)
- Highlight current position in flowchart
- Connect flowchart nodes to corresponding code lines

### 7. Output Console

- Display print statements in real-time
- Show console output as execution progresses
- Error messages with line numbers if execution fails

## Technical Implementation Suggestions

### Frontend

- React with hooks for state management
- Use Web Workers for Python execution isolation
- Implement Pyodide or Skulpt for in-browser Python execution
- Use libraries like:
  
  - Monaco Editor or CodeMirror for code editing
  - Recharts or D3.js for visualizations
  - Lucide React for icons

### Backend (if needed)

- Python Flask/FastAPI server
- Execute code in sandboxed environment
- Return execution trace as JSON
- Websocket for real-time updates

### Execution Trace Format

```json
{
  "steps": [
    {
      "line": 5,
      "variables": {"x": 10, "y": 20},
      "stack": ["main"],
      "output": "",
      "action": "assignment"
    },
    {
      "line": 6,
      "variables": {"x": 10, "y": 20, "sum": 30},
      "stack": ["main"],
      "output": "",
      "action": "expression"
    }
  ]
}
```

## UI Layout Suggestion

```plaintext
┌─────────────────────────────────────────────────┐
│  Python Code Flow Visualizer                    │
├──────────────────────┬──────────────────────────┤
│                      │                          │
│  Code Editor         │   Variable Watch         │
│  (with line numbers  │   ┌──────────────────┐   │
│   and highlighting)  │   │ x: 10 (int)      │   │
│                      │   │ y: 20 (int) ⚡    │   │
│  1. x = 10          │   │ sum: 30 (int)    │   │
│  2. y = 20    ←     │   └──────────────────┘   │
│  3. sum = x + y     │                          │
│  4. print(sum)      │   Call Stack:            │
│                      │   ┌──────────────────┐   │
│                      │   │ main()           │   │
│                      │   └──────────────────┘   │
├──────────────────────┴──────────────────────────┤
│  Controls: [◄] [►] [⏸] [⟲] Speed: [====●----]│
├─────────────────────────────────────────────────┤
│  Console Output:                                │
│  > 30                                           │
└─────────────────────────────────────────────────┘
```

## Example Use Cases to Support

### Example 1: Simple Loop

```python
for i in range(5):
    print(i)
```

Should show: loop iterations, variable `i` updating, each print output

### Example 2: Function Calls

```python
def add(a, b):
    return a + b

result = add(5, 3)
print(result)
```

Should show: function call jump, parameter passing, return value, stack changes

### Example 3: Conditional Logic

```python
x = 10
if x > 5:
    print("Large")
else:
    print("Small")
```

Should show: condition evaluation, which branch executes (highlight taken path)

### Example 4: Nested Structures

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

print(factorial(4))
```

Should show: recursive calls, stack depth, return sequence

## Bonus Features

- Save/load code snippets
- Share visualization via URL
- Export execution trace as GIF/video
- Breakpoint support
- Memory visualization for data structures
- Performance metrics (time/space complexity insights)
- Dark/light theme toggle
- Tutorial mode with example programs

## Design Considerations

- Use color coding effectively (execution=yellow, error=red, completed=green)
- Smooth animations for transitions
- Responsive design for mobile/tablet
- Clear typography for code readability
- Intuitive control buttons
- Accessible keyboard shortcuts

## Constraints & Limitations

- Limit code execution time (timeout after 30 seconds)
- Restrict certain dangerous operations (file I/O, network calls)
- Set maximum number of execution steps (e.g., 10,000)
- Display warning for infinite loops

---

Use this prompt to guide your Blitz project development. Start with core features (code input, basic execution, variable tracking) and progressively add advanced features (call stack, flowcharts, advanced controls).