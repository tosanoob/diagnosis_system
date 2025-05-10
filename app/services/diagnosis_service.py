"""
Service layer cho chẩn đoán và phân tích dữ liệu y khoa
"""
from typing import List, Dict, Tuple, Optional, Any, Union
import asyncio
from app.db.chromadb_service import chromadb_instance
from app.db.neo4j_service import neo4j_instance
from app.services.llm_service import extract_keywords, get_image_caption, generate_with_image, gemini_llm_request
from app.constants.enums import EntityType
from app.models.domain import ReasoningPrompt
from app.core.utils import (
    count_disease_scores, 
    sort_image_results,
    sort_text_results,
    sort_document_results,
    get_document
)
from app.core.logging import logger

# Helper coroutines for image diagnosis
async def get_caption_async(image_base64: str) -> str:
    """Async wrapper for getting image caption"""
    caption = get_image_caption(image_base64)
    logger.app_info("Caption:")
    logger.app_info(caption)
    return caption

async def get_keywords_async(text: str) -> List[str]:
    """Async wrapper for extracting keywords"""
    return extract_keywords(text)

async def retrieve_disease_keywords_async(keywords: List[str]) -> Tuple[List, List]:
    """Get disease keywords from ChromaDB"""
    diseases = chromadb_instance.retrieve_keyword(keywords, entity_type=EntityType.DISEASE)
    disease_labels = sort_text_results(diseases)
    disease_labels = [(item[0].replace('.txt', '').replace('_', ' ').strip(), item[1]) for item in disease_labels]
    return diseases, disease_labels

async def retrieve_symptom_anatomy_async(keywords: List[str]) -> Tuple[Dict, Dict]:
    """Get symptom and anatomy keywords from ChromaDB"""
    symptoms = chromadb_instance.retrieve_keyword(keywords, entity_type=EntityType.SYMPTOM)
    anatomies = chromadb_instance.retrieve_keyword(keywords, entity_type=EntityType.ANATOMY)
    return symptoms, anatomies

async def process_disease_queries_async(symptoms: Dict, anatomies: Dict) -> Tuple[List, List]:
    """Process disease queries using Neo4j and ChromaDB"""
    diseases_query = neo4j_instance.diagnose_disease_context(symptoms, anatomies)
    disease_scores = count_disease_scores(diseases_query)
    sorted_diseases = sorted(disease_scores.items(), key=lambda x: x[1], reverse=True)[:5]
    top_diseases = chromadb_instance.retrieve_keyword([item[0] for item in sorted_diseases], entity_type=EntityType.DISEASE)
    query_labels = sort_text_results(top_diseases)
    query_labels = [(item[0].replace('.txt', '').replace('_', ' ').strip(), item[1]) for item in query_labels]
    logger.app_info("Top diseases:")
    logger.app_info(sorted_diseases)
    logger.app_info("Query labels:")
    logger.app_info(query_labels)
    return sorted_diseases, query_labels

async def retrieve_similar_images_async(image_base64: str) -> List:
    """Get similar images from ChromaDB"""
    similar_images = chromadb_instance.retrieve_image_info(image_base64, n_results=15)
    logger.app_info("Labels from images:")
    image_labels = sort_image_results(similar_images)
    image_labels = [(item[0][:item[0].find('(')].strip(), item[1]) for item in image_labels]
    logger.app_info(image_labels)
    return image_labels

async def retrieve_similar_documents_async(text: str) -> List:
    """Get similar documents from ChromaDB"""
    similar_documents = chromadb_instance.retrieve_document(text)
    logger.app_info("Similar Documents:")
    document_labels = sort_document_results(similar_documents)
    logger.app_info(document_labels)
    return document_labels

