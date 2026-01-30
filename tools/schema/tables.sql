--- citext
CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;

--- Developer
CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT,
    reason TEXT,
    PRIMARY KEY (user_id)   
);

CREATE TABLE IF NOT EXISTS traceback (
    error_id TEXT,
    command TEXT,
    guild_id BIGINT,
    channel_id BIGINT,
    user_id BIGINT,
    traceback TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (error_id)
);

CREATE TABLE IF NOT EXISTS donators (
    user_id BIGINT,
    PRIMARY KEY (user_id)
);

--- Fun
CREATE TABLE IF NOT EXISTS marriages (
    user_id BIGINT,
    partner_id BIGINT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS family_relationships (
    child_id BIGINT,
    parent_id BIGINT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (child_id, parent_id)
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT,
    allow_incest BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS blunt (
    guild_id BIGINT,
    user_id BIGINT,
    hits BIGINT  DEFAULT 0,
    passes BIGINT  DEFAULT 0,
    members JSONB[]  DEFAULT '{}'::JSONB[],
    PRIMARY KEY (guild_id)
);

--- Information
CREATE TABLE IF NOT EXISTS birthdays (
    user_id BIGINT,
    date DATE,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS reminders (
    user_id BIGINT,
    text CITEXT,
    jump_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, timestamp)
);

CREATE TABLE IF NOT EXISTS timezone (
    user_id BIGINT,
    location TEXT,
    PRIMARY KEY (user_id)
);

--- Miscellanous
CREATE TABLE IF NOT EXISTS highlight_words (
    user_id BIGINT,
    word TEXT,
    strict BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, word)
);

CREATE TABLE IF NOT EXISTS highlight_block (
    user_id BIGINT,
    entity_id BIGINT,
    PRIMARY KEY (user_id, entity_id)
);

--- Moderation
CREATE TABLE IF NOT EXISTS cases (
    guild_id BIGINT,
    case_id BIGINT,
    case_type TEXT,
    message_id BIGINT,
    moderator_id BIGINT,
    target_id BIGINT,
    moderator TEXT,
    target TEXT,
    reason TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (guild_id, case_id)
);

--- Servers
CREATE TABLE IF NOT EXISTS config (
    guild_id BIGINT UNIQUE,
    prefix TEXT  DEFAULT ',',
    baserole BIGINT DEFAULT NULL,
    voicemaster JSONB  DEFAULT '{}'::JSONB,
    mod_log BIGINT DEFAULT NULL,
    invoke JSONB  DEFAULT '{}'::JSONB,
    lock_ignore JSONB[]  DEFAULT '{}'::JSONB[],
    reskin JSONB  DEFAULT '{}'::JSONB,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS join_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message TEXT,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS leave_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message TEXT,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS boost_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message TEXT,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS booster_roles (
    guild_id BIGINT,
    user_id BIGINT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS aliases (
    guild_id BIGINT,
    alias TEXT,
    command TEXT,
    invoke TEXT,
    PRIMARY KEY (guild_id, alias)
);

CREATE TABLE IF NOT EXISTS reskin (
    user_id BIGINT,
    username TEXT,
    avatar_url TEXT,
    colors JSONB  DEFAULT '{}'::JSONB,
    emojis JSONB  DEFAULT '{}'::JSONB,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS auto_roles (
    guild_id BIGINT,
    role_id BIGINT,
    humans BOOLEAN DEFAULT FALSE,
    bots BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS auto_responses (
    guild_id BIGINT,
    trigger TEXT,
    response TEXT,
    self_destruct BIGINT,
    not_strict BOOLEAN DEFAULT FALSE,
    ignore_command_check BOOLEAN DEFAULT FALSE,
    reply BOOLEAN DEFAULT FALSE,
    delete BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id, trigger)
);

CREATE TABLE IF NOT EXISTS fake_permissions (
    guild_id BIGINT,
    role_id BIGINT,
    permission TEXT,
    PRIMARY KEY (guild_id, role_id, permission)
);

CREATE TABLE IF NOT EXISTS afk (
    user_id BIGINT,
    message TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS reaction_triggers (
    guild_id BIGINT,
    trigger TEXT,
    emoji TEXT,
    strict BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id, trigger, emoji)
);

CREATE TABLE IF NOT EXISTS sticky_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message_id BIGINT,
    message TEXT,
    schedule TEXT,
    PRIMARY KEY (guild_id, channel_id, message_id)
);

--- Starboard
CREATE TABLE IF NOT EXISTS starboard (
    guild_id BIGINT,
    channel_id BIGINT,
    emoji TEXT,
    threshold BIGINT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS starboard_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message_id BIGINT,
    emoji TEXT,
    starboard_message_id BIGINT,
    PRIMARY KEY (guild_id, channel_id, message_id, emoji)
);



--- VoiceMaster
CREATE SCHEMA IF NOT EXISTS voicemaster;

CREATE TABLE IF NOT EXISTS voicemaster.configuration (
    guild_id BIGINT UNIQUE,
    category_id BIGINT,
    interface_id BIGINT,
    channel_id BIGINT,
    role_id BIGINT,
    region TEXT,
    bitrate BIGINT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS voicemaster.channels (
    guild_id BIGINT,
    channel_id BIGINT,
    owner_id BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);


--- Last.FM
CREATE SCHEMA IF NOT EXISTS lastfm_library;

CREATE TABLE IF NOT EXISTS lastfm (
    user_id BIGINT UNIQUE,
    username TEXT,
    config JSONB  DEFAULT '{}'::JSONB
);

CREATE TABLE IF NOT EXISTS lastfm_commands (
    guild_id BIGINT,
    user_id BIGINT,
    command TEXT,
    public BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS lastfm_crowns (
    guild_id BIGINT,
    user_id BIGINT,
    username TEXT,
    artist CITEXT,
    plays BIGINT,
    PRIMARY KEY (guild_id, artist)
);

CREATE TABLE IF NOT EXISTS lastfm_library.artists (
    user_id BIGINT,
    username TEXT,
    artist CITEXT,
    plays BIGINT,
    PRIMARY KEY (user_id, artist)
);

CREATE TABLE IF NOT EXISTS lastfm_library.albums (
    user_id BIGINT,
    username TEXT,
    artist CITEXT,
    album CITEXT,
    plays BIGINT,
    PRIMARY KEY (user_id, artist, album)
);

CREATE TABLE IF NOT EXISTS lastfm_library.tracks (
    user_id BIGINT,
    username TEXT,
    artist CITEXT,
    track CITEXT,
    plays BIGINT,
    PRIMARY KEY (user_id, artist, track)
);


--- Commands-Specific
CREATE SCHEMA IF NOT EXISTS commands;

CREATE TABLE IF NOT EXISTS commands.ignored (
    guild_id BIGINT,
    target_id BIGINT,
    PRIMARY KEY (guild_id, target_id)
);

CREATE TABLE IF NOT EXISTS commands.disabled (
    guild_id BIGINT,
    channel_id BIGINT,
    command TEXT,
    PRIMARY KEY (guild_id, channel_id, command)
);

CREATE TABLE IF NOT EXISTS commands.restricted (
    guild_id BIGINT,
    role_id BIGINT,
    command TEXT,
    PRIMARY KEY (guild_id, role_id, command)
);

--- Metrics
CREATE SCHEMA IF NOT EXISTS metrics;

CREATE TABLE IF NOT EXISTS metrics.names (
    user_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS metrics.avatars (
    user_id BIGINT NOT NULL,
    avatar TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, avatar)
);

CREATE TABLE IF NOT EXISTS metrics.banners (
    user_id BIGINT NOT NULL,
    banner TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, banner)
);

--- GitHub
CREATE TABLE IF NOT EXISTS github_watches (
    guild_id BIGINT,
    channel_id BIGINT,
    repository TEXT,
    last_commit_sha TEXT,
    PRIMARY KEY (guild_id, repository)
);

--- Leveling
CREATE SCHEMA IF NOT EXISTS leveling;

CREATE TABLE IF NOT EXISTS leveling.users (
    guild_id BIGINT,
    user_id BIGINT,
    xp BIGINT DEFAULT 0,
    level BIGINT DEFAULT 0,
    last_message TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS leveling.settings (
    guild_id BIGINT,
    enabled BOOLEAN DEFAULT TRUE,
    xp_rate INTEGER DEFAULT 15,
    xp_cooldown INTEGER DEFAULT 60,
    level_up_channel BIGINT,
    level_up_message TEXT DEFAULT 'Congratulations {user.mention}! You reached level {level}!',
    PRIMARY KEY (guild_id)
);

--- AI
CREATE SCHEMA IF NOT EXISTS ai;

CREATE TABLE IF NOT EXISTS ai.channels (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL
);