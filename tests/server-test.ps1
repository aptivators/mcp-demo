# Medicare MCP Server Test Script (Fixed Version)
# Save as: server-test-fixed.ps1

Write-Host "Testing Medicare MCP Server (Streamable HTTP)..." -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

function Parse-SSEResponse {
    param([string]$Content)
    Write-Host "Raw SSE Content:" -ForegroundColor Gray
    Write-Host $Content -ForegroundColor Gray
    Write-Host "--- End Raw Content ---" -ForegroundColor Gray
    
    # Split on double newlines to separate events
    $events = $Content -split "`r`n`r`n|`n`n"
    $results = @()
    
    foreach ($event in $events) {
        if ($event.Trim() -eq "") { continue }
        
        Write-Host "Processing event block: '$event'" -ForegroundColor DarkGray
        
        # Split lines and look for data
        $lines = $event -split "`r`n|`n"
        $dataLines = @()
        
        foreach ($line in $lines) {
            $line = $line.Trim()
            if ($line.StartsWith("data:")) {
                # Extract everything after "data:" (with or without space)
                if ($line.StartsWith("data: ")) {
                    $dataLines += $line.Substring(6)
                } elseif ($line.StartsWith("data:")) {
                    $dataLines += $line.Substring(5)
                }
            }
        }
        
        if ($dataLines.Count -gt 0) {
            $data = $dataLines -join ""
            Write-Host "Extracted data: $data" -ForegroundColor DarkGray
            
            if ($data.Trim() -ne "") {
                try {
                    $jsonData = $data | ConvertFrom-Json
                    $results += $jsonData
                    Write-Host "Successfully parsed JSON data, results count now: $($results.Count)" -ForegroundColor Green
                }
                catch {
                    Write-Host "Could not parse SSE data as JSON: $data" -ForegroundColor Yellow
                    Write-Host "Parse error: $($_.Exception.Message)" -ForegroundColor Yellow
                }
            }
        }
    }
    
    Write-Host "Final results count before return: $($results.Count)" -ForegroundColor Magenta
    Write-Host "Results type: $($results.GetType().Name)" -ForegroundColor Magenta
    
    # Force return as array to prevent PowerShell from unwrapping
    return ,$results
}

function Process-Response {
    param(
        [Microsoft.PowerShell.Commands.WebResponseObject]$Response,
        [string]$TestName
    )
    $contentType = $Response.Headers['Content-Type']
    Write-Host "Content-Type: $contentType" -ForegroundColor Gray
    try {
        if ($contentType -like "*text/event-stream*") {
            Write-Host "Processing SSE response..." -ForegroundColor Yellow
            $results = Parse-SSEResponse -Content $Response.Content
            Write-Host "Results count: $($results.Count)" -ForegroundColor Gray
            
            if ($results -and $results.Count -gt 0) {
                Write-Host "SUCCESS: $TestName completed!" -ForegroundColor Green
                foreach ($result in $results) {
                    Write-Host "Response data:" -ForegroundColor Cyan
                    $result | ConvertTo-Json -Depth 4
                    Write-Host "" # Empty line for readability
                }
                return $results
            } else {
                Write-Host "No valid JSON data found in SSE response" -ForegroundColor Yellow
                return $null
            }
        }
        elseif ($contentType -like "*application/json*") {
            Write-Host "Processing JSON response..." -ForegroundColor Yellow
            $jsonData = $Response.Content | ConvertFrom-Json
            Write-Host "SUCCESS: $TestName completed!" -ForegroundColor Green
            Write-Host "Response data:" -ForegroundColor Cyan
            $jsonData | ConvertTo-Json -Depth 4
            return $jsonData
        }
        else {
            Write-Host "Unknown Content-Type: $contentType" -ForegroundColor Red
            Write-Host "Raw response content:" -ForegroundColor Gray
            $Response.Content
            return $null
        }
    }
    catch {
        Write-Host "FAILED: Error processing $TestName response - $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Raw response content:" -ForegroundColor Gray
        $Response.Content
        return $null
    }
}

