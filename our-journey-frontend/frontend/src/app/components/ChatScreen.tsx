import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, Send, Mic, LogOut } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { signOut } from 'aws-amplify/auth';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';
import { useApp } from '../context/AppContext';
import { Message } from '../types';
import { RESOURCE_CATEGORIES, MOCK_RESOURCES } from '../data/resources';
import { ResourceCard } from './ResourceCard';
import webSocketManager from './websocketManager';

export const ChatScreen = () => {
  const navigate = useNavigate();
  const { userInfo, messages, addMessage, updateMessage, language, setLanguage } = useApp();
  const [inputValue, setInputValue] = useState('');
  const [showCategories, setShowCategories] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isInputDisabled, setIsInputDisabled] = useState(false);
  const [currentInfoMessage, setCurrentInfoMessage] = useState(null);
  const [currentAssistantMessageId, setCurrentAssistantMessageId] = useState(null);
  const [countyResource, setCountyResource] = useState(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Helper function to convert literal \n strings to actual newlines
  const unescapeNewlines = (text: string) => {
    // Single replace to convert all escaped newlines to real ones
    // This preserves \n\n as paragraph breaks and \n as line breaks
    return text.replace(/\\n/g, '\n');
  };

  useEffect(() => {
    if (messages.length === 0) {
      // Initial welcome message
      const welcomeMsg: Message = {
        id: '1',
        text: language === 'en'
          ? `Hi${userInfo?.county ? ' there' : ''}! What can I help you with today?`
          : `¡Hola${userInfo?.county ? '' : ''}! ¿En qué puedo ayudarte hoy?`,
        sender: 'bot',
        timestamp: new Date(),
        quickReplies: language === 'en'
          ? ['Housing', 'Jobs', 'Legal Help', 'Healthcare', 'Crisis Help']
          : ['Vivienda', 'Empleo', 'Ayuda Legal', 'Salud', 'Ayuda de Crisis']
      };
      addMessage(welcomeMsg);
    }
  }, []);

  // When language changes and only the welcome message exists, update it
  useEffect(() => {
    if (messages.length === 1 && messages[0].id === '1') {
      updateMessage('1', {
        text: language === 'en'
          ? `Hi${userInfo?.county ? ' there' : ''}! What can I help you with today?`
          : `¡Hola${userInfo?.county ? '' : ''}! ¿En qué puedo ayudarte hoy?`,
        quickReplies: language === 'en'
          ? ['Housing', 'Jobs', 'Legal Help', 'Healthcare', 'Crisis Help']
          : ['Vivienda', 'Empleo', 'Ayuda Legal', 'Salud', 'Ayuda de Crisis']
      });
    }
  }, [language]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Transform messages from app format to Claude API format
  const transformMessagesToClaudeFormat = (msgs) => {
    return msgs
      .filter(msg => msg.id !== '1') // Exclude the initial welcome message (id: '1')
      .filter(msg => msg.sender !== 'bot' || msg.text) // Filter out empty bot messages
      .map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: [
          {
            text: msg.text
          }
        ]
      }));
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };
    addMessage(userMessage);
    
    const currentInput = inputValue; // Store before clearing
    setInputValue('');
    setShowCategories(false);

    try {
      setIsStreaming(true);
      setIsInputDisabled(true);
      setCurrentInfoMessage(null);
      
      // Add placeholder for assistant message that will be updated as it streams
      const assistantMessageId = (Date.now() + 1).toString();
      const assistantMessage: Message = {
        id: assistantMessageId,
        text: '',
        sender: 'bot',
        timestamp: new Date()
      };
      addMessage(assistantMessage);
      setCurrentAssistantMessageId(assistantMessageId);

      // Get all messages in Claude format for context
      const allMessages = [...messages, userMessage];
      const claudeFormatMessages = transformMessagesToClaudeFormat(allMessages);

      // Define callback for when bot message chunks are received
      const onBotMessageReceived = (botMessage, isNewMessage = false) => {
        // Clear info message when actual response starts coming in
        if (botMessage && botMessage.trim().length > 0) {
          setCurrentInfoMessage(null);
          setIsStreaming(false);
        }
        
        if (isNewMessage) {
          // Create a completely new assistant message
          const newAssistantMessageId = Date.now().toString();
          const newAssistantMessage: Message = {
            id: newAssistantMessageId,
            text: botMessage,
            sender: 'bot',
            timestamp: new Date()
          };
          addMessage(newAssistantMessage);
          setCurrentAssistantMessageId(newAssistantMessageId);
        } else {
          // Update existing assistant message using updateMessage
          updateMessage(assistantMessageId, { text: botMessage });
        }
      };

      // Define callback for info messages
      const onInfoReceived = (infoMessage) => {
        setCurrentInfoMessage(infoMessage);
      };

      // Define callback for when message is complete
      const onMessageComplete = () => {
        console.log('Message fully received, re-enabling input');
        setIsInputDisabled(false);
        setCurrentAssistantMessageId(null);
      };

      // Define callback for county PDF resource - set once, ignore if already received
      const onCountyResourceReceived = (resource) => {
        setCountyResource(prev => prev ?? resource);
      };

      // WebSocket call with all callbacks
      await webSocketManager.sendMessageAndWaitForResponse(
        currentInput,
        claudeFormatMessages,
        onBotMessageReceived,
        onInfoReceived,
        onMessageComplete,
        { ...userInfo, language },
        onCountyResourceReceived
      );
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove the placeholder message on error if it's still empty
      if (currentAssistantMessageId) {
        const message = messages.find(m => m.id === currentAssistantMessageId);
        if (message && !message.text) {
          // If we had a way to remove messages, we'd do it here
          // For now, just mark it as an error
          updateMessage(currentAssistantMessageId, { 
            text: language === 'en' 
              ? 'Sorry, there was an error processing your request.' 
              : 'Lo siento, hubo un error al procesar tu solicitud.'
          });
        }
      }
      // Re-enable input on error
      setIsStreaming(false);
      setIsInputDisabled(false);
      setCurrentInfoMessage(null);
      setCurrentAssistantMessageId(null);
    }
  };

  const handleQuickReply = (reply: string) => {
    // Set the input value and send
    setInputValue(reply);
    // Use setTimeout to ensure state update completes
    setTimeout(() => {
      handleSend();
    }, 0);
  };

  const handleCategoryClick = (category: string) => {
    setInputValue(category);
    // Use setTimeout to ensure state update completes
    setTimeout(() => {
      handleSend();
    }, 0);
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#F5F5F5]">
      {/* Header */}
      <div className="bg-white shadow-sm p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10">
            <img src="/Robin.png" alt="JoJo" className="w-full h-full object-contain" />
          </div>
          <div>
            <h2 className="font-semibold text-[#212121]">JoJo</h2>
            <p className="text-xs text-gray-500">
              {language === 'en' ? 'Online • Your reentry guide' : 'En línea • Tu guía de reingreso'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Language Toggle */}
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as 'en' | 'es')}
            className="text-sm px-2 py-1 rounded border border-gray-300 bg-white"
          >
            <option value="en">EN</option>
            <option value="es">ES</option>
          </select>

          {/* Menu */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <Menu className="w-5 h-5" />
              </Button>
            </SheetTrigger>
            <SheetContent>
              <div className="py-6">
                <h3 className="font-semibold mb-4">Menu</h3>
                <div className="space-y-2">
                  <button
                    onClick={() => {
                      webSocketManager.clearConversation();
                      navigate('/');
                      window.location.reload();
                    }}
                    className="w-full text-left p-3 hover:bg-gray-100 rounded-lg text-green-600 font-medium"
                  >
                    {language === 'en' ? '+ New Conversation' : '+ Nueva Conversación'}
                  </button>
                  <button
                    onClick={() => navigate('/categories')}
                    className="w-full text-left p-3 hover:bg-gray-100 rounded-lg"
                  >
                    {language === 'en' ? 'Browse Categories' : 'Explorar Categorías'}
                  </button>
                  <button
                    onClick={() => navigate('/settings')}
                    className="w-full text-left p-3 hover:bg-gray-100 rounded-lg"
                  >
                    {language === 'en' ? 'Settings' : 'Configuración'}
                  </button>
                  <button
                    onClick={() => {
                      navigate('/');
                      window.location.reload();
                    }}
                    className="w-full text-left p-3 hover:bg-gray-100 rounded-lg"
                  >
                    {language === 'en' ? 'Start Over' : 'Empezar de Nuevo'}
                  </button>
                  <button
                    onClick={() => navigate('/admin')}
                    className="w-full text-left p-3 hover:bg-gray-100 rounded-lg text-blue-600"
                  >
                    Admin Dashboard
                  </button>
                  <button
                    onClick={handleSignOut}
                    className="w-full text-left p-3 hover:bg-gray-100 rounded-lg text-red-600 flex items-center gap-2"
                  >
                    <LogOut className="w-4 h-4" />
                    {language === 'en' ? 'Sign Out' : 'Cerrar Sesión'}
                  </button>
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div key={message.id}>
            {message.sender === 'bot' ? (
              <div className="flex gap-3">
                <div className="w-8 h-8 flex-shrink-0">
                  <img src="/Robin.png" alt="JoJo" className="w-full h-full object-contain" />
                </div>
                <div className="flex-1">
                  <div className="bg-[#E8F5E9] rounded-2xl rounded-tl-none p-4 max-w-[80%]">
                    <div className="prose prose-sm max-w-none text-gray-800 prose-headings:text-gray-900 prose-p:text-gray-800 prose-a:text-[#1B5E20] prose-strong:text-gray-900 prose-code:text-gray-800 prose-pre:bg-gray-100 prose-li:text-gray-800">
                      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                        {unescapeNewlines(message.text)}
                      </ReactMarkdown>
                    </div>
                  </div>
                  
                  {message.resources && message.resources.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {message.resources.map((resource) => (
                        <ResourceCard key={resource.id} resource={resource} />
                      ))}
                    </div>
                  )}

                  {message.quickReplies && message.quickReplies.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {message.quickReplies.map((reply, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleQuickReply(reply)}
                          className="px-4 py-2 border-2 border-[#388E3C] text-[#388E3C] rounded-full hover:bg-[#388E3C] hover:text-white transition-colors"
                        >
                          {reply}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex justify-end">
                <div className="bg-white rounded-2xl rounded-tr-none p-4 max-w-[80%] shadow-sm border border-gray-200">
                  <div className="prose prose-sm max-w-none text-gray-800 prose-headings:text-gray-900 prose-p:text-gray-800 prose-a:text-[#1B5E20] prose-strong:text-gray-900 prose-code:text-gray-800 prose-pre:bg-gray-100 prose-li:text-gray-800">
                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                      {unescapeNewlines(message.text)}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Info Message Display */}
        {currentInfoMessage && (
          <div className="flex gap-3">
            <div className="w-8 h-8 flex-shrink-0">
              <img src="/Robin.png" alt="JoJo" className="w-full h-full object-contain" />
            </div>
            <div className="flex-1">
              <div className="bg-[#E8F5E9] rounded-2xl rounded-tl-none p-4 max-w-[80%]">
                <p className="text-gray-600 italic">{currentInfoMessage}</p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Categories (show when no conversation yet) */}
      {showCategories && messages.length <= 1 && (
        <div className="px-4 pb-4">
          <p className="text-sm text-gray-600 mb-3">
            {language === 'en' ? 'Popular topics:' : 'Temas populares:'}
          </p>
          <div className="grid grid-cols-2 gap-2">
            {RESOURCE_CATEGORIES.slice(0, 6).map((cat) => (
              <button
                key={cat.id}
                onClick={() => handleCategoryClick(language === 'es' && cat.nameEs ? cat.nameEs : cat.name)}
                className="p-3 bg-white rounded-xl border border-gray-200 hover:border-[#388E3C] hover:bg-[#E8F5E9] transition-all text-left"
              >
                <span className="text-sm font-medium text-gray-800">{language === 'es' && cat.nameEs ? cat.nameEs : cat.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* County Resource Banner - shown once received, persists for the session */}
      {countyResource && (
        <div className="px-4 py-2 bg-[#E8F5E9] border-t border-[#A5D6A7]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-lg flex-shrink-0">📄</span>
              <p className="text-sm text-[#1B5E20] font-medium truncate">
                {language === 'en'
                  ? `${countyResource.county} County Reentry Resource Guide`
                  : `Guía de Recursos de Reingreso del Condado ${countyResource.county}`}
              </p>
            </div>
            <a
              href={countyResource.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 text-xs font-semibold px-3 py-1.5 bg-[#1B5E20] text-white rounded-full hover:bg-[#388E3C] transition-colors"
            >
              {language === 'en' ? 'Download' : 'Descargar'}
            </a>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 p-4">
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !isInputDisabled && handleSend()}
            placeholder={language === 'en' ? 'Type your message...' : 'Escribe tu mensaje...'}
            className="flex-1 bg-[#F5F5F5] border-0 focus:ring-2 focus:ring-[#388E3C]"
            disabled={isInputDisabled}
          />
          <Button
            variant="ghost"
            size="icon"
            className="text-gray-500"
            disabled={isInputDisabled}
          >
            <Mic className="w-5 h-5" />
          </Button>
          <Button
            onClick={handleSend}
            size="icon"
            className="bg-[#1B5E20] hover:bg-[#388E3C] text-white"
            disabled={isInputDisabled}
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};