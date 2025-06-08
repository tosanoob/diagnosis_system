import json
import os
import numpy as np
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.db import crud
from app.db.sqlite_service import get_db
from app.core.logging import logger

# Deprecated - will be removed
labels = json.load(open('labels.json', 'r', encoding='utf-8'))
labels_to_folder = labels['disease_document_path']

def count_disease_scores(relation_list):
    """
    Đếm số lần xuất hiện của mỗi disease trong danh sách các dictionary.

    Args:
        relation_list (List[dict]): Danh sách các dictionary có key 'disease'

    Returns:
        dict: {disease: score}
    """
    disease_scores = {}
    for item in relation_list:
        disease = item.get('disease')
        if disease:
            disease_scores[disease] = disease_scores.get(disease, 0) + 1
    return disease_scores

def dynamic_top_k(scores, drop_threshold=0.2, mean_threshold=0.5, top_k=15):
    """
    Dynamic top_k using the Gap algorithm, choose the suitable top_k based on the score drop value.
    The score drop is calculated as log(score_0/score_i+1), assume the scores are sorted in descending order.
    The mean score of top_k must be no less than mean_threshold, if not, the top_k will be reduced.
    """
    if len(scores) <= top_k:
        return top_k
    selected = []
    for i in range(len(scores)):
        if i == 0:
            selected.append(scores[i])
        else:
            if scores[0] / scores[i] > drop_threshold:
                selected.append(scores[i])
    while True:
        if len(selected) >= 0:
            if sum(selected) / len(selected) >= mean_threshold:
                break
            else:
                selected.pop()
        else:
            break
    if len(selected) > top_k:
        return top_k
    else:
        return len(selected)

def sort_text_results(text_results, method='weighted', top_k=3):
    """
    Sort the text results by score with different scoring methods
    
    Args:
        text_results (dict): Dictionary containing text results
        method (str): Scoring method to use. Options:
            - 'average': Average distance of items with same label (default)
            - 'weighted': Weighted average based on frequency, lower score is better
            - 'min': Minimum distance among items with same label
            - 'frequency': Score based on frequency of label appearance
        top_k (int): Number of top results to return, default is 3
            
    Returns:
        list: List of tuples (label, score) sorted by score from low to high, limited to top_k results
    """
    all_label_scores = []
    for item in text_results:
        for subitem in text_results[item]:
            docs = subitem['metadata']['docs']
            labels = eval(docs)
            for l in labels:
                all_label_scores.append(
                    {
                        'label': l,
                        'score': subitem['distance']
                    }
                )
    all_labels = [item['label'] for item in all_label_scores]
    all_labels = list(set(all_labels))
    label_score = {}
    label_count = {}
    
    # Initialize scores and counts
    for label in all_labels:
        label_score[label] = 0
        label_count[label] = 0
        
    # Calculate scores based on method
    if method == 'average':
        for item in all_label_scores:
            label = item['label']
            score = item['score']
            label_score[label] = label_score[label] + score
            label_count[label] = label_count[label] + 1
        for label in all_labels:
            label_score[label] = label_score[label] / label_count[label]
            
    elif method == 'weighted':
        for item in all_label_scores:
            label = item['label']
            score = item['score']
            label_score[label] = label_score[label] + score
            label_count[label] = label_count[label] + 1
        for label in all_labels:
            # Weighted average: more frequent labels get lower scores (better)
            weight = label_count[label] / len(all_label_scores)
            # Normalize the average score and apply frequency weight
            avg_score = label_score[label] / label_count[label]
            max_score = max(label_score.values()) / min(label_count.values())
            normalized_score = avg_score / max_score
            label_score[label] = normalized_score * (1 - weight)  # Subtract weight to make frequent labels better
            
    elif method == 'min':
        for item in all_label_scores:
            label = item['label']
            score = item['score']
            if label not in label_score or score < label_score[label]:
                label_score[label] = score
            label_count[label] = label_count[label] + 1
            
    elif method == 'frequency':
        for item in all_label_scores:
            label = item['label']
            label_count[label] = label_count[label] + 1
        for label in all_labels:
            # Score based on frequency (higher frequency = lower score = better)
            label_score[label] = 1 - (label_count[label] / len(all_label_scores))
            
    sorted_label_score = sorted(label_score.items(), key=lambda x: x[1])
    if top_k > 0:
        return sorted_label_score[:top_k]
    else:
        return sorted_label_score

