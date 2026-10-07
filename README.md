# LibreOffice MCP Server

A comprehensive Model Context Protocol (MCP) server that provides tools and resources for interacting with LibreOffice documents. This server enables AI assistants and other MCP clients to create, read, convert, and manipulate LibreOffice documents programmatically.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![LibreOffice](https://img.shields.io/badge/LibreOffice-24.2+-green.svg)](https://www.libreoffice.org/)
[![MCP Python SDK](https://img.shields.io/badge/MCP%20Python%20SDK-2.x-orange.svg)](https://github.com/modelcontextprotocol/python-sdk)

## 📂 Repository Structure

This repository is organized into logical directories:

- **`src/`** - Core MCP server implementation
- **`tests/`** - Test suite and validation scripts  
- **`examples/`** - Demo scripts and usage examples
- **`config/`** - Configuration templates for integrations
- **`scripts/`** - Utility scripts for setup and management
- **`docs/`** - Comprehensive documentation

For detailed information, see [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md).

## 🚀 Features

### LibreOffice Extension (Plugin) - NEW! 🎉
- **Native Integration**: Embedded document tools with direct UNO API access
- **Real-time Editing**: Live document manipulation with instant visual feedback
- **Multi-document**: Work with all open LibreOffice documents
- **Live Search and Editing**: Search open documents, enumerate Writer headings, and preview guarded batch text replacements
- **Auto-start**: Automatically available when LibreOffice starts
- **HTTP API**: Local REST API at `http://localhost:8765`
- **Status Dialog**: Check server, extension, listener, and health endpoint status in LibreOffice

### Document Operations
- **Create Documents**: New Writer, Calc, Impress, and Draw documents
- **Read Content**: Extract text from any LibreOffice document
- **Convert Formats**: Convert between 50+ formats (PDF, DOCX, HTML, etc.)
- **Edit Documents**: Insert, append, or replace text in Writer documents
- **Document Info**: Get detailed metadata about documents

### Spreadsheet Operations
- **Read Spreadsheets**: Extract data from Calc spreadsheets and Excel files
- **Structured Data**: Get data as 2D arrays with row/column information

### Advanced Tools
- **Document Search**: Find documents containing specific text
- **Batch Convert**: Convert multiple documents simultaneously
- **Merge Documents**: Combine multiple documents into one
- **Document Analysis**: Get detailed statistics (word count, sentences, etc.)

### Live Viewing & Real-time Editing
- **GUI Integration**: Open documents in LibreOffice for live viewing
- **Real-time Updates**: See changes as AI assistants modify documents
- **Change Monitoring**: Watch documents for modifications in real-time
- **Interactive Sessions**: Create live editing sessions with automatic refresh

### MCP Resources
- **Document Discovery**: List all LibreOffice documents (`documents://`)
- **Content Access**: Access specific document content (`document://{path}`)

## 📋 Requirements

- **LibreOffice**: 24.2+ (must be accessible via command line)
- **Python**: 3.12+
- **UV Package Manager**: For dependency management

For detailed installation instructions for all platforms, run:
```bash
./mcp-helper.sh requirements
```

## 🛠 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/patrup/mcp-libre/
   cd mcp-libre
   ```

2. **Check prerequisites**:
   ```bash
   ./mcp-helper.sh requirements  # Show detailed requirements
   ./mcp-helper.sh check         # Verify your system
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Make helper script executable**:
   ```bash
   chmod +x mcp-helper.sh
   ```

## 🎯 Quick Start

### Test the Server
```bash
# Run functionality tests
./mcp-helper.sh test

# Run interactive demo
./mcp-helper.sh demo
```

### Start MCP Server
```bash
# Standard MCP mode (stdio, using MCP Python SDK 2.x)
python src/main.py

# Or using UV
uv run python src/main.py

# Show help and options
python src/main.py --help

# Run tests
python src/main.py --test
```

### Integration with Super Assistant
```bash
# Start the MCP proxy
./mcp-helper.sh proxy

# Then configure Super Assistant extension:
# Server URL: http://localhost:3006
```

## 🔧 Available Tools

| Tool | Description |
|------|-------------|
| `create_document` | Create new LibreOffice documents |
| `read_document_text` | Extract text from documents |
| `convert_document` | Convert between formats |
| `get_document_info` | Get document metadata |
| `read_spreadsheet_data` | Read spreadsheet data |
| `insert_text_at_position` | Edit document text |
| `search_documents` | Search documents by content |
| `batch_convert_documents` | Batch format conversion |
| `merge_text_documents` | Merge multiple documents |
| `get_document_statistics` | Document analysis |
| `open_document_in_libreoffice` | Open document in GUI for live viewing |
| `create_live_editing_session` | Start live editing with real-time preview |
| `watch_document_changes` | Monitor document changes in real-time |
| `refresh_document_in_libreoffice` | Force document refresh in GUI |

## 📚 Documentation

- **[Prerequisites](docs/PREREQUISITES.md)**: Quick reference for system requirements
- **[Plugin Migration Guide](docs/PLUGIN_MIGRATION_GUIDE.md)**: Migrate from external server to plugin
- **[Examples](docs/EXAMPLES.md)**: Code examples and usage patterns
- **[Live Viewing Guide](docs/LIVE_VIEWING_GUIDE.md)**: See changes live in LibreOffice GUI
- **[Super Assistant Setup](docs/SUPER_ASSISTANT_SETUP.md)**: Chrome extension integration
- **[ChatGPT Browser Guide](docs/CHATGPT_BROWSER_GUIDE.md)**: Using with ChatGPT and alternatives
- **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Common issues and solutions
- **[Quick Start](docs/QUICK_START.md)**: Quick reference guide
- **[Complete Solution](docs/COMPLETE_SOLUTION.md)**: Comprehensive overview

## 🔗 Integration Options

### 1. LibreOffice Extension (NEW - Recommended!) 🎉

**Use the extension to work directly with documents open in LibreOffice:**

```bash
# Build and install the LibreOffice extension
cd plugin/
./install.sh install

# Test the extension
./install.sh test
```

**Benefits of the Extension:**
- **Direct UNO access**: Work with open documents without file conversion or subprocesses
- **Real-time Editing**: Live document manipulation in open LibreOffice windows
- **Native Integration**: Appears in LibreOffice Tools menu
- **Multi-document Support**: Work with all open documents simultaneously
- **Auto-start**: Automatically starts with LibreOffice
- **Status Dialog**: View server and HTTP listener status in LibreOffice

**Usage:**
- The extension provides a local REST API on `http://localhost:8765`
- Call it with an HTTP client or connect through a compatible MCP-to-REST bridge
- Access controls via **Tools > MCP Server** in LibreOffice
- Real-time document editing with instant visual feedback

For detailed plugin information, see [`plugin/README.md`](plugin/README.md).

#### Read-only live search

The live bridge exposes `search_document_elements_live` for text inspection in a
document that is already open in LibreOffice. Open the document first, then call
the tool from Warp. Omit `document_identifier` to search the active document; to
target another open document, pass its exact title or URL (use
`list_open_documents` to see available documents). This tool does not open,
modify, or save files.

```json
{
  "query": "budget",
  "max_results": 100
}
```

The search is a case-insensitive substring match. Results include each matching
element's text, location, type, and relevant formatting: paragraph/style and
character runs in Writer; sheet/cell address, formula, style, and number format
in Calc; page/slide and shape metadata in Impress and Draw. `max_results`
defaults to 100 (maximum 500); `truncated` indicates that more matches exist or
Calc's scan limit was reached. The live tool is provided by the extension-backed
Warp bridge, not by the standalone file-search tool `search_documents`.

#### Live heading search and guarded replacement

Use `search_document_headings_live` to enumerate Writer headings without first
knowing their text. It can optionally filter by a case-insensitive `query` and
returns body paragraph locations, styles, and outline levels. Use those values
with `replace_document_elements_live` to prepare exact substring replacements.
Each edit must include the location, exact full paragraph text and style, the
substring to replace (exactly once), and replacement text. The entire batch is
checked before any text changes; stale text, styles, duplicate paragraph targets,
or ambiguous substrings reject the batch.

Replacement defaults to `dry_run: true`, which returns a preview without changing
the document. Set `dry_run` to `false` to apply the verified changes. These tools
operate only on a Writer document that is already open, only target body
paragraphs, and never save the document automatically.

```json
{
  "edits": [
    {
      "location": { "section": "body", "paragraph": 3 },
      "expected_text": "🎯 Agenda sugerida",
      "expected_style": "Heading 1",
      "search_text": "🎯 ",
      "replacement_text": ""
    }
  ],
  "dry_run": true
}
```

#### Inspecting and updating paragraph styles

Use `get_writer_paragraph_styles_live` to discover the exact paragraph style
names and inspect their supported attributes and inheritance state. Style
names vary by document and locale, so use the exact name returned by inspection.

`update_writer_paragraph_style_live` updates one property on a shared paragraph
style. It requires `property_name` and `value`, plus exactly one target:
`style_name`, or a body `location` accompanied by exact `expected_text` and
`expected_style` guards. An optional `expected_current_value` prevents applying
a stale update. The operation previews by default; set `dry_run` to `false` to
change the in-memory document. Its result reports affected descendant styles.

The `property_name` allowlist and value types are:

- `CharFontName`: non-empty string.
- `CharHeight`: number from 0.1 to 1000; `CharWeight`: number from 0 to 150.
- `CharPosture`: one of `NONE`, `ITALIC`, or `OBLIQUE`.
- `CharColor`: integer from -1 to 16,777,215; `CharUnderline`: integer from 0
  to 18; `ParaAdjust`: integer from 0 to 5.
- `ParaFirstLineIndent`: integer from -1,000,000 to 1,000,000.
- `ParaLeftMargin`, `ParaRightMargin`, `ParaTopMargin`, and `ParaBottomMargin`:
  integers from 0 to 1,000,000, in UNO units.

`apply_writer_paragraph_formatting_live` is separate from shared-style updates.
It requires `targets`, `property_name`, and `value`. Each target identifies one
body paragraph by location and includes its exact `expected_text` and
`expected_style`; duplicate paragraph locations are rejected. The whole batch
is preflighted before any changes. Character properties are applied only to
portions inheriting the value, preserving directly formatted portions. It also
previews by default and accepts `dry_run: false` to apply in memory. Set the
optional `override_direct` flag to `true` to replace direct values of the
selected property too; other formatting properties and non-target paragraphs
remain unchanged. By default, `override_direct` is `false`.

Both operations accept an optional `document_identifier` for an already-open
Writer document and never save automatically. `targets` accepts 1–500 entries.

```json
{
  "query": "normal",
  "max_results": 100
}
```

Use an exact style name returned by inspection for the update:

```json
{
  "property_name": "CharFontName",
  "value": "Calibri",
  "style_name": "normal",
  "expected_current_value": "Liberation Serif",
  "dry_run": true
}
```

To update paragraph formatting without changing the shared style, pass guarded
paragraph targets instead:

```json
{
  "targets": [
    {
      "location": { "section": "body", "paragraph": 3 },
      "expected_text": "The exact current paragraph text",
      "expected_style": "Body Text"
    }
  ],
  "property_name": "CharFontName",
  "value": "Calibri",
  "override_direct": true,
  "dry_run": true
}
```
### 2. Claude Desktop

Generate configuration automatically:
```bash
./generate-config.sh claude
# Creates ~/.config/claude/claude_desktop_config.json
```

Then restart Claude Desktop and start using LibreOffice commands:
- *"Create a new Writer document and save it as project-report.odt"*
- *"Convert my document to PDF format"*

### 3. Super Assistant Chrome Extension

Generate configuration and start proxy:
```bash
./generate-config.sh mcp
npx @srbhptl39/mcp-superassistant-proxy@latest --config ~/Documents/mcp/mcp.config.json
# Server URL: http://localhost:3006
```

### MCP Client Integration

The standalone server communicates with MCP clients over stdio. Generate a client
configuration with `./generate-config.sh claude`, or configure the client to launch
`python src/main.py` from the project directory.

The LibreOffice extension is a separate integration: it exposes a local REST API,
not the MCP stdio/HTTP protocol transport. A client that speaks MCP cannot connect
to the extension endpoint directly without a compatible bridge.

## 🎨 Usage Examples

### Natural Language (via Super Assistant)
- *"Create a new Writer document with a project report"*
- *"Convert my ODT file to PDF format"*
- *"Search for documents containing 'budget' in my Documents folder"*
- *"Get statistics for my essay - how many words?"*

### Programmatic Usage
Use the standalone MCP server from an MCP client to invoke tools such as
`create_document`, `read_document_text`, and `convert_document`. The server is
launched in stdio mode with `uv run python src/main.py`.

## 📁 Supported File Formats

### Input (Reading)
- **LibreOffice**: `.odt`, `.ods`, `.odp`, `.odg`
- **Microsoft Office**: `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
- **Text**: `.txt`, `.rtf`

### Output (Conversion)
- **PDF**: `.pdf`
- **Microsoft Office**: `.docx`, `.xlsx`, `.pptx`
- **Web**: `.html`, `.htm`
- **Text**: `.txt`
- **LibreOffice**: `.odt`, `.ods`, `.odp`, `.odg`
- **Many others**: 50+ formats supported by LibreOffice

## 🧪 Testing

### LibreOffice Extension Testing
```bash
# Install and test the plugin
cd plugin/
./install.sh install    # Build and install extension
./install.sh test       # Test functionality
./install.sh status     # Check status
./install.sh interactive # Interactive testing mode
```

### Real LibreOffice UNO Integration Test

Run the UNO smoke test with a Python interpreter that can import LibreOffice's
`uno` module and with LibreOffice available on `PATH`:

```bash
/usr/bin/python3 tests/integration_live_tools_uno.py
```

If LibreOffice is not on `PATH`, set `LIBREOFFICE_BIN` to its executable path.
The script starts a separate headless LibreOffice process with a temporary user
profile, creates a temporary unsaved Writer document, verifies heading search,
dry-run, emoji substring replacement, and stale-edit rejection, then disposes
the document without saving. It never attaches to or restarts an existing
LibreOffice session. This directly exercises the source UNO bridge; the REST
tool registration and stdio forwarding are covered by `pytest -q`.

### External Server Testing
```bash
# Show system requirements and installation guides
./mcp-helper.sh requirements

# Check dependencies and verify setup
./mcp-helper.sh check

# Run built-in functionality tests
./mcp-helper.sh test

# Interactive demo of all capabilities
./mcp-helper.sh demo

# Test specific functionality directly
uv run python libremcp.py --test
```

## 🔧 Configuration

### MCP Configuration for Integrations

Generate personalized configuration files for Claude Desktop and/or Super Assistant:

```bash
# Generate both Claude Desktop and Super Assistant configs
./generate-config.sh

# Generate only Claude Desktop config
./generate-config.sh claude

# Generate only Super Assistant config  
./generate-config.sh mcp

# Generate Super Assistant config in custom location
./generate-config.sh mcp /path/to/custom/directory
```

This automatically creates configurations with your actual project paths:
- **Claude Desktop**: `~/.config/claude/claude_desktop_config.json`
- **Super Assistant**: `~/Documents/mcp/mcp.config.json` (or custom location)

### Environment Variables
```bash
export PYTHONPATH="/path/to/mcp-libre"
export LIBREOFFICE_PATH="/usr/bin/libreoffice"  # Optional
```

### Custom Search Paths
Edit `libremcp.py` to modify document discovery locations:
```python
search_paths = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path("/custom/path"),
    Path.cwd()
]
```

## 🛡 Security

- **Local Execution**: All operations run locally
- **File Permissions**: Limited to user's file access
- **Extension API**: Binds to `localhost:8765`; it has no authentication, so do not expose it beyond a trusted local environment
- **Temporary Files**: Automatically cleaned up

## 🚨 Troubleshooting

### LibreOffice Issues
```bash
# Check LibreOffice installation
libreoffice --version
libreoffice --headless --help

# Test conversion manually
libreoffice --headless --convert-to pdf document.odt
```

### Java Warnings
- Java warnings are usually non-fatal
- Core functionality works without Java
- Install Java for full LibreOffice features

### Permission Errors
- Check file and directory permissions
- Ensure LibreOffice can access document paths
- Verify write permissions for output directories

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The MIT License is a permissive license that allows:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use

For other license options, see [LICENSE_OPTIONS.md](LICENSE_OPTIONS.md).

## 🔗 Links

- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **LibreOffice**: https://www.libreoffice.org/
- **FastMCP Framework**: https://github.com/modelcontextprotocol/python-sdk

## 📞 Support

- **Issues**: Use GitHub issues for bug reports
- **Documentation**: See the `docs/` folder for detailed guides
- **Examples**: Check `EXAMPLES.md` for usage patterns

---

*LibreOffice MCP Server v0.1.0 - Bridging AI and Document Processing*
