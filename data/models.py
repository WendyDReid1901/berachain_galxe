import inspect

from libs.pretty_utils.miscellaneous.files import read_json
from libs.py_eth_async.data.models import GWei, RawContract
from libs.pretty_utils.type_functions.classes import Singleton

from data.config import ABIS_DIR

from data.config import SETTINGS_FILE

from typing import Optional, Union
from decimal import Decimal

import asyncio
from web3 import Web3
from eth_typing import ChecksumAddress
from eth_utils import to_wei, from_wei
from dataclasses import dataclass
from web3.contract import AsyncContract

from data.config import logger
from libs.py_eth_async.data.models import DefaultABIs


class AutoRepr:
    def __repr__(self) -> str:
        values = ('{}={!r}'.format(key, value) for key, value in vars(self).items())
        return '{}({})'.format(self.__class__.__name__, ', '.join(values))


class Network:
    def __init__(self, name: str, rpc: str, chain_id: Optional[int] = None, tx_type: int = 0,
                 coin_symbol: Optional[str] = None, explorer: Optional[str] = None) -> None:
        self.name: str = name.lower()
        self.rpc: str = rpc
        self.chain_id: Optional[int] = chain_id
        self.tx_type: int = tx_type
        self.coin_symbol: Optional[str] = coin_symbol
        self.explorer: Optional[str] = explorer


class Networks:
    # ETH Mainnet
    Ethereum = Network(
        name='ethereum',
        rpc='https://rpc.ankr.com/eth/',
        chain_id=1,
        tx_type=2,
        coin_symbol='ETH',
        explorer='https://etherscan.io/',
    )

    Berachain = Network(
        name='berachain',
        rpc='https://artio.rpc.berachain.com', # rpc: https://rpc.ankr.com/berachain_testnet
        chain_id=80085,
        tx_type=2,
        coin_symbol='BERA',
        explorer='https://artio.beratrail.io/',
    )


@dataclass
class FromTo:
    from_: Union[int, float]
    to_: Union[int, float]


class BaseContract(RawContract):
    def __init__(self,
                 title,
                 address,
                 abi,
                 min_value: Optional[float] = 0,
                 stable: Optional[bool] = False,
                 belongs_to: Optional[str] = "",
                 decimals: Optional[int] = 18,
                 token_out_name: Optional[str] = '',
                 ):
        super().__init__(address, abi)
        self.title = title
        self.min_value = min_value
        self.stable = stable
        self.belongs_to = belongs_to  # Имя помойки например AAVE
        self.decimals = decimals
        self.token_out_name = token_out_name


class SwapInfo:
    def __init__(self, token_from: BaseContract, token_to: BaseContract, swap_platform: BaseContract):
        self.token_from = token_from
        self.token_to = token_to
        self.swap_platform = swap_platform


class Settings(Singleton, AutoRepr):
    def __init__(self):
        json = read_json(path=SETTINGS_FILE)
        self.rpcs = json['networks']['EVM_chain']['rpcs']
        self.bera_amount_for_swap: FromTo = FromTo(
            from_=json['bera_amount_for_swap']['from'], to_=json['bera_amount_for_swap']['to']
        )


settings = Settings()


class Routers(Singleton):
    """
    An instance with router contracts
        variables:
            ROUTER: BaseContract
            ROUTER.title = any
    """

    BEX_WETH = BaseContract(
        title="BEX_WETH", address='0x5806E416dA447b267cEA759358cF22Cc41FAE80F',
        abi=read_json(path=(ABIS_DIR, 'blank.json'))
    )
    BEX = BaseContract(
        title="BEX", address='0x0d5862FDbdd12490f9b4De54c236cff63B038074',
        abi=read_json(path=(ABIS_DIR, 'blank.json'))
    )
    HONEY_MINT = BaseContract(
        title="HONEY_MINT", address='0x09ec711b81cD27A6466EC40960F2f8D85BB129D9',
        abi=read_json(path=(ABIS_DIR, 'honey_mint.json'))
    )
    HONEY_JAR_MINT = BaseContract(
        title="HONEY_JAR_MINT", address='0x6553444CaA1d4FA329aa9872008ca70AE6131925',
        abi=read_json(path=(ABIS_DIR, 'honey_jar.json'))
    )
    BEND = BaseContract(
        title="BEND", address='0xA691f7CfB3C65A17Dcbf9D6d748Cc677B0640db0',
        abi=read_json(path=(ABIS_DIR, 'bend.json'))
    )


