"""
Service layer cho chẩn đoán và phân tích dữ liệu y khoa
"""
from typing import List, Dict, Tuple, Optional, Any, Union
import asyncio
import sys
import itertools
from concurrent.futures import ThreadPoolExecutor
import json
# Third-party imports
from rapidfuzz import process, fuzz

# App imports
from app.db.chromadb_service import chromadb_instance
from app.db.neo4j_service import neo4j_instance
from app.db.sqlite_service import get_db
from app.db import crud
from app.services.llm_service import (
    extract_keywords, 
    get_image_caption, 
    generate_with_image, 
    gemini_llm_request,
    openai_to_gemini_history,
    get_gemini_config,
    general_gemini_request,
    AllModelsFailedException
)
from app.services.disease_domain_crossmap_service import normalize_disease_name
from app.constants.enums import EntityType
from app.models.domain import ReasoningPrompt
from app.core.utils import (
    count_disease_scores, 
    sort_image_results,
    sort_text_results,
    sort_document_results,
    get_document,
    softmax,
    format_context,
    labels_to_folder,
    group_image_labels,
    format_label_name,
    score_fusion
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
    image_labels = sort_image_results(similar_images, top_k=15)
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
    top_k_labels_score = softmax(top_k_labels_score)
    return top_k_labels, top_k_labels_score

async def prepare_results_async(image_labels: List, query_labels: List, document_labels: List, disease_labels: List) -> Tuple[List, List]:
    """Prepare final results from all sources"""

    # Hàm chuẩn hóa điểm số
    def normalize_scores(labels_with_scores):
        # Normalize scores to 0-1 range for comparison across different methods
        if not labels_with_scores:
            return []
        scores = [score for _, score in labels_with_scores]
        min_score, max_score = min(scores), max(scores)
        score_range = max_score - min_score if max_score != min_score else 1
        return [(label, (score - min_score) / score_range) for label, score in labels_with_scores]

    # Get database session for get_document calls
    db = next(get_db())
    
    try:
        neo4j_labels = normalize_scores(query_labels + disease_labels)
        chroma_labels = normalize_scores(document_labels)
        image_labels = normalize_scores(image_labels)
        all_labels = neo4j_labels + chroma_labels + image_labels
        top_5_labels, top_5_labels_score = await get_top_labels_async(all_labels, reverse=True)
        label_documents = [get_document(label, db) for label in top_5_labels]
        return list(zip(top_5_labels, top_5_labels_score)), label_documents
    finally:
        db.close()

async def image_diagnosis_only_async(image_base64: str) -> Tuple[List, List]:
    """Async version of image diagnosis with concurrent tasks"""
    image_labels = await retrieve_similar_images_async(image_base64)
    return await prepare_results_async(image_labels, [], [], [])

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
    
    # Get database session for get_document calls
    db = next(get_db())
    try:
        label_documents = [get_document(label, db) for label in top_5_labels]
        return list(zip(top_5_labels, top_5_labels_score)), label_documents
    finally:
        db.close()

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

# ---- multi-turn diagnosis from image only ----

async def get_first_diagnosis_v2(image_base64: str, text: str = None) -> Tuple[List, str, List]:
    """Get context from image only"""
    all_labels, label_documents = await image_diagnosis_only_async(image_base64)
    
    reasoning_prompt = ReasoningPrompt.format_prompt_first(text, True, format_context(all_labels, label_documents))
    response = generate_with_image(image_base64, ReasoningPrompt.IMAGE_ONLY_SYSTEM_PROMPT, reasoning_prompt, max_tokens=10000)

    chat_history = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": text
                } if text else None,
                {
                    "type": "image",
                    "image": image_base64,
                    "mime_type": "image/jpeg"
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": response
                }
            ]
        }
    ]
    return all_labels, response, chat_history

async def get_later_diagnosis_v2(chat_history: List, text: str = None) -> Tuple[str, List]:
    """Get later diagnosis from chat history"""
    reasoning_prompt = ReasoningPrompt.format_prompt_later(text)
    chat_history.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": reasoning_prompt
            }
        ]
    })
    gemini_history = openai_to_gemini_history(chat_history)
    
    response = general_gemini_request(contents=gemini_history, config=get_gemini_config())
    chat_history.append({
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": response    
            }
        ]
    })
    return response, chat_history

# ----------------- v3 -------------------

