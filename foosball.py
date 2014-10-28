import sqlite3
import os
from datetime import datetime
from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash, jsonify

# create our application
app = Flask(__name__)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'test.db'),
    DEBUG=True,
    SECRET_KEY='Secret Key Here',
    USSERNAME='Danny',
    PASSWORD='ChangeForProduction'
))

def connect_db():
    """Connects to the specified database"""
    rv = sqlite3.connect(app.config["DATABASE"])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def set_dates(m):
    keys = m.keys()
    if 'start_time' in keys:
        m['start_time'] = datetime.fromtimestamp(float(m['start_time']))

    return m

@app.route('/')
def home():
    # Get recent games
    db = get_db()
    cur = db.execute('''select game_id, 
                               strftime('%m-%d-%Y %H:%M:%S', datetime(games.start_time, 'localtime')) start_time, 
                               (select count(*)
                                from players, scores, teams 
                                where players.player_id = scores.player_id 
                                  and players.team_id = teams.team_id 
                                  and players.game_id = games.game_id
                                  and lower(teams.name) = 'red') red_score,
                                (select count(*)
                                from players, scores, teams 
                                where players.player_id = scores.player_id 
                                  and players.team_id = teams.team_id 
                                  and players.game_id = games.game_id
                                  and lower(teams.name) = 'blue') blue_score
                        from games
                        order by games.start_time desc
                        limit 10''')
    games = cur.fetchall()

    # Get scores by position 
    cur = db.execute('''
        select 
            (select count(*) 
            from scores, players
            where scores.player_id = players.player_id 
              and players.position = 1) goalie_points,
            (select count(*) 
            from scores, players
            where scores.player_id = players.player_id 
              and players.position = 2) defender_points,
            (select count(*) 
            from scores, players
            where scores.player_id = players.player_id 
              and players.position = 3) center_points,
            (select count(*) 
            from scores, players
            where scores.player_id = players.player_id 
              and players.position = 4) striker_points''')
    points_by_position = cur.fetchone()

    # Get players by PPG 
    cur = db.execute('''
        select a.*,
               substr((cast(a.total_score as FLOAT)/a.total_games), 1, 5) ppg
        from (
            select users.user_id,
                   users.username,
                   (select count(*)
                    from scores, players 
                    where players.user_id = users.user_id 
                      and players.player_id = scores.player_id) total_score,
                   (select count(distinct games.game_id)
                    from players, games
                    where players.game_id = games.game_id 
                      and players.user_id = users.user_id) total_games
            from users) a
        order by ppg desc, a.total_score desc''')
    players_by_ppg = cur.fetchall()

    # Get sum of Red and Blue Wins
    cur = db.execute('''
        select 
            (select count(*)
            from games
            where games.end_time is not null 
              and (
                select count(*)
                from scores, players, teams 
                where scores.player_id = players.player_id
                  and players.game_id = games.game_id 
                  and players.team_id = teams.team_id 
                  and lower(teams.name) = 'red') >
              (
                select count(*)
                from scores, players, teams 
                where scores.player_id = players.player_id
                  and players.game_id = games.game_id 
                  and players.team_id = teams.team_id 
                  and lower(teams.name) = 'blue')) red_wins,
            (select count(*)
            from games
            where games.end_time is not null 
              and (
                select count(*)
                from scores, players, teams 
                where scores.player_id = players.player_id
                  and players.game_id = games.game_id 
                  and players.team_id = teams.team_id 
                  and lower(teams.name) = 'red') <
              (
                select count(*)
                from scores, players, teams 
                where scores.player_id = players.player_id
                  and players.game_id = games.game_id 
                  and players.team_id = teams.team_id 
                  and lower(teams.name) = 'blue')) blue_wins''')
    red_blue_scores = cur.fetchone()


    # Get top players by points -- Leading Scorers
    cur = db.execute('''select *, 
                               (select count(*) 
                                from scores, players 
                                where scores.player_id = players.player_id 
                                  and users.user_id = players.user_id) total_score 
                        from users
                        order by total_score desc
                        limit 10''');
    leading_scorers = cur.fetchall()

    # Get top player for each position by point - Leader Scorers by Position
    
    return render_template('home.html', games=games, leading_scorers=leading_scorers,
        players_by_ppg=players_by_ppg, red_blue_scores=red_blue_scores, 
        points_by_position=points_by_position)

