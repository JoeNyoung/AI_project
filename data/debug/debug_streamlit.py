{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "🧩 Vector Search (debug_vector)",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/debug/debug_vector.py",
      "args": ["\"panamax 운임\"", "--events", "운임 급등"],
      "console": "integratedTerminal"
    },
    {
      "name": "🧩 RAG Pipeline (debug_rag)",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/debug/debug_rag.py",
      "args": ["\"현재 capesize 시황?\"", "--role", "리더"],
      "console": "integratedTerminal"
    },
    {
      "name": "🖥 Streamlit UI",
      "type": "python",
      "request": "launch",
      "module": "streamlit",
      "args": ["run", "${workspaceFolder}/streamlit_app.py", "--server.port", "8501"],
      "console": "integratedTerminal"
    }
  ]
}