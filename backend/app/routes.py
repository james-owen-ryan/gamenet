import csv
import os
import gensim
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, g
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, login_user, logout_user, current_user, login_required
from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired
from gamesage import GameSage
from game import GameNetGame, GameSageGame, GameIdea

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'gamenet.db')
# These get set below
app.gamenet_ontology_database = None
app.gamesage_ontology_database = None
app.ontology_term_id_dictionary = None
app.ontology_tf_idf_model = None
app.ontology_lsa_model = None
app.gamenet_gameplay_database = None
app.gamesage_gameplay_database = None
app.gameplay_term_id_dictionary = None
app.gameplay_tf_idf_model = None
app.gameplay_lsa_model = None

db = SQLAlchemy(app)
lm = LoginManager()
lm.init_app(app)


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(user_name=form.user_name.data).first()
        if not user:
            user = User(user_name=form.user_name.data)
            db.session.add(user)
            db.session.commit()

        login_user(user)

        return redirect('/gamesage')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


@app.before_request
def before_request():
    g.user = current_user


class LoginForm(Form):
    user_name = StringField('name', validators=[DataRequired()])


# Database Models

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(64))
    game_net_requests = db.relationship('GameNetGameRequest', backref='user', lazy='dynamic')
    icon_clicks = db.relationship('IconClick', backref='user', lazy='dynamic')
    game_sage_queries = db.relationship('GameSageQuery', backref='user', lazy='dynamic')
    game_net_queries = db.relationship('GameNetQuery', backref='user', lazy='dynamic')
    game_net_link_clicks = db.relationship('GameNetLinkClick', backref='user', lazy='dynamic')

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.id)
        except NameError:
            return str(self.id)

    def __repr__(self):
        return "<User {0} | {1}>".format(self.id, self.user_name)


class GameNetGameRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(16))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime)
    game_id = db.Column(db.Integer)

    def __repr__(self):
        return "<GameNetGameRequest {0} | {1} | {2} | {3} | {4} >".format(self.id,
                                                                          self.ip,
                                                                          self.user_id,
                                                                          self.timestamp,
                                                                          self.game_id)


class GameNetQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(16))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime)
    game_query = db.Column(db.String(255))
    game_id = db.Column(db.Integer)

    def __repr__(self):
        return "<GameNetQuery {0} | {1} | {2} | {3} | {4} | {5} >".format(self.id,
                                                                    self.ip,
                                                                    self.user_id,
                                                                    self.timestamp,
                                                                    self.game_query,
                                                                    self.game_id)


class IconClick(db.Model):
    WIKI = 'wikipedia'
    YOUTUBE = 'youtube'
    GOOGLE = 'google'

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(16))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime)
    icon_type = db.Column(db.String(9))
    game_id = db.Column(db.Integer)

    def __repr__(self):
        return "<IconClick {0} | {1} | {2} | {3} | {4} | {5} >".format(self.id,
                                                                       self.ip,
                                                                       self.user_id,
                                                                       self.timestamp,
                                                                       self.icon_type,
                                                                       self.game_id)


class GameNetLinkClick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(16))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime)
    game_source_id = db.Column(db.Integer)
    game_dest_id = db.Column(db.Integer)

    def __repr__(self):
        return "<GameNetLinkClick {0} | {1} | {2} | {3} | {4} | {5} >".format(self.id,
                                                                              self.ip,
                                                                              self.user_id,
                                                                              self.timestamp,
                                                                              self.game_source_id,
                                                                              self.game_dest_id)


class GameSageQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(16))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime)
    game_sage_query = db.Column(db.PickleType)

    def __repr__(self):
        return "<GameSageQuery {0} | {1} | {2} | {3} | {4} >".format(self.id,
                                                                     self.ip,
                                                                     self.user_id,
                                                                     self.timestamp,
                                                                     self.game_sage_query)


@app.route('/gamenet/icon_click', methods=['POST'])
def icon_click():
    if current_user.is_authenticated():
        ic = IconClick(user=current_user, ip=request.remote_addr,
                                 timestamp=datetime.now(), icon_type=request.form['icon_type'], game_id=request.form['game_id'])
    else:
        ic = IconClick(user=None, ip=request.remote_addr,
                       timestamp=datetime.now(), icon_type=request.form['icon_type'], game_id=request.form['game_id'])
    db.session.add(ic)
    db.session.commit()
    try:
        if logger:
            logger.debug(ic)
    except NameError:
        pass

    return "OK"


