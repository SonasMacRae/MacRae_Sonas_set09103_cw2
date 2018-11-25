# Imports used
from flask import *
from flask import Flask, flash, redirect, render_template, request, session, abort
import sqlite3
import hashlib
import datetime
import os


app = Flask(__name__)
db_location = 'var/cw.db'
app.secret_key = os.urandom(12)


# Used to make dictionaries
def make_dicts(cursor, row):
	
	return dict((cursor.description[idx][0], value)
		for idx, value in enumerate(row))


# Function used to query the database
def query_db(query, args=(), one=False):
	
	cur = get_db().execute(query, args)
	rv = cur.fetchall()
	cur.close()
	
	return (rv[0] if rv else None) if one else rv


# Gets a connection to the database
def get_db():
	
	db = getattr(g, 'db', None)
	if db is None:
		db = sqlite3.connect(db_location)
		g.db = db
	db.row_factory = sqlite3.Row
	print db.row_factory
	
	return db


# Closes the connection to the database
def close_db_connection(exception):
	
	db = getattr(g, 'db', None)
	if db is not None:
		db.close()


# Initilises the database
def init_db():
	
	with app.app_context():
		db = get_db()
		with app.open_resource('schema.sql', mode='r') as f:
			db.cursor().executescript(f.read())
		db.commit()


# Used to build user objects
class User:
	
	def __init__(self, username, time):
		self.username = username
		self.time = time


# Used to build joke objects
class Joke:
	
	def __init__(self, joke, user, time, genre, jokeid, rating):
		self.joke = joke
		self.user = user
		self.time = time
		self.genre = genre
		self.jokeid = jokeid
		self.rating = rating


# Used to build comment objects
class Comment:

	def __init__(self, commentid, jokeid, user, time, comment):
		self.commentid = commentid
		self.jokeid = jokeid
		self.user = user
		self.time = time
		self.comment = comment


# Turns datetime strings into a more beautiful format
def TimeFixingTool(time):
	timesplit = time.split('.')
	timesplit2 = timesplit[0].split(' ')
	ddmmyy = timesplit2[0].split('-')
	newddmmyy = ddmmyy[2] + "/" + ddmmyy[1] + "/" + ddmmyy[0]
	splitminutes = timesplit2[1].split(':')
	newminutes = splitminutes[0] + ":" + splitminutes[1]
	
	return newminutes + ", " + newddmmyy


@app.route("/testtest/")
def testtest():
	return "hello world"


# Deals with 404 errors
@app.errorhandler(404)
def page_not_found(error):
	return render_template('errorpage.html'), 404


# The home URL, checks if the user is logged in
@app.route("/")
def root():
	if not session.get('logged_in'):
		return render_template('login.html')	
	else:
		return displayjokes()


# Generates a HTML page for making new posts
@app.route("/newpost/")
def newpost():
	
	return render_template("newpost.html")


# Generates a comments HTML page based on the jokeid
@app.route("/comments/<jokeid>")
def newcomment(jokeid):
	
	jokes = []
	comments = []
	
	# Adds joke objects to an object list from the database that share the same id as the jokeid
	for joke in query_db('select * from jokes'):
		if str(joke['id']) == str(jokeid):
			newjoke = Joke(joke['joke'], joke['user'], TimeFixingTool(joke['timejoined']), joke['category'], joke['id'], [0])
			jokes.append(newjoke)
	
	# Adds comment objects to an object list from the database that share the same id as the jokeid
	for comment in query_db('select * from comments'):
		if str(comment['jokeid']) == str(jokeid):
			newcomment = Comment(comment['id'], comment['jokeid'], comment['user'], comment['timeofcomment'], comment["comment"])
			comments.append(comment)
			
			print comment['id']

	session['jokeid'] = jokeid
	
	# Renders the comments HTML page and passes in the comments and jokes object lists
	return render_template('newcomment.html', comments=comments, jokes=jokes)


# Route that deals with postcomment POST requests
@app.route("/postcomment", methods=['POST'])
def postcomment():
	
	# Saves the last comment_id from the comments table in the database
	for comment in query_db('select * from comments'):
		commentid = comment['id']
	
	# Create variables that will be used to build the new comment object
	newcommentid = commentid + 1
	time = str(datetime.datetime.now())
	user = str(session['username'])
	comment = request.form['comment']	
	jokeid = session['jokeid']	
	print "this is the new comment id", newcommentid	
	# A command that will be executed that will save the comment object to the database
	command = "insert into comments values (\"" + str(newcommentid) + "\""
	command += ", \"" + str(jokeid) + "\""
	command += ", \"" + user + "\""
	command += ", \"" + time + "\""
	command += ", \"" + comment + "\")"

	# Get a connection to the datbase
	db = get_db()
	# Execute the command
	db.cursor().execute(command)
	# Commit the change
	db.commit()

	return newcomment(session['jokeid'])


# Deals with postjokes POST requests
@app.route("/postjoke", methods=['POST'])
def postjoke():
	
	# Saves the users username as a string
	user = str(session['username'])
	
	jokeid = 0	

	# Fetches the last jokeid from the jokes table in the database
	for joke in query_db('select * from jokes'):
		jokeid = joke['id']

	# Create variables which will be used to build a command
	jid = jokeid + 1
	timejoined = datetime.datetime.now()
	joke = request.form['joke']
	category = request.form['category']
	upvote = 0
	downvote = 0

	# String command which will be used to save the joke variables
	# to the joke table in the database
	command = "insert into jokes values (\"" + str(jid) + "\""
	command += ", \"" + user + "\""
	command += ", \"" + str(timejoined) + "\""
	command += ", \"" + joke + "\""
	command += ", \"" + category + "\""
	command += ", \"" + str(upvote) + "\""
	command += ", \"" + str(downvote) + "\")"

	# Executes and commits the command stated above
	db = get_db()
	db.cursor().execute(command)
	db.commit()
	
	# Returns the page which displays all of the jokes saved in the databse
	return displayjokes()


# URL route to render the HTML page to deal with new users
@app.route("/newaccount/")
def newaccount():
	
	return render_template('signup.html')


# Deals with signup POST methods
@app.route("/signup", methods=['POST'])
def signup():
	
	# Fetches username, password and time data from the rendered HTML page
	username = request.form['username']
	password = request.form['password']
	time = datetime.datetime.now()

	# Checks if the username is available
	for user in query_db('select * from users'):
		if user['username'].lower() == str(username.lower()):
			return render_template('signup.html')
	
	if not username or not password:
		return render_template('signup.html')
	
	# Hashes the password
	hashedPassword = hashlib.md5(password.encode())
	hashedPassword = hashedPassword.hexdigest()
	# as a string
	command = "insert into users values (\""
	command += str(time)
	command += "\", \"" + str(username) + "\", \"" + str(hashedPassword) + "\")" 
	
	# Executes the command above and commits the change to the database
	db = get_db()
	db.cursor().execute(command)
	db.commit()
	
	session['logged_in'] = False
		
	# Returns the root function to take the user back to the login screen 
	return root()


# Renders the HTML page that deals with signing in
@app.route("/signin/")
def signin():
	
	return render_template('login.html')


# Deals with login POST requests
@app.route("/login", methods=['POST'])
def signinFunction():
	
	# Saves the username and password details from the rendered HTML page
	# and saves them into variables
	username = request.form['username']
	password = str(request.form['password'])
	hashedPassword = hashlib.md5(password.encode())
	hashedPassword = hashedPassword.hexdigest()
	
	# Checks the username and password against the database to see
	# if they are valid
	for dbUsername in query_db('select * from users'):
		if username == dbUsername['username'] and dbUsername['password'] == str(hashedPassword):
			session['logged_in'] = True
			session['username'] = username
			return root()
 
	return root()


# Generates the HTML page for the users profile
@app.route("/mypage/")
def mypage():
	
	jokes = []
	
	# Adds joke objects to a list that share the same username as the user
	# that is using the website
	for joke in query_db('select * from jokes'):
		if joke['user'] == str(session['username']):
			newjoke = Joke(joke['joke'], joke['user'], TimeFixingTool(joke['timejoined']), joke['category'], joke['id'], [0])
			jokes.append(newjoke)
	
	# Reverses the list so the newer posts appear at the top of the page
	jokes = jokes[::-1]	
	
	# Render the profile HTML page and passes in the joke list and the username variable
	return render_template('userProfile.html', jokes=jokes, user=str(session['username']))


@app.route('/deletecomment', methods=['POST'])
def deletecomment():

	print "does this function even do anything"	
	db = get_db()
	db.cursor().execute('delete from comments where id = ?', [request.form['cid']])
	db.commit()
	print "is this even working"
	print str(request.form['cid'])

	return newcomment(session['jokeid'])
	

# Deals delete POST requests, used to delete posts from the database
@app.route('/delete', methods=['POST'])
def deletepost():

	# Delete the record from the database and commit the change
	db = get_db()
	db.cursor().execute('delete from jokes where id = ?', [request.form['jid']])
	db.commit()
		
	# Checks the type of page in which the request was made from
	# And returns the user back to that page
	if request.form['pagetype'] == "profile":	
		return mypage()	
	else:
		return displayjokes()


# Deals with logout requests
@app.route("/logout")
def logout():
	
	# Set the session['logged_in'] boolean to False
	session['logged_in'] = False
	
	# Return the root
	return root()


# Used to dipplay all of the users who have signed up to the site,
# this is used for testing purposes and is not easily accessible
# from the website
@app.route("/displayusers/")
def displayusers():
	
	users = []
	
	for user in query_db('select * from users'):
		users.append(user['username'])
	
	return render_template('displayusers.html', users=users)


