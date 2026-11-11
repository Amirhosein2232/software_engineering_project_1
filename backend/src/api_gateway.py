import sys
from pathlib import Path

# Automatically add the 'backend/' folder to Python's search path
# Path(__file__) is backend/src/api_gateway.py -> .parents is backend/
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import router modules (We will stub these blueprints in Step 2)
from modules.auth.routes import router as auth_router
from modules.student.routes import router as student_router
#from modules.operator.routes import router as operator_router
#from modules.admin.routes import router as admin_router

# Initialize the central API Hub
app = FastAPI(
    title="Ticketing System API Gateway",
    description="Central router mapping domain submodules dynamically",
    version="1.0.0"
)

# Global Cross-Origin Resource Sharing (CORS) Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust this to your Frontend origin for safety
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dynamic Submodule Routing Mounts
app.include_router(auth_router, prefix="/api/auth", tags=["1. Authentication & Security"])
app.include_router(student_router, prefix="/api/student", tags=["2. Student Operations"])
#app.include_router(operator_router, prefix="/api/operator", tags=["3. Operator Helpdesk"])
#app.include_router(admin_router, prefix="/api/admin", tags=["4. Global Administration"])

if __name__ == "__main__":

    # Tell Uvicorn exactly where to look for 'api_gateway'
    # Spin up development engine
    uvicorn.run(
        "src.api_gateway:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )