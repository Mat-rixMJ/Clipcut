"""
System requirements checker for ClipCut
Verifies all dependencies are installed correctly
"""
import subprocess
import sys


def check_command(command: str, name: str) -> bool:
    """Check if a command is available in PATH."""
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ {name}: {version}")
            return True
        else:
            print(f"❌ {name}: Command failed")
            return False
    except FileNotFoundError:
        print(f"❌ {name}: Not found in PATH")
        return False
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False


def check_python_package(package: str) -> bool:
    """Check if a Python package is installed."""
    try:
        __import__(package)
        print(f"✅ Python package: {package}")
        return True
    except ImportError:
        print(f"❌ Python package: {package} - Not installed")
        return False


def main():
    print("=" * 60)
    print("   ClipCut System Requirements Check")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # Check Python version
    print("🐍 Python Version:")
    python_version = sys.version.split()[0]
    major, minor = map(int, python_version.split('.')[:2])
    
    if major >= 3 and minor >= 10:
        print(f"✅ Python {python_version} (>= 3.10 required)")
    else:
        print(f"❌ Python {python_version} (>= 3.10 required)")
        all_ok = False
    
    print()
    
    # Check system commands
    print("🔧 System Tools:")
    all_ok &= check_command("ffmpeg", "FFmpeg")
    all_ok &= check_command("ffprobe", "FFprobe")
    all_ok &= check_command("yt-dlp", "yt-dlp")
    
    print()
    
    # Check Python packages
    print("📦 Python Packages:")
    packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
    ]
    
    for package in packages:
        all_ok &= check_python_package(package)
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✨ All requirements satisfied! You're ready to go!")
        print()
        print("Next steps:")
        print("1. Run: start_server.bat (Windows) or python -m uvicorn app.main:app")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Test: python scripts/test_pipeline.py")
    else:
        print("⚠️  Some requirements are missing!")
        print()
        print("Installation instructions:")
        print()
        print("FFmpeg:")
        print("  - Windows: Download from https://ffmpeg.org/download.html")
        print("  - Mac: brew install ffmpeg")
        print("  - Linux: sudo apt install ffmpeg")
        print()
        print("Python packages:")
        print("  pip install -r backend/requirements.txt")
    
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
