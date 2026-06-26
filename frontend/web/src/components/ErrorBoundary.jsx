import React from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';
import { toast } from 'sonner';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    // Update state to show fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to service (optional)
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    toast.error('Something went wrong. Please refresh the page.', {
      duration: 5000
    });
  }

  handleRefresh = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex items-center justify-center px-4 py-12">
          <div className="max-w-md w-full bg-gray-800 rounded-2xl shadow-2xl border border-gray-700 p-8 text-center">
            <div className="w-24 h-24 bg-red-900/20 rounded-2xl flex items-center justify-center mx-auto mb-6 border-2 border-red-900/50">
              <AlertCircle className="w-12 h-12 text-red-400" />
            </div>
            
            <h1 className="text-2xl font-bold text-white mb-4">Something went wrong</h1>
            <p className="text-gray-400 mb-8 max-w-sm mx-auto">
              We're sorry, an unexpected error occurred. Our team has been notified.
            </p>
            
            <div className="space-y-3 mb-8">
              <button
                onClick={this.handleRefresh}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
              >
                <RefreshCw className="w-5 h-5 animate-spin" />
                Refresh Page
              </button>
              
              <button
                onClick={this.handleHome}
                className="w-full bg-gray-700 hover:bg-gray-600 text-gray-100 font-medium py-3 px-4 rounded-xl transition-all duration-200 flex items-center justify-center gap-2"
              >
                <Home className="w-5 h-5" />
                Go to Dashboard
              </button>
            </div>
            
            <div className="text-xs text-gray-500 pt-4 border-t border-gray-700">
              Error: {this.state.error?.message || 'Unknown error'}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;