async def get_top_labels_async(labels: List[Tuple[str, float]], top_k: int = 5, reverse: bool = False) -> Tuple[List, List]:
    """Get top k labels from list
    
    Args:
        labels: List of labels and their scores
        top_k: Number of top labels to return
        reverse: If input is bare distance, reverse should be True, otherwise if input is score (as higher is better), reverse should be False 
    Returns:
        Tuple of top k labels and their scores
    """

    all_labels = sorted(labels, key=lambda x: x[1], reverse=reverse)
    label_percentage_score = all_labels.copy()
    all_labels = [item[0] for item in label_percentage_score]
    all_labels = list(set(all_labels))
    top_k_labels = all_labels[:top_k]
    top_k_labels_score = []
    for label in top_k_labels:
        for item in label_percentage_score:
            if item[0] == label:
                top_k_labels_score.append(item[1])
                break
    return top_k_labels, top_k_labels_score

async def prepare_results_async(image_labels: List, query_labels: List, document_labels: List, disease_labels: List) -> Tuple[List, List]:
    """Prepare final results from all sources"""

    # Hàm chuẩn hóa điểm số
    def normalize_scores(labels_with_scores):
        if not labels_with_scores:
            return []
        
        # Tìm giá trị min và max trong danh sách điểm
        scores = [score for _, score in labels_with_scores]
        min_score = min(scores)
        max_score = max(scores)
        
        # Tránh chia cho 0 nếu min_score = max_score
        if max_score == min_score:
            return [(label, 0.0) for label, _ in labels_with_scores]
        
        # Chuẩn hóa điểm số về phạm vi (0,1)
        # Lưu ý: Điểm thấp hơn thường tốt hơn trong hệ thống này, nên chúng ta đảo ngược thang điểm
        normalized_labels = [(label, 1 - ((score - min_score) / (max_score - min_score))) 
                            for label, score in labels_with_scores]
        
        return normalized_labels

    neo4j_labels = normalize_scores(query_labels + disease_labels)
    chroma_labels = normalize_scores(document_labels)
    image_labels = normalize_scores(image_labels)
    all_labels = neo4j_labels + chroma_labels + image_labels
    top_5_labels, top_5_labels_score = await get_top_labels_async(all_labels, reverse=True)
    label_documents = [get_document(label) for label in top_5_labels]
    return list(zip(top_5_labels, top_5_labels_score)), label_documents

async def image_diagnosis_async(image_base64: str) -> Tuple[List, List]:
    """Async version of image diagnosis with concurrent tasks"""
    # Get caption from image
    caption = await get_caption_async(image_base64)
    
    # Extract keywords from caption
    keywords = await get_keywords_async(caption)
    
    # Run parallel tasks for retrieving data
    diseases_task = asyncio.create_task(retrieve_disease_keywords_async(keywords))
    symptom_anatomy_task = asyncio.create_task(retrieve_symptom_anatomy_async(keywords))
    similar_images_task = asyncio.create_task(retrieve_similar_images_async(image_base64))
    documents_task = asyncio.create_task(retrieve_similar_documents_async(caption))
    
    # Await completion of initial tasks
    _, disease_labels = await diseases_task
    symptoms, anatomies = await symptom_anatomy_task
    image_labels = await similar_images_task
    document_labels = await documents_task
    
    # Process disease queries with the results from symptoms and anatomies
    _, query_labels = await process_disease_queries_async(symptoms, anatomies)
    
    # Prepare final results
    return await prepare_results_async(image_labels, query_labels, document_labels, disease_labels)

async def text_diagnosis_async(text: str) -> Tuple[List, List]:
    """Async version of text diagnosis with concurrent tasks"""
    # Extract keywords from text
    keywords = await get_keywords_async(text)
    
    # Run parallel tasks for retrieving data
    diseases_task = asyncio.create_task(retrieve_disease_keywords_async(keywords))
    symptom_anatomy_task = asyncio.create_task(retrieve_symptom_anatomy_async(keywords))
    documents_task = asyncio.create_task(retrieve_similar_documents_async(text))
    
    # Await completion of initial tasks
    _, disease_labels = await diseases_task
    symptoms, anatomies = await symptom_anatomy_task
    document_labels = await documents_task
    
    # Process disease queries with the results from symptoms and anatomies
    _, query_labels = await process_disease_queries_async(symptoms, anatomies)
    
    # Prepare final results (without image_labels for text diagnosis)
    return await prepare_results_async([], query_labels, document_labels, disease_labels)

