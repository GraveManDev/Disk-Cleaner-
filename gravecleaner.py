import os
import shutil
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import math
from datetime import datetime
from queue import Queue, Empty
import glob
import json

class SmoothDiskCleaner:
    def __init__(self, root):
        # Инициализация настроек
        self.settings = {
            'clean_temp': True,
            'clean_thumbnails': True,
            'clean_duplicates': True,
            'clean_logs': False,
            'clean_empty_folders': False,
            'exclude_folders': [],
            'max_file_size_mb': 50
        }
        self.load_settings()
        
        # Инициализация цветов и шрифтов
        self._init_colors()
        self._init_fonts()
        
        # Очередь для обновления UI
        self.ui_queue = Queue()
        
        # Настройка главного окна
        self.root = root
        self.root.title("Smooth Disk Cleaner")
        self.root.geometry("1000x700")
        self.root.minsize(900, 650)
        self.root.configure(bg=self.bg_color)
        
        # Переменные состояния
        self.cleaning = False
        self.progress_value = 0
        self.files_deleted = 0
        self.space_freed = 0
        self.current_operation = "Ожидание запуска..."
        
        # Создание интерфейса
        self._setup_ui()
        
        # Проверка очереди сообщений
        self.root.after(100, self._process_queue)

    def _init_colors(self):
        """Светло-оранжевая цветовая схема"""
        self.bg_color = "#f8f4e9"
        self.card_color = "#ffffff"
        self.accent_color = "#ffa500"
        self.text_color = "#333333"
        self.error_color = "#ff4d4d"
        self.success_color = "#4CAF50"
        self.warning_color = "#ff9800"
        self.log_bg_color = "#ffffff"
        self.log_border = "#e0e0e0"

    def _init_fonts(self):
        """Инициализация шрифтов"""
        self.title_font = ("Segoe UI", 22, "bold")
        self.subtitle_font = ("Segoe UI", 11)
        self.mono_font = ("Consolas", 10)
        self.button_font = ("Segoe UI", 12, "bold")

    def _setup_ui(self):
        """Создание пользовательского интерфейса"""
        # Главный контейнер
        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=25, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        header_frame = tk.Frame(main_frame, bg=self.bg_color)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(
            header_frame,
            text="SMOOTH DISK CLEANER",
            font=self.title_font,
            fg=self.accent_color,
            bg=self.bg_color
        ).pack(side=tk.LEFT)
        
        # Область контента
        self.content_frame = tk.Frame(main_frame, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Основной интерфейс очистки
        self._setup_main_interface()
        
        # Панель кнопок
        buttons_frame = tk.Frame(main_frame, bg=self.bg_color)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Кнопка запуска
        self.start_btn = tk.Button(
            buttons_frame,
            text="НАЧАТЬ ОЧИСТКУ",
            bg=self.accent_color,
            fg="#ffffff",
            activebackground="#e69500",
            activeforeground="#ffffff",
            font=self.button_font,
            borderwidth=0,
            padx=30,
            pady=10,
            relief=tk.FLAT,
            command=self.start_cleaning
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка остановки
        self.stop_btn = tk.Button(
            buttons_frame,
            text="ОСТАНОВИТЬ",
            bg=self.error_color,
            fg="#ffffff",
            activebackground="#cc4444",
            activeforeground="#ffffff",
            font=self.button_font,
            borderwidth=0,
            padx=30,
            pady=10,
            relief=tk.FLAT,
            state=tk.DISABLED,
            command=self.stop_cleaning
        )
        self.stop_btn.pack(side=tk.LEFT)
        
        # Кнопка настроек
        self.settings_btn = tk.Button(
            buttons_frame,
            text="НАСТРОЙКИ",
            bg="#e0e0e0",
            fg=self.text_color,
            activebackground="#d0d0d0",
            activeforeground=self.text_color,
            font=self.button_font,
            borderwidth=0,
            padx=30,
            pady=10,
            relief=tk.FLAT,
            command=self.show_settings
        )
        self.settings_btn.pack(side=tk.RIGHT)

    def _setup_main_interface(self):
        """Настройка основного интерфейса очистки"""
        # Очистка предыдущего содержимого
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Левая панель (статистика)
        left_panel = tk.Frame(self.content_frame, bg=self.bg_color)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Карточка статистики
        stats_card = tk.Frame(
            left_panel, 
            bg=self.card_color, 
            padx=20, 
            pady=20,
            highlightbackground="#e0e0e0",
            highlightthickness=1
        )
        stats_card.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            stats_card,
            text="Статистика",
            font=("Segoe UI", 16, "bold"),
            fg=self.text_color,
            bg=self.card_color
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Удалено файлов
        files_frame = tk.Frame(stats_card, bg=self.card_color)
        files_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(
            files_frame,
            text="Удалено файлов:",
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color
        ).pack(side=tk.LEFT)
        
        self.files_label = tk.Label(
            files_frame,
            text="0",
            font=self.subtitle_font,
            fg=self.accent_color,
            bg=self.card_color
        )
        self.files_label.pack(side=tk.RIGHT)
        
        # Освобождено места
        space_frame = tk.Frame(stats_card, bg=self.card_color)
        space_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(
            space_frame,
            text="Освобождено места:",
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color
        ).pack(side=tk.LEFT)
        
        self.space_label = tk.Label(
            space_frame,
            text="0 Б",
            font=self.subtitle_font,
            fg=self.accent_color,
            bg=self.card_color
        )
        self.space_label.pack(side=tk.RIGHT)
        
        # Текущая операция
        op_frame = tk.Frame(stats_card, bg=self.card_color)
        op_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(
            op_frame,
            text="Текущая операция:",
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color
        ).pack(side=tk.LEFT)
        
        self.current_op_label = tk.Label(
            op_frame,
            text=self.current_operation,
            font=self.subtitle_font,
            fg=self.accent_color,
            bg=self.card_color,
            wraplength=300,
            justify=tk.LEFT
        )
        self.current_op_label.pack(side=tk.RIGHT)
        
        # Прогресс-бар
        progress_frame = tk.Frame(stats_card, bg=self.card_color)
        progress_frame.pack(fill=tk.X, pady=(20, 0))
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("custom.Horizontal.TProgressbar", 
                       background=self.accent_color,
                       troughcolor="#f0f0f0",
                       bordercolor="#e0e0e0",
                       lightcolor=self.accent_color,
                       darkcolor=self.accent_color)
        
        self.progress = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            mode='determinate',
            length=100,
            style="custom.Horizontal.TProgressbar"
        )
        self.progress.pack(fill=tk.X)
        
        self.progress_label = tk.Label(
            progress_frame,
            text="0%",
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color
        )
        self.progress_label.pack(side=tk.RIGHT, padx=5)
        
        # Правая панель (лог)
        right_panel = tk.Frame(self.content_frame, bg=self.bg_color)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Карточка лога
        log_card = tk.Frame(
            right_panel, 
            bg=self.card_color, 
            padx=20, 
            pady=20,
            highlightbackground="#e0e0e0",
            highlightthickness=1
        )
        log_card.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            log_card,
            text="Журнал операций",
            font=("Segoe UI", 16, "bold"),
            fg=self.text_color,
            bg=self.card_color
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Контейнер для лога
        log_container = tk.Frame(log_card, bg=self.log_bg_color)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        # Текстовое поле лога
        self.log_text = tk.Text(
            log_container,
            bg=self.log_bg_color,
            fg=self.text_color,
            insertbackground=self.text_color,
            wrap=tk.WORD,
            font=self.mono_font,
            padx=12,
            pady=12,
            state=tk.DISABLED,
            relief=tk.FLAT,
            highlightthickness=0,
            width=60
        )
        
        # Скроллбары
        scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(log_container, orient="horizontal", command=self.log_text.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text.configure(xscrollcommand=h_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Настройка тегов для цветного текста
        self.log_text.tag_config("timestamp", foreground="#888888")
        self.log_text.tag_config("info", foreground="#0078d7")
        self.log_text.tag_config("success", foreground=self.success_color)
        self.log_text.tag_config("warning", foreground=self.warning_color)
        self.log_text.tag_config("error", foreground=self.error_color)

    def _process_queue(self):
        """Обработка сообщений из очереди для обновления UI"""
        try:
            while True:
                task = self.ui_queue.get_nowait()
                if task[0] == "progress":
                    self._update_progress(task[1])
                elif task[0] == "log":
                    self._log_message(task[1], task[2])
                elif task[0] == "operation":
                    self.current_operation = task[1]
                    self.current_op_label.config(text=task[1])
                elif task[0] == "files":
                    self.files_deleted = task[1]
                    self.files_label.config(text=str(task[1]))
                elif task[0] == "space":
                    self.space_freed = task[1]
                    self.space_label.config(text=self._format_size(task[1]))
        except Empty:
            pass
        
        self.root.after(100, self._process_queue)

    def _update_progress(self, value):
        """Плавное обновление прогресс-бара"""
        if value > self.progress_value:
            step = max(1, (value - self.progress_value) // 10)
        else:
            step = -1
            
        self.progress_value = value
        self.progress["value"] = self.progress_value
        self.progress_label.config(text=f"{self.progress_value}%")

    def _log_message(self, message, level="info"):
        """Добавление сообщения в лог"""
        self.log_text.config(state=tk.NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(tk.END, f"[{level.upper()}] ", level)
        self.log_text.insert(tk.END, message + "\n")
        
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _format_size(self, size_bytes):
        """Форматирование размера в читаемый вид"""
        if size_bytes == 0:
            return "0 Б"
        
        size_names = ("Б", "КБ", "МБ", "ГБ", "ТБ")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        
        return f"{s} {size_names[i]}"

    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                    # Обновляем только существующие ключи
                    for key in self.settings:
                        if key in loaded_settings:
                            self.settings[key] = loaded_settings[key]
        except Exception as e:
            print(f"Ошибка загрузки настроек: {str(e)}")

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {str(e)}")

    def start_cleaning(self):
        """Запуск процесса очистки"""
        if self.cleaning:
            return
            
        self.cleaning = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.files_deleted = 0
        self.space_freed = 0
        self.progress_value = 0
        self.progress["value"] = 0
        self.progress_label.config(text="0%")
        self.current_operation = "Очистка начата"
        self.current_op_label.config(text=self.current_operation)
        
        # Очистка лога
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Запуск очистки в отдельном потоке
        cleaning_thread = threading.Thread(target=self._run_cleaning, daemon=True)
        cleaning_thread.start()

    def stop_cleaning(self):
        """Остановка процесса очистки"""
        self.cleaning = False
        self.current_operation = "Очистка остановлена"
        self.current_op_label.config(text=self.current_operation)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._log_message("Очистка остановлена пользователем", "warning")

    def _run_cleaning(self):
        """Основной процесс очистки"""
        try:
            total_steps = sum([
                self.settings['clean_temp'],
                self.settings['clean_thumbnails'],
                self.settings['clean_duplicates'],
                self.settings['clean_logs'],
                self.settings['clean_empty_folders']
            ])
            
            if total_steps == 0:
                self.ui_queue.put(("log", "Не выбрано ни одной категории для очистки!", "warning"))
                return
                
            step = 0
            progress_per_step = 100 / total_steps
            
            # Очистка временных файлов
            if self.settings['clean_temp'] and self.cleaning:
                step += 1
                self._clean_temp_files()
                self.ui_queue.put(("progress", int(step * progress_per_step)))
            
            # Очистка кэша эскизов
            if self.settings['clean_thumbnails'] and self.cleaning:
                step += 1
                self._clean_thumbnail_cache()
                self.ui_queue.put(("progress", int(step * progress_per_step)))
            
            # Удаление дубликатов
            if self.settings['clean_duplicates'] and self.cleaning:
                step += 1
                self._clean_duplicates_in_chunks()
                self.ui_queue.put(("progress", int(step * progress_per_step)))
            
            # Очистка логов
            if self.settings['clean_logs'] and self.cleaning:
                step += 1
                self._clean_system_logs()
                self.ui_queue.put(("progress", int(step * progress_per_step)))
            
            # Удаление пустых папок
            if self.settings['clean_empty_folders'] and self.cleaning:
                step += 1
                self._clean_empty_folders()
                self.ui_queue.put(("progress", int(step * progress_per_step)))
            
            if self.cleaning:
                self.ui_queue.put(("progress", 100))
                self.ui_queue.put(("operation", "Очистка завершена"))
                self.ui_queue.put(("log", f"Удалено файлов: {self.files_deleted}", "success"))
                self.ui_queue.put(("log", f"Освобождено места: {self._format_size(self.space_freed)}", "success"))
                messagebox.showinfo("Готово", "Очистка диска успешно завершена!")
        
        except Exception as e:
            self.ui_queue.put(("log", f"Ошибка: {str(e)}", "error"))
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")
        finally:
            self.cleaning = False
            self.ui_queue.put(("operation", "Готов к работе"))
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def _clean_temp_files(self):
        """Очистка временных файлов"""
        self.ui_queue.put(("operation", "Поиск временных файлов..."))
        
        temp_folders = [
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Microsoft', 'Windows', 'INetCache'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Microsoft', 'Windows', 'INetCookies'),
        ]
        
        for folder in temp_folders:
            if not self.cleaning:
                break
                
            if os.path.exists(folder):
                self.ui_queue.put(("operation", f"Очистка {os.path.basename(folder)}..."))
                self._clean_folder(folder)

    def _clean_thumbnail_cache(self):
        """Очистка кэша эскизов Windows"""
        self.ui_queue.put(("operation", "Очистка кэша эскизов..."))
        
        thumb_cache_paths = [
            os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer'),
        ]
        
        for path in thumb_cache_paths:
            if not self.cleaning:
                break
                
            if os.path.exists(path):
                for file in glob.glob(os.path.join(path, 'thumbcache_*.db')):
                    try:
                        if self._is_file_safe_to_delete(file):
                            file_size = os.path.getsize(file)
                            os.remove(file)
                            self.files_deleted += 1
                            self.space_freed += file_size
                            
                            if self.files_deleted % 10 == 0:
                                self.ui_queue.put(("files", self.files_deleted))
                                self.ui_queue.put(("space", self.space_freed))
                    except Exception as e:
                        self.ui_queue.put(("log", f"Не удалось удалить {file}: {str(e)}", "error"))

    def _clean_duplicates_in_chunks(self):
        """Удаление дубликатов с разбивкой на чанки"""
        self.ui_queue.put(("operation", "Поиск дубликатов файлов..."))
        
        search_paths = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Documents'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Pictures'),
        ]
        
        for path in search_paths:
            if not self.cleaning:
                break
                
            if os.path.exists(path):
                self.ui_queue.put(("operation", f"Поиск в {os.path.basename(path)}..."))
                self._find_and_remove_duplicates(path)

    def _clean_system_logs(self):
        """Очистка системных логов"""
        self.ui_queue.put(("operation", "Очистка системных логов..."))
        
        log_paths = [
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Logs'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'LogFiles'),
        ]
        
        for path in log_paths:
            if not self.cleaning:
                break
                
            if os.path.exists(path):
                self._clean_folder(path, extensions=['.log', '.txt'])

    def _clean_empty_folders(self):
        """Удаление пустых папок"""
        self.ui_queue.put(("operation", "Поиск пустых папок..."))
        
        search_paths = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Documents'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Pictures'),
        ]
        
        for path in search_paths:
            if not self.cleaning:
                break
                
            if os.path.exists(path):
                self._remove_empty_folders(path)

    def _clean_folder(self, folder_path, extensions=None):
        """Очистка указанной папки"""
        self.ui_queue.put(("log", f"Очистка папки: {folder_path}", "info"))
        
        for root, dirs, files in os.walk(folder_path):
            if not self.cleaning:
                return
                
            for file in files:
                file_path = os.path.join(root, file)
                
                # Проверка на исключенные папки
                if any(excluded in file_path for excluded in self.settings['exclude_folders']):
                    continue
                    
                # Проверка на расширения файлов
                if extensions and not any(file.lower().endswith(ext) for ext in extensions):
                    continue
                    
                try:
                    if self._is_file_safe_to_delete(file_path):
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        self.files_deleted += 1
                        self.space_freed += file_size
                        
                        if self.files_deleted % 50 == 0:
                            self.ui_queue.put(("files", self.files_deleted))
                            self.ui_queue.put(("space", self.space_freed))
                except Exception as e:
                    self.ui_queue.put(("log", f"Не удалось удалить {file_path}: {str(e)}", "error"))
            
            # Обновляем счетчики после обработки каждой папки
            self.ui_queue.put(("files", self.files_deleted))
            self.ui_queue.put(("space", self.space_freed))

    def _find_and_remove_duplicates(self, start_path):
        """Поиск и удаление дубликатов с пагинацией"""
        file_hashes = {}
        processed_files = 0
        
        for root, dirs, files in os.walk(start_path):
            if not self.cleaning:
                return
                
            for file in files:
                file_path = os.path.join(root, file)
                
                # Проверка на исключенные папки
                if any(excluded in file_path for excluded in self.settings['exclude_folders']):
                    continue
                    
                try:
                    # Ограничиваем количество одновременно обрабатываемых файлов
                    if processed_files % 100 == 0:
                        self.ui_queue.put(("operation", f"Анализ файлов... ({processed_files})"))
                        
                    file_hash = self._get_file_hash(file_path)
                    
                    if file_hash in file_hashes:
                        # Найден дубликат
                        try:
                            if self._is_file_safe_to_delete(file_path):
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                self.files_deleted += 1
                                self.space_freed += file_size
                                
                                if self.files_deleted % 10 == 0:
                                    self.ui_queue.put(("files", self.files_deleted))
                                    self.ui_queue.put(("space", self.space_freed))
                                    self.ui_queue.put(("log", f"Удалён дубликат: {file_path}", "info"))
                        except Exception as e:
                            self.ui_queue.put(("log", f"Не удалось удалить дубликат {file_path}: {str(e)}", "error"))
                    else:
                        file_hashes[file_hash] = file_path
                    
                    processed_files += 1
                except Exception as e:
                    self.ui_queue.put(("log", f"Ошибка при обработке {file_path}: {str(e)}", "error"))

    def _remove_empty_folders(self, start_path):
        """Рекурсивное удаление пустых папок"""
        for root, dirs, files in os.walk(start_path, topdown=False):
            if not self.cleaning:
                return
                
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                
                # Проверка на исключенные папки
                if any(excluded in dir_path for excluded in self.settings['exclude_folders']):
                    continue
                    
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        self.ui_queue.put(("log", f"Удалена пустая папка: {dir_path}", "info"))
                except Exception as e:
                    self.ui_queue.put(("log", f"Не удалось удалить папку {dir_path}: {str(e)}", "error"))

    def _is_file_safe_to_delete(self, file_path):
        """Проверка, что файл безопасен для удаления"""
        # Проверка размера файла
        file_size = os.path.getsize(file_path)
        max_size = self.settings['max_file_size_mb'] * 1024 * 1024
        
        if file_size > max_size:
            self.ui_queue.put(("log", f"Пропуск большого файла: {file_path} ({self._format_size(file_size)})", "warning"))
            return False
            
        # Проверка на системные файлы
        if file_path.startswith(os.environ.get('SystemRoot', 'C:\\Windows')):
            self.ui_queue.put(("log", f"Пропуск системного файла: {file_path}", "warning"))
            return False
            
        return True

    def _get_file_hash(self, file_path, block_size=65536):
        """Вычисление хеша файла"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(block_size)
        return hasher.hexdigest()

    def show_settings(self):
        """Отображение окна настроек"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройки")
        settings_window.geometry("500x600")
        settings_window.configure(bg=self.bg_color)
        settings_window.resizable(False, False)
        
        # Центрирование окна настроек
        window_width = 500
        window_height = 600
        x = (self.root.winfo_screenwidth() // 2) - (window_width // 2)
        y = (self.root.winfo_screenheight() // 2) - (window_height // 2)
        settings_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Главный контейнер
        main_frame = tk.Frame(settings_window, bg=self.bg_color, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        tk.Label(
            main_frame,
            text="Настройки очистки",
            font=("Segoe UI", 18, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        ).pack(pady=(0, 20))
        
        # Фрейм с настройками
        settings_frame = tk.Frame(main_frame, bg=self.card_color, padx=15, pady=15)
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Категории очистки
        tk.Label(
            settings_frame,
            text="Категории для очистки:",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.card_color
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Временные файлы
        self.clean_temp_var = tk.BooleanVar(value=self.settings['clean_temp'])
        tk.Checkbutton(
            settings_frame,
            text="Временные файлы",
            variable=self.clean_temp_var,
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color,
            selectcolor=self.bg_color,
            activebackground=self.card_color,
            activeforeground=self.text_color
        ).pack(anchor=tk.W, pady=5)
        
        # Кэш эскизов
        self.clean_thumbnails_var = tk.BooleanVar(value=self.settings['clean_thumbnails'])
        tk.Checkbutton(
            settings_frame,
            text="Кэш эскизов",
            variable=self.clean_thumbnails_var,
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color,
            selectcolor=self.bg_color,
            activebackground=self.card_color,
            activeforeground=self.text_color
        ).pack(anchor=tk.W, pady=5)
        
        # Дубликаты файлов
        self.clean_duplicates_var = tk.BooleanVar(value=self.settings['clean_duplicates'])
        tk.Checkbutton(
            settings_frame,
            text="Дубликаты файлов",
            variable=self.clean_duplicates_var,
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color,
            selectcolor=self.bg_color,
            activebackground=self.card_color,
            activeforeground=self.text_color
        ).pack(anchor=tk.W, pady=5)
        
        # Системные логи
        self.clean_logs_var = tk.BooleanVar(value=self.settings['clean_logs'])
        tk.Checkbutton(
            settings_frame,
            text="Системные логи",
            variable=self.clean_logs_var,
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color,
            selectcolor=self.bg_color,
            activebackground=self.card_color,
            activeforeground=self.text_color
        ).pack(anchor=tk.W, pady=5)
        
        # Пустые папки
        self.clean_empty_folders_var = tk.BooleanVar(value=self.settings['clean_empty_folders'])
        tk.Checkbutton(
            settings_frame,
            text="Пустые папки",
            variable=self.clean_empty_folders_var,
            font=self.subtitle_font,
            fg=self.text_color,
            bg=self.card_color,
            selectcolor=self.bg_color,
            activebackground=self.card_color,
            activeforeground=self.text_color
        ).pack(anchor=tk.W, pady=5)
        
        # Максимальный размер файла
        tk.Label(
            settings_frame,
            text="Макс. размер файла (МБ):",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.card_color
        ).pack(anchor=tk.W, pady=(20, 5))
        
        self.max_file_size_var = tk.IntVar(value=self.settings['max_file_size_mb'])
        tk.Scale(
            settings_frame,
            from_=1,
            to=500,
            orient=tk.HORIZONTAL,
            variable=self.max_file_size_var,
            bg=self.card_color,
            fg=self.text_color,
            highlightbackground=self.card_color,
            troughcolor="#f0f0f0",
            activebackground=self.accent_color
        ).pack(fill=tk.X, pady=5)
        
        # Исключенные папки
        tk.Label(
            settings_frame,
            text="Исключенные папки:",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.card_color
        ).pack(anchor=tk.W, pady=(20, 5))
        
        self.excluded_folders_listbox = tk.Listbox(
            settings_frame,
            height=4,
            bg="white",
            fg=self.text_color,
            selectbackground=self.accent_color,
            selectforeground="white",
            font=self.subtitle_font
        )
        self.excluded_folders_listbox.pack(fill=tk.X, pady=5)
        
        for folder in self.settings['exclude_folders']:
            self.excluded_folders_listbox.insert(tk.END, folder)
        
        # Кнопки управления исключениями
               # Кнопки управления исключениями
        buttons_frame = tk.Frame(settings_frame, bg=self.card_color)
        buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        add_btn = tk.Button(
            buttons_frame,
            text="Добавить",
            bg="#e0e0e0",
            fg=self.text_color,
            activebackground="#d0d0d0",
            activeforeground=self.text_color,
            font=("Segoe UI", 10),
            borderwidth=0,
            padx=10,
            pady=5,
            relief=tk.FLAT,
            command=self._add_excluded_folder
        )
        add_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        remove_btn = tk.Button(
            buttons_frame,
            text="Удалить",
            bg="#e0e0e0",
            fg=self.text_color,
            activebackground="#d0d0d0",
            activeforeground=self.text_color,
            font=("Segoe UI", 10),
            borderwidth=0,
            padx=10,
            pady=5,
            relief=tk.FLAT,
            command=self._remove_excluded_folder
        )
        remove_btn.pack(side=tk.LEFT)
        
        # Кнопки сохранения/отмены
        bottom_buttons_frame = tk.Frame(main_frame, bg=self.bg_color)
        bottom_buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        save_btn = tk.Button(
            bottom_buttons_frame,
            text="Сохранить",
            bg=self.accent_color,
            fg="white",
            activebackground="#e69500",
            activeforeground="white",
            font=("Segoe UI", 12, "bold"),
            borderwidth=0,
            padx=20,
            pady=8,
            relief=tk.FLAT,
            command=lambda: self._save_settings_and_close(settings_window)
        )
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_btn = tk.Button(
            bottom_buttons_frame,
            text="Отмена",
            bg="#e0e0e0",
            fg=self.text_color,
            activebackground="#d0d0d0",
            activeforeground=self.text_color,
            font=("Segoe UI", 12),
            borderwidth=0,
            padx=20,
            pady=8,
            relief=tk.FLAT,
            command=settings_window.destroy
        )
        cancel_btn.pack(side=tk.RIGHT)

    def _add_excluded_folder(self):
        """Добавление папки в список исключений"""
        folder = filedialog.askdirectory(title="Выберите папку для исключения")
        if folder and folder not in self.settings['exclude_folders']:
            self.excluded_folders_listbox.insert(tk.END, folder)

    def _remove_excluded_folder(self):
        """Удаление папки из списка исключений"""
        selection = self.excluded_folders_listbox.curselection()
        if selection:
            self.excluded_folders_listbox.delete(selection[0])

    def _save_settings_and_close(self, window):
        """Сохранение настроек и закрытие окна"""
        self.settings = {
            'clean_temp': self.clean_temp_var.get(),
            'clean_thumbnails': self.clean_thumbnails_var.get(),
            'clean_duplicates': self.clean_duplicates_var.get(),
            'clean_logs': self.clean_logs_var.get(),
            'clean_empty_folders': self.clean_empty_folders_var.get(),
            'exclude_folders': list(self.excluded_folders_listbox.get(0, tk.END)),
            'max_file_size_mb': self.max_file_size_var.get()
        }
        
        self.save_settings()
        window.destroy()
        messagebox.showinfo("Сохранено", "Настройки успешно сохранены!")

    def run(self):
        """Запуск главного цикла приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = SmoothDiskCleaner(root)
    app.run()