// Copyright (c) uAthena / bornrok.com
// Discord webhook relay: a background thread that POSTs queued text lines to a configured
// Discord incoming-webhook (used to mirror rare-drop global announces). All public calls are
// non-blocking and safe from the single map game loop; everything is a no-op until configured.
#ifndef _DISCORD_H_
#define _DISCORD_H_

void discord_init(void);              // read conf/discord.conf, start the worker if enabled
void discord_final(void);             // stop and join the worker thread
void discord_announce(const char* text);  // enqueue one line for delivery (fire-and-forget)

#endif /* _DISCORD_H_ */
