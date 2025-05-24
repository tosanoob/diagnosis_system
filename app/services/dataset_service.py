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
    
    # Variables to track created resources for potential rollback
    domain = None
    created_diseases = []
    
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
            
            # Tạo dictionary ánh xạ label tới disease_id
            label_to_disease_id = {}
            for disease in created_diseases:
                label_to_disease_id[disease["label"]] = disease["id"]

            # Process images with metadata and encode them
            processed_count = await process_images_with_metadata(
                dataset=dataset,
                metadata=metadata,
                domain_id=domain_id,
                domain_name=domain_name,
                label_to_disease_id=label_to_disease_id,
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
            
            # Rollback: Xóa tất cả domain và diseases đã tạo nếu xử lý thất bại
            await rollback_dataset_creation(domain, created_diseases, db, user_id)
            
            # Re-raise the exception after rollback
            raise
            
async def rollback_dataset_creation(domain, created_diseases, db, user_id):
    """
    Rollback domain and diseases creation when dataset processing fails
    
    Args:
        domain: The domain that was created
        created_diseases: List of diseases that were created
        db: Database session
        user_id: ID of the user performing the rollback
    """
    logger.app_info("Rolling back domain and diseases due to dataset processing failure")
    
    # Xóa tất cả các bệnh đã tạo
    if created_diseases:
        for disease in created_diseases:
            try:
                await disease_service.delete_disease(
                    disease_id=disease["id"],
                    soft_delete=False,  # Hard delete
                    deleted_by=user_id,
                    db=db
                )
                logger.app_info(f"Rolled back disease: {disease['label']} ({disease['id']})")
            except Exception as e:
                logger.error(f"Error rolling back disease {disease['id']}: {str(e)}")
    
    # Xóa domain đã tạo
    if domain:
        try:
            await domain_service.delete_domain(
                domain_id=domain["id"],
                soft_delete=False,  # Hard delete
                deleted_by=user_id,
                db=db
            )
            logger.app_info(f"Rolled back domain: {domain['domain']} ({domain['id']})")
        except Exception as e:
            logger.error(f"Error rolling back domain {domain['id']}: {str(e)}")

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
    domain_name: str,
    label_to_disease_id: Dict[str, str],
    db: Session
) -> int:
    """
    Process images from the dataset, match with metadata, and encode them
    
    Args:
        dataset: HuggingFace dataset
        metadata: List of metadata items
        domain_id: ID of the domain these images belong to
        domain_name: Name of the domain these images belong to
        db: Database session
        
    Returns:
        Number of processed images
    """
    # Metadata must be a list, each item is a dict.
    # The image in dataset with index i has metadata[i]
    if not isinstance(metadata, list):
        raise ValueError("Metadata must be a list")
    
    # Get image data from dataset
    # Assuming dataset has 'train' split with 'image' and 'file_name' columns
    print(split_keys:=list(dataset.keys()))
    print(dataset.get(split_keys[0]))
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
    possible_image_fields = ["image", "img", "image_path", "image_url"]
    possible_filename_fields = ["file_name", "filename", "name"]
    possible_label_fields = ["label", "labels"]
    filename_field = None            
    label_field = None

    metadata_sample = metadata[0]
    for field in possible_label_fields:
        if field in metadata_sample:
            label_field = field
            break   
            
    if label_field is None:
        raise ValueError("Label field not found in metadata")

    for field in possible_filename_fields:
        if field in metadata_sample:
            filename_field = field
            break
            
    if filename_field is None:
        raise ValueError("Filename field not found in metadata")

    possible_filename_fields = ["file_name", "filename", "name"]
    image_field = None

    for field in possible_image_fields:
        if field in images[0]:
            image_field = field
            break

    if image_field is None:
        raise ValueError("Image field not found in dataset")

    images_with_metadata = [
        {
            **images[i],
            filename_field: metadata[i][filename_field],
            label_field: metadata[i][label_field]
        }
        for i in range(len(images))
    ]
    
    for i in range(0, len(images_with_metadata), BATCH_SIZE):
        batch = images_with_metadata[i:i+BATCH_SIZE]
        # Extract images and match with metadata
        batch_ids = []
        batch_images = []
        batch_metadata = []
            
        for item in batch:
            # Get image from dataset (may have different structures)
            image = item[image_field]
            filename = item[filename_field]
            label = item[label_field]

            item_metadata = {}
            # Skip if we couldn't get the image or filename
            if image is None or filename is None:
                continue
            
            # Convert PIL image to numpy array if needed
            if hasattr(image, "convert"):  # PIL Image
                image_array = np.array(image)
            else:
                image_array = image
                
            batch_ids.append(f"{domain_name}-{label}-{str(uuid.uuid4())}")

            batch_images.append(image_array)
            
            # Include domain_id in metadata
            item_metadata["domain_id"] = domain_id
            item_metadata["domain_name"] = domain_name
            item_metadata["domain_disease"] = label
            item_metadata["domain_disease_id"] = label_to_disease_id[label]
            item_metadata["label"] = ""
            item_metadata["label_id"] = ""
            item_metadata["is_disabled"] = False
            batch_metadata.append(item_metadata)
        
        # Skip empty batches
        if not batch_images:
            continue
            
        # Encode images
        try:
            embeddings = image_service.encode_numpy_images(batch_images)
            print(np.array(embeddings).shape)
            # Save embeddings and metadata to vector DB
            await store_embeddings_in_vectordb(batch_ids, embeddings, batch_metadata)
            
            processed_count += len(batch_images)
            logger.app_info(f"Processed {processed_count} images so far")
            
        except Exception as e:
            raise RuntimeError(f"Error encoding or storing images: {str(e)}")
    
    return processed_count

async def store_embeddings_in_vectordb(ids, embeddings, metadata_list):
    """
    Store image embeddings and metadata in vector database
    
    Args:
        embeddings: List of image embeddings
        metadata_list: List of metadata for each image
    """
    
    # Store in ChromaDB
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: chromadb_instance.add_image_caption(
            image_id=ids,
            metadata=metadata_list,
            embeddings=embeddings
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
    diseases_result = await disease_service.get_disease_by_domain(domain_id=domain_id, db=db)
    
    # get_disease_by_domain trả về tuple (diseases, total_count)
    diseases = diseases_result[0]
    total_diseases = diseases_result[1]
    
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
            chromadb_instance.delete_entire_domain(domain_id=domain_id)
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
        "diseases_deleted": total_diseases,
        "vector_db_records_deleted": vector_db_deleted,
        "message": f"Successfully deleted dataset domain {domain_name}"
    } 