def sort_document_results(document_results, method='weighted', top_k=3):
    """
    Sort the document results by score with different scoring methods
    
    Args:
        document_results (dict): Dictionary containing document results with keys:
            - 'distances': Distances of each document
            - 'metadatas': Metadata of each document, including 'disease'
            - 'documents': Content of the documents
        method (str): Scoring method to use. Options:
            - 'average': Average distance of items with same label (default)
            - 'weighted': Weighted average based on frequency, lower score is better
            - 'min': Minimum distance among items with same label
            - 'frequency': Score based on frequency of label appearance
        top_k (int): Number of top results to return, default is 3
            
    Returns:
        list: List of tuples (label, score) sorted by score from low to high, limited to top_k results
    """
    if not document_results or 'distances' not in document_results or 'metadatas' not in document_results:
        return []
    
    distances = document_results['distances']
    metadatas = document_results['metadatas']
    documents = document_results.get('documents', [])
    
    # Create list of labels and their scores
    all_label_scores = []
    for i in range(len(distances)):
        if i < len(metadatas) and 'disease' in metadatas[i]:
            label = metadatas[i]['disease']
            score = distances[i]
            all_label_scores.append({'label': label, 'score': score})
    
    # Initialize dictionaries for scores and counts
    all_labels = list(set([item['label'] for item in all_label_scores]))
    label_score = {label: 0 for label in all_labels}
    label_count = {label: 0 for label in all_labels}
    
    # Calculate scores based on method
    if method == 'average':
        for item in all_label_scores:
            label = item['label']
            score = item['score']
            label_score[label] = label_score[label] + score
            label_count[label] = label_count[label] + 1
        for label in all_labels:
            label_score[label] = label_score[label] / label_count[label]
            
    elif method == 'weighted':
        for item in all_label_scores:
            label = item['label']
            score = item['score']
            label_score[label] = label_score[label] + score
            label_count[label] = label_count[label] + 1
        for label in all_labels:
            # Weighted average: more frequent labels get lower scores (better)
            weight = label_count[label] / len(all_label_scores)
            # Normalize the average score and apply frequency weight
            avg_score = label_score[label] / label_count[label]
            max_score = max(label_score.values()) / min(label_count.values()) if min(label_count.values()) > 0 else 1
            normalized_score = avg_score / max_score if max_score > 0 else avg_score
            label_score[label] = normalized_score * (1 - weight)  # Subtract weight to make frequent labels better
            
    elif method == 'min':
        for item in all_label_scores:
            label = item['label']
            score = item['score']
            if label not in label_score or score < label_score[label]:
                label_score[label] = score
            label_count[label] = label_count[label] + 1
            
    elif method == 'frequency':
        for item in all_label_scores:
            label = item['label']
            label_count[label] = label_count[label] + 1
        for label in all_labels:
            # Score based on frequency (higher frequency = lower score = better)
            label_score[label] = 1 - (label_count[label] / len(all_label_scores))
    
    # Sort labels by score from low to high
    sorted_label_score = sorted(label_score.items(), key=lambda x: x[1])
    if top_k > 0:
        return sorted_label_score[:top_k]
    else:
        return sorted_label_score

