#!/usr/bin/env python3
"""
Simple Google Drive Authentication Test
Diagnoses authentication issues and tests basic Google Drive API access
"""

import os
import sys
import pickle
from pathlib import Path

# Load environment variables from .env file manually
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✅ Loaded environment variables from .env file")
    else:
        print(f"⚠️  No .env file found")

# Load the .env file
load_env_file()

def test_environment_variables():
    """Test if required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    
    client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
    
    print(f"   GOOGLE_OAUTH_CLIENT_ID: {'✓ SET' if client_id else '✗ MISSING'}")
    print(f"   GOOGLE_OAUTH_CLIENT_SECRET: {'✓ SET' if client_secret else '✗ MISSING'}")
    
    if not client_id or not client_secret:
        print("❌ Environment variables are missing!")
        print("   Run: export GOOGLE_OAUTH_CLIENT_ID='your-client-id'")
        print("   Run: export GOOGLE_OAUTH_CLIENT_SECRET='your-client-secret'")
        return False
    
    print("✅ Environment variables are set")
    return True

def test_token_file():
    """Test if token file exists and is readable"""
    print("\n🔍 Checking Token File...")
    
    token_file = 'google_drive_token.pickle'
    token_path = Path(token_file)
    
    if not token_path.exists():
        print(f"❌ Token file '{token_file}' does not exist")
        print("   You need to complete the OAuth flow to create this file")
        return False
    
    try:
        with open(token_file, 'rb') as f:
            credentials = pickle.load(f)
        
        print(f"✅ Token file exists and is readable")
        print(f"   Token valid: {'✓' if credentials.valid else '✗'}")
        print(f"   Token expired: {'✓' if credentials.expired else '✗'}")
        print(f"   Has refresh token: {'✓' if credentials.refresh_token else '✗'}")
        
        return credentials.valid or (credentials.refresh_token and credentials.expired)
        
    except Exception as e:
        print(f"❌ Token file is corrupted: {e}")
        return False

def test_google_drive_service():
    """Test Google Drive service initialization"""
    print("\n🔍 Testing Google Drive Service...")
    
    try:
        # Import here to avoid issues if modules aren't available
        sys.path.append('.')
        from carousel_engine.services.google_drive import GoogleDriveService
        
        # Create service instance
        service = GoogleDriveService()
        
        # Test service initialization
        service._ensure_service_initialized()
        
        # Test a simple API call
        about_result = service.service.about().get(fields='user').execute()
        
        if about_result and 'user' in about_result:
            user_email = about_result['user'].get('emailAddress', 'unknown')
            print(f"✅ Google Drive service working!")
            print(f"   Authenticated as: {user_email}")
            return True
        else:
            print("❌ Google Drive API returned unexpected response")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import Google Drive service: {e}")
        return False
    except Exception as e:
        print(f"❌ Google Drive service failed: {e}")
        return False

def test_basic_api_access():
    """Test basic Google Drive API operations"""
    print("\n🔍 Testing Basic API Access...")
    
    try:
        sys.path.append('.')
        from carousel_engine.services.google_drive import GoogleDriveService
        
        service = GoogleDriveService()
        service._ensure_service_initialized()
        
        # Test listing files (simple query)
        results = service.service.files().list(
            pageSize=1,
            fields="files(id, name)"
        ).execute()
        
        if results is not None:
            files = results.get('files', [])
            print(f"✅ Basic API access working!")
            print(f"   Can access Drive files: {'✓' if files else 'Empty but accessible'}")
            return True
        else:
            print("❌ API returned None response")
            return False
            
    except Exception as e:
        print(f"❌ Basic API access failed: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("🚀 Google Drive Authentication Diagnostic Tool")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Environment Variables
    if test_environment_variables():
        tests_passed += 1
    
    # Test 2: Token File
    if test_token_file():
        tests_passed += 1
    
    # Test 3: Service Initialization
    if test_google_drive_service():
        tests_passed += 1
    
    # Test 4: Basic API Access
    if test_basic_api_access():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Google Drive authentication is working correctly.")
    elif tests_passed == 0:
        print("💥 All tests failed! You need to set up authentication from scratch.")
        print("   Run: python3 setup_google_oauth.py")
    else:
        print("⚠️  Some tests failed. Authentication is partially configured.")
        print("   Check the failed tests above for specific issues to resolve.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)