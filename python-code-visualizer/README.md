# Python Code Flow Visualizer

A web application that visualizes Python code execution line-by-line, showing how the program flows through conditional statements, loops, function calls, and variable states in real-time.

## Features

- **Code Editor**: Monaco Editor with Python syntax highlighting
- **Line-by-Line Visualization**: Highlight the current line being executed
- **Variable State Tracking**: Real-time variable watch panel
- **Call Stack Visualization**: Display the call stack as functions are invoked
- **Execution Controls**: Play/Pause, Step Forward/Backward, Speed Control
- **Output Console**: Display print statements and error messages

## Tech Stack

- **Frontend**: React 18 with TypeScript
- **Code Editor**: Monaco Editor
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```

2. Navigate to the project directory:
   ```bash
   cd python-code-visualizer
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

### Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`.

### Building for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── components/     # React components
├── contexts/       # React context providers
├── hooks/          # Custom React hooks
├── styles/         # CSS and Tailwind configuration
├── utils/          # Utility functions
├── App.tsx         # Main App component
├── main.tsx        # Entry point
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test` - Run tests
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Monaco Editor](https://microsoft.github.io/monaco-editor/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Lucide Icons](https://lucide.dev/)