@app.route('/users')
def display_users():
    db = get_db()
    cur = db.execute('''
        select users.*,
               (select count(*)
                from players, scores 
                where players.user_id = users.user_id 
                  and players.player_id = scores.player_id) scores,
                (select count(distinct games.game_id)
                    from players, games
                    where players.game_id = games.game_id 
                      and players.user_id = users.user_id) total_games
        from users 
        order by lower(users.username)''')
    users = cur.fetchall()
    return render_template('users.html', users=users)

@app.route('/users/json')
def users_json():
    db = get_db()
    cur = db.execute('select * from users order by user_id')
    users = cur.fetchall()
    users_output = []
    for user in users:
        users_output.append({"user_id": user["user_id"], "username": user["username"], 
                             "first_name": user["first_name"], "last_name": user["last_name"], 
                             "age": user["age"], "location": user["location"]})
    return jsonify(users=users_output) 

@app.route('/users/create', methods=['GET'])
def create_user():
    return render_template('create_user.html')

def create_user(username, first_name, last_name, age, location):
    db = get_db()
    cur = db.execute('''insert into users (username, first_name, last_name, age, location)
                     values (?, ?, ?, ?, ?)''', (username, first_name, last_name, age, location))
    db.commit()

@app.route('/users/create', methods=['POST'])
def add_user():
    create_user(request.form['username'], request.form['first_name'], request.form['last_name'], 
                request.form['age'], request.form['location'])
    return redirect(url_for('create_user'))

@app.route('/users/<int:user_id>', methods=['GET'])
def user_details(user_id):
    # Get user record 
    db = get_db()
    cur = db.execute('''
        select users.*,
               (select count(*)
                from players, scores 
                where players.user_id = users.user_id 
                  and players.player_id = scores.player_id) total_points,
                (select count(distinct games.game_id)
                    from players, games
                    where players.game_id = games.game_id 
                      and players.user_id = users.user_id) total_games
        from users 
        where user_id = ?''', (user_id,))
    user_info = cur.fetchone()

    # Get recent games
    cur = db.execute('''
        select games.game_id,
               strftime('%m-%d-%Y %H:%M:%S', datetime(games.start_time, 'localtime')) start_time, 
               (select teams.name 
                from teams
                where teams.team_id = (
                    select distinct players.team_id 
                    from players, users
                    where users.user_id = ? 
                      and players.game_id = games.game_id
                      and players.user_id = users.user_id)) team_name,
               (select count(*)
                from scores, users, players 
                where players.user_id = users.user_id 
                  and scores.player_id = players.player_id 
                  and users.user_id = ?
                  and players.game_id = games.game_id) score 
        from games
        where games.game_id in (
            select players.game_id 
            from users, players 
            where users.user_id = ? 
              and players.user_id = users.user_id )
        order by games.start_time desc
        limit 10''', (user_id, user_id, user_id,))
    recent_games = cur.fetchall()

    # Get most popular positions played

    # Get scores for each position
    cur = db.execute('''
        select
            (select count(*)
            from players, scores 
            where players.user_id = users.user_id 
              and players.player_id = scores.player_id
              and players.position = 1) goalie_points,
            (select count(*)
            from players, scores 
            where players.user_id = users.user_id 
              and players.player_id = scores.player_id
              and players.position = 2) defender_points,
            (select count(*)
            from players, scores 
            where players.user_id = users.user_id 
              and players.player_id = scores.player_id
              and players.position = 3) center_points,
            (select count(*)
            from players, scores 
            where players.user_id = users.user_id 
              and players.player_id = scores.player_id
              and players.position = 4) striker_points
        from users
        where users.user_id = ?''', (user_id,))
    points_by_position = cur.fetchone()

    # Get points scored for last 30 games
    cur = db.execute('''
        select games.game_id, count(*) points
        from games, users, players, scores
        where players.user_id = users.user_id 
          and users.user_id = ?
          and games.game_id = players.game_id
          and scores.player_id = players.player_id
         group by games.game_id
         limit 20''', (user_id,))
    game_scores = cur.fetchall()

    return render_template('edit_user.html', user_info=user_info, recent_games=recent_games,
        points_by_position=points_by_position, game_scores=game_scores)

