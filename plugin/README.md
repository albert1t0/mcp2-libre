# LibreOffice MCP Extension

## 🎯 Overview

The LibreOffice MCP Extension integrates Model Context Protocol (MCP) server functionality directly into LibreOffice, enabling AI assistants to interact with LibreOffice documents in real-time through direct UNO API access.

## 🚀 Key Features

### **Real-time Document Manipulation**
- Create documents directly in LibreOffice (Writer, Calc, Impress, Draw)
- Insert and format text in active documents
- Live document editing without file I/O overhead
- Multi-document support for all open documents

### **Advanced Document Operations**
- Save and export documents to various formats (PDF, DOCX, ODT, etc.)
- Get comprehensive document information and statistics
- Real-time text content extraction
- Format text with fonts, styles, and attributes

### **AI Assistant Integration**
- Local REST API server running on `localhost:8765`
- JSON endpoints for listing and executing the extension's document tools
- Server status and health checks
- This API is not an MCP protocol transport; MCP clients cannot connect to it directly without a compatible bridge

### **Native LibreOffice Integration**
- Appears in LibreOffice Tools menu
- Auto-starts with LibreOffice
- Native status dialog showing server state, extension state, HTTP listener thread, endpoint, and health-check URL
- Installable `.oxt` extension package

## 📋 Installation

### **Method 1: Extension Manager (Recommended)**
1. Download `libreoffice-mcp-extension.oxt`
2. Open LibreOffice
3. Go to **Tools > Extension Manager**
4. Click **Add** and select the .oxt file
5. Restart LibreOffice

### **Method 2: Command Line**
```bash
unopkg add libreoffice-mcp-extension.oxt
```

### **Method 3: Build from Source**
```bash
cd plugin/
./build.sh
unopkg add ../build/libreoffice-mcp-extension.oxt
```

Or run the repository helper to build and install the extension:
```bash
./install.sh install
```
Restart LibreOffice after installation. The extension starts its server when LibreOffice loads it.

## 🔧 Usage

### **Manual Control**
After installation, access MCP server controls via:
- **Tools > MCP Server** (menu)
- Use the toolbar action to start the server

Available commands:
- **Start MCP Server**: Begins the HTTP API server
- **Stop MCP Server**: Stops the server
- **Restart MCP Server**: Restarts the server
- **Show Server Status**: Opens a native dialog with the server and HTTP listener state, endpoint, and health-check URL

### **HTTP API Endpoints**

The extension starts an HTTP server on `http://localhost:8765` with the following endpoints:
This is a local REST API for the extension's tools, not a standards-compliant MCP
HTTP transport. Requests are unauthenticated; keep the listener on a trusted local
machine and do not expose the port to an untrusted network. The API also allows
cross-origin requests (`Access-Control-Allow-Origin: *`).

#### **GET Endpoints**
```bash
# Server information
curl http://localhost:8765/

# List available tools
curl http://localhost:8765/tools

# Health check
curl http://localhost:8765/health
```

#### **POST Endpoints**
```bash
# Execute a specific tool
curl -X POST http://localhost:8765/tools/create_document_live \
  -H "Content-Type: application/json" \
  -d '{"doc_type": "writer"}'

# Execute tool via generic endpoint
curl -X POST http://localhost:8765/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "insert_text_live",
    "parameters": {
      "text": "Hello from AI assistant!"
    }
  }'
```

## 🛠️ Available Document Tools

### **Document Creation**
- `create_document_live`: Create new Writer, Calc, Impress, or Draw documents
- Parameters: `doc_type` (writer|calc|impress|draw)

### **Text Manipulation**
- `insert_text_live`: Insert text at cursor or specific position
- `format_text_live`: Apply formatting to selected text
- `get_text_content_live`: Extract text content from document
- `search_document_elements_live`: Search open documents and inspect matching text with location and formatting

### **Document Information**
- `get_document_info_live`: Get comprehensive document details
- `list_open_documents`: List all currently open documents

### **File Operations**
- `save_document_live`: Save active document
- `export_document_live`: Export to PDF, DOCX, ODT, TXT, etc.

## 🔗 AI Assistant Configuration
The extension API can be called by an HTTP client or by a compatible MCP-to-REST
bridge. It cannot be configured as a direct MCP server in Claude Desktop or another
MCP client. For native MCP client integration, use the standalone stdio server
described in the repository's main `README.md`.
```

## 🎮 Example Usage

### **Create and Edit Document**
```bash
# Create a new Writer document
curl -X POST http://localhost:8765/tools/create_document_live \
  -H "Content-Type: application/json" \
  -d '{"doc_type": "writer"}'

# Insert text
curl -X POST http://localhost:8765/tools/insert_text_live \
  -H "Content-Type: application/json" \
  -d '{"text": "This is AI-generated content!"}'

# Apply formatting to selected text
curl -X POST http://localhost:8765/tools/format_text_live \
  -H "Content-Type: application/json" \
  -d '{
    "bold": true,
    "font_size": 14,
    "font_name": "Arial"
  }'

