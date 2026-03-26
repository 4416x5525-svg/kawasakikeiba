"""ローカル起動スクリプト。

使い方:
    python run.py

ブラウザで http://localhost:8000 を開く。
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "kawasaki_keiba.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src"],
    )
