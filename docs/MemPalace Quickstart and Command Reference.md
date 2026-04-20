# MemPalace Quickstart and Command Reference

MemPalace is a local "Second Brain" for your AI, organized into **Wings** (Projects), **Halls** (Categories), and **Rooms** (Specific Topics).

## 1. Initialization

Run this once to set up your Palace.

```
mempalace init ~/my-palace
```

## 2. Mining Data (Indexing)

"Mining" turns your local files or chat histories into searchable memories.

|   |   |
|---|---|
|**Command**|**Description**|
|`mempalace mine .`|Indexes the current directory (Code mode).|
|`mempalace mine ./docs --mode text`|Indexes markdown/txt files as documentation.|
|`mempalace mine ~/Downloads/chats --mode convos`|Indexes JSON/Markdown chat exports.|

## 3. Searching

Query your memories directly from the terminal.

|   |   |
|---|---|
|**Command**|**Description**|
|`mempalace search "search term"`|Search across all Wings and Rooms.|
|`mempalace search "" --list`|List all existing Wings and Rooms.|
|`mempalace search "motor specs" --wing LACE`|Limit search to a specific project.|

## 4. Manual Memory Management

If you want to manually "file" a specific thought.

|   |   |
|---|---|
|**Command**|**Description**|
|`mempalace remember "Text to remember" --room "Logic"`|Quick-save a snippet.|
|`mempalace forget --room "Obsolete"`|Remove a specific Room from memory.|

## 5. Configuration Files

- **Identity:** `~/.mempalace/identity.txt` (Define who you are and your global preferences for the AI).
    
- **Exclusions:** Create a `.mempalignore` file in your project (works like `.gitignore`) to prevent indexing of `node_modules`, `build` folders, etc.
    

## 6. Pro Workflow

1. **Index your project:** `mempalace mine .`
    
2. **Connect to Roo Code:** Use the MCP server (see setup guide).
    
3. **Automate:** Let Roo Code's Custom Instructions handle the "saving" so your Palace grows as you work.