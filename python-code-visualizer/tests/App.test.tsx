import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../src/App';

describe('App', () => {
  it('should render the application title', () => {
    render(<App />);
    expect(screen.getByText('Python Code Flow Visualizer')).toBeInTheDocument();
  });
});