@app.route('/gamenet/gamenet_link_click', methods=['POST'])
def game_link_click():
    if current_user.is_authenticated():
        gl = GameNetLinkClick(user=current_user,
                              ip=request.remote_addr,
                              timestamp=datetime.now(),
                              game_source_id=request.form['game_source_id'],
                              game_dest_id=request.form['game_dest_id'])
    else:
        gl = GameNetLinkClick(user=None,
                              ip=request.remote_addr,
                              timestamp=datetime.now(),
                              game_source_id=request.form['game_source_id'],
                              game_dest_id=request.form['game_dest_id'])

    db.session.add(gl)
    db.session.commit()
    try:
        if logger:
            logger.debug(gl)
    except NameError:
        pass
    return "OK"


@app.route('/')
def gamecip_project_home():
    return redirect('http://gamecip.soe.ucsc.edu/projects')


@app.route('/gamenet')
def gamenet_home():
    """Render the GameNet homepage."""
    return render_template('gamenet_index.html', entered_unknown_game=False)


@app.route('/gamenet/about')
def gamenet_about():
    """Render the about page."""
    return render_template('gamenet_about.html')


@app.route('/gamenet/faq')
def gamenet_faq():
    """Render the FAQ page."""
    return render_template('gamenet_faq.html')


@app.route('/gamenet/ontology')
def gamenet_home_ontology():
    """Render the home page of the ontology network."""
    return render_template('gamenet_index-ontology.html', entered_unknown_game=False)


@app.route('/gamenet/ontology/findByTitle=<selected_game_title>')
def render_gamenet_entry_given_game_title_ontology(selected_game_title):
    if any(game for game in app.gamenet_ontology_database if game.title.lower() == selected_game_title.lower()):
        selected_game = next(
            game for game in app.gamenet_ontology_database if game.title.lower() == selected_game_title.lower()
        )
        if current_user.is_authenticated():
            gamenet_query = GameNetQuery(
                user=current_user, ip=request.remote_addr, game_query=selected_game_title,
                game_id=selected_game.id, timestamp=datetime.now()
            )
        else:
            gamenet_query = GameNetQuery(
                user=None, ip=request.remote_addr, game_query=selected_game_title,
                game_id=selected_game.id, timestamp=datetime.now()
            )
        db.session.add(gamenet_query)
        db.session.commit()
        try:
            if logger:
                logger.debug(gamenet_query)
        except NameError:
            pass
        return render_template('game.html', network='ontology', game=selected_game)
    else:
        # The game title/arbitrary query that the user typed in does not match
        # any game in our database, so keep displaying the home page, but express this
        if current_user.is_authenticated():
            gamenet_query = GameNetQuery(
                user=current_user, ip=request.remote_addr, game_query=selected_game_title, timestamp=datetime.now()
            )
        else:
            gamenet_query = GameNetQuery(
                user=None, ip=request.remote_addr, game_query=selected_game_title, timestamp=datetime.now()
            )
        db.session.add(gamenet_query)
        db.session.commit()
        try:
            if logger:
                logger.debug(gamenet_query)
        except NameError:
            pass
        return render_template('gamenet_index-ontology.html', entered_unknown_game=True)


@app.route('/gamenet/ontology/games/<selected_game_id>')
def render_gamenet_entry_given_game_id_ontology(selected_game_id):
    """Render the GameNet entry for a user-selected game."""
    selected_game = app.gamenet_ontology_database[int(selected_game_id)]
    if current_user.is_authenticated():
        gamenet_game_request = GameNetGameRequest(
            user=current_user, ip=request.remote_addr, game_id=selected_game_id, timestamp=datetime.now()
        )
    else:
        gamenet_game_request = GameNetGameRequest(
            user=None, ip=request.remote_addr, game_id=selected_game_id, timestamp=datetime.now()
        )
    db.session.add(gamenet_game_request)
    db.session.commit()
    try:
        if logger:
            logger.debug(gamenet_game_request)
    except NameError:
        pass
    return render_template('game.html', network='ontology', game=selected_game)


@app.route('/gamenet/gameplay')
def gamenet_home_gameplay():
    """Render the home page of the ontology network."""
    return render_template('gamenet_index-gameplay.html', entered_unknown_game=False)


