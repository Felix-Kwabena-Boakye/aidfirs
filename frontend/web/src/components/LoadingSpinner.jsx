import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingSpinner = ({ message = "Loading...", size = "lg" }) => {
  const sizeClasses = {
    sm: 'w-5 h-5',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  return (
    <div className="flex flex-col items-center justify-center space-y-4 p-8">
      <div className="relative">
        <Loader2 className={`animate-spin ${sizeClasses[size]} text-blue-400`} />
        <div className="absolute inset-0 w-full h-full border-2 border-blue-400/20 rounded-full animate-ping"></div>
      </div>
      <p className="text-gray-400 font-medium">{message}</p>
    </div>
  );
};

export default LoadingSpinner;

