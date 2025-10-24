# travel-multi-agent-workshop

## Setting up local development

When you deploy this solution, it automatically configures `.env` files with the required Azure endpoints and authentication tokens for both the main application and MCP server.

To run the solution locally after deployment:

### Terminal 1 - Start the MCP Server:

Open new terminal, navigate to the `mcp_server`, then run:

**Linux/macOS:**
```bash
source venv/bin/activate
PYTHONPATH=../python python mcp_http_server.py
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
$env:PYTHONPATH="../python"; python mcp_http_server.py
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
set PYTHONPATH=../python && python mcp_http_server.py
```

### Terminal 2 - Start the Travel API:

Open a new terminal, navigate to `python` folder, then run:

**Linux/macOS:**
```bash
source venv/bin/activate
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 3 - Start the Frontend:

Open a new terminal, navigate to the `frontend` folder, then run:

**All platforms:**
```bash
npm install
npm start
```

Access the applications:

- Travel API: [http://localhost:8000/docs](http://localhost:8000/docs)
- MCP Server: [http://localhost:8080/docs](http://localhost:8080/docs)
- Frontend: [http://localhost:4200](http://localhost:4200/)