async def get_images(image_base64: str) -> List[Tuple[str, float]]:
    """Get images with filter labels"""
    image_labels = chromadb_instance.retrieve_image_info(image_base64, n_results=10)
    image_labels = group_image_labels(image_labels, top_k=5)
    # image_labels = [(item[0][:item[0].find('(')].strip(), item[1]) for item in image_labels]
    return image_labels

async def get_first_stage_diagnosis_v3(image_base64: str, text: str = None) -> Tuple[List, str, List]:
    """Get first stage diagnosis from image only"""
    # Get database session for both querying diseases and getting documents
    db = next(get_db())
    try:
        # Query tất cả bệnh trong domain STANDARD từ database
        standard_domain = db.query(crud.domain.model).filter(
            crud.domain.model.domain.ilike("STANDARD"),
            crud.domain.model.deleted_at.is_(None)
        ).first()
        
        if not standard_domain:
            logger.app_info("Không tìm thấy domain STANDARD, fallback to static labels")
            all_labels = list(labels_to_folder.keys())
        else:
            # Lấy tất cả bệnh trong domain STANDARD
            diseases = db.query(crud.disease.model).filter(
                crud.disease.model.domain_id == standard_domain.id,
                crud.disease.model.deleted_at.is_(None),
                crud.disease.model.included_in_diagnosis.is_(True)
            ).all()
            
            all_labels = [disease.label for disease in diseases]

    finally:
        db.close()
    
    image_labels = await get_images(image_base64)
    # image_labels = [item[0] for item in image_labels]
    related_data = format_label_name(all_labels)
    reasoning_prompt = ReasoningPrompt.format_prompt_pick_disease(related_data, text)
    response = generate_with_image(image_base64, ReasoningPrompt.IMAGE_ONLY_SYSTEM_PROMPT, reasoning_prompt, max_tokens=10000)
    
    # Extract diagnoses from response text
    response = response.split("```python")[1].split("```")[0]
    try:
        llm_labels = json.loads(response)
    except json.JSONDecodeError:
        try:
            llm_labels = eval(response)
        except Exception as e:
            logger.app_info(f"Error parsing LLM response: {e}")
            llm_labels = []

    # Áp dụng improved fuzzy matching với multiple strategies
    matched_labels = []
    for llm_label in llm_labels:
        # Sử dụng improved matching với min_score = 60 (thấp hơn để có nhiều kết quả hơn)
        best_match = find_best_label_match(
            llm_label,
            all_labels,
            min_score=60
        )
        
        if best_match:
            matched_label, score = best_match
            matched_labels.append(matched_label)
            logger.app_info(f"Matched '{llm_label}' to '{matched_label}' with score {score}")
        else:
            logger.app_info(f"No good match found for '{llm_label}'")
            
    # Loại bỏ các label trùng lặp
    llm_labels = list(set(matched_labels))
    print(f'LLM labels: {llm_labels}')
    print(f'Image labels: {image_labels}')

    label_scores = score_fusion(image_labels, llm_labels, 0.05)
    label_documents = [get_document(label, db) for label, _ in label_scores]

    reasoning_prompt = ReasoningPrompt.format_prompt_analyze_diagnosis_v3(text, True, format_context(label_scores, label_documents))
    response = generate_with_image(image_base64, ReasoningPrompt.IMAGE_ONLY_SYSTEM_PROMPT, reasoning_prompt, max_tokens=10000)

    chat_history = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": reasoning_prompt
                } if text else None,
                {
                    "type": "image",
                    "image": image_base64,
                    "mime_type": "image/jpeg"
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": response
                }
            ]
        }
    ]
    
    return label_scores, response, chat_history

async def get_second_stage_diagnosis_v3(chat_history: List, text: str = None) -> Tuple[str, List]:
    """Get later diagnosis from chat history"""
    reasoning_prompt = text
    chat_history.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": reasoning_prompt
            }
        ]
    })
    gemini_history = openai_to_gemini_history(chat_history)
    
    response = general_gemini_request(contents=gemini_history, config=get_gemini_config())
    chat_history.append({
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": response    
            }
        ]
    })
    return response, chat_history

