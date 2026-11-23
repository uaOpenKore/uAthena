# ID в базе игры нестабильны: как сайту искать аккаунты, чаров и имущество

Для программиста сайта. База игры: MySQL (Percona 5.7), таблицы InnoDB, кодировка cp1251.

## Почему ID нельзя хранить на сайте
- **При каждом старте чар-сервера** (обычно после ежемесячной перезагрузки) ID перенумеровываются подряд, чтобы
  закрыть дырки после удалений (`Doc/id_compact.md`). Меняются: `char_id`, `guild_id`, `party_id`, `pet_id`,
  `homun_id`, `mer_id`, номера строк вещей (`inventory.id`, `cart_inventory.id`, `storage.id`, `guild_storage.id`),
  `memo_id`, и `account_id` (если появились дырки).
- **Архив:** аккаунт, давно не заходивший, уходит в архив, а при возврате получает **новые** `account_id` и
  `char_id` (`Doc/account_archive.md`).

Поэтому:
1. **На сайте храните только стабильные ключи**: логин аккаунта (`login.userid`), имя персонажа (`char.name`),
   имя гильдии (`guild.name`), имя пати (`party.name`). Они уникальны: сервер не даёт создать второй такой же
   (и не отдаёт имена и логины из архива).
2. **ID получайте запросом в момент работы** и используйте только внутри этого же запроса или запроса страницы.
   Не кладите `char_id`/`account_id` в свою базу, кэш, ссылки или cookies.
3. Лучше всего: **один запрос с подзапросом по имени**. Тогда между «узнал ID» и «использовал ID» не может
   пройти рестарт.

## Стабильные ключи
| что | стабильный ключ | ID (нестабильный) |
|---|---|---|
| аккаунт | `login.userid` | `login.account_id` |
| персонаж | `char.name` | `char.char_id` |
| гильдия | `guild.name` | `guild.guild_id` |
| пати | `party.name` | `party.party_id` |
| питомец | нет: через хозяина (`pet.char_id`) | `pet.pet_id` |
| гомункул | нет: через хозяина (`char.homun_id`) | `homunculus.homun_id` |
| вещь | нет: только «подпись» (`nameid`, `refine`, `attribute`, `card0..3`) + место | `id` строки |

Имена в базе в **cp1251**: подключайтесь с `SET NAMES cp1251` или перекодируйте параметры.
Сравнение логинов по умолчанию **без учёта регистра** (как на сервере).

## Примеры запросов

### Аккаунт
```sql
-- ID аккаунта по логину
SELECT account_id FROM login WHERE userid = ?;

-- данные аккаунта (без пароля!)
SELECT userid, email, sex, level AS gm_level, lastlogin, logincount, state, ban_until
FROM login WHERE userid = ?;
```

### Персонажи
```sql
-- все персонажи аккаунта
SELECT name, class, base_level, job_level, zeny, last_map, online
FROM `char`
WHERE account_id = (SELECT account_id FROM login WHERE userid = ?)
ORDER BY char_num;

-- логин аккаунта, которому принадлежит персонаж
SELECT l.userid FROM login l JOIN `char` c ON c.account_id = l.account_id WHERE c.name = ?;

-- кто сейчас онлайн
SELECT name, base_level, last_map FROM `char` WHERE online = 1 ORDER BY name;
```

### Инвентарь персонажа
```sql
SELECT i.nameid, d.name_japanese AS item, i.amount, i.refine, i.attribute,
       i.card0, i.card1, i.card2, i.card3, i.equip, i.expire_time
FROM inventory i
LEFT JOIN item_db d ON d.id = i.nameid
WHERE i.char_id = (SELECT char_id FROM `char` WHERE name = ?);
```
`equip <> 0` — вещь надета, `expire_time <> 0` — аренда.
Названия предметов: таблица `item_db` (если она заполнена у вас в базе; сервер берёт предметы из
`db/item_db.txt` + `item_db2.txt`, так что таблицу надо обновлять вместе с ними).

### Тележка персонажа
```sql
SELECT nameid, amount, refine, attribute, card0, card1, card2, card3
FROM cart_inventory
WHERE char_id = (SELECT char_id FROM `char` WHERE name = ?);
```

### Склад Кафры (один на аккаунт)
```sql
-- по логину
SELECT nameid, amount, refine, attribute, card0, card1, card2, card3
FROM storage
WHERE account_id = (SELECT account_id FROM login WHERE userid = ?);

-- по имени любого персонажа аккаунта
SELECT s.nameid, s.amount, s.refine, s.card0, s.card1, s.card2, s.card3
FROM storage s
WHERE s.account_id = (SELECT account_id FROM `char` WHERE name = ?);
```

