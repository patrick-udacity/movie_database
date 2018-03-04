from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

DB_Base = declarative_base()


# This class is users that visit a site.
class User(DB_Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


# This class is contains properties of a movie.
class Movie(DB_Base):
    __tablename__ = 'movie_tbl'

    movie_id = Column(Integer, primary_key=True)
    movie_name = Column(String(250), nullable=False)
    movie_genre = Column(String(80))
    description = Column(String(250), nullable=False)
    year_released = Column(String(80), nullable=False)
    avg_rating = Column(String(80))
    entry_owner = Column(String(250), nullable=False)
    image = Column(String(250))
    trailer_link = Column(String(1000))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'movie_id': self.movie_id,
            'movie_name': self.movie_name,
            'movie_genre': self.movie_genre,
            'description': self.description,
            'year_released': self.year_released,
            'avg_rating': self.avg_rating,
            'entry_owner': self.entry_owner,
            'image': self.image,
            'trailer_link': self.trailer_link,
            }


# This class is genres of movies.
class Genre(DB_Base):
    __tablename__ = 'genre_tbl'

    genre_id = Column(Integer, primary_key=True)
    movie_genre = Column(String(80), nullable=False)
    genre_description = Column(String(250))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'genre_id': self.genre_id,
            'movie_genre': self.movie_genre,
            'genre_description': self.genre_description,

        }


# This class is users that create movie entries.
class Entry_Owner(DB_Base):
    __tablename__ = 'user_tbl'

    email = Column(String(250), primary_key=True)
    user_name = Column(String(250), nullable=False)
    picture = Column(String(250), nullable=False)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'email': self.email,
            'user_name': self.user_name,
            'picture': self.picture,

        }


class Rating(DB_Base):
    __tablename__ = 'ratings_table'

    rating_id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, nullable=False)
    user_id = Column(String(250), nullable=False)
    rating = Column(Float, nullable=False)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'rating_id': self.rating_id,
            'movie_id': self.movie_id,
            'user_id': self.user_id,
            'rating': self.rating,

        }

engine = create_engine('sqlite:///movie_reviews.db')


DB_Base.metadata.create_all(engine)
