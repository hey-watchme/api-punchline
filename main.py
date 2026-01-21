from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import json
import re
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Supabase client
from supabase_client import SupabaseClient

# Import LLM provider
from llm_providers import get_current_llm, CURRENT_PROVIDER, CURRENT_MODEL

app = FastAPI(
    title="PUNCHLINE API",
    description="POC API for extracting memorable punchlines from conversations",
    version="0.1.0"
)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy initialization of Supabase client
supabase_client = None


def get_supabase_client():
    """Lazy initialize and get Supabase client"""
    global supabase_client
    if supabase_client is None:
        try:
            supabase_client = SupabaseClient()
            print("Supabase client initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Supabase client: {e}")
            raise e
    return supabase_client


# Request/Response Models
class PunchlineExtractionRequest(BaseModel):
    """Request model for punchline extraction"""
    conversation_text: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class WatchMeExtractionRequest(BaseModel):
    """Request model for extracting punchlines from WatchMe data"""
    device_id: str
    local_date: str
    local_time: Optional[str] = None
    user_id: Optional[str] = None


class PunchlineResponse(BaseModel):
    """Individual punchline response"""
    rank: int
    text: str
    speaker: str
    context_before: str
    humor_score: int
    memorability_score: int
    category: str
    reasoning: str


class ExtractionResponse(BaseModel):
    """Full extraction response"""
    status: str
    request_id: str
    structured_conversation: Optional[Dict[str, Any]] = None
    punchlines: Optional[List[PunchlineResponse]] = None
    metadata: Dict[str, Any]


class HistoryRequest(BaseModel):
    """Request model for history endpoint"""
    user_id: str
    limit: Optional[int] = 10


def extract_json_from_response(raw_response: str) -> Dict[str, Any]:
    """Extract JSON from LLM response"""
    content = raw_response.strip()

    try:
        # Pattern 1: Response is already JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Pattern 2: ```json ... ``` format
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1).strip()
            return json.loads(json_content)

        # Pattern 3: Extract first {...} block
        json_block_match = re.search(r'({.*})', content, re.DOTALL)
        if json_block_match:
            json_content = json_block_match.group(1).strip()
            return json.loads(json_content)

        # No pattern matched
        raise ValueError("Failed to extract JSON data")

    except (json.JSONDecodeError, ValueError) as e:
        # Fallback on JSON parsing failure
        return {
            "processing_error": f"JSON parsing error: {str(e)}",
            "raw_response": raw_response,
            "extracted_content": content[:500] + "..." if len(content) > 500 else content
        }


async def structure_conversation(conversation_text: str) -> Dict[str, Any]:
    """
    Pipeline 1: Structure the conversation using LLM

    Args:
        conversation_text: Raw conversation text

    Returns:
        Structured conversation data
    """
    try:
        # Load prompt template
        with open('prompts/structure_conversation.txt', 'r') as f:
            prompt_template = f.read()

        # Format prompt with conversation text
        prompt = prompt_template.replace('{conversation_text}', conversation_text)

        # Call LLM
        llm = get_current_llm()
        raw_response = llm.generate(prompt)

        # Extract JSON from response
        structured_data = extract_json_from_response(raw_response)

        return structured_data

    except Exception as e:
        print(f"Error in structure_conversation: {str(e)}")
        raise e


