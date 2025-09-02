import { useState } from 'react';

const AuthTokenDemo = () => {
  const [showModal, setShowModal] = useState(true);
  const [tokenData, setTokenData] = useState(null);
  const [sharepointFiles, setSharepointFiles] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sharepointLoading, setSharepointLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionHeaders, setSessionHeaders] = useState({});
  const [user, setUser] = useState(null);

  const handleAcceptWarning = () => {
    setShowModal(false);
  };

  const initializeMcpSession = async (baseUrl = 'http://127.0.0.1:8001/mcp', extraHeaders = {}) => {
    const baseHeaders = {
      'accept': 'application/json, text/event-stream',
      'content-type': 'application/json',
      ...extraHeaders
    };

    // Step 1: Initialize
    const initPayload = {
      "jsonrpc": "2.0",
      "method": "initialize",
      "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
          "name": "react-client",
          "version": "1.0.0"
        }
      },
      "id": 1
    };

    const initResponse = await fetch(baseUrl, {
      method: 'POST',
      headers: baseHeaders,
      body: JSON.stringify(initPayload)
    });

    if (!initResponse.ok) {
      throw new Error(`Initialize failed: ${initResponse.status}`);
    }

    // Debug: Check the actual response content
    const responseText = await initResponse.text();
    console.log('Initialize response:', responseText);
    const responseHeaders = initResponse.headers;
    console.log('Initialize response headers:', Array.from(responseHeaders.entries()));
    let sessionId = initResponse.headers.get('mcp-session-id');
    
    // Try to extract session ID from response body if not in headers
    if (!sessionId && responseText) {
      try {
        // Handle Server-Sent Events format
        const lines = responseText.split('\n');
        const dataLine = lines.find(line => line.startsWith('data: '));
        
        if (dataLine) {
          const jsonData = dataLine.substring(6);
          const responseData = JSON.parse(jsonData);
          sessionId = responseData.sessionId || responseData.result?.sessionId;
        }
      } catch (e) {
        console.log('Could not parse response for session ID');
      }
    }

    console.log('Final session ID:', sessionId);

    // If no session ID, proceed without it (some servers don't require it)
    const headersForRequests = sessionId ? 
      { ...baseHeaders, 'mcp-session-id': sessionId } : 
      baseHeaders;

    // Step 2: Send initialization complete notification
    const initCompletePayload = {
      "jsonrpc": "2.0",
      "method": "notifications/initialized"
    };

    await fetch(baseUrl, {
      method: 'POST',
      headers: headersForRequests,
      body: JSON.stringify(initCompletePayload)
    });

    return { sessionId: sessionId || 'no-session', headers: headersForRequests };
  };

  const callMcpTool = async (toolName, parameters = {}, baseUrl = 'http://127.0.0.1:8001/mcp', extraHeaders = {}) => {
    // Initialize session first
    const { sessionId, headers } = await initializeMcpSession(baseUrl, extraHeaders);

    // Step 3: Call the tool
    const toolPayload = {
      "jsonrpc": "2.0",
      "method": "tools/call",
      "params": {
        "name": toolName,
        ...(Object.keys(parameters).length > 0 && { arguments: parameters })
      },
      "id": 2
    };

    const response = await fetch(baseUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(toolPayload)
    });

    if (!response.ok) {
      throw new Error(`Tool call failed: ${response.status}`);
    }

    const responseText = await response.text();
    
    // Handle Server-Sent Events response
    const lines = responseText.split('\n');
    const dataLine = lines.find(line => line.startsWith('data: '));
    
    if (dataLine) {
      const jsonData = dataLine.substring(6); // Remove 'data: ' prefix
      const result = JSON.parse(jsonData);
      
      if (result.error) {
        throw new Error(result.error.message || 'MCP call failed');
      }
      
      return { result: result.result, sessionId };
    } else {
      throw new Error('No data found in response: ' + responseText);
    }
  };

  const retrieveSharePointFiles = async (accessToken) => {
    setSharepointLoading(true);
    
    try {
      console.log('Calling SharePoint MCP server...');
      
      // Call the SharePoint MCP server with the access token
      const { result } = await callMcpTool(
        'get_sharepoint_files', 
        {}, 
        'http://127.0.0.1:8002/mcp',
        { 'authorization': `Bearer ${accessToken}` }
      );
      
      // Parse the result - it should contain the SharePoint files
      const contentText = result.content?.[0]?.text;
      let filesData = null;
      
      if (contentText) {
        try {
          const parsedContent = JSON.parse(contentText);
          filesData = parsedContent;
          console.log('SharePoint files data:', filesData);
        } catch (parseError) {
          console.error('Error parsing SharePoint response:', parseError);
          filesData = { error: 'Failed to parse SharePoint response', raw: contentText };
        }
      } else {
        filesData = result;
      }
      
      setSharepointFiles(filesData);
      
    } catch (err) {
      console.error('SharePoint call failed:', err);
      setSharepointFiles({ 
        error: `Failed to retrieve SharePoint files: ${err.message}`,
        status: 'failed'
      });
    } finally {
      setSharepointLoading(false);
    }
  };

  const retrieveToken = async () => {
    setLoading(true);
    setError(null);
    setSharepointFiles(null);
    
    try {
      console.log('Retrieving token from auth MCP server...');
      const { result, sessionId } = await callMcpTool('get_service_token', {});
      
      // Extract token from the result (following your Python script pattern)
      const contentText = result.content?.[0]?.text;
      
      if (!contentText) {
        throw new Error('No content received from auth server');
      }
      
      // Parse the content to get user info and token
      const parsedContent = JSON.parse(contentText);
      const user = parsedContent.user;
      const accessToken = parsedContent.authentication?.access_token;
      
      if (!accessToken) {
        throw new Error('No access token received from auth server');
      }
      
      setUser(user);
      console.log('User:', user);
      console.log('Access token received (first 20 chars):', accessToken.substring(0, 20) + '...');

      // Add token to session headers
      const newHeaders = {
        'Authorization': `Bearer ${accessToken}`,
        'X-Session-Token': accessToken,
        'Mcp-Session-Id': sessionId,
        'Content-Type': 'application/json'
      };
      
      setSessionHeaders(newHeaders);
      
      // For demonstration, we'll decode basic info from the token
      let decodedInfo = {};
      try {
        if (typeof accessToken === 'string' && accessToken.includes('.')) {
          // If it's a JWT, try to decode the payload (unsecure demo only)
          const payload = accessToken.split('.')[1];
          const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
          decodedInfo = decoded;
        } else {
          decodedInfo = { token: accessToken.substring(0, 20) + '...', type: 'opaque_token' };
        }
      } catch (decodeError) {
        decodedInfo = { 
          token: accessToken.substring(0, 20) + '...',
          type: 'unknown_format'
        };
      }
      
      setTokenData({
        raw: result,
        decoded: decodedInfo,
        headers: newHeaders,
        sessionId: sessionId,
        parsedContent: parsedContent
      });
      
      // Now retrieve SharePoint files with the token
      await retrieveSharePointFiles(accessToken);
      
    } catch (err) {
      console.error('Token retrieval failed:', err);
      setError(`Failed to retrieve token: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const renderSharePointFiles = () => {
    if (sharepointLoading) {
      return (
        <div className="flex items-center justify-center py-8">
          <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="ml-2 text-gray-600">Loading SharePoint files...</span>
        </div>
      );
    }

    if (!sharepointFiles) {
      return (
        <div className="bg-gray-50 rounded-md p-4">
          <p className="text-sm text-gray-600">No SharePoint data available. Retrieve token first.</p>
        </div>
      );
    }

    if (sharepointFiles.error) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">SharePoint Error</h3>
              <p className="mt-1 text-sm text-red-700">{sharepointFiles.error}</p>
              {sharepointFiles.raw && (
                <details className="mt-2">
                  <summary className="text-xs text-red-600 cursor-pointer">Raw response</summary>
                  <pre className="mt-1 text-xs text-red-600 whitespace-pre-wrap">{JSON.stringify(sharepointFiles.raw, null, 2)}</pre>
                </details>
              )}
            </div>
          </div>
        </div>
      );
    }

    // Display SharePoint files
    const files = sharepointFiles.objects || [];
    
    if (files.length === 0) {
      return (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <p className="text-sm text-yellow-800">No files found in the SharePoint folder.</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <p className="text-sm text-green-800">
            <strong>Success:</strong> Found {files.length} file{files.length !== 1 ? 's' : ''} in SharePoint folder.
          </p>
        </div>
        
        <div className="bg-gray-50 rounded-md p-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Files:</h4>
          <div className="space-y-2">
            {files.map((file, index) => {
              // Construct the full SharePoint URL for the file using SP_COMPANY
              const baseUrl = process.env.REACT_APP_SP_BASE_URL;
              console.log('Base URL from env:', baseUrl);
              const fileUrl = file.ServerRelativeUrl ? `${baseUrl}${file.ServerRelativeUrl}` : null;
              
              // Alternative URL construction if __metadata is available
              const alternativeUrl = file.__metadata?.uri || file.odata?.editLink;
              
              const downloadUrl = fileUrl || alternativeUrl;
              
              return (
                <div key={index} className="bg-white rounded border p-3 hover:shadow-sm transition-shadow">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        {/* File icon */}
                        <svg className="h-5 w-5 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        
                        {/* File name - clickable if URL is available */}
                        {downloadUrl ? (
                          <a 
                            href={downloadUrl}
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="font-medium text-sm text-blue-600 hover:text-blue-800 hover:underline truncate"
                            title={`Open ${file.Name || file.name || 'file'}`}
                          >
                            {file.Name || file.name || 'Unnamed file'}
                          </a>
                        ) : (
                          <p className="font-medium text-sm text-gray-900 truncate">
                            {file.Name || file.name || 'Unnamed file'}
                          </p>
                        )}
                        
                        {/* External link icon for clickable files */}
                        {downloadUrl && (
                          <svg className="h-3 w-3 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        )}
                      </div>
                      
                    </div>
                    
                    <div className="text-right text-xs text-gray-500 ml-4 flex-shrink-0">
                      {file.Length && <p>Size: {Math.round(file.Length / 1024)} KB</p>}
                      {file.TimeLastModified && <p>Modified: {new Date(file.TimeLastModified).toLocaleDateString()}</p>}
                      
                      {/* Additional action buttons */}
                      {downloadUrl && (
                        <div className="flex space-x-1 mt-1">
                          <a
                            href={downloadUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100"
                            title="Open file"
                          >
                            Open
                          </a>
                          <button
                            onClick={() => navigator.clipboard.writeText(downloadUrl)}
                            className="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-600 bg-gray-50 rounded hover:bg-gray-100"
                            title="Copy link"
                          >
                            Copy Link
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        
        <details className="bg-gray-50 rounded-md p-4">
          <summary className="text-sm font-medium text-gray-900 cursor-pointer">Raw SharePoint Response</summary>
          <pre className="mt-3 text-xs text-gray-800 whitespace-pre-wrap overflow-x-auto">
            {JSON.stringify(sharepointFiles, null, 2)}
          </pre>
        </details>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      {/* Warning Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h3 className="ml-3 text-lg font-medium text-gray-900">
                Usage Monitoring Notice
              </h3>
            </div>
            <div className="mb-6">
              <p className="text-sm text-gray-600 mb-3">
                This application connects to external services and your usage may be monitored and logged for security and compliance purposes.
              </p>
              <p className="text-sm text-gray-600 mb-3">
                By proceeding, you acknowledge that:
              </p>
              <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                <li>Your activities may be recorded</li>
                <li>Tokens and requests are handled for demonstration purposes</li>
                <li>This is a development/testing environment</li>
              </ul>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => window.close()}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 border border-gray-300 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                  onClick={() => { handleAcceptWarning(); retrieveToken(); }}
                  disabled={loading}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Retrieving Token...
                    </>
                  ) : (
                    'I Understand, Continue'
                  )}
                </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      {!showModal && (
        <div className="max-w-4xl mx-auto">
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h1 className="text-2xl font-bold text-gray-900">
                Hello {user?.displayName || 'User'}!
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Retrieve authentication token from MCP server and access SharePoint files
              </p>
            </div>

            <div className="p-6">
              {error && (
                <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
                  <div className="flex">
                    <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">Error</h3>
                      <p className="mt-1 text-sm text-red-700">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              {!tokenData && !loading && (
                <div className="text-center py-8">
                  <button
                    onClick={retrieveToken}
                    disabled={loading}
                    className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Retrieving Token...
                      </>
                    ) : (
                      'Retrieve Token & SharePoint Files'
                    )}
                  </button>
                </div>
              )}

              {tokenData && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-3">
                      MCP Session Info
                    </h3>
                    <div className="bg-blue-50 rounded-md p-4">
                      <p className="text-sm text-blue-800">
                        <strong>Session ID:</strong> <code>{tokenData.sessionId}</code>
                      </p>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-3">
                      List of SharePoint Files
                    </h3>
                    {renderSharePointFiles()}
                  </div>

                  <details>
                    <summary className="text-lg font-medium text-gray-900 mb-3 cursor-pointer">
                      Raw MCP Response (Auth Server)
                    </summary>
                    <div className="bg-gray-50 rounded-md p-4 overflow-x-auto">
                      <pre className="text-sm text-gray-800 whitespace-pre-wrap">
                        {JSON.stringify(tokenData.raw, null, 2)}
                      </pre>
                    </div>
                  </details>
                </div>
              )}
            </div>
          </div>

          {/* Connection Status */}
          <div className="mt-6 bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">
                MCP Server Connections
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-3 w-3 bg-green-400 rounded-full"></div>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-gray-900">
                    Auth Server: <code className="bg-gray-100 px-2 py-1 rounded text-xs">http://127.0.0.1:8001/mcp</code>
                  </p>
                  <p className="text-sm text-gray-600">
                    Tool: get_service_token
                  </p>
                </div>
              </div>
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className={`h-3 w-3 rounded-full ${sharepointFiles && sharepointFiles.status === 'success' ? 'bg-green-400' : sharepointFiles && sharepointFiles.error ? 'bg-red-400' : 'bg-gray-400'}`}></div>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-gray-900">
                    SharePoint Server: <code className="bg-gray-100 px-2 py-1 rounded text-xs">http://127.0.0.1:8002/mcp</code>
                  </p>
                  <p className="text-sm text-gray-600">
                    Tool: get_sharepoint_files
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuthTokenDemo;