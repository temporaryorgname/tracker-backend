BEGIN;

CREATE TABLE public.meta (
	"key" varchar(255) PRIMARY KEY,
	value TEXT
);
INSERT INTO public.meta (key, value) VALUES ('SCHEMA_VERSION', '0.2');

ALTER TABLE public.users ADD verified_email boolean;
ALTER TABLE public.users ADD last_activity timestamp;

ALTER TABLE public.food ADD parent_id integer REFERENCES public.food(id);

CREATE TABLE public.tags (
	id serial PRIMARY KEY,
	user_id integer REFERENCES public.users(id),
	parent_id integer REFERENCES public.tags(id),
	tag varchar(255),
	description text
);

CREATE TABLE public.journal (
	id serial PRIMARY KEY,
	user_id integer REFERENCES public.users(id),
	start_date date NOT NULL,
	start_time time without time zone,
	end_date date,
	end_time time without time zone,
	note text
);

CREATE TABLE public.journal_tags (
	journal_entry_id integer REFERENCES public.journal(id),
	tag_id integer REFERENCES public.tags(id)
);

CREATE TABLE public.followers (
	follower_id integer REFERENCES public.users(id),
	followee_id integer REFERENCES public.users(id)
);

CREATE TABLE public.food_photo_labels (
	id serial PRIMARY KEY,
	user_id integer REFERENCES public.users(id),
	photo_id integer REFERENCES public.food_photos(id),
	tag_id integer REFERENCES public.tags(id),
	bounding_box box,
	bounding_polygon polygon
);

CREATE TABLE public.exercises (
	id serial PRIMARY KEY,
	name varchar(255),
	description text
);

CREATE TABLE public.workout_set (
	id serial PRIMARY KEY,
	"date" date,
	user_id integer REFERENCES public.users(id),
	exercise_id integer REFERENCES public.exercises(id),
	parent_id integer REFERENCES public.workout_set(id),
	"order" integer,
	reps integer,
	duration integer,
	tempo varchar(64)
);
