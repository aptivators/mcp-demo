
# Gemini MCP Frontend

This frontend provides a modern interface for interacting with both your Medicare MCP server and Azure MCP server, powered by Gemini 2.0 Flash. It is designed for real-time, multi-server integration, secure configuration, and a seamless conversational experience.

---

## Installation

To get started with the Gemini MCP Frontend:

1. **Clone the repository** (if you haven't already):

   ```sh
   git clone <your-repo-url>
   cd <repo-folder>/frontend
   ```

2. **Install dependencies:**

   ```sh
   npm install
   ```

3. **Start the development server:**

   ```sh
   npm start
   ```

4. **Configure your environment:**
   - Enter your Gemini API key and MCP server URLs in the app settings panel.
   - Make sure your MCP servers are running and accessible.

---

## Features

### 🎯 Core Functionality

- **Dual Server Integration:** Connects to both Medicare and Azure MCP servers
- **Gemini 2.0 Flash Integration:** Uses your API key to power the conversational agent
- **Real-time Server Status:** Displays connection status for both servers
- **Flexible Server Selection:** Choose Medicare only, Azure only, or both servers

### 🔧 Configuration Management

- **API Key Management:** Secure input for your Gemini API key
- **Server URLs:** Configurable endpoints for both MCP servers
- **Azure Authentication:** Ready for Azure Client ID and Tenant ID integration
- **Connection Testing:** Built-in health checks for server connectivity

### 💬 Chat Interface

- **Modern UI:** Glass-morphism design with dark theme
- **Real-time Messaging:** Smooth conversation flow with loading states
- **Error Handling:** Graceful error display and recovery
- **Quick Actions:** Pre-built prompts for common queries

### 🛠 MCP Integration

- **Tool Discovery:** Automatically fetches available tools from both servers
- **Resource Access:** Retrieves available resources from MCP servers
- **Context Awareness:** Provides Gemini with full context of available capabilities
- **Server Attribution:** Tracks which server provides which tools/resources

---

## Setup Instructions

1. **Start your MCP servers** (ensure they're running on the configured ports)
2. **Get your Gemini API key** from Google AI Studio
3. **Configure the frontend:**
    - Enter your Gemini API key
    - Set correct server URLs (default: `localhost:3000` for Medicare, `localhost:3001` for Azure)
    - Test connections to ensure servers are responding

---

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

---

## Azure Integration Notes

- The frontend is designed to work with Azure SDK authentication.
- Ensure your Azure MCP server exposes the standard MCP endpoints:
  - `GET /health` - Health check
  - `GET /tools` - Available tools
  - `GET /resources` - Available resources
  - `POST /call-tool` - Execute tools
- Handle Azure authentication in your server-side implementation using the Azure SDK
- Configure Azure credentials in the settings panel when needed

---

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

---

For more details, see the implementation notes in `client/README.md`, `notes.txt`, and the source code.
