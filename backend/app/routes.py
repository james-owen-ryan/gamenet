import csv
from flask import Flask, render_template, jsonify
from game import Game


app = Flask(__name__)

@app.route('/')
def home():
    """Render the GameNet homepage."""
    return render_template('index.html')

@app.route('/games/<selected_game_id>')
def open_page_for_selected_game(selected_game_id):
    """Render the GameNet entry for a user-selected game."""
    selected_game = app.database[int(selected_game_id)]
    return render_template('game.html', game=selected_game)

@app.route('/gamesageQuery=<gamesage_query>')
def generate_entry_for_gamesage_query(selected_game_id):
    """Generate and render a GameNet entry for a GameSage query."""

    return render_template('game.html', game=selected_game)

def load_database():
    """Load the database of game representations from a TSV file."""
    database = []
    with open('static/games_metadata.tsv', 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for row in reader:
            game_id, title, year, platform, wiki_url, wiki_summary, related_games_str, unrelated_games_str = row
            game_object = (
                Game(game_id, title, year, platform, wiki_url, wiki_summary, related_games_str, unrelated_games_str)
            )
            database.append(game_object)
    # Now that all the games have been read in, allow each game's un/related-games entries to be
    # attributed game titles and years via lookup into the database that is now fully populated
    for game in database:
        for entry in game.related_games:
            title = database[int(entry.game_id)].title
            year = database[int(entry.game_id)].year
            entry.set_game_title_and_year(title=title, year=year)
        for entry in game.unrelated_games:
            title = database[int(entry.game_id)].title
            year = database[int(entry.game_id)].year
            entry.set_game_title_and_year(title=title, year=year)
    return database

if __name__ == '__main__':
    app.database = load_database()
    app.run(debug=False)
else:
    app.database = load_database()

if not app.debug:
    import logging
    file_handler = logging.FileHandler('gamenet.log')
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)