def find_best_label_match(
    query_name: str,
    all_labels: List[str],
    min_score: int = 60
) -> Optional[tuple]:
    """
    Tìm label match tốt nhất với improved fuzzy matching
    
    Args:
        query_name: Tên bệnh cần tìm
        all_labels: Danh sách labels chuẩn
        min_score: Điểm tối thiểu để accept match
        
    Returns:
        tuple: (matched_label, score) hoặc None
    """
    if not query_name or not all_labels:
        return None
    
    # Normalize query
    normalized_query = normalize_disease_name(query_name)
    logger.app_info(f"Tìm match cho: '{query_name}' -> normalized: '{normalized_query}'")
    
    # Tạo mapping từ normalized labels tới original labels
    label_mapping = {}
    normalized_labels = []
    
    # Tạo thêm mapping cho nội dung trong ngoặc đơn (tên tiếng Anh)
    english_mapping = {}
    english_terms = []
    
    import re
    for label in all_labels:
        normalized_label = normalize_disease_name(label)
        normalized_labels.append(normalized_label)
        label_mapping[normalized_label] = label
        
        # Extract nội dung trong ngoặc đơn để matching riêng
        parentheses_content = re.findall(r'\(([^)]*)\)', label)
        for content in parentheses_content:
            # Chuẩn hóa nội dung trong ngoặc
            normalized_content = content.lower().strip()
            # Tách các từ nếu có dấu phẩy hoặc dấu gạch ngang
            terms = re.split(r'[,-]', normalized_content)
            for term in terms:
                clean_term = term.strip()
                if clean_term and len(clean_term) > 2:  # Chỉ lấy term có độ dài > 2
                    english_terms.append(clean_term)
                    english_mapping[clean_term] = label
    
    # Log một vài ví dụ normalized labels để debug
    logger.app_info(f"Một vài normalized labels: {normalized_labels[:5]}")
    logger.app_info(f"English terms extracted: {english_terms[:10]}")
    
    # Thử multiple fuzzy matching strategies
    best_match = None
    best_score = 0
    
    # Strategy 1: fuzz.ratio với normalized text
    match1 = process.extractOne(
        normalized_query,
        normalized_labels,
        scorer=fuzz.ratio,
        score_cutoff=min_score
    )
    
    if match1 and match1[1] > best_score:
        best_match = match1
        best_score = match1[1]
        logger.app_info(f"fuzz.ratio match: '{match1[0]}' với score {match1[1]}")
    
    # Strategy 2: fuzz.partial_ratio với normalized text  
    match2 = process.extractOne(
        normalized_query,
        normalized_labels,
        scorer=fuzz.partial_ratio,
        score_cutoff=min_score
    )
    
    if match2 and match2[1] > best_score:
        best_match = match2
        best_score = match2[1]
        logger.app_info(f"fuzz.partial_ratio match: '{match2[0]}' với score {match2[1]}")
    
    # Strategy 3: fuzz.token_sort_ratio với normalized text
    match3 = process.extractOne(
        normalized_query,
        normalized_labels,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=min_score
    )
    
    if match3 and match3[1] > best_score:
        best_match = match3
        best_score = match3[1]
        logger.app_info(f"fuzz.token_sort_ratio match: '{match3[0]}' với score {match3[1]}")
    
    # Strategy 4: Exact match với original text (case insensitive)
    for label in all_labels:
        if query_name.lower() == label.lower():
            logger.app_info(f"Exact match tìm thấy: '{label}' cho query '{query_name}'")
            return (label, 100.0)
    
    # Strategy 5: Fuzzy match với English terms trong ngoặc đơn
    if english_terms:
        query_lower = query_name.lower().strip()
        
        # Thử exact match với English terms trước
        for term in english_terms:
            if query_lower == term:
                matched_label = english_mapping[term]
                logger.app_info(f"English exact match: '{query_name}' -> '{matched_label}' với score 100.0")
                return (matched_label, 100.0)
        
        # Thử fuzzy match với English terms
        english_match = process.extractOne(
            query_lower,
            english_terms,
            scorer=fuzz.ratio,
            score_cutoff=min_score
        )
        
        if english_match and english_match[1] > best_score:
            matched_label = english_mapping[english_match[0]]
            logger.app_info(f"English fuzzy match: '{query_name}' -> '{matched_label}' với score {english_match[1]}")
            return (matched_label, english_match[1])
    
    if best_match:
        matched_label = label_mapping[best_match[0]]
        logger.app_info(f"Best match cuối cùng: '{matched_label}' với score {best_match[1]}")
        return (matched_label, best_match[1])
    
    logger.app_info(f"Không tìm thấy match nào cho '{query_name}' với min_score={min_score}")
    return None