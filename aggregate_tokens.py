import asyncio
import json
from collections import defaultdict
from typing import TypedDict, NewType

import httpx

TOKENLISTS_FOLDER = "tokenlists"

CHAIN_NAMES_BY_ID = {
    '1': 'ethereum',
    '10': 'optimistic-ethereum',
    '100': 'xdai',
    '10000': 'smartbch',
    '101': 'solana',
    '1024': 'clover',
    '11297108109': 'palm',
    '122': 'fuse',
    '128': 'heco',
    '1284': 'moonbeam',
    '1285': 'moonriver',
    '1287': 'moonbase',
    '1313161554': 'aurora',
    '137': 'polygon',
    '1666600000': 'harmony',
    '1666700000': 'harmony-testnet',
    '20': 'elastos',
    '25': 'cronos',
    '250': 'ftm',
    '256': 'heco-testnet',
    '288': 'boba',
    '3': 'ropsten',
    '321': 'kcc',
    '361': 'theta',
    '4': 'rinkeby',
    '40': 'telos',
    '4002': 'ftmtest',
    '42': 'kovan',
    '42161': 'farms',
    '42220': 'celo',
    '43113': 'fuji',
    '43114': 'avax',
    '4689': 'iotex',
    '5': 'goerli',
    '56': 'bsc',
    '65': 'okex-testnet',
    '66': 'okex',
    '70': 'hoo',
    '80001': 'mumbai',
    '82': 'meter',
    '88': 'tomochain',
    '97': 'bsc-testnet'
}

Address = NewType('Address', str)

ChainId = NewType('ChainId', str)


class Token(TypedDict):
    symbol: str
    name: str
    address: str
    decimals: str
    chainId: str
    logoURI: str
    coingeckoId: str


def get_coingecko_ids() -> dict[ChainId, dict[Address, str]]:
    chain_id_to_coingecko_platform = {
        "1284": "moonbeam",
        "361": "theta",
        "70": "hoo-smart-chain",
        "122": "fuse",
        "42262": "oasis",
        "128": "huobi-token",
        "321": "kucoin-community-chain",
        "42161": "arbitrum-one",
        "1088": "metis-andromeda",
        "56": "binance-smart-chain",
        "66": "okex-chain",
        "250": "fantom",
        "88": "tomochain",
        "82": "meter",
        "42220": "celo",
        "10": "optimistic-ethereum",
        "137": "polygon-pos",
        "43114": "avalanche",
        "1285": "moonriver",
        "25": "cronos",
        "288": "boba",
        "10000": "smartbch",
        "1313161554": "aurora",
        "1666600000": "harmony-shard-0",
        "100": "xdai",
        "1": "ethereum",
        "32659": "fusion-network",
        "40": "telos",
        "101": "solana",
    }
    coingecko_platform_to_chain_id = {v: k for k, v in chain_id_to_coingecko_platform.items()}
    coins = httpx.get('https://api.coingecko.com/api/v3/coins/list', params={'include_platform': True}).json()
    res = defaultdict(dict)
    for coin in coins:
        if not coin['id']:
            continue
        for platform, address in coin.get('platforms', {}).items():
            if platform and address and platform in coingecko_platform_to_chain_id:
                res[coingecko_platform_to_chain_id[platform]][address] = coin['id']
    print(res.keys())
    print(len(res['1']))
    return res


coingecko_ids = get_coingecko_ids()