@app.route('/games')
def display_games():
    db = get_db()
    curr = db.execute('''
        select game_id, 
           strftime('%m-%d-%Y %H:%M:%S', datetime(games.start_time, 'localtime')) start_time, 
           games.end_time,
           (select count(*)
            from players, scores, teams 
            where players.player_id = scores.player_id 
              and players.team_id = teams.team_id 
              and players.game_id = games.game_id
              and lower(teams.name) = 'red') red_score,
            (select count(*)
            from players, scores, teams 
            where players.player_id = scores.player_id 
              and players.team_id = teams.team_id 
              and players.game_id = games.game_id
              and lower(teams.name) = 'blue') blue_score
        from games
        order by games.start_time desc''')
    games = curr.fetchall()
    return render_template('games.html', games=games)

@app.route('/games/create', methods=['GET'])
def create_game():
    db = get_db()
    curr = db.execute('select * from users order by username')
    users = curr.fetchall()
    return render_template('create_game.html', users=users)

def create_game(inputs):
    # Create game
    db = get_db()
    cur = db.execute('''insert into games (start_time) values ((select datetime('now')))''') 
    cur = db.execute('''select max(game_id)game_id from games''')
    game_id = cur.fetchone()['game_id']

    # Create teams
    cur = db.execute('''insert into teams (name) values (?)''', (inputs['team1-name'],))
    cur = db.execute('''select max(team_id) team_id from teams''')
    team1_id = cur.fetchone()['team_id']
    cur = db.execute('''insert into teams (name) values (?)''', (inputs['team2-name'],))
    cur = db.execute('''select max(team_id) team_id from teams''')
    team2_id = cur.fetchone()['team_id']

    # Create players
    cur = db.execute('''insert into players (user_id, game_id, team_id, position) values (?, ?, ?, ?)''',
                     (inputs['team1-position1'], game_id, team1_id, '1'))
    cur = db.execute('''insert into players (user_id, game_id, team_id, position) values (?, ?, ?, ?)''',
                     (inputs['team1-position2'], game_id, team1_id, '2'))
    cur = db.execute('''insert into players (user_id, game_id, team_id, position) values (?, ?, ?, ?)''',
                     (inputs['team1-position3'], game_id, team1_id, '3'))
    cur = db.execute('''insert into players (user_id, game_id, team_id, position) values (?, ?, ?, ?)''',
                     (inputs['team1-position4'], game_id, team1_id, '4'))
    
    cur = db.execute('''insert into players (user_id, game_id, team_id, position) values (?, ?, ?, ?)''',
                     (inputs['team2-position1'], game_id, team2_id, '1'))
    cur = db.execute('''insert into players (user_id, game_id, team_id, position) values (?, ?, ?, ?)''',
                     (inputs['team2-position2'], game_id, team2_id, '2'))
    cur = db.execute('''insert into players (user_id, game_id, team_id, position) values (?, ?, ?, ?)''',
                     (inputs['team2-position3'], game_id, team2_id, '3'))
    cur = db.execute('''insert into players (user_id, game_id, team_id, position) values (?, ?, ?, ?)''',
                    (inputs['team2-position4'], game_id, team2_id, '4'))

    db.commit() 
    return redirect(url_for('edit_game', game_id=game_id))

@app.route('/games/create', methods=['POST'])
def add_game():
    # Check that all required fields are here
    required_fields = ['team1-name', 'team1-position1', 'team1-position2', 'team1-position3',
                       'team1-position4','team2-name', 'team2-position1', 'team2-position2', 
                       'team2-position3', 'team2-position4']

    has_required_fields = True
    for field in required_fields:
        has_required_fields = field in request.form.keys()
    
    if not has_required_fields:
        flash('You must enter values for all fields.')
        return redirect(url_for('create_game'))
  
    else:
        return create_game(request.form)

