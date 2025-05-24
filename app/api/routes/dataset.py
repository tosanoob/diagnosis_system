from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
import json

from app.db.sqlite_service import get_db
from app.api.routes.auth import get_current_user, get_admin_user
from app.services import dataset_service

router = APIRouter()

@router.post("/upload", response_model=Dict[str, Any])
async def upload_dataset(
    background_tasks: BackgroundTasks,
    dataset_name: str,
    custom_domain_name: Optional[str] = None,
    metadata_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)  # Changed from get_admin_user to get_current_user
):
    """
    Upload a dataset from Hugging Face and create corresponding domain and diseases
    
    Args:
        dataset_name: Name of the dataset on Hugging Face
        custom_domain_name: Custom name for the domain (optional)
        metadata_file: JSON file mapping metadata to images in the dataset
    
    Returns:
        Information about the uploaded dataset and created domain
    """
    # Read and parse metadata file
    metadata_content = await metadata_file.read()
    try:
        metadata = json.loads(metadata_content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON metadata file")
    
    # Process the dataset upload
    background_tasks.add_task(dataset_service.process_dataset_upload,
        dataset_name=dataset_name,
        metadata=metadata,
        custom_domain_name=custom_domain_name,
        db=db,
        user_id=current_user["user_id"]
    )
    
    return {
        "success": True,
        "message": "Dataset upload started in background"
    }

@router.delete("/{domain_name}", response_model=Dict[str, Any])
async def delete_dataset(
    domain_name: str = Path(..., description="Name of the domain to delete"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)  # Changed from get_admin_user to get_current_user
):
    """
    Delete a dataset and all its associated diseases and vector DB records
    
    Args:
        domain_name: Name of the domain to delete
    
    Returns:
        Confirmation of deletion
    """
    try:
        result = await dataset_service.delete_dataset(
            domain_name=domain_name,
            db=db,
            user_id=current_user["user_id"]
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
