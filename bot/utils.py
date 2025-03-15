import logging
import tempfile
import os
from telegram import Update

logger = logging.getLogger(__name__)


async def download_photo(update: Update) -> str:
    """Скачивание фотографии во временный файл."""
    try:
        photo_file = await update.message.photo[-1].get_file()
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            await photo_file.download_to_drive(temp_file.name)
            return temp_file.name
    except Exception as e:
        logger.error(f"Error downloading photo: {e}")
        raise


def cleanup_temp_file(file_path: str):
    """Удаление временного файла."""
    try:
        os.unlink(file_path)
    except Exception as e:
        logger.error(f"Error deleting temp file {file_path}: {e}")

