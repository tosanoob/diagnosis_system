"""
Cung cấp dịch vụ ChromaDB cho việc lưu trữ và truy vấn các embeddings
"""
from chromadb import PersistentClient, Documents, Embeddings, EmbeddingFunction
from app.services.llm_service import embedding_request
from app.core.config import settings
from app.constants.enums import EntityType
from app.core.logging import logger
import traceback

class BGEM3EmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.embedding_function = embedding_request

    def __call__(self, input: Documents) -> Embeddings:
        return self.embedding_function(input)

class ChromaDBService:
    def __init__(self, path: str):
        self.client = PersistentClient(path=path)
        try:
            self.keyword_collection = self.client.get_collection(
                "entity-collection-ip", 
                embedding_function=BGEM3EmbeddingFunction())
            self.document_collection = self.client.get_collection(
                "document-collection-ip", 
                embedding_function=BGEM3EmbeddingFunction())
            self.image_caption_collection = self.client.get_collection(
                "image-caption-collection-ip", 
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
                            threshold: float = 0.5) -> dict:
        """
        Hàm tìm ảnh gần nhất với hình ảnh gửi, trả về hình ảnh tương tự, thông tin hình ảnh.
        Args:
            image_base64: Hình ảnh được mã hóa dưới dạng base64
            n_results: Số kết quả trả về
            threshold: Ngưỡng độ tương đồng
        Returns:
            dict: Top n ảnh tương tự với ngưỡng distance
        """
        try:
            # Import trong hàm để tránh import circular
            from app.services.image_service import encode_base64_images
            
            if isinstance(image_base64, str):
                image_base64 = [image_base64]
                
            # Mã hóa ảnh thành embeddings
            embeddings = encode_base64_images(image_base64)
            if embeddings is None:
                logger.error("Failed to encode images")
                return []
                
            # Truy vấn ChromaDB với embeddings
            query_results = self.image_caption_collection.query(
                query_embeddings=embeddings,
                n_results=n_results)
                
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

# Khởi tạo instance với đường dẫn từ cấu hình
chromadb_instance = ChromaDBService(settings.CHROMA_DATA_PATH) 