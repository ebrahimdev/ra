#!/usr/bin/env python3
"""
Test script for dual-collection vector DB functionality.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.services.vector_store_service import VectorStoreService
from src.utils.text_processing import create_fine_chunks, create_coarse_chunks

def test_dual_collections():
    """Test the dual-collection functionality."""
    print("Testing dual-collection vector DB functionality...")
    
    # Initialize vector store service
    vector_store = VectorStoreService()
    
    # Sample text for testing
    sample_text = """
    Machine learning has revolutionized the field of artificial intelligence. 
    Deep learning models, particularly neural networks, have achieved remarkable success in various domains. 
    Convolutional neural networks (CNNs) excel at image recognition tasks, while recurrent neural networks (RNNs) 
    are particularly effective for sequential data processing. Transformer architectures have further advanced 
    natural language processing capabilities, enabling models like BERT and GPT to understand and generate human-like text.
    
    The training process involves optimizing model parameters through backpropagation and gradient descent. 
    Data preprocessing is crucial for model performance, including normalization, augmentation, and feature engineering. 
    Regularization techniques such as dropout and weight decay help prevent overfitting and improve generalization.
    
    Evaluation metrics vary depending on the task. For classification, accuracy, precision, recall, and F1-score 
    are commonly used. For regression tasks, mean squared error and mean absolute error are typical metrics. 
    Cross-validation ensures robust model evaluation by testing on multiple data splits.
    """
    
    # Test fine chunking
    print("\n1. Testing fine chunking...")
    fine_chunks = create_fine_chunks(sample_text)
    print(f"Created {len(fine_chunks)} fine chunks:")
    for i, chunk in enumerate(fine_chunks):
        print(f"  Fine chunk {i+1}: {len(chunk)} chars, {chunk[:100]}...")
    
    # Test coarse chunking
    print("\n2. Testing coarse chunking...")
    coarse_chunks = create_coarse_chunks(sample_text)
    print(f"Created {len(coarse_chunks)} coarse chunks:")
    for i, chunk in enumerate(coarse_chunks):
        print(f"  Coarse chunk {i+1}: {len(chunk)} chars, {chunk[:100]}...")
    
    # Test ingestion
    print("\n3. Testing paper ingestion...")
    paper_metadata = {
        'title': 'Test Paper on Machine Learning',
        'authors': ['John Doe', 'Jane Smith'],
        'year': '2024',
        'arxiv_id': '2401.12345',
        'source': 'test'
    }
    
    success = vector_store.ingest_paper_text(sample_text, paper_metadata)
    print(f"Ingestion success: {success}")
    
    # Test collection stats
    print("\n4. Testing collection statistics...")
    stats = vector_store.get_collection_stats()
    print(f"Fine chunks: {stats.get('fine_chunks_count', 0)}")
    print(f"Coarse chunks: {stats.get('coarse_chunks_count', 0)}")
    print(f"Total documents: {stats.get('total_documents', 0)}")
    
    # Test searching fine collection
    print("\n5. Testing fine collection search...")
    fine_results = vector_store.search_collection("neural networks", k=2, collection_name="fine")
    print(f"Fine search results: {len(fine_results['results'])} found")
    for i, result in enumerate(fine_results['results']):
        print(f"  Result {i+1}: {result['similarity_score']:.3f} - {result['text'][:100]}...")
    
    # Test searching coarse collection
    print("\n6. Testing coarse collection search...")
    coarse_results = vector_store.search_collection("machine learning training", k=2, collection_name="coarse")
    print(f"Coarse search results: {len(coarse_results['results'])} found")
    for i, result in enumerate(coarse_results['results']):
        print(f"  Result {i+1}: {result['similarity_score']:.3f} - {result['text'][:100]}...")
    
    # Test combined search
    print("\n7. Testing combined search...")
    combined_results = vector_store.search_both_collections("deep learning", k_fine=1, k_coarse=1)
    print(f"Combined search results: {len(combined_results['results'])} found")
    for i, result in enumerate(combined_results['results']):
        print(f"  Result {i+1} ({result['collection']}): {result['similarity_score']:.3f} - {result['text'][:100]}...")
    
    print("\n✅ Dual-collection test completed successfully!")

if __name__ == "__main__":
    test_dual_collections() 