def get_document(disease_name: str, db: Optional[Session] = None) -> List[str]:
    """
    Lấy description của bệnh từ database domain STANDARD
    
    Args:
        disease_name: Tên bệnh cần tìm
        db: Database session (optional)
        
    Returns:
        List[str]: Danh sách descriptions của bệnh (nếu có nhiều match)
    """
    # print(f"Finding document for disease from DB: {disease_name}")
    
    # Tạo database session nếu chưa có
    if db is None:
        db = next(get_db())
    
    try:
        # Tìm domain STANDARD
        standard_domain = db.query(crud.domain.model).filter(
            crud.domain.model.domain.ilike("STANDARD"),
            crud.domain.model.deleted_at.is_(None)
        ).first()
        
        if not standard_domain:
            print("Không tìm thấy domain STANDARD")
            return []
        
        # Tìm diseases với tên tương ứng trong domain STANDARD
        diseases = db.query(crud.disease.model).filter(
            crud.disease.model.domain_id == standard_domain.id,
            crud.disease.model.deleted_at.is_(None)
        ).all()
        
        # Tìm exact match hoặc partial match
        matching_diseases = []
        
        # Thử exact match trước (case insensitive)
        for disease in diseases:
            if disease.label.lower() == disease_name.lower():
                matching_diseases.append(disease)
        
        # Nếu không có exact match, thử partial match
        if not matching_diseases:
            for disease in diseases:
                if disease_name.lower() in disease.label.lower() or disease.label.lower() in disease_name.lower():
                    matching_diseases.append(disease)
        
        # Lấy descriptions
        documents = []
        for disease in matching_diseases:
            if disease.description and disease.description.strip():
                documents.append(disease.description)
                # print(f"Found disease: {disease.label} with description length: {len(disease.description)}")
            else:
                # Nếu không có description, sử dụng tên bệnh làm placeholder
                documents.append(f"Thông tin về bệnh {disease.label}")
                # print(f"Found disease: {disease.label} but no description available")
        
        if not documents:
            print(f"Không tìm thấy bệnh '{disease_name}' trong domain STANDARD")
            # Fallback: trả về thông tin cơ bản
            return [f"Không tìm thấy thông tin chi tiết về bệnh {disease_name}"]
        
        return documents
        
    except Exception as e:
        print(f"Lỗi khi lấy document từ database: {str(e)}")
        # Fallback to old logic if database fails
        return get_document_legacy(disease_name)
    finally:
        if db:
            db.close()

def get_document_legacy(disease_name: str) -> List[str]:
    """
    Legacy function để lấy document từ file (backup)
    """
    try:
        document_path = None
        # print("Finding document for disease (legacy): ", disease_name)
        if disease_name == 'PEMPHIGUS':
            document_path = labels_to_folder['PEMPHIGUS']
        else:
            for item in labels_to_folder:
                if disease_name in item:
                    document_path = labels_to_folder[item]
                    break
        
        if not document_path or not os.path.exists(document_path):
            return [f"Không tìm thấy thông tin về bệnh {disease_name}"]
            
        documents_files = os.listdir(document_path)
        documents_files = sorted(documents_files, key=lambda x: int(x.replace('.json','').split('_')[-1]))
        documents = []
        for d in documents_files:
            documents.append(
                json.load(open(os.path.join(document_path, d), 'r', encoding='utf-8'))['content']
            )
        return documents
    except Exception as e:
        print(f"Lỗi trong legacy function: {str(e)}")
        return [f"Không tìm thấy thông tin về bệnh {disease_name}"]

def softmax(scores):
    exp_scores = [np.exp(score) for score in scores]
    sum_exp_scores = sum(exp_scores)
    return [exp_score / sum_exp_scores for exp_score in exp_scores]

def format_context(all_labels, label_documents):
    context = ''
    len_labels = len(all_labels)
    for i in range(len_labels):
        context += f'**Tên bệnh:** {all_labels[i][0]}\n'
        context += f'**Điểm số:** {all_labels[i][1]}\n'
        context += f'**Thông tin dữ liệu về bệnh:** {label_documents[i]}\n'
        context += '-----------------------------------\n'
    return context

def format_label_name(all_labels):
    return '\n'.join([f'- {label}' for label in all_labels])

