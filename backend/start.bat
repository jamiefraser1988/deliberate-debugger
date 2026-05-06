(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& c:\Repos\deliberate-debugger\backend\.venv\Scripts\Activate.ps1)
uvicorn main:app --reload      