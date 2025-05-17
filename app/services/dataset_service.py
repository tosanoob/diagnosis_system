"""
Service for managing datasets
"""
import os
import shutil
import tempfile
import uuid
import json
from typing import List, Dict, Any, Optional
import asyncio
from sqlalchemy.orm import Session
import numpy as np
from datasets import load_dataset
from huggingface_hub import hf_hub_download

from app.core.config import settings
from app.core.logging import logger
from app.db import crud
from app.models.database import DomainCreate, DiseaseCreate
from app.services import domain_service, disease_service, image_service
from app.db.chromadb_service import chromadb_instance

# Dataset processing constants
BATCH_SIZE = 32  # Number of images to process in a batch

async def process_dataset_upload(
    dataset_name: str,
    metadata: List[Dict[str, Any]],
    custom_domain_name: Optional[str] = None,
    db: Session = None,
    user_id: str = None
) -> Dict[str, Any]:
    """
    Process the upload of a dataset from Hugging Face
    
    Args:
        dataset_name: Name of the dataset on Hugging Face
        metadata: List of objects mapping metadata for images
        custom_domain_name: Custom name for the domain (optional)
        db: Database session
        user_id: ID of the user performing the upload
        
    Returns:
        Dict with information about the uploaded dataset and created domain
    """
    # Determine domain name (use custom name if provided, otherwise use dataset name)
    domain_name = custom_domain_name if custom_domain_name else dataset_name
    
    # Create a temporary directory to store the dataset
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.app_info(f"Downloading dataset {dataset_name} to {temp_dir}")
        
        try:
            # Download dataset from Hugging Face
            dataset = await download_huggingface_dataset(dataset_name, temp_dir)
            
            # Create domain
            domain_data = DomainCreate(
                domain=domain_name,
                description=f"Domain created from Hugging Face dataset {dataset_name}",
                created_by=user_id
            )
            
            domain = await domain_service.create_domain(
                domain_data=domain_data,
                db=db,
                created_by=user_id
            )
            
            domain_id = domain["id"]
            
            # Extract unique labels from metadata
            unique_labels = set()
            for item in metadata:
                if "label" in item:
                    unique_labels.add(item["label"])
            
            # Create diseases for each unique label
            created_diseases = []
            for label in unique_labels:
                disease_data = DiseaseCreate(
                    label=label,
                    domain_id=domain_id,
                    description=f"Disease created from Hugging Face dataset {dataset_name}",
                    included_in_diagnosis=True
                )
                
                disease = await disease_service.create_disease(
                    disease_data=disease_data,
                    db=db,
                    created_by=user_id
                )
                created_diseases.append(disease)
            
            # Process images with metadata and encode them
            processed_count = await process_images_with_metadata(
                dataset=dataset,
                metadata=metadata,
                domain_id=domain_id,
                db=db
            )
            
            return {
                "success": True,
                "domain": domain,
                "diseases_created": len(created_diseases),
                "images_processed": processed_count,
                "message": f"Successfully uploaded dataset {dataset_name} and created domain {domain_name}"
            }
            
        except Exception as e:
            logger.error(f"Error processing dataset upload: {str(e)}")
            # TODO: Roll back domain and diseases if they were created
            raise
            
async def download_huggingface_dataset(dataset_name: str, target_dir: str):
    """
    Download a dataset from Hugging Face
    
    Args:
        dataset_name: Name of the dataset on Hugging Face
        target_dir: Directory to save the dataset
        
    Returns:
        The loaded dataset
    """
    # This function runs blocking I/O operations, so we run it in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: load_dataset(dataset_name, cache_dir=target_dir)
    )