def sort_image_results(image_results, method='weighted', top_k=3):
    """
    Sort the image results by distance with different scoring methods
    
    Args:
        image_results (List[dict]): List of dictionaries containing 'label' and 'distance'
        method (str): Scoring method to use. Options:
            - 'average': Average distance of items with same label (default)
            - 'weighted': Weighted average based on frequency, lower score is better
            - 'min': Minimum distance among items with same label
            - 'frequency': Score based on frequency of label appearance
        top_k (int): Number of top results to return, default is 3
            
    Returns:
        list: List of tuples (label, score) sorted by score from low to high, limited to top_k results
    """
    sorted_image_results = sorted(image_results, key=lambda x: x['distance'])
    
    top_k = dynamic_top_k([item['distance'] for item in sorted_image_results], drop_threshold=0.2, mean_threshold=0.5, top_k=15)
    sorted_image_results = sorted_image_results[:top_k]
    
    labels = [item['label'] for item in sorted_image_results]
    labels = list(set(labels))
    label_score = {}
    label_count = {}
    # Initialize scores and counts
    for label in labels:
        label_score[label] = 0
        label_count[label] = 0
        
    # Calculate scores based on method
    if method == 'average':
        for item in sorted_image_results:
            label = item['label']
            score = item['distance']
            label_score[label] = label_score.get(label, 0) + score
            label_count[label] = label_count.get(label, 0) + 1
        for label in labels:
            label_score[label] = label_score[label] / label_count[label]
            
    elif method == 'weighted':
        for item in sorted_image_results:
            label = item['label']
            score = item['distance']
            label_score[label] = label_score.get(label, 0) + score
            label_count[label] = label_count.get(label, 0) + 1
        for label in labels:
            # Weighted average: more frequent labels get lower scores (better)
            weight = label_count[label] / len(sorted_image_results)
            # Normalize the average score and apply frequency weight
            avg_score = label_score[label] / label_count[label]
            max_score = max(label_score.values()) / min(label_count.values())
            normalized_score = avg_score / max_score
            label_score[label] = normalized_score * (1 - weight)  # Subtract weight to make frequent labels better
            
    elif method == 'min':
        for item in sorted_image_results:
            label = item['label']
            score = item['distance']
            if label not in label_score or score < label_score[label]:
                label_score[label] = score
            label_count[label] = label_count.get(label, 0) + 1
            
    elif method == 'frequency':
        for item in sorted_image_results:
            label = item['label']
            label_count[label] = label_count.get(label, 0) + 1
        for label in labels:
            # Score based on frequency (higher frequency = lower score = better)
            label_score[label] = 1 - (label_count[label] / len(sorted_image_results))
            
    sorted_label_score = sorted(label_score.items(), key=lambda x: x[1])
    if top_k > 0:
        return sorted_label_score[:top_k]
    else:
        return sorted_label_score

