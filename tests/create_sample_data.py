#!/usr/bin/env python3
"""
Script tạo sample metadata và crossmap files để test
"""
import json
import os
from pathlib import Path

def create_sample_metadata():
    """Tạo sample metadata cho SkinCAP"""
    sample_metadata = [
        {"label": "acne", "index": 0},
        {"label": "melanoma", "index": 1},
        {"label": "basal cell carcinoma", "index": 2},
        {"label": "squamous cell carcinoma", "index": 3},
        {"label": "seborrheic dermatitis", "index": 4}
    ]
    
    # Extend để có đủ samples
    extended_metadata = []
    for i in range(1000):
        base_item = sample_metadata[i % len(sample_metadata)]
        extended_metadata.append({
            "label": base_item["label"],
            "index": i
        })
    
    with open("metadata-skincap.json", "w", encoding="utf-8") as f:
        json.dump(extended_metadata, f, ensure_ascii=False, indent=2)
    
    print("✅ Created metadata-skincap.json with 1000 sample entries")

def create_sample_crossmap():
    """Tạo sample crossmap từ SkinCAP labels sang standard labels"""
    sample_crossmap = {
        "acne": "TRỨNG CÁ (Acne)",
        "melanoma": "UNG THƯ TẾ BÀO HẮC TỐ (Malignant melanoma)",
        "basal cell carcinoma": "UNG THƯ TẾ BÀO ĐÁY (Basal cell carcinoma - BCC)",
        "squamous cell carcinoma": "UNG THƯ TẾ BÀO VẢY (Squamous cell carcinoma-SCC)",
        "seborrheic dermatitis": "VIÊM DA DẦU (Seborrheic Dermatitis)",
        "psoriasis": "BỆNH VẢY NẾN (Psoriasis)",
        "eczema": "VIÊM DA CƠ ĐỊA (Atopic dermatitis)",
        "vitiligo": "BỆNH BẠCH BIẾN (Vitiligo)",
        "wart": "BỆNH HẠT CƠM (Warts)",
        "folliculitis": "VIÊM NANG LÔNG (Folliculitis)"
    }
    
    with open("crossmap_SkinCAP.json", "w", encoding="utf-8") as f:
        json.dump(sample_crossmap, f, ensure_ascii=False, indent=2)
    
    print("✅ Created crossmap_SkinCAP.json with sample mappings")

def main():
    """Main function"""
    print("🔧 Creating sample data files for diagnosis pipeline test")
    print("="*60)
    
    # Kiểm tra xem files đã tồn tại chưa
    metadata_exists = Path("metadata-skincap.json").exists()
    crossmap_exists = Path("crossmap_SkinCAP.json").exists()
    
    if metadata_exists and crossmap_exists:
        print("ℹ️  Both files already exist:")
        print("  - metadata-skincap.json ✅")
        print("  - crossmap_SkinCAP.json ✅")
        print("\n⚠️  Delete these files if you want to recreate them")
        return
    
    # Tạo files nếu chưa có
    if not metadata_exists:
        create_sample_metadata()
    else:
        print("ℹ️  metadata-skincap.json already exists")
    
    if not crossmap_exists:
        create_sample_crossmap()
    else:
        print("ℹ️  crossmap_SkinCAP.json already exists")
    
    print("\n✅ Sample data files ready!")
    print("🚀 You can now run the diagnosis pipeline test:")
    print("   python run_diagnosis_pipeline_test.py")

if __name__ == "__main__":
    main() 