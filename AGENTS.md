Проект: astrology-mcp-server.

Язык: Python 3.11+ или Python 3.12+.

Основной фреймворк MCP: FastMCP.

Транспорт: HTTP / Streamable HTTP, чтобы один сервер можно было подключать к разным ботам.

Основной движок расчётов: Kerykeion.

Низкоуровневый расчётный слой, если нужен дополнительный контроль: pyswisseph.

Обязательное окружение: conda environment с именем astro.

Агент обязан:
1. Создать conda-окружение astro.
2. Установить все зависимости только в окружение astro.
3. Запускать сервер только из окружения astro.
4. Запускать тесты только из окружения astro.
5. Запускать ruff, mypy, pytest и любые dev-инструменты только из окружения astro.
6. Не использовать глобальный Python.
7. Не использовать глобальный pip.
8. Не использовать argparse.
9. Не делать CLI-парсинг аргументов.
10. Все настройки задавать через config-модуль, переменные окружения или параметры функций.

Все команды Python должны выполняться одним из двух способов:

conda activate astro
python ...

или:

conda run -n astro python ...
conda run -n astro pytest
conda run -n astro ruff check .
conda run -n astro mypy astrology_mcp