@app.route('/gamenet/gameplay/findByTitle=<selected_game_title>')
def render_gamenet_entry_given_game_title_gameplay(selected_game_title):
    if any(game for game in app.gamenet_gameplay_database if game and
            # Have to watch out for all the None filler entries in gameplay database
            game.title.lower() == selected_game_title.lower()):
        selected_game = next(
            game for game in app.gamenet_gameplay_database if game and
            game.title.lower() == selected_game_title.lower()
        )
        if current_user.is_authenticated():
            gamenet_query = GameNetQuery(
                user=current_user, ip=request.remote_addr, game_query=selected_game_title,
                game_id=selected_game.id, timestamp=datetime.now()
            )
        else:
            gamenet_query = GameNetQuery(
                user=None, ip=request.remote_addr, game_query=selected_game_title,
                game_id=selected_game.id, timestamp=datetime.now()
            )
        db.session.add(gamenet_query)
        db.session.commit()
        try:
            if logger:
                logger.debug(gamenet_query)
        except NameError:
            pass
        return render_template('game.html', network='gameplay', game=selected_game)
    else:
        # The game title/arbitrary query that the user typed in does not match
        # any game in our database, so keep displaying the home page, but express this
        if current_user.is_authenticated():
            gamenet_query = GameNetQuery(
                user=current_user, ip=request.remote_addr, game_query=selected_game_title, timestamp=datetime.now()
            )
        else:
            gamenet_query = GameNetQuery(
                user=None, ip=request.remote_addr, game_query=selected_game_title, timestamp=datetime.now()
            )
        db.session.add(gamenet_query)
        db.session.commit()
        try:
            if logger:
                logger.debug(gamenet_query)
        except NameError:
            pass
        return render_template('gamenet_index-gameplay.html', entered_unknown_game=True)


@app.route('/gamenet/gameplay/games/<selected_game_id>')
def render_gamenet_entry_given_game_id_gameplay(selected_game_id):
    """Render the GameNet entry for a user-selected game."""
    # Because we have gaps in the IDs held by all games (unlike in the ontology network,
    # which has all IDs in the range 0-11828), we have to find the selected game differently
    selected_game = app.gamenet_gameplay_database[int(selected_game_id)]
    if current_user.is_authenticated():
        gamenet_game_request = GameNetGameRequest(
            user=current_user, ip=request.remote_addr, game_id=selected_game_id, timestamp=datetime.now()
        )
    else:
        gamenet_game_request = GameNetGameRequest(
            user=None, ip=request.remote_addr, game_id=selected_game_id, timestamp=datetime.now()
        )
    db.session.add(gamenet_game_request)
    db.session.commit()
    try:
        if logger:
            logger.debug(gamenet_game_request)
    except NameError:
        pass
    return render_template('game.html', network='gameplay', game=selected_game)


@app.route('/gamenet/ontology/game_idea', methods=['POST'])
def generate_gamenet_ontology_entry_for_game_idea_from_gamesage():
    """Generate and render a GameNet entry for a GameSage query."""
    idea_text = request.form['user_submitted_text']
    related_games_str = request.form['most_related_games_str']
    unrelated_games_str = request.form['least_related_games_str']
    if current_user.is_authenticated():
        gsq = GameSageQuery(
            user=current_user, game_sage_query=idea_text, ip=request.remote_addr, timestamp=datetime.now()
        )
    else:
        gsq = GameSageQuery(
            user=None, game_sage_query=idea_text, ip=request.remote_addr, timestamp=datetime.now()
        )
    db.session.add(gsq)
    db.session.commit()
    try:
        if logger:
            logger.debug(gsq)
    except NameError:
        pass
    game_idea = GameIdea(
        idea_text=idea_text, related_games_str=related_games_str, unrelated_games_str=unrelated_games_str
    )
    # Set the title and year of each entry in the game idea's un/related games listings
    for entry in game_idea.related_games+game_idea.unrelated_games:
        title = app.gamenet_ontology_database[int(entry.game_id)].title
        year = app.gamenet_ontology_database[int(entry.game_id)].year
        entry.set_game_title_and_year(title=title, year=year)
    return render_template('game_idea.html', network='ontology', game_idea=game_idea)

@app.route('/gamenet/gameplay/game_idea', methods=['POST'])
def generate_gamenet_gameplay_entry_for_game_idea_from_gamesage():
    """Generate and render a GameNet entry for a GameSage query."""
    idea_text = request.form['user_submitted_text']
    related_games_str = request.form['most_related_games_str']
    unrelated_games_str = request.form['least_related_games_str']
    if current_user.is_authenticated():
        gsq = GameSageQuery(
            user=current_user, game_sage_query=idea_text, ip=request.remote_addr, timestamp=datetime.now()
        )
    else:
        gsq = GameSageQuery(
            user=None, game_sage_query=idea_text, ip=request.remote_addr, timestamp=datetime.now()
        )
    db.session.add(gsq)
    db.session.commit()
    try:
        if logger:
            logger.debug(gsq)
    except NameError:
        pass
    game_idea = GameIdea(
        idea_text=idea_text, related_games_str=related_games_str, unrelated_games_str=unrelated_games_str
    )
    # Set the title and year of each entry in the game idea's un/related games listings
    for entry in game_idea.related_games+game_idea.unrelated_games:
        title = app.gamenet_gameplay_database[int(entry.game_id)].title
        year = app.gamenet_gameplay_database[int(entry.game_id)].year
        entry.set_game_title_and_year(title=title, year=year)
    return render_template('game_idea.html', network='gameplay', game_idea=game_idea)