function Send-MCPRequest {
    param(
        [string]$Body,
        [string]$TestName,
        [hashtable]$Headers
    )
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/mcp/" -Method Post -Body $Body -Headers $Headers
        $result = Process-Response -Response $response -TestName $TestName
        return @{
            Response = $response
            Data = $result
        }
    }
    catch {
        Write-Host "FAILED: $TestName error - $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "Error response body: $responseBody" -ForegroundColor Red
        }
        return $null
    }
}

# Common headers for Streamable HTTP transport
$headers = @{
    'Content-Type' = 'application/json'
    'Accept' = 'application/json, text/event-stream'
}

# 1. Initialize MCP session
Write-Host ""
Write-Host "1. Initializing MCP session..." -ForegroundColor Yellow

$initBody = @"
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "clientInfo": {"name": "test-client", "version": "1.0"},
    "capabilities": {}
  },
  "id": 1
}
"@

$initResult = Send-MCPRequest -Body $initBody -TestName "Initialize" -Headers $headers

if (-not $initResult) {
    Write-Host "FAILED: Could not initialize MCP session. Exiting." -ForegroundColor Red
    exit 1
}

# Extract session ID from response headers
$sessionId = $null
if ($initResult.Response -and $initResult.Response.Headers['Mcp-Session-Id']) {
    $sessionId = $initResult.Response.Headers['Mcp-Session-Id']
    Write-Host "Session ID: $sessionId" -ForegroundColor Cyan
    $headers['Mcp-Session-Id'] = $sessionId
} else {
    Write-Host "WARNING: No session ID received, continuing without session..." -ForegroundColor Yellow
}

# Check if initialization was successful
if ($initResult.Data -and $initResult.Data[0] -and $initResult.Data[0].error) {
    Write-Host "FAILED: Initialization returned error: $($initResult.Data[0].error.message)" -ForegroundColor Red
    exit 1
}

# 1.5. Send initialized notification (THIS IS THE MISSING STEP!)
Write-Host ""
Write-Host "1.5. Sending initialized notification..." -ForegroundColor Yellow

$initializedBody = @"
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized",
  "params": {}
}
"@

Send-MCPRequest -Body $initializedBody -TestName "Initialized Notification" -Headers $headers

# Wait a moment for the server to process
Start-Sleep -Milliseconds 500

# 2. List resources
Write-Host ""
Write-Host "2. Listing available resources..." -ForegroundColor Yellow

$resourcesBody = @"
{
    "jsonrpc": "2.0",
    "method": "resources/list",
    "params": {},
    "id": 2
}
"@
Send-MCPRequest -Body $resourcesBody -TestName "Resources List" -Headers $headers

# 3. Test application status resource
Write-Host ""
Write-Host "3. Testing application status resource..." -ForegroundColor Yellow

$statusBody = @"
{
    "jsonrpc": "2.0",
    "method": "resources/read",
    "params": {
        "uri": "data://app-status"
    },
    "id": 3
}
"@
Send-MCPRequest -Body $statusBody -TestName "Application Status" -Headers $headers

# 4. List tools
Write-Host ""
Write-Host "4. Listing available tools..." -ForegroundColor Yellow

$toolsBody = @"
{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 4
}
"@
Send-MCPRequest -Body $toolsBody -TestName "Tools List" -Headers $headers

# 5. Test health tool
Write-Host ""
Write-Host "5. Testing health tool..." -ForegroundColor Yellow

$healthBody = @"
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "health",
        "arguments": {}
    },
    "id": 5
}
"@
Send-MCPRequest -Body $healthBody -TestName "Health Tool" -Headers $headers

# 6. List Medicare datasets
Write-Host ""
Write-Host "6. Testing Medicare datasets resource..." -ForegroundColor Yellow

$datasetsBody = @"
{
  "jsonrpc": "2.0",
  "method": "resources/read",
  "params": {
    "uri": "medicare://datasets"
  },
  "id": 6
}
"@
Send-MCPRequest -Body $datasetsBody -TestName "Medicare Datasets" -Headers $headers

