from typing import Dict

from agent.tools.data_providers.RapidDataProviderBase import RapidDataProviderBase, EndpointSchema


class CryptoProvider(RapidDataProviderBase):
    def __init__(self):
        endpoints: Dict[str, EndpointSchema] = {
            "bitcoin_price": {
                "route": "/v2/cryptocurrency/quotes/latest",
                "method": "GET",
                "name": "Bitcoin Price Data",
                "description": "Get current Bitcoin price, market cap, and trading data.",
                "payload": {
                    "symbol": "Bitcoin symbol (BTC)",
                    "convert": "Optional. Currency to convert to (USD, EUR, etc). Default is USD.",
                    "aux": "Optional. Additional data fields (num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,market_cap_by_total_supply,volume_24h_reported,volume_7d,volume_7d_reported,volume_30d,volume_30d_reported)"
                }
            },
            "ordinals_info": {
                "route": "/ordinals/inscription",
                "method": "GET", 
                "name": "Bitcoin Ordinals Data",
                "description": "Get information about Bitcoin Ordinals inscriptions and BRC-20 tokens.",
                "payload": {
                    "inscription_id": "Optional. Specific inscription ID to look up",
                    "limit": "Optional. Number of results to return (1-100). Default is 20.",
                    "offset": "Optional. Offset for pagination. Default is 0."
                }
            },
            "blockchain_stats": {
                "route": "/blockchain/stats",
                "method": "GET",
                "name": "Blockchain Statistics", 
                "description": "Get Bitcoin blockchain statistics including hash rate, difficulty, blocks.",
                "payload": {
                    "blockchain": "Blockchain network (bitcoin, ethereum, etc)",
                    "timeframe": "Optional. Time period for stats (24h, 7d, 30d). Default is 24h."
                }
            },
            "defi_protocols": {
                "route": "/defi/protocols",
                "method": "GET",
                "name": "DeFi Protocol Data",
                "description": "Get information about DeFi protocols, TVL, and yield farming data.",
                "payload": {
                    "protocol": "Optional. Specific protocol name (uniswap, compound, etc)",
                    "chain": "Optional. Blockchain to filter by (ethereum, bitcoin, solana, etc)",
                    "category": "Optional. Protocol category (dex, lending, yield, etc)"
                }
            },
            "nft_collections": {
                "route": "/nft/collections",
                "method": "GET", 
                "name": "NFT Collection Data",
                "description": "Get NFT collection statistics including Bitcoin Ordinals collections.",
                "payload": {
                    "collection": "Optional. Specific collection name",
                    "blockchain": "Optional. Blockchain (bitcoin, ethereum, solana)",
                    "sort_by": "Optional. Sort criteria (volume, floor_price, market_cap)",
                    "limit": "Optional. Number of results (1-100). Default is 20."
                }
            },
            "crypto_news": {
                "route": "/news/latest",
                "method": "GET",
                "name": "Cryptocurrency News",
                "description": "Get latest cryptocurrency news and market updates.",
                "payload": {
                    "category": "Optional. News category (bitcoin, defi, nft, altcoins, etc)",
                    "limit": "Optional. Number of articles (1-50). Default is 10.",
                    "language": "Optional. Language code (en, es, fr, etc). Default is en."
                }
            }
        }
        
        # RapidAPI base URL for crypto APIs - this would need to be configured
        # with actual RapidAPI crypto service endpoints
        super().__init__(
            base_url="https://pro-api.coinmarketcap.com",  # Example - would use actual RapidAPI endpoints
            endpoints=endpoints
        ) 