import datetime

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError

from db_api.database import db, Wallet, get_accounts
from data.config import logger


async def main():
    changed_finished_onchain = False
    changed_finished_claim_second_nft = False

    async with AsyncSession(db.engine) as session:

        try:
            await session.execute(
                text("""
                    ALTER TABLE accounts
                    ADD COLUMN finished_onchain BOOLEAN DEFAULT FALSE;
                """)
            )
            changed_finished_onchain = True
        except OperationalError:
            logger.warning('finished_onchain уже создана в бд')

        try:
            await session.execute(
                text("""
                    ALTER TABLE accounts
                    ADD COLUMN finished_claim_second_nft BOOLEAN DEFAULT FALSE;
                """)
            )
            changed_finished_claim_second_nft = True
        except OperationalError:
            logger.warning('finished_claim_second_nft уже создана в бд')

        wallets: list[Wallet] = await get_accounts()
        print(f'Всего в базе данных: {len(wallets)} записей.')
        for wallet in wallets:
            if changed_finished_onchain:
                wallet.finished_onchain = False
            if changed_finished_claim_second_nft:
                wallet.finished_claim_second_nft = False

            session.add(wallet)

        await session.commit()
        await session.close()

    print('Migration completed.')

asyncio.run(main())
