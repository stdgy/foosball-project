-- Tables
-- users - user_id, first_name, last_name, age, location
-- games - game_id, start_time, end_time
-- teams - team_id, name
-- players - player_id, user_id, game_id, team_id
-- scores - score_id, player_id, row, time

create table users (
    user_id integer primary key autoincrement,
    username text unique,
    first_name text not null,
    last_name text not null,
    age integer,
    location text
);

create table games (
    game_id integer primary key autoincrement,
    start_time text,
    end_time text
);

create table teams (
    team_id integer primary key autoincrement,
    name text not null
);

create table players (
    player_id integer primary key autoincrement,
    user_id integer,
    game_id integer,
    team_id integer,
    position integer,
    foreign key (user_id) references users(user_id),
    foreign key (game_id) references games(game_id),
    foreign key (team_id) references teams(team_id)
);

create table scores (
    score_id integer primary key autoincrement,
    player_id integer,
    time text not null,
    foreign key (player_id) references players(player_id)
);
