from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, declarative_base
from datetime import datetime

engine = create_engine('sqlite:///database.db')
Session = sessionmaker(bind=engine)

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(nullable=False)
    upload_date: Mapped[datetime] = mapped_column(insert_default=func.now())
    data: Mapped[str] = mapped_column(nullable=False)

Base.metadata.create_all(engine)


