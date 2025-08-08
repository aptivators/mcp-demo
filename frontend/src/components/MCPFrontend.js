import { AlertCircle, CheckCircle, Database, Loader2, MessageSquare, Send, Server, Settings } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

const MCPFrontend = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [serverStatus, setServerStatus] = useState({
    medicare: 'disconnected',
    azure: 'disconnected'
  });
  // TODO: Move the configuration to a more secure place in production
  const [config, setConfig] = useState({
    geminiApiKey: '',
    medicareServerUrl: 'http://localhost:3000',
    azureServerUrl: 'http://localhost:3001',
    azureClientId: '',
    azureTenantId: ''
  });
  const [showConfig, setShowConfig] = useState(false);
  const [selectedServer, setSelectedServer] = useState('both');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Check server status on component mount
    checkServerStatus();
  }, []);

  const checkServerStatus = async () => {
    // Check Medicare server
    try {
      const response = await fetch(`${config.medicareServerUrl}/health`);
      if (response.ok) {
        setServerStatus(prev => ({ ...prev, medicare: 'connected' }));
      }
    } catch (error) {
      setServerStatus(prev => ({ ...prev, medicare: 'error' }));
    }

    // Check Azure server
    try {
      const response = await fetch(`${config.azureServerUrl}/health`);
      if (response.ok) {
        setServerStatus(prev => ({ ...prev, azure: 'connected' }));
      }
    } catch (error) {
      setServerStatus(prev => ({ ...prev, azure: 'error' }));
    }
  };

  const getMCPTools = async (serverType) => {
    const serverUrl = serverType === 'medicare' ? config.medicareServerUrl : config.azureServerUrl;
    
    try {
      const response = await fetch(`${serverUrl}/tools`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error(`Failed to get ${serverType} tools:`, error);
    }
    return [];
  };

  const getMCPResources = async (serverType) => {
    const serverUrl = serverType === 'medicare' ? config.medicareServerUrl : config.azureServerUrl;
    
    try {
      const response = await fetch(`${serverUrl}/resources`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error(`Failed to get ${serverType} resources:`, error);
    }
    return [];
  };

  const callMCPTool = async (serverType, toolName, parameters) => {
    const serverUrl = serverType === 'medicare' ? config.medicareServerUrl : config.azureServerUrl;
    
    try {
      const response = await fetch(`${serverUrl}/call-tool`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: toolName,
          arguments: parameters
        })
      });
      
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error(`Failed to call ${serverType} tool ${toolName}:`, error);
    }
    return null;
  };

  const callGeminiWithMCP = async (userMessage) => {
    if (!config.geminiApiKey) {
      throw new Error('Gemini API key not configured');
    }

    // Get available tools and resources from selected servers
    let availableTools = [];
    let availableResources = [];

    if (selectedServer === 'medicare' || selectedServer === 'both') {
      const medicareTools = await getMCPTools('medicare');
      const medicareResources = await getMCPResources('medicare');
      availableTools = [...availableTools, ...medicareTools.map(t => ({ ...t, server: 'medicare' }))];
      availableResources = [...availableResources, ...medicareResources.map(r => ({ ...r, server: 'medicare' }))];
    }

    if (selectedServer === 'azure' || selectedServer === 'both') {
      const azureTools = await getMCPTools('azure');
      const azureResources = await getMCPResources('azure');
      availableTools = [...availableTools, ...azureTools.map(t => ({ ...t, server: 'azure' }))];
      availableResources = [...availableResources, ...azureResources.map(r => ({ ...r, server: 'azure' }))];
    }

    // Prepare context for Gemini
    const systemPrompt = `You are an AI assistant with access to MCP (Model Context Protocol) servers. 
    
Available Tools:
${availableTools.map(tool => `- ${tool.name} (${tool.server} server): ${tool.description || 'No description'}`).join('\n')}

Available Resources:
${availableResources.map(resource => `- ${resource.name} (${resource.server} server): ${resource.description || 'No description'}`).join('\n')}

When you need to use a tool or access a resource, indicate which server and tool/resource you want to use. The user's message is: "${userMessage}"

Please help the user with their request using the available MCP tools and resources.`;

    try {
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${config.geminiApiKey}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents: [{
            parts: [{
              text: systemPrompt
            }]
          }]
        })
      });

      if (!response.ok) {
        throw new Error(`Gemini API error: ${response.statusText}`);
      }

      const data = await response.json();
      return data.candidates[0].content.parts[0].text;
    } catch (error) {
      throw new Error(`Failed to call Gemini API: ${error.message}`);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await callGeminiWithMCP(inputValue);
      
      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response,
        timestamp: new Date().toLocaleTimeString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date().toLocaleTimeString()
      };

      setMessages(prev => [...prev, errorMessage]);
    }

    setIsLoading(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <div className="w-4 h-4 rounded-full bg-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected':
        return 'text-green-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">MCP Demo Frontend</h1>
              <p className="text-gray-300">Powered by Gemini 2.0 Flash with Model Context Protocol</p>
            </div>
            <button
              onClick={() => setShowConfig(!showConfig)}
              className="p-3 bg-white/10 hover:bg-white/20 rounded-xl backdrop-blur-sm transition-all"
            >
              <Settings className="w-6 h-6 text-white" />
            </button>
          </div>

          {/* Server Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Database className="w-5 h-5 text-blue-400" />
                  <span className="text-white font-medium">Medicare Server</span>
                </div>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(serverStatus.medicare)}
                  <span className={`text-sm ${getStatusColor(serverStatus.medicare)}`}>
                    {serverStatus.medicare}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Server className="w-5 h-5 text-purple-400" />
                  <span className="text-white font-medium">Azure Server</span>
                </div>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(serverStatus.azure)}
                  <span className={`text-sm ${getStatusColor(serverStatus.azure)}`}>
                    {serverStatus.azure}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Configuration Panel */}
          {showConfig && (
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 mb-6">
              <h3 className="text-xl font-semibold text-white mb-4">Configuration</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Gemini API Key
                  </label>
                  <input
                    type="password"
                    value={config.geminiApiKey}
                    onChange={(e) => setConfig(prev => ({ ...prev, geminiApiKey: e.target.value }))}
                    className="w-full p-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Enter your Gemini API key"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Server Selection
                  </label>
                  <select
                    value={selectedServer}
                    onChange={(e) => setSelectedServer(e.target.value)}
                    className="w-full p-3 bg-white/20 border border-white/30 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="both">Both Servers</option>
                    <option value="medicare">Medicare Server Only</option>
                    <option value="azure">Azure Server Only</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Medicare Server URL
                  </label>
                  <input
                    type="text"
                    value={config.medicareServerUrl}
                    onChange={(e) => setConfig(prev => ({ ...prev, medicareServerUrl: e.target.value }))}
                    className="w-full p-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="http://localhost:3000"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Azure Server URL
                  </label>
                  <input
                    type="text"
                    value={config.azureServerUrl}
                    onChange={(e) => setConfig(prev => ({ ...prev, azureServerUrl: e.target.value }))}
                    className="w-full p-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="http://localhost:3001"
                  />
                </div>
              </div>
              <button
                onClick={checkServerStatus}
                className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                Test Connections
              </button>
            </div>
          )}
        </div>

        {/* Chat Interface */}
        <div className="bg-white/10 backdrop-blur-sm rounded-xl overflow-hidden">
          {/* Messages */}
          <div className="h-96 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 py-12">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Start a conversation with your MCP servers!</p>
                <p className="text-sm mt-2">Try asking about Medicare datasets or Azure resources.</p>
              </div>
            )}
            
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-3 rounded-xl ${
                    message.type === 'user'
                      ? 'bg-purple-600 text-white'
                      : message.type === 'error'
                      ? 'bg-red-600 text-white'
                      : 'bg-white/20 text-white'
                  }`}
                >
                  <div className="text-sm">{message.content}</div>
                  <div className="text-xs opacity-70 mt-2">{message.timestamp}</div>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white/20 text-white px-4 py-3 rounded-xl flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-white/20 p-4">
            <div className="flex space-x-4">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask questions about Medicare data or Azure resources..."
                className="flex-1 p-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                rows="1"
                disabled={isLoading}
              />
              <button
                onClick={handleSendMessage}
                disabled={isLoading || !inputValue.trim()}
                className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:opacity-50 text-white rounded-lg transition-colors flex items-center space-x-2"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => setInputValue("What Medicare datasets are available?")}
            className="p-4 bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-xl text-white transition-all text-left"
          >
            <div className="font-medium">Explore Medicare Data</div>
            <div className="text-sm text-gray-300 mt-1">View available datasets and documents</div>
          </button>
          
          <button
            onClick={() => setInputValue("Show me Azure resources I can access")}
            className="p-4 bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-xl text-white transition-all text-left"
          >
            <div className="font-medium">Azure Resources</div>
            <div className="text-sm text-gray-300 mt-1">List accessible Azure services</div>
          </button>
          
          <button
            onClick={() => setInputValue("What tools and capabilities do you have?")}
            className="p-4 bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-xl text-white transition-all text-left"
          >
            <div className="font-medium">Available Tools</div>
            <div className="text-sm text-gray-300 mt-1">See all MCP server capabilities</div>
          </button>
        </div>
      </div>
    </div>
  );
};

export default MCPFrontend;