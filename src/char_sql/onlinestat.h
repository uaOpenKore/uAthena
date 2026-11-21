// Online statistics (S. 2026-11-21): the minutes each character spends on a map-server (autotrade shops do not
// count) and the minutes paid with @buyplaytime / @autopay, per character and server date, for the web site.
// Kept apart from the play-time limit (char.play_minutes goes down when time is bought). Not in SQL: the
// char-server samples who is online every minute, hands the sums to a worker thread every
// onlinestat_interval seconds; the worker appends them to its spool file and pushes the file into MongoDB
// (uaro.online_daily, one document per character and day, $inc), emptying the file once Mongo took it. With
// Mongo down the file just grows and goes in at the next connection; nothing in the game waits for Mongo.
#ifndef _ONLINESTAT_H_
#define _ONLINESTAT_H_

#define ONLINESTAT_CONF_NAME "conf/mongo_athena.conf"

// Reads conf/mongo_athena.conf (and its import, conf/mongo_conf.txt with the credentials).
void onlinestat_read_conf(const char* path, int depth);

// Starts the worker (and the per-minute sampling timer) when onlinestat_mongo_uri is set.
void onlinestat_init(void);

// The last minutes to the file (and Mongo, if it answers within a few seconds); stops the worker.
void onlinestat_final(void);

// One sampled online minute of a character (date = server date YYYYMMDD; name in cp1251).
void onlinestat_add(int date, int char_id, int account_id, const char* name, int online, int paid_buy, int paid_auto);

#endif /* _ONLINESTAT_H_ */