async def fusion_diagnosis_async(image_base64: str, text: str) -> Tuple[List, List]:
    """Async version of fusion diagnosis that combines image and text diagnosis"""
    # Run image and text diagnosis in parallel
    image_labels_task = asyncio.create_task(image_diagnosis_async(image_base64))
    text_labels_task = asyncio.create_task(text_diagnosis_async(text))
    
    # Await both tasks
    image_labels, _ = await image_labels_task
    text_labels, _ = await text_labels_task
    
    # Combine results
    all_labels = image_labels + text_labels
    top_5_labels, top_5_labels_score = await get_top_labels_async(all_labels, reverse=False)
    label_documents = [get_document(label) for label in top_5_labels]
    
    return list(zip(top_5_labels, top_5_labels_score)), label_documents

# Public API
async def get_context(
    text: Optional[str] = None, 
    image_base64: Optional[Union[str, List[str]]] = None
) -> Tuple[List, List]:
    """
    Lấy context cho chẩn đoán dựa trên text và/hoặc image_base64
    
    Args:
        text: Văn bản mô tả triệu chứng
        image_base64: Hình ảnh được mã hóa dưới dạng base64
        
    Returns:
        Tuple chứa danh sách nhãn và tài liệu tương ứng
    """
    if isinstance(image_base64, list) and image_base64:
        image_base64 = image_base64[0]  # Chỉ sử dụng ảnh đầu tiên nếu có nhiều ảnh
        
    if image_base64 and text:
        return await fusion_diagnosis_async(image_base64, text)
    elif image_base64:
        return await image_diagnosis_async(image_base64)
    elif text:
        return await text_diagnosis_async(text)
    else:
        raise ValueError("No input provided")

async def get_diagnosis(
    text: Optional[str] = None, 
    image_base64: Optional[Union[str, List[str]]] = None
) -> str:
    """
    Thực hiện chẩn đoán dựa trên text và/hoặc image_base64
    
    Args:
        text: Văn bản mô tả triệu chứng
        image_base64: Hình ảnh được mã hóa dưới dạng base64
        
    Returns:
        Kết quả chẩn đoán dưới dạng text
    """
    system_prompt = ReasoningPrompt.SYSTEM_PROMPT
    
    def format_context(all_labels, label_documents):
        context = ''
        len_labels = len(all_labels)
        for i in range(len_labels):
            context += f'**Tên bệnh:** {all_labels[i][0]}\n'
            context += f'**Điểm số:** {all_labels[i][1]}\n'
            context += f'**Thông tin dữ liệu về bệnh:** {label_documents[i]}\n'
            context += '-----------------------------------\n'
        return context
    
    if isinstance(image_base64, list) and image_base64:
        image_base64 = image_base64[0]  # Chỉ sử dụng ảnh đầu tiên nếu có nhiều ảnh
    
    if image_base64 and text:
        all_labels, label_documents = await fusion_diagnosis_async(image_base64, text)
        reasoning_prompt = ReasoningPrompt.format_prompt(text, image_base64, format_context(all_labels, label_documents))
        response = generate_with_image(image_base64, system_prompt, reasoning_prompt, max_tokens=10000)
    elif image_base64:
        all_labels, label_documents = await image_diagnosis_async(image_base64)
        reasoning_prompt = ReasoningPrompt.format_prompt(None, image_base64, format_context(all_labels, label_documents))
        response = generate_with_image(image_base64, system_prompt, reasoning_prompt, max_tokens=10000)
    elif text:
        all_labels, label_documents = await text_diagnosis_async(text)
        reasoning_prompt = ReasoningPrompt.format_prompt(text, None, format_context(all_labels, label_documents))
        response = gemini_llm_request(system_prompt, reasoning_prompt, max_tokens=10000)
    else:
        raise ValueError("No input provided")
    return all_labels,response 