### Гильдия и гильд-склад
```sql
-- гильдия персонажа
SELECT g.name, g.master, g.guild_lv, g.connect_member, g.max_member
FROM guild g
WHERE g.guild_id = (SELECT guild_id FROM `char` WHERE name = ?);

-- члены гильдии по её имени
SELECT m.name, m.class, m.lv, m.online, p.name AS position
FROM guild_member m
LEFT JOIN guild_position p ON p.guild_id = m.guild_id AND p.position = m.position
WHERE m.guild_id = (SELECT guild_id FROM guild WHERE name = ?)
ORDER BY m.position, m.name;

-- гильд-склад по имени гильдии
SELECT nameid, amount, refine, attribute, card0, card1, card2, card3
FROM guild_storage
WHERE guild_id = (SELECT guild_id FROM guild WHERE name = ?);

-- гильд-склад гильдии персонажа
SELECT gs.nameid, gs.amount, gs.refine, gs.card0, gs.card1, gs.card2, gs.card3
FROM guild_storage gs
WHERE gs.guild_id = (SELECT guild_id FROM `char` WHERE name = ? AND guild_id > 0);

-- замки гильдии
SELECT castle_id FROM guild_castle WHERE guild_id = (SELECT guild_id FROM guild WHERE name = ?);
```

### Пати
```sql
SELECT c.name, c.base_level, c.online
FROM `char` c
WHERE c.party_id = (SELECT party_id FROM party WHERE name = ?) AND c.party_id > 0;
```

### Питомцы и гомункул персонажа
```sql
-- питомцы (вылупленный и в яйцах), записанные на персонажа
SELECT p.name, p.class, p.level, p.intimate, p.incuvate
FROM pet p WHERE p.char_id = (SELECT char_id FROM `char` WHERE name = ?);

-- гомункул
SELECT h.name, h.class, h.level, h.intimacy
FROM homunculus h
WHERE h.homun_id = (SELECT homun_id FROM `char` WHERE name = ? AND homun_id > 0);
```

### Создатель кованой/сваренной вещи
`card0` = 255 или 254, создатель = `card2 | card3<<16` (16-битные знаковые половинки):
```sql
SELECT i.nameid, c.name AS maker
FROM inventory i
LEFT JOIN `char` c ON c.char_id = ((i.card2 & 0xFFFF) | ((i.card3 & 0xFFFF) << 16))
WHERE i.char_id = (SELECT char_id FROM `char` WHERE name = ?) AND i.card0 IN (255, 254);
```
Если создатель удалён или в архиве, `maker` будет NULL. После сдвига ID сервер переписывает и эти ссылки.

### Лавки автотрейда
Поиск по товарам: `Doc/autotrade_tables.md`. Продавца берите по имени:
```sql
SELECT c.name, s.map, s.x, s.y, s.title, i.nameid, i.amount, i.price
FROM autotrade_shop s
JOIN `char` c ON c.char_id = s.char_id
JOIN autotrade_item i ON i.char_id = s.char_id
WHERE i.nameid = ?
ORDER BY i.price;
```

## Изменение имущества: только заявки
Сайт **не пишет** в таблицы вещей (`Doc/web_storage.md`). Заявку тоже создавайте **одним запросом с
подзапросами**, чтобы ID взялись в момент вставки:
```sql
-- выдать 5 Red Potion персонажу «Имя» в инвентарь (магазин сайта)
INSERT INTO web_storage_request (account_id, char_id, op, dst, nameid, amount, note)
SELECT c.account_id, c.char_id, 'add', 'inventory', 501, 5, 'shop order #123'
FROM `char` c WHERE c.name = ?;

-- взять 10 Red Potion из гильд-склада персонажа в его Кафру
INSERT INTO web_storage_request (account_id, char_id, op, src, dst, nameid, amount, note)
SELECT c.account_id, c.char_id, 'move', 'guild_storage', 'storage', 501, 10, 'site'
FROM `char` c WHERE c.name = ? AND c.guild_id > 0;
```
Проверить заявку по её `id` (номер заявки не меняется) или по `note`:
```sql
SELECT status, result, done_at FROM web_storage_request WHERE id = ?;
```
Если сервер перезапустился, пока заявка ждала, её `account_id`/`char_id` он **сам перепишет** на новые
вместе со всеми таблицами. Выполненные заявки удалённых персонажей при этом удаляются.

## Статистика онлайна (Монга)
`uaro.online_daily` хранит `char_id`, `account_id` и `name` на тот день. После сдвига ID старые документы
остаются со старыми номерами. Группируйте и ищите по **`name`** (`Doc/onlinestat_mongo.md`), а не по `char_id`.

## Коротко
- Сайт знает игрока по **логину**, персонажа по **имени**, гильдию и пати по **имени**.
- ID только через подзапрос в том же запросе.
- Вещи меняются только заявками.
