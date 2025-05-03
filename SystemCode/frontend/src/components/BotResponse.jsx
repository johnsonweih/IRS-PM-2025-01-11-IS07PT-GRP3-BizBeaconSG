import React, { useEffect, useState, useMemo } from "react";
import ReactMarkdown from 'react-markdown';
import LinkPreview from './LinkPreview';
import { HandThumbUpIcon as HandThumbUpOutline } from '@heroicons/react/24/outline';
import { HandThumbDownIcon as HandThumbDownOutline } from '@heroicons/react/24/outline';
import { HandThumbUpIcon as HandThumbUpSolid } from '@heroicons/react/24/solid';
import { HandThumbDownIcon as HandThumbDownSolid } from '@heroicons/react/24/solid';
import './BotResponse.css';

const BotResponse = ({ response, chatLogRef }) => {
  const [displayedText, setDisplayedText] = useState("");
  const [isPrinting, setIsPrinting] = useState(true);
  const [isButtonVisible, setIsButtonVisible] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Extract URLs only once when the response changes
  const links = useMemo(() => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const matches = response.match(urlRegex);
    return matches || [];
  }, [response]);

  useEffect(() => {
    let index = 0;
    let interval;

    if (isPrinting) {
      interval = setInterval(() => {
        if (index < response.length) {
          const newText = response.slice(0, index + 1);
          setDisplayedText(newText);
          index++;
        } else {
          clearInterval(interval);
          setIsButtonVisible(false);
        }
      }, 20);
    }

    return () => clearInterval(interval);
  }, [response, isPrinting]);

  const togglePrinting = () => {
    setIsPrinting(!isPrinting);
    if (!isPrinting) {
      setDisplayedText("");
    }
  };

  const handleFeedback = (type) => {
    setFeedback(type);
    // You can add analytics or logging here if needed
  };

  return (
    <div className="relative">
      <div className="whitespace-pre-wrap break-words markdown-content">
        <ReactMarkdown>{displayedText}</ReactMarkdown>
        {isPrinting && displayedText.length < response.length && (
          <span className="inline-block w-0.5 h-4 ml-0.5 bg-current animate-blink" />
        )}
      </div>
      
      <div className="flex items-center gap-3 mt-3">
        <button
          onClick={() => handleFeedback('thumbsUp')}
          className={`p-2 rounded-full transition-colors duration-200 ${
            feedback === 'thumbsUp'
              ? 'bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
          }`}
          title="Helpful"
        >
          {feedback === 'thumbsUp' ? (
            <HandThumbUpSolid className="w-6 h-6" />
          ) : (
            <HandThumbUpOutline className="w-6 h-6" />
          )}
        </button>
        <button
          onClick={() => handleFeedback('thumbsDown')}
          className={`p-2 rounded-full transition-colors duration-200 ${
            feedback === 'thumbsDown'
              ? 'bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
          }`}
          title="Not helpful"
        >
          {feedback === 'thumbsDown' ? (
            <HandThumbDownSolid className="w-6 h-6" />
          ) : (
            <HandThumbDownOutline className="w-6 h-6" />
          )}
        </button>
      </div>

      <div className="link-preview">
        {links.map((url) => (
          <LinkPreview key={url} url={url} />
        ))}
      </div>
      {isButtonVisible && (
        <button 
          className="absolute right-0 top-0 p-1 opacity-70 hover:opacity-100 transition-opacity focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-opacity-50 rounded"
          onClick={togglePrinting}
          title={isPrinting ? "Stop typing" : "Continue typing"}
        >
          {isPrinting ? "⏸️" : "▶️"}
        </button>
      )}
    </div>
  );
};

export default BotResponse;
