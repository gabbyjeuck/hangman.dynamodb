#Name: Gabrielle Jeuck
#Date: May 6, 2020
#Course: SDEV 400 - Secure Programming in the Cloud
"""Purpose: Homework 4 - Create a custom program using Cloud 9.  Utilizes s3 
            buckets and DynamoDB to house leaderboards.  This particular hangmna
            program allows users to get bonus points based on guessing the full 
            word and regular points based on game modes."""    

# IMPORTS
import boto3
from boto3.dynamodb.conditions import Key, Attr
import random, re, decimal, json

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)
        
# CLIENTS / TABLE / BUCKET
db_client = boto3.resource('dynamodb')
table = db_client.Table('Hangman-2')
s3_client = boto3.client('s3')
bucketname = 'gjeuck-hangman'
# holds total scores for current game session
score_streak = 0

# READS TEXT FILES FROM S3 AND RETURNS TO AN ARRAY FOR WORDS LISTS
def read_objects(client, bucket, file):
    fileObj = client.get_object(Bucket=bucket, Key=file)
    fileData = fileObj['Body'].read()
    contents = fileData.decode('utf-8')
    contents_array = []
    contents_array = contents.split()
    return contents_array

# READS FILES FOR INSTRUCTIONS/CREDITS
def read_objects_instructions(client, bucket, file):
    fileObj = client.get_object(Bucket=bucket, Key=file)
    fileData = fileObj['Body'].read()
    contents = fileData.decode('utf-8')
    print(contents)

# UPDATES USERS SCORES WHILE PLAYING
def update_score(table, client, user, score):
    response = table.update_item(
        Key={
            'PlayerName': user
        },
        UpdateExpression='SET Score = :score, GameTitle = :title', 
        ExpressionAttributeValues={
            ':score': score,
            ':title': 'Hangman'
        }
        )

# GETS USERS CURRENT SCORES AT BEGINNING OF GAME
def get_db_item(table, client, user):
    try:
        response = table.get_item(
            Key={
                'PlayerName': user
            }   
        )
        # takes item from dictionary for display 
        items = response['Item']
        username = items.get('PlayerName')
        score = items.get('Score')
        print("{} has a top score of {}!".format(username, score))
        return score
    except KeyError:
        return None

# DISPLAYS LEADERBOARDS FROM DYNAMODB
def leaderboards(client, table):
    data = {}
    players = []
    scores = []
    response = table.query(
        IndexName = 'GameTitle-Score-index',
        KeyConditionExpression=Key('GameTitle').eq('Hangman'),
        Limit = 10,
        ScanIndexForward = False
        )
        
    print("---- TOP 10 LEADERBOARDS ----")
    # TAKES ITEMS FROM DYNAMODB
    items = response['Items']
    # APPENDS ITEMS TO LISTS
    for i, item in enumerate(items):
        players.append(item.get('PlayerName'))
        scores.append(item.get('Score'))

    print("{:<4}{:>10}{:>14}".format("Rank", "Player", "Score"))
    # TAKES ITEMS FROM LIST AND APPLIES THEM TO CUSTOM DICTIONARY
    for i, key in enumerate(players):
        for value in scores:
            data[key] = value
            scores.remove(value)
            break
        print("{:2d}".format(i+1),"\t{:15s}{:1f}".format(key, value))        
        
# GENERATES RANDOM WORD FROM DESIGNATED LIST
def word_generator(words):
    random_word = random.choice(words)
    return random_word.upper()
    
# EASY
def easy_words():
    print("---------------------")
    print("------Easy Mode------")
    print("---------------------")
    file = 'easy_words.txt'
    words = read_objects(s3_client, bucketname, file)
    random_word = word_generator(words)
    return random_word
    
# HARD
def hard_words():
    print("---------------------")
    print("------Hard Mode------")
    print("---------------------")
    file = 'hard_words.txt'
    words = read_objects(s3_client, bucketname, file)
    random_word = word_generator(words)
    return random_word

# DRAWS HANGMAN CHARACTER BASED ON TURNS / MISSED GUESSES
def show_hangman(turns):
    stages = ["""
                    -------
                    |     |
                    |    X_X
                    |    \\|/
                    |     |
                    |     |
                    |    / \\
                    |
                    -------
                """,
              """ 
                    -------
                    |     |
                    |     O
                    |    \\|/
                    |     |
                    |      \\
                    -------
                """,
              """
                    -------
                    |     |
                    |     O
                    |    \\|/
                    |     |
                    |     
                    -------
                """,
              """
                    -------
                    |     |
                    |     O
                    |     |/
                    |     |
                    |     
                    -------
                """,
              """
                    -------
                    |     |
                    |     O
                    |     |
                    |     |
                    |     
                    -------
                """,
              """
                    -------
                    |     |
                    |     O
                    |
                    |
                    |     
                    -------
                """,
              """
                    -------
                    |     |
                    |
                    |
                    |
                    |     
                    -------
                """
              ]
    return stages[turns]

