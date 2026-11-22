# Лимит игрового времени / Daily play-time limit

## Русский

**Каждому персонажу даётся 8 часов игры в сутки.** Лимит у каждого персонажа свой, а не общий на аккаунт.

**Что считается**
- Считается только время, когда персонаж в игре на карте.
- Выбор персонажа, загрузка и лавка на автотрейде в лимит не входят.
- Считаются целые минуты.

**Когда обнуляется.** Каждый день в 00:00 по времени сервера.

**Предупреждения.** За 30, 10 и 1 минуту до конца лимита в чат приходит сообщение. Когда время вышло, игра сообщит об этом и через 40 секунд отключит. Войти этим персонажем снова можно будет после 00:00. Другие персонажи аккаунта играют по своему лимиту.

**Команды**
- `@playtime`: сколько сыграно сегодня, сколько осталось и когда обнулится.
- `@buyplaytime <минуты>`: выкупить сыгранные минуты за зени. Цена **5 зени × базовый уровень** за минуту: персонажу 50 уровня одна минута стоит 250 зени, час стоит 15 000. Выкупить можно только уже сыгранные минуты. Если лимит уже вышел, покупка отменяет отключение.
- `@autopay on`: дальше каждая сыгранная минута сразу оплачивается зени по той же цене и **не тратит лимит**. Оплата идёт с первой же минуты, так что следи за зени.
  - `@autopay off` выключает оплату, `@autopay` показывает, включена ли она и цену.
  - Настройка сохраняется после выхода из игры.
  - Если зени не хватает на следующую минуту, оплата выключается сама с сообщением в чате, и минуты снова идут в лимит.

## English

**Each character gets 8 hours of play a day.** The limit is per character, not shared across the account.

**What counts**
- Only the time your character is in the game on a map.
- Character select, loading and an autotrade shop do not count.
- Whole minutes are counted.

**When it resets.** Every day at 00:00 server time.

**Warnings.** At 30, 10 and 1 minute left you get a chat message. When the time is up, the game tells you and disconnects you 40 seconds later. That character can log in again after 00:00. Your other characters play on their own limits.

**Commands**
- `@playtime`: how long you played today, how much is left and when it resets.
- `@buyplaytime <minutes>`: buy back played minutes for zeny. The price is **5 zeny × base level** a minute: for a level 50 character one minute costs 250 zeny, an hour 15,000. You can only buy back minutes you have already played. If your time is already up, buying cancels the disconnect.
- `@autopay on`: from then on, every minute you play is paid in zeny at the same price and **does not use up the limit**. Payment starts with the very first minute, so watch your zeny.
  - `@autopay off` turns it off, and `@autopay` shows whether it is on and the price.
  - The setting is kept when you log out.
  - If you don't have enough zeny for the next minute, it turns itself off with a chat message, and your minutes count against the limit again.
