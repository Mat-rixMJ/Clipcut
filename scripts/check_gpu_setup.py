"""Check GPU dependencies and setup for ClipCut acceleration"""
import sys
import subprocess
from pathlib import Path

def check_pytorch_cuda():
    """Check if PyTorch with CUDA is installed and available"""
    print("\n" + "="*60)
    print("1. Checking PyTorch CUDA Support")
    print("="*60)
    
    try:
        import torch
        print(f"✓ PyTorch installed: {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            print(f"✓ CUDA available: YES")
            print(f"  - CUDA version: {torch.version.cuda}")
            print(f"  - GPU count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  - GPU {i}: {torch.cuda.get_device_name(i)}")
            return True
        else:
            print("✗ CUDA available: NO")
            print("  PyTorch is installed but without CUDA support")
            return False
    except ImportError:
        print("✗ PyTorch not installed")
        return False
    except Exception as e:
        print(f"✗ Error checking PyTorch: {e}")
        return False


def check_ffmpeg_hwaccel():
    """Check FFmpeg hardware acceleration support"""
    print("\n" + "="*60)
    print("2. Checking FFmpeg Hardware Acceleration")
    print("="*60)
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-hwaccels"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        hwaccels = result.stdout.strip().split('\n')[1:]  # Skip header
        print(f"✓ FFmpeg found, available hardware accelerators:")
        for acc in hwaccels:
            acc = acc.strip()
            if acc:
                print(f"  - {acc}")
        
        # Check for common ones
        has_cuda = any('cuda' in acc.lower() for acc in hwaccels)
        has_d3d11va = any('d3d11va' in acc.lower() for acc in hwaccels)
        has_dxva2 = any('dxva2' in acc.lower() for acc in hwaccels)
        
        if has_cuda:
            print("\n✓ NVIDIA CUDA acceleration available")
        if has_d3d11va:
            print("✓ Direct3D 11 acceleration available (recommended for Windows)")
        if has_dxva2:
            print("✓ DXVA2 acceleration available")
            
        return len(hwaccels) > 0
        
    except FileNotFoundError:
        print("✗ FFmpeg not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("✗ FFmpeg command timed out")
        return False
    except Exception as e:
        print(f"✗ Error checking FFmpeg: {e}")
        return False


def check_whisper():
    """Check if Whisper is installed"""
    print("\n" + "="*60)
    print("3. Checking Whisper Installation")
    print("="*60)
    
    try:
        import whisper
        print(f"✓ Whisper installed")
        return True
    except ImportError:
        print("✗ Whisper not installed")
        return False


def check_system_info():
    """Get system GPU information"""
    print("\n" + "="*60)
    print("4. System GPU Information")
    print("="*60)
    
    # Try nvidia-smi for NVIDIA GPUs
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ NVIDIA GPU detected:")
            for line in result.stdout.strip().split('\n'):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    print(f"  - {parts[0]}")
                    print(f"    Driver: {parts[1]}")
                    print(f"    VRAM: {parts[2]}")
            return True
    except:
        pass
    
    # Fallback to generic detection
    print("ℹ NVIDIA GPU not detected or nvidia-smi not available")
    print("  Checking for other GPUs via Windows...")
    
    try:
        # Use wmic on Windows
        result = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            gpus = [line.strip() for line in result.stdout.split('\n')[1:] if line.strip()]
            if gpus:
                print("  Detected GPUs:")
                for gpu in gpus:
                    print(f"  - {gpu}")
    except:
        pass
    
    return False


def generate_recommendations(pytorch_cuda, ffmpeg_ok):
    """Generate setup recommendations"""
    print("\n" + "="*60)
    print("5. Setup Recommendations")
    print("="*60)
    
    if pytorch_cuda and ffmpeg_ok:
        print("\n✓ GPU acceleration is fully configured!")
        print("\nRecommended settings for .env or environment:")
        print("  WHISPER_DEVICE=cuda")
        print("  FFMPEG_HWACCEL=cuda  # For NVIDIA GPUs")
        print("  # OR")
        print("  FFMPEG_HWACCEL=d3d11va  # For any Windows GPU")
        
    elif not pytorch_cuda and ffmpeg_ok:
        print("\n⚠ Partial GPU support available")
        print("\nFFmpeg hardware acceleration is available but PyTorch CUDA is not.")
        print("\nTo enable Whisper GPU acceleration:")
        print("  1. Uninstall CPU PyTorch:")
        print("     pip uninstall torch torchvision torchaudio")
        print("\n  2. Install CUDA PyTorch (requires NVIDIA GPU):")
        print("     pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        print("\n  3. Or install for CUDA 12.1:")
        print("     pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        print("\nCurrent recommended settings:")
        print("  WHISPER_DEVICE=cpu")
        print("  FFMPEG_HWACCEL=d3d11va")
        
    elif pytorch_cuda and not ffmpeg_ok:
        print("\n⚠ PyTorch CUDA available but FFmpeg acceleration not detected")
        print("\nWhisper can use GPU, but FFmpeg will use CPU for scene detection.")
        print("Consider installing FFmpeg with hardware acceleration support.")
        print("\nCurrent recommended settings:")
        print("  WHISPER_DEVICE=cuda")
        print("  FFMPEG_HWACCEL=  # Leave empty")
        
    else:
        print("\n✗ No GPU acceleration available")
        print("\nTo enable GPU acceleration:")
        print("  1. Ensure you have a compatible GPU (NVIDIA for CUDA, or any GPU for D3D11VA)")
        print("  2. Install CUDA PyTorch (see commands above)")
        print("  3. Ensure FFmpeg is properly installed")
        print("\nCurrent settings:")
        print("  WHISPER_DEVICE=cpu")
        print("  FFMPEG_HWACCEL=")


def main():
    print("\nClipCut GPU Setup Checker")
    print("=" * 60)
    
    # Run checks
    pytorch_cuda = check_pytorch_cuda()
    ffmpeg_ok = check_ffmpeg_hwaccel()
    whisper_ok = check_whisper()
    check_system_info()
    
    # Generate recommendations
    generate_recommendations(pytorch_cuda, ffmpeg_ok)
    
    print("\n" + "="*60)
    print("Check Complete")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
