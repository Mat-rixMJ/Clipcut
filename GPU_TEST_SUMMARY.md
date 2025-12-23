# GPU Acceleration Test Summary

## ✅ GPU Setup Complete

### Hardware Detected

- **GPU:** NVIDIA GeForce RTX 3050 6GB Laptop GPU
- **Driver:** 591.59
- **VRAM:** 6.00 GB
- **CUDA:** 11.8

### Software Stack

- ✅ **PyTorch:** 2.7.1+cu118 with CUDA support
- ✅ **FFmpeg:** Hardware acceleration enabled (CUDA, D3D11VA, DXVA2, QSV, AMF)
- ✅ **Whisper:** openai-whisper installed
- ✅ **Server:** Running with full GPU acceleration

### Enabled Accelerations

#### 1. Whisper Transcription (GPU)

- **Setting:** `WHISPER_DEVICE=cuda`
- **Impact:** 3-5x faster transcription
- **Expected:** ~5 min → ~1-2 min for 14-min video

#### 2. FFmpeg Scene Detection (GPU)

- **Setting:** `FFMPEG_HWACCEL=cuda`
- **Hardware:** NVDEC hardware decode
- **Impact:** 2-4x faster scene detection
- **Expected:** ~9 min → ~2-4 min for 14-min video

### Performance Expectations

| Stage               | CPU Time    | GPU Time      | Speedup            |
| ------------------- | ----------- | ------------- | ------------------ |
| Download            | ~3 min      | ~3 min        | 1x (network bound) |
| Ingest              | instant     | instant       | 1x                 |
| **Transcription**   | **~5 min**  | **~1-2 min**  | **3-5x**           |
| **Scene Detection** | **~9 min**  | **~2-4 min**  | **2-4x**           |
| Clip Generation     | ~2 min      | ~2 min        | 1x (I/O bound)     |
| **Total**           | **~20 min** | **~8-12 min** | **40-60% faster**  |

## Test Commands

### Quick Test (Short Video)

```powershell
# Test with a short video (~5 min)
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos/process-youtube" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
$videoId = $response.video_id
Write-Host "Video ID: $videoId"

# Monitor progress
python scripts/monitor_pipeline.py $videoId
```

### Performance Test (Longer Video)

```powershell
# Test with a longer video to see full GPU benefits
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos/process-youtube" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"url":"YOUR_YOUTUBE_URL"}'
$videoId = $response.video_id

# Monitor with timing
python scripts/monitor_pipeline.py $videoId
```

### GPU Monitoring During Processing

```powershell
# In another terminal, monitor GPU usage
nvidia-smi -l 1  # Updates every second
```

## Troubleshooting

### If Whisper CUDA Fails

- Check: `python -c "import torch; print(torch.cuda.is_available())"`
- Should return: `True`
- If False: Reinstall PyTorch with CUDA
  ```powershell
  pip uninstall torch torchvision torchaudio
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```

### If FFmpeg CUDA Fails

- FFmpeg will automatically fallback to CPU decode
- Check logs in `D:\clipcut\pipeline.log`
- Alternative: Use `FFMPEG_HWACCEL=d3d11va` (works on all GPUs)

### Memory Issues

- RTX 3050 has 6GB VRAM
- Whisper "small" model uses ~2GB
- If OOM errors occur: fallback to `WHISPER_DEVICE=cpu`

## Next Steps

1. **Test with short video** to verify setup works
2. **Compare timing** with previous CPU-only runs
3. **Monitor GPU usage** with nvidia-smi
4. **Test longer videos** to see full performance gains

## Alternative Configurations

### Hybrid Mode (Whisper GPU, FFmpeg D3D11VA)

```powershell
$env:WHISPER_DEVICE="cuda"
$env:FFMPEG_HWACCEL="d3d11va"
# Restart server
```

### Conservative Mode (FFmpeg GPU only)

```powershell
$env:WHISPER_DEVICE="cpu"
$env:FFMPEG_HWACCEL="cuda"
# Restart server
```

### Maximum Compatibility (D3D11VA)

```powershell
$env:WHISPER_DEVICE="cuda"
$env:FFMPEG_HWACCEL="d3d11va"  # Works on Intel/AMD/NVIDIA
# Restart server
```