def group_image_labels(image_results, top_k=5):
    """
    Nhóm các nhãn bệnh từ kết quả tìm kiếm hình ảnh và tính điểm cho các nhãn STANDARD
    
    Args:
        image_results (List[Dict]): Danh sách kết quả tìm kiếm từ ChromaDB
            Mỗi item chứa: 'domain_id', 'domain_disease_id', 'label', 'distance'
        top_k (int): Số lượng nhãn STANDARD trả về (mặc định là 5)
    
    Returns:
        List[Tuple[str, float]]: Danh sách các nhãn STANDARD và điểm của chúng sau khi đã softmax
    """
    # Kiểm tra đầu vào
    if not image_results:
        return []

    # Sắp xếp kết quả theo khoảng cách tăng dần (khoảng cách nhỏ = tương đồng cao)
    sorted_image_results = sorted(image_results, key=lambda x: x['distance'])
    
    # Dictionary để lưu điểm của các nhãn STANDARD
    standard_label_scores = {}
    
    # Lấy session database
    db_generator = get_db()
    db = next(db_generator)
    
    try:
        # Tìm STANDARD domain
        standard_domain = db.query(crud.domain.model).filter(
            crud.domain.model.domain.ilike("STANDARD"),
            crud.domain.model.deleted_at.is_(None)
        ).first()
        
        if not standard_domain:
            logger.warning("Không tìm thấy domain STANDARD trong database")
            return []
        
        standard_domain_id = standard_domain.id
        logger.info(f"Tìm thấy domain STANDARD với ID: {standard_domain_id}")
        
        # Duyệt qua từng kết quả hình ảnh
        for item in sorted_image_results:
            domain_id = item.get('domain_id')
            disease_id = item.get('domain_disease_id')
            distance = item.get('distance', 0)
            
            if not domain_id or not disease_id:
                logger.warning(f"Kết quả thiếu domain_id hoặc domain_disease_id: {item}")
                continue
            
            # Nếu kết quả đã thuộc domain STANDARD, cộng điểm trực tiếp
            if domain_id == standard_domain_id:
                # Lấy disease từ database
                disease = db.query(crud.disease.model).filter(
                    crud.disease.model.id == disease_id,
                    crud.disease.model.deleted_at.is_(None)
                ).first()
                
                if disease:
                    # Điểm = 1 - distance (để điểm cao hơn = tương đồng cao hơn)
                    score = 1 - distance
                    standard_label_scores[disease.label] = standard_label_scores.get(disease.label, 0) + score
                    # logger.debug(f"Cộng {score:.4f} điểm cho nhãn STANDARD trực tiếp: {disease.label}")
            else:
                # Kết quả thuộc domain khác, tìm các crossmap với domain STANDARD
                crossmaps = db.query(crud.disease_domain_crossmap.model).filter(
                    # Tìm crossmap cho disease hiện tại
                    ((crud.disease_domain_crossmap.model.disease_id_1 == disease_id) & 
                     (crud.disease_domain_crossmap.model.domain_id_1 == domain_id)) |
                    ((crud.disease_domain_crossmap.model.disease_id_2 == disease_id) & 
                     (crud.disease_domain_crossmap.model.domain_id_2 == domain_id))
                ).all()
                
                if not crossmaps:
                    logger.debug(f"Không tìm thấy crossmap cho disease {disease_id} ở domain {domain_id}")
                
                # Duyệt qua các crossmap tìm được
                for crossmap in crossmaps:
                    # Xác định disease ID của STANDARD domain trong crossmap
                    standard_disease_id = None
                    if crossmap.domain_id_1 == standard_domain_id:
                        standard_disease_id = crossmap.disease_id_1
                    elif crossmap.domain_id_2 == standard_domain_id:
                        standard_disease_id = crossmap.disease_id_2
                    
                    if standard_disease_id:
                        # Lấy thông tin disease STANDARD
                        standard_disease = db.query(crud.disease.model).filter(
                            crud.disease.model.id == standard_disease_id,
                            crud.disease.model.deleted_at.is_(None)
                        ).first()
                        
                        if standard_disease:
                            # Điểm = 1 - distance
                            score = 1 - distance
                            standard_label_scores[standard_disease.label] = standard_label_scores.get(standard_disease.label, 0) + score
                            logger.debug(f"Cộng {score:.4f} điểm cho nhãn STANDARD qua crossmap: {standard_disease.label}")
        
        # Lấy các nhãn có điểm > 0
        labels_with_scores = [(label, score) for label, score in standard_label_scores.items() if score > 0]
        
        if not labels_with_scores:
            logger.warning("Không tìm thấy nhãn STANDARD nào có điểm > 0")
            return []
            
        # Sắp xếp theo điểm giảm dần
        labels_with_scores = sorted(labels_with_scores, key=lambda x: x[1], reverse=True)
        
        # Lấy điểm của top_k nhãn
        top_scores = [score for _, score in labels_with_scores]
        
        # Softmax để tổng điểm = 1
        normalized_scores = softmax(top_scores)
        
        # Lấy top_k nhãn
        
        # Tạo kết quả cuối cùng
        result = [(label, score) for (label, _), score in zip(labels_with_scores, normalized_scores)]
        logger.app_info(f"Kết quả group_image_labels: {result}")

        if top_k > 0 and top_k < len(result):
            result = result[:top_k]
        
        return result
    
    except Exception as e:
        logger.error(f"Lỗi trong group_image_labels: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []
    finally:
        db_generator.close()

def score_fusion(image_labels: List[Tuple[str, float]], llm_labels: List[str], llm_weight: float = 0.5):
    """
    Bổ sung điểm cho các nhãn từ LLM với weight cụ thể
    """
    # Tạo dictionary để lưu điểm của các nhãn
    label_scores = {}
    for label, _ in image_labels:
        label_scores[label] = 0
    
    # Cộng điểm cho các nhãn từ LLM
    for label in llm_labels:
        if label in label_scores:
            label_scores[label] += llm_weight
        else:
            label_scores[label] = llm_weight

    label_with_scores = [(label, score) for label, score in label_scores.items()]
    scores = [score for _, score in label_with_scores]
    normalized_scores = softmax(scores)
    result = [(label, score) for (label, _), score in zip(label_with_scores, normalized_scores)]
    return result