"""Main crawler implementation."""

import os
import time
import logging
import requests
import sys
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from icrawler.builtin import UrlListCrawler
from pathlib import Path
from urllib.parse import urlparse

class YandexImageCrawler:
    """Main crawler class for Yandex image search and download."""

    def __init__(
        self,
        output_dir: str = "downloaded_images",
        max_images: int = 100,
        workers: int = 2,
        download_threads: int = 4,
        pause_time: int = 7,
        resume: bool = True
    ):
        self.output_dir = output_dir
        self.max_images = max_images
        self.workers = workers
        self.download_threads = download_threads
        self.pause_time = pause_time
        self.resume = resume

        # Create necessary directories
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            print(f"Error creating output directory: {str(e)}", file=sys.stderr)
            sys.exit(1)
        self._setup_logging()

    def _setup_logging(self):
        try:
            log_dir = os.path.join(self.output_dir, 'logs')
            temp_dir = os.path.join(log_dir, 'temp')
            state_dir = os.path.join(log_dir, 'states')
            for d in [log_dir, temp_dir, state_dir]:
                os.makedirs(d, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = os.path.join(log_dir, f'crawler_{timestamp}.log')
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - [%(processName)s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
        except OSError as e:
            print(f"Error setting up logging: {str(e)}", file=sys.stderr)
            sys.exit(1)

    def _download_url_image(self, url: str, output_path: str) -> bool:
        try:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            if not resp.headers.get('content-type', '').startswith('image/'):
                logging.error(f"Invalid content type for URL {url}: {resp.headers.get('content-type')}")
                return False
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            logging.error(f"Download/save error: {url} -> {output_path}, {e}")
            return False

    def _load_json(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to parse JSON {file_path}: {str(e)}")
            return {}

    def _save_json(self, file_path: str, data: Dict[str, Any]):
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save JSON {file_path}: {str(e)}")

    def _get_file_extension(self, path: str) -> str:
        try:
            parsed = urlparse(path)
            if parsed.scheme:
                path = parsed.path
            ext = os.path.splitext(path)[1].lower()
            if not ext and parsed.scheme:
                try:
                    resp = requests.head(path, timeout=5)
                    ext_map = {
                        "image/jpeg": ".jpg", "image/png": ".png",
                        "image/gif": ".gif", "image/webp": ".webp"
                    }
                    return ext_map.get(resp.headers.get('content-type', ''), '.jpg')
                except Exception:
                    return '.jpg'
            return ext or '.jpg'
        except Exception as e:
            logging.error(f"Get ext error: {path}, {e}")
            return '.jpg'

    def process_images(self, image_paths: List[str]):
        total_images = len(image_paths)
        logging.info(f"Found {total_images} images to process")
        progress = self._get_progress_summary(total_images)
        logging.info(
            f"Progress: Total {progress['total']}, "
            f"Completed {progress['completed']}, "
            f"Failed {progress['failed']}, "
            f"Remaining {progress['remaining']}"
        )

        # Resume: remove completed images
        if self.resume:
            filtered = []
            for path in image_paths:
                state_file = self._get_state_file_path(path)
                if os.path.exists(state_file):
                    existing_state = self._load_json(state_file)
                    if existing_state.get('status') != 'completed':
                        filtered.append(path)
                    else:
                        logging.info(f"Skipping already completed: {path}")
                else:
                    filtered.append(path)
            image_paths = filtered
            if not image_paths:
                logging.info("All images already processed. Exiting.")
                return

        process_args = [(path, idx+1, len(image_paths)) for idx, path in enumerate(image_paths)]
        max_workers = min(len(image_paths), self.workers)
        batch_size = min(100, len(image_paths))

        for i in range(0, len(process_args), batch_size):
            batch = process_args[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(process_args) + batch_size - 1) // batch_size
            logging.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} images)")
            try:
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(self._process_single_image, args): args for args in batch}
                    completed = 0
                    for future in as_completed(futures, timeout=3600):
                        try:
                            future.result()
                            completed += 1
                            if completed % 10 == 0:
                                logging.info(f"Batch {batch_num}: Completed {completed}/{len(batch)} images")
                        except Exception as e:
                            args = futures[future]
                            logging.error(f"Error processing image {args[0]}: {str(e)}")
                logging.info(f"Batch {batch_num} completed: {completed}/{len(batch)} images processed")
            except Exception as e:
                logging.error(f"Error in batch {batch_num}: {str(e)}")
                continue
            if i + batch_size < len(process_args):
                time.sleep(2)

        final_progress = self._get_progress_summary(total_images)
        logging.info(
            f"Final progress: Total {final_progress['total']}, "
            f"Completed {final_progress['completed']}, "
            f"Failed {final_progress['failed']}, "
            f"Remaining {final_progress['remaining']}"
        )

    def _process_single_image(self, args: tuple) -> None:
        image_path, idx, total_images = args
        driver = None
        state_file = self._get_state_file_path(image_path)
        state = {
            'image_path': image_path,
            'status': 'processing',
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'process_id': os.getpid()
        }
        try:
            logging.info(f"\n=== Processing image {idx}/{total_images} ===")
            logging.info(f"Image path: {image_path}")
            output_dir = self._get_output_dir_name(image_path, self.output_dir)
            os.makedirs(output_dir, exist_ok=True)

            if self.resume and os.path.exists(state_file):
                existing_state = self._load_json(state_file)
                if existing_state.get('status') == 'completed':
                    logging.info(f"Image {image_path} already processed, skipping")
                    return
                state.update(existing_state)
            self._save_json(state_file, state)

            # Download if URL
            if image_path.startswith(('http://', 'https://')):
                temp_image_path = os.path.join(output_dir, 'source_image' + self._get_file_extension(image_path))
                if not self._download_url_image(image_path, temp_image_path):
                    state.update({'status': 'failed', 'error': 'Failed to download source image', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                    self._save_json(state_file, state)
                    return
                image_path = temp_image_path

            if not os.path.exists(image_path):
                state.update({'status': 'failed', 'error': 'Source image file not found', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                self._save_json(state_file, state)
                return

            try:
                driver = self._init_chrome_driver()
            except Exception as e:
                logging.error(f"Failed to initialize WebDriver: {str(e)}")
                state.update({'status': 'failed', 'error': f'WebDriver init error: {str(e)}', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                self._save_json(state_file, state)
                return

            logging.info("=== Phase 1: Collecting image URLs ===")
            image_urls = self._crawl_image_urls(driver, image_path)
            if not image_urls:
                state.update({'status': 'failed', 'error': 'No URLs found', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                self._save_json(state_file, state)
                return

            state.update({'status': 'downloading', 'downloaded_count': 0, 'total_count': len(image_urls), 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            self._save_json(state_file, state)

            # Write URLs to temp file
            temp_url_file = self._get_temp_file_path(idx)
            try:
                with open(temp_url_file, 'w') as f:
                    for url in image_urls:
                        f.write(f"{url}\n")
            except Exception as e:
                state.update({'status': 'failed', 'error': f'Write URL file err: {str(e)}', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                self._save_json(state_file, state)
                return

            # Download with iCrawler
            try:
                crawler = UrlListCrawler(
                    downloader_threads=self.download_threads,
                    storage={'root_dir': output_dir}
                )
                logging.info("=== Phase 3: Downloading images ===")
                crawler.crawl(temp_url_file)
            except Exception as e:
                state.update({'status': 'failed', 'error': f'Download failed: {str(e)}', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                self._save_json(state_file, state)
                return

            state.update({'status': 'completed', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            self._save_json(state_file, state)
            logging.info(f"Successfully processed image {idx}/{total_images}")

        except Exception as e:
            logging.error(f"Unexpected error processing image {image_path}: {str(e)}")
            error_state = {
                'image_path': image_path,
                'status': 'failed',
                'error': f'Unexpected error: {str(e)}',
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'process_id': os.getpid()
            }
            self._save_json(state_file, error_state)
        finally:
            if driver:
                try:
                    driver.quit()
                    logging.debug("WebDriver closed")
                except Exception as e:
                    logging.warning(f"Error closing WebDriver: {str(e)}")
            try:
                temp_url_file = self._get_temp_file_path(idx)
                if os.path.exists(temp_url_file):
                    os.remove(temp_url_file)
            except Exception as e:
                logging.warning(f"Error cleaning up temp file: {str(e)}")

    def _init_chrome_driver(self) -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_binary = "/usr/bin/google-chrome"
        if os.path.exists(chrome_binary):
            chrome_options.binary_location = chrome_binary
        chromedriver_path = "/usr/bin/chromedriver"
        if not os.path.exists(chromedriver_path):
            chromedriver_path = "/usr/local/bin/chromedriver"
        if os.path.exists(chromedriver_path):
            service = Service(executable_path=chromedriver_path)
        else:
            service = Service()
        try:
            logging.info("Creating Chrome WebDriver instance...")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logging.info("Chrome WebDriver initialized")
            return driver
        except Exception as e:
            logging.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
            raise

    def _crawl_image_urls(self, driver: webdriver.Chrome, image_path: str) -> List[str]:
        """Crawl image URLs from Yandex search results.
        
        This method performs the following steps:
        1. Uploads the source image to Yandex
        2. Waits for search results to load
        3. Extracts image URLs from the search results
        4. Handles pagination to collect more results
        
        Args:
            driver: Initialized Chrome WebDriver instance
            image_path: Path to the source image file
            
        Returns:
            List of image URLs found in search results
            
        Raises:
            WebDriverException: If there are issues with browser automation
            TimeoutException: If page elements don't load within expected time
            FileNotFoundError: If source image file doesn't exist
        """
        start_time = time.time()
        try:
            wait = WebDriverWait(driver, 10)
            driver.get("https://yandex.ru/images/")
            camera_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//button[@aria-label="Поиск по картинке"]')
            ))
            camera_btn.click()
            file_input = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//input[@type="file"]')
            ))
            file_input.send_keys(image_path)
            similar_tab = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'a.CbirNavigation-TabsItem_name_similar-page')
            ))
            similar_tab.click()
            time.sleep(self.pause_time)
            img_urls = set()
            last_height = driver.execute_script("return document.body.scrollHeight")
            while len(img_urls) < self.max_images:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                time.sleep(self.pause_time)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                for img in soup.find_all('img'):
                    src = img.get("src")
                    if src and src.startswith("//"):
                        img_urls.add("https:" + src)
                    if len(img_urls) >= self.max_images:
                        break
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            logging.info(f"Collected {len(img_urls)} image URLs in {time.time() - start_time:.2f}s")
            return list(img_urls)
        except Exception as e:
            logging.error(f"Error during image crawl: {str(e)}")
            return []

    @staticmethod
    def _get_output_dir_name(image_path: str, base_dir: str) -> str:
        path = Path(urlparse(image_path).path if image_path.startswith("http") else image_path)
        parent = path.parent.name or "default"
        name = path.stem
        out_path = Path(base_dir) / parent / name

        i = 1
        while out_path.exists():
            out_path = Path(base_dir) / parent / f"{name}_{i}"
            i += 1

        return str(out_path)

    def _get_state_file_path(self, image_path: str) -> str:
        import hashlib
        image_hash = hashlib.md5(image_path.encode()).hexdigest()
        return os.path.join(self.output_dir, 'logs', 'states', f"download_state_{image_hash}.json")

    def _get_temp_file_path(self, idx: int) -> str:
        return os.path.join(self.output_dir, 'logs', 'temp', f"temp_image_urls_{idx}.txt")

    def _get_progress_summary(self, total_images: int) -> Dict[str, int]:
        completed = failed = 0
        states_dir = os.path.join(self.output_dir, 'logs', 'states')
        if os.path.exists(states_dir):
            for filename in os.listdir(states_dir):
                if filename.startswith('download_state_') and filename.endswith('.json'):
                    try:
                        state = self._load_json(os.path.join(states_dir, filename))
                        if state.get('status') == 'completed':
                            completed += 1
                        elif state.get('status') == 'failed':
                            failed += 1
                    except Exception:
                        continue
        return {
            'total': total_images,
            'completed': completed,
            'failed': failed,
            'remaining': total_images - completed - failed
        }
