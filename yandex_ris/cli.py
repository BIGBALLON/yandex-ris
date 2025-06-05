"""Command line interface for Yandex Image Crawler."""

import argparse
import logging
import os
from pathlib import Path
from urllib.parse import urlparse
from .crawler import YandexImageCrawler

def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_image_paths(input_path: str) -> list:
    """Get all image paths from input (file, directory or URL)."""
    image_paths = []
    
    # Check if input is a URL
    if is_valid_url(input_path):
        return [input_path]
    
    # Check if input is a directory
    if os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    image_paths.append(os.path.join(root, file))
        return image_paths
    
    # Check if input is a file
    if os.path.isfile(input_path):
        # If it's an image file
        if input_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            return [input_path]
        # If it's a text file containing paths
        with open(input_path, 'r') as f:
            paths = [line.strip() for line in f if line.strip()]
            # Process each path in the file
            for path in paths:
                image_paths.extend(get_image_paths(path))
            return image_paths
    
    return []

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Yandex Image Search and Download Tool')
    
    parser.add_argument('--input', '-i', 
                      required=True,
                      help='Input path (file, directory or URL)')
    
    parser.add_argument('--output', '-o',
                      default='downloaded_images',
                      help='Output root directory (default: downloaded_images)')
    
    parser.add_argument('--max-images', '-m',
                      type=int,
                      default=100,
                      help='Maximum number of images to download per source (default: 100)')
    
    parser.add_argument('--pause-time', '-p',
                      type=int,
                      default=7,
                      help='Page load wait time in seconds (default: 7)')
    
    parser.add_argument('--workers', '-w',
                      type=int,
                      default=2,
                      help='Number of parallel processing workers (default: 2)')
    
    parser.add_argument('--download-threads', '-t',
                      type=int,
                      default=4,
                      help='Number of download threads per process (default: 4)')
    
    parser.add_argument('--log-level',
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO',
                      help='Logging level (default: INFO)')
    
    return parser.parse_args()

def main():
    """Main entry point for the command line interface."""
    args = parse_arguments()
    
    # Configure logging
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - [%(processName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Initialize crawler
    crawler = YandexImageCrawler(
        output_dir=args.output,
        max_images=args.max_images,
        workers=args.workers,
        download_threads=args.download_threads,
        pause_time=args.pause_time,
        resume=True  # Always enable resume functionality
    )
    
    # Get image paths
    image_paths = get_image_paths(args.input)
    
    if not image_paths:
        logging.error(f"No valid images found in input: {args.input}")
        return
    
    logging.info(f"Found {len(image_paths)} images to process")
    
    # Process images
    crawler.process_images(image_paths)

if __name__ == "__main__":
    main() 