BEGIN;

UPDATE public.meta SET value='0.4' WHERE key='SCHEMA_VERSION';

ALTER TABLE public.users ADD prefered_units varchar(32);
ALTER TABLE public.users ADD target_weight numeric;
ALTER TABLE public.users ADD target_calories numeric;
ALTER TABLE public.users ADD weight_goal varchar(64);
ALTER TABLE public.users ADD country varchar(128);
ALTER TABLE public.users ADD state varchar(128);
ALTER TABLE public.users ADD city varchar(128);

CREATE TABLE public.tag_relation (
	parent_id integer REFERENCES public.tag(id),
	child_id integer REFERENCES public.tag(id)
);
ALTER TABLE public.tag DROP COLUMN parent_id;
