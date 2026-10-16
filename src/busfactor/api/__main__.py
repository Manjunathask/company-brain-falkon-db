"""Run the local Bus Factor HTTP application."""
import os

import uvicorn


def main():
    uvicorn.run("busfactor.api.app:app", host=os.getenv("HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", "8000")), reload=False)


if __name__ == "__main__":
    main()
