from flask import Flask, render_template, request
from flask import redirect, jsonify, url_for, flash, make_response
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from movie_db_setup import DB_Base, Movie, Genre, Entry_Owner, Rating, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
import pdb

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"


# Connect to Movie Database and create database session
movie_engine = create_engine('sqlite:///movie_reviews.db')
DB_Base.metadata.bind = movie_engine
DBSession = sessionmaker(bind=movie_engine)
moviedb_session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login_movie_db.html', STATE=state)


# Create anti-forgery state token
@app.route('/movie_db_login')
def showLoginMovie():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login_movie_db.html', STATE=state)


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    moviedb_session.add(newUser)
    moviedb_session.commit()
    user = (moviedb_session.query(User).
            filter_by(email=login_session['email']).one())
    return user.id


# This pulls info for the active logged on user.
def getUserInfo(user_id):
    user = moviedb_session.query(User).filter_by(id=user_id).one()
    return user


# Add the current user to the table of contributors.
def setUserAsContributor(login_session):
    #pdb.set_trace()
    try:
        user = (
            moviedb_session.query(Entry_Owner).
            filter_by(email=login_session['email']).one())
    except:
        newContributer = (
            Entry_Owner(email=login_session['email'],
                        user_name=login_session['username'],
                        picture=login_session['picture']))
        moviedb_session.add(newContributer)
        moviedb_session.commit()
        flash('%s set as a contributer.' % (login_session['email'],))

# This pulls info for the users that have submitted movies.
def getDBUserInfo(user_id):
    #pdb.set_trace()
    user = moviedb_session.query(Entry_Owner).filter_by(email=user_id).one()
    return user


def getUserID(email):
    try:
        user = moviedb_session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getRatingInfo(movie_id):
        returned_rating = (
            moviedb_session.query(Rating.rating).
            filter(Rating.movie_id == movie_id).all())
        returned_count = len(returned_rating)
        ratingsList = []

        # remove the returned result overhead.
        if returned_count > 0:
            total_count = 0
            for current_item in range(0, returned_count):
                ratingsList.append(returned_rating[current_item][0])

            # Convert this to a dictionary.
            # I didn't before because of the list of tuples.
            ratingsDict = {
                '1': ratingsList.count(1),
                '2': ratingsList.count(2),
                '3': ratingsList.count(3),
                '4': ratingsList.count(4),
                '5': ratingsList.count(5)
            }
            return ratingsDict
        # Return 0 as the empty list if no rating entries exist.
        else:
            ratingsDict = {
                '1': '0',
                '2': '0',
                '3': '0',
                '4': '0',
                '5': '0'
            }
            return ratingsDict


def getAvgRating(movie_id):
    returned_rating = (
        moviedb_session.query(Rating.rating).
        filter(Rating.movie_id == movie_id).all())
    returned_count = len(returned_rating)
    # Get all ratings and average them.
    if returned_count > 0:
        total_count = 0
        for current_item in range(0, returned_count):
            if returned_rating[current_item][0] > 0:
                total_count += returned_rating[current_item][0]
        avg_rating = float(total_count)/returned_count
        return avg_rating
    # Return 0 as the avg if no rating entries exist.
    else:
        return 0


def getRatingForCurrentUser(user_id, movie_id):
    try:
        currentRating = (
            moviedb_session.query(Rating).
            filter(Rating.user_id == user_id).
            filter(Rating.movie_id == movie_id).one()
        )
        return currentRating
    except:
        newRating = createRating(user_id, movie_id)
        return newRating


def setRatingForCurrentUser(user_id, movie_id, rating):
    # If the rating is left blank,then set it as zero.
    if rating == '':
        rating = 0
    # If the user's rating already exist then update it.
    try:
        currentRating = (
            moviedb_session.query(Rating).filter(Rating.user_id == user_id).
            filter(Rating.movie_id == movie_id).one())
        currentRating.user_id = user_id
        currentRating.movie_id = movie_id
        currentRating.rating = rating
        moviedb_session.add(currentRating)
        moviedb_session.commit()
        flash('Rating set to  %s for %s.' % (rating, user_id))
        return 'Updated'
    # If the user has no entry for this movie then create it.
    except:
        newRating = Rating(movie_id=movie_id, user_id=user_id, rating=rating)
        moviedb_session.add(newRating)
        moviedb_session.commit()
        flash('Rating set to  %s for %s.' % (rating, user_id))
        return 'Created'


def createRating(login_session, movie_id):
    newRating = Rating(user_id=login_session, movie_id=movie_id, rating=0)
    moviedb_session.add(newRating)
    moviedb_session.commit()
    return newRating


def createMovie(login_session, movieDict):
    # Add the movie to the Movie table.
    newMovie = Movie(
        movie_name=movieDict["movie_name"],
        movie_genre=movieDict["movie_genre"],
        description=movieDict["description"],
        year_released=movieDict["year_released"],
        avg_rating=movieDict["avg_rating"],
        entry_owner=movieDict["entry_owner"],
        image=movieDict["image"],
        trailer_link=movieDict["trailer_link"])
    moviedb_session.add(newMovie)
    moviedb_session.commit()
    return newMovie


# JSON APIs to view Movie Information
# An API to show all movies in the database.
@app.route('/movies/JSON')
def moviesJSON():
    movies = moviedb_session.query(Movie).all()
    return jsonify(movies=[m.serialize for m in movies])


# An API to show all details for a specific movie.
@app.route('/movies/<int:movie_id>/details/JSON')
def movieDetailsJSON(movie_id):
    movie = moviedb_session.query(Movie).filter_by(
        movie_id=movie_id).one()
    items = moviedb_session.query(Movie).filter_by(
        movie_id=movie_id).all()
    return jsonify(movie=[i.serialize for i in items])


# An API to show all movies in a specific genre
@app.route('/movies/genre/<string:movie_genre>/JSON')
def moviesGenreJSON(movie_genre):
    movies = moviedb_session.query(Movie).filter_by(
        movie_genre=movie_genre).all()
    return jsonify(movies=[m.serialize for m in movies])


# An API to show all movies submitted by a specific ID
@app.route('/movies/submitter/<string:entry_owner>/JSON')
def moviesSubmitterJSON(entry_owner):
    movies = moviedb_session.query(Movie).filter_by(
        entry_owner=entry_owner).all()
    return jsonify(movies=[m.serialize for m in movies])


# An API to show all entry owners
@app.route('/movies/submitters/JSON')
def moviesSubmittersJSON():
    submitters = moviedb_session.query(Entry_Owner).all()
    return jsonify(submitters=[s.serialize for s in submitters])


# An API to show all ratings
@app.route('/movies/ratings/JSON')
def moviesRatingsJSON():
    ratings = moviedb_session.query(Rating).all()
    return jsonify(ratings=[r.serialize for r in ratings])


# An API to show all movies rated by a specific ID
@app.route('/movies/ratings/<string:user_id>/JSON')
def moviesRaterJSON(user_id):
    ratings = moviedb_session.query(Rating).filter_by(
        user_id=user_id).all()
    return jsonify(ratings=[r.serialize for r in ratings])


# Show all movies
@app.route('/')
@app.route('/movies/')
def showGenre():
    genres = moviedb_session.query(Genre).order_by(asc(Genre.movie_genre))
    if 'username' not in login_session:
        return render_template('movies_public.html', genres=genres)
    else:
        currentUserPhoto = login_session['picture']
        return render_template(
            'movies.html', genres=genres, currentUserPhoto=currentUserPhoto)


# Show a genre's member movies
@app.route('/movies/genre/<string:movie_genre>/', methods=['GET', 'POST'])
def showGenreMembers(movie_genre):
    genre = (
        moviedb_session.query(Genre).filter_by(movie_genre=movie_genre).one())
    movies = (
        moviedb_session.query(Movie).filter_by(movie_genre=movie_genre).
        order_by(asc(Movie.movie_name)).all())
    if 'username' not in login_session:
        return render_template(
            'genre_members_public.html', genre=genre, movies=movies)
    else:
        currentUserPhoto = login_session['picture']
        return render_template(
            'genre_members.html', genre=genre, movies=movies,
            currentUserPhoto=currentUserPhoto)


# Show a movie's details
@app.route('/movies/detail/<string:movie_id>/')
def showMovieDetails(movie_id):
    #pdb.set_trace()
    movie = moviedb_session.query(Movie).filter_by(movie_id=movie_id).one()
    creator = getDBUserInfo(movie.entry_owner)
    creatorName = (
        moviedb_session.query(Entry_Owner).
        filter_by(email=movie.entry_owner).one())
    currentUserPhoto = login_session['picture']

    if (
        'username' not in login_session or
            creator.email != login_session['email']):
            return render_template(
                'movie_details_public.html', creator=creator, movie=movie,
                currentUserPhoto=currentUserPhoto)
    else:
        return render_template(
            'movie_details.html', creator=creator,
            movie=movie, currentUserPhoto=currentUserPhoto)


# Delete a movie
@app.route('/movies/deleteMovie/<string:movie_id>/', methods=['GET', 'POST'])
def movieDelete(movie_id):
    if 'username' not in login_session:
        return render_template('login_movie_db')
    else:
        movieToDelete = (
            moviedb_session.query(Movie).filter_by(movie_id=movie_id).one())
        creator = getDBUserInfo(movieToDelete.entry_owner)
        currentUserPhoto = login_session['picture']
        if movieToDelete.entry_owner != login_session['email']:
            flash(
                'You are not authorized to delete the movie "%s"!' %
                (movieToDelete.movie_name))
            return redirect(
                url_for('showGenreMembers',
                        movie_genre=movieToDelete.movie_genre))
        elif request.method == 'POST':
            # Confirmed a valid user. Delete movie.
            if 'delete-movie-submit' in request.form:
                movieRatingsToDelete = (
                    moviedb_session.query(Rating).
                    filter_by(movie_id=movie_id).all())
                # Remove each existing rating for this movie.
                for rating in movieRatingsToDelete:
                    moviedb_session.delete(rating)
                moviedb_session.delete(movieToDelete)
                moviedb_session.commit()
                flash('%s Successfully Deleted' % movieToDelete.movie_name)
                return redirect(
                    url_for(
                        'showGenreMembers',
                        movie_genre=movieToDelete.movie_genre))
            if 'delete-movie-cancel' in request.form:
                flash('Deletion of "%s" Cancelled' % movieToDelete.movie_name)
                return redirect(
                    url_for('showGenreMembers',
                            movie_genre=movieToDelete.movie_genre))
        else:
            return render_template(
                'delete_movie.html', creator=creator, movie=movieToDelete,
                currentUserPhoto=currentUserPhoto)


# Create a movie
@app.route('/movies/create/<string:movie_genre>/', methods=['GET', 'POST'])
def movieCreate(movie_genre):
    currentUserPhoto = login_session['picture']
    if 'username' not in login_session:
        return render_template('login_movie_db')
    else:
        if request.method == 'POST':
            # Confirmed a valid user. Create movie.
            if 'new-movie-submit' in request.form:
                
                # Ensure that the adding user registered as contributer.
                setUserAsContributor(login_session)
                
                # Create a new dict to hold movie attributes.
                movieDict = {}
                movieDict["movie_name"] = ""
                movieDict["movie_genre"] = movie_genre
                movieDict["description"] = ""
                movieDict["year_released"] = ""
                movieDict["avg_rating"] = "0"
                movieDict["entry_owner"] = login_session['email']
                movieDict["image"] = ""
                movieDict["trailer_link"] = ""
                if request.form['movie_name']:
                    movieDict["movie_name"] = request.form['movie_name']
                if request.form['genre']:
                    movieDict["movie_genre"] = request.form['genre']
                if request.form['description']:
                    movieDict["description"] = request.form['description']
                if request.form['image']:
                    movieDict["image"] = request.form['image']
                if request.form['trailer_link']:
                    movieDict["trailer_link"] = request.form['trailer_link']
                if request.form['year_released']:
                    movieDict["year_released"] = request.form['year_released']
                if request.form['rateIt']:
                    movieDict["avg_rating"] = request.form['rateIt']
                newMovie = createMovie(login_session, movieDict)
                setRatingForCurrentUser(
                    login_session['email'],
                    newMovie.movie_id, request.form['rateIt'])
                flash('"%s" successfully added.' % (newMovie.movie_name))
                return redirect(
                    url_for(
                        'showGenreMembers', movie_genre=newMovie.movie_genre))
            elif 'new-movie-cancel' in request.form:
                return redirect(
                    url_for(
                        'showGenreMembers', movie_genre=movie_genre))
        else:
            return render_template(
                'new_movie.html', creator=login_session['email'],
                movie_genre=movie_genre, currentUserPhoto=currentUserPhoto)


