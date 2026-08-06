import os
import urllib.request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
CONFIG_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

def download_file(url, filepath):
    if not os.path.exists(filepath):
        logger.info(f"Downloading {url} to {filepath}...")
        try:
            # Add a user-agent to avoid 403 Forbidden
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
                data = response.read()
                out_file.write(data)
            logger.info(f"Successfully downloaded {filepath}")
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            raise
    else:
        logger.info(f"File already exists at {filepath}")

def main():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        
    model_path = os.path.join(MODELS_DIR, "en_US-lessac-medium.onnx")
    config_path = os.path.join(MODELS_DIR, "en_US-lessac-medium.onnx.json")
    
    download_file(MODEL_URL, model_path)
    download_file(CONFIG_URL, config_path)
    logger.info("All models downloaded successfully.")

if __name__ == "__main__":
    main()
