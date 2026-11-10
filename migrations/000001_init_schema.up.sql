BEGIN;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    title VARCHAR(200) NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'closed')),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX surveys_creator_id_idx ON surveys (creator_id);

CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id UUID NOT NULL REFERENCES surveys (id) ON DELETE CASCADE,
    text TEXT NOT NULL CHECK (length(trim(text)) > 0),
    type VARCHAR(20) NOT NULL CHECK (type IN ('single_choice', 'multiple_choice', 'text')),
    position INTEGER NOT NULL CHECK (position > 0),
    is_required BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (survey_id, position)
);

CREATE TABLE answer_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
    text TEXT NOT NULL CHECK (length(trim(text)) > 0),
    position INTEGER NOT NULL CHECK (position > 0),
    UNIQUE (question_id, position),
    UNIQUE (question_id, id)
);

CREATE TABLE survey_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id UUID NOT NULL REFERENCES surveys (id) ON DELETE RESTRICT,
    respondent_id UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (survey_id, respondent_id)
);
CREATE INDEX survey_attempts_respondent_id_idx ON survey_attempts (respondent_id);

CREATE TABLE answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID NOT NULL REFERENCES survey_attempts (id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions (id) ON DELETE RESTRICT,
    option_id UUID,
    text_value TEXT,
    FOREIGN KEY (question_id, option_id)
        REFERENCES answer_options (question_id, id) ON DELETE RESTRICT,
    CHECK ((option_id IS NOT NULL) <> (text_value IS NOT NULL))
);
CREATE INDEX answers_question_option_idx ON answers (question_id, option_id);
CREATE UNIQUE INDEX answers_choice_idx ON answers (attempt_id, question_id, option_id)
    WHERE option_id IS NOT NULL;
CREATE UNIQUE INDEX answers_text_idx ON answers (attempt_id, question_id)
    WHERE option_id IS NULL;
CREATE INDEX answers_attempt_id_idx ON answers (attempt_id);

COMMIT;
