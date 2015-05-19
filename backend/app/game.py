class GameNetGame(object):
    """A game representation for GameNet's purposes."""

    def __init__(self, game_id, title, year, platform, wiki_url, wiki_summary,
                 related_games_str, unrelated_games_str):
        """Initialize a Game object."""
        self.id = game_id
        self.title = title.decode('utf-8')
        self.year = year
        self.platform = platform.decode('utf-8')
        self.wiki_url = wiki_url
        self.wiki_summary = wiki_summary.decode('utf-8')
        # Replace newline characters with linebreaks -- otherwise they get
        # rendered as empty strings
        self.wiki_summary = self.wiki_summary.replace('\n', '<br>')
        self.related_games = self.parse_related_games_str(related_games_str)
        self.unrelated_games = self.parse_related_games_str(unrelated_games_str)
        self.multiline_title = self.generate_multiline_title(self.title)
        self.google_images_query = self.generate_google_images_query(self.title, platform)
        self.youtube_query = self.generate_youtube_query(self.title, platform)

    @staticmethod
    def parse_related_games_str(related_games_str):
        """Parse a formatted string representation of a game's un/related games."""
        game_entries = []
        entry_strings = related_games_str.split(',')
        for entry in entry_strings:
            game_id, score = entry.split('&')
            game_entries.append(RelatedGamesEntry(game_id=game_id, score=score))
        return game_entries

    @staticmethod
    def generate_multiline_title(title):
        """Generate a multiline title for long titles that have a subtitle."""
        if len(title) > 33 and ':' in title:
            split_up_title = title.split(':')
            subtitle = ':'.join(subsubtitle for subsubtitle in split_up_title[1:])
            if subtitle[0] == ' ':
                subtitle = subtitle[1:]
                title = split_up_title[0]
            multiline_title = ':<br>'.join((title, subtitle))
            return multiline_title
        else:
            return title

    @staticmethod
    def generate_google_images_query(title, platform):
        """Generate a Google Images query for a search related to this game."""
        # Build up the query, which will be composed partly of weird
        # Google URL foo
        prefix = "https://www.google.com/search?site=&tbm=isch&source=hp&biw=1438&bih=722&q="
        infix = "&oq="
        suffix = (
            "&gs_l=img.3..0i24.2683.14223.0.14537.23.20.0.3.3.0.217.2149.10j9j1.20.0.msedr"
            "...0...1ac.1.64.img..0.23.2149.Uj4VDYLpDFU"
        )
        # Remove ampersands from the title, as these screw up the Google query
        title = title.replace('&', ' ')
        query = '+'.join(title.split())
        if platform:
            # I've informally observed that better results come from using 'nes'
            # rather than Famicom (or variants thereof), even in the case of
            # a Famicom exclusive like Mother
            if platform in ('family computer', 'famicom', 'family computer disk system'):
                platform = "nes"
            query += "+{}".format('+'.join(platform.split()))
        query += '+gameplay'
        full_query = prefix + query + infix + query + suffix
        return full_query

    @staticmethod
    def generate_youtube_query(title, platform):
        """Generate a YouTube query for a Let's Play video for this game."""
        query = "https://www.youtube.com/results?search_query=let's+play+"
        query += '+'.join(title.split())
        if platform:
            query += "+{}".format('+'.join(platform.split()))
        return query


class GameIdea(object):
    """A representation of a GameIdea received as a GameSage query."""

    def __init__(self, idea_text, related_games_str, unrelated_games_str):
        """Initialize a GameIdea object."""
        self.idea_text = idea_text
        related_games_str = related_games_str
        unrelated_games_str = unrelated_games_str
        self.related_games = self.parse_related_games_str(related_games_str)
        self.unrelated_games = self.parse_related_games_str(unrelated_games_str)

    @staticmethod
    def parse_related_games_str(related_games_str):
        """Parse a formatted string representation of a game idea's un/related games."""
        game_entries = []
        entry_strings = related_games_str.split(',')
        for entry in entry_strings:
            game_id, score = entry.split('&')
            game_entries.append(RelatedGamesEntry(game_id=game_id, score=score))
        return game_entries


class RelatedGamesEntry(object):
    """An entry in a game's list of un/related games."""

    def __init__(self, game_id, score):
        """Initialize a RelatedGamesEntry object."""
        self.game_id = game_id
        self.score = float(score)
        self.background_color = self.get_background_color(self.score)
        # These get set when load_database() in routes.py calls
        # set_game_title_and_year()
        self.game_title = None
        self.game_year = None

    def set_game_title_and_year(self, title, year):
        """Set the title and year of the un/related game."""
        self.game_title = title
        self.game_year = year

    @staticmethod
    def get_background_color(score):
        """Set the background color for this entry depending on its score."""
        # Related-game background colors
        if score > 0.95:
            background_color = "#E64C00"
        elif score > 0.9:
            background_color = "#FF6D00"
        elif score > 0.8:
            background_color = "#FF7900"
        elif score > 0.7:
            background_color = "#FF8500"
        elif score > 0.6:
            background_color = "#FF9100"
        elif score > 0.5:
            background_color = "#FF9D00"
        elif score > 0.4:
            background_color = "#FFA900"
        elif score > 0.3:
            background_color = "#FFB500"
        elif score > 0.2:
            background_color = "#FFC100"
        elif score > 0.1:
            background_color = "#FFCD00"
        elif score >= 0.05:
            background_color = "#FDE171"
        # Unrelated-game background colors
        elif score < -0.3:
            background_color = "#004CE6"
        elif score < -0.265:
            background_color = "#3389F9"
        elif score < -0.23:
            background_color = "#33A1F9"
        elif score < -0.195:
            background_color = "#33ADF9"
        elif score < -0.16:
            background_color = "#33B9F9"
        elif score < -0.125:
            background_color = "#33C5F9"
        elif score < -0.09:
            background_color = "#33D1F9"
        elif score < -0.055:
            background_color = "#33DDF9"
        elif score < -0.02:
            background_color = "#33E9F9"
        elif score < 0.015:
            background_color = "#33F5F9"
        else:
            background_color = "#3300F9"
        return background_color


class GameSageGame(object):
    """A game representation for the purposes of GameSage."""

    def __init__(self, game_id, title, lsa_vector_str):
        """Initialize a Game object."""
        self.id = game_id
        self.title = title.decode('utf-8')
        self.lsa_vector = self.parse_lsa_vector_str(lsa_vector_str)
        self.gamenet_link = self.get_link_to_gamenet_entry(game_id, title)

    @staticmethod
    def parse_lsa_vector_str(lsa_vector_str):
        """Parse a string specifying an LSA vector to return a list representation of it."""
        lsa_vector = [float(i) for i in lsa_vector_str.split(',')[1:]]  # Exclude first dimension
        # Add in the dimension indices -- these are needed for folding in
        lsa_vector_with_indices = []
        for i in xrange(len(lsa_vector)):
            index_of_this_dimension = i+1
            value_along_this_dimension = lsa_vector[i]
            lsa_vector_with_indices.append((index_of_this_dimension, value_along_this_dimension))
        return lsa_vector_with_indices

    @staticmethod
    def get_link_to_gamenet_entry(game_id, title):
        """Return a link to this game's Gamenet entry."""
        url = "/gamenet/games/"
        url += game_id
        link = "<a href={} target=_blank>".format(url) + title + "</a>"
        return link