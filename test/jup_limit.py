import requests
import threading


def mock_quote():
    url = 'https://jupiter-swap-api.quiknode.pro/318D48632327/swap'
    data = {
        "userPublicKey": "3gqQQT8KS6sDLUzHGbBDweg5bT1g443eMSDkKgwGzRdM",
        "quoteResponse": {
            "inputMint": "So11111111111111111111111111111111111111112",
            "inAmount": "1000000000",
            "outputMint": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
            "outAmount": "47737119",
            "otherAmountThreshold": "47498434",
            "swapMode": "ExactIn",
            "slippageBps": 50,
            "platformFee": None,
            "priceImpactPct": "0",
            "routePlan": [
                {
                    "swapInfo": {
                        "ammKey": "BKLhZ5NrFhCjViC4wyAMXBNsJFHbFfYujo3TtUmBxTH3",
                        "label": "Phoenix",
                        "inputMint": "So11111111111111111111111111111111111111112",
                        "outputMint": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
                        "inAmount": "200000000",
                        "outAmount": "9546224",
                        "feeAmount": "4776",
                        "feeMint": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"
                    },
                    "percent": 20
                },
                {
                    "swapInfo": {
                        "ammKey": "G7ixPyiyNeggVf1VanSetFMNbVuVCPtimJmd9axfQqng",
                        "label": "Meteora DLMM",
                        "inputMint": "So11111111111111111111111111111111111111112",
                        "outputMint": "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",
                        "inAmount": "800000000",
                        "outAmount": "59167218",
                        "feeAmount": "240003",
                        "feeMint": "So11111111111111111111111111111111111111112"
                    },
                    "percent": 80
                },
                {
                    "swapInfo": {
                        "ammKey": "BCuk3J7Djjn6WYzSBWrHyGM2cgpUeBBHQtxskgiqyv7p",
                        "label": "Whirlpool",
                        "inputMint": "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",
                        "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                        "inAmount": "59167218",
                        "outAmount": "148627676",
                        "feeAmount": "0",
                        "feeMint": "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4"
                    },
                    "percent": 100
                },
                {
                    "swapInfo": {
                        "ammKey": "6ojSigXF7nDPyhFRgmn3V9ywhYseKF9J32ZrranMGVSX",
                        "label": "Phoenix",
                        "inputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                        "outputMint": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
                        "inAmount": "148627676",
                        "outAmount": "38190895",
                        "feeAmount": "19105",
                        "feeMint": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"
                    },
                    "percent": 100
                }
            ],
            "contextSlot": 257193413,
            "timeTaken": 0.411891677
        }
    }
    response = requests.post(url, json=data)
    print(f'{response.status_code} {response.text}')


for _ in range(200):
    threading.Thread(target=mock_quote, args=()).start()
