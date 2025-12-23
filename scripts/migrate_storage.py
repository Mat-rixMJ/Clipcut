#!/usr/bin/env python3
"""
Storage Migration Script

Consolidates all ClipCut media files from scattered locations into unified storage:
D:\clipcut\data\

This script is safe to run multiple times - it won't overwrite existing files.
"""
import shutil
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Define source and destination paths
CLIPCUT_ROOT = Path("D:/clipcut")
UNIFIED_DATA_DIR = CLIPCUT_ROOT / "data"
BACKEND_DATA_DIR = CLIPCUT_ROOT / "backend" / "data"

# Target subdirectories
VIDEOS_DIR = UNIFIED_DATA_DIR / "videos"
AUDIO_DIR = UNIFIED_DATA_DIR / "audio"
RENDERS_DIR = UNIFIED_DATA_DIR / "renders"
ARTIFACTS_DIR = UNIFIED_DATA_DIR / "artifacts"

# Create all directories if they don't exist
for dir_path in [VIDEOS_DIR, AUDIO_DIR, RENDERS_DIR, ARTIFACTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"✓ Directory exists: {dir_path}")


def migrate_files(source_dir: Path, dest_dir: Path, pattern: str, file_type: str) -> int:
    """
    Migrate files from source to destination.
    
    Args:
        source_dir: Source directory to migrate from
        dest_dir: Destination directory to migrate to
        pattern: Glob pattern for files (e.g., "*.mp4")
        file_type: Human-readable file type for logging
    
    Returns:
        Number of files migrated
    """
    if not source_dir.exists():
        logger.info(f"ℹ Source directory doesn't exist, skipping: {source_dir}")
        return 0
    
    files = list(source_dir.glob(pattern))
    if not files:
        logger.info(f"ℹ No {file_type} files found in {source_dir}")
        return 0
    
    logger.info(f"📦 Found {len(files)} {file_type} file(s) in {source_dir}")
    
    migrated = 0
    for file_path in files:
        dest_file = dest_dir / file_path.name
        
        if dest_file.exists():
            logger.warning(f"⚠ Already exists, skipping: {dest_file}")
            continue
        
        try:
            shutil.copy2(file_path, dest_file)
            logger.info(f"✓ Migrated {file_type}: {file_path.name}")
            migrated += 1
        except Exception as e:
            logger.error(f"✗ Failed to migrate {file_path}: {e}")
    
    return migrated


def migrate_subdirectories(source_base: Path, dest_base: Path, pattern: str) -> int:
    """
    Migrate subdirectories with files.
    Useful for renders/{video_id}/ structure.
    """
    if not source_base.exists():
        logger.info(f"ℹ Source directory doesn't exist: {source_base}")
        return 0
    
    total_migrated = 0
    
    # Find all subdirectories
    subdirs = [d for d in source_base.iterdir() if d.is_dir()]
    if not subdirs:
        logger.info(f"ℹ No subdirectories found in {source_base}")
        return 0
    
    logger.info(f"📦 Found {len(subdirs)} subdirectories in {source_base}")
    
    for subdir in subdirs:
        files = list(subdir.glob(pattern))
        if not files:
            continue
        
        # Create corresponding destination subdirectory
        dest_subdir = dest_base / subdir.name
        dest_subdir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"  → Subdirectory: {subdir.name} ({len(files)} files)")
        
        for file_path in files:
            dest_file = dest_subdir / file_path.name
            
            if dest_file.exists():
                logger.warning(f"    ⚠ Already exists, skipping: {file_path.name}")
                continue
            
            try:
                shutil.copy2(file_path, dest_file)
                logger.info(f"    ✓ Migrated: {file_path.name}")
                total_migrated += 1
            except Exception as e:
                logger.error(f"    ✗ Failed to migrate {file_path}: {e}")
    
    return total_migrated


def main():
    print("=" * 80)
    print("ClipCut Storage Migration Tool")
    print("=" * 80)
    print()
    print(f"Unified storage location: {UNIFIED_DATA_DIR}")
    print()
    
    total_migrated = 0
    
    # ========== MIGRATE VIDEOS ==========
    logger.info("\n[1/4] Migrating original videos...")
    if BACKEND_DATA_DIR.exists():
        backend_videos = BACKEND_DATA_DIR / "videos"
        migrated = migrate_files(backend_videos, VIDEOS_DIR, "*.mp4", "video")
        total_migrated += migrated
    
    # ========== MIGRATE AUDIO ==========
    logger.info("\n[2/4] Migrating extracted audio...")
    if BACKEND_DATA_DIR.exists():
        backend_audio = BACKEND_DATA_DIR / "audio"
        migrated = migrate_files(backend_audio, AUDIO_DIR, "*.wav", "audio")
        total_migrated += migrated
    
    # ========== MIGRATE RENDERS ==========
    logger.info("\n[3/4] Migrating rendered clips...")
    if BACKEND_DATA_DIR.exists():
        backend_renders = BACKEND_DATA_DIR / "renders"
        migrated = migrate_subdirectories(backend_renders, RENDERS_DIR, "*.mp4")
        total_migrated += migrated
    
    # ========== CLEANUP ==========
    logger.info("\n[4/4] Cleanup...")
    if BACKEND_DATA_DIR.exists():
        try:
            # Only remove if it's now empty
            remaining_items = list(BACKEND_DATA_DIR.glob("**/*"))
            if len(remaining_items) == 0:
                shutil.rmtree(BACKEND_DATA_DIR)
                logger.info(f"✓ Removed empty directory: {BACKEND_DATA_DIR}")
            else:
                logger.warning(f"⚠ Not removing {BACKEND_DATA_DIR} - still contains files")
                logger.info(f"   You can manually delete it after verifying migration")
        except Exception as e:
            logger.error(f"✗ Failed to cleanup {BACKEND_DATA_DIR}: {e}")
    
    # ========== SUMMARY ==========
    print()
    print("=" * 80)
    print(f"Migration Complete: {total_migrated} file(s) migrated")
    print("=" * 80)
    print()
    print("✓ All files consolidated in: D:\\clipcut\\data\\")
    print()
    print("Directory structure:")
    print("  • videos/   - Original uploads and YouTube downloads")
    print("  • audio/    - Extracted audio files")
    print("  • renders/  - Rendered clips organized by video_id")
    print()
    print("Next steps:")
    print("  1. Verify the migration was successful")
    print("  2. Restart the backend server")
    print("  3. Test the pipeline with a new video submission")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        exit(1)