async def extract_punchlines(structured_conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pipeline 2: Extract punchlines from structured conversation

    Args:
        structured_conversation: Structured conversation from Pipeline 1

    Returns:
        Extracted punchlines with scores
    """
    try:
        # Load prompt template
        with open('prompts/extract_punchlines.txt', 'r') as f:
            prompt_template = f.read()

        # Format prompt with structured conversation
        prompt = prompt_template.replace(
            '{structured_conversation}',
            json.dumps(structured_conversation, indent=2, ensure_ascii=False)
        )

        # Call LLM
        llm = get_current_llm()
        raw_response = llm.generate(prompt)

        # Extract JSON from response
        punchlines_data = extract_json_from_response(raw_response)

        return punchlines_data

    except Exception as e:
        print(f"Error in extract_punchlines: {str(e)}")
        raise e


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PUNCHLINE API",
        "version": "0.1.0",
        "status": "running",
        "llm_provider": CURRENT_PROVIDER,
        "llm_model": CURRENT_MODEL
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "llm_provider": CURRENT_PROVIDER,
        "llm_model": CURRENT_MODEL,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/extract-punchlines", response_model=ExtractionResponse)
async def extract_punchlines_endpoint(request: PunchlineExtractionRequest):
    """
    Main endpoint for extracting punchlines from conversation

    This endpoint:
    1. Structures the conversation
    2. Extracts punchlines
    3. Saves results to database
    4. Returns complete analysis
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        # Initialize Supabase if needed
        db = get_supabase_client()

        # Save initial request to database
        await db.save_punchline_request(
            request_id=request_id,
            conversation_text=request.conversation_text,
            user_id=request.user_id,
            context_data=request.context
        )

        # Pipeline 1: Structure conversation
        print(f"Starting Pipeline 1: Structure conversation for request {request_id}")
        structured_conversation = await structure_conversation(request.conversation_text)

        # Check for processing errors
        if "processing_error" in structured_conversation:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to structure conversation: {structured_conversation.get('processing_error')}"
            )

        # Save structured conversation to database
        await db.save_structured_conversation(
            request_id=request_id,
            structured_result=structured_conversation,
            speakers=structured_conversation.get('speakers', []),
            turn_count=structured_conversation.get('total_turns', 0),
            summary=structured_conversation.get('summary', '')
        )

        # Pipeline 2: Extract punchlines
        print(f"Starting Pipeline 2: Extract punchlines for request {request_id}")
        punchlines_result = await extract_punchlines(structured_conversation)

        # Check for processing errors
        if "processing_error" in punchlines_result:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract punchlines: {punchlines_result.get('processing_error')}"
            )

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Prepare metadata
        metadata = {
            "total_punchlines": len(punchlines_result.get('punchlines', [])),
            "processing_time_ms": processing_time_ms,
            "model_used": f"{CURRENT_PROVIDER}/{CURRENT_MODEL}",
            "conversation_length": len(request.conversation_text),
            "turn_count": structured_conversation.get('total_turns', 0)
        }

        # Save punchline results to database
        await db.save_punchline_results(
            request_id=request_id,
            punchlines=punchlines_result.get('punchlines', []),
            metadata=metadata,
            llm_model=f"{CURRENT_PROVIDER}/{CURRENT_MODEL}"
        )

        # Return complete response
        return ExtractionResponse(
            status="success",
            request_id=request_id,
            structured_conversation=structured_conversation,
            punchlines=punchlines_result.get('punchlines', []),
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in extract_punchlines_endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/extract/{request_id}", response_model=ExtractionResponse)
async def get_extraction_result(request_id: str):
    """
    Get extraction result by request ID

    Args:
        request_id: Unique request ID

    Returns:
        Complete extraction result
    """
    try:
        db = get_supabase_client()
        result = await db.get_request_by_id(request_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Request not found: {request_id}"
            )

        # Format response
        structured_conv = result.get('structured_conversation', {})
        punchline_results = result.get('punchline_results', {})

        return ExtractionResponse(
            status="success",
            request_id=request_id,
            structured_conversation=structured_conv.get('structured_result') if structured_conv else None,
            punchlines=punchline_results.get('punchlines') if punchline_results else None,
            metadata=punchline_results.get('metadata', {}) if punchline_results else {}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_extraction_result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/history")
async def get_user_history(user_id: str, limit: int = 10):
    """
    Get user's extraction history

    Args:
        user_id: User ID
        limit: Maximum number of results (default: 10)

    Returns:
        List of user's past requests
    """
    try:
        db = get_supabase_client()
        history = await db.get_user_history(user_id, limit)

        return {
            "user_id": user_id,
            "requests": history,
            "total_requests": len(history)
        }

    except Exception as e:
        print(f"Error in get_user_history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/extract-from-watchme", response_model=ExtractionResponse)
async def extract_from_watchme(request: WatchMeExtractionRequest):
    """
    Extract punchlines from WatchMe spot_features transcription data

    This endpoint:
    1. Fetches transcription from WatchMe spot_features table
    2. Uses existing pipeline to structure and extract punchlines
    3. Saves results to database

    Args:
        request: Contains device_id, local_date, and optional local_time

    Returns:
        Complete extraction response with punchlines
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        # Initialize Supabase if needed
        db = get_supabase_client()

        # Fetch transcription from WatchMe spot_features
        print(f"Fetching WatchMe transcription for device {request.device_id} on {request.local_date}")
        transcription = await db.get_watchme_transcription(
            device_id=request.device_id,
            local_date=request.local_date,
            local_time=request.local_time
        )

        if not transcription:
            raise HTTPException(
                status_code=404,
                detail=f"No transcription found for device {request.device_id} on {request.local_date}"
            )

        # Save initial request to database
        context_data = {
            "source": "watchme_spot_features",
            "device_id": request.device_id,
            "local_date": request.local_date,
            "local_time": request.local_time
        }

        await db.save_punchline_request(
            request_id=request_id,
            conversation_text=transcription,
            user_id=request.user_id,
            context_data=context_data
        )

        # Pipeline 1: Structure conversation
        print(f"Starting Pipeline 1: Structure conversation for request {request_id}")
        structured_conversation = await structure_conversation(transcription)

        # Check for processing errors
        if "processing_error" in structured_conversation:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to structure conversation: {structured_conversation.get('processing_error')}"
            )

        # Save structured conversation to database
        await db.save_structured_conversation(
            request_id=request_id,
            structured_result=structured_conversation,
            speakers=structured_conversation.get('speakers', []),
            turn_count=structured_conversation.get('total_turns', 0),
            summary=structured_conversation.get('summary', '')
        )

        # Pipeline 2: Extract punchlines
        print(f"Starting Pipeline 2: Extract punchlines for request {request_id}")
        punchlines_result = await extract_punchlines(structured_conversation)

        # Check for processing errors
        if "processing_error" in punchlines_result:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract punchlines: {punchlines_result.get('processing_error')}"
            )

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Prepare metadata
        metadata = {
            "source": "watchme_spot_features",
            "device_id": request.device_id,
            "local_date": request.local_date,
            "local_time": request.local_time,
            "total_punchlines": len(punchlines_result.get('punchlines', [])),
            "processing_time_ms": processing_time_ms,
            "model_used": f"{CURRENT_PROVIDER}/{CURRENT_MODEL}",
            "conversation_length": len(transcription),
            "turn_count": structured_conversation.get('total_turns', 0)
        }

        # Save punchline results to database
        await db.save_punchline_results(
            request_id=request_id,
            punchlines=punchlines_result.get('punchlines', []),
            metadata=metadata,
            llm_model=f"{CURRENT_PROVIDER}/{CURRENT_MODEL}"
        )

        # Return complete response
        return ExtractionResponse(
            status="success",
            request_id=request_id,
            structured_conversation=structured_conversation,
            punchlines=punchlines_result.get('punchlines', []),
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in extract_from_watchme: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    # Local development server
    uvicorn.run(app, host="0.0.0.0", port=8060)