"""
Cung cấp dịch vụ ChromaDB cho việc lưu trữ và truy vấn các embeddings
"""
from chromadb import PersistentClient, Documents, Embeddings, EmbeddingFunction
from app.services.llm_service import embedding_request
from app.services.image_service import encode_base64_images
from app.core.config import settings
from app.core.logging import logger
import traceback
from typing import Literal

class BGEM3EmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.embedding_function = embedding_request

    def __call__(self, input: Documents) -> Embeddings:
        return self.embedding_function(input)

class ImageEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.embedding_function = encode_base64_images

    def __call__(self, input: Documents) -> Embeddings:
        return self.embedding_function(input)

class ChromaDBService:
    def __init__(self, path: str):
        self.client = PersistentClient(path=path)
        try:
            self.keyword_collection = self.client.get_or_create_collection(
                settings.ENTITY_COLLECTION, 
                embedding_function=BGEM3EmbeddingFunction(),
                metadata={"hnsw:space": "ip"}
                )
            self.document_collection = self.client.get_or_create_collection(
                settings.DOCUMENT_COLLECTION, 
                embedding_function=BGEM3EmbeddingFunction(),
                metadata={"hnsw:space": "ip"}
                )
            self.image_caption_collection = self.client.get_or_create_collection(
                settings.IMAGE_COLLECTION, 
                embedding_function=ImageEmbeddingFunction(),
                metadata={"hnsw:space": "ip"}
                )
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo ChromaDB: {str(e)}")
            traceback.print_exc()
        
    def retrieve_keyword(self, keywords: str | list[str],
                         n_results: int = 3,
                         threshold: float = 0.2,
                         entity_type: str = None) -> list[str]:
        """
        Hàm tìm từ khóa chính xác từ danh sách từ khóa do LLM trả về
        Args:
            keywords: Các từ khóa do LLM trả về
            n_results: Số kết quả trả về
            threshold: Ngưỡng độ tương đồng
            entity_type: Loại entity cần tìm
        Returns:
            list[str]: Danh sách từ khóa có thật ở Neo4j
        """
        if isinstance(keywords, str):
            keywords = [keywords]
        query_results = self.keyword_collection.query(
            query_texts=keywords,
            n_results=n_results*9)
        results = {}
        for i, query_word in enumerate(keywords):
            keyword_result = query_results["documents"][i]
            keyword_metadata = query_results["metadatas"][i]
            keyword_distance = query_results["distances"][i]
            results[query_word] = []
            for index, item in enumerate(keyword_result):
                if entity_type:
                    if entity_type not in keyword_metadata[index]["type"]:
                        continue
                if keyword_distance[index] > threshold:
                    continue
                results[query_word].append({
                    "entities": query_results["documents"][i][index],
                    "metadata": query_results["metadatas"][i][index],
                    "distance": query_results["distances"][i][index]
                })
                if len(results[query_word]) >= n_results:
                    break
        
        return results
    
    def retrieve_document(self, query: str,
                          n_results: int = 3,
                          threshold: float = 0.5) -> dict:
        """
        Hàm tìm tài liệu mô tả gần nhất với mô tả do LLM trả về
        Args:
            query: Mô tả do LLM trả về
            n_results: Số kết quả trả về
            threshold: Ngưỡng độ tương đồng
        Returns:
            dict: Top n tài liệu liên quan với ngưỡng distance
        """
        if isinstance(query, str):
            query = [query]
        query_results = self.document_collection.query(
            query_texts=query,
            n_results=n_results)
        results = {
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        for i, query_text in enumerate(query):
            document_result = query_results["documents"][i]
            document_metadata = query_results["metadatas"][i]
            document_distance = query_results["distances"][i]
            for index, item in enumerate(document_result):
                if document_distance[index] > threshold:
                    continue
                results["documents"].append(item)
                results["metadatas"].append(document_metadata[index])
                results["distances"].append(document_distance[index])
        return results

    def retrieve_image_info(self, image_base64: str | list[str],
                            n_results: int = 5,
                            threshold: float = 0.5,
                            filter_labels: str |list[str] = None) -> dict:
        """
        Hàm tìm ảnh gần nhất với hình ảnh gửi, trả về hình ảnh tương tự, thông tin hình ảnh.
        Args:
            image_base64: Hình ảnh được mã hóa dưới dạng base64
            n_results: Số kết quả trả về
            threshold: Ngưỡng độ tương đồng
            filter_labels: Danh sách các label cần lọc, nếu None sẽ lấy ra tất cả
        Returns:
            dict: Top n ảnh tương tự với ngưỡng distance
        """
        try:
            
            if isinstance(image_base64, str):
                image_base64 = [image_base64]
                
            # Mã hóa ảnh thành embeddings
            embeddings = encode_base64_images(image_base64)
            if embeddings is None:
                logger.error("Failed to encode images")
                return []
                
            condition = {"is_disabled": False}
            if filter_labels:
                if isinstance(filter_labels, str):
                    filter_labels = [filter_labels]
                if len(filter_labels) == 1:
                    condition = {"$and": [
                        {"is_disabled": False},
                        {"label": filter_labels[0]}
                    ]}
                else:
                    condition = {"$and": [
                        {"is_disabled": False},
                        {"$or": [{"label": label} for label in filter_labels]}
                    ]}
                    
            # Truy vấn ChromaDB với embeddings
            query_results = self.image_caption_collection.query(
                query_embeddings=embeddings,
                n_results=n_results,
                where=condition
            )
                
            # Xử lý kết quả
            final_results = []
            for i, item in enumerate(query_results["documents"]):
                for k in range(len(item)):
                    if query_results["distances"][i][k] > threshold:
                        continue
                    final_results.append({
                        'image_id': query_results["ids"][i][k],
                        'distance': query_results["distances"][i][k],
                        **query_results["metadatas"][i][k]
                    })
            return final_results
        except ImportError as e:
            logger.error(f"Lỗi khi import encode_base64_images: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Lỗi khi truy vấn hình ảnh: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    def add_image_caption(self, image_id: list[str], metadata: list[dict], embeddings: list[list[float]]):
        """
        Thêm thông tin hình ảnh vào ChromaDB
        Args:
            image_id: ID của hình ảnh
            metadata: Thông tin hình ảnh
            embeddings: Embeddings của hình ảnh
        """
        self.image_caption_collection.add(
            ids=image_id,
            embeddings=embeddings,
            metadatas=metadata
        )

    def create_mapping(self, domain_id: str, domain_disease_id: str, label_id: str, label: str):
        """
        Tạo mapping mới giữa domain_id. và bệnh chuẩn
        Args:
            domain_id: ID của domain
            domain_disease_id: ID của bệnh trong domain
            label_id: ID của bệnh chuẩn ánh xạ tới
            label: Tên của bệnh chuẩn ánh xạ tới
        """
        update_records = self.image_caption_collection.get(
            where={"$and": [{"domain_id": domain_id}, {"domain_disease_id": domain_disease_id}]},
            include=["metadatas"]
        )
        ids = update_records.get("ids")
        metadatas = update_records.get("metadatas")
        if len(update_records) > 0:
            for item in metadatas:
                item["label_id"] = label_id
                item["label"] = label
                item["is_disabled"] = False
        self.image_caption_collection.update(
            ids=ids,
            metadatas=metadatas
        )

    def delete_mapping(self, domain_id: str, domain_disease_id: str):
        """
        Xóa mapping giữa domain_id và bệnh trong domain (xóa mềm và tạm thời disable các ảnh này)
        Args:
            domain_id: ID của domain
            domain_disease_id: ID của bệnh trong domain
        """
        update_records = self.image_caption_collection.get(
            where={"$and": [{"domain_id": domain_id}, {"domain_disease_id": domain_disease_id}]},
            include=["metadatas"]
        )
        ids = update_records.get("ids")
        metadatas = update_records.get("metadatas")
        if len(ids) > 0:
            for item in metadatas:
                item["is_disabled"] = True
                item["label"] = ""
                item["label_id"] = ""
            self.image_caption_collection.update(
                ids=ids,
                metadatas=metadatas
            )

    def modify_state_standard_disease(self, label_id: str, label: str, option: Literal["enable", "disable"] = "enable"):
        """
        Cập nhật lại trạng thái enable/disable của bệnh chuẩn
        Args:
            label_id: ID của bệnh chuẩn
            label: Tên của bệnh chuẩn
        """
        is_disabled = True if option == "disable" else False
        update_records = self.image_caption_collection.get(
            where={"$and": [{"label":label}, {"label_id": label_id}]},
            include=["metadatas"]
        )
        ids = update_records.get("ids")
        metadatas = update_records.get("metadatas")
        if len(ids) > 0:
            for item in metadatas:
                item["is_disabled"] = is_disabled
                item["label"] = ""
                item["label_id"] = ""
            self.image_caption_collection.update(
                ids=ids,
                metadatas=metadatas
            )

    def delete_entire_domain(self, domain_id: str):
        """
        Xóa toàn bộ dữ liệu của domain phụ cụ thể
        Args:
            domain_id: ID của domain
        """
        self.image_caption_collection.delete(where={"domain_id": domain_id})

# Khởi tạo instance với đường dẫn từ cấu hình
chromadb_instance = ChromaDBService(settings.CHROMA_DATA_PATH) 