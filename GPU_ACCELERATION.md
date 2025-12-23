# GPU Acceleration for ClipCut

## Overview

ClipCut now supports GPU acceleration for two major bottlenecks in the video processing pipeline:

1. **Whisper Transcription** (CUDA/GPU: 3-5x faster)
2. **FFmpeg Scene Detection** (Hardware Decode: 2-4x faster)

## Performance Improvements

- **CPU-only mode**: ~20 min for 14-min video
- **GPU-accelerated mode**: ~8-12 min for 14-min video (40-60% faster)

### Breakdown

| Stage           | CPU Time | GPU Time | Speedup |
| --------------- | -------- | -------- | ------- |
| Transcription   | 5 min    | 1-2 min  | 3-5x    |
| Scene Detection | 9 min    | 2-4 min  | 2-4x    |

---

## Configuration

### Environment Variables

Add these to your `.env` file or set as environment variables:

```bash
# Whisper GPU Acceleration
WHISPER_DEVICE=cuda        # Options: 'cpu' (default), 'cuda'

# FFmpeg Hardware Acceleration
FFMPEG_HWACCEL=cuda        # Options: '', 'cuda', 'd3d11va', 'dxva2', 'qsv'
```

### Hardware Requirements

#### For Whisper GPU Acceleration (`WHISPER_DEVICE=cuda`)

- **GPU**: NVIDIA GPU with CUDA support
- **Driver**: Latest NVIDIA drivers
- **PyTorch**: CUDA-enabled PyTorch installed
  ```bash
  # Check if PyTorch sees your GPU
  python -c "import torch; print(torch.cuda.is_available())"
  ```

#### For FFmpeg Hardware Acceleration

**Option 1: NVIDIA CUDA (`FFMPEG_HWACCEL=cuda`)**

- **GPU**: NVIDIA GPU with NVDEC support (GTX 900 series or newer)
- **FFmpeg**: Compiled with `--enable-cuda-nvdec`
- **Use case**: Best for NVIDIA GPUs

**Option 2: Windows Direct3D 11 (`FFMPEG_HWACCEL=d3d11va`)**

- **GPU**: Any modern GPU (Intel/AMD/NVIDIA) on Windows 8+
- **FFmpeg**: Standard Windows build (usually included)
- **Use case**: Best compatibility on Windows, works with integrated GPUs

**Option 3: Intel Quick Sync (`FFMPEG_HWACCEL=qsv`)**

- **GPU**: Intel CPU with Quick Sync Video support
- **FFmpeg**: Compiled with `--enable-libmfx`
- **Use case**: Intel CPUs with integrated graphics

---

## Usage Examples

### CPU-Only Mode (Default)

```bash
# No environment variables needed
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### GPU-Accelerated Mode (NVIDIA)

```bash
# Set environment variables before starting server
$env:WHISPER_DEVICE="cuda"
$env:FFMPEG_HWACCEL="cuda"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### GPU-Accelerated Mode (Windows D3D11 - Universal)

```bash
# Works with any GPU on Windows
$env:WHISPER_DEVICE="cuda"  # If you have NVIDIA GPU
$env:FFMPEG_HWACCEL="d3d11va"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Hybrid Mode (Whisper CPU, FFmpeg GPU)

```bash
# Use GPU only for video decoding, CPU for transcription
$env:WHISPER_DEVICE="cpu"
$env:FFMPEG_HWACCEL="d3d11va"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## Verification

### Check if GPU is being used

#### Whisper

```bash
# In pipeline.log or console, you'll see:
# "Loading Whisper model 'small' on device 'cuda'"
```

#### FFmpeg

```bash
# In pipeline.log or ffmpeg output, you'll see:
# "Input #0... Stream #0:0: Video: h264 (CUDA)"
# or
# "Input #0... Stream #0:0: Video: h264 (D3D11)"
```

### GPU Monitoring

```bash
# NVIDIA GPU
nvidia-smi -l 1  # Shows GPU utilization every 1 second

# Windows Task Manager
# Performance tab -> GPU section shows Video Encode/Decode usage
```

---

## Troubleshooting

### Whisper GPU Issues

**Problem**: `RuntimeError: CUDA out of memory`

- **Solution**: Use smaller model or reduce batch size
- **Fallback**: Set `WHISPER_DEVICE=cpu`

**Problem**: `torch.cuda.is_available() = False`

- **Solution**: Reinstall PyTorch with CUDA support:
  ```bash
  pip uninstall torch
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```

### FFmpeg GPU Issues

**Problem**: `Error initializing hwaccel cuda`

- **Cause**: GPU doesn't support NVDEC or FFmpeg not compiled with CUDA
- **Solution**: Try `FFMPEG_HWACCEL=d3d11va` instead (works on all Windows GPUs)

**Problem**: `No device available for hwaccel: d3d11va`

- **Cause**: Outdated GPU drivers
- **Solution**: Update graphics drivers, or fallback: `FFMPEG_HWACCEL=""`

**Problem**: Scene detection slower with GPU

- **Cause**: Overhead of GPU setup for short videos
- **Solution**: GPU acceleration is most beneficial for videos >5 minutes

---

## Best Practices

1. **Start with defaults**: Test CPU-only mode first to ensure pipeline works
2. **Enable incrementally**: Enable one GPU feature at a time to isolate issues
3. **Monitor performance**: Use `monitor_pipeline.py` to track actual speedups
4. **Check compatibility**: Verify FFmpeg hardware support:
   ```bash
   ffmpeg -hwaccels  # Lists available hardware accelerators
   ```
5. **Fallback gracefully**: If GPU fails, pipeline will continue on CPU (check logs)

---

## Recommended Settings by Hardware

### NVIDIA RTX/GTX GPU + Windows

```bash
WHISPER_DEVICE=cuda
FFMPEG_HWACCEL=cuda
```

### Intel/AMD GPU + Windows

```bash
WHISPER_DEVICE=cpu  # (No CUDA support)
FFMPEG_HWACCEL=d3d11va
```

### Intel CPU with Quick Sync

```bash
WHISPER_DEVICE=cpu
FFMPEG_HWACCEL=qsv
```

### No GPU / Compatibility Mode

```bash
# Leave unset or explicitly set to defaults
WHISPER_DEVICE=cpu
FFMPEG_HWACCEL=
```