# 7. Test Medicare documents list tool
Write-Host ""
Write-Host "7. Testing Medicare documents list..." -ForegroundColor Yellow

$documentsBody = @"
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "list_medicare_documents",
        "arguments": {}
    },
    "id": 7
}
"@
Send-MCPRequest -Body $documentsBody -TestName "Medicare Documents List" -Headers $headers

# 8. Test nursing home dataset
Write-Host ""
Write-Host "8. Testing nursing home dataset resource..." -ForegroundColor Yellow

$nursingHomeBody = @"
{
  "jsonrpc": "2.0",
  "method": "resources/read",
  "params": {
    "uri": "medicare://nursing-home-dataset"
  },
  "id": 8
}
"@
Send-MCPRequest -Body $nursingHomeBody -TestName "Nursing Home Dataset" -Headers $headers

# 9. Test prompts list
Write-Host ""
Write-Host "9. Listing available prompts..." -ForegroundColor Yellow

$promptsBody = @"
{
    "jsonrpc": "2.0",
    "method": "prompts/list",
    "params": {},
    "id": 9
}
"@
Send-MCPRequest -Body $promptsBody -TestName "Prompts List" -Headers $headers

# 10. Test a prompt
Write-Host ""
Write-Host "10. Testing explain tools prompt..." -ForegroundColor Yellow

$explainToolsBody = @"
{
    "jsonrpc": "2.0",
    "method": "prompts/get",
    "params": {
        "name": "explain_available_tools",
        "arguments": {}
    },
    "id": 10
}
"@
Send-MCPRequest -Body $explainToolsBody -TestName "Explain Tools Prompt" -Headers $headers

# Fixed Test Case 11 - SharePoint Query via Medicare MCP server
# This version is self-contained and doesn't depend on external functions

Write-Host ""
Write-Host "11. Testing SharePoint query tool via Medicare MCP server..." -ForegroundColor Yellow

# Simple SSE parser function (self-contained)
function Parse-SimpleSSE {
    param([string]$Content)
    $results = @()
    $events = $Content -split "`r`n`r`n|`n`n"
    
    foreach ($event in $events) {
        if ($event.Trim() -eq "") { continue }
        $lines = $event -split "`r`n|`n"
        
        foreach ($line in $lines) {
            $line = $line.Trim()
            if ($line.StartsWith("data:")) {
                $data = if ($line.StartsWith("data: ")) { $line.Substring(6) } else { $line.Substring(5) }
                if ($data.Trim() -ne "") {
                    try {
                        $jsonData = $data | ConvertFrom-Json
                        $results += $jsonData
                    }
                    catch {
                        Write-Host "Could not parse SSE data: $data" -ForegroundColor Yellow
                    }
                }
            }
        }
    }
    return ,$results
}

Write-Host ""
Write-Host "11. Testing SharePoint query tool via Medicare MCP server..." -ForegroundColor Yellow

# Step 1: Get access token from Auth MCP server
Write-Host "11a. Getting access token from Auth MCP server..." -ForegroundColor Cyan

# First, we need to initialize the Auth MCP server session too
$authHeaders = @{
    'Content-Type' = 'application/json'
    'Accept' = 'application/json, text/event-stream'
}

# Initialize Auth MCP session
$authInitBody = @"
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "clientInfo": {"name": "test-client", "version": "1.0"},
    "capabilities": {}
  },
  "id": 1
}
"@

