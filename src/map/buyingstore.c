// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// [Backport] Buying Store engine, ported from eAthena and adapted to uAthena:
//  - older string-based log API (log_pick_pc/log_zeny with type "B")
//  - pc_can_give_items() has inverted semantics here (TRUE => GM is restricted)
//  - no searchstore / no CELL_CHKNOVENDING (only map flag.novending)
//  - dropped the eAthena "owner must already own one of each item" requirement
//    (made no sense for a buying store; weight is still pre-checked)

#include "../common/cbasetypes.h"
#include "../common/db.h"      // ARR_FIND
#include "../common/nullpo.h"  // nullpo_*
#include "../common/showmsg.h" // ShowWarning
#include "../common/socket.h"  // RBUF*
#include "../common/strlib.h"  // safestrncpy
#include "atcommand.h"         // msg_txt
#include "battle.h"            // battle_config.*
#include "buyingstore.h"
#include "clif.h"              // clif_buyingstore_*
#include "itemdb.h"            // itemdb_*
#include "log.h"               // log_pick_pc, log_zeny
#include "map.h"               // map[], map_id2sd
#include "pc.h"                // struct map_session_data

#include <string.h>

static unsigned int buyingstore_nextid = 0;
static const short buyingstore_blankslots[MAX_SLOTS] = { 0 };  // for blank-card check

/// Returns a unique (small) buying store id, used as the chat handle in @sellto.
static unsigned int buyingstore_getuid(void)
{
	return ++buyingstore_nextid;  // start at 1 so 0 always means "no store"
}


bool buyingstore_setup(struct map_session_data* sd, unsigned char slots)
{
	nullpo_retr(false, sd);

	if( !battle_config.feature_buying_store || sd->vender_id || sd->state.buyingstore || sd->state.trading || slots == 0 )
		return false;

	if( sd->sc.count && sd->sc.data[SC_NOCHAT].timer != -1 && (sd->sc.data[SC_NOCHAT].val1&MANNER_NOROOM) )
		return false; // muted

	if( map[sd->bl.m].flag.novending )
	{
		clif_displaymessage(sd->fd, msg_txt(276)); // "You can't open shop on this map"
		return false;
	}

	if( slots > MAX_BUYINGSTORE_SLOTS )
	{
		ShowWarning("buyingstore_setup: Requested %d slots, but server supports only %d slots.\n", (int)slots, MAX_BUYINGSTORE_SLOTS);
		slots = MAX_BUYINGSTORE_SLOTS;
	}

	sd->buyingstore.slots = slots;
	clif_buyingstore_open(sd); // native client window (no-op on PACKETVER 7)

	return true;
}


void buyingstore_create(struct map_session_data* sd, int zenylimit, unsigned char result, const char* storename, const unsigned char* itemlist, unsigned int count)
{
	unsigned int i, weight, listidx;
	struct item_data* id;

	nullpo_retv(sd);

	if( !result || count == 0 )
		return; // canceled or no items

	if( !battle_config.feature_buying_store || sd->state.trading || sd->buyingstore.slots == 0 || count > sd->buyingstore.slots || zenylimit <= 0 || zenylimit > sd->status.zeny || !storename[0] )
	{
		sd->buyingstore.slots = 0;
		clif_buyingstore_open_failed(sd, BUYINGSTORE_CREATE, 0);
		return;
	}

	if( pc_can_give_items(pc_isGM(sd)) )
	{// GM not allowed to give zeny
		sd->buyingstore.slots = 0;
		clif_displaymessage(sd->fd, msg_txt(246));
		clif_buyingstore_open_failed(sd, BUYINGSTORE_CREATE, 0);
		return;
	}

	if( sd->sc.count && sd->sc.data[SC_NOCHAT].timer != -1 && (sd->sc.data[SC_NOCHAT].val1&MANNER_NOROOM) )
		return; // muted

	if( map[sd->bl.m].flag.novending )
	{
		clif_displaymessage(sd->fd, msg_txt(276));
		return;
	}

	weight = sd->weight;

	// check item list
	for( i = 0; i < count; i++ )
	{// itemlist: <name id>.W <amount>.W <price>.L
		unsigned short nameid, amount;
		int price;

		nameid = RBUFW(itemlist,i*8+0);
		amount = RBUFW(itemlist,i*8+2);
		price  = RBUFL(itemlist,i*8+4);

		if( ( id = itemdb_exists(nameid) ) == NULL || amount == 0 )
			break;

		if( price <= 0 || price > BUYINGSTORE_MAX_PRICE )
			break; // unlike vending, items cannot be bought at 0 zeny

		if( ( battle_config.buyingstore_restrict_items && !id->flag.buyingstore ) || !itemdb_cantrade_sub(id, pc_isGM(sd), pc_isGM(sd)) )
			break; // restricted (when whitelist enabled) or character-bound item

		if( amount > BUYINGSTORE_MAX_AMOUNT )
			break;

		if( i )
		{// duplicate check
			ARR_FIND( 0, i, listidx, sd->buyingstore.items[listidx].nameid == nameid );
			if( listidx != i )
			{
				ShowWarning("buyingstore_create: Found duplicate item on buying list (nameid=%hu, amount=%hu, account_id=%d, char_id=%d).\n", nameid, amount, sd->status.account_id, sd->status.char_id);
				break;
			}
		}

		weight += id->weight*amount;
		sd->buyingstore.items[i].nameid = nameid;
		sd->buyingstore.items[i].amount = amount;
		sd->buyingstore.items[i].price  = price;
	}

	if( i != count )
	{// invalid item/amount/price
		sd->buyingstore.slots = 0;
		clif_buyingstore_open_failed(sd, BUYINGSTORE_CREATE, 0);
		return;
	}

	if( (sd->max_weight*90)/100 < weight )
	{// would go overweight (>90%) if all wanted items were bought
		sd->buyingstore.slots = 0;
		clif_buyingstore_open_failed(sd, BUYINGSTORE_CREATE_OVERWEIGHT, weight);
		return;
	}

	// success
	sd->state.buyingstore = 1;
	sd->buyer_id = buyingstore_getuid();
	sd->buyingstore.zenylimit = zenylimit;
	sd->buyingstore.slots = i; // actual amount of items
	safestrncpy(sd->message, storename, sizeof(sd->message));
	clif_buyingstore_myitemlist(sd);
	clif_buyingstore_entry(sd);
}


