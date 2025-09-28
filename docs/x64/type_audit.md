# x64 Type Audit

Ниже приведены места в исходном коде, где использование 32-битных типов может привести к проблемам при переносе на x64. Формат записей: `файл:строка — описание риска`.

## Таймеры, тики и счётчики
- src/common/timer.h:24 — макрос `DIFF_TICK` отбрасывает разницу тиков до `int`, что ограничивает диапазон 32 битами.
- src/common/timer.h:30 — тип `TimerFunc` передаёт значение тика как `unsigned int`, что не выдержит 64-битного времени работы.
- src/common/timer.h:47 — прототип `add_timer` принимает тик как `unsigned int`, урезая 64-битные значения.
- src/common/timer.h:48 — `add_timer_interval` также оперирует 32-битным тиком и интервалом.
- src/common/timer.h:51 — `addtick_timer` хранит тики в `unsigned int`, что приведёт к переполнению.
- src/common/timer.h:52 — `settick_timer` принимает `unsigned int tick`, ограничивая диапазон.
- src/common/timer.c:250 — реализация `add_timer_interval` использует `unsigned int tick`, так что даже при изменении прототипа потребуется переписать тело.
- src/common/timer.c:300 — `settick_timer` работает с `unsigned int tick` и локальным `unsigned int old_tick`, что ломается при 64-битных тиках.
- src/common/timer.c:303 — локальный `unsigned int old_tick` сохраняет прошлое время, теряя старшие биты 64-битных значений.
- src/common/timer.c:316 — сравнение через `DIFF_TICK` возвращает `int`, что переполнится на длинных аптаймах.
- src/common/socket.c:806 — таймер `connect_check_clear` получает `unsigned int tick`, поэтому история соединений не работает на 64-битных тиках.
- src/map/clif.h:98 — API `clif_clearunit_delayed` принимает `unsigned int tick`, ограничивая время отложенного удаления.
- src/map/clif.h:122 — `clif_damage` передаёт тики как `unsigned int`, из-за чего длительные задержки переполняются.
- src/map/map.c:445 — `map_moveblock` принимает `unsigned int tick`, из-за чего события перемещения зависят от 32-битного диапазона.
- src/map/status.c:7105 — глобальные `unsigned int` тиков регенерации (`natural_heal_prev_tick`) не выдержат 64-битного времени.

## Размеры буферов и длины
- src/char/char.h:27 — `mapif_sendall` принимает длину буфера как `unsigned int`, что ломает передачи >4 ГБ.
- src/char/char.h:28 — `mapif_sendallwos` использует `unsigned int len` и ограничивает длину пакета.
- src/char/char.h:29 — `mapif_send` также принимает `unsigned int len`, отбрасывая старшие биты `size_t`.
- src/char/char.c:3848 — реализация `mapif_sendall` оперирует `unsigned int len`, требуя обновления под `size_t`.
- src/char/char.c:3867 — `mapif_sendallwos` в коде использует 32-битную длину при отправке пакетов.
- src/char/char.c:3885 — `mapif_send` внутри ограничивает длину `unsigned int`.
- src/common/socket.c:412 — `realloc_fifo` принимает размеры FIFO как `unsigned int`, что запрещает буферы >4 ГБ.
- src/common/db.c:2268 — сравнение `strlen(...) >= (unsigned int)srcsize` хранит размер буфера в `unsigned int`.
- src/map/script.c:8169 — `clif_announce` получает `(int)strlen(str)+1`, что обрезает длину строки до 32 бит.
- src/map/script.c:8171 — `clif_GMmessage` получает длину сообщения как `int`, теряя значения `size_t`.
- src/map/script.c:8174 — `intif_announce` также получает длину через `(int)strlen`.
- src/map/script.c:8176 — `intif_GMmessage` отбрасывает длину до `int`.
- src/map/script.c:11803 — `getstrlen` сохраняет результат `strlen` в `int len`, урезая длины >2^31.
- src/login/login.c:2488 — проверки `(int)RFIFOREST(fd)` сравнивают размеры буфера с 32-битным кастом.
- src/char/inter.c:726 — аналогичная проверка `RFIFOREST` кастует к `int`, ломая большие пакеты.

