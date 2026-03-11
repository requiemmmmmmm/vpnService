from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=5)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