try {
    Write-Host "Initializing Auth MCP server session..." -ForegroundColor Gray
    $authInitResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8001/mcp/" -Method Post -Body $authInitBody -Headers $authHeaders
    
    # Process the auth init response inline (since Process-Response function may not be in scope)
    Write-Host "Processing Auth server initialization response..." -ForegroundColor Gray
    $contentType = $authInitResponse.Headers['Content-Type']
    Write-Host "Auth server content-type: $contentType" -ForegroundColor Gray
    
    if ($contentType -like "*text/event-stream*") {
        $authInitResult = Parse-SimpleSSE -Content $authInitResponse.Content
    } elseif ($contentType -like "*application/json*") {
        $authInitResult = $authInitResponse.Content | ConvertFrom-Json
    } else {
        Write-Host "Unknown Auth server response format: $contentType" -ForegroundColor Yellow
        $authInitResult = $null
    }
    
    # Get session ID for auth server
    $authSessionId = $null
    if ($authInitResponse.Headers['Mcp-Session-Id']) {
        $authSessionId = $authInitResponse.Headers['Mcp-Session-Id']
        Write-Host "Auth Server Session ID: $authSessionId" -ForegroundColor Cyan
        $authHeaders['Mcp-Session-Id'] = $authSessionId
    }
    
    # Send initialized notification to auth server
    $authInitializedBody = @"
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized",
  "params": {}
}
"@
    Invoke-WebRequest -Uri "http://127.0.0.1:8001/mcp/" -Method Post -Body $authInitializedBody -Headers $authHeaders | Out-Null
    Start-Sleep -Milliseconds 500
    
    Write-Host "Auth MCP server initialized successfully." -ForegroundColor Green
}
catch {
    Write-Host "FAILED: Could not initialize Auth MCP server - $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure the Auth MCP server is running on port 8001" -ForegroundColor Yellow
    # Continue without auth for testing other functionality
    $accessToken = $null
}

# Now try to get the access token
if ($authHeaders['Mcp-Session-Id']) {
    $authTokenBody = @"
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "get_access_token_only",
        "arguments": {}
    },
    "id": 11
}
"@
 
    try {
        Write-Host "Requesting access token from Auth MCP server..." -ForegroundColor Gray
        $authResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8001/mcp/" -Method Post -Body $authTokenBody -Headers $authHeaders
        
        # Process the token response inline
        Write-Host "Processing token response..." -ForegroundColor Gray
        $contentType = $authResponse.Headers['Content-Type']
        Write-Host "Token response content-type: $contentType" -ForegroundColor Gray
        
        if ($contentType -like "*text/event-stream*") {
            $authResult = Parse-SimpleSSE -Content $authResponse.Content
        } elseif ($contentType -like "*application/json*") {
            $authResult = @($authResponse.Content | ConvertFrom-Json)
        } else {
            Write-Host "Unknown token response format: $contentType" -ForegroundColor Yellow
            $authResult = $null
        }
        
        Write-Host "Auth response processed. Checking for token..." -ForegroundColor Gray
        Write-Host "Raw auth result type: $($authResult.GetType().Name)" -ForegroundColor Gray
        Write-Host "Auth result count: $($authResult.Count)" -ForegroundColor Gray
        
        # Debug: Show the full response structure
        if ($authResult) {
            Write-Host "Full auth response structure:" -ForegroundColor Gray
            $authResult | ConvertTo-Json -Depth 5
        }
        
        # Handle different response formats (SSE vs JSON)
        $accessToken = $null
        if ($authResult -and $authResult.Count -gt 0) {
            # For SSE responses, authResult is an array
            $tokenData = $authResult[0]
            Write-Host "Token data type: $($tokenData.GetType().Name)" -ForegroundColor Gray
            
            # Check different possible response structures
            if ($tokenData -and $tokenData.result) {
                Write-Host "Found result object in token data" -ForegroundColor Gray
                if ($tokenData.result.access_token) {
                    $accessToken = $tokenData.result.access_token
                    Write-Host "Found access_token in result.access_token" -ForegroundColor Green
                } elseif ($tokenData.result.structuredContent -and $tokenData.result.structuredContent.access_token) {
                    $accessToken = $tokenData.result.structuredContent.access_token
                    Write-Host "Found access_token in result.structuredContent.access_token" -ForegroundColor Green
                } elseif ($tokenData.result.token) {
                    $accessToken = $tokenData.result.token
                    Write-Host "Found access_token in result.token" -ForegroundColor Green
                } elseif ($tokenData.result -is [string]) {
                    $accessToken = $tokenData.result
                    Write-Host "Found access_token as direct result string" -ForegroundColor Green
                } else {
                    Write-Host "Result object found but no recognized token field:" -ForegroundColor Yellow
                    $tokenData.result | ConvertTo-Json -Depth 3
                }
            } elseif ($tokenData -and $tokenData.access_token) {
                $accessToken = $tokenData.access_token
                Write-Host "Found access_token directly in response" -ForegroundColor Green
            } elseif ($tokenData -and $tokenData.token) {
                $accessToken = $tokenData.token
                Write-Host "Found token directly in response" -ForegroundColor Green
            } elseif ($tokenData -and $tokenData.error) {
                Write-Host "FAILED: Auth server returned error: $($tokenData.error.message)" -ForegroundColor Red
            } else {
                Write-Host "FAILED: Could not find access token in response" -ForegroundColor Red
                Write-Host "Available fields in tokenData:" -ForegroundColor Yellow
                if ($tokenData) {
                    $tokenData | Get-Member -MemberType Properties | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Yellow }
                }
            }
            
            if ($accessToken) {
                Write-Host "Successfully extracted access token from Auth MCP server." -ForegroundColor Green
                Write-Host "Token preview: $($accessToken.Substring(0, [Math]::Min(20, $accessToken.Length)))..." -ForegroundColor Cyan
            }
        } else {
            Write-Host "FAILED: No data returned from Auth MCP server or empty array" -ForegroundColor Red
        }
    } catch {
        Write-Host "FAILED: Error getting token from Auth MCP server - $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "Error response body: $responseBody" -ForegroundColor Red
        }
        $accessToken = $null
    }
} else {
    Write-Host "FAILED: No Auth MCP server session available" -ForegroundColor Red
    $accessToken = $null
}

