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
from app.services import domain_service, disease_service, image_service, disease_domain_crossmap_service
from app.services.llm_service import gemini_llm_request, AllModelsFailedException
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
            
            # Tự động tạo ánh xạ với domain STANDARD bằng Gemini AI
            auto_mapping_result = await auto_map_diseases_with_gemini(
                dataset_name=dataset_name,
                domain_id=domain_id,
                domain_name=domain_name,
                new_diseases=created_diseases,
                db=db,
                created_by=user_id
            )
            
            return {
                "success": True,
                "domain": domain,
                "diseases_created": len(created_diseases),
                "images_processed": processed_count,
                "auto_mapping": auto_mapping_result,
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

    len_dataset = len(images)
    if len_dataset != len(metadata):
        min_len = min(len_dataset, len(metadata))
    else:
        min_len = len_dataset
        
    images_with_metadata = [
        {
            **images[i],
            filename_field: metadata[i][filename_field],
            label_field: metadata[i][label_field]
        }
        for i in range(min_len)
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

async def auto_map_diseases_with_gemini(
    dataset_name: str,
    domain_id: str,
    domain_name: str,
    new_diseases: List[Dict[str, Any]],
    db: Session,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tự động tạo ánh xạ giữa domain mới và domain STANDARD bằng Gemini AI
    
    Args:
        dataset_name: Tên dataset
        domain_id: ID của domain mới
        domain_name: Tên domain mới
        new_diseases: Danh sách các disease mới tạo
        db: Database session
        created_by: Người tạo ánh xạ
        
    Returns:
        Dict[str, Any]: Kết quả auto mapping
    """
    try:
        # Tìm domain STANDARD
        standard_domain = db.query(crud.domain.model).filter(
            crud.domain.model.domain.ilike("STANDARD"),
            crud.domain.model.deleted_at.is_(None)
        ).first()
        
        if not standard_domain:
            logger.warning("Không tìm thấy domain STANDARD, bỏ qua auto mapping")
            return {
                "success": False,
                "message": "Không tìm thấy domain STANDARD",
                "mappings_created": 0
            }
        
        # Lấy tất cả diseases trong STANDARD domain
        standard_diseases = db.query(crud.disease.model).filter(
            crud.disease.model.domain_id == standard_domain.id,
            crud.disease.model.deleted_at.is_(None)
        ).all()
        
        if not standard_diseases:
            logger.warning("Domain STANDARD không có diseases nào")
            return {
                "success": False,
                "message": "Domain STANDARD không có diseases nào",
                "mappings_created": 0
            }
        
        # Chuẩn bị prompt cho Gemini
        new_disease_labels = [disease["label"] for disease in new_diseases]
        standard_disease_labels = [disease.label for disease in standard_diseases]
        
        SYSTEM_INSTRUCTION = """Bạn là một chuyên gia trong cả lĩnh vực bệnh da liễu và khoa học dữ liệu. Nhiệm vụ của bạn là nghiên cứu và phân nhóm các nhãn bệnh liên quan đến nhau để đạt hiệu quả tối đa trong việc chẩn đoán bệnh từ hình ảnh da liễu."""

        USER_INSTRUCTION = f"""Bạn được cung cấp các thông tin sau:
- Một bộ 65 bệnh chuẩn lấy từ dữ liệu của Bộ Y tế Việt Nam, về các bệnh da liễu thường gặp và cách phòng ngừa, điều trị bệnh da liễu tương ứng
- Một danh sách các nhãn bệnh từ một bộ dataset khác.

Nhiệm vụ của bạn là thực hiện ánh xạ sau: với mỗi nhãn bệnh từ dataset ngoài, hãy liệt kê một danh sách các nhãn bệnh chuẩn CÓ LIÊN QUAN hoặc có TƯƠNG ĐỒNG CAO với nhãn đó.
Mục đích của ánh xạ này là thực hiện encode một nhãn bên ngoài thành one-hot encoding của 65 bệnh chuẩn ở trên. Do đó, hãy đảm bảo ánh xạ này thật chuẩn, không dư thừa cũng không thiếu sót.

Ví dụ: 
"Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions" => ['DÀY SỪNG ÁNH SÁNG', 'UNG THƯ BIỂU MÔ TẾ BÀO ĐÁY', 'UNG THƯ TẾ BÀO HẮC TỐ', ...] hoặc các bệnh liên quan khác

CHÚ Ý: ở ví dụ trên có thể không giống với 65 bệnh chuẩn, nhưng bạn phải sinh ra ánh xạ chính xác sang tên của các bệnh chuẩn trong 65 bệnh đã cung cấp.

Sau đây là thông tin về các bệnh chuẩn:

**STANDARD DISEASES**
{chr(10).join(f'- {label}' for label in standard_disease_labels)}

**EXTERNAL DATASET LABELS**
{chr(10).join(f'- {label}' for label in new_disease_labels)}

Hãy đảm bảo đọc kỹ thông tin của các bệnh ở STANDARD DISEASES, suy luận từng bệnh ở EXTERNAL DATASET LABELS và đưa ra kết quả phù hợp ở dạng JSON, với key là các nhãn ở EXTERNAL DATASET LABELS và value là danh sách các nhãn bệnh chuẩn (STANDARD DISEASES) có liên quan hoặc tương đồng cao với nhãn đó.
Đảm bảo bạn ghi chính xác tên bệnh ở STANDARD DISEASES, ngay cả phần trong dấu ngoặc.
Bạn có thể suy luận để cải thiện câu trả lời của mình, nhưng không được thêm bất kỳ thông tin nào không liên quan.
Đảm bảo kết quả của bạn là một JSON object hợp lệ, đặt trong cú pháp ```json và ```.
"""

        # Gọi Gemini API
        logger.app_info(f"Đang gọi Gemini để tự động ánh xạ diseases cho dataset {dataset_name}")
        retries = 3
        for _ in range(retries):
            try:
                gemini_response = gemini_llm_request(
                    system_instruction=SYSTEM_INSTRUCTION,
                    user_instruction=USER_INSTRUCTION,
                        model=None,  # Sử dụng fallback logic với multiple models
                    temperature=0.0,
                    max_tokens=5000
                )
            except AllModelsFailedException as e:
                logger.error(f"Tất cả Gemini models đều fail khi tự động ánh xạ: {str(e)}")
                return {
                    "success": False,
                    "message": f"Tất cả Gemini models đều fail: {str(e)}",
                    "mappings_created": 0,
                    "gemini_response": None,
                    "import_result": None
                }
            
            # Parse JSON response từ Gemini
            try:
                # Làm sạch response để chỉ lấy JSON
                response_text = gemini_response.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:-3]
                elif response_text.startswith("```"):
                    response_text = response_text[3:-3]
                logger.app_info(f"Gemini response: {response_text}")
                mappings = json.loads(response_text)
                
                if not isinstance(mappings, dict):
                    continue
                else:
                    break
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Lỗi parse JSON từ Gemini response: {str(e)}")
                logger.error(f"Gemini response: {gemini_response}")
                mappings = None
                continue
            
        if not isinstance(mappings, dict):
            return {
                "success": False,
                "message": "Lỗi parse JSON từ Gemini response",
                "gemini_response": gemini_response,
                "import_result": None,
                "mappings_created": 0
            }
        
        # Sử dụng service import_crossmaps_from_json để tạo ánh xạ
        logger.app_info(f"Tạo ánh xạ tự động với {len(mappings)} mappings")
        import_result = await disease_domain_crossmap_service.import_crossmaps_from_json(
            target_domain_name=domain_name,
            mappings=mappings,
            db=db,
            created_by=created_by
        )
        logger.app_info(f"Import result: {import_result}")
        
        return {
            "success": True,
            "message": f"Tự động tạo ánh xạ thành công cho dataset {dataset_name}",
            "gemini_mappings": mappings,
            "import_result": import_result,
            "mappings_created": import_result.get("success_count", 0)
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi tự động ánh xạ diseases với Gemini: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi tự động ánh xạ: {str(e)}",
            "mappings_created": 0,
            "gemini_response": None,
            "import_result": None
        } 