@app.route('/gamesage')
def gamesage_home():
    """Render the GameSage homepage."""
    return render_template('gamesage_index.html')


@app.route('/gamesage/about')
def gamesage_about():
    """Render the about page."""
    return render_template('gamesage_about.html')


@app.route('/gamesage/faq')
def gamesage_faq():
    """Render the FAQ page."""
    return render_template('gamesage_faq.html')


@app.route('/gamesage/session', methods=['POST'])
def gamesage_session():
    """Render a GameSage session page."""
    idea_text_to_be_refined = request.form['idea_text_to_be_refined']
    return render_template('gamesage_session.html', idea_text_to_be_refined=idea_text_to_be_refined)


@app.route('/gamesage/session/guided')
def gamesage_guided_session():
    """Render a guided GameSage session page."""
    return render_template('gamesage_guided_session.html')


@app.route('/gamesage/ontology/submittedText', methods=['POST'])
def generate_gamenet_ontology_query_for_game_idea():
    """Generate a query for GameNet."""
    user_submitted_text = request.form['user_submitted_text']
    gamesage = GameSage(
        network='ontology', database=app.gamesage_ontology_database,
        term_id_dictionary=app.ontology_term_id_dictionary,
        tf_idf_model=app.ontology_tf_idf_model, lsa_model=app.ontology_lsa_model,
        user_submitted_text=user_submitted_text
    )
    return jsonify(
        user_submitted_text=user_submitted_text,
        most_related_games_str=gamesage.most_related_games_str,
        least_related_games_str=gamesage.least_related_games_str
    )


@app.route('/gamesage/gameplay/submittedText', methods=['POST'])
def generate_gamenet_gameplay_query_for_game_idea():
    """Generate a query for GameNet."""
    user_submitted_text = request.form['user_submitted_text']
    gamesage = GameSage(
        network='gameplay', database=app.gamesage_gameplay_database,
        term_id_dictionary=app.gameplay_term_id_dictionary,
        tf_idf_model=app.gameplay_tf_idf_model, lsa_model=app.gameplay_lsa_model,
        user_submitted_text=user_submitted_text
    )
    return jsonify(
        user_submitted_text=user_submitted_text,
        most_related_games_str=gamesage.most_related_games_str,
        least_related_games_str=gamesage.least_related_games_str
    )