## Преобразования указателей и идентификаторов
- src/common/db.h:499 — макрос `i2key` приводит ключ к `(int)`, отбрасывая верхние биты указателя/идентификатора.
- src/common/timer.c:256 — сообщения об ошибках приводят `TimerFunc` к `(int)`, что теряет адрес функции.
- src/common/timer.c:275 — `delete_timer` форматирует `func` через `(int)`, укорачивая указатель.
- src/common/timer.c:318 — `settick_timer` печатает `timer_data[tid].func` как `(int)`, обрезая адрес.
- src/map/guild.c:1838 — `memcpy` вычисляет смещение через `(int)&c->guild_id - (int)c`, полагаясь на 32-битные указатели.
- src/map/guild.c:1928 — `add_timer` передаёт имя события `(int)evname`, обрезая указатель на строку.
- src/map/clif.c:708 — `add_timer` получает `(int)tbl`, теряя 64-битный адрес копии блока.
- src/map/battle.c:196 — `add_timer` передаёт `(int)dat`, хотя `dat` — указатель на структуру.
- src/map/mob.c:1982 — `add_timer` кладёт `(int)dlist`, что ломает указатель на список дропа.
- src/map/mob.c:1996 — повторная постановка таймера с `(int)dlist` также обрезает указатель.
- src/map/pet.c:1081 — `add_timer` получает `(int)dlist`, урезая адрес списка добычи питомца.
- src/map/npc.c:284 — локальная переменная `int pos = (int)data` хранит указатель в `int`.
- src/map/npc.c:470 — `npc_event_timer` вызывает `add_timer` с `(int)evname`, обрезая строковый указатель.
- src/map/npc.c:614 — `add_timer(...,(int)ted)` сохраняет указатель сценария в `int`.
- src/map/npc.c:686 — аналогично, `(int)ted` при повторной установке таймера.
- src/map/npc.c:1187 — `ShowDebug` печатает `sd->npc_id` через `(int)`, что ломает 64-битные идентификаторы.
- src/map/script.c:4670 — `script_pushint(st,(int)st->script)` записывает указатель на байткод в 32-битное значение.
- src/map/script.c:4671 — `script_pushint(st,(int)st->stack->var_function)` обрезает указатель таблицы переменных.
- src/map/script.c:4721 — повторно сохраняет `st->script` как `(int)`.
- src/map/script.c:4722 — повторное сохранение `var_function` как `(int)`.
- src/map/script.c:7502 — `script_pushint(st,(int)time(NULL))` обрезает 64-битный `time_t`.
- src/map/script.c:7513 — `script_pushint(st,gettick())` кладёт 32-битный тик в скриптовый стек без расширения до 64 бит.
- src/map/guild.c:207 — `db_alloc(..., sizeof(int))` используется для таблиц с ключами, что предполагает 32-битные идентификаторы.
- src/common/socket.c:295 — преобразование `socket` к `(int)` фиксирует файловые дескрипторы как 32-битные.
- src/common/socket.c:345 — аналогичное преобразование в другой ветке инициализации сокета.
- src/map/intif.c:924 — `min_gm_level = (int)RFIFOW(fd,28);` предполагает, что идентификатор помещается в 32 бита.
- src/char/char.c:3018 — `char_loadName((int)RFIFOL(fd,2), ...)` кастует идентификатор персонажа к `int`, что не выдержит 64-битные ID.

## Работа с базами данных и идентификаторами
- src/login_sql/login.c:432 — `int id = (int)mysql_insert_id(&mysql_handle);` усечёт 64-битный автоинкремент.
- src/char_sql/int_party.c:148 — `party_id = p->party_id = (int)mysql_insert_id(&mysql_handle);` обрезает 64-битный идентификатор партии.
- src/char_sql/int_pet.c:48 — `p->pet_id = pet_id = (int)mysql_insert_id(&mysql_handle);` урезает ID питомца до 32 бит.
- src/char_sql/int_guild.c:170 — `g->guild_id = (int)mysql_insert_id(&mysql_handle);` теряет старшие биты ID гильдии.
- src/char_sql/int_homun.c:120 — `hd->hom_id = (int)mysql_insert_id(&mysql_handle);` обрезает ID гомункулуса.
- src/common/db.c:671 — сравнение с `(unsigned int)~0` предполагает 32-битный диапазон счётчика.
- src/common/db.c:685 — проверка `free_count == (unsigned int)~0` также завязана на 32 бита.
- src/common/db.c:691 — присвоение `free_max = (unsigned int)~0` фиксирует максимальный размер пула как 32-битный.
- src/common/db.c:717 — цикл `unsigned int i` ограничивает размер базы 32 битами.
- src/char/int_guild.c:1219 — `g->member[i].exp = *((unsigned int*)data);` предполагает, что опыт участника умещается в 32 бита.
- src/common/malloc.h:159 — `unsigned int malloc_usage(void);` возвращает использование памяти в 32 битах, что переполнится на x64.

