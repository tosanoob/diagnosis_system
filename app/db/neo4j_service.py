"""
Cung cấp dịch vụ Neo4j cho việc truy vấn đồ thị tri thức y khoa
"""
from typing import List, Dict
from neo4j import GraphDatabase
from app.core.config import settings
from app.core.logging import logger

class Neo4jService:
    def __init__(self,
                 neo4j_uri=None, 
                 neo4j_user=None, 
                 neo4j_password=None, 
                 neo4j_db=None):
        """
        Khởi tạo service truy vấn Neo4j
        
        Args:
            neo4j_uri: URI Neo4j
            neo4j_user: Username Neo4j
            neo4j_password: Password Neo4j
            neo4j_db: Tên database Neo4j
        """
        # Load thông tin kết nối từ settings
        self.neo4j_uri = neo4j_uri or settings.NEO4J_URI
        self.neo4j_user = neo4j_user or settings.NEO4J_USERNAME
        self.neo4j_password = neo4j_password or settings.NEO4J_PASSWORD
        self.neo4j_db = neo4j_db or settings.NEO4J_DATABASE
        self.neo4j_driver = None
        
        # Định nghĩa các entity type và relation
        self.entity_types = {
            'Disease',
            'Cause',
            'Symptom',
            'Treatment',
            'Diagnosis',
            'Prevention',
            'Anatomy',
            'Complication',
            'Contraindication'
        }
        
        self.relationships = {
            'HAS_SYMPTOM': {'subject': 'Disease', 'object': 'Symptom'},
            'CAUSED_BY': {'subject': 'Disease', 'object': 'Cause'},
            'RISK_FACTOR': {'subject': 'Disease', 'object': 'Cause'},
            'TREATED_WITH': {'subject': 'Disease', 'object': 'Treatment'},
            'DIAGNOSED_BY': {'subject': 'Disease', 'object': 'Diagnosis'},
            'PREVENTED_BY': {'subject': 'Disease', 'object': 'Prevention'},
            'AFFECTS': {'subject': 'Disease', 'object': 'Anatomy'},
            'COMPLICATION_OF': {'subject': 'Disease', 'object': 'Complication'},
            'CONTRAINDICATES': {'subject': 'Disease', 'object': 'Contraindication'},
        }
        
        # Tự động kết nối khi khởi tạo
        self.connect_neo4j()
        
    def connect_neo4j(self):
        """Kết nối đến Neo4j"""
        try:
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Kiểm tra kết nối
            self.neo4j_driver.verify_connectivity()
            logger.app_info(f"Kết nối thành công đến Neo4j: {self.neo4j_uri}")
            
            return True
        except Exception as e:
            logger.error(f"Lỗi kết nối Neo4j: {str(e)}")
            return False
    
    def close(self):
        """Đóng kết nối với Neo4j"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            logger.app_info("Đã đóng kết nối Neo4j")
    
    def query_disease_symptoms(self, disease_query: str, limit: int = None) -> List[Dict]:
        """
        Tìm các triệu chứng của một bệnh cụ thể
        
        Args:
            disease_query: Tên bệnh hoặc từ khóa tìm kiếm
            limit: Số lượng kết quả trả về
            
        Returns:
            Danh sách các triệu chứng của bệnh
        """
        
        # Query Neo4j để lấy các triệu chứng
        try:
            with self.neo4j_driver.session(database=self.neo4j_db) as session:
                query = """
                MATCH (d:Disease {id: $disease_id})-[:HAS_SYMPTOM]->(s:Symptom)
                RETURN d.name AS Disease, s.name AS Symptom
                """
                if limit:
                    query += f"LIMIT {limit}"
                
                result = session.run(query, disease_id=disease_query, limit=limit)
                symptoms = [{"disease": record["Disease"], "symptom": record["Symptom"]} 
                           for record in result]
                return symptoms
        except Exception as e:
            logger.error(f"Lỗi khi query triệu chứng của bệnh: {str(e)}")
            return []
    
    def query_disease_causes(self, disease_query: str, limit: int = None) -> Dict:
        """
        Tìm các nguyên nhân của một bệnh cụ thể
        
        Args:
            disease_query: Tên bệnh hoặc từ khóa tìm kiếm
            limit: Số lượng kết quả trả về
            
        Returns:
            Danh sách các nguyên nhân của bệnh
        """
        
        # Query Neo4j để lấy các nguyên nhân
        try:
            with self.neo4j_driver.session(database=self.neo4j_db) as session:
                query = """
                MATCH (d:Disease {id: $disease_id})-[:CAUSED_BY]->(c:Cause)
                RETURN d.name AS Disease, c.name AS Cause
                """
                if limit:
                    query += f"LIMIT {limit}"
                
                result = session.run(query, disease_id=disease_query, limit=limit)
                causes = [{"disease": record["Disease"], "cause": record["Cause"]} 
                         for record in result]
                # Thêm các yếu tố rủi ro
                query_risk = """
                MATCH (d:Disease {id: $disease_id})-[:RISK_FACTOR]->(c:Cause)
                RETURN d.name AS Disease, c.name AS RiskFactor
                """
                if limit:
                    query_risk += f"LIMIT {limit}"
                
                result = session.run(query_risk, disease_id=disease_query, limit=limit)
                risk_factors = [{"disease": record["Disease"], "risk_factor": record["RiskFactor"]} 
                               for record in result]
                
                return {"causes": causes, "risk_factors": risk_factors}
        except Exception as e:
            logger.error(f"Lỗi khi query nguyên nhân của bệnh: {str(e)}")
            return {"causes": [], "risk_factors": []}
    
    def query_disease_affected_anatomy(self, disease_query: str, limit: int = None) -> List[Dict]:
        """
        Tìm các bộ phận cơ thể bị ảnh hưởng bởi một bệnh cụ thể
        
        Args:
            disease_query: Tên bệnh hoặc từ khóa tìm kiếm
            limit: Số lượng kết quả trả về
            
        Returns:
            Danh sách các bộ phận cơ thể bị ảnh hưởng
        """
        # Query Neo4j để lấy các bộ phận cơ thể bị ảnh hưởng
        try:
            with self.neo4j_driver.session(database=self.neo4j_db) as session:
                query = """
                MATCH (d:Disease {id: $disease_id})-[:AFFECTS]->(a:Anatomy)
                RETURN d.name AS Disease, a.name AS Anatomy
                """
                if limit:
                    query += f"LIMIT {limit}"
                
                result = session.run(query, disease_id=disease_query, limit=limit)
                anatomy = [{"disease": record["Disease"], "anatomy": record["Anatomy"]} 
                          for record in result]
                
                return anatomy
        except Exception as e:
            logger.error(f"Lỗi khi query bộ phận cơ thể bị ảnh hưởng: {str(e)}")
            return []
    
    def query_diseases_by_symptom(self, symptom_query: str | list[str], limit: int = None) -> List[Dict]:
        """
        Tìm các bệnh có triệu chứng cụ thể
        
        Args:
            symptom_query: Tên triệu chứng hoặc từ khóa tìm kiếm
            limit: Số lượng kết quả trả về
            
        Returns:
            Danh sách các bệnh có triệu chứng này
        """
        # Query Neo4j để lấy các bệnh có triệu chứng này
        try:
            if isinstance(symptom_query, list):
                symptom_keys = symptom_query
            else:
                symptom_keys = [symptom_query]
                
            with self.neo4j_driver.session(database=self.neo4j_db) as session:
                diseases = []
                for symptom_key in symptom_keys:
                    query = """
                    MATCH (s:Symptom {id: $symptom_id})<-[:HAS_SYMPTOM]-(d:Disease)
                    RETURN d.name AS Disease, s.name AS Symptom
                    """
                    if limit:
                        query += f"LIMIT {limit}"
                
                    result = session.run(query, symptom_id=symptom_key, limit=limit)
                    diseases.extend([{"disease": record["Disease"], "symptom": record["Symptom"]} 
                               for record in result])
                
                return diseases
        except Exception as e:
            logger.error(f"Lỗi khi query bệnh theo triệu chứng: {str(e)}")
            return []
    
    def query_diseases_by_anatomy(self, anatomy_query: str, limit: int = None) -> List[Dict]:
        """
        Tìm các bệnh ảnh hưởng đến một bộ phận cơ thể cụ thể
        
        Args:
            anatomy_query: Tên bộ phận cơ thể hoặc từ khóa tìm kiếm
            limit: Số lượng kết quả trả về
            
        Returns:
            Danh sách các bệnh ảnh hưởng đến bộ phận cơ thể này
        """
        # Query Neo4j để lấy các bệnh ảnh hưởng đến bộ phận cơ thể này
        try:
            with self.neo4j_driver.session(database=self.neo4j_db) as session:
                query = """
                MATCH (a:Anatomy {id: $anatomy_id})<-[:AFFECTS]-(d:Disease)
                RETURN d.name AS Disease, a.name AS Anatomy
                """
                if limit:
                    query += f"LIMIT {limit}"
                
                result = session.run(query, anatomy_id=anatomy_query, limit=limit)
                diseases = [{"disease": record["Disease"], "anatomy": record["Anatomy"]} 
                           for record in result]
                
                return diseases
        except Exception as e:
            logger.error(f"Lỗi khi query bệnh theo bộ phận cơ thể: {str(e)}")
            return []
    
    def diagnose_disease_context(self, symptoms, affected_anatomy):
        """
        Chẩn đoán bệnh dựa trên triệu chứng và bộ phận cơ thể bị ảnh hưởng
        
        Args:
            symptoms: Danh sách các triệu chứng và metadata
            affected_anatomy: Danh sách các bộ phận cơ thể bị ảnh hưởng và metadata
            
        Returns:
            Danh sách các bệnh có thể có
        """
        results = []
        try:
            for symptom_key, symptom_matches in symptoms.items():
                if not symptom_matches:
                    continue
                for match in symptom_matches:
                    disease_by_symptoms = self.query_diseases_by_symptom(
                        match["entities"], limit=5)
                    results.extend(disease_by_symptoms)
                    
            for anatomy_key, anatomy_matches in affected_anatomy.items():
                if not anatomy_matches:
                    continue
                for match in anatomy_matches:
                    disease_by_anatomy = self.query_diseases_by_anatomy(
                        match["entities"], limit=5)
                    results.extend(disease_by_anatomy)
                    
            return results
        except Exception as e:
            logger.error(f"Lỗi khi chẩn đoán bệnh: {str(e)}")
            return []

# Khởi tạo instance với thông tin kết nối từ cấu hình
neo4j_instance = Neo4jService() 