class Tokens(Singleton):
    """
    An instance with token contracts
        variables:
            TOKEN: BaseContract
            TOKEN.title = symbol from OKLINK
    """
    WBERA = BaseContract(
        title="WBERA", address='0x5806E416dA447b267cEA759358cF22Cc41FAE80F',
        abi=DefaultABIs.Token
    )
    BERA = BaseContract(
        title="BERA", address='0x0000000000000000000000000000000000000000',
        abi=DefaultABIs.Token
    )
    STGUSDC = BaseContract(
        title="STGUSDC", address='0x6581e59A1C8dA66eD0D313a0d4029DcE2F746Cc5',
        abi=DefaultABIs.Token
    )
    HONEY = BaseContract(
        title="HONEY", address='0x7EeCA4205fF31f947EdBd49195a7A88E6A91161B',
        abi=DefaultABIs.Token
    )
    WBTC = BaseContract(
        title="WBTC", address='0x9DAD8A1F64692adeB74ACa26129e0F16897fF4BB',
        abi=DefaultABIs.Token
    )
    WETH = BaseContract(
        title="WETH", address='0x8239FBb3e3D0C2cDFd7888D8aF7701240Ac4DcA4',
        abi=DefaultABIs.Token
    )
    HONEY_MINT = BaseContract(
        title="HONEY_MINT", address='0x9F2A613a139851BC984A614FD718C6fEF0f02894',
        abi=DefaultABIs.Token
    )

    @staticmethod
    def get_token_list():
        return [
            value for name, value in inspect.getmembers(Tokens)
            if isinstance(value, BaseContract)
        ]


class Pools(Singleton):
    """
        An instance with pool contracts
            variables:
                POOL: BaseContract
                POOL.TITLE = any
    """
    BERA_STGUSDC = BaseContract(
        title="BERA_STGUSDC", address='0x36af4fbab8ebe58b4effe0d5d72ceffc6efc650a',
        abi=DefaultABIs.Token
    )
    STGUSDC_HONEY = BaseContract(
        title="STGUSDC_HONEY", address='0xaebf2a333755d2783ab2a8e8bf30b49e254926cb',
        abi=DefaultABIs.Token
    )
    WERA_WBTC = BaseContract(
        title="WERA_WBTC", address='0xd3c962f3f36484439a41d0e970cf6581ddf0a9a1',
        abi=DefaultABIs.Token
    )
    WBERA_WETH = BaseContract(
        title="WBERA_WETH", address='0xd3c962f3f36484439a41d0e970cf6581ddf0a9a1',
        abi=DefaultABIs.Token
    )


class Lending_Tokens(Singleton):
    """
        An instance with lending contracts
            variables:
                LENDING_TOKEN: BaseContract
                LENDING_TOKEN.title = symbol from Oklink
    """
    aHONEY = BaseContract(
        title='aHONEY', address='0x7EeCA4205fF31f947EdBd49195a7A88E6A91161B',
        abi=DefaultABIs.Token,
        belongs_to="BEND"
    )
    aWETH = BaseContract(
        title='aWETH', address='0x8239fbb3e3d0c2cdfd7888d8af7701240ac4dca4',
        abi=DefaultABIs.Token,
        belongs_to="BEND"
    )
    aWBTC = BaseContract(
        title='aWBTC', address='0x9dad8a1f64692adeb74aca26129e0f16897ff4bb',
        abi=DefaultABIs.Token,
        belongs_to="BEND"
    )

    # aBasUSDbC = BaseContract(
    #     title="aBasUSDbC", address='0x0a1d576f3efef75b330424287a95a366e8281d54',
    #     abi=DefaultABIs.Token,
    #     min_value=0.00009,
    #     belongs_to="AAVE"
    # )

    @staticmethod
    def get_token_list():
        return [
            value for name, value in inspect.getmembers(Lending_Tokens)
            if isinstance(value, BaseContract)
        ]


