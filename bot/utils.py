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
        logger.error(f"Ошибка при скачивании фото: {e}")
        raise


async def download_voice(update: Update) -> str:
    """Скачивание голосового сообщения во временный файл."""
    try:
        voice_file = await update.message.voice.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            await voice_file.download_to_drive(temp_file.name)
            return temp_file.name
    except Exception as e:
        logger.error(f"Ошибка при скачивании голосового сообщения: {e}")
        raise


async def download_document(update: Update) -> tuple[str, str]:
    """Скачивание документа во временный файл и возвращение пути и имени файла."""
    try:
        document = update.message.document
        file_name = document.file_name
        file_extension = os.path.splitext(file_name)[1] if file_name else ""

        document_file = await document.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            await document_file.download_to_drive(temp_file.name)
            return temp_file.name, file_name
    except Exception as e:
        logger.error(f"Ошибка при скачивании документа: {e}")
        raise


def cleanup_temp_file(file_path: str):
    """Удаление временного файла."""
    try:
        os.unlink(file_path)
    except Exception as e:
        logger.error(f"Ошибка при удалении временного файла {file_path}: {e}")
