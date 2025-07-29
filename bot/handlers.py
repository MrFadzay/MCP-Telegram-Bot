from telegram import Update
from telegram.ext import ContextTypes
import logging
from bot.llm_utils import LLMSelector
from bot.services.user_service import UserService
from bot.utils import (
    download_photo, download_voice, download_document, cleanup_temp_file
)

logger = logging.getLogger(__name__)


class MessageHandlers:
    def __init__(self, llm_selector: LLMSelector):
        self.llm_selector = llm_selector

    async def _ensure_user_settings(self, telegram_user):
        """Убедиться, что настройки пользователя загружены"""
        try:
            # Создать или обновить пользователя в БД
            await UserService.get_or_create_user(telegram_user.id, telegram_user)

            # Загрузить настройки пользователя в ProviderManager
            settings_loaded = await self.llm_selector.provider_manager.load_user_settings(telegram_user.id)

            if not settings_loaded:
                logger.info(
                    f"Using default settings for user {telegram_user.id}")

        except Exception as e:
            logger.error(
                f"Failed to ensure user settings for {telegram_user.id}: {e}")

    async def handle_message(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        if not update.message or not update.message.from_user:
            return

        try:
            # Автоматически восстанавливаем настройки пользователя
            await self._ensure_user_settings(update.message.from_user)

            config = self.llm_selector.provider_manager.get_current_config()
            if not config:
                await update.message.reply_text(
                    "Пожалуйста, сначала выберите провайдера и "
                    "модель с помощью команды /select"
                )
                return

            user_message = update.message.text
            try:
                response = await self.llm_selector.generate_response(
                    user_message, user_id=update.message.from_user.id
                )
                if response:
                    await update.message.reply_text(response)
                else:
                    logger.error(
                        f"generate_response вернул None для сообщения: "
                        f"{user_message}")
                    await update.message.reply_text(
                        "Произошла внутренняя ошибка. "
                        "Повторите попытку позже."
                    )
            except Exception as e:
                logger.error(f"Ошибка при генерации ответа: {str(e)}")
                await update.message.reply_text(
                    "Произошла ошибка при генерации ответа. "
                    "Попробуйте выбрать другую модель или повторить позже."
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {str(e)}")
            await update.message.reply_text(
                "Произошла ошибка при обработке вашего сообщения.")

    async def handle_photo(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Обработчик входящих фотографий"""
        if not update.message or not update.message.photo or not update.message.from_user:
            return
            try:
                config = \
                    self.llm_selector.provider_manager.get_current_config()
                if not config:
                    await update.message.reply_text(
                        "Пожалуйста, сначала выберите провайдера и "
                        "модель с помощью команды /select"
                    )
                    return

                user_caption = update.message.caption
                file_path = await download_photo(update)
                response = await self.llm_selector.generate_response_with_image(
                    file_path,
                    user_caption
                )
                if response:
                    await update.message.reply_text(response)
                else:
                    logger.error(
                        f"generate_response_with_image вернул None для файла: "
                        f"{file_path}"
                    )
                    await update.message.reply_text(
                        "Произошла ошибка при обработке изображения."
                    )
                cleanup_temp_file(file_path)

            except Exception as e:
                logger.error(f"Ошибка при обработке фотографии: {str(e)}")
                await update.message.reply_text(
                    "Произошла ошибка при обработке вашего фото.")
        else:
            logger.warning(
                f"Получено обновление без фото: {update}"
            )
            return

    async def handle_voice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Обработчик входящих голосовых сообщений"""
        if not update.message or not update.message.voice or not update.message.from_user:
            return
            try:
                config = \
                    self.llm_selector.provider_manager.get_current_config()
                if not config:
                    await update.message.reply_text(
                        "Пожалуйста, сначала выберите провайдера и "
                        "модель с помощью команды /select"
                    )
                    return

                await update.message.reply_text(
                    "Получено голосовое сообщение. Обрабатываю..."
                )

                file_path = await download_voice(update)
                provider = self.llm_selector.provider_manager.current_provider
                model = self.llm_selector.provider_manager.current_model
                user_caption = update.message.caption

                # Обработка в зависимости от провайдера
                if provider == "google" and "gemini-2.5" in model:
                    try:
                        # Используем нативную поддержку аудио в Gemini
                        google_client = self.llm_selector.provider_manager.get_provider_instance(
                            "google"
                        )

                        # Если модель не поддерживает аудио, используем подходящую
                        if not any(audio_model in model for audio_model in
                                   ["gemini-2.5-flash", "gemini-2.5-pro"]):
                            model = "gemini-2.5-flash"

                        prompt = (
                            user_caption or
                            "Пожалуйста, проанализируй это голосовое сообщение "
                            "и расскажи, о чем в нем говорится. Если это на русском "
                            "языке, ответь на русском."
                        )

                        response = await google_client.generate_response_with_audio(
                            file_path, model, prompt
                        )

                        await update.message.reply_text(response)

                    except Exception as e:
                        logger.error(
                            f"Ошибка при обработке аудио через Gemini: {str(e)}"
                        )
                        await update.message.reply_text(
                            "Произошла ошибка при обработке аудио через Gemini. "
                            "Попробуйте другую модель или повторите позже."
                        )

                elif provider == "ollama":
                    # Для Ollama нужно использовать внешнюю библиотеку для STT
                    try:
                        # Проверяем, установлен ли Whisper
                        try:
                            import whisper
                        except ImportError:
                            await update.message.reply_text(
                                "Для обработки голосовых сообщений через Ollama "
                                "требуется библиотека Whisper. Установите её с помощью "
                                "команды: pip install openai-whisper"
                            )
                            cleanup_temp_file(file_path)
                            return

                        # Загружаем модель Whisper для транскрибации
                        await update.message.reply_text(
                            "Транскрибирую голосовое сообщение с помощью Whisper..."
                        )

                        # Используем малую модель для быстрой транскрибации
                        whisper_model = whisper.load_model("base")
                        result = whisper_model.transcribe(file_path)
                        transcribed_text = result["text"]

                        await update.message.reply_text(
                            f"Транскрипция: {transcribed_text}\n\n"
                            f"Генерирую ответ..."
                        )

                        # Отправляем транскрибированный текст в Ollama
                        prompt = (
                            f"Пользователь отправил голосовое сообщение "
                            f"со следующим текстом: '{transcribed_text}'. "
                            f"Пожалуйста, ответь на это сообщение."
                        )

                        response = await self.llm_selector.generate_response(
                            prompt, user_id=update.message.from_user.id
                        )
                        await update.message.reply_text(response)

                    except Exception as e:
                        logger.error(
                            f"Ошибка при обработке аудио через Whisper+Ollama: {str(e)}"
                        )
                        await update.message.reply_text(
                            "Произошла ошибка при обработке голосового сообщения. "
                            "Возможно, проблема с библиотекой Whisper или моделью Ollama."
                        )

                else:
                    # Для других провайдеров пока отправляем сообщение о разработке
                    await update.message.reply_text(
                        f"Обработка голосовых сообщений для провайдера {provider} "
                        f"находится в разработке. Попробуйте использовать Google Gemini "
                        f"или Ollama."
                    )

                cleanup_temp_file(file_path)

            except Exception as e:
                logger.error(
                    f"Ошибка при обработке голосового сообщения: {str(e)}")
                await update.message.reply_text(
                    "Произошла ошибка при обработке вашего голосового сообщения.")
        else:
            logger.warning(
                f"Получено обновление без голосового сообщения: {update}"
            )
            return

    async def handle_document(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Обработчик входящих документов"""
        if not update.message or not update.message.document or not update.message.from_user:
            return
            try:
                config = \
                    self.llm_selector.provider_manager.get_current_config()
                if not config:
                    await update.message.reply_text(
                        "Пожалуйста, сначала выберите провайдера и "
                        "модель с помощью команды /select"
                    )
                    return

                await update.message.reply_text(
                    "Получен документ. Обрабатываю..."
                )

                file_path, file_name = await download_document(update)

                # Определяем тип документа по расширению
                import os
                file_ext = os.path.splitext(file_name)[1].lower()

                # Обработка в зависимости от типа файла
                if file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json']:
                    # Текстовые файлы
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()

                        # Ограничиваем размер содержимого для отправки в LLM
                        if len(file_content) > 4000:
                            file_content = file_content[:4000] + \
                                "\n\n[Содержимое обрезано из-за большого размера]"

                        prompt = (
                            f"Пользователь отправил файл {file_name}. "
                            f"Вот его содержимое:\n\n{file_content}\n\n"
                            f"Пожалуйста, проанализируйте этот файл."
                        )

                        response = await self.llm_selector.generate_response(
                            prompt, user_id=update.message.from_user.id
                        )
                        if response:
                            await update.message.reply_text(response)
                        else:
                            await update.message.reply_text(
                                "Не удалось проанализировать содержимое файла."
                            )
                    except UnicodeDecodeError:
                        await update.message.reply_text(
                            "Не удалось прочитать файл как текст. Возможно, это бинарный файл."
                        )
                elif file_ext == '.pdf':
                    # PDF файлы
                    try:
                        # Проверяем наличие библиотеки PyPDF2
                        try:
                            import PyPDF2
                        except ImportError:
                            await update.message.reply_text(
                                "Для обработки PDF-файлов требуется библиотека PyPDF2. "
                                "Установите её с помощью команды: pip install PyPDF2"
                            )
                            cleanup_temp_file(file_path)
                            return

                        await update.message.reply_text(
                            "Извлекаю текст из PDF-документа..."
                        )

                        # Извлекаем текст из PDF
                        pdf_text = ""
                        with open(file_path, 'rb') as file:
                            pdf_reader = PyPDF2.PdfReader(file)
                            num_pages = len(pdf_reader.pages)

                            # Информация о документе
                            await update.message.reply_text(
                                f"PDF-документ содержит {num_pages} страниц. "
                                f"Обрабатываю..."
                            )

                            # Извлекаем текст из каждой страницы
                            # Ограничиваем 20 страницами
                            for page_num in range(min(num_pages, 20)):
                                page = pdf_reader.pages[page_num]
                                pdf_text += page.extract_text() + "\n\n"

                        # Если текст слишком длинный, разбиваем на части
                        if len(pdf_text) > 8000:
                            await update.message.reply_text(
                                "Документ слишком большой, анализирую первую часть..."
                            )
                            # Простое разделение на части по ~8000 символов
                            chunks = [pdf_text[i:i+8000]
                                      for i in range(0, len(pdf_text), 8000)]

                            # Обрабатываем первую часть для начального ответа
                            prompt = (
                                f"Это первая часть PDF документа '{file_name}' "
                                f"(всего {num_pages} страниц). "
                                f"Пожалуйста, начните анализ:\n\n{chunks[0]}"
                            )

                            response = await self.llm_selector.generate_response(
                                prompt, user_id=update.message.from_user.id
                            )
                            await update.message.reply_text(response)

                            # Если пользователь хочет продолжить анализ, он может запросить это отдельно
                            if len(chunks) > 1:
                                await update.message.reply_text(
                                    "Документ слишком большой для полного анализа за один раз. "
                                    "Это был анализ первой части. Если вам нужен анализ "
                                    "остальных частей, пожалуйста, укажите это в сообщении."
                                )
                        else:
                            # Если текст помещается целиком
                            prompt = (
                                f"Пользователь отправил PDF документ '{file_name}' "
                                f"({num_pages} страниц). "
                                f"Вот его содержимое:\n\n{pdf_text}\n\n"
                                f"Пожалуйста, проанализируйте этот документ."
                            )
                            response = await self.llm_selector.generate_response(
                                prompt, user_id=update.message.from_user.id
                            )
                            await update.message.reply_text(response)

                    except Exception as e:
                        logger.error(f"Ошибка при обработке PDF: {str(e)}")
                        await update.message.reply_text(
                            f"Произошла ошибка при обработке PDF-файла: {str(e)}"
                        )
                elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    # Изображения
                    user_caption = (
                        update.message.caption or
                        f"Анализ изображения {file_name}"
                    )
                    response = await self.llm_selector.generate_response_with_image(
                        file_path,
                        user_caption
                    )
                    if response:
                        await update.message.reply_text(response)
                    else:
                        await update.message.reply_text(
                            "Не удалось проанализировать изображение."
                        )
                else:
                    # Другие типы файлов
                    await update.message.reply_text(
                        f"Получен файл {file_name}. "
                        f"К сожалению, обработка файлов типа {file_ext} пока не поддерживается."
                    )

                cleanup_temp_file(file_path)

            except Exception as e:
                logger.error(f"Ошибка при обработке документа: {str(e)}")
                await update.message.reply_text(
                    "Произошла ошибка при обработке вашего документа."
                )
        else:
            logger.warning(
                f"Получено обновление без документа: {update}"
            )
            return