async def process_images_with_metadata(
    dataset,
    metadata: List[Dict[str, Any]],
    domain_id: str,
    db: Session
) -> int:
    """
    Process images from the dataset, match with metadata, and encode them
    
    Args:
        dataset: HuggingFace dataset
        metadata: List of metadata items
        domain_id: ID of the domain these images belong to
        db: Database session
        
    Returns:
        Number of processed images
    """
    # Build a lookup for metadata by filename
    metadata_by_filename = {item.get("filename", ""): item for item in metadata}
    
    # Get image data from dataset
    # Assuming dataset has 'train' split with 'image' and 'file_name' columns
    try:
        # Try to access different possible structures of the dataset
        if 'train' in dataset:
            images = dataset['train']
        elif 'validation' in dataset:
            images = dataset['validation']
        elif 'test' in dataset:
            images = dataset['test']
        else:
            # Just take the first split whatever it is
            images = dataset[list(dataset.keys())[0]]
    except Exception as e:
        logger.error(f"Error accessing dataset structure: {str(e)}")
        raise
    
    # Track progress
    processed_count = 0
    
    # Process images in batches
    for i in range(0, len(images), BATCH_SIZE):
        batch = images[i:i+BATCH_SIZE]
        
        # Extract images and match with metadata
        batch_images = []
        batch_metadata = []
        
        for item in batch:
            # Get image from dataset (may have different structures)
            image = None
            filename = None
            
            # Try different possible structures
            if hasattr(item, "get"):
                if "image" in item:
                    image = item["image"]
                elif "img" in item:
                    image = item["img"]
                
                if "file_name" in item:
                    filename = item["file_name"]
                elif "filename" in item:
                    filename = item["filename"]
            
            # Skip if we couldn't get the image or filename
            if image is None or filename is None:
                continue
                
            # Find matching metadata
            item_metadata = metadata_by_filename.get(filename)
            if not item_metadata:
                continue
            
            # Convert PIL image to numpy array if needed
            if hasattr(image, "convert"):  # PIL Image
                image_array = np.array(image)
            else:
                image_array = image
                
            batch_images.append(image_array)
            
            # Include domain_id in metadata
            item_metadata["domain_id"] = domain_id
            batch_metadata.append(item_metadata)
        
        # Skip empty batches
        if not batch_images:
            continue
            
        # Encode images
        try:
            embeddings = image_service.encode_numpy_images(batch_images)
            
            # Save embeddings and metadata to vector DB
            await store_embeddings_in_vectordb(embeddings, batch_metadata)
            
            processed_count += len(batch_images)
            logger.app_info(f"Processed {processed_count} images so far")
            
        except Exception as e:
            logger.error(f"Error encoding or storing images: {str(e)}")
            continue
    
    return processed_count

async def store_embeddings_in_vectordb(embeddings, metadata_list):
    """
    Store image embeddings and metadata in vector database
    
    Args:
        embeddings: List of image embeddings
        metadata_list: List of metadata for each image
    """
    # Prepare IDs for ChromaDB
    ids = [str(uuid.uuid4()) for _ in range(len(embeddings))]
    
    # Store in ChromaDB
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: chromadb_instance.image_caption_collection.add(
            embeddings=embeddings,
            metadatas=metadata_list,
            ids=ids
        )
    )

async def delete_dataset(
    domain_name: str,
    db: Session,
    user_id: str
) -> Dict[str, Any]:
    """
    Delete a dataset domain and all associated records
    
    Args:
        domain_name: Name of the domain to delete
        db: Database session
        user_id: ID of the user performing the deletion
        
    Returns:
        Dict with information about the deletion
    """
    # Get domain by name
    domain = await domain_service.get_domain_by_name(domain_name, db)
    
    if not domain:
        raise ValueError(f"Domain {domain_name} not found")
    
    domain_id = domain["id"]
    
    # Get all diseases in this domain
    diseases = await disease_service.get_disease_by_domain(domain_id=domain_id, db=db)
    
    # Delete all diseases in this domain
    for disease in diseases:
        await disease_service.delete_disease(
            disease_id=disease["id"],
            soft_delete=False,  # Hard delete
            deleted_by=user_id,
            db=db
        )
    
    # Delete vector DB records with this domain_id
    # This is a blocking operation, so we run it in a thread pool
    def delete_from_vector_db():
        try:
            # Delete by filtering on domain_id in metadata
            chromadb_instance.image_caption_collection.delete(
                where={"domain_id": domain_id}
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting vector DB records: {str(e)}")
            return False
    
    loop = asyncio.get_event_loop()
    vector_db_deleted = await loop.run_in_executor(None, delete_from_vector_db)
    
    # Delete the domain itself
    deleted_domain = await domain_service.delete_domain(
        domain_id=domain_id,
        soft_delete=False,  # Hard delete
        deleted_by=user_id,
        db=db
    )
    
    return {
        "success": True,
        "domain_deleted": deleted_domain,
        "diseases_deleted": len(diseases),
        "vector_db_records_deleted": vector_db_deleted,
        "message": f"Successfully deleted dataset domain {domain_name}"
    } 