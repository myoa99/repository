# Запуск под Windows

Откройте `cmd` или PowerShell в корне репозитория и выполните команду:

```bat
scripts\setup_env.bat
```
Скрипт автоматически:

найдёт Anaconda или Miniconda;
создаст окружение course_env, если оно ещё не существует;
установит зависимости из requirements.txt;
выполнит smoke test.
Повторный запуск безопасен: существующее окружение не пересоздаётся.
Smoke test
Запустить smoke test вручную можно командой:
```bat
conda run -n course_env python broken_env.py
```
Ожидаемый вывод:
```txt
python: путь_к_python
pandas: версия_pandas
```
Проверить код завершения команды в cmd:
```bat
echo %ERRORLEVEL%
```
Ожидаемый результат:
```txt
0
```
Если настройка окружения ещё не выполнялась, сначала запустите:
```bat
scripts\setup_env.bat
```
