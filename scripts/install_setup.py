#!/usr/bin/env python3
"""
Installation and setup script for Gmail Email Classification System
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def run_command(command, description):
    """Run a shell command with error handling"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    print(f"Current Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print("✅ Python version is compatible")
    return True

def install_dependencies():
    """Install required Python packages"""
    print_header("Installing Dependencies")
    
    # Check if pip is available
    if not shutil.which("pip"):
        print("❌ pip is not installed. Please install pip first.")
        return False
    
    # Install requirements
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"❌ Requirements file not found: {requirements_file}")
        return False
    
    return run_command(
        f"pip install -r {requirements_file}",
        "Installing Python dependencies"
    )

def setup_environment():
    """Setup environment configuration"""
    print_header("Setting Up Environment")
    
    project_root = Path(__file__).parent.parent
    env_example = project_root / ".env.example"
    env_file = project_root / ".env"
    
    if not env_example.exists():
        print("❌ .env.example file not found")
        return False
    
    if env_file.exists():
        print("⚠️  .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            print("📋 Keeping existing .env file")
            return True
    
    try:
        shutil.copy2(env_example, env_file)
        print(f"✅ Created .env file from template")
        print(f"📝 Please edit {env_file} with your API keys and settings")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def check_credentials():
    """Check for Gmail API credentials"""
    print_header("Checking Gmail API Credentials")
    
    project_root = Path(__file__).parent.parent
    credentials_file = project_root / "credentials.json"
    
    if credentials_file.exists():
        print("✅ credentials.json found")
        return True
    else:
        print("❌ credentials.json not found")
        print("\n📋 To get Gmail API credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable the Gmail API")
        print("4. Create OAuth 2.0 Client ID credentials")
        print("5. Download as 'credentials.json' and place in project root")
        print("\n⚠️  You can continue setup, but authentication will fail until credentials are added")
        return False

def create_directories():
    """Create necessary directories"""
    print_header("Creating Directories")
    
    project_root = Path(__file__).parent.parent
    directories = ["logs", "scripts"]
    
    for dir_name in directories:
        dir_path = project_root / dir_name
        try:
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Directory created/verified: {dir_name}")
        except Exception as e:
            print(f"❌ Failed to create directory {dir_name}: {e}")
            return False
    
    return True

def test_imports():
    """Test if all required modules can be imported"""
    print_header("Testing Module Imports")
    
    required_modules = [
        "agno",
        "openai",
        "google.auth",
        "google_auth_oauthlib",
        "googleapiclient",
        "dotenv"
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        return False
    
    print("✅ All required modules imported successfully")
    return True

def run_connection_test():
    """Run the connection test script"""
    print_header("Testing System Configuration")
    
    test_script = Path(__file__).parent / "test_connection.py"
    
    if not test_script.exists():
        print("⚠️  Connection test script not found, skipping test")
        return True
    
    print("🔄 Running connection test...")
    print("Note: This will require Gmail authentication if credentials are available\n")
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    original_cwd = os.getcwd()
    
    try:
        os.chdir(project_root)
        result = subprocess.run([sys.executable, str(test_script)], 
                              capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    finally:
        os.chdir(original_cwd)

def print_next_steps(all_checks_passed):
    """Print next steps for the user"""
    print_header("Setup Complete")
    
    if all_checks_passed:
        print("🎉 Installation completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Edit .env file with your OpenAI API key")
        print("2. Download credentials.json from Google Cloud Console (if not done)")
        print("3. Run: python gmail_setup_agent.py")
        print("4. Run: python gmail_realtime_agent.py")
        
        print("\n🔧 Useful Commands:")
        print("• Test connection: python scripts/test_connection.py")
        print("• Setup agent: python gmail_setup_agent.py")
        print("• Real-time agent: python gmail_realtime_agent.py")
        print("• Help: python gmail_realtime_agent.py --help")
    
    else:
        print("⚠️  Installation completed with some issues")
        print("\n🔧 Please fix the following before proceeding:")
        print("• Install missing dependencies")
        print("• Add Gmail API credentials")
        print("• Configure environment variables")
        print("\nThen run: python scripts/test_connection.py")

def main():
    """Main installation function"""
    print("🚀 Gmail Email Classification System - Setup")
    print("This script will install dependencies and configure the system")
    
    # Run all setup steps
    steps = [
        ("Python Version Check", check_python_version),
        ("Install Dependencies", install_dependencies),
        ("Setup Environment", setup_environment),
        ("Create Directories", create_directories),
        ("Check Credentials", check_credentials),
        ("Test Imports", test_imports),
    ]
    
    results = []
    
    for step_name, step_func in steps:
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {e}")
            results.append((step_name, False))
    
    # Optional connection test
    print("\n" + "="*60)
    response = input("Run connection test now? (requires Gmail credentials) [y/N]: ").lower()
    if response == 'y':
        test_result = run_connection_test()
        results.append(("Connection Test", test_result))
    
    # Summary
    print("\n" + "="*60)
    print("📊 Setup Results:")
    
    all_required_passed = True
    for step_name, passed in results:
        # Credentials check is not required for setup to succeed
        is_required = step_name != "Check Credentials"
        status = "✅ PASSED" if passed else "❌ FAILED"
        required_text = "" if is_required else " (optional)"
        print(f"  {step_name}{required_text}: {status}")
        
        if not passed and is_required:
            all_required_passed = False
    
    print_next_steps(all_required_passed)
    
    return all_required_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)