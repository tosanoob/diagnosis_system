import json
import os
import numpy as np
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

def get_document(disease_name):
    document_path = None
    print("Finding document for disease: ", disease_name)
    if disease_name == 'PEMPHIGUS':
        document_path = labels_to_folder['PEMPHIGUS']
    else:
        for item in labels_to_folder:
            if disease_name in item:
                document_path = labels_to_folder[item]
                break
    documents_files = os.listdir(document_path)
    documents_files = sorted(documents_files, key=lambda x: int(x.replace('.json','').split('_')[-1]))
    documents = []
    for d in documents_files:
        documents.append(
            json.load(open(os.path.join(document_path, d), 'r', encoding='utf-8'))['content']
        )
    return documents

def softmax(scores):
    exp_scores = [np.exp(score) for score in scores]
    sum_exp_scores = sum(exp_scores)
    return [exp_score / sum_exp_scores for exp_score in exp_scores]