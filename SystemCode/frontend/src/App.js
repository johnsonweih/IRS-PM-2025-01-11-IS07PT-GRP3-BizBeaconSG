import React from 'react';
import './index.css';
import Chat from './components/Chat';
import { ThemeProvider } from './context/ThemeContext';

function App() {
  return (
    <ThemeProvider>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
        <Chat />
      </div>
    </ThemeProvider>
  );
}

export default App;
