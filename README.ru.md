<div align="center">

<img src="https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/logo.svg" alt="jsrecon" width="880">

### Наведи на веб-приложение — получи API, с которым говорит его JavaScript.

jsrecon распаковывает source maps, разбирает каждый бандл настоящей грамматикой JavaScript и
отдаёт эндпоинты, GraphQL-операции, роуты и утёкшие ключи, которые знает фронтенд, — таблицей,
JSON, Markdown и скелетом OpenAPI 3.1.

[![CI](https://github.com/web3daemon/jsrecon/actions/workflows/ci.yml/badge.svg)](https://github.com/web3daemon/jsrecon/actions/workflows/ci.yml)
[![Release v0.2.0](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-version.svg)](https://github.com/web3daemon/jsrecon/blob/main/CHANGELOG.md)
[![Python 3.10+](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-python.svg)](https://www.python.org/)
[![License MIT](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-license.svg)](https://github.com/web3daemon/jsrecon/blob/main/LICENSE)
[![Parser tree-sitter](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-parser.svg)](https://tree-sitter.github.io/)
[![Output OpenAPI 3.1](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-openapi.svg)](#что-на-выходе)

[English](https://github.com/web3daemon/jsrecon/blob/main/README.md) · **Русский**

<br>

<img src="https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/demo.svg" alt="демо jsrecon: разбор демо-магазина — эндпоинты, GraphQL, роуты, утёкший ключ, восстановленные исходники" width="100%">

</div>

## Установка

```bash
pipx install git+https://github.com/web3daemon/jsrecon      # релиз на PyPI — скоро
```

Python 3.10+. Без конфигов, без API-ключей, без браузера.

## Попробовать за 30 секунд

В репозитории лежит маленький демо-магазин: исходники на TypeScript, собранные и минифицированные
esbuild, с source map рядом с бандлом — ровно так уходит в прод много фронтендов:

```bash
git clone https://github.com/web3daemon/jsrecon && cd jsrecon
python -m http.server 8080 -d examples/shop/dist      # в одном терминале
jsrecon map http://localhost:8080 -o recon            # в другом
```

Это тот самый прогон из демо выше: 16 эндпоинтов с методами и параметрами пути, 4 GraphQL-операции,
8 экранов и один AWS-ключ, которому не место в клиенте. Каждая находка указывает на исходный файл и
строку — `src/api/orders.ts:18`, а не `main-RU4RXFFD.js:1`.

## Зачем

Грепнуть минифицированный бандл по `/api/` — получить шум: строки, которые не URL, и URL, собранные
через `+` или шаблон, от которых регулярка видит половину.

**jsrecon читает код так же, как движок.** Каждый бандл разбирается
[tree-sitter](https://tree-sitter.github.io/)-ом, поэтому минифицированный `s.get(…)`, метод внутри
объекта опций (`fetch(url, { method: "POST" })`) и шаблонный путь
(`` `/orders/${id}/refund` `` → `/orders/{id}/refund`) распознаются.

**А если бандл отдаёт source map, исходный TypeScript лежит прямо внутри.** jsrecon разворачивает
его обратно в дерево файлов и анализирует *его*, а не минифицированную кашу: настоящие имена,
комментарии, структура папок. Каждая находка указывает на исходный файл и строку.

## Что находит

| | |
|---|---|
| 🌐 **HTTP-эндпоинты** | вызовы `fetch` / `axios` / `ky` / `$.ajax` / XHR с **методом** плюс URL и пути, похожие на API |
| 🧩 **Параметры пути и запроса** | `` `/orders/${id}` `` → `/orders/{id}`, `?page=${page}` → query-параметр — сразу в OpenAPI |
| 🧬 **GraphQL** | операции `query` / `mutation` / `subscription` в тегах `gql` и в обычных строках |
| 🗺 **Source maps → исходники** | `sourcesContent` разворачивается в исходное дерево файлов и анализируется первым |
| 🧭 **Клиентские роуты** | таблицы роутеров и `<Route path>` — все экраны приложения до первого клика |
| 🔑 **Утёкшие серверные ключи** | узкая защитная проверка на ключи, которым не место в браузере; значения всегда замаскированы |
| 📍 **Откуда взялось** | у каждой находки есть `файл:строка`, в исходнике, если есть карта |
| 📤 **Отчёты** | живая таблица, `findings.json`, `findings.md`, `openapi.json` и дерево `sources/` |

## Использование

```bash
jsrecon map https://app.example.com              # страница: её <script> и modulepreload
jsrecon map https://app.example.com/main.js      # один бандл
jsrecon map ./dist                               # локальная сборка
jsrecon map ./dist -o recon                      # + отчёты и восстановленные исходники
jsrecon map ./app.min.js --json | jq '.endpoints'   # JSON в stdout
```

| флаг | |
|---|---|
| `-o, --out DIR` | записать `findings.json`, `findings.md`, `openapi.json` и `sources/` в `DIR` |
| `--json` | вывести находки в stdout как JSON (таблица уходит в stderr) |
| `--no-secrets` | пропустить проверку ключей |
| `--timeout N` | таймаут HTTP в секундах (по умолчанию 20) |

## Что на выходе

```
recon/
├── findings.json      все находки: метод, уверенность, файл и строка
├── findings.md        то же таблицами Markdown — для тикета или отчёта
├── openapi.json       скелет OpenAPI 3.1: пути, методы, параметры пути и запроса
└── sources/           исходное дерево, восстановленное из source maps
```

OpenAPI — это скелет: пути и параметры, без схем тел запросов и ответов. Точка старта для клиента
или для спецификации из трафика в [httpcrabber](https://github.com/web3daemon/httpcrabber-client),
а не готовый контракт.

## Recon-сьюта

jsrecon — сосед **[httpcrabber](https://github.com/web3daemon/httpcrabber-client)**: httpcrabber
записывает, что приложение *делает* в сети, jsrecon читает, что его код *умеет*. Запусти оба на
одном приложении — получишь и увиденный трафик, и эндпоинты, до которых ещё не дошёл.

## Для чего

jsrecon читает JavaScript, который сайт и так отдаёт каждому посетителю, — те же байты, что
скачивает твой браузер. Наводи на приложение, API которого нужно понять:

- сторонний сервис без публичного SDK и документации — чтобы написать клиент;
- публичный API, для которого нужна спецификация OpenAPI или типизированный клиент;
- цель багбаунти в рамках её скоупа или пентест, на который есть разрешение;
- свои фронтенды — в том числе поймать ключ, случайно попавший в сборку, раньше других.

Инструмент читает только то, что загружается при обычном открытии страницы. Он не обходит
авторизацию и защиту от ботов и не маскируется (User-Agent — `jsrecon`). Поиск ключей — защитный,
значения маскируются. Не направляй его на системы, которые тебе не разрешено тестировать, —
ответственность за использование на тебе. См. [SECURITY.md](https://github.com/web3daemon/jsrecon/blob/main/SECURITY.md).

## Роадмап

- [x] метод из опций `fetch` и `XMLHttpRequest.open`
- [x] клиентские роуты
- [x] параметры пути и запроса, `файл:строка` у каждой находки
- [ ] генерация типизированного async-клиента на `httpx` + pydantic
- [ ] MCP-сервер: агент спрашивает *«какие эндпоинты у этого приложения?»*
- [ ] `jsrecon watch` — перезапуск по расписанию и алерт при изменении API
- [ ] сессии [httpcrabber](https://github.com/web3daemon/httpcrabber-client) как вход

Строю в открытую: [t.me/web3daemon_social](https://t.me/web3daemon_social) ·
[X @web3daemon](https://x.com/web3daemon).

## Лицензия

[MIT](https://github.com/web3daemon/jsrecon/blob/main/LICENSE)