# Step 2: Use token for Medicare MCP server SharePoint query
if ($accessToken) {
    Write-Host ""
    Write-Host "11b. Using token for SharePoint query via Medicare MCP server..." -ForegroundColor Cyan

    $company = "yourcompany"  # Replace with your actual company name
    $sitePath = "/sites/your-site"  # Replace with your actual site path
    $folderRelativeUrl = "Shared Documents/YourFolder"

    # Use the SharePoint REST API to get files in the folder
    $sharepointUrl = "https://$company.sharepoint.com$sitePath/_api/web/GetFolderByServerRelativeUrl('$folderRelativeUrl')/Files"

    Write-Host "Using SharePoint REST API URL: $sharepointUrl" -ForegroundColor Gray

    $sharepointBody = @"
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "query_sharepoint",
        "arguments": {
            "sharepoint_url": "$sharepointUrl",
            "access_token": "$accessToken"
        }
    },
    "id": 12
}
"@

    $sharepointResult = Send-MCPRequest -Body $sharepointBody -TestName "SharePoint Query via Medicare Server" -Headers $headers

    if ($sharepointResult -and $sharepointResult.Data) {
        Write-Host "SharePoint query completed successfully!" -ForegroundColor Green
        if ($sharepointResult.Data.Count -gt 0 -and $sharepointResult.Data[0].result) {
            $result = $sharepointResult.Data[0].result
            if ($result.status -eq "success") {
                Write-Host "SharePoint objects found: $($result.objects.Count)" -ForegroundColor Cyan
                if ($result.objects.Count -gt 0) {
                    Write-Host "First object preview:" -ForegroundColor Gray
                    $result.objects[0] | ConvertTo-Json -Depth 2
                }
            } else {
                Write-Host "SharePoint query failed: $($result.error)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "Unexpected SharePoint response format" -ForegroundColor Yellow
            $sharepointResult.Data | ConvertTo-Json -Depth 4
        }
    } else {
        Write-Host "No data returned from SharePoint query." -ForegroundColor Yellow
    }
} else {
    Write-Host "Skipping SharePoint query due to missing access token." -ForegroundColor Red
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "- Auth MCP server not running on port 8001" -ForegroundColor Yellow
    Write-Host "- get_access_token_only tool not available on Auth server" -ForegroundColor Yellow
    Write-Host "- Authentication failed (user not logged in)" -ForegroundColor Yellow
    Write-Host "- Network connectivity issues" -ForegroundColor Yellow
}
# Final message

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Testing complete!" -ForegroundColor Cyan