class Liquidity_Tokens(Singleton):
    """
        An instance with LP contracts
            variables:
                LP_TOKEN: BaseContract
                LP_TOKEN.title = symbol from Oklink
     """

    # SYNCSWAP_WETH_USDC = BaseContract(
    #     title='USDC/WETH cSLP', address='0x814a23b053fd0f102aeeda0459215c2444799c70',
    #     abi=read_json(path=(ABIS_DIR, 'sync_swap_liquidity.json')),
    #     belongs_to='SyncSwapLiquidity',
    #     token_out_name='USDC',
    #     decimals=18
    # )

    @staticmethod
    def get_token_list():
        return [
            value for name, value in inspect.getmembers(Liquidity_Tokens)
            if isinstance(value, BaseContract)
        ]


class TokenAmount:
    Wei: int
    Ether: Decimal
    decimals: int

    def __init__(self, amount: Union[int, float, str, Decimal], decimals: int = 18, wei: bool = False) -> None:
        """
        A token amount instance.

        :param Union[int, float, str, Decimal] amount: an amount
        :param int decimals: the decimals of the token (18)
        :param bool wei: the 'amount' is specified in Wei (False)
        """
        if wei:
            self.Wei: int = amount
            self.Ether: Decimal = Decimal(str(amount)) / 10 ** decimals

        else:
            self.Wei: int = int(Decimal(str(amount)) * 10 ** decimals)
            self.Ether: Decimal = Decimal(str(amount))

        self.decimals = decimals


unit_denominations = {
    'wei': 10 ** -18,
    'kwei': 10 ** -15,
    'mwei': 10 ** -12,
    'gwei': 10 ** -9,
    'szabo': 10 ** -6,
    'finney': 10 ** -3,
    'ether': 1,
    'kether': 10 ** 3,
    'mether': 10 ** 6,
    'gether': 10 ** 9,
    'tether': 10 ** 12,
}