void buyingstore_close(struct map_session_data* sd)
{
	if( sd->state.buyingstore )
	{
		sd->state.buyingstore = 0;
		sd->buyer_id = 0;
		memset(&sd->buyingstore, 0, sizeof(sd->buyingstore));
		clif_buyingstore_disappear_entry(sd);
	}
}


void buyingstore_open(struct map_session_data* sd, int account_id)
{
	struct map_session_data* pl_sd;

	nullpo_retv(sd);

	if( !battle_config.feature_buying_store || sd->state.trading )
		return;

	if( pc_can_give_items(pc_isGM(sd)) )
	{// GM not allowed to sell
		clif_displaymessage(sd->fd, msg_txt(246));
		return;
	}

	if( ( pl_sd = map_id2sd(account_id) ) == NULL || !pl_sd->state.buyingstore )
		return; // not online or not buying

	if( sd->bl.m != pl_sd->bl.m || !check_distance_bl(&sd->bl, &pl_sd->bl, AREA_SIZE) )
		return; // out of view range

	clif_buyingstore_itemlist(sd, pl_sd);
}


void buyingstore_trade(struct map_session_data* sd, int account_id, unsigned int buyer_id, const unsigned char* itemlist, unsigned int count)
{
	int zeny = 0;
	unsigned int i, weight, listidx, k;
	struct map_session_data* pl_sd;

	nullpo_retv(sd);

	if( count == 0 )
		return;

	if( !battle_config.feature_buying_store || sd->state.trading )
	{
		clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, 0);
		return;
	}

	if( pc_can_give_items(pc_isGM(sd)) )
	{// GM not allowed to sell
		clif_displaymessage(sd->fd, msg_txt(246));
		clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, 0);
		return;
	}

	if( ( pl_sd = map_id2sd(account_id) ) == NULL || !pl_sd->state.buyingstore || pl_sd->buyer_id != buyer_id )
	{// not online, not buying or different store
		clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, 0);
		return;
	}

	if( sd->bl.id == pl_sd->bl.id )
	{// cannot sell to own store
		clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, 0);
		return;
	}

	if( sd->bl.m != pl_sd->bl.m || !check_distance_bl(&sd->bl, &pl_sd->bl, AREA_SIZE) )
	{// out of view range
		clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, 0);
		return;
	}

	if( pl_sd->status.zeny < pl_sd->buyingstore.zenylimit )
		pl_sd->buyingstore.zenylimit = pl_sd->status.zeny; // buyer lost zeny meanwhile

	weight = pl_sd->weight;

	// check item list
	for( i = 0; i < count; i++ )
	{// itemlist: <index>.W <name id>.W <amount>.W
		unsigned short nameid, amount;
		int index;

		index  = RBUFW(itemlist,i*6+0)-2;
		nameid = RBUFW(itemlist,i*6+2);
		amount = RBUFW(itemlist,i*6+4);

		if( i )
		{// duplicate check
			ARR_FIND( 0, i, k, (int)(RBUFW(itemlist,k*6+0)-2) == index );
			if( k != i )
			{
				clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, nameid);
				return;
			}
		}

		if( index < 0 || index >= MAX_INVENTORY || sd->inventory_data[index] == NULL || sd->status.inventory[index].nameid != nameid || sd->status.inventory[index].amount < amount )
		{
			clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, nameid);
			return;
		}

		if( sd->status.inventory[index].expire_time || !itemdb_cantrade(&sd->status.inventory[index], pc_isGM(sd), pc_isGM(pl_sd)) || memcmp(sd->status.inventory[index].card, buyingstore_blankslots, sizeof(buyingstore_blankslots)) )
		{// non-tradable / rental / carded item
			clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, nameid);
			return;
		}

		ARR_FIND( 0, pl_sd->buyingstore.slots, listidx, pl_sd->buyingstore.items[listidx].nameid == nameid );
		if( listidx == pl_sd->buyingstore.slots || pl_sd->buyingstore.items[listidx].amount == 0 )
		{// no such item or already fully bought
			clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, nameid);
			return;
		}

		if( pl_sd->buyingstore.items[listidx].amount < amount )
		{// buyer does not want that much
			clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_COUNT, nameid);
			return;
		}

		if( pc_checkadditem(pl_sd, nameid, amount) == ADDITEM_OVERAMOUNT )
		{// buyer has no space
			clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, nameid);
			return;
		}

		if( amount*(unsigned int)sd->inventory_data[index]->weight > pl_sd->max_weight-weight )
		{// buyer would go overweight
			clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_FAILED, nameid);
			return;
		}
		weight += amount*sd->inventory_data[index]->weight;

		if( amount*pl_sd->buyingstore.items[listidx].price > pl_sd->buyingstore.zenylimit-zeny )
		{// buyer lacks zeny
			clif_buyingstore_trade_failed_seller(sd, BUYINGSTORE_TRADE_SELLER_ZENY, nameid);
			return;
		}
		zeny += amount*pl_sd->buyingstore.items[listidx].price;
	}

	// process item list (all checks passed: commit atomically)
	for( i = 0; i < count; i++ )
	{
		unsigned short nameid, amount;
		int index;

		index  = RBUFW(itemlist,i*6+0)-2;
		nameid = RBUFW(itemlist,i*6+2);
		amount = RBUFW(itemlist,i*6+4);

		ARR_FIND( 0, pl_sd->buyingstore.slots, listidx, pl_sd->buyingstore.items[listidx].nameid == nameid );
		zeny = amount*pl_sd->buyingstore.items[listidx].price;

		// log (B)uying store
		if( log_config.enable_logs&LOG_VENDING )
		{
			log_pick_pc(sd,    "B", nameid, -((int)amount), &sd->status.inventory[index]);
			log_pick_pc(pl_sd, "B", nameid,    (int)amount, &sd->status.inventory[index]);
		}
		if( log_config.zeny > 0 )
			log_zeny(sd, "B", pl_sd, zeny);

		// move item: seller inventory -> buyer inventory
		pc_additem(pl_sd, &sd->status.inventory[index], amount);
		pc_delitem(sd, index, amount, 1);
		pl_sd->buyingstore.items[listidx].amount -= amount;

		// pay up: buyer -> seller
		pc_payzeny(pl_sd, zeny);
		pc_getzeny(sd, zeny);
		pl_sd->buyingstore.zenylimit -= zeny;

		// notify clients (no-op on PACKETVER 7)
		clif_buyingstore_delete_item(sd, index, amount, pl_sd->buyingstore.items[listidx].price);
		clif_buyingstore_update_item(pl_sd, nameid, amount);
	}

	// anything left to buy?
	ARR_FIND( 0, pl_sd->buyingstore.slots, i, pl_sd->buyingstore.items[i].amount != 0 );
	if( i == pl_sd->buyingstore.slots )
		clif_buyingstore_trade_failed_buyer(pl_sd, BUYINGSTORE_TRADE_BUYER_NO_ITEMS);
	else if( pl_sd->buyingstore.zenylimit == 0 )
		clif_buyingstore_trade_failed_buyer(pl_sd, BUYINGSTORE_TRADE_BUYER_ZENY);
	else
		return; // continue buying

	// cannot continue buying
	buyingstore_close(pl_sd);

	if( pl_sd->state.autotrade )
		map_quit(pl_sd);
}