# Edit an existing movie.
@app.route('/movies/editMovie/<string:movie_id>/', methods=['GET', 'POST'])
def movieEdit(movie_id):
    movie = moviedb_session.query(Movie).filter_by(movie_id=movie_id).one()
    userRating = getRatingForCurrentUser(login_session['email'], movie_id)
    creator = getDBUserInfo(movie.entry_owner)
    creatorName = moviedb_session.query(
        Entry_Owner).filter_by(email=movie.entry_owner).one()
    currentUserPhoto = login_session['picture']
    if ('username' not in login_session or
            creator.email != login_session['email']):
                return render_template(
                    'movie_details_public.html',
                    creator=creator,
                    movie=movie,
                    currentUserPhoto=currentUserPhoto)
    else:
        if request.method == 'POST':
            if 'edit-movie-submit' in request.form:
                if request.form['movie_name']:
                    movie.movie_name = request.form['movie_name']
                if request.form['description']:
                    movie.description = request.form['description']
                if request.form['image']:
                    movie.image = request.form['image']
                if request.form['trailer_link']:
                    movie.trailer_link = request.form['trailer_link']
                if request.form['year_released']:
                    movie.year_released = request.form['year_released']
                if request.form['genre']:
                    movie.movie_genre = request.form['genre']
                if request.form['rateIt']:
                    setRatingForCurrentUser(
                        login_session['email'],
                        movie_id, request.form['rateIt'])
                    movie.avg_rating = getAvgRating(movie_id)

                moviedb_session.add(movie)
                moviedb_session.commit()
                flash('"%s" Successfully Updated.' % (movie.movie_name))
                return redirect(
                    url_for(
                        'showGenreMembers', movie_genre=movie.movie_genre))
            elif 'edit-movie-cancel' in request.form:
                return redirect(
                    url_for(
                        'showGenreMembers', movie_genre=movie.movie_genre))
        else:
            return render_template(
                'edit_movie.html',
                creator=creator,
                movie=movie,
                currentUserPhoto=currentUserPhoto,
                userRating=userRating)


# Rate a movie
@app.route('/movies/rateMovie/<string:movie_id>/', methods=['GET', 'POST'])
def movieEditRating(movie_id):
    if 'username' not in login_session:
        flash('Please login to rate a movie.')
        return render_template('login_movie_db.html')
    else:
        movie = moviedb_session.query(Movie).filter_by(movie_id=movie_id).one()
        genre = (
            moviedb_session.query(Genre).
            filter_by(movie_genre=movie.movie_genre).one())
        movies = (
            moviedb_session.query(Movie).
            filter_by(movie_genre=genre.movie_genre).
            order_by(asc(Movie.movie_name)).all())
        creator = getDBUserInfo(movie.entry_owner)
        creatorName = (moviedb_session.query(Entry_Owner).
                       filter_by(email=movie.entry_owner).one())
        currentUserPhoto = login_session['picture']
        userRating = getRatingForCurrentUser(login_session['email'], movie_id)
        allRatings = getRatingInfo(movie_id)
        updatedUserRating = ""

        if request.method == 'POST':
            if 'rate-movie-submit' in request.form:
                if request.form['updateRateIt']:
                    updatedUserRating = request.form['updateRateIt']
                    userRating.rating = int(updatedUserRating)
                    setRatingForCurrentUser(
                        login_session['email'], movie_id, userRating.rating)
                    avgRating = getAvgRating(movie_id)
                    movie.avg_rating = avgRating
                    moviedb_session.add(movie)
                    moviedb_session.commit()
                return redirect(
                    url_for('showGenreMembers', movie_genre=movie.movie_genre))
            elif 'rate-movie-cancel' in request.form:
                return redirect(
                    url_for('showGenreMembers', movie_genre=movie.movie_genre))
        else:
            return render_template(
                'rate_movie.html',
                creator=creator,
                movie=movie,
                currentUserPhoto=currentUserPhoto,
                userRating=userRating,
                allRatings=allRatings
            )


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    urlText = (
        'https://graph.facebook.com/oauth/access_token?' +
        'grant_type=fb_exchange_token&client_id=%s&' +
        'client_secret=%s&fb_exchange_token=%s')
    url = urlText % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"

    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = (
        'https://graph.facebook.com/v2.8/me?' +
        'access_token=%s&fields=name,id,email' % token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session for proper logout
    login_session['access_token'] = token

    # Get user picture
    url = (
        'https://graph.facebook.com/v2.8/me/picture?access_token=' +
        '%s&redirect=0&height=200&width=200' % token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += (' " style = "width: 200px;' +
               'height: 200px;border-radius: 150px;' +
               '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> ')

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = ('https://graph.facebook.com/%s/permissions?access_token=%s'
           % (facebook_id, access_token))
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += (' " style = "width: 150px; ' +
               'height: 150px;border-radius: 150px;' +
               '-webkit-border-radius: 150px;' +
               '-moz-border-radius: 150px;"> ')
    flash("You are now logged in as %s." % login_session['username'])
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
            del login_session['username']
            del login_session['email']
            del login_session['picture']
            del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showGenre'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showGenre'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
