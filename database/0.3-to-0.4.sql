BEGIN;

UPDATE public.meta SET value='0.4' WHERE key='SCHEMA_VERSION';

CREATE TABLE public.user_profile (
	id integer REFERENCES public.users(id) PRIMARY KEY,
	display_name varchar(256),
	last_activity date,
	gender varchar(64),
	prefered_units varchar(32),
	target_weight numeric,
	target_calories numeric,
	weight_goal varchar(64),
	country varchar(128),
	state varchar(128),
	city varchar(128)
);
INSERT INTO public.user_profile (id, display_name, last_activity) SELECT id, name, last_activity FROM public.users;

ALTER TABLE public.users DROP COLUMN name;
ALTER TABLE public.users DROP COLUMN last_activity;

CREATE TABLE public.tag_relation (
	parent_id integer REFERENCES public.tag(id),
	child_id integer REFERENCES public.tag(id)
);
ALTER TABLE public.tag DROP COLUMN parent_id;
