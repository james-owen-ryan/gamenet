import string
import csv
import gensim
from nltk import WordNetLemmatizer
from nltk import word_tokenize
from nltk import HunposTagger


class GameSage(object):
    """An anthropomorphization of the procedure in LSA called 'folding in'."""

    def __init__(self, network, database, term_id_dictionary, tf_idf_model, lsa_model, user_submitted_text):
        """Initialize a GameSage object."""
        self.network = network
        self.database = database
        self.term_id_dictionary = term_id_dictionary
        self.tf_idf_model = tf_idf_model
        self.lsa_model = lsa_model
        if self.network == 'ontology':
            preprocessed_text = self._preprocess_text_in_ontology_network_style(text=user_submitted_text)
        else:  # 'gameplay'
            preprocessed_text = self._preprocess_text_in_gameplay_network_style(text=user_submitted_text)
        lsa_vector_for_user_submitted_text = self._fold_in_user_submitted_text(text=preprocessed_text)
        self.most_related_games, self.least_related_games = self._get_most_related_games_to_user_submitted_text(
            lsa_vector_for_user_submitted_text=lsa_vector_for_user_submitted_text
        )
        self.most_related_games_str, self.least_related_games_str = (
            self._generate_related_games_strings()
        )

    def _generate_related_games_strings(self):
        """Generate strings representing the most and least related games, for GameNet to parse."""
        if self.network == 'gameplay':
            id_mapping = self._build_gameplay_database_indices_to_game_id_mapping()
            most_related_games_str = (
                ','.join('{}&{}'.format(id_mapping[entry[0]], entry[1]) for entry in self.most_related_games)
            )
            least_related_games_str = (
                ','.join('{}&{}'.format(id_mapping[entry[0]], entry[1]) for entry in self.least_related_games)
            )
        else:  # 'ontology'
            most_related_games_str = (
                ','.join('{}&{}'.format(entry[0], entry[1]) for entry in self.most_related_games)
            )
            least_related_games_str = (
                ','.join('{}&{}'.format(entry[0], entry[1]) for entry in self.least_related_games)
            )
        return most_related_games_str, least_related_games_str

    @staticmethod
    def _build_gameplay_database_indices_to_game_id_mapping():
        """Build a mapping from 'gameplay' database indices to game IDs."""
        gameplay_database_index_to_game_id = {}
        with open('static/games_metadata-gameplay.tsv', 'r') as tsvfile:
            metadata_entries = [line.split('\t') for line in tsvfile.readlines()]
            for i in xrange(len(metadata_entries)):
                game_id = metadata_entries[i][0]
                gameplay_database_index_to_game_id[i] = game_id
        return gameplay_database_index_to_game_id

    def _get_most_related_games_to_user_submitted_text(self, lsa_vector_for_user_submitted_text):
        """Get the 50 most related and unrelated games to the user-submitted text."""
        # Reindex the LSA space to account for the folding in (ignore first dimension of
        # the LSA vector for the user-submitted text)
        corpus_including_new_lsa_vector = (
            [game.lsa_vector for game in self.database] + [lsa_vector_for_user_submitted_text]
        )
        reindexed_lsa_space = gensim.similarities.docsim.Similarity(
            output_prefix="temp_gensim_lsa_file_that_can_be_deleted",
            corpus=corpus_including_new_lsa_vector,
            num_features=len(self.database[0].lsa_vector)+1, num_best=len(corpus_including_new_lsa_vector)
        )
        lsa_scores_for_all_games_relative_to_this_game = (
            reindexed_lsa_space[lsa_vector_for_user_submitted_text]
        )
        most_related_games = lsa_scores_for_all_games_relative_to_this_game[1:51]  # [0] will be the text itself
        least_related_games = lsa_scores_for_all_games_relative_to_this_game[-50:]
        least_related_games.reverse()  # Order these with least related game first
        return most_related_games, least_related_games

    def _fold_in_user_submitted_text(self, text):
        """Fold user-submitted text into our LSA model, i.e., derive an LSA vector for the text."""
        frequency_count_vector_for_user_submitted_text = (
            (self.term_id_dictionary.doc2bow(text.split()))
        )
        tf_idf_vector_for_user_submitted_text = (
            self.tf_idf_model[frequency_count_vector_for_user_submitted_text]
        )
        document_lsa_vector_for_user_submitted_text = (
            self.lsa_model[tf_idf_vector_for_user_submitted_text]
        )
        # Exclude first dimension, as we've already done with the existing LSA vectors
        lsa_vector_for_user_submitted_text = document_lsa_vector_for_user_submitted_text[1:]
        return lsa_vector_for_user_submitted_text

    def _preprocess_text_in_ontology_network_style(self, text):
        """Preprocess user-submitted text in the same way we preprocessed the Wikipedia corpus."""
        # Remove weird characters that could cause encoding issues
        text = filter(lambda char: char in string.printable, text)
        # Remove newline and tab characters
        for special_char in ('\n', '\r', '\t'):
            text = text.replace(special_char, ' ')
        # Remove preliminary set of punctuation symbols
        for punctuation_symbol in ('_', '.', ',', ';'):
            text = text.replace(punctuation_symbol, ' ')
        text = text.lower()
        # Remove redundant whitespace
        text = ' '.join(text.split())
        # Tokenize multiword game titles
        text = self._tokenize_multiword_titles(text=text)
        # Tokenize multiword platform names
        text = self._tokenize_multiword_platform_names(text=text)
        # Remove punctuation and symbols (except underscores)
        text = self._remove_punctuation_and_symbols(text=text)
        # Again remove redundant whitespace
        text = ' '.join(text.split())
        # Remove stopwords
        text = self._remove_stopwords_ontology(text=text)
        # Lemmatize words
        text = self._lemmatize_words(text=text)
        # Remove stopwords again (some may have been reintroduced
        # by lemmatization)
        text = self._remove_stopwords_ontology(text=text)
        return text

    def _tokenize_multiword_titles(self, text):
        """Tokenize occurrences of multiword titles."""
        titles = [game.title.lower() for game in self.database if game.title]
        multiword_titles = [title for title in titles if len(title.split()) > 1]
        tokenized_multiword_titles = {}
        for multiword_title in multiword_titles:
            tokenized_multiword_titles[multiword_title] = '_'.join(multiword_title.split())
        multiword_titles.sort(key=lambda t: len(t.split()), reverse=True)
        titles_sorted_by_number_of_words = multiword_titles
        text = ' {} '.format(text)
        for title in titles_sorted_by_number_of_words:
            tokenized_title = tokenized_multiword_titles[title]
            try:
                while ' {} '.format(title) in text:
                    text = text.replace(
                        ' {} '.format(title), ' {} '.format(tokenized_title)
                    )
            except UnicodeEncodeError:
                pass  # Not worth struggling with game titles with weird encodings
        text = ' '.join(text.split())
        return text

    @staticmethod
    def _tokenize_multiword_platform_names(text):
        """Tokenize occurrences of multiword platform names."""
        f = open('./static/multiword_platform_names.txt', 'r')
        multiword_platform_names = f.readlines()
        multiword_platform_names = [name.strip('\n') for name in multiword_platform_names]
        multiword_platform_names = [name.lower() for name in multiword_platform_names]
        tokenized_multiword_names = {}
        for multiword_name in multiword_platform_names:
            tokenized_multiword_names[multiword_name] = '_'.join(multiword_name.split())
        multiword_platform_names.sort(key=lambda t: len(t.split()), reverse=True)
        platform_names_sorted_by_number_of_words = multiword_platform_names
        text = ' {} '.format(text)
        for platform_name in platform_names_sorted_by_number_of_words:
            tokenized_title = tokenized_multiword_names[platform_name]
            while ' {} '.format(platform_name) in text:
                text = text.replace(
                    ' {} '.format(platform_name), ' {} '.format(tokenized_title)
                )
        return text

    @staticmethod
    def _remove_punctuation_and_symbols(text):
        """Remove punctuation and other symbols."""
        for symbol in (
            '[', ']', '\'', '&', '(', ')', '\\', '/', '*', '!',
            '?', '$', '^', '~', '+', '=', '{', '}', '`', '|', '#'
        ):
            text = text.replace(symbol, ' ')
        for symbol in ('"', ':'):
            text = text.replace(symbol, '')
        return text

    @staticmethod
    def _remove_stopwords_ontology(text):
        """Remove all stopwords from the text."""
        f = open('./static/stopwords.txt', 'r')
        stopwords = f.readlines()
        stopwords = [stopword.strip('\n') for stopword in stopwords]
        tokens = [token.lower() for token in text.split()]
        for i in xrange(len(tokens)):
            if tokens[i] in stopwords:
                tokens[i] = ''
            elif len(tokens[i]) == 1:  # Remove single letters
                tokens[i] = ''
        text = ' '.join([token for token in tokens if token])
        return text

    @staticmethod
    def _lemmatize_words(text):
        """Lemmatize all words in the text."""
        lemmatizer = WordNetLemmatizer()
        lemmatizations = {}
        tokens = text.split()
        for word in tokens:
            if word not in lemmatizations:
                lemmatizations[word] = lemmatizer.lemmatize(word)
        for i in xrange(5):  # Need to repeat several times to be safe
            tokens = text.split()
            for j in xrange(len(tokens)):
                try:
                    tokens[j] = lemmatizations[tokens[j]]
                except KeyError:
                    # During last pass, words were turned into their lemmas, which don't
                    # have entries in lemmatizations
                    pass
        text = ' '.join(tokens)
        return text

    def _preprocess_text_in_gameplay_network_style(self, text):
        """Preprocess user-submitted text in the same way we preprocessed the GameFAQs corpus."""
        # Remove weird characters that could cause encoding issues
        text = filter(lambda char: char in string.printable, text)
        # Remove newline and tab characters
        for special_char in ('\n', '\r', '\t'):
            text = text.replace(special_char, '. ')
        # Remove most punctuation and symbols
        text = self._remove_punctuation_and_symbols(text=text)
        # POS-tag the text
        pos_tagged_text = self._pos_tag_text(text=text)
        # Remove all tokens that aren't POS-tagged as a verb or common noun
        pos_tagged_text = self._remove_everything_but_verbs_and_common_nouns(pos_tagged_text)
        # Convert text to lowercase
        for i in xrange(len(pos_tagged_text)):
            pos_tagged_text[i][0] == pos_tagged_text[i][0].lower()
        # Remove numbers and non-Latin characters
        pos_tagged_text = self._remove_any_numbers_and_non_english_characters_from_text(
            pos_tagged_text=pos_tagged_text
        )
        # Lemmatize, and remove stopwords
        pos_tagged_text = self._lemmatize_and_remove_stopwords(
            pos_tagged_text=pos_tagged_text
        )
        # Throw away the POS tags
        text = [tag[0] for tag in pos_tagged_text]
        text = ' '.join(text)
        # Remove redundant whitespace
        text = ' '.join(text.split())
        return text

    @staticmethod
    def _pos_tag_text(text):
        tokens = word_tokenize(text)
        # Prepare the POS tagger
        pos_tagger = HunposTagger('./static/en_wsj.model', './static/hunpos-tag')
        # POS-tag the text
        pos_tagged_text = pos_tagger.tag(tokens)
        # Convert each word-tag tuple to a list, to support item assignment, which
        # we need during lemmatization and stopword removal
        pos_tagged_text = [list(t) for t in pos_tagged_text]
        return pos_tagged_text

    @staticmethod
    def _remove_everything_but_verbs_and_common_nouns(pos_tagged_text):
        """Remove everything but verbs and common nouns from the POS-tagged text."""
        pos_tagged_text = [
            word_and_tag_pair for word_and_tag_pair in pos_tagged_text if word_and_tag_pair[0] != '' and
            word_and_tag_pair[1] in ('VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'NN', 'NNS')
        ]
        return pos_tagged_text

    @staticmethod
    def _remove_any_numbers_and_non_english_characters_from_text(pos_tagged_text):
        """Remove any digits from the POS-tagged text."""
        for i in xrange(len(pos_tagged_text)):
            word = pos_tagged_text[i][0]
            # Remove numbers
            for digit in string.digits:
                word = word.replace(digit, '')
            # Remove words with non-Latin characters
            try:
                word.decode('ascii')
            except UnicodeDecodeError:
                word = ''
            # Write the preprocessed word back
            pos_tagged_text[i][0] = word
        return pos_tagged_text

    @staticmethod
    def _remove_all_other_punctuation(pos_tagged_text):
        """Remove all remaining punctuation from POS-tagged text."""
        for j in xrange(len(pos_tagged_text)):
            word = pos_tagged_text[j][0]
            for symbol in (',', '.', ';', '-'):
                word = word.replace(symbol, ' ')
            # Write the preprocessed word back
            pos_tagged_text[j][0] = word
        return pos_tagged_text

    @staticmethod
    def _lemmatize_and_remove_stopwords(pos_tagged_text):
        """Lemmatize the pos_tagged_text and remove any stopwords."""
        # Prepare lemmatizer
        lemmatizer = WordNetLemmatizer()
        lemmatizations_already_computed = {}
        penn_to_wordnet_pos_tags = {
            'NN': 'n', 'NNS': 'n', 'VB': 'v', 'VBD': 'v', 'VBG': 'v',  'VBN': 'v', 'VBP': 'v',
            'VBZ': 'v', 'JJ': 'a', 'JJR': 'a', 'JJS': 'a', 'RB': 'r', 'RBR': 'r', 'RBS': 'r',
        }
        # Build stopwords list
        f = open('./static/stopwords.txt', 'r')
        stopwords = f.readlines()
        stopwords = [stopword.strip('\n') for stopword in stopwords]
        contractions_missed_because_of_punctuation_removal = [
            'arent', 'cant', 'couldnt', 'didnt', 'doesnt', 'dont', 'hadnt', 'hasnt', 'havent',
            'hed', 'hell', 'hes', 'id', 'ill', 'im', 'ive', 'isnt', 'its', 'lets', 'mightnt', 'mustnt',
            'shant', 'shed', 'shell', 'shes', 'shouldnt', 'thats', 'theres', 'theyd', 'theyll', 'theyre',
            'theyve', 'wed', 'were', 'weve', 'werent', 'whatll', 'whatre', 'whats', 'whatve', 'wheres',
            'whod', 'wholl', 'whore', 'whos', 'whove', 'wont', 'wouldnt',  'youd', 'youll', 'youre', 'youve'
        ]
        stopwords += contractions_missed_because_of_punctuation_removal
        # Run the lemmatization procedure multiple times to be safe (problem
        # when, e.g., 'apples apples' shows up)
        for i in xrange(5):
            for j in xrange(len(pos_tagged_text)):
                word, pos_tag = pos_tagged_text[j]
                if word != '':
                    # Lemmatize word
                    if word in lemmatizations_already_computed:
                        pos_tagged_text[j][0] = lemmatizations_already_computed[word]
                    else:
                        lemmatizations_already_computed[word] = lemmatizer.lemmatize(
                            word=word, pos=penn_to_wordnet_pos_tags[pos_tag]
                        )
                        pos_tagged_text[j][0] = lemmatizations_already_computed[word]
                    # If it's a stopword (or unicharacter symbol), remove it
                    if pos_tagged_text[j][0] in stopwords or len(pos_tagged_text[j][0]) == 1:
                        pos_tagged_text[j][0] = ''
        return pos_tagged_text