# URL route used to display all of the jokes stored in the database
@app.route("/displayjokes/")
def displayjokes():
	
	# Checks if the user is logged in, if not they will be
	# redirected to the login page
	if not session.get('logged_in'):
		return root()

	genres = []
	
	# Adds all of the genres found in the jokes table of the database to a list
	for joke in query_db('select * from jokes'):
		if joke['category'] not in genres:
			genres.append(joke['category'])
	
	ojokes = []
	
	# Adds all of the jokes stored in the jokes table of the database to a list
	for joke in query_db('select * from jokes'):
		newjoke = Joke(joke['joke'], joke['user'], TimeFixingTool(joke['timejoined']), joke['category'], joke['id'], [0])
		ojokes.append(newjoke)
		jokes = ojokes[::-1]	

	# Renders a HTML page and passes in the jokes and genres objects 
	return render_template('displayjokes.html', jokes=jokes, genres=genres)


# Route used to display a specific users profile page
@app.route("/user/<search>")
def searchuser(search):

	users = []

	# Adds the users data from the database into an object list	
	for user in query_db('select * from users'):
		if user['username'] == search:
			newuser = User(search, TimeFixingTool(user['time']))
			users.append(newuser)
	
	jokes = []

	# Adds all of the jokes posted by the users profile which will be displayed
	for joke in query_db('select * from jokes'):
		if joke['user'] == search:
			newjoke = Joke(joke['joke'], joke['user'], TimeFixingTool(joke['timejoined']), joke['category'], joke['id'], [0])
			jokes.append(newjoke)
	
	# Reverses the jokes list so the new posts will appear first
	jokes = jokes[::-1]	
	
	return render_template('searchuserprofile.html', users=users, jokes=jokes)


# HTML page to display all of the genres found in the jokes table of the database
@app.route("/genres/")
def genres():

	genres = []

	# Adds all of the genres from the jokes table in the database to a list	
	for joke in query_db('select * from jokes'):
		if joke['category'] not in genres:
			genres.append(joke['category'])
	
	# Renders a HTML page to display the genres and passes in the genre list
	return render_template('genres.html', genres=genres)


# Displays all of the jokes from a certain genre
@app.route("/filterjokes/<search>")
def filterjokes(search):
	
	jokes = []
	
	# Adds all of the jokes from the certain genre to an object list
	for joke in query_db('select * from jokes'):
		if joke['category'] == search:
			newjoke = Joke(joke['joke'], joke['user'], TimeFixingTool(joke['timejoined']), joke['category'], joke['id'], [0])
			jokes.append(newjoke)
	
	# Reverses the jokes list so the newer posts appear first
	jokes = jokes[::-1]	
	
	# Render the HTML page to display the jokes and pass in the jokes and search data
	return render_template('filterjokes.html', jokes=jokes, category=search)


@app.route("/updatecomment/<commentid>")
def updatethecomment(commentid):

	comments = []
	
	for comment in query_db('select * from comments'):
		if str(commentid) == str(comment['id']):
			newcomment = Comment(comment['id'], comment['jokeid'], comment['user'], comment['timeofcomment'], comment['comment'])
			comments.append(newcomment)
	
	return render_template('updatecomment.html', comments=comments)


# Route used to display the HTML page used to update posts
@app.route("/updatepost/<postid>")
def updatethepost(postid):

	jokes = []

	for joke in query_db('select * from jokes'):
		if str(postid) == str(joke['id']): 		
			newjoke = Joke(joke['joke'], joke['user'], joke['timejoined'], joke['category'], joke['id'], [0])
			jokes.append(newjoke)
	
	# Renders the html page and passes in the jokes list
	return render_template('updatepost.html', jokes=jokes)

@app.route('/updatecomment', methods=['POST'])
def updatecomment():
	
	command = "UPDATE comments SET comment = "
	command += "\'" + request.form['comment'] + "\' WHERE id = \'" + request.form['cid'] + "\'" 
	
	db = get_db()	
	db.cursor().execute(command)
	db.commit()
	
	return newcomment(session['jokeid'])


# Deals with requests to make updates to posts
@app.route('/updatepost', methods=['POST'])
def updatepost():
	
	# String command which will be used to update the jokes table in the database
	command = "UPDATE jokes SET joke = "
	command += "\'" + request.form['joke'] + "\' WHERE id = \'" + request.form['jid'] + "\'" 
	
	# Executes the command created above and commits the change
	db = get_db()	
	db.cursor().execute(command)
	db.commit()
	
	# Returns the displayjokes function which will display all of the jokes stored in the database
	return displayjokes()


if __name__ == "__main__":

	app.run(host='0.0.0.0', debug=True)
