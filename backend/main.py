from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List

# Internal modules
from backend.services.image_preprocessing import preprocess_image
from backend.services.layout_detection import detect_table_layout
from backend.services.paddleocr_service import extract_bill_data_with_paddle
from backend.agents.confidence_agent import ConfidenceAgent
from backend.agents.error_agent import ErrorDetectionAgent
from backend.agents.workflow_agent import WorkflowDecisionAgent
from backend.agents.learning_agent import LearningAgent
from backend.schemas.bill_schema import BillAnalysisResponse, ItemSchema

# Initialize Agents
confidence_agent = ConfidenceAgent()
error_agent = ErrorDetectionAgent()
workflow_agent = WorkflowDecisionAgent()
learning_agent = LearningAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load resources if needed
    print("Agentic Bill Management System Backend Started")
    yield
    # Shutdown
    print("Shutting down")

app = FastAPI(title="Agentic Bill Management System", lifespan=lifespan)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for hackathon/demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/bills/analyze", response_model=BillAnalysisResponse)
async def analyze_bill(file: UploadFile = File(...)):
    """
    Analyzes an uploaded bill image using the Agentic AI Pipeline.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # 1. Read Image
        contents = await file.read()
        
        # 2. Use PaddleOCR for superior bill analysis (free & more accurate)
        items_data, total_price = extract_bill_data_with_paddle(contents)
        
        # Convert internal dicts to Schema
        items_schema = []
        for item in items_data:
            items_schema.append(ItemSchema(
                name=item['name'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                line_total=item['line_total'],
                confidence=item['confidence']
            ))
            
        # 3. Agentic Analysis
        
        # Confidence Agent
        confidence_scores = confidence_agent.analyze(items_schema)
        overall_confidence = confidence_scores.get("overall", 0.0)
        
        # Error Detection Agent
        errors = error_agent.detect_errors(items_schema, total_price)
        
        # Workflow Decision Agent
        decision = workflow_agent.decide(overall_confidence)
        
        return BillAnalysisResponse(
            items=items_schema,
            total=total_price,
            confidence_scores=confidence_scores,
            errors=errors,
            workflow_decision=decision
        )

        
    except Exception as e:
        # Demo-safe error handling
        print(f"Error processing bill: {e}")
        # Return a partial/empty response or 500 depending on strategy. 
        # For hackathon wows, maybe return empty structure with error message in 'errors'
        # but 500 is more standard for crashes.
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
