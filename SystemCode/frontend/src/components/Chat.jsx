import React, { useState, useRef, useEffect } from 'react';
import BotResponse from './BotResponse';
import Loading from './Loading';
import Error from './Error';
import { useTheme } from '../context/ThemeContext';

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const chatLogRef = useRef(null);
  const inputRef = useRef(null);
  const { isDarkMode, toggleTheme } = useTheme();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    try {
      setIsLoading(true);
      setError(null);
      
      const userMessage = { role: 'user', content: input };
      setMessages(prev => [...prev, userMessage]);
      setInput('');

      // Format chat history for backend
      const chatHistory = messages.map(msg => [msg.content, msg.role === 'assistant' ? msg.content : '']);

      const response = await fetch('http://localhost:4000/respond', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: input,
          chat_history: chatHistory 
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response from server');
      }

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.botResponse }]);
    } catch (err) {
      setError(err.message);
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(e);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4 bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      <div className="flex items-center justify-between mb-4 p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <div className="flex-1 text-center">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-white">Business Location Advisor</h1>
          <p className="text-gray-600 dark:text-gray-300 mt-1">Ask me anything about business locations and opportunities</p>
        </div>
        <button
          onClick={toggleTheme}
          className="ml-4 p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-200 flex-shrink-0"
          title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDarkMode ? "🌞" : "🌙"}
        </button>
      </div>

      <div 
        ref={chatLogRef}
        className="flex-1 overflow-y-auto p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm mb-4"
      >
        {messages.map((message, index) => (
          <div 
            key={index} 
            className={`flex flex-col mb-4 ${message.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div 
              className={`max-w-[80%] p-4 rounded-lg ${
                message.role === 'user' 
                  ? 'bg-primary-600 text-white rounded-br-none' 
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-bl-none'
              }`}
            >
              {message.role === 'assistant' ? (
                <BotResponse response={message.content} chatLogRef={chatLogRef} />
              ) : (
                message.content
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="max-w-[80%] p-4 bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg rounded-bl-none">
              <Loading />
            </div>
          </div>
        )}
        {error && (
          <div className="flex justify-center mb-4">
            <Error message={error} />
          </div>
        )}
      </div>

      <form 
        onSubmit={sendMessage} 
        className="flex gap-2 p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm"
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message here..."
          disabled={isLoading}
          rows={1}
          className="flex-1 p-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none min-h-[40px] max-h-[150px] bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
        />
        <button 
          type="submit" 
          disabled={!input.trim() || isLoading}
          className={`btn btn-primary ${isLoading ? 'opacity-50 cursor-wait' : ''}`}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default Chat; 