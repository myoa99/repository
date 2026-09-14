## Запуск под Windows

Откройте `cmd` или PowerShell в корне репозитория и выполните команду:

```bat
scripts\setup_env.bat
Скрипт автоматически:

найдёт Anaconda или Miniconda;
создаст окружение course_env, если оно ещё не существует;
установит зависимости из requirements.txt;
выполнит smoke test.
Повторный запуск безопасен: существующее окружение не пересоздаётся.

Smoke test
Запустить smoke test вручную можно командой:

bat

Collapse


 Copy

conda run -n course_env python broken_env.py
Ожидаемый вывод:

text

Collapse


 Copy

python: путь_к_python
pandas: версия_pandas
Проверить код завершения команды в cmd:

bat

Collapse


 Copy

echo %ERRORLEVEL%
Ожидаемый результат:

text

Collapse


 Copy

0
В PowerShell код завершения проверяется командой:

powershell

Collapse


 Copy

$LASTEXITCODE
Ожидаемый результат:

text

Collapse


 Copy

0
Если настройка окружения ещё не выполнялась, сначала запустите:

bat

Collapse


 Copy

scripts\setup_env.bat
