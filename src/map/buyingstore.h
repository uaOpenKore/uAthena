// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// [Backport] Buying Store (skup via shop) from eAthena, adapted to uAthena.
// The merchant posts a list of items he wants to BUY for zeny; other players
// sell those items to him. Mirror of vending (which sells). Engine is UI-
// agnostic: driven by chat atcommands on PACKETVER 7 (no native window), and
// the clif_buyingstore_* hooks send native packets on clients >= 2010.

#ifndef _BUYINGSTORE_H_
#define _BUYINGSTORE_H_

struct map_session_data;

// constants (client-side restrictions, kept identical to eAthena)
#define BUYINGSTORE_MAX_PRICE 99990000
#define BUYINGSTORE_MAX_AMOUNT 9999

// failure constants for clif/feedback
enum e_buyingstore_failure
{
	BUYINGSTORE_CREATE               = 1,  // "Failed to open buying store."
	BUYINGSTORE_CREATE_OVERWEIGHT    = 2,  // overweight
	BUYINGSTORE_TRADE_BUYER_ZENY     = 3,  // buyer hit zeny limit
	BUYINGSTORE_TRADE_BUYER_NO_ITEMS = 4,  // everything was bought
	BUYINGSTORE_TRADE_SELLER_FAILED  = 5,  // generic seller failure
	BUYINGSTORE_TRADE_SELLER_COUNT   = 6,  // amount higher than wanted
	BUYINGSTORE_TRADE_SELLER_ZENY    = 7,  // buyer lacks balance
	BUYINGSTORE_CREATE_NO_INFO       = 8,
};

bool buyingstore_setup(struct map_session_data* sd, unsigned char slots);
void buyingstore_create(struct map_session_data* sd, int zenylimit, unsigned char result, const char* storename, const unsigned char* itemlist, unsigned int count);
void buyingstore_close(struct map_session_data* sd);
void buyingstore_open(struct map_session_data* sd, int account_id);
void buyingstore_trade(struct map_session_data* sd, int account_id, unsigned int buyer_id, const unsigned char* itemlist, unsigned int count);

#endif  // _BUYINGSTORE_H_
