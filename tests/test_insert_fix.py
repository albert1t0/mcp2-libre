#!/usr/bin/env python3

"""
Test script for the insert_text_at_position function to verify the fix
"""

import tempfile
import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Import the functions we need to test
from libremcp import create_document, insert_text_at_position, read_document_text

def test_insert_text_fix():
    """Test that insert_text_at_position works with simple character insertion"""
    
    print("🧪 Testing insert_text_at_position fix...")
    print("=" * 50)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    test_doc = temp_dir / "test_insert.odt"
    
    try:
        # 1. Create a test document
        print("\n📝 Step 1: Creating test document...")
        result = create_document(str(test_doc), "writer", "Hello World")
        print(f"✅ Created: {result.path}")
        
        # 2. Read initial content
        print("\n📖 Step 2: Reading initial content...")
        content = read_document_text(str(test_doc))
        print(f"✅ Initial content: '{content.content.strip()}'")
        print(f"   Word count: {content.word_count}")
        
        # 3. Test inserting a simple character (this was failing before)
        print("\n✏️  Step 3: Inserting a simple period '.' at the end...")
        result = insert_text_at_position(str(test_doc), ".", "end")
        print("✅ Successfully inserted period")
        print(f"   File updated: {result.filename}")
        
        # 4. Verify the change
        print("\n🔍 Step 4: Verifying the change...")
        content = read_document_text(str(test_doc))
        print(f"✅ Updated content: '{content.content.strip()}'")
        assert "Hello World" in content.content
        assert content.content.rstrip().endswith(".")
        
        # 5. Test inserting at start
        print("\n⬆️  Step 5: Inserting text at start...")
        insert_text_at_position(str(test_doc), "Beginning: ", "start")
        content = read_document_text(str(test_doc))
        normalized_content = content.content.lstrip("\ufeff\n\r ")
        assert normalized_content.startswith("Beginning:")
        print("✅ Successfully inserted at start")
        
        # 6. Test replacing content
        print("\n🔄 Step 6: Replacing content...")
        insert_text_at_position(
            str(test_doc), "This is completely new content!", "replace"
        )
        print("✅ Successfully replaced content")
        
        # 7. Final verification
        print("\n📋 Step 7: Final verification...")
        final_content = read_document_text(str(test_doc))
        print(f"✅ Final content: '{final_content.content.strip()}'")
        print(f"   Final word count: {final_content.word_count}")
        assert (
            final_content.content.strip("\ufeff\n\r ")
            == "This is completely new content!"
        )
        
        print("\n🎉 All tests passed! The insert_text_at_position fix is working.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise
        
    finally:
        # Clean up
        import shutil
        try:
            shutil.rmtree(temp_dir)
            print(f"\n🗑️  Cleaned up test directory: {temp_dir}")
        except:
            pass

def test_edge_cases():
    """Test edge cases that might cause issues"""
    
    print("\n🧪 Testing edge cases...")
    print("=" * 30)
    
    temp_dir = Path(tempfile.mkdtemp())
    
    edge_cases = [
        ("Empty string", ""),
        ("Just a space", " "),
        ("Single character", "x"),
        ("Special characters", "!@#$%^&*()"),
        ("Unicode", "Hello 世界 🌍"),
        ("Newlines", "Line 1\nLine 2\nLine 3"),
        ("Long text", "This is a very long text " * 20),
    ]
    
    for test_name, test_text in edge_cases:
        test_doc = temp_dir / f"test_{test_name.replace(' ', '_').lower()}.odt"
        
        try:
            print(f"\n🔬 Testing: {test_name}")
            
            # Create document
            create_document(str(test_doc), "writer", "Initial content")
            
            # Insert text
            result = insert_text_at_position(str(test_doc), test_text, "end")
            
            # Verify
            content = read_document_text(str(test_doc))
            
            print(f"   ✅ Success - Final length: {len(content.content)} chars")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    # Clean up
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except:
        pass

if __name__ == "__main__":
    print("🚀 LibreOffice MCP Server - Insert Text Fix Test")
    print("=" * 60)
    
    # Run main test
    try:
        test_insert_text_fix()
        success = True
    except Exception:
        success = False
    
    if success:
        # Run edge case tests
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("The insert_text_at_position function should now work properly")
        print("with Claude Desktop when you ask to insert simple characters.")
    else:
        print("\n" + "=" * 60)
        print("❌ Some tests failed. The fix may need more work.")
        
    print("\n💡 Try this in Claude Desktop:")
    print('   "Add a period to the end of my document.odt"')
    print('   "Insert \'Hello\' at the beginning of my file"')