class Unit(AutoRepr):
    """
    An instance of an Ethereum unit.

    Attributes:
        unit (str): a unit name.
        decimals (int): a number of decimals.
        Wei (int): the amount in Wei.
        KWei (Decimal): the amount in KWei.
        MWei (Decimal): the amount in MWei.
        GWei (Decimal): the amount in GWei.
        Szabo (Decimal): the amount in Szabo.
        Finney (Decimal): the amount in Finney.
        Ether (Decimal): the amount in Ether.
        KEther (Decimal): the amount in KEther.
        MEther (Decimal): the amount in MEther.
        GEther (Decimal): the amount in GEther.
        TEther (Decimal): the amount in TEther.

    """
    unit: str
    decimals: int
    Wei: int
    KWei: Decimal
    MWei: Decimal
    GWei: Decimal
    Szabo: Decimal
    Finney: Decimal
    Ether: Decimal
    KEther: Decimal
    MEther: Decimal
    GEther: Decimal
    TEther: Decimal

    def __init__(self, amount: Union[int, float, str, Decimal], unit: str) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.
            unit (str): a unit name.

        """
        self.unit = unit
        self.decimals = 18
        self.Wei = to_wei(amount, self.unit)
        self.KWei = from_wei(self.Wei, 'kwei')
        self.MWei = from_wei(self.Wei, 'mwei')
        self.GWei = from_wei(self.Wei, 'gwei')
        self.Szabo = from_wei(self.Wei, 'szabo')
        self.Finney = from_wei(self.Wei, 'finney')
        self.Ether = from_wei(self.Wei, 'ether')
        self.KEther = from_wei(self.Wei, 'kether')
        self.MEther = from_wei(self.Wei, 'mether')
        self.GEther = from_wei(self.Wei, 'gether')
        self.TEther = from_wei(self.Wei, 'tether')

    def __add__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return Wei(self.Wei + other.Wei)

        elif isinstance(other, int):
            return Wei(self.Wei + other)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(self.GWei + GWei(other).GWei)

            else:
                return Ether(self.Ether + Ether(other).Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __radd__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return Wei(other.Wei + self.Wei)

        elif isinstance(other, int):
            return Wei(other + self.Wei)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(GWei(other).GWei + self.GWei)

            else:
                return Ether(Ether(other).Ether + self.Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __sub__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return Wei(self.Wei - other.Wei)

        elif isinstance(other, int):
            return Wei(self.Wei - other)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(self.GWei - GWei(other).GWei)

            else:
                return Ether(self.Ether - Ether(other).Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __rsub__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return Wei(other.Wei - self.Wei)

        elif isinstance(other, int):
            return Wei(other - self.Wei)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(GWei(other).GWei - self.GWei)

            else:
                return Ether(Ether(other).Ether - self.Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __mul__(self, other):
        if isinstance(other, TokenAmount):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            if self.unit != 'ether':
                raise ArithmeticError('You can only perform this action with an Ether unit!')

            return Ether(Decimal(str(self.Ether)) * Decimal(str(other.Ether)))

        if isinstance(other, Unit):
            if isinstance(other, Unit) and self.unit != other.unit:
                raise ArithmeticError('The units are different!')

            denominations = int(Decimal(str(unit_denominations[self.unit])) * Decimal(str(10 ** self.decimals)))
            return Wei(self.Wei * other.Wei / denominations)

        elif isinstance(other, int):
            return Wei(self.Wei * other)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(self.GWei * GWei(other).GWei)

            else:
                return Ether(self.Ether * Ether(other).Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __rmul__(self, other):
        if isinstance(other, TokenAmount):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            if self.unit != 'ether':
                raise ArithmeticError('You can only perform this action with an Ether unit!')

            return Ether(Decimal(str(other.Ether)) * Decimal(str(self.Ether)))

        if isinstance(other, Unit):
            if isinstance(other, Unit) and self.unit != other.unit:
                raise ArithmeticError('The units are different!')

            denominations = int(Decimal(str(unit_denominations[self.unit])) * Decimal(str(10 ** self.decimals)))
            return Wei(other.Wei * self.Wei / denominations)

        elif isinstance(other, int):
            return Wei(other * self.Wei)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(GWei(other).GWei * self.GWei)

            else:
                return Ether(Ether(other).Ether * self.Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __truediv__(self, other):
        if isinstance(other, TokenAmount):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            if self.unit != 'ether':
                raise ArithmeticError('You can only perform this action with an Ether unit!')

            return Ether(Decimal(str(self.Ether)) / Decimal(str(other.Ether)))

        if isinstance(other, Unit):
            if isinstance(other, Unit) and self.unit != other.unit:
                raise ArithmeticError('The units are different!')

            denominations = int(Decimal(str(unit_denominations[self.unit])) * Decimal(str(10 ** self.decimals)))
            return Wei(self.Wei / other.Wei * denominations)

        elif isinstance(other, int):
            return Wei(self.Wei / Decimal(str(other)))

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(self.GWei / GWei(other).GWei)

            else:
                return Ether(self.Ether / Ether(other).Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __rtruediv__(self, other):
        if isinstance(other, TokenAmount):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            if self.unit != 'ether':
                raise ArithmeticError('You can only perform this action with an Ether unit!')

            return Ether(Decimal(str(other.Ether)) / Decimal(str(self.Ether)))

        if isinstance(other, Unit):
            if isinstance(other, Unit) and self.unit != other.unit:
                raise ArithmeticError('The units are different!')

            denominations = int(Decimal(str(unit_denominations[self.unit])) * Decimal(str(10 ** self.decimals)))
            return Wei(other.Wei / self.Wei * denominations)

        elif isinstance(other, int):
            return Wei(Decimal(str(other)) / self.Wei)

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return GWei(GWei(other).GWei / self.GWei)

            else:
                return Ether(Ether(other).Ether / self.Ether)

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __iadd__(self, other):
        return self.__add__(other)

    def __isub__(self, other):
        return self.__sub__(other)

    def __imul__(self, other):
        return self.__mul__(other)

    def __itruediv__(self, other):
        return self.__truediv__(other)

    def __lt__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei < other.Wei

        elif isinstance(other, int):
            return self.Wei < other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei < GWei(other).GWei

            else:
                return self.Ether < Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __le__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei <= other.Wei

        elif isinstance(other, int):
            return self.Wei <= other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei <= GWei(other).GWei

            else:
                return self.Ether <= Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __eq__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei == other.Wei

        elif isinstance(other, int):
            return self.Wei == other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei == GWei(other).GWei

            else:
                return self.Ether == Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __ne__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei != other.Wei

        elif isinstance(other, int):
            return self.Wei != other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei != GWei(other).GWei

            else:
                return self.Ether != Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __gt__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei > other.Wei

        elif isinstance(other, int):
            return self.Wei > other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei > GWei(other).GWei

            else:
                return self.Ether > Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")

    def __ge__(self, other):
        if isinstance(other, (Unit, TokenAmount)):
            if self.decimals != other.decimals:
                raise ArithmeticError('The values have different decimals!')

            return self.Wei >= other.Wei

        elif isinstance(other, int):
            return self.Wei >= other

        elif isinstance(other, float):
            if self.unit == 'gwei':
                return self.GWei >= GWei(other).GWei

            else:
                return self.Ether >= Ether(other).Ether

        else:
            raise ArithmeticError(f"{type(other)} type isn't supported!")


class Wei(Unit):
    """
    An instance of a Wei unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'wei')