class TokenListProvider:
    name: str
    base_url: str
    chains: dict[ChainId, str]
    _by_chain_id = False
    _set_chain_id = False
    _tokens_to_list = False
    _set_coingecko_id = True

    parsed_tokens: list[Token]

    @classmethod
    async def get_tokenlists(cls) -> dict[str, dict[ChainId, list[Token]]]:
        res: dict[ChainId, list[Token]] = defaultdict(list)
        for chain_id, chain_name in cls.chains.items():
            resp = await httpx.AsyncClient().get(cls.base_url.format(chain_id if cls._by_chain_id else chain_name))
            while resp.status_code != 200:
                sleep_time = int(resp.headers.get("Retry-After", 1))
                print(f"[{cls.name}] {chain_id} {chain_name} waiting {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
                resp = await httpx.AsyncClient().get(cls.base_url.format(chain_id if cls._by_chain_id else chain_name))
            tokenlist = resp.json()
            if "tokens" in tokenlist:
                tokens = tokenlist["tokens"]
            elif "data" in tokenlist:
                tokens = tokenlist["data"]
            else:
                tokens = tokenlist
            if cls._set_chain_id:
                for token in tokens.values():
                    token["chainId"] = chain_id
            if cls._tokens_to_list:
                tokens = list(tokens.values())
            for token in tokens:
                if not token['address']:
                    continue
            if cls._set_coingecko_id:
                for token in tokens:
                    coingecko_id = coingecko_ids.get(chain_id, {}).get(token['address'])
                    if coingecko_id:
                        token["coingeckoId"] = coingecko_id
            res[chain_id] = tokens
            print(f"[{cls.name}] {chain_id} {chain_name} OK")
        return {cls.name: res}


class CoinGeckoTokenLists(TokenListProvider):
    name = "coingecko"
    base_url = "https://tokens.coingecko.com/{}/all.json"
    chains = {
        "1284": "moonbeam",
        "361": "theta",
        "70": "hoo-smart-chain",
        "42161": "arbitrum-one",
        "56": "binance-smart-chain",
        "66": "okex-chain",
        "250": "fantom",
        "88": "tomochain",
        "82": "meter",
        "42220": "celo",
        "10": "optimistic-ethereum",
        "137": "polygon-pos",
        "43114": "avalanche",
        "1285": "moonriver",
        "25": "cronos",
        "288": "boba",
        "10000": "smartbch",
        "1313161554": "aurora",
        "1666600000": "harmony-shard-0",
        "100": "xdai",
        "1": "ethereum",
        "101": "solana"
    }


class UniswapTokenLists(TokenListProvider):
    name = "uniswap"
    base_url = "https://raw.githubusercontent.com/Uniswap/default-token-list/main/src/tokens/{}.json"
    chains = {
        "5": "goerli",
        "42": "kovan",
        "1": "mainnet",
        "80001": "mumbai",
        "137": "polygon",
        "4": "rinkeby",
        "3": "ropsten",
    }


class SushiswapTokenLists(TokenListProvider):
    name = "sushiswap"
    base_url = "https://raw.githubusercontent.com/sushiswap/default-token-list/master/tokens/{}.json"
    chains = {
        "42161": "arbitrum",
        "43114": "avalanche",
        "97": "bsc-testnet",
        "56": "bsc",
        "42220": "celo",
        "1024": "clover",
        "4002": "fantom-testnet",
        "250": "fantom",
        "43113": "fuji",
        "122": "fuse",
        "5": "goerli",
        "1666700000": "harmony-testnet",
        "1666600000": "harmony",
        "256": "heco-testnet",
        "128": "heco",
        "42": "kovan",
        "1": "mainnet",
        "80001": "matic-testnet",
        "137": "matic",
        "1287": "moonbase",
        "1285": "moonriver",
        "65": "okex-testnet",
        "66": "okex",
        "11297108109": "palm",
        "4": "rinkeby",
        "3": "ropsten",
        "40": "telos",
        "100": "xdai"
    }


class OneInchTokenLists(TokenListProvider):
    name = "1inch"
    base_url = "https://api.1inch.io/v4.0/{}/tokens"
    chains = {
        "1": "ethereum",
        "10": "optimism",
        "56": "bsc",
        "100": "gnosis",
        "137": "polygon",
        "43114": "avalanche",
        "42161": "arbitrum",
    }
    _by_chain_id = True
    _set_chain_id = True
    _tokens_to_list = True


class SolanaLabsTokenLists(TokenListProvider):
    name = "solanalabs"
    base_url = "https://raw.githubusercontent.com/solana-labs/token-list/main/src/tokens/{}.tokenlist.json"
    chains = {
        "101": "solana"
    }


class OpenOceanTokenLists(TokenListProvider):
    # TODO: maybe more, check all ids from coingecko
    name = "openocean"
    base_url = "https://open-api.openocean.finance/v1/cross/tokenList?chainId={}"
    chains = {
        "42161": "arbitrum-one",
        "43114": "avalanche",
        "56": "binance-smart-chain",
        "66": "okex-chain",
        "250": "fantom",
        "10": "optimistic-ethereum",
        "137": "polygon-pos",
        "288": "boba",
        "100": "xdai-gnosis",
        "128": "heco",
        "1": "ethereum",
    }
    _by_chain_id = True


class ElkFinanceTokenLists(TokenListProvider):
    name = "elkfinance"
    base_url = "https://raw.githubusercontent.com/elkfinance/tokens/main/{}.tokenlist.json"
    chains = {
        "42161": "farms",
        "43114": "avax",
        "56": "bsc",
        "25": "cronos",
        "20": "elastos",
        "1": "ethereum",
        "250": "ftm",
        "4002": "ftmtest",
        "43113": "fuji",
        "122": "fuse",
        "1666600000": "harmony",
        "128": "heco",
        "70": "hoo",
        "4689": "iotex",
        "321": "kcc",
        "137": "matic",
        "1285": "moonriver",
        "80001": "mumbai",
        "66": "okex",
        "40": "telos",
        "100": "xdai"
    }
    # "all", "top"


# TODO: support
class RefFinanceTokenLists(TokenListProvider):
    # unusual format
    base_url = "https://indexer.ref-finance.net/list-token"


class OneSolTokenLists(TokenListProvider):
    name = "1sol"
    base_url = "https://raw.githubusercontent.com/1sol-io/token-list/main/src/tokens/solana.tokenlist.json"
    chains = {
        "101": "solana"
    }


class QuickSwapTokenLists(TokenListProvider):
    name = "quickswap"
    base_url = "https://raw.githubusercontent.com/sameepsi/quickswap-default-token-list/master/src/tokens/mainnet.json"
    chains = {
        "137": "polygon"
    }


class FuseSwapTokenLists(TokenListProvider):
    name = "fuseswap"
    base_url = "https://raw.githubusercontent.com/fuseio/fuseswap-default-token-list/master/src/tokens/fuse.json"
    chains = {
        "122": "fuse"
    }


tokenlists_providers = [
    CoinGeckoTokenLists,
    OneInchTokenLists,
    UniswapTokenLists,
    SushiswapTokenLists,
    OpenOceanTokenLists,
    SolanaLabsTokenLists,
    ElkFinanceTokenLists,
    OneSolTokenLists,
    QuickSwapTokenLists,
    FuseSwapTokenLists
]


async def collect_trusted_tokens() -> dict[ChainId, dict[Address, Token]]:
    data = await asyncio.gather(*[provider.get_tokenlists() for provider in tokenlists_providers])
    provider_data: dict[str, dict[ChainId, list[Token]]] = {}
    for prov in data:
        provider_data |= prov

    res = defaultdict(dict)
    for provider_name, tokens_by_chains in provider_data.items():
        for chain_id, tokens in tokens_by_chains.items():
            for token in tokens:
                addr = token["address"].lower()
                if addr in res[chain_id]:
                    if "listedIn" in res[chain_id][addr]:
                        res[chain_id][addr]["listedIn"].append(provider_name)
                    else:
                        res[chain_id][addr]["listedIn"] = [provider_name]
                else:
                    res[chain_id][addr] = token
                    res[chain_id][addr]["listedIn"] = [provider_name]

    trusted = {
        chain_id: {addr: token for addr, token in tokens.items() if len(token["listedIn"]) > 1} for
        chain_id, tokens in res.items()
    }
    trusted = {k: v for k, v in trusted.items() if len(v) > 0}
    for chain_id, tokens in trusted.items():
        filename = f"{TOKENLISTS_FOLDER}/{CHAIN_NAMES_BY_ID[chain_id]}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(tokens, f, ensure_ascii=False, indent=4)
    filename = f"{TOKENLISTS_FOLDER}/all.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(trusted, f, ensure_ascii=False, indent=4)

    print('collected trusted tokens')
    return trusted


if __name__ == "__main__":
    asyncio.run(collect_trusted_tokens())