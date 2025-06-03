#!/usr/bin/env python3
"""
OneDrive Indexer Troubleshooting Script

This script demonstrates how to use the OneDriveIndexer independently
for debugging and troubleshooting purposes.
"""

import sys
import os
from datetime import datetime
from indexer import OneDriveIndexer

def test_authentication():
    """Test Microsoft Graph API authentication"""
    print("🔐 Testing Authentication...")
    indexer = OneDriveIndexer()
    
    token = indexer.get_access_token()
    if token:
        print("✅ Authentication successful")
        return True
    else:
        print("❌ Authentication failed")
        return False

def test_university_folder():
    """Test finding the University folder"""
    print("\n📁 Testing University Folder Discovery...")
    indexer = OneDriveIndexer()
    
    folder = indexer.find_university_folder()
    if folder:
        print(f"✅ University folder found: {folder['name']} (ID: {folder['id']})")
        return True
    else:
        print("❌ University folder not found")
        return False

def test_indexing():
    """Test the indexing process"""
    print("\n📊 Testing Indexing Process...")
    indexer = OneDriveIndexer()
    
    success = indexer.build_index(force_rebuild=True)
    if success:
        stats = indexer.get_stats()
        print(f"✅ Indexing successful:")
        print(f"   📁 Folders: {stats['total_folders']}")
        print(f"   📄 Files: {stats['total_files']}")
        print(f"   💾 Size: {stats['total_size'] / (1024*1024*1024):.2f} GB")
        return True
    else:
        print("❌ Indexing failed")
        return False

def test_cache_loading():
    """Test loading cached index"""
    print("\n🗂️ Testing Cache Loading...")
    indexer = OneDriveIndexer()
    
    try:
        indexer.load_cached_index()
        stats = indexer.get_stats()
        print(f"✅ Cache loaded successfully:")
        print(f"   📊 Paths: {stats['total_paths']}")
        print(f"   🕒 Last updated: {stats['last_updated']}")
        return True
    except Exception as e:
        print(f"❌ Cache loading failed: {e}")
        return False

def test_folder_browsing():
    """Test folder browsing functionality"""
    print("\n🧭 Testing Folder Browsing...")
    indexer = OneDriveIndexer()
    
    # Load existing index
    indexer.load_cached_index()
    
    # Test root folder
    root_contents = indexer.get_folder_contents('root')
    print(f"✅ Root folder contains {len(root_contents)} items")
    
    # Show first few items
    for i, item in enumerate(root_contents[:5]):
        icon = "📁" if item['type'] == 'folder' else "📄"
        print(f"   {icon} {item['name']}")
    
    if len(root_contents) > 5:
        print(f"   ... and {len(root_contents) - 5} more items")
    
    return len(root_contents) > 0

def test_search():
    """Test search functionality"""
    print("\n🔍 Testing Search Functionality...")
    indexer = OneDriveIndexer()
    
    # Load existing index
    indexer.load_cached_index()
    
    # Test search
    results = indexer.search_files('pdf')
    print(f"✅ Found {len(results)} PDF files")
    
    # Show first few results
    for i, result in enumerate(results[:3]):
        print(f"   📄 {result['name']} (in {result.get('folder_path', 'unknown')})")
    
    return len(results) > 0

def main():
    """Run all tests"""
    print("🧪 OneDrive Indexer Troubleshooting\n")
    print("="*50)
    
    tests = [
        ("Authentication", test_authentication),
        ("University Folder", test_university_folder),
        ("Cache Loading", test_cache_loading),
        ("Folder Browsing", test_folder_browsing),
        ("Search", test_search),
        ("Full Indexing", test_indexing),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*50)
    print("📋 Test Summary:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The indexer is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())
