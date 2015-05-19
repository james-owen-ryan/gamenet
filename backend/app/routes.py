import csv
import gensim
from flask import Flask, render_template, jsonify, request
from gamesage import GameSage
from game import GameNetGame, GameSageGame, GameIdea


app = Flask(__name__)


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


@app.route('/gamenet/findByTitle=<selected_game_title>')
def render_gamenet_entry_given_game_title(selected_game_title):
    if any(g for g in app.gamenet_database if g.title.lower() == selected_game_title.lower()):
        selected_game = next(g for g in app.gamenet_database if g.title.lower() == selected_game_title.lower())
        return render_template('game.html', game=selected_game)
    else:
        # The game title/arbitrary query that the user typed in does not match
        # any game in our database, so keep displaying the home page, but note this
        return render_template('gamenet_index.html', entered_unknown_game=True)


@app.route('/gamenet/games/<selected_game_id>')
def render_gamenet_entry_given_game_id(selected_game_id):
    """Render the GameNet entry for a user-selected game."""
    selected_game = app.database[int(selected_game_id)]
    return render_template('game.html', game=selected_game)


@app.route('/gamenet/game_idea', methods=['POST'])
def generate_gamenet_entry_for_game_idea_from_gamesage():
    """Generate and render a GameNet entry for a GameSage query."""
    idea_text = request.form['user_submitted_text']
    related_games_str = request.form['most_related_games_str']
    unrelated_games_str = request.form['least_related_games_str']
    game_idea = GameIdea(
        idea_text=idea_text, related_games_str=related_games_str, unrelated_games_str=unrelated_games_str
    )
    # Set the title and year of each entry in the game idea's un/related games listings
    for entry in game_idea.related_games+game_idea.unrelated_games:
        title = app.database[int(entry.game_id)].title
        year = app.database[int(entry.game_id)].year
        entry.set_game_title_and_year(title=title, year=year)
    return render_template('gameIdea.html', game_idea=game_idea)


@app.route('/gamesage')
def gamesage_home():
    """Render the GameSage homepage."""
    return render_template('gamesage_index.html')


@app.route('/gamesage/submittedText', methods=['POST'])
def generate_gamenet_query():
    """Generate a query for GameNet."""
    user_submitted_text = request.form['user_submitted_text']
    gamesage = GameSage(
        database=app.gamesage_database, term_id_dictionary=app.term_id_dictionary,
        tf_idf_model=app.tf_idf_model, lsa_model=app.lsa_model,
        user_submitted_text=user_submitted_text
    )
    return jsonify(
        user_submitted_text=user_submitted_text,
        most_related_games_str=gamesage.most_related_games_str,
        least_related_games_str=gamesage.least_related_games_str
    )


def load_gamenet_database():
    """Load the database of GameNet game representations from a TSV file."""
    database = []
    with open('static/games_metadata.tsv', 'r') as tsvfile:
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


def load_gamesage_database():
    """Load the database of GameSage game representations from a TSV file."""
    database = []
    with open('static/game_lsa_vectors.tsv', 'r') as tsv_file:
        reader = csv.reader(tsv_file, delimiter='\t')
        for row in reader:
            game_id, title, year, lsa_vector_str = row
            game_object = GameSageGame(game_id, title, lsa_vector_str)
            database.append(game_object)
    return database


def load_term_id_dictionary():
    """Load the term-ID dictionary for our corpus."""
    term_id_dictionary = gensim.corpora.Dictionary.load('./static/id2term.dict')
    return term_id_dictionary


def load_tf_idf_model():
    """Load our tf-idf model."""
    tf_idf_model = (
        gensim.models.TfidfModel.load('./static/wiki_games_tfidf_model')
    )
    return tf_idf_model


def load_lsa_model():
    """Load our LSA model."""
    lsa_model = gensim.models.LsiModel.load('./static/model_207.lsi')
    return lsa_model


if __name__ == '__main__':
    app.gamenet_database = load_gamenet_database()
    app.gamesage_database = load_gamesage_database()
    app.term_id_dictionary = load_term_id_dictionary()
    app.tf_idf_model = load_tf_idf_model()
    app.lsa_model = load_lsa_model()
    app.run(debug=False)
else:
    app.gamenet_database = load_gamenet_database()
    app.gamesage_database = load_gamesage_database()
    app.term_id_dictionary = load_term_id_dictionary()
    app.tf_idf_model = load_tf_idf_model()
    app.lsa_model = load_lsa_model()
if not app.debug:
    import logging
    file_handler = logging.FileHandler('gamenet.log')
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)
