import React from 'react';

const Loading = () => {
  return (
    <div className="flex items-center space-x-2">
      <div className="w-2 h-2 bg-primary-600 dark:bg-primary-400 rounded-full animate-bounce" />
      <div className="w-2 h-2 bg-primary-600 dark:bg-primary-400 rounded-full animate-bounce delay-100" />
      <div className="w-2 h-2 bg-primary-600 dark:bg-primary-400 rounded-full animate-bounce delay-200" />
    </div>
  );
};

export default Loading;
