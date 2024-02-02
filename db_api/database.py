from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.future import select
from db_api import sqlalchemy_
from db_api.models import Wallet, Base
from data.config import WALLETS_DB
from sqlalchemy import and_, or_


db = sqlalchemy_.DB(f'sqlite+aiosqlite:///{WALLETS_DB}', pool_recycle=3600, connect_args={'check_same_thread': False})


async def get_account(private_key: str) -> Optional[Wallet]:
    return await db.one(Wallet, Wallet.private_key == private_key)


async def get_accounts(
        faucet: bool = False,
        twitter: bool = False,
        check_balance: bool = False,
        registration: bool = False,
        daily_mint: bool = False,
        onchain: bool = False,
        galxy_second_nft: bool = False,
) -> List[Wallet]:
    if faucet:
        query = select(Wallet).where(
            Wallet.next_available_claim == 0
            #Wallet.next_available_claim <= int(time.time())
        )
    elif twitter:
        query = select(Wallet).where(
            #Wallet.twitter_account_status == "OK",
            Wallet.follow_and_retweet == False
        )
    elif check_balance:
        query = select(Wallet).where(
            Wallet.next_available_claim != 0
        )
    elif registration:
        query = select(Wallet).where(
            Wallet.register == False
        )
    elif daily_mint:
        today = datetime.now(timezone.utc).date()
        query = select(Wallet).where(
            Wallet.galxe_daily_claim < today
        )
    elif onchain:
        query = select(Wallet).where(
            Wallet.next_available_claim != 0,
            Wallet.finished_onchain == False
        )
    elif galxy_second_nft:
        query = select(Wallet).where(
            Wallet.finished_onchain == True,
            Wallet.twitter_account_status == 'OK',
            Wallet.finished_claim_second_nft == False
        )
    else:
        query = select(Wallet)
    return await db.all(query)


async def initialize_db():
    await db.create_tables(Base)
