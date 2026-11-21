# Таблицы автотрейда в SQL (для поиска на сайте)

Map-сервер хранит лавки автотрейда в двух таблицах базы `ragnarok`. С их помощью лавки переживают рестарт
сервера, и по ним же сайт может искать товары. Обе таблицы в кодировке **cp1251** (как `char`), без
автоинкремента.

**В таблицах только лавки на автотрейде.** Лавки игроков, которые сейчас сами стоят в игре, сюда не попадают.

## `autotrade_shop`: одна строка на лавку

| поле | тип | что это |
|---|---|---|
| `char_id` | INT UNSIGNED, PK | персонаж-торговец (`char.char_id`) |
| `account_id` | INT UNSIGNED | его аккаунт (`login.account_id`) |
| `sex` | TINYINT | пол аккаунта (служебное) |
| `map` | VARCHAR(16) | карта, например `prontera` |
| `x`, `y` | SMALLINT | клетка, где стоит лавка |
| `dir` | TINYINT | направление взгляда (служебное) |
| `title` | VARCHAR(80) | название лавки, **cp1251** |
| `opened` | DATETIME | когда лавка ушла в автотрейд |

## `autotrade_item`: одна строка на товар лавки

| поле | тип | что это |
|---|---|---|
| `char_id` | INT UNSIGNED, PK (1) | лавка (`autotrade_shop.char_id`) |
| `cart_slot` | SMALLINT, PK (2) | номер ячейки в тележке (служебное) |
| `nameid` | INT UNSIGNED | ID предмета (как в `item_db`) |
| `amount` | SMALLINT | сколько **осталось** в продаже |
| `price` | INT UNSIGNED | цена **за штуку**, зени |
| `refine` | TINYINT UNSIGNED | заточка (`+7` → 7) |
| `attribute` | TINYINT | 1 = предмет сломан |
| `card0`..`card3` | INT | карты в слотах (ID карт как в `item_db`, 0 = пусто) |

Поля `refine`, `attribute`, `card0..3` добавляет `sql-files/upgrade_2026-11-21_autotrade_cards.sql`. Если их
нет, сервер хранит лавки как раньше, без них.

## Когда данные меняются

- **`@autotrade`:** строки лавки и всех её товаров появляются.
- **Продажа:** у товара уменьшается `amount`; проданный до конца товар пропадает.
- **Всё распродано, лавка закрыта, или владелец вошёл в игру на этот аккаунт:** строки лавки и её товаров удаляются.
- **Штатное выключение сервера:** таблицы переписываются из памяти сервера целиком.
- **Старт сервера:** лавки поднимаются из таблиц, строки остаются.

Таблицы всегда отражают текущее состояние: обновление идёт сразу при каждой продаже.

## Примеры запросов

Найти, где продаётся предмет (по ID), от дешёвых к дорогим:
```sql
SELECT i.nameid, i.price, i.amount, s.title, s.map, s.x, s.y, c.name AS seller
FROM autotrade_item i
JOIN autotrade_shop s ON s.char_id = i.char_id
JOIN `char` c ON c.char_id = i.char_id
WHERE i.nameid = 1765
ORDER BY i.price ASC;
```

Все лавки с числом товаров:
```sql
SELECT s.char_id, c.name AS seller, s.title, s.map, s.x, s.y, s.opened, COUNT(*) AS items
FROM autotrade_shop s
JOIN `char` c ON c.char_id = s.char_id
LEFT JOIN autotrade_item i ON i.char_id = s.char_id
GROUP BY s.char_id;
```

Поиск по названию лавки:
```sql
SELECT * FROM autotrade_shop WHERE title LIKE CONCAT('%', ?, '%');
```
Строку поиска передавай параметром (не склеивай в запрос), в cp1251. Проще всего подключаться с
`SET NAMES cp1251` или с кодировкой соединения cp1251/utf8mb4, тогда MariaDB сама перекодирует.

## Что нужно знать сайту

- **Названия предметов** в базе не хранятся: `use_sql_db: no`, item_db читается сервером из файла
  `db/item_db.txt`. Сайту нужен свой справочник `nameid → имя`: из `db/item_db.txt` или из `iteminfo`
  клиента.
- **Заточка и карты** берутся из `refine` и `card0..card3` самой строки товара. С `cart_inventory` строку не
  связывай: `cart_slot` — это порядок загрузки тележки, а не ключ.
  Например, «+7 и выше с картой 4001»: `WHERE nameid = ? AND refine >= 7 AND 4001 IN (card0, card1, card2, card3)`.
- **Доступ:** сайту хватит пользователя MariaDB с правом `SELECT` на `autotrade_shop`, `autotrade_item`
  и `char` (для имени продавца).