def load_gamenet_ontology_database():
    """Load the database of GameNet game representations from a TSV file."""
    database = []
    with open('static/games_metadata-ontology.tsv', 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for row in reader:
            game_id, title, year, platform, wiki_url, wiki_summary, related_games_str, unrelated_games_str = row
            game_object = (
                GameNetGame(
                    game_id, title, year, platform, wiki_url,
                    wiki_summary, related_games_str, unrelated_games_str
                )
            )
            database.append(game_object)
    # Now that all the games have been read in, allow each game's un/related-games entries to be
    # attributed game titles and years via lookup into the database that is now fully populated
    for game in database:
        for entry in game.related_games+game.unrelated_games:
            title = database[int(entry.game_id)].title
            year = database[int(entry.game_id)].year
            entry.set_game_title_and_year(title=title, year=year)
    return database


def load_gamesage_ontology_database():
    """Load the database of GameSage game representations from a TSV file."""
    database = []
    with open('static/game_lsa_vectors-ontology.tsv', 'r') as tsv_file:
        reader = csv.reader(tsv_file, delimiter='\t')
        for row in reader:
            game_id, title, year, lsa_vector_str = row
            game_object = GameSageGame(game_id, title, lsa_vector_str)
            database.append(game_object)
    return database


def load_ontology_term_id_dictionary():
    """Load the term-ID dictionary for our corpus."""
    term_id_dictionary = gensim.corpora.Dictionary.load('./static/ontology-id2term.dict')
    return term_id_dictionary


def load_ontology_tf_idf_model():
    """Load our tf-idf model."""
    tf_idf_model = (
        gensim.models.TfidfModel.load('./static/ontology-tfidf_model')
    )
    return tf_idf_model


def load_ontology_lsa_model():
    """Load our LSA model."""
    lsa_model = gensim.models.LsiModel.load('./static/ontology-model_207.lsi')
    return lsa_model


def load_gamenet_gameplay_database():
    """Load the database of GameNet game representations from a TSV file."""
    database = []
    with open('static/games_metadata-gameplay.tsv', 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for row in reader:
            game_id, title, year, platform, wiki_url, wiki_summary, related_games_str, unrelated_games_str = row
            game_object = (
                GameNetGame(
                    game_id, title, year, platform, wiki_url,
                    wiki_summary, related_games_str, unrelated_games_str
                )
            )
            # Append a bunch of None entries so that games are indexed by their
            # IDs, which allows fast accessing
            while len(database) < int(game_id):
                database.append(None)
            # Now can append the game_object at the index matching its game_id
            database.append(game_object)
    # Now that all the games have been read in, allow each game's un/related-games entries to be
    # attributed game titles and years via lookup into the database that is now fully populated
    for game in [game for game in database if game]:
        for entry in game.related_games+game.unrelated_games:
            game_object_of_that_entry = database[int(entry.game_id)]
            title = game_object_of_that_entry.title
            year = game_object_of_that_entry.year
            entry.set_game_title_and_year(title=title, year=year)
    return database


def load_gamesage_gameplay_database():
    """Load the database of GameSage game representations from a TSV file."""
    database = []
    with open('static/game_lsa_vectors-gameplay.tsv', 'r') as tsv_file:
        reader = csv.reader(tsv_file, delimiter='\t')
        for row in reader:
            game_id, title, year, lsa_vector_str = row
            game_object = GameSageGame(game_id, title, lsa_vector_str)
            database.append(game_object)
    return database


def load_gameplay_term_id_dictionary():
    """Load the term-ID dictionary for our corpus."""
    term_id_dictionary = gensim.corpora.Dictionary.load('./static/gameplay-id2term.dict')
    return term_id_dictionary


def load_gameplay_tf_idf_model():
    """Load our tf-idf model."""
    tf_idf_model = (
        gensim.models.TfidfModel.load('./static/gameplay-tfidf_model')
    )
    return tf_idf_model


def load_gameplay_lsa_model():
    """Load our LSA model."""
    lsa_model = gensim.models.LsiModel.load('./static/gameplay-model_334.lsi')
    return lsa_model


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    # Prepare the ontology network (i.e., tools as fueled by Wikipedia corpus)
    app.gamenet_ontology_database = load_gamenet_ontology_database()
    app.gamesage_ontology_database = load_gamesage_ontology_database()
    app.ontology_term_id_dictionary = load_ontology_term_id_dictionary()
    app.ontology_tf_idf_model = load_ontology_tf_idf_model()
    app.ontology_lsa_model = load_ontology_lsa_model()
    # Prepare the gameplay network (i.e., tools as fueled by GameFAQs corpus)
    app.gamenet_gameplay_database = load_gamenet_gameplay_database()
    app.gamesage_gameplay_database = load_gamesage_gameplay_database()
    app.gameplay_term_id_dictionary = load_gameplay_term_id_dictionary()
    app.gameplay_tf_idf_model = load_gameplay_tf_idf_model()
    app.gameplay_lsa_model = load_gameplay_lsa_model()
    app.run(debug=True)
else:
    app.secret_key = 'super secret key'
    # Prepare the ontology network (i.e., tools as fueled by Wikipedia corpus)
    app.gamenet_ontology_database = load_gamenet_ontology_database()
    app.gamesage_ontology_database = load_gamesage_ontology_database()
    app.ontology_term_id_dictionary = load_ontology_term_id_dictionary()
    app.ontology_tf_idf_model = load_ontology_tf_idf_model()
    app.ontology_lsa_model = load_ontology_lsa_model()
    # Prepare the gameplay network (i.e., tools as fueled by GameFAQs corpus)
    app.gamenet_gameplay_database = load_gamenet_gameplay_database()
    app.gamesage_gameplay_database = load_gamesage_gameplay_database()
    app.gameplay_term_id_dictionary = load_gameplay_term_id_dictionary()
    app.gameplay_tf_idf_model = load_gameplay_tf_idf_model()
    app.gameplay_lsa_model = load_gameplay_lsa_model()

if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler
    logger = logging.getLogger('app_info')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(RotatingFileHandler('gamenet_actions.log', maxBytes=1024 * 1024 * 10, backupCount=20))

