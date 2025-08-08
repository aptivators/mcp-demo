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

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Testing complete!" -ForegroundColor Cyan