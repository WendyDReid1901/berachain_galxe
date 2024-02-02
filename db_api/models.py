import datetime

from data.models import AutoRepr
from sqlalchemy import (Column, Integer, Text, Boolean, DateTime)
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Wallet(Base, AutoRepr):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)

    token = Column(Text)
    private_key = Column(Text, unique=True)
    address = Column(Text)
    proxy = Column(Text)

    twitter_account_status = Column(Text)
    user_agent = Column(Text)
    platform = Column(Text)
    next_available_claim = Column(Integer)
    follow_and_retweet = Column(Boolean)
    galxe_faucet_claim = Column(Boolean)
    galxe_onboarding_claim = Column(Boolean)

    email_data = Column(Text)
    register = Column(Boolean)
    galxe_daily_claim = Column(DateTime)
    finished_onchain = Column(Boolean)
    finished_claim_second_nft = Column(Boolean)

    def __init__(
            self,
            token: str,
            private_key: str,
            address: str,
            proxy: str,
            user_agent: str,
            platform: str,
            email: str = None,
    ) -> None:

        self.token = token
        self.private_key = private_key
        self.address = address
        self.proxy = proxy

        self.twitter_account_status = "OK"
        self.user_agent = user_agent
        self.platform = platform

        self.next_available_claim = 0
        self.follow_and_retweet = False
        self.galxe_faucet_claim = False
        self.galxe_onboarding_claim = False

        self.email_data = email
        self.register = False
        self.galxe_daily_claim = datetime.datetime(1970, 1, 1)
        self.finished_onchain = False
        self.finished_claim_second_nft = False