# RUNS HANGMAN GAME
def hangman(word, mode, user, current_score):
    game_mode = mode
    guessed = False
    points = 0
    global score_streak
    guessed_words = []
    guessed_letters = []
    turns = 6
    secret_word = "_" * len(word)
    regex = "[a-zA-Z]"
    bonus = False

    print("Let's play Hangman!")
    print(show_hangman(turns))
    print(secret_word)
    print("The word is", len(word), "characters")
    print("\n")
    
    # CONTINUES UNTIL USER RUNS OUT OF GUESSES
    while not guessed and turns > 0:

        user_guess = input("Guess a letter or word: ").upper()

        # SINGLE LETTER GUESS AND A-Z
        if len(user_guess) == 1 and user_guess.isalpha():
            # if the users input is already used, let user know
            if user_guess in guessed_letters:
                print("You have already guessed the letter ", user_guess)
            # elif users guess is not in word add to list and take turn away
            elif user_guess not in word:
                print(user_guess, "is not in the word.")
                turns -= 1
                print("Remaining tries:", turns)
                guessed_letters.append(user_guess)
                
            # letter is guessed by user checks to see if all characters found
            else:
                print("\nYay! You guessed the letter ", user_guess, ".")
                guessed_letters.append(user_guess)
                word_list = list(secret_word)
                for i, letter in enumerate(word):
                    if letter == user_guess:
                        word_list[i] = user_guess
                    secret_word = "".join(word_list)
                if "_" not in secret_word:
                    guessed = True
            
        # if user guesses full word and uses A-Z
        elif len(user_guess) == len(word) and user_guess.isalpha():
            # checks if user already guessed that specific word
            if user_guess in guessed_words:
                print("You already guessed the word ", user_guess, ".")
            # if its not the word, adds to list and takes turn
            elif user_guess != word:
                print(user_guess, " is not the word!")
                turns -= 1
                guessed_words.append(user_guess)
            # otherwise word is guessed
            else:
                guessed = True
                bonus = True
                secret_word = word
                print("Congrats! You guessed the word, ",secret_word, "!")
        # IF USER INPUT IS NOT LETTERS A-Z or a-z       
        elif user_guess not in regex:
            print("Invalid character.  Please use letters only.")
            
        else:
            print("Not a valid guess")
        # DISPLAYS EACH TURN 
        print(show_hangman(turns))
        print(secret_word)
        print("The word is", len(word), "characters")
        print("Guessed Letters:", str(guessed_letters))
        print("Guessed Words:", str(guessed_words))
        
        # WHEN GUESSED CALCULATES SCORES BASED ON GAME MODES
        if guessed:
            print("Yay! You did it! The man is FREE!")

            if game_mode is 'easy':
                bonus_points = 10
                points = 5
                if bonus == True:
                    points += bonus_points
            elif game_mode is 'hard':
                bonus_points = 20
                points = 15
                if bonus == True:
                    points += bonus_points
            
            #COMBINES ALL POINTS TO CURRENT STREAK
            score_streak += points
            # IF USER GUESSES FULL WORD, BONUS POINTS ARE GIVEN
            if bonus == False:
                print("You earned", points,"points")
            else: 
                if game_mode is 'easy':
                    print("You earned", bonus_points,"bonus points for guessing full word. Total points:", points)
                if game_mode is 'hard':
                    print("You earned", bonus_points,"bonus points for guessing full word. Total points:", points)
                    
            print("Your current win streak is",score_streak,"points!")
            
            # IF SCORE_STREAK IS >= CURRENT SCORE from beginning of DB
            if current_score >= score_streak:
                print("Previous score was higher, did not save current score!")
            else:
                print("Updated your score from",current_score,"to",score_streak)
                update_score(table, db_client, user, score_streak)
        # USER FAILED TO GUESS WORD        
        if turns == 0:
            print("You ran out of turns. The word was:", word)

# VALIDATES PLAYERS CHRACTER LENGTH
def get_player_name():
    while True:
        user = input("Please tell me your name: ").capitalize()
        if (len(user) >= 1) and (len(user) <= 14):
            break
        else:
            print("Your name must be between 1 and 14 characters long.")
    return user
    
# USER INPUT FOR MENU SELECTIONS 1-6
def user_input():
    while True:
        try:
            user_choice = int(input("Enter your choice: "))
            if (user_choice >= 1) and (user_choice <= 6):
                break
            else:
                print("Please select from the number choices 1-6!")
        except ValueError:
            print("Please select from the number choices 1-6!")
    return user_choice

# MAIN MENU
def main_menu(user, current_score):
    print("\nWelcome to Hangman",user +"!")
    print("1. Easy Play")
    print("2. Hard Play")
    print("3. Leaderboards")
    print("4. Instructions")
    print("5. Credits")
    print("6. Quit")
    user_choice = user_input()
    if user_choice == 1:
        word = easy_words()
        mode = 'easy'
        hangman(word, mode, user, current_score)
    elif user_choice == 2:
        mode = 'hard'
        word = hard_words()
        hangman(word, mode, user, current_score)
    elif user_choice == 3:
        leaderboards(db_client, table)
    elif user_choice == 4:
        file = 'UserGuide.txt'
        read_objects_instructions(s3_client, bucketname, file)
    elif user_choice == 5:
        file = 'Credits.txt'
        read_objects_instructions(s3_client, bucketname, file)
    elif user_choice == 6:
        print("Thank you for playing",user,"!")
        exit()

# main
def main():

    print("---------------------")
    print("-------HANGMAN-------")
    print("---------------------")
    # Gets users name for scoreboard/points
    user = get_player_name()
    
    # Checks database for user if username is in board returns score
    # else takes current_score and sets to 0.
    current_score = get_db_item(table, db_client, user)
    if current_score is not None:
        print("")
    else:
        print("No scores have been added for you,",user,"\nTry winning some to get on the leaderboards!")
        current_score = 0

    # launches main_menu 
    main_menu(user, current_score)
    
    # Once game is complete offers to play again, if user chooses Y it continues, else quits
    while input("Do you want to play again? Y/N: ").upper() == "Y":
        main_menu(user, current_score)
    else:
        print("You didn't choose to play again.\nThank you for playing")
        quit()

# call main
if __name__== "__main__":
    main()