# Save document
curl -X POST http://localhost:8765/tools/save_document_live \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/home/user/Documents/ai-document.odt"}'

# Export to PDF
curl -X POST http://localhost:8765/tools/export_document_live \
  -H "Content-Type: application/json" \
  -d '{
    "export_format": "pdf",
    "file_path": "/home/user/Documents/ai-document.pdf"
  }'
```

### **Document Analysis**
```bash
# Get document information
curl http://localhost:8765/tools/get_document_info_live

# Extract text content
curl http://localhost:8765/tools/get_text_content_live

# List all open documents
curl http://localhost:8765/tools/list_open_documents
```
### **Read-only Live Search and Inspection**

Open the document in LibreOffice before searching. The tool searches the active
document by default, or a specific open document when `document_identifier` is
set to its exact title or URL. Call `list_open_documents` first if you need to
find a document's URL. It performs a case-insensitive substring search and
never opens, edits, or saves documents.

```bash
# Search the active document
curl -X POST http://localhost:8765/tools/search_document_elements_live \
  -H "Content-Type: application/json" \
  -d '{"query":"budget"}'

# Search a particular document that is already open
curl -X POST http://localhost:8765/tools/search_document_elements_live \
  -H "Content-Type: application/json" \
  -d '{"query":"budget","document_identifier":"file:///home/user/report.ods","max_results":50}'
```

`max_results` defaults to 100 and accepts values from 1 to 500. A result contains
the document type, match count, `truncated` status, and a `matches` list:

- **Writer**: matching paragraph or table-cell text, paragraph location, style,
  outline level/alignment, and character-run font, size, bold, and italic data.
- **Calc**: displayed cell value, formula when applicable, sheet and cell address,
  cell style, number format, and available font/alignment properties. Scanning is
  capped at 100,000 cells per request; `cells_scanned` and `truncated` report
  whether the cap was reached.
- **Impress and Draw**: text-bearing shape, page/slide, shape name/type, and
  available text and shape formatting.

If more matches exist than requested, `truncated` is true. Unsupported document
types, closed targets, and ambiguous titles return an error. For MCP clients, use
the project's `libreoffice-live` Warp bridge; the extension endpoint itself is a
local REST API, not an MCP protocol transport. Refresh the bridge after installing
or updating the extension.

## 🔄 Comparison with External MCP Server
| Capability | Standalone server | Extension |
|------------|------------------|-----------|
| **Connection** | MCP over stdio | Local REST API |
| **Document access** | LibreOffice command-line/file operations | Direct UNO access to open documents |
| **LibreOffice UI** | No built-in controls | Tools menu, toolbar action, and status dialog |
| **Best suited for** | MCP clients and file-based operations | Editing documents currently open in LibreOffice |

## 🛠️ Technical Architecture

```
HTTP client or compatible MCP-to-REST bridge
     ↓ (REST API calls)
LibreOffice Plugin Extension
     ↓ (UNO API - direct access)
LibreOffice Internal Components
Documents & Data Structures
```

### **Core Components**
- **UNO Bridge**: Direct LibreOffice API integration
- **Document tools**: Embedded operations for open LibreOffice documents
- **AI Interface**: HTTP API for external connections
- **Extension Registration**: LibreOffice lifecycle management

## 🐛 Troubleshooting

### **Extension Not Loading**
1. Check LibreOffice version (requires 7.0+)
2. Verify Python environment
3. Check Extension Manager for conflicts
4. Review LibreOffice error logs

### **HTTP Server Not Starting**
1. Verify port 8765 is available
2. Check firewall settings
3. Review extension logs
4. Try restarting LibreOffice

If testing from the repository, `./install.sh test` checks that the extension is
installed, invokes `start_server.py` to activate it in LibreOffice if needed, then
runs the HTTP test client. Save open documents before restarting LibreOffice.

### **Tool Execution Errors**
1. Ensure document is open for document-specific tools
2. Check parameter formats in API calls
3. Verify LibreOffice permissions
4. Check UNO API compatibility

### **Getting Help**
- Check LibreOffice extension logs
- Use `curl http://localhost:8765/health` for server status
- Access **Tools > MCP Server > Show Server Status**
- Visit project GitHub repository for issues

## 📝 Development

### **Building from Source**
```bash
git clone <repository-url>
cd mcp-libre/plugin
./build.sh
```

### **Installing Development Version**
```bash
unopkg remove org.mcp.libreoffice.extension  # Remove old version
unopkg add ../build/libreoffice-mcp-extension.oxt
```

### **Debugging**
- Enable LibreOffice Basic IDE debugging
- Check Python console output
- Monitor HTTP server logs
- Use UNO reflection tools

## 📜 License

This extension is released under the MIT License. See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please check the main project repository for contribution guidelines.

---

**Happy AI-powered document editing with LibreOffice! 🎉**
