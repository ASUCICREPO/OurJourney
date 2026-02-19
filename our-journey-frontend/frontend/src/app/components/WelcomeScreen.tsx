import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';

export const WelcomeScreen = () => {
  const navigate = useNavigate();
  const { language, setLanguage } = useApp();
  const { isAuthenticated, userGroup, login, isLoading } = useAuth();

  /**
   * Auto-redirect authenticated users based on their group
   * - Admins → /admin
   * - Users → /onboarding
   */
  useEffect(() => {
    // Clean up OAuth callback parameters from URL
    const url = new URL(window.location.href);
    if (url.searchParams.has('code') || url.searchParams.has('error')) {
      // Remove OAuth parameters without triggering navigation
      window.history.replaceState({}, document.title, url.pathname);
    }
    
    // Only redirect once we're done loading
    if (!isLoading && isAuthenticated && userGroup) {
      console.log(`User authenticated as ${userGroup}, redirecting...`);
      
      if (userGroup === 'Admins') {
        navigate('/admin', { replace: true });
      } else if (userGroup === 'Users') {
        navigate('/onboarding', { replace: true });
      }
    }
  }, [isLoading, isAuthenticated, userGroup, navigate]);

  /**
   * Handle sign-in button click
   * Redirects to Cognito Hosted UI for authentication
   */
  const handleStartChat = async () => {
    // If already authenticated, manually trigger redirect
    if (isAuthenticated && userGroup) {
      console.log('User already authenticated, navigating...');
      if (userGroup === 'Admins') {
        navigate('/admin', { replace: true });
      } else if (userGroup === 'Users') {
        navigate('/onboarding', { replace: true });
      }
      return;
    }
    
    // Don't allow clicking if loading
    if (isLoading) {
      console.log('Authentication check in progress...');
      return;
    }
    
    try {
      console.log('Initiating Cognito login...');
      await login();
    } catch (error) {
      console.error('Login error:', error);
      
      // Handle the "already authenticated" error gracefully
      if (error.name === 'UserAlreadyAuthenticatedException') {
        console.log('User already authenticated, refreshing page...');
        window.location.reload();
      } else {
        alert('Failed to initiate login. Please try again.');
      }
    }
  };

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F5F5F5] flex flex-col items-center justify-center p-6">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="mb-6">
            <div className="w-24 h-24 mx-auto animate-pulse">
              <img src="/Robin.png" alt="JoJo" className="w-full h-full object-contain" />
            </div>
          </div>
          <p className="text-gray-700">
            {language === 'en' ? 'Loading...' : 'Cargando...'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F5F5F5] flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
        {/* Language Toggle */}
        <div className="flex justify-center gap-2 mb-8">
          <button
            onClick={() => setLanguage('en')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              language === 'en'
                ? 'bg-[#1B5E20] text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            English
          </button>
          <button
            onClick={() => setLanguage('es')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              language === 'es'
                ? 'bg-[#1B5E20] text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Español
          </button>
        </div>

        {/* JoJo Avatar */}
        <div className="mb-6">
          <div className="w-24 h-24 mx-auto">
            <img src="/Robin.png" alt="JoJo" className="w-full h-full object-contain" />
          </div>
        </div>

        {/* Welcome Message */}
        <h1 className="text-2xl font-semibold text-[#212121] mb-4">
          {language === 'en' ? "Hi, I'm JoJo!" : "¡Hola, soy JoJo!"}
        </h1>
        
        <p className="text-gray-700 mb-6 leading-relaxed">
          {language === 'en'
            ? "I'm your guide to reentry resources in North Carolina. I'm here to help you find housing, jobs, healthcare, and more. Let's get started!"
            : "Soy tu guía de recursos de reingreso en Carolina del Norte. Estoy aquí para ayudarte a encontrar vivienda, empleo, atención médica y más. ¡Empecemos!"}
        </p>

        {/* Sign In Button - Updated to trigger Cognito authentication */}
        <Button
          onClick={handleStartChat}
          disabled={isLoading}
          className="w-full bg-[#1B5E20] hover:bg-[#388E3C] text-white py-6 rounded-xl mb-6 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {language === 'en' ? 'Sign In to Start' : 'Iniciar Sesión'}
        </Button>

        {/* Privacy Note */}
        <p className="text-sm text-gray-500">
          {language === 'en'
            ? 'Your information is confidential and used only to help you.'
            : 'Tu información es confidencial y se usa solo para ayudarte.'}
        </p>
      </div>
    </div>
  );
};