@app.route('/games/<int:game_id>', methods=['GET'])
def edit_game(game_id):
    # Check if game is ongoing, or if it has ended
    db = get_db()
    cur = db.execute('''select end_time from games where game_id = ?''', (game_id,))
    cur = cur.fetchone()
    time = cur['end_time']

    # Get game 
    cur = db.execute('''select games.game_id,
                            strftime('%m-%d-%Y %H:%M:%S', datetime(games.start_time, 'localtime')) start_time,
                            strftime('%M:%S', datetime(strftime('%s', games.end_time) - strftime('%s', games.start_time), 'unixepoch')) duration
                        from games
                        where game_id = ?''', (game_id,))
    game = cur.fetchone()

    # Get teams
    cur = db.execute('''select distinct teams.*,
                       (select count(*)
                        from scores, players
                        where scores.player_id = players.player_id 
                          and players.team_id = teams.team_id) score 
                from teams, players
                where players.game_id = ?
                  and players.team_id = teams.team_id''', (game_id,))
    team_info = cur.fetchall()

    teams = {}
    teams['red'] = {}
    teams['red']['score'] = [team['score'] for team in team_info if team['name'].lower() == 'red'].pop()
    teams['blue'] = {}
    teams['blue']['score']  = [team['score'] for team in team_info if team['name'].lower() == 'blue'].pop()

    # Get players and scores for each team
    cur = db.execute('''select players.*, 
                            users.username,
                               (select count(*)
                                from scores
                                where scores.player_id = players.player_id) score 
                        from players, users 
                        where players.game_id = ?
                          and players.user_id = users.user_id
                        order by players.position''', (game_id,))
    players = cur.fetchall()

    # Get score history 
    cur = db.execute('''select strftime('%H:%M:%S', datetime(scores.time, 'localtime')) time, 
                               users.username, players.position, teams.name team_name
                        from scores, players, users, teams 
                        where players.game_id = ?
                          and scores.player_id = players.player_id
                          and players.user_id = users.user_id 
                          and players.team_id = teams.team_id 
                        order by scores.time''', (game_id,))
    scores = cur.fetchall()

    cur = db.execute('''
        select strftime('%s', scores.time) time,
               (select count(*)
                from scores s, players p, teams t
                where p.game_id = players.game_id
                  and s.player_id = p.player_id 
                  and t.team_id = p.team_id 
                  and lower(t.name) = 'red' 
                  and s.time <= scores.time) red_score,
               (select count(*)
                from scores s, players p, teams t
                where p.game_id = players.game_id
                  and s.player_id = p.player_id 
                  and t.team_id = p.team_id 
                  and lower(t.name) = 'blue' 
                  and s.time <= scores.time) blue_score,
                users.username,
                teams.name
        from players, scores, users, teams 
        where players.game_id = ?
          and scores.player_id = players.player_id 
          and users.user_id = players.user_id 
          and teams.team_id = players.team_id 
        order by scores.time''', (game_id,))
    running_scores = cur.fetchall()

    cur = db.execute('''
        select players.player_id, players.user_id, players.game_id, players.team_id,
               players.position, teams.name, users.username,
               (select count(*)
                from scores 
                where scores.player_id = players.player_id) score 
        from players, teams, users
        where players.game_id = ?
          and players.team_id = teams.team_id
          and players.user_id = users.user_id''', (game_id,))
    total_players = cur.fetchall()

    # Collect each position into a row for printing
    positions = []
    for position in [(1, 'Goalie'), (2, 'Defender'), (3, 'Center'), (4, 'Striker')]:
        x = {}
        x['position'] = position[1]
        x['red_name'] = [player['username'] for player in total_players if player['position'] == position[0] and 
                    player['name'].lower() == 'red'].pop()
        x['red_id'] = [player['player_id'] for player in total_players if player['position'] == position[0] and 
                    player['name'].lower() == 'red'].pop()
        x['red_score'] = [player['score'] for player in total_players if player['position'] == position[0] and 
                    player['name'].lower() == 'red'].pop()
        x['blue_name'] = [player['username'] for player in total_players if player['position'] == position[0] and 
                    player['name'].lower() == 'blue'].pop()
        x['blue_id'] = [player['player_id'] for player in total_players if player['position'] == position[0] and 
                    player['name'].lower() == 'blue'].pop()
        x['blue_score'] = [player['score'] for player in total_players if player['position'] == position[0] and 
                    player['name'].lower() == 'blue'].pop()
        positions.append(x)

    # Collect total scores by user/player 
    cur = db.execute('''
        select distinct users.username,
               (select count(*)
                from scores, players p
                where scores.player_id = p.player_id
                  and p.user_id = users.user_id
                  and p.game_id = players.game_id) score 
        from players, users 
        where players.game_id = ?
          and players.user_id = users.user_id''', (game_id,))
    scores_by_user = cur.fetchall()

    if time == None:
        # Game is still going
        return render_template('edit_game.html', game=game, teams=teams, players=players, scores=scores,
            positions=positions)
    else:
        # Game is over
        return render_template('edit_game_over.html', game=game, teams=teams, players=players, scores=scores,
            running_scores=running_scores, positions=positions, scores_by_user=scores_by_user)


@app.route("/games/<int:game_id>/score", methods=['POST'])
def score(game_id):
    player_id = request.form['player_id']
    
    if player_id is None:
        flash('Error: No player id was passed for scoring.')
        return redirect(url_for('edit_game', game_id=game_id))

    db = get_db()
    cur = db.execute('''insert into scores (player_id, time) 
                        values (?, (select datetime('now')))''', (player_id,))
    db.commit()

    # Forward back to edit screen 
    return redirect(url_for('edit_game', game_id=game_id))

@app.route("/games/<int:game_id>/end", methods=['POST'])
def end_game(game_id):
    # Add an end time to the game 
    db = get_db()
    cur = db.execute('''update games
                        set end_time = (select datetime('now'))
                        where game_id = ?''', (game_id,))
    db.commit()

    # Forward to edit screen 
    return redirect(url_for('edit_game', game_id=game_id))

@app.route("/games/<int:game_id>/undo", methods=['POST'])
def undo_game(game_id):
    # Check that game isn't already over
    db = get_db() 
    cur = db.execute('''
        select end_time
        from games where game_id = ?''', (game_id,))
    end_time = cur.fetchone()

    # If not over, remove last point scored
    if end_time is not None:
        cur = db.execute('''
            delete from scores 
            where score_id = (
                select score_id 
                from scores 
                where time = (
                    select max(time) 
                    from scores 
                    where player_id in (
                        select player_id 
                        from players
                        where game_id = ?)))''', (game_id,))
        db.commit()

    # Forward back to edit screen 
    return redirect(url_for('edit_game', game_id=game_id))

@app.route("/games/<int:game_id>/rematch", methods=['POST'])
def rematch(game_id):
    # Get players from given game 
    db = get_db()
    cur = db.execute('''
        select players.*
        from players, teams 
        where players.game_id = ?
          and players.team_id = teams.team_id 
          and lower(teams.name) = 'red'
        order by players.position''', (game_id,))
    r_players = cur.fetchall()
    new_positions_red = []
    # Move r_players forward one position
    for i in range(len(r_players)):
        # Get next player
        next = (i - 1) % len(r_players)
        while r_players[i]['user_id'] == r_players[next]['user_id'] and i != next:
            next = (next - 1) % len(r_players)
        new_positions_red.append(next)

    cur = db.execute('''
        select players.*
        from players, teams 
        where players.game_id = ?
          and players.team_id = teams.team_id 
          and lower(teams.name) = 'blue'
        order by players.position''', (game_id,))
    b_players = cur.fetchall()
    new_positions_blue = []
    # Move b_players forward one position
    for i in range(len(b_players)):
        # Get next player
        next = (i - 1) % len(b_players)
        while b_players[i]['user_id'] == b_players[next]['user_id'] and i != next:
            next = (next - 1) % len(b_players)
        new_positions_blue.append(next)

    # Insert new game
    cur = db.execute('''
        insert into games 
        (start_time)
        values 
        ((select datetime('now')))''')
    cur = db.execute('''
        select max(game_id) game_id from games''')
    new_game_id = cur.fetchone()['game_id']

    # Insert teams for game 
    cur = db.execute('''insert into teams (name) values ('Red')''')
    cur = db.execute('''select max(team_id) team_id from teams''')
    red_id = cur.fetchone()['team_id']

    cur = db.execute('''insert into teams (name) values ('Blue')''')
    cur = db.execute('''select max(team_id) team_id from teams''')
    blue_id = cur.fetchone()['team_id']

    # Insert players for game
    currPosition = 1
    for p in new_positions_red:
        cur = db.execute('''insert into players (user_id, game_id, team_id, position)
                values (?, ?, ?, ?)''', (r_players[p]["user_id"], 
                    new_game_id, red_id, currPosition,))
        currPosition += 1

    currPosition = 1
    for p in new_positions_blue:
        cur = db.execute('''insert into players (user_id, game_id, team_id, position)
                values (?, ?, ?, ?)''', (b_players[p]["user_id"], 
                    new_game_id, blue_id, currPosition,))
        currPosition += 1

    db.commit()
    # Forward back to edit screen 
    return redirect(url_for('edit_game', game_id=new_game_id))

@app.route("/static/<path:path>", methods=['GET'])
def serve_static(path):
    return app.send_static_file(os.path.join('static', path))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
