from ai.rag.vector_store import get_qdrant_client
from ai.config import settings

def main():
    client = get_qdrant_client()
    print("URL:", settings.qdrant_url)
    print("Collection:", settings.qdrant_collection)
    print("Collections on server:")
    print(client.get_collections())

if __name__ == "__main__":
    main()