class MWei(Unit):
    """
    An instance of a MWei unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'mwei')


class GWei(Unit):
    """
    An instance of a GWei unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'gwei')


class Szabo(Unit):
    """
    An instance of a Szabo unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'szabo')


class Finney(Unit):
    """
    An instance of a Finney unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'finney')


class Ether(Unit):
    """
    An instance of an Ether unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'ether')


class KEther(Unit):
    """
    An instance of a KEther unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'kether')


class MEther(Unit):
    """
    An instance of a MEther unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'mether')


class GEther(Unit):
    """
    An instance of a GEther unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'gether')


class TEther(Unit):
    """
    An instance of a TEther unit.
    """

    def __init__(self, amount: Union[int, float, str, Decimal]) -> None:
        """
        Initialize the class.

        Args:
            amount (Union[int, float, str, Decimal]): an amount.

        """
        super().__init__(amount, 'tether')


@dataclass
class DefaultABIs:
    Token = [
        {
            'constant': True,
            'inputs': [],
            'name': 'name',
            'outputs': [{'name': '', 'type': 'string'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'symbol',
            'outputs': [{'name': '', 'type': 'string'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'totalSupply',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'decimals',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [{'name': 'who', 'type': 'address'}],
            'name': 'balanceOf',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [{'name': '_owner', 'type': 'address'}, {'name': '_spender', 'type': 'address'}],
            'name': 'allowance',
            'outputs': [{'name': 'remaining', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': False,
            'inputs': [{'name': '_spender', 'type': 'address'}, {'name': '_value', 'type': 'uint256'}],
            'name': 'approve',
            'outputs': [],
            'payable': False,
            'stateMutability': 'nonpayable',
            'type': 'function'
        },
        {
            'constant': False,
            'inputs': [{'name': '_to', 'type': 'address'}, {'name': '_value', 'type': 'uint256'}],
            'name': 'transfer',
            'outputs': [], 'payable': False,
            'stateMutability': 'nonpayable',
            'type': 'function'
        }]


class Contracts:
    def __init__(self, client) -> None:
        self.client = client

    async def get_contract(self,
                           contract_address: ChecksumAddress,
                           abi: Union[list, dict] = DefaultABIs.Token
                           ) -> AsyncContract:
        return self.client.w3.eth.contract(address=contract_address, abi=abi)


class Transactions:
    def __init__(self, client):
        self.client = client

    @staticmethod
    async def gas_price(w3: Web3, max_retries=30) -> Wei:
        retries = 0
        while retries < max_retries:
            try:
                return Wei(await w3.eth.gas_price)
            except asyncio.exceptions.TimeoutError:
                logger.debug(f"Retry {retries + 1}/{max_retries} due to TimeoutError ETH gas price")
                retries += 1

        raise ValueError(f"Unable to get gas price after {max_retries} retries")


class Wallet:
    def __init__(self, client) -> None:
        self.client = client

    async def balance(self, token_address: Optional[str] = None,
                      address: Optional[ChecksumAddress] = None) -> Union[Wei, TokenAmount]:
        if not address:
            address = self.client.account.address

        address = Web3.to_checksum_address(address)
        if not token_address:
            return Wei(await self.client.w3.eth.get_balance(account=address))

        token_address = Web3.to_checksum_address(token_address)
        contract = await self.client.contracts.get_contract(contract_address=token_address)
        return TokenAmount(
            amount=await contract.functions.balanceOf(address).call(),
            decimals=await contract.functions.decimals().call(),
            wei=True
        )

    async def nonce(self, address: Optional[ChecksumAddress] = None) -> int:
        if not address:
            address = self.client.account.address
        return await self.client.w3.eth.get_transaction_count(address)
