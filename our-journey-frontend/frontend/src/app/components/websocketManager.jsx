import { WEBSOCKET_API } from './constants.jsx';

class WebSocketManager {
  constructor() {
    this.ws = null;
    this.isConnected = false;
    this.isConnecting = false;
    this.messageCallback = null;
    this.infoCallback = null; // For temporary info messages
    this.completionCallback = null; // For when message is complete
    this.countyResourceCallback = null; // For county PDF resource data
    this.currentMessage = ''; // Track the current streaming message
    this.hasContent = false; // Track if current message has content for break token validation
    this.shouldCreateNewMessage = false; // Track if next delta should create new message
    this.conversationId = null; // Track the current conversation ID
  }

  // Generate a new conversation ID
  generateConversationId() {
    // Generate UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    return 'conv_' + 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  // Start a new conversation (generates new ID)
  startNewConversation() {
    this.conversationId = this.generateConversationId();
    console.log('Started new conversation:', this.conversationId);
    
    // Optionally persist to localStorage for session recovery
    try {
      localStorage.setItem('currentConversationId', this.conversationId);
    } catch (e) {
      console.warn('Could not save conversationId to localStorage:', e);
    }
    
    return this.conversationId;
  }

  // Get or create conversation ID
  getConversationId() {
    if (!this.conversationId) {
      // Try to recover from localStorage first
      try {
        const stored = localStorage.getItem('currentConversationId');
        if (stored) {
          this.conversationId = stored;
          console.log('Recovered conversation ID from localStorage:', this.conversationId);
          return this.conversationId;
        }
      } catch (e) {
        console.warn('Could not read conversationId from localStorage:', e);
      }
      
      // Generate new if none exists
      this.startNewConversation();
    }
    return this.conversationId;
  }

  // Clear current conversation ID (call when starting fresh)
  clearConversation() {
    this.conversationId = null;
    try {
      localStorage.removeItem('currentConversationId');
    } catch (e) {
      console.warn('Could not clear conversationId from localStorage:', e);
    }
    console.log('Conversation cleared');
  }

  // Set a specific conversation ID (for loading existing conversations)
  setConversationId(conversationId) {
    this.conversationId = conversationId;
    try {
      localStorage.setItem('currentConversationId', conversationId);
    } catch (e) {
      console.warn('Could not save conversationId to localStorage:', e);
    }
    console.log('Conversation ID set to:', conversationId);
  }

  // Connect to WebSocket
  connect() {
    return new Promise((resolve, reject) => {
      if (this.isConnected || this.isConnecting) {
        resolve();
        return;
      }

      this.isConnecting = true;

      try {
        this.ws = new WebSocket(WEBSOCKET_API);

        this.ws.onopen = () => {
          this.isConnected = true;
          this.isConnecting = false;
          console.log('WebSocket connection established');
          resolve();
        };

        this.ws.onclose = (event) => {
          this.isConnected = false;
          this.isConnecting = false;
          console.log('WebSocket connection closed:', event.code, event.reason);
        };

        this.ws.onerror = (error) => {
          this.isConnected = false;
          this.isConnecting = false;
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleStreamingMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  // Handle different types of streaming messages
  handleStreamingMessage(data) {
    if (data.type === 'messageStart') {
      // Reset current message for new message
      this.currentMessage = '';
      this.hasContent = false;
      this.shouldCreateNewMessage = false;
      console.log('Message start received');
    } 
    else if (data.type === 'contentBlockDelta') {
      // Simple delta processing - just accumulate text
      const deltaText = data.data.delta.text;
      
      // Only process if deltaText has actual content
      if (deltaText && deltaText.length > 0) {
        this.currentMessage += deltaText;
        this.hasContent = true;
        
        // Check if this should create a new message (after break token)
        const isNewMessage = this.shouldCreateNewMessage;
        
        // Reset the flag after using it
        if (this.shouldCreateNewMessage) {
          this.shouldCreateNewMessage = false;
        }
        
        // Update the UI with the current accumulated message
        if (this.messageCallback) {
          this.messageCallback(this.currentMessage, isNewMessage);
        }
      } else {
        console.log('Empty delta text received, skipping update');
      }
    }
    else if (data.type === 'breakTokenType') {
      // Only process if we have content from previous contentBlockDelta
      if (this.hasContent && this.currentMessage.length > 0) {
        console.log('Break token received - finalizing current message and preparing for new one');
        
        // Finalize current message
        if (this.messageCallback) {
          this.messageCallback(this.currentMessage, false);
        }
        
        // Reset for next message and flag that next delta should create new message
        this.currentMessage = '';
        this.hasContent = false;
        this.shouldCreateNewMessage = true;
        
        // Next contentBlockDelta will create a new message
      } else {
        console.log('Break token ignored - no preceding content');
      }
    }
    else if (data.type === 'messageStop') {
      // Message is complete, notify completion callback before closing
      console.log('Message stop received, final message:', this.currentMessage);
      
      // Notify that message is complete before closing
      if (this.completionCallback) {
        this.completionCallback();
      }
      
      this.close();
    }
    else if (data.type === 'info') {
      // Handle info messages (not streaming, just status updates)
      if (this.infoCallback) {
        // Handle both string and object formats
        const infoMessage = data.data.message || data.data;
        this.infoCallback(infoMessage);
      }
    }
    else if (data.type === 'countyResource') {
      // Handle county PDF resource data sent before the AI stream starts
      console.log('County resource received:', data.data);
      if (this.countyResourceCallback) {
        this.countyResourceCallback(data.data);
      }
    }
    else {
      // Handle legacy format or other message types
      if (data.message && this.messageCallback) {
        this.messageCallback(data.message, false);
        // For legacy messages, also call completion callback
        if (this.completionCallback) {
          this.completionCallback();
        }
        this.close(); // Close for non-streaming messages
      }
    }
  }

  // Send message with chat history and user info
  sendMessage(message, messages, userInfo = null) {
    return new Promise((resolve, reject) => {
      if (!this.isConnected) {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      // Get or generate conversation ID
      const conversationId = this.getConversationId();

      const packet = {
        action: 'sendMessage', // Route name for API Gateway
        message: message,
        messages: messages,
        conversationId: conversationId, // Include conversation ID
        userInfo: userInfo // Include user info if provided
      };

      try {
        this.ws.send(JSON.stringify(packet));
        console.log('Message sent:', packet);
        resolve();
      } catch (error) {
        console.error('Error sending message:', error);
        reject(error);
      }
    });
  }

  // Close WebSocket connection
  close() {
    if (this.ws && this.isConnected) {
      this.ws.close();
      console.log('WebSocket connection closed manually');
    }
    // Reset message state (but preserve conversationId)
    this.currentMessage = '';
    this.hasContent = false;
    this.shouldCreateNewMessage = false;
    this.infoCallback = null;
    this.completionCallback = null;
    this.countyResourceCallback = null;
  }

  // Get connection status
  getConnectionStatus() {
    if (this.isConnecting) return 'connecting';
    if (this.isConnected) return 'connected';
    return 'disconnected';
  }

  // Complete send message workflow (connect -> send -> wait for response -> close on messageStop)
  async sendMessageAndWaitForResponse(message, messages, onMessageReceived, onInfoReceived = null, onMessageComplete = null, userInfo = null, onCountyResourceReceived = null) {
    try {
      this.messageCallback = onMessageReceived;
      this.infoCallback = onInfoReceived;
      this.completionCallback = onMessageComplete;
      this.countyResourceCallback = onCountyResourceReceived;
      await this.connect();
      await this.sendMessage(message, messages, userInfo);
      // Connection will be closed automatically when messageStop is received
      return true;
    } catch (error) {
      console.error('Error in sendMessageAndWaitForResponse:', error);
      this.close(); // Ensure cleanup on error
      throw error;
    }
  }
}

// Create singleton instance
const webSocketManager = new WebSocketManager();